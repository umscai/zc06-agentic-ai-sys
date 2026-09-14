from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from config import settings
import utils as ut
import logging
logger = logging.getLogger(__name__)

Base = declarative_base()

class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    index = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    asset_id = Column(String(50), nullable=False, index=True)

    temperature_c = Column(Float, nullable=False)
    vibration_hz = Column(Float, nullable=False)
    pressure_psi = Column(Float, nullable=False)
    power_kw = Column(Float, nullable=False)

    is_anomaly = Column(Boolean, nullable=False, default=False)



def init_telemetry_db(force_reset:bool = False):
    """
    init and Create a new TELEMETRY SQLite database
    Args:
        - force_reset: if True, reset existing dB and then init/setup, otherwise no action is taken
    Returns:
        None
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        ut.init_and_setup_db(settings.TELEMETRY_DIR / settings.TELEMETRY_DB, Base, force_reset)
    except Exception as e:
        logger.error(f"Error in init_telemetry_db: {e}")
        raise


if __name__ == "__main__":
    init_telemetry_db(force_reset=True)
