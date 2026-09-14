from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from config import settings
import utils as ut
import logging
logger = logging.getLogger(__name__)

Base = declarative_base()

class AnomalyLog(Base):
    __tablename__ = "anomaly_log"

    index = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    asset_id = Column(String(50), nullable=False, index=True)

    anomaly_class = Column(String(20), nullable=False)
    telemetry = Column(Text, nullable=False)        # JSON-stringified telemetry dict
    severity_bands = Column(Text, nullable=False)   # JSON-stringified severity_bands dict
    failure = Column(Text, nullable=False)
    action_taken = Column(Text, nullable=False)


def init_ltm_db(force_reset:bool = False):
    """
    init and Create a new LTM SQLite database
    Args:
        - force_reset: if True, reset existing dB and then init/setup, otherwise no action is taken
    Returns:
        None
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        ut.init_and_setup_db(settings.LTM_DIR / settings.LTM_DB, Base, force_reset)
    except Exception as e:
        logger.error(f"Error in init_ltm_db: {e}")
        raise


if __name__ == "__main__":
    init_ltm_db(force_reset=True)

