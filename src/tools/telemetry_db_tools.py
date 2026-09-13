# telemetry_db_tools.py
from typing import Dict
from sqlalchemy import create_engine
from db_model.telemetry_model import TelemetryLog
from config import settings
from utils import get_session
import pandas as pd
import logging

logger = logging.getLogger(__name__)

engine = create_engine(
    f"sqlite:///{settings.TELEMETRY_DIR / settings.TELEMETRY_DB}",
    echo=False,                                # Keep False for clean logs in production
    connect_args={"check_same_thread": False}  # Prevents thread errors in LangGraph workers
)

#----------------------------------------------------------------------------------------
def log_telemetry(
    asset_id: str,
    telemetry: Dict[str, float],
    is_anomaly: bool,
) -> tuple[int, str]:
    """
    Logs raw telemetry features and anomaly metrics into SQLite database.
    Args:
        - asset_id: asset (equipment/device) ID
        - telemetry: telemetry-name and value in dict format
        - is_anomaly: True if detected as anomaly otherwise  False
    Returns:
        The auto-incremented index of the inserted row, and string version of timestamp up to sec
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        with get_session(engine) as session:
            new_entry = TelemetryLog(
                asset_id=asset_id,
                temperature_c=telemetry.get("temperature_c", 0.0),
                vibration_hz=telemetry.get("vibration_hz", 0.0),
                pressure_psi=telemetry.get("pressure_psi", 0.0),
                power_kw=telemetry.get("power_kw", 0.0),
                is_anomaly=is_anomaly
            )
            session.add(new_entry)
            session.flush()  # Populates new_entry.index prior to commit
            timestamp_str = new_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            return new_entry.index, timestamp_str
    except Exception as e:
        logger.error(f"Error in log_telemetry for asset {asset_id}: {e}")
        raise

#----------------------------------------------------------------------------------------
def get_telemetry_df()->pd.DataFrame:
    """
    get telemetry data in data-frame format
    Args:
        - None
    Returns:
        pandas dataframe contains telemetry log
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        table_name = TelemetryLog.__tablename__ #Direct Attribute Access
        #[NOTE] we can also use metadata: table_name = TelemetryLog.__table__.name
        df = pd.read_sql_table(table_name, engine)
        return df
    except Exception as e:
        logger.error(f"Error in get_telemetry_df: {e}")
        raise
















# # telemetry_db_tools.py
# from typing import Dict
# #from ts_model import SessionLocal, TelemetryLog, init_db
# from sqlalchemy import create_engine
# from db_model.telemetry_model import TelemetryLog
# from config import settings
# from utils import get_session
# import logging
# logger = logging.getLogger(__name__)

# # Ensure tables exist upon module import
# #init_db()

# engine = create_engine(f"sqlite:///{settings.TELEMETRY_DIR/settings.TELEMETRY_DB}")

# def log_telemetry(
#     asset_id: str,
#     telemetry: Dict[str, float],
#     is_anomaly: bool,
#     anomaly_case_num: int
# ) -> int:
#     """
#     Logs raw telemetry features and anomaly metrics into SQLite database.
#      Args:
#         asset_id: The id of the asset (equipment/device)
#         telemetry, dict of telemetry and their values
#         is_anomaly: True if anomaly detected (otherwise False)
#         anomaly_case_num: anomaly case number for pre-defined/known anomaly pattern/case
#     Returns
#         The auto-incremented index of the inserted row.
#     Raises:
#         Exception: Re-raises any exception caught during processing after logging.
#     """
#     try:
#         with get_session(engine) as session:
#             new_entry = TelemetryLog(
#                 asset_id=asset_id,
#                 temperature_c=telemetry.get("temperature_c", 0.0),
#                 vibration_hz=telemetry.get("vibration_hz", 0.0),
#                 pressure_psi=telemetry.get("pressure_psi", 0.0),
#                 power_kw=telemetry.get("power_kw", 0.0),
#                 is_anomaly=is_anomaly,
#                 anomaly_case_num=anomaly_case_num
#             )
#             session.add(new_entry)
#     except Exception as e:
#             logger.error(f"Error in get_severity_bands_df: {e}")
#             raise





# from sqlalchemy import create_engine
# from utils import get_session, LTM_DB_PATH, LOGGER_NAME
# from data.models.ltm import UserInteraction
# import uuid
# from typing import List, Optional, Literal
# from langchain_core.tools import tool
# from .schemas import UserInteractionRead
# import logging
# logger = logging.getLogger(LOGGER_NAME)

# # Create the engine using your absolute path
# # sqlite:/// followed by a / for absolute paths results in 4 slashes total
# engine = create_engine(f"sqlite:///{LTM_DB_PATH}")

# #SentimentType = Literal["happy", "satisfied", "enthusiastic", "neutral", "frustrated", "upset", "angry"]

# def write_user_interaction(user_id: str, query: str, response: str, sentiment: str):
#     """
#     Writes a new user interaction to the LTM database.
#     Args:
#         user_id(str): user id used in external dB as user identifier
#         query(str): user query during interaction
#         response(str): system response to user query
#         sentiment: user sentiment during the interaction
#     """
#     try:
#         with get_session(engine) as session:
#             new_entry = UserInteraction(
#                 user_id=user_id,
#                 query=query,
#                 response=response,
#                 sentiment=sentiment #
#             )
#             session.add(new_entry)
#     except Exception as e:
#         logger.error(f"Error in write_user_interaction: {str(e)}")


# # ts_db_tools.py
# import json
# from typing import Dict, Any
# from ts_model import SessionLocal, TelemetryLog, init_db

# # Ensure tables are created on import
# init_db()

# def log_telemetry(
#     asset_id: str,
#     telemetry: Dict[str, float],
#     z_scores: Dict[str, float],
#     severity_bands: Dict[str, str],
#     anomaly_case: int,
#     is_anomaly: bool
# ) -> int:
#     """
#     Logs telemetry payload, calculated z-scores, and severity bands into SQLite database.
#     Returns the inserted log record ID.
#     """
#     db = SessionLocal()
#     try:
#         log_entry = TelemetryLog(
#             asset_id=asset_id,
#             telemetry_json=json.dumps(telemetry),
#             z_scores_json=json.dumps(z_scores),
#             severity_bands_json=json.dumps(severity_bands),
#             anomaly_case=anomaly_case,
#             is_anomaly=is_anomaly
#         )
#         db.add(log_entry)
#         db.commit()
#         db.refresh(log_entry)
#         return log_entry.id
#     except Exception as e:
#         db.rollback()
#         raise e
#     finally:
#         db.close()