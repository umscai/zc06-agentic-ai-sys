"""
This file contains the utility functions used in this project
"""

import os
import random
import math
import datetime
from pathlib import Path
import numpy as np
from numpy.typing import ArrayLike # for type-hint
import pandas as pd
import seaborn as sns
from seaborn.axisgrid import JointGrid # for type-hint
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.axes import Axes # for type-hint
from typing import Optional, List, Dict, Any, Tuple
from config import settings

#
from sqlalchemy import create_engine, Engine, inspect
from sqlalchemy.orm import sessionmaker

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, declarative_base
from contextlib import contextmanager

#
import logging
logger = logging.getLogger(__name__)

def get_asset_test_case(asset_index:int=1, test_case_index:int=1)->pd.DataFrame:
    """
    get configuration of specific asset-index and test-case-index
    Args:
        - asset_index: asset index 1,2,3
        - test_case_index: test-case-index 1,2,3,4
    """
    try:
        df = pd.read_csv(settings.DATA_DIR/settings.ASSET_TEST_CASE_INFO_CSV)
        df1=df[df['asset_index'] == asset_index].copy()
        df1=df1.rename(columns={f'start{test_case_index}':'start', f'end{test_case_index}':'end'})
        return df1[settings.ASSET_TEST_CASE_COL_LIST].copy()
    except Exception as e:
        logger.error(f"Error in get_asset_test_case: {e}")
        raise

#----------------------------------------------------------------------------------------
def generate_test_case_data(
    df: pd.DataFrame,
    num_samples: int = 10,
    trend: str = "sigmoid",  # Options: 'linear', 'sigmoid'
    sigmoid_steepness: float = 6.0,  # Controls transition sharpness (-k to +k range)
    rng: np.random.Generator = settings.RNG,
) -> pd.DataFrame:
    """
    generate telemetry data for the test case with information in df
    Args:
        - df: dataframe contains information about test-case
        - num_samples: number of samples
        - trend: how to increase from start to end , linear or sigmoid like
        - sigmoid_steepness: sigmoid sharpness
        - rng: random number generator (already init with seed, using `new` PCG64 with Better statistical properties & speed)
    Return:
        pandas dataframe with num_samples per column (telemetry parameter)
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        output_df = pd.DataFrame()

        # 3. Generate linear interpolated values with Gaussian jitter for each parameter
        for _, row in df.iterrows():
            param_name = row["parameter"]
            start_val = row["start"]
            end_val = row["end"]
            normal_min = row["normal_min"]
            normal_max = row["normal_max"]

            # Calculate parameter sigma based on normal range and z-score
            param_sigma = (
                normal_max - normal_min
            ) / settings.NORMAL_Z_SCORE_MAX / 2
            jitter_sigma = param_sigma / 5.0

            # Linear trend line from start to end
            #linear_trend = np.linspace(start_val, end_val, num_samples)
            # --- Trend Generation Logic ---
            if trend == "sigmoid":
                # 1. Map samples across an input domain centered at 0
                x = np.linspace(
                    -sigmoid_steepness, sigmoid_steepness, num_samples
                )

                # 2. Standard sigmoid function yielding values from 0.0 to 1.0
                sig = 1 / (1 + np.exp(-x))

                # 3. Scale normalized [0, 1] bounds to fit [0, 1] exactly
                if num_samples >1:
                    sig_normalized = (sig - sig.min()) / (sig.max() - sig.min())
                else:
                    sig_normalized = 1

                # 4. Scale and shift to [start_val, end_val]
                # (If start > end, (end_val - start_val) is negative, smoothly curving down)
                trend_line = start_val + (end_val - start_val) * sig_normalized

            elif trend == "linear":
                trend_line = np.linspace(start_val, end_val, num_samples)

            else:
                raise ValueError(
                    f"Unsupported trend shape: '{trend}'. Supported options: 'linear', 'sigmoid'."
                )

            # Add zero-mean normal jitter
            jitter = rng.normal(loc=0.0, scale=jitter_sigma, size=num_samples)

            output_df[param_name] = trend_line + jitter


        output_df = output_df.round(1)
        return output_df
    except Exception as e:
        logger.error(f"Error in generate_test_case_data: {e}")
        raise

#----------------------------------------------------------------------------------------
def plot_test_case_telemetry(
    data: pd.DataFrame,
    df_config: pd.DataFrame,
    title:str = 'Test Case A',
    test_point:bool=False
) -> None:
    """
    Plots time-series telemetry data with critical threshold lines if limits are breached.

    Args:
        - data : The generated test case samples containing 'datetime' and parameter columns.
        - df_config : Configuration DataFrame containing parameter limits ('parameter', 'low_min', 'high_max').
        - title: figure title
        -test_point: if True include first and last points with legend  test-point
    Returns:
        None
     Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        param_list = settings.TELEMETRY_PARAM_LIST
        fig, axs = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.98)
        colors = sns.color_palette("Set1", n_colors=len(param_list))
        if test_point:
            test_points=data.iloc[[0, -1]]

        for ax, param, color in zip(axs.flatten(), param_list, colors):
            # 1. Plot the main telemetry line
            sns.lineplot(data=data, x=data.index, y=param, ax=ax, color=color, linewidth=2, label=param, marker='s', zorder=2)
            if test_point:
                sns.scatterplot(data=test_points, x=test_points.index, y=param, ax=ax, color='black', label='Test-Point', marker='*', s=200, zorder=3)

            ax.grid(True, linestyle="--", alpha=0.6)
            ax.set_xlabel('Index')
            #ax.legend()

            # 2. Format x-axis datetime labels
            #ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d\n%H:%M:%S"))

            # 3. Lookup parameter threshold limits from config DataFrame
            config_row = df_config[df_config["parameter"] == param]
            if not config_row.empty:
                crit_min = config_row["low_min"].values[0]
                crit_max = config_row["high_max"].values[0]

                n_min = config_row["normal_min"].values[0]
                n_max = config_row["normal_max"].values[0]



                min_val = data[param].min()
                max_val = data[param].max()

                # Plot horizontal threshold lines if limits are exceeded
                # if min_val < crit_min:
                #     ax.axhline(
                #         y=crit_min,
                #         color="crimson",
                #         linestyle="--",
                #         linewidth=1.5,
                #         label=f"Critical Min ({crit_min})",
                #     )
                ax.axhline(y=crit_min, color="crimson", linestyle="--", linewidth=1.5, label=f"Low Min ({crit_min})")
                ax.axhline(y=n_min, color="forestgreen", linestyle="-.", linewidth=1.5, label=f"Normal Min ({n_min})")
                ax.axhline(y=n_max, color="forestgreen", linestyle="-.", linewidth=1.5, label=f"Normal Max ({n_max})")
                ax.axhline(y=crit_max, color="crimson", linestyle="--", linewidth=1.5, label=f"High Max ({crit_max})")

                # if max_val > crit_max or :
                #     ax.axhline(
                #         y=crit_max,
                #         color="crimson",
                #         linestyle="--",
                #         linewidth=1.5,
                #         label=f"Critical Max ({crit_max})",
                #     )
                ax.legend()

        #plt.tight_layout()
        plt.tight_layout(rect=[0, 0, 1, 0.96])
    except Exception as e:
        logger.error(f"Error in plot_test_case_telemetry: {e}")
        raise

#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
@contextmanager
def get_session_old1(engine: Engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except:
        # This catches standard errors (Exception) AND KeyboardInterrupt/SystemExit,
        # if we need logging we may use two similar block with different logging statement
        # one for except Exception: the other the rest as except:
        session.rollback()
        raise
    finally:
        session.close()

#----------------------------------------------------------------------------------------
@contextmanager
def get_session_old2(engine: Engine):
    """Provide a transactional scope around a series of operations."""
    # Use context manager directly on Session
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

#----------------------------------------------------------------------------------------
@contextmanager
def get_session(engine: Engine):
    """Provide a transactional scope around a series of operations."""
    with Session(engine) as session:
        with session.begin(): # Automatically commits on success, rolls back on error
            yield session
        # Session is automatically closed here when exiting the outer 'with'

#----------------------------------------------------------------------------------------
def init_and_setup_db(db_path: Path, base_cls: declarative_base, force_reset:bool=False):
    """
    init and Create a new SQLite database at db_path using the provided Base metadata
    reset before creating if force_reset=True
    Args:
        - db_path: path to dB
        - base_cls: declarative_base of the dB model
        - force_reset: if True, reset existing dB and then init/setup, otherwise no action is taken
    Returns:
        None
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        db_path = Path(db_path)
        if db_path.exists():
            if force_reset:
                db_path.unlink()
                print(f"Existing database at {db_path} removed.")
            else:
                print(f'database already exist at :{db_path} (no action is taken)')
                return
        else:
            print(f'No database at {db_path}, Init and setup for the first time!')

        # Ensure parent folder exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(f"sqlite:///{db_path.resolve()}")

        # Pass the actual Base from the models module
        base_cls.metadata.create_all(engine)
        print("Database and tables created successfully.")

        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        print(f"Detected tables in {db_path}: {table_names}")
    except Exception as e:
        logger.error(f"Error in init_and_setup_db at {db_path} with force_reset={force_reset}: {e}")
        raise

#----------------------------------------------------------------------------------------
def get_val(obj, key):
    """
    A helper function to extract out of type dict or pydantic model
    Args:
        obj: a dict or a pydantic model obj
        key: the key in dict, or field in pydantic model
    """
    if obj is None: return None
    if hasattr(obj, key): return getattr(obj, key)
    if isinstance(obj, dict): return obj.get(key)
    return None


def xxx(args):
    """
    helper function
    Args:
        args:
    Return:
        None
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        pass
    except Exception as e:
        logger.error(f"Error in xxx: {e}")
        raise
