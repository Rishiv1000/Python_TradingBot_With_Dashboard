import time


def _verify_position(kite, symbol, exchange, expected_qty):
    """
    Verify Zerodha account actually holds `expected_qty` for the symbol.
    Returns (actual_qty, ok: bool)
    """
    try:
        positions = kite.positions()
        all_pos = positions.get("day", []) + positions.get("net", [])
        for pos in all_pos:
            if pos["tradingsymbol"].upper() == symbol.upper() and pos["exchange"].upper() == exchange.upper():
                actual_qty = pos["quantity"]
                ok = (actual_qty == expected_qty)
                return actual_qty, ok
        # Symbol not found in positions — qty is 0
        return 0, (expected_qty == 0)
    except Exception as e:
        print(f"⚠️ Position verify failed for {symbol}: {e}")
        return None, False


def place_real_buy(kite, symbol, quantity, exchange, config):
    if not getattr(config, "REAL_TRADING_ENABLED", False):
        print(f"[BLOCK] REAL_TRADING is disabled. Simulated buy for {symbol}.")
        return f"SIMULATED-BUY-{symbol}-{int(time.time())}"

    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        ltp = kite.ltp(instrument)[instrument]["last_price"]

        # Aggressive limit — 0.5% above LTP so it fills immediately (like market order)
        slippage = getattr(config, "BUY_SLIPPAGE", 0.5)
        limit_price = round(ltp * (1 + slippage / 100), 1)

        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=exchange.upper(),
            tradingsymbol=symbol.upper(),
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=quantity,
            order_type=kite.ORDER_TYPE_LIMIT,
            price=limit_price,
            product=kite.PRODUCT_MIS,
        )
        print(f"✅ BUY order placed: {symbol} @ {limit_price} (LTP={ltp}) | order_id: {order_id}")

        # Verify account actually holds the position
        time.sleep(1.5)
        actual_qty, ok = _verify_position(kite, symbol, exchange, quantity)
        if ok:
            print(f"✅ Position verified: {symbol} qty={actual_qty}")
        else:
            print(f"⚠️ Position mismatch: {symbol} expected={quantity}, actual={actual_qty}")

        return order_id
    except Exception as e:
        print(f"❌ BUY order failed for {symbol}: {e}")
        return None


def place_real_sell(kite, symbol, quantity, exchange, product, config, tag=None):
    if not getattr(config, "REAL_TRADING_ENABLED", False):
        print(f"[BLOCK] REAL_TRADING is disabled. Simulated sell for {symbol}.")
        return f"SIMULATED-SELL-{symbol}-{int(time.time())}"

    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        ltp = kite.ltp(instrument)[instrument]["last_price"]

        # Aggressive limit — 0.5% below LTP so it fills immediately (like market order)
        slippage = getattr(config, "SELL_SLIPPAGE", 0.5)
        limit_price = round(ltp * (1 - slippage / 100), 1)

        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=exchange.upper(),
            tradingsymbol=symbol.upper(),
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=quantity,
            order_type=kite.ORDER_TYPE_LIMIT,
            price=limit_price,
            product=product,
            tag=str(tag)[:20] if tag else None,
        )
        print(f"✅ SELL order placed: {symbol} @ {limit_price} (LTP={ltp}) | order_id: {order_id}")

        # Verify position is now closed (qty = 0)
        time.sleep(1.5)
        actual_qty, ok = _verify_position(kite, symbol, exchange, 0)
        if ok:
            print(f"✅ Position closed: {symbol} qty=0")
        else:
            print(f"⚠️ Position NOT cleared: {symbol} still showing qty={actual_qty}")

        return order_id
    except Exception as e:
        print(f"❌ SELL order failed for {symbol}: {e}")
        return None
