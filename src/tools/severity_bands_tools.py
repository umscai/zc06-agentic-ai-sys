from pathlib import Path
from config import settings
import utils as ut
import pandas as pd
import numpy as np
from langchain_core.tools import tool
import logging
logger = logging.getLogger(__name__)

#----------------------------------------------------------------------------------------
@tool
def get_severity_bands(telemetry: dict[str, float], asset_id:int=1)-> dict[str,str]:
    """
    Classifies telemetry values into categories compared to Normal Range of operation as:
    Critically_Low, Low, Normal, High, and Critically_High
    Args:
        - telemetry: dict of telemetry (key, value)
        - asset_id: asset id to get info on normal operational ranges and ...
    Return:
        Dictionary mapping each parameter name to its category label
    """
    try:
        df_anomaly_range = ut.get_asset_test_case(asset_index=asset_id, test_case_index=1)
        #['parameter', 'low_min', 'normal_min', 'normal_max', 'high_max', 'start', 'end']

        parameters = settings.TELEMETRY_PARAM_LIST #["temperature_c", "vibration_hz", "pressure_psi", "power_kw"]
        severity_bands = {}

        # Map raw numeric values to level labels
        for param in parameters:
            val = telemetry.get(param)
            if val is None:
                raise ValueError(f"Missing parameter '{param}' in input values.")

            param_row = df_anomaly_range[df_anomaly_range["parameter"] == param]
            if param_row.empty:
                raise ValueError(f"Parameter '{param}' not found in anomaly range config.")

            row = param_row.iloc[0]

            if val <= row["low_min"]:
                severity_bands[param] = "Critically_Low"
            elif row["low_min"] < val < row["normal_min"]:
                severity_bands[param] = "Low"
            elif row["normal_min"] <= val <= row["normal_max"]:
                severity_bands[param] = "Normal"
            elif row["normal_max"] < val < row["high_max"]:
                severity_bands[param] = "High"
            elif row["high_max"] <= val:
                severity_bands[param] = "Critically_High"
            else: # should not happen!
                severity_bands[param] = "Out_of_Range"

        return severity_bands
    except Exception as e:
        logger.error(f"Error in get_severity_bands: {e}")
        # On exception we set all to Low, to go for logging and next sample analysis (no interruption for agent workflow)
        return{
            'temperature_c':'Low',
            'vibration_hz': 'Low',
            'pressure_psi': 'Low',
            'power_kw': 'Low',
        }


#----------------------------------------------------------------------------------------
def get_telemetry_normal_range(telemetry_name: str, asset_id:int=1)-> tuple[float|None,float|None]:
    """
    get normal operation range for the telemetry
    Args:
        - telemetry: telemetry_name
        - asset_id: asset id to get info on normal operational ranges and ...
    Return:
        (normal_min, normal_max) of the telemetry, or None in case of error, where Agent use 10% steps to decrease/increase
    """
    try:
        normal_min, normal_max = None, None
        df_anomaly_range = ut.get_asset_test_case(asset_index=asset_id, test_case_index=1)
        #['parameter', 'low_min', 'normal_min', 'normal_max', 'high_max', 'start', 'end']

        parameters = settings.TELEMETRY_PARAM_LIST #["temperature_c", "vibration_hz", "pressure_psi", "power_kw"]
        if telemetry_name in parameters:
            param_row = df_anomaly_range[df_anomaly_range["parameter"] == telemetry_name]
            if not param_row.empty:
                row = param_row.iloc[0]
                normal_min = row["normal_min"]
                normal_max = row["normal_max"]
        return normal_min, normal_max
    except Exception as e:
        logger.error(f"Error in get_telemetry_normal_range: {e}")
        return None, None # Agent use 10% increase/decrease step



