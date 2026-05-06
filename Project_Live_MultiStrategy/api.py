import os
import pickle
import subprocess
import sys
from typing import Optional

import mysql.connector
import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
ENV_PATH          = os.path.abspath(os.path.join(BASE_DIR, "shared", ".env"))
ACCESS_TOKEN_FILE = os.path.abspath(os.path.join(BASE_DIR, "shared", "access_token.txt"))
LOGS_DIR          = os.path.abspath(os.path.join(BASE_DIR, "logs"))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(ENV_PATH)


def _env(key, default=""):
    val = os.getenv(key, default)
    return val.strip('"').strip("'").strip() if val else default


API_KEY     = _env("KITE_API_KEY")
API_SECRET  = _env("KITE_API_SECRET")
DB_HOST     = _env("DB_HOST", "localhost")
DB_USER     = _env("DB_USER", "root")
DB_PASSWORD = _env("DB_PASSWORD", "")
DB_NAME     = _env("DB_NAME", "trading_bot_live")

STRATEGIES = {
    "GREEN": {
        "folder": os.path.abspath(os.path.join(BASE_DIR, "Green Strategy")),
        "runner": os.path.abspath(os.path.join(BASE_DIR, "Green Strategy", "main_runner.py")),
        "table":  "symbols_green",
        "color":  "#2ea043",
    },
    "GREEN3": {
        "folder": os.path.abspath(os.path.join(BASE_DIR, "Green3 Strategy")),
        "runner": os.path.abspath(os.path.join(BASE_DIR, "Green3 Strategy", "main_runner.py")),
        "table":  "symbols_green3",
        "color":  "#58a6ff",
    },
}

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="MultiStrategy Live API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB helpers (MySQL) ────────────────────────────────────────────────────────
def _db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )


def db_fetchall(query: str, params=()):
    conn = _db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        conn.close()


def db_exec(query: str, params=()):
    conn = _db()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
    finally:
        conn.close()


def db_scalar(query: str, params=()):
    conn = _db()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        r = cursor.fetchone()
        return r[0] if r else 0
    finally:
        conn.close()


# ── Kite helpers ──────────────────────────────────────────────────────────────
def get_kite():
    """Return a KiteConnect instance with access token set, or None."""
    if not API_KEY:
        return None
    if not os.path.exists(ACCESS_TOKEN_FILE):
        return None
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=API_KEY, timeout=10)
        with open(ACCESS_TOKEN_FILE) as f:
            tok = f.read().strip()
        if not tok:
            return None
        kite.set_access_token(tok)
        return kite
    except Exception as e:
        print(f"[get_kite] error: {e}")
        return None


def kite_logged_in() -> bool:
    if not API_KEY:
        return False
    if not os.path.exists(ACCESS_TOKEN_FILE):
        return False
    try:
        with open(ACCESS_TOKEN_FILE) as f:
            tok = f.read().strip()
        return bool(tok)
    except Exception:
        return False


# ── Process helpers ───────────────────────────────────────────────────────────
import time as _time

_proc_cache: dict = {}
_proc_cache_ts: float = 0.0
_PROC_CACHE_TTL = 2.0


def _scan_all_procs() -> dict:
    runner_map = {
        os.path.normcase(os.path.abspath(meta["runner"])): name
        for name, meta in STRATEGIES.items()
    }
    found: dict = {name: None for name in STRATEGIES}
    for p in psutil.process_iter(["pid", "cmdline", "status"]):
        try:
            if p.info["status"] == psutil.STATUS_ZOMBIE:
                continue
            cmd = os.path.normcase(" ".join(p.info.get("cmdline") or []))
            for norm_runner, name in runner_map.items():
                if norm_runner in cmd:
                    found[name] = p
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found


def _get_proc_cache() -> dict:
    global _proc_cache, _proc_cache_ts
    now = _time.monotonic()
    if now - _proc_cache_ts > _PROC_CACHE_TTL:
        _proc_cache    = _scan_all_procs()
        _proc_cache_ts = now
    return _proc_cache


def _find_proc(runner: str):
    norm = os.path.normcase(os.path.abspath(runner))
    cache = _get_proc_cache()
    for name, meta in STRATEGIES.items():
        if os.path.normcase(os.path.abspath(meta["runner"])) == norm:
            return cache.get(name)
    return None


def _invalidate_proc_cache():
    global _proc_cache_ts
    _proc_cache_ts = 0.0


def is_running(strategy: str) -> bool:
    p = _get_proc_cache().get(strategy)
    return p is not None


# ── Pydantic models ───────────────────────────────────────────────────────────
class SessionRequest(BaseModel):
    request_token: str


class SymbolRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"


# ═════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/status")
def get_status():
    # Check trading lock from base_config
    trading_enabled = False
    try:
        import importlib.util
        base_cfg_path = os.path.join(BASE_DIR, "shared", "base_config.py")
        spec = importlib.util.spec_from_file_location("base_config_check", base_cfg_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        trading_enabled = bool(getattr(mod, "REAL_TRADING_ENABLED", False))
    except Exception:
        pass

    cache = _get_proc_cache()
    result = {}
    for strategy, meta in STRATEGIES.items():
        running    = cache.get(strategy) is not None
        sym_count  = 0
        open_count = 0
        try:
            conn = mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
            )
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {meta['table']}")
            sym_count = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM {meta['table']} WHERE isExecuted=1")
            open_count = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            print(f"[status] DB error for {strategy}: {e}")
        result[strategy] = {
            "running":         running,
            "symbol_count":    sym_count,
            "open_count":      open_count,
            "color":           meta["color"],
            "trading_enabled": trading_enabled,
        }
    return result


@app.get("/api/kite/status")
def kite_status():
    return {"logged_in": kite_logged_in()}


@app.get("/api/kite/login_url")
def kite_login_url():
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not configured")
    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=API_KEY)
    return {"url": kite.login_url()}


@app.post("/api/kite/session")
def kite_session(body: SessionRequest):
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "API_KEY or API_SECRET not configured"}
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=API_KEY)
        data = kite.generate_session(body.request_token, api_secret=API_SECRET)
        with open(ACCESS_TOKEN_FILE, "w") as f:
            f.write(data["access_token"])
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/symbols/{strategy}")
def get_symbols(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    try:
        return db_fetchall(
            f"SELECT symbol, exchange, instrument_token, isExecuted FROM {STRATEGIES[strategy]['table']} ORDER BY symbol"
        )
    except Exception:
        return []


@app.post("/api/symbols/{strategy}")
def add_symbol(strategy: str, body: SymbolRequest):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    kite = get_kite()
    if kite is None:
        raise HTTPException(status_code=401, detail="Kite session missing — login first")
    try:
        inst = f"{body.exchange.upper()}:{body.symbol.upper()}"
        ltp_data = kite.ltp(inst)
        token = ltp_data[inst]["instrument_token"]
        table = STRATEGIES[strategy]["table"]
        db_exec(
            f"INSERT INTO {table} (symbol, exchange, instrument_token, isExecuted) VALUES (%s, %s, %s, 0) "
            f"ON DUPLICATE KEY UPDATE exchange=%s, instrument_token=%s",
            (body.symbol.upper(), body.exchange.upper(), token, body.exchange.upper(), token),
        )
        return {"success": True, "token": token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/symbols/{strategy}/{symbol}")
def delete_symbol(strategy: str, symbol: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    db_exec(
        f"DELETE FROM {STRATEGIES[strategy]['table']} WHERE symbol=%s",
        (symbol.upper(),),
    )
    return {"success": True}


@app.get("/api/df/{strategy}/{symbol}")
def get_df(strategy: str, symbol: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    meta = STRATEGIES[strategy]
    cache_path = os.path.join(meta["folder"], "live_df_cache.pkl")
    if not os.path.exists(cache_path):
        return {"candle_count": 0, "last_candle": None, "columns": [], "data": []}
    try:
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
        if symbol.upper() not in cache:
            return {"candle_count": 0, "last_candle": None, "columns": [], "data": []}
        df = cache[symbol.upper()]
        candle_count = len(df)
        last_candle = None
        if not df.empty and "date" in df.columns:
            last_candle = str(df.iloc[-1]["date"])
        df_tail = df.tail(500).fillna("")
        return {
            "candle_count": candle_count,
            "last_candle":  last_candle,
            "columns":      list(df_tail.columns),
            "data":         df_tail.to_dict(orient="records"),
        }
    except Exception as e:
        return {"candle_count": 0, "last_candle": None, "columns": [], "data": [], "error": str(e)}


@app.get("/api/positions")
def get_positions():
    rows = []
    for strategy, meta in STRATEGIES.items():
        try:
            strategy_rows = db_fetchall(
                f"SELECT symbol, buyprice, buytime, product FROM {meta['table']} WHERE isExecuted=1"
            )
            for r in strategy_rows:
                r["strategy"] = strategy
            rows.extend(strategy_rows)
        except Exception:
            pass
    return rows


@app.get("/api/history")
def get_history():
    try:
        rows = db_fetchall(
            "SELECT strategy, symbol, buytime, buyprice, selltime, sellprice, pnl, reason "
            "FROM trades_log ORDER BY id DESC LIMIT 200"
        )
        return rows
    except Exception:
        return []


@app.get("/api/terminal/{strategy}")
def get_terminal(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    log_path = os.path.join(LOGS_DIR, f"{strategy.lower()}_terminal.log")
    if not os.path.exists(log_path):
        return {"lines": "No log yet. Start the strategy first."}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": "".join(lines[-200:]) or "Log is empty."}
    except Exception as e:
        return {"lines": f"Error reading log: {e}"}


@app.delete("/api/terminal/{strategy}")
def clear_terminal(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    log_path = os.path.join(LOGS_DIR, f"{strategy.lower()}_terminal.log")
    try:
        open(log_path, "w").close()
    except Exception:
        pass
    return {"success": True}


@app.post("/api/strategy/{strategy}/start")
def start_strategy(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    meta = STRATEGIES[strategy]
    if is_running(strategy):
        return {"success": True, "message": "Already running"}
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [sys.executable, meta["runner"]],
        cwd=meta["folder"],
        **kwargs,
    )
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/strategy/{strategy}/stop")
def stop_strategy(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    p = _find_proc(STRATEGIES[strategy]["runner"])
    if p:
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/strategy/{strategy}/terminate")
def terminate_strategy(strategy: str):
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    p = _find_proc(STRATEGIES[strategy]["runner"])
    if p:
        try:
            for c in p.children(recursive=True):
                c.kill()
            p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/strategy/stop-all")
def stop_all():
    for strategy in STRATEGIES:
        p = _find_proc(STRATEGIES[strategy]["runner"])
        if p:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/strategy/kill-all")
def kill_all():
    for strategy in STRATEGIES:
        p = _find_proc(STRATEGIES[strategy]["runner"])
        if p:
            try:
                for c in p.children(recursive=True):
                    c.kill()
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    _invalidate_proc_cache()
    return {"success": True}


@app.post("/api/setup-db")
def setup_db():
    """Initialize MySQL database and tables for all strategies."""
    try:
        from shared.setup_system.setup_db import initialize_live_database
        success = initialize_live_database(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
        if success:
            return {"success": True, "message": f"Database '{DB_NAME}' ready."}
        return {"success": False, "error": "Setup failed — check server logs."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/set-defaults")
def set_defaults():
    """Reset all positions and fill missing instrument tokens."""
    try:
        import time as _t
        from shared.candle_data import search_kite_symbol
        kite = get_kite()
        if not kite:
            return {"success": False, "error": "Kite session missing — login first"}

        total_updated = 0
        for strategy, meta in STRATEGIES.items():
            table = meta["table"]
            try:
                # Reset open positions
                db_exec(
                    f"UPDATE {table} SET isExecuted=0, buyprice=NULL, buytime=NULL, "
                    f"buy_order_id=NULL, product='MIS'"
                )
                # Fill missing tokens
                rows = db_fetchall(
                    f"SELECT id, symbol, exchange FROM {table} "
                    f"WHERE instrument_token IS NULL OR instrument_token=0"
                )
                for row in rows:
                    token = search_kite_symbol(kite, row["exchange"] or "NSE", row["symbol"])
                    if token:
                        db_exec(
                            f"UPDATE {table} SET instrument_token=%s WHERE id=%s",
                            (token, row["id"]),
                        )
                        total_updated += 1
                    _t.sleep(0.35)
            except Exception as e:
                print(f"[set-defaults] {strategy}: {e}")

        return {"success": True, "updated": total_updated}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/symbols/{strategy}/reload-cache")
def reload_symbol_cache(strategy: str):
    """Signal the strategy process to reload symbols from DB on next cycle."""
    strategy = strategy.upper()
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Unknown strategy")
    signal_file = os.path.join(STRATEGIES[strategy]["folder"], ".reload_symbols")
    try:
        open(signal_file, "w").close()
        return {"success": True, "message": f"{strategy} will reload symbols on next cycle."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/symbols/reload-all")
def reload_all_symbol_caches():
    """Signal all strategy processes to reload symbols."""
    for strategy, meta in STRATEGIES.items():
        signal_file = os.path.join(meta["folder"], ".reload_symbols")
        try:
            open(signal_file, "w").close()
        except Exception:
            pass
    return {"success": True, "message": "All strategies will reload symbols on next cycle."}


@app.post("/api/server/stop")
def stop_server():
    """Gracefully stop the API server."""
    import threading
    def _shutdown():
        import time as _t
        _t.sleep(0.5)
        os._exit(0)
    threading.Thread(target=_shutdown, daemon=True).start()
    return {"success": True, "message": "Server shutting down..."}
