import time


def place_real_buy(kite, symbol, quantity, exchange, config):
    if not getattr(config, "REAL_TRADING_ENABLED", False):
        print(f"[BLOCK] REAL_TRADING is disabled. Simulated buy for {symbol}.")
        return f"SIMULATED-BUY-{symbol}-{int(time.time())}"

    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        ltp = kite.ltp(instrument)[instrument]["last_price"]
        slippage = getattr(config, "BUY_SLIPPAGE", 0.10)
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
        print(f"BUY order placed: {symbol} @ {limit_price} ({order_id})")
        return order_id
    except Exception as e:
        print(f"BUY order failed for {symbol}: {e}")
        return None


def place_real_sell(kite, symbol, quantity, exchange, product, config, tag=None):
    if not getattr(config, "REAL_TRADING_ENABLED", False):
        print(f"[BLOCK] REAL_TRADING is disabled. Simulated sell for {symbol}.")
        return f"SIMULATED-SELL-{symbol}-{int(time.time())}"

    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        ltp = kite.ltp(instrument)[instrument]["last_price"]
        slippage = getattr(config, "SELL_SLIPPAGE", 0.10)
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
        print(f"SELL order placed: {symbol} @ {limit_price} ({order_id})")
        return order_id
    except Exception as e:
        print(f"SELL order failed for {symbol}: {e}")
        return None
