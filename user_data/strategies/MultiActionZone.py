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
from technical.util import resample_to_interval, resampled_merge

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from datetime import datetime, timedelta

class MultiActionZone(IStrategy):
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
    timeframe = '4h'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the "ask_strategy" section in the config.
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Number of candles used for calculations in lowest price of period
    min_price_period: int = 32

    # max loss able for calculation position size
    max_loss_per_trade = 10 # USD

    long_period = 360

    # Optional order type mapping.
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc'
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
            'resample_{}_fastMA'.format(4 * long_period): {
                'color': '#ffccd5',
            }, 
            'resample_{}_slowMA'.format(4 * long_period): {
                'color': '#89c2d9',
            },
            'lowest': {
                'color': '#fff3b0',
            }
        },
    }
    

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        stoploss_price = last_candle['lowest']

        # set stoploss when is new order
        if current_profit == 0 and current_time - timedelta(minutes=1) < trade.open_date_utc:
        # Convert absolute price to percentage relative to current_rate
            return (stoploss_price / current_rate) - 1

        return 1 # return a value bigger than the initial stoploss to keep using the initial stoploss

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float, min_stake: float, max_stake: float, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        stop_price = last_candle['lowest']
        volume_for_buy = self.max_loss_per_trade / (current_rate - stop_price)
        use_money = volume_for_buy * current_rate

        return use_money

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def get_ticker_indicator(self):
        return int(self.timeframe[:-1])

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

        # EMA - Exponential Moving Average Short
        fastMA_short = ta.EMA(dataframe, timeperiod=12)
        slowMA_short = ta.EMA(dataframe, timeperiod=26)
        dataframe['fastMA'] = fastMA_short
        dataframe['slowMA'] = slowMA_short

        # :param dataframe: dataframe containing close/high/low/open/volume
        # :param interval: to which ticker value in minutes would you like to resample it
        dataframe_long = resample_to_interval(dataframe, self.get_ticker_indicator() * self.long_period)

        # EMA - Exponential Moving Average Long
        fastEMA_long = ta.EMA(dataframe_long, timeperiod=12)
        slowEMA_long = ta.EMA(dataframe_long, timeperiod=26)
        dataframe_long['fastMA'] = fastEMA_long
        dataframe_long['slowMA'] = slowEMA_long

        dataframe = resampled_merge(dataframe, dataframe_long)
        dataframe.fillna(method='ffill', inplace=True)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """

        dataframe.loc[
            (
                (dataframe['resample_{}_fastMA'.format(self.get_ticker_indicator() * self.long_period)] > dataframe['resample_{}_slowMA'.format(self.get_ticker_indicator() * self.long_period)]) & 
                (dataframe['resample_{}_close'.format(self.get_ticker_indicator() * self.long_period)] > dataframe['resample_{}_fastMA'.format(self.get_ticker_indicator() * self.long_period)] ) &
                (dataframe['fastMA'] > dataframe['slowMA']) &  
                (dataframe['close'] > dataframe['fastMA'] ) &
                (dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with sell column
        """
        dataframe.loc[
            (
                (dataframe['resample_{}_fastMA'.format(self.get_ticker_indicator() * self.long_period)] < dataframe['resample_{}_slowMA'.format(self.get_ticker_indicator() * self.long_period)]) & 
                (dataframe['resample_{}_close'.format(self.get_ticker_indicator() * self.long_period)] < dataframe['resample_{}_fastMA'.format(self.get_ticker_indicator() * self.long_period)] ) &
                (dataframe['fastMA'] < dataframe['slowMA']) &  
                (dataframe['close'] < dataframe['fastMA'] ) &
                (dataframe['volume'] > 0)  # Make sure Volume is not 0
            ),
            'sell'] = 1
        return dataframe
    
    

