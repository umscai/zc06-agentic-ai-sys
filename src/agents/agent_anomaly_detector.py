
from langchain_core.runnables import RunnableConfig
from config import settings
from agents.agent_common import AgentState
from tools.telemetry_db_tools import log_telemetry
from tools.anomaly_detector_tool import detect_anomaly
import logging
logger = logging.getLogger(__name__)

#----------------------------------------------------------------------------------------
def detect_anomaly_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    This LangGraph Node responsible for processing incoming telemetry to check
    if they are in normal operation range, or not, based on zscore, by using detect_anomaly tool
    also save the telemetry data into telemetry database using log_telemetry tool
    and finally update the state for proper routing
    Args:
        state(AgentState): current state of the LangGraph/Workflow graph
        config(RunnableConfig): Runtime configuration for the runnable (e.g. thread_id)
    Returns:
        AgentState: The updated graph state
    """
    try:
        asset_id = state.get("asset_id", 1)
        telemetry = state.get("telemetry", {})
        if telemetry:
            # Compute Z-Scores and statistical anomaly boolean
            z_scores, is_anomaly = detect_anomaly(telemetry, asset_id)

            # log telemetry data into dB
            log_id, timestamp_str = log_telemetry(
                asset_id=asset_id,
                telemetry=telemetry,
                is_anomaly=is_anomaly
            )

            # 4. Prepare updated state dict, and init all fields
            updates = {
                #"asset_id": asset_id,
                #"telemetry": telemetry
                "telemetry_timestamp_str": timestamp_str,
                "z_scores": z_scores,
                "severity_bands": {},
                "is_anomaly": is_anomaly,
                "context":"",
                "classification_class": None,
                "confidence": None,
                "primary_failure_mode": None,
                "root_cause_analysis": None,
                "action": None,
                "VFD": None,
                "root_cause_analysis"
                "response": "", # update below
                "tool_used":[], #TODO should we update with tools used by this node, even if it was not LLM that used the tool
                "error": None
            }
            # Here there is no user-message, ai-message or system-message that need to be added to messages
            # if needed we can do updates["messages"] = [{"role": "system", "content": "A message"}]
            if not is_anomaly:
                updates["response"]=f'{timestamp_str}: No Anomaly detected.'
            else:
                updates["response"]=f"{timestamp_str}: Anomaly detected!."
            logger.info(f"is_anomaly={is_anomaly}")
        else:
            logger.debug("Empty telemetry detected in detect_anomaly_node")
            updates = {
                #"asset_id": asset_id,
                #"telemetry": telemetry
                "telemetry_timestamp_str":"",
                "z_scores": {},
                "severity_bands": {},
                "is_anomaly": False,
                "context":"",
                "classification_class": None,
                "confidence": None,
                "primary_failure_mode": None,
                "root_cause_analysis": None,
                "action": None,
                "VFD": None,
                "response": "",
                "tool_used":[],
                "error": None
            }
        return updates
    except Exception as e:
        logger.error(f"Error in detect_anomaly_node: {str(e)}")
        updates = {
            #"asset_id": asset_id,
            #"telemetry": telemetry
            "telemetry_timestamp_str":"",
            "z_scores": {},
            "severity_bands": {},
            "is_anomaly": False,
            "context":"",
            "classification_class": None,
            "confidence": None,
            "primary_failure_mode": None,
            "root_cause_analysis": None,
            "action": None,
            "VFD": None,
            "response": "",
            "tool_used":[],
            "error":  str(e)
        }
        return updates