# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy import IStrategy
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter
from freqtrade.persistence import Trade

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from datetime import datetime, timedelta

class ActionZone(IStrategy):
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 2

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        "0": 100000
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -1.00
    use_custom_stoploss = True

    # Trailing stoploss
    trailing_stop = False
    # trailing_only_offset_is_reached = False
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.0  # Disabled / not configured


    # Optimal timeframe for the strategy.
    timeframe = '1d'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the "ask_strategy" section in the config.
    use_exit_signal = True
    exit_profit_only = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Number of candles used for calculations in lowest price of period
    min_price_period: int = 32

    # max loss able for calculation position size
    max_loss_per_trade = 10 # USD

    fast_ma_period = 12
    slow_ma_period = 26

    # Optional order type mapping.
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }

    plot_config = {
        'main_plot': {
            'fastMA': {
                'color': 'red',
                'fill_to': 'slowMA',
                'fill_color': 'rgba(232, 232, 232,0.2)'
            }, 
            'slowMA': {
                'color': 'blue',
            },
        },
    }
    
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float, min_stake: float, max_stake: float, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        stop_price = last_candle['lowest']
        volume_for_buy = self.max_loss_per_trade / (current_rate - stop_price)
        use_money = volume_for_buy * current_rate

        return use_money

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """

        # MIN - Lowest value over a specified period
        lowest = ta.MIN(dataframe, timeperiod=self.min_price_period)
        dataframe['lowest'] = lowest

        # EMA - Exponential Moving Average
        fastEMA = ta.EMA(dataframe, timeperiod=self.fast_ma_period)
        slowEMA = ta.EMA(dataframe, timeperiod=self.slow_ma_period)
        dataframe['fastMA'] = fastEMA
        dataframe['slowMA'] = slowEMA


        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                (dataframe['fastMA'] > dataframe['slowMA']) &  # Bull
                (dataframe['close'] > dataframe['fastMA'] ) & # Price Cross Up
                (dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with sell column
        """
        dataframe.loc[
            (
                (dataframe['fastMA'] < dataframe['slowMA']) & # Bear
                (dataframe['close'] < dataframe['fastMA'] ) & # Price Cross Down
                (dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'exit_long'] = 1
        return dataframe
    
    

