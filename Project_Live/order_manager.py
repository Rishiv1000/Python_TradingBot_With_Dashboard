import time
import db_manager.config as config

def place_real_buy(kite, symbol, quantity, exchange):
    """
    Places a limit buy order with slippage.
    """
    if not getattr(config, 'REAL_TRADING_ENABLED', False):
        print(f"🔒 [BLOCK] REAL_TRADING is DISABLED in config. Skipping buy for {symbol}")
        return f"SIMULATED-BUY-{symbol}-{int(time.time())}"

    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        ltp_data = kite.ltp(instrument)
        ltp = ltp_data[instrument]["last_price"]
        
        # Calculate limit price with slippage
        slippage = getattr(config, 'BUY_SLIPPAGE', 0.10)
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
        print(f"✅ BUY Order Placed: {symbol} @ {limit_price} (ID: {order_id})")
        return order_id
    except Exception as e:
        print(f"❌ BUY Order Failed for {symbol}: {e}")
        return None

def place_real_sell(kite, symbol, quantity, exchange, product, tag=None):
    """
    Places a limit sell order for an existing position.
    """
    if not getattr(config, 'REAL_TRADING_ENABLED', False):
        print(f"🔒 [BLOCK] REAL_TRADING is DISABLED in config. Skipping sell for {symbol}")
        return f"SIMULATED-SELL-{symbol}-{int(time.time())}"

    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        ltp_data = kite.ltp(instrument)
        ltp = ltp_data[instrument]["last_price"]
        
        # Calculate limit price with slippage
        slippage = getattr(config, 'SELL_SLIPPAGE', 0.10)
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
            tag=str(tag)[:20] if tag else None
        )
        print(f"✅ SELL Order Placed: {symbol} @ {limit_price} (ID: {order_id})")
        return order_id
    except Exception as e:
        print(f"❌ SELL Order Failed for {symbol}: {e}")
        return None
