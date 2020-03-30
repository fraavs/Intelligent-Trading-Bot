import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Union
import json
import pickle

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn import metrics
from sklearn.model_selection import ParameterGrid

from trade.utils import *

"""
In fact, it training a hyper-model while the model itself is not trained - it is a rule-based model.
Find best signal generation models using pre-computed (rolling) predict label scores and searching through the threshold grid.
The output is an ordered list of best performing threshold-based signal generation models.
"""

grid_signals = [
    # Production
    {
        'threshold_buy_10': [0.20, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29, 0.30, 0.31, 0.32, 0.33, 0.34, 0.35],
        'threshold_buy_20': [0.06, 0.065, 0.07, 0.075, 0.08],
        'percentage_sell_price': [1.016, 1.017, 1.018, 1.019],
        'sell_timeout': [65, 70, 75],
    },
    # Debug
    #{
    #    'threshold_buy_10': [0.2, 0.2, 0.2, 0.2, 0.2],
    #    'threshold_buy_20': [0.0],
    #    'percentage_sell_price': [1.015, 1.020],
    #    'sell_timeout': [60],
    #},
]

#
# Parameters
#
class P:
    in_path_name = r"_TEMP_FEATURES"
    in_file_name = r"_BTCUSDT-1m-rolling-predictions.csv"
    in_nrows = 100_000_000

    out_path_name = r"_TEMP_FEATURES"
    out_file_name = r"_BTCUSDT-1m-signal-models"

    simulation_start = 100  # Default 0
    simulation_end = -100  # Default till end of input data. Negative value is shift from the end

    #
    # Parameters of the whole optimization
    #
    performance_weight = 12.0  # Per year. 1.0 means all are equal, 3.0 means last has 3 times more weight than first

def main(args=None):

    start_dt = datetime.now()

    #
    # Load data with rolling label score predictions
    #
    print(f"Loading data with label rolling predict scores from input file...")

    in_path = Path(P.in_path_name).joinpath(P.in_file_name)
    if not in_path.exists():
        print(f"ERROR: Input file does not exist: {in_path}")
        return

    if P.in_file_name.endswith(".csv"):
        in_df = pd.read_csv(in_path, parse_dates=['timestamp'], nrows=P.in_nrows)
    elif P.in_file_name.endswith(".parq"):
        in_df = pd.read_parquet(in_path)
    else:
        print(f"ERROR: Unknown input file extension. Only csv and parquet are supported.")

    # Select the necessary interval of data
    if not P.simulation_start:
        P.simulation_start = 0
    if not P.simulation_end:
        P.simulation_end = len(in_df)
    elif P.simulation_end < 0:
        P.simulation_end = len(in_df) + P.simulation_end

    in_df = in_df.iloc[P.simulation_start:P.simulation_end]

    #
    # Loop on all trade hyper-models - one model is one trade (threshold-based) strategy
    #
    grid = ParameterGrid(grid_signals)
    models = list(grid)  # List of model dicts
    performances = []

    for i, model in enumerate(models):
        # Set parameters of the model

        start_dt = datetime.now()
        performance = simulate_trade(in_df, model, P.performance_weight)
        elapsed = datetime.now() - start_dt
        print(f"Finished simulation {i} / {len(models)} in {elapsed.total_seconds():.1f} seconds.")

        performances.append(performance)

    #
    # Post-process: sort and filter
    #

    # Column names
    model_keys = models[0].keys()
    performance_keys = performances[0].keys()
    header_str = ",".join(list(model_keys) + list(performance_keys))

    lines = []
    for i, model in enumerate(models):
        model_values = [f"{v:.3f}" for v in model.values()]
        performance_values = [f"{v:.2f}" for v in performances[i].values()]
        line_str = ",".join(model_values + performance_values)
        lines.append(line_str)

    #
    # Store simulation parameters and performance
    #
    out_path = Path(P.out_path_name)
    out_path.mkdir(parents=True, exist_ok=True)  # Ensure that folder exists
    out_path = out_path.joinpath(P.out_file_name)

    if out_path.with_suffix('.txt').is_file():
        add_header = False
    else:
        add_header = True
    with open(out_path.with_suffix('.txt'), "a+") as f:
        if add_header:
            f.write(header_str + "\n")
        #f.writelines(lines)
        f.write("\n".join(lines))
        f.write("\n")

    pass

def simulate_trade(df, model: dict, performance_weight: float):
    """
    It will use 1.0 as initial trade amount and overall performance will be the end amount with respect to the initial one.
    It will always use 1.0 to enter market (for buying) independent of the available (earned or lost) funds.
    It will use the whole data set from start to end.

    :param df:
    :param model:
        threshold_buy_10 - Buy only if score is higher
        threshold_buy_20 - Buy only if score is higher
        percentage_sell_price - how much increase sell price in comparision to buy price (it is our planned profit)
        sell_timeout - Sell using latest close price after this time
    :param performance_weight: weight for the last time point for the 1 year period. for the first point it is 1.0
    :return: Performance record
    """
    #
    # Model parameters
    #
    threshold_buy_10 = float(model.get("threshold_buy_10"))
    threshold_buy_20 = float(model.get("threshold_buy_20"))

    percentage_sell_price = float(model.get("percentage_sell_price"))
    sell_timeout = int(model.get("sell_timeout"))

    # All transactions will be collected in this list for later analysis
    transactions = []  # List of dicts like dict(i=23, is_forced_sell=False, profit=-0.123)

    total_buy_signal_count = 0  # How many rows satisfy buy signal criteria independent of mode


    # Selecting only needed rows increases performance by several times (~4 times)
    df = df[["high", "close", "high_60_10_gb", "high_60_20_gb"]]

    #
    # Main loop over trade sessions
    #
    #
    # Main loop over trade sessions
    #

    i = 0
    for row in df.itertuples(index=True, name="Row"):
        i += 1
        # Object parameters
        close_price = row.close
        high_price = row.high
        # Object parameters (label prediction scores)
        high_60_10_gb = row.high_60_10_gb
        high_60_20_gb = row.high_60_20_gb

        #
        # Apply model parameters and generate a signal for the current row
        #
        if high_60_10_gb >= threshold_buy_10 and high_60_20_gb >= threshold_buy_20:
            is_buy_signal = True
            total_buy_signal_count += 1
        else:
            is_buy_signal = False

        #
        # Determine trade mode
        #
        if not transactions or transactions[-1]["is_filled"]:
            is_buy_mode = True
        else:
            is_buy_mode = False

        if is_buy_mode:  # Buy mode: in cash - trying to buy
            transaction = {}
            if is_buy_signal:
                transaction["buy_time"] = i
                transaction["buy_price"] = close_price
                transaction["sell_price"] = close_price * percentage_sell_price
                transaction["is_filled"] = False

                # Compute weight of this transaction which linearly
                # Weight changes with i from 1.0 to specified parameters, say, from 1.0 to 2.0 at the end if parameter is 2.0
                # f(i)=i * (e-s)/(n-1) + s - [s=f(0),e=f(n-1)]
                # if s=1.0 then f(i)=1.0 + i * (e-1)/(n-1)
                #transaction["weight"] = 1.0 + i * (performance_weight - 1.0) / (len(df)-1)
                # 1 year has 525_600 transactions. if for 525_600, x times more, then for 1 minute x/525_600 times more, and for i minutes i/525_600
                transaction["weight"] = 1.0 + i * (performance_weight-1.0) / 525_600

                transactions.append(transaction)

        else:  # Sell mode: in market - trying to sell
            transaction = transactions[-1]
            if high_price >= transaction["sell_price"]:  # Determine if it was filled for the desired price
                transaction["sell_time"] = i
                transaction["fill_time"] = transaction["sell_time"] - transaction["buy_time"]
                transaction["is_timeout"] = False
                transaction["profit"] = transaction["sell_price"] - transaction["buy_price"]
                transaction["has_profit"] = True
                transaction["is_filled"] = True
            elif (i - transaction["buy_time"]) > sell_timeout:  # Sell time out. Forced sell
                transaction["sell_price"] = close_price
                transaction["sell_time"] = i
                transaction["fill_time"] = transaction["sell_time"] - transaction["buy_time"]
                transaction["is_timeout"] = True
                transaction["profit"] = transaction["sell_price"] - transaction["buy_price"]
                transaction["has_profit"] = False if transaction["profit"] <= 0.0 else True
                transaction["is_filled"] = True

    if not transactions:
        return {}

    #
    # Remove last transaction if not filled
    #
    transaction = transactions[-1]
    if not transaction["is_filled"]:
        del transactions[-1]

    #
    # Compute performance parameters from the list of transactions
    #

    # total_buy_signal_count
    t_count = len(transactions)  # No transactions - we need no transactions relative to time, that is, transaction frequency, say, per day or month

    # Frequency of transactions
    no_months = len(df) / 43_920
    t_per_month = t_count / no_months

    # All absolute
    profit_per_transaction = np.sum([t["profit"] for t in transactions]) / t_count
    profit_per_month = profit_per_transaction * t_per_month

    # All weighted
    sum_of_weights = np.sum([t["weight"] for t in transactions])
    sum_of_weighted_profits = np.sum([t["weight"]*t["profit"] for t in transactions])
    weighted_profit_per_transaction = sum_of_weighted_profits / sum_of_weights
    weighted_profit_per_month = weighted_profit_per_transaction * t_per_month  # TODO: Not sure that this is correct

    # Limit (profitable) transactions
    t_limit_percentage = len([t for t in transactions if not t["is_timeout"]]) * 100.0 / t_count
    limit_fill_times = [t["fill_time"] for t in transactions if not t["is_timeout"]]
    limit_fill_time = np.mean(limit_fill_times)  # Average fill time for limit transactions
    limit_fill_time_std = np.std(limit_fill_times)  # Deviation fill time for limit transactions

    # Timeout transactions
    t_timeout_percentage = len([t for t in transactions if t["is_timeout"]]) * 100.0 / t_count

    # Loss transactions
    t_loss_percentage = len([t for t in transactions if not t["has_profit"]]) * 100.0 / t_count
    loss_per_transaction = np.sum([t["profit"] for t in transactions if not t["has_profit"]]) / t_count
    loss_per_month = loss_per_transaction * t_per_month

    performance = dict(
        t_per_month=t_per_month,

        profit_per_transaction=profit_per_transaction,
        profit_per_month=profit_per_month,

        weighted_profit_per_transaction=weighted_profit_per_transaction,
        weighted_profit_per_month=weighted_profit_per_month,

        t_limit_percentage=t_limit_percentage,
        limit_fill_time=limit_fill_time,
        limit_fill_time_std=limit_fill_time_std,

        t_timeout_percentage=t_timeout_percentage,

        t_loss_percentage=t_loss_percentage,
        loss_per_transaction=loss_per_transaction,
        loss_per_month=loss_per_month,
    )

    return performance


if __name__ == '__main__':
    main(sys.argv[1:])
