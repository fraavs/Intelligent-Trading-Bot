from typing import Union
import json


class App:
    """Globally visible variables."""

    #
    # Server instance variables
    #

    # System
    loop = None  # asyncio main loop
    sched = None  # Scheduler
    database = None  # Store and analyze data

    # Connector client
    client = None

    # WebSocket for push notifications
    bm = None
    conn_key = None  # Socket

    signal = None,

    #
    # State of the server (updated after each interval)
    #
    # State 0 or None or empty means ok. String and other non empty objects mean error
    error_status = 0  # Networks, connections, exceptions etc. what does not allow us to work at all
    server_status = 0  # If server allow us to trade (maintenance, down etc.)
    account_status = 0  # If account allows us to trade (funds, suspended etc.)
    trade_state_status = 0  # Something wrong with our trading logic (wrong use, inconsistent state etc. what we cannot recover)

    # Trade status
    status = None  # BOUGHT, SOLD, BUYING, SELLING
    order = None  # Latest or current order
    order_time = None  # Order submission time

    # Available assets for trade
    # Can be set by the sync/recover function or updated by the trading algorithm
    base_quantity = "0.04108219"  # BTC owned (on account, already bought, available for trade)
    quote_quantity = "1000.0"  # USDT owned (on account, available for trade)

    #
    # Trder. Status data retrieved from the server. Below are examples only.
    #
    system_status = {"status": 0, "msg": "normal"}  # 0: normal，1：system maintenance
    symbol_info = {
        "symbol": "BTCUSDT",
        "status": "TRADING",
        "baseAsset": "BTC",
        "baseAssetPrecision": 8,
        "quoteAsset": "USDT",
        "quotePrecision": 8,
        "orderTypes": ["LIMIT", "LIMIT_MAKER", "MARKET", "STOP_LOSS_LIMIT", "TAKE_PROFIT_LIMIT"],
        "icebergAllowed": True,
        "ocoAllowed": True,
        "isSpotTradingAllowed": True,
        "isMarginTradingAllowed": True,
        "filters": [],
    }
    account_info = {
        "makerCommission": 15,
        "takerCommission": 15,
        "buyerCommission": 0,
        "sellerCommission": 0,
        "canTrade": True,
        "canWithdraw": True,
        "canDeposit": True,
        "balances": [
            {"asset": "BTC", "free": "4723846.89208129", "locked": "0.00000000"},
            {"asset": "LTC", "free": "4763368.68006011", "locked": "0.00000000"},
        ]
    }

    #
    # Constant configuration parameters
    #
    config = {
        "command": "collector",  # "collector" "trader"

        "api_key": "***REMOVED***",
        "api_secret": "***REMOVED***",

        "symbol": "BTCUSDT",
        "base_asset": "BTC",
        "quote_asset": "USDT",

        # === NAMES ===

        # Target columns with true values which will be predicted
        # Leave only what we want to be generated (e.g., only one label for debug purposes)
        "labels": [
            'high_10', 'high_15', 'high_20',
            'low_10', 'low_15', 'low_20',
        ],
        "labels_regr": [
            'high_max_60','high_max_120','high_max_180',  # Maximum high (relative)
            'low_min_60','low_min_120','low_min_180',  # Minimum low (relative)
            'high_to_low_60', 'high_to_low_120', 'high_to_low_180',
            'close_area_future_60', 'close_area_future_120', 'close_area_future_180', 'close_area_future_300',
        ],
        "class_labels_all": [  # All existing target labels implemented in label generation procedure
            'high_max_60','high_max_120','high_max_180',  # Maximum high (relative)
            'high_10', 'high_15', 'high_20', 'high_25',  # At least one time above
            'high_01', 'high_02', 'high_03', 'high_04',  # Always below

            'low_min_60','low_min_120','low_min_180',  # Minimum low (relative)
            'low_01', 'low_02', 'low_03', 'low_04',  # Always above
            'low_10', 'low_15', 'low_20', 'low_25',  # At least one time below

            'high_to_low_60','high_to_low_120','high_to_low_180',

            'close_area_future_60','close_area_future_120','close_area_future_180','close_area_future_300',
            ],

        "features_kline": [  # Feature columns implemented (hard-coded) by feature generation function
            'close_1','close_5','close_15','close_60','close_180','close_720',
            'close_std_5','close_std_15','close_std_60','close_std_180','close_std_720',  # Removed "std_1" which is constant
            'volume_1','volume_5','volume_15','volume_60','volume_180','volume_720',
            'span_1', 'span_5', 'span_15', 'span_60', 'span_180', 'span_720',
            'trades_1','trades_5','trades_15','trades_60','trades_180','trades_720',
            'tb_base_1','tb_base_5','tb_base_15','tb_base_60','tb_base_180','tb_base_720',
            'tb_quote_1','tb_quote_5','tb_quote_15','tb_quote_60','tb_quote_180','tb_quote_720',
            'close_area_60', 'close_area_120', 'close_area_180', 'close_area_300', 'close_area_720',
            'close_trend_5', 'close_trend_15', 'close_trend_60', 'close_trend_180', 'close_trend_720',
        ],  # 51 features

        "features_futur": [  # Feature columns implemented (hard-coded) by feature generation function
            "f_close_1", "f_close_2", "f_close_5", "f_close_20", "f_close_60", "f_close_180",
            "f_close_std_2", "f_close_std_5", "f_close_std_20", "f_close_std_60", "f_close_std_180",  # Removed "std_1" which is constant
            "f_volume_1", "f_volume_2", "f_volume_5", "f_volume_20", "f_volume_60", "f_volume_180",
            "f_span_1", "f_span_2", "f_span_5", "f_span_20", "f_span_60", "f_span_180",
            "f_trades_1", "f_trades_2", "f_trades_5", "f_trades_20", "f_trades_60", "f_trades_180",
            'f_close_area_20', 'f_close_area_60', 'f_close_area_120', 'f_close_area_180',
            'close_trend_2', 'close_trend_5', 'close_trend_20', 'close_trend_60', 'close_trend_180',
        ],  # 38 features

        "features_depth": [
            "gap_2","gap_5","gap_10",
            "bids_1_2","bids_1_5","bids_1_10", "asks_1_2","asks_1_5","asks_1_10",
            "bids_2_2","bids_2_5","bids_2_10", "asks_2_2","asks_2_5","asks_2_10",
            "bids_5_2","bids_5_5","bids_5_10", "asks_5_2","asks_5_5","asks_5_10",
            "bids_10_2","bids_10_5","bids_10_10", "asks_10_2","asks_10_5","asks_10_10",
            "bids_20_2","bids_20_5","bids_20_10", "asks_20_2","asks_20_5","asks_20_10",
        ],

        # === COLLECTOR SERVER ===
        "collector": {
            "folder": "DATA",
            "flush_period": 300,  # seconds
            "depth": {
                "folder": "DEPTH",
                "symbols": ["BTCUSDT", "ETHBTC", "ETHUSDT", "IOTAUSDT", "IOTABTC", "IOTAETH"],
                "limit": 100,  # Legal values (depth): '5, 10, 20, 50, 100, 500, 1000, 5000' <100 weight=1
                "freq": "1m",  # Binance standard frequency: 5s, 1m etc.
            },
            "stream": {
                "folder": "STREAM",
                # Stream formats:
                # For kline channel: <symbol>@kline_<interval>, Event type: "e": "kline", Symbol: "s": "BNBBTC"
                # For depth channel: <symbol>@depth<levels>[@100ms], Event type: NO, Symbol: NO
                # btcusdt@ticker
                "channels": ["kline_1m", "depth20"],  # kline_1m, depth20, depth5
                "symbols": ["BTCUSDT", "ETHBTC", "ETHUSDT", "IOTAUSDT", "IOTABTC", "IOTAETH"],  # "BTCUSDT", "ETHBTC", "ETHUSDT", "IOTAUSDT", "IOTABTC", "IOTAETH"
            }
        },

        # === SIGNALER SERVER ===
        "signaler": {
            "analysis": {  # Same for all symbols
                "folder": "_TEMP_MODELS",
                # History needed to compute derived features
                # Take base aggregation from feature generation code and add something
                "features_horizon": 1440+160,
            },
            "model": {
                # Model 4 [0.4, -0.44]
                "buy_threshold": 0.25,
                "sell_threshold": -0.52,
            },
        },

        # === TRADER SERVER ===
        "trader": {
            "folder": "DATA",

            # For debugging: determine what parts of code will be executed
            "no_trades_only_data_processing": False,  # in market or out of market processing is excluded (all below parameters ignored)
            "test_order_before_submit": False,  # Send test submit to the server as part of validation
            "simulate_order_execution": False,  # Instead of real orders, simulate their execution (immediate buy/sell market orders and use high price of klines for limit orders)

            "percentage_used_for_trade": 99,  # in % to the available USDT quantity, that is, we will derive how much BTC to buy using this percentage
            "limit_price_adjustment": -0.0001,  # Limit price of orders will be better than the latest close price (0 means no change, positive - better for us, negative - worse for us)

            # Signal model (trade strategy) - currently NOT USED
            "sell_timeout": 70,  # Seconds
            "percentage_sell_price": 1.018,  # our planned profit per trade via limit sell order (part of the model)
        },
    }

    """
    Approach 2: Indirect access via static methods
    port = App.conf("MYSQL_PORT")
    App.set("username", "hi")
    """
    __conf = {
        "username": "",
        "password": "",
        "MYSQL_PORT": 3306,
        "MYSQL_DATABASE": 'mydb',
        "MYSQL_DATABASE_TABLES": ['tb_users', 'tb_groups']
    }
    __setters = ["username", "password"]  # A list of (configuration) names which can be set

    @staticmethod
    def conf(name):
        return App.__conf[name]

    @staticmethod
    def set(name, value):
        if name in App.__setters:
            App.__conf[name] = value
        else:
            raise NameError("Name not accepted in set() method")

    # TODO: Lock for synchronization of access to shared resources
    # INFO: use queue instead of asynchio https://docs.python.org/3/library/queue.html


class Debug:
    parameter_debug = 234


def data_provider_problems_exist():
    if App.error_status != 0:
        return True
    if App.server_status != 0:
        return True
    return False

def problems_exist():
    if App.error_status != 0:
        return True
    if App.server_status != 0:
        return True
    if App.account_status != 0:
        return True
    if App.trade_state_status != 0:
        return True
    return False


if __name__ == "__main__":
    import requests

    bot_token = "***REMOVED***"
    chat_id = "-***REMOVED***"  #"***REMOVED***" (al su) "-***REMOVED***" (ITB)
    text = "Score: *123*"

    #bot = telegram.Bot(token=token)
    #bot.sendMessage(chat_id="***REMOVED***", text=text, parse_mode=telegram.ParseMode.HTML)

    # It does not work for users (number) - chat not found error
    url = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=markdown&text=' + text

    response = requests.get(url)
    response_json = response.json()

    pass
