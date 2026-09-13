from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from config import settings
import utils as ut

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

# Sample Run
# max@m223:~/x/zc06-agentic-ai$ uv run python -m src.db_model.telemetry_model
# Existing database at /home/max/x/zc06-agentic-ai/out/db_telemetry/telemetry.db removed.
# Database and tables created successfully.
# Detected tables in /home/max/x/zc06-agentic-ai/out/db_telemetry/telemetry.db: ['telemetry_logs']
# max@m223:~/x/zc06-agentic-ai$
if __name__ == "__main__":
    # Pass the Base containing TelemetryLog metadata
    ut.reset_and_setup_db(settings.TELEMETRY_DIR / settings.TELEMETRY_DB, Base)

