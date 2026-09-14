# ltm_db_tools.py
import json
import logging
from typing import Dict, List, Any
from sqlalchemy import create_engine
from db_model.ltm_model import AnomalyLog  # Ensure correct import path
from config import settings
from utils import get_session
import pandas as pd

logger = logging.getLogger(__name__)

engine = create_engine(
    f"sqlite:///{settings.LTM_DIR / settings.LTM_DB}",
    echo=False,                                # Keep False for clean logs in production
    connect_args={"check_same_thread": False}  # Prevents thread errors in LangGraph workers
)


def log_anomaly(
    asset_id: str,
    anomaly_class: str,
    telemetry: Dict[str, float],
    severity_bands: Dict[str, str],
    failure: str,
    action_taken: str,
) -> int:
    """
    Logs anomaly information into the LTM SQLite database.

    Args:
        asset_id: Unique asset (equipment/device) ID.
        anomaly_class: Classification string ("CLASS_0", "CLASS_1", "CLASS_2").
        telemetry: Dict of telemetry values.
        severity_bands: Dict of severity classifications per parameter.
        failure: Description of primary failure mode or diagnosis.
        action_taken: Summary of automated control or field action taken.

    Returns:
        The auto-incremented index of the inserted row.
    """
    try:
        with get_session(engine) as session:
            new_entry = AnomalyLog(
                asset_id=str(asset_id),
                anomaly_class=anomaly_class,
                telemetry=json.dumps(telemetry),
                severity_bands=json.dumps(severity_bands),
                failure=failure,
                action_taken=str(action_taken),
            )
            session.add(new_entry)
            session.flush()  # Populates new_entry.index prior to commit
            return new_entry.index
    except Exception as e:
        logger.error(f"Error in log_anomaly for asset {asset_id}: {e}")
        raise


def get_anomaly_history(asset_id: str, k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves the last k anomaly records for a specific asset ordered by most recent first.

    Args:
        asset_id: Target asset identifier.
        k: Maximum number of recent anomalies to retrieve (default: 3).

    Returns:
        List of dictionaries with deserialized telemetry and severity_bands.
    """
    try:
        with get_session(engine) as session:
            records = (
                session.query(AnomalyLog)
                .filter(AnomalyLog.asset_id == str(asset_id))
                .order_by(AnomalyLog.timestamp.desc())
                .limit(k)
                .all()
            )

            history = []
            for record in records:
                history.append({
                    "index": record.index,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                    "asset_id": record.asset_id,
                    "anomaly_class": record.anomaly_class,
                    "telemetry": json.loads(record.telemetry) if record.telemetry else {},
                    "severity_bands": json.loads(record.severity_bands) if record.severity_bands else {},
                    "failure": record.failure,
                    "action_taken": record.action_taken,
                })
            return history
    except Exception as e:
        logger.error(f"Error retrieving anomaly history for asset {asset_id}: {e}")
        return []


def format_anomaly_context(history: List[Dict[str, Any]]) -> str:
    """Formats a list of anomaly records into a clean context block for prompt templates."""
    if not history:
        return "No recent anomaly history recorded for this asset."

    formatted_records = []
    ## We reverse them to get [Oldest, Middle, Newest] for the LLM prompt
    for idx, rec in enumerate(reversed(history), 1):
        record_str = (
            f"[{idx}] Timestamp: {rec.get('timestamp')}\n"
            f"    - Telemetry: {rec.get('telemetry')}\n"
            f"    - Severity Bands: {rec.get('severity_bands')}\n"
            f"    - Anomaly Class: {rec.get('anomaly_class')}\n"
            f"    - Failure Mode: {rec.get('failure')}\n"
            f"    - Action Taken: {rec.get('action_taken')}"
        )
        formatted_records.append(record_str)

    return "\n\n".join(formatted_records)

#----------------------------------------------------------------------------------------
def get_ltm_df()->pd.DataFrame:
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
        table_name = AnomalyLog.__tablename__ #Direct Attribute Access
        #[NOTE] we can also use metadata: table_name = AnomalyLog.__table__.name
        df = pd.read_sql_table(table_name, engine)
        return df
    except Exception as e:
        logger.error(f"Error in get_ltm_df: {e}")
        raise

