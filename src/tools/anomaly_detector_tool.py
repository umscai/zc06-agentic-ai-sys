from typing import Dict, Tuple
import pandas as pd
from config import settings
import utils as ut
import logging
logger = logging.getLogger(__name__)

#----------------------------------------------------------------------------------------
def detect_anomaly(telemetry: Dict[str, float], asset_id:int) -> Tuple[Dict[str, float], bool]:
    """
    Calculates z-scores for each telemetry metric using mean (mu) and
    standard deviation (std) from reference dataframe info.
    Args:
        - telemetry: telemetry data in dict format
        - asset_id: asset id/index
    Returns:
        z_scores (Dict[str, float]): Calculated Z-score for each telemetry item.
        is_anomaly (bool): True if any parameter's abs(z-score) exceeds threshold.
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        z_scores = {}
        is_anomaly = False

        df_info = ut.get_asset_test_case(asset_index=asset_id, test_case_index=1)
        INFO_DICT = df_info.set_index("parameter")[["normal_min", "normal_max"]].to_dict(orient="index")

        for param, value in telemetry.items():
            if param in INFO_DICT:
                mu = (INFO_DICT[param]["normal_max"]+INFO_DICT[param]["normal_min"])/2
                std = (INFO_DICT[param]["normal_max"]-INFO_DICT[param]["normal_min"])/settings.NORMAL_Z_SCORE_MAX/2
                z = (value - mu) / std if std != 0 else 0.0
                z_scores[param] = round(float(z), 3)
                if abs(z) > settings.ANOMALY_Z_SCORE_MIN:
                    is_anomaly = True
            else:
                z_scores[param] = 0.0

        return z_scores, is_anomaly
    except Exception as e:
        logger.error(f"Error in detect_anomaly: {e}")
        raise

