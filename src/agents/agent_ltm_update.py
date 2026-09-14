

from langchain_core.runnables import RunnableConfig
from agents.agent_common import AgentState
from tools.ltm_db_tools import log_anomaly
import logging
logger = logging.getLogger(__name__)


def ltm_update_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph Node responsible for logging anomaly information into Long-Term-Memory (LTM)
    Args:
        state (AgentState): Current state of the workflow graph.
        config (RunnableConfig): Runtime configuration (e.g., configurable LLM instance).
    Returns:
        AgentState: Partial state update dict for LangGraph.
    """
    try:
        telemetry_timestamp_str= state.get('telemetry_timestamp_str', '')
        telemetry = state.get("telemetry", {})
        severity_bands = state.get("severity_bands", {})
        asset_id = state.get("asset_id", 0)
        primary_failure_mode = state.get('primary_failure_mode', 'Unknown')
        root_cause_analysis= state.get('root_cause_analysis', 'Unknown')
        action = state.get('action', 'Full system check')
        classification_class = state.get('classification_class', 'Unknown')
        action_taken = state.get('action_taken', 'Unknown')


        log_id= log_anomaly(
            asset_id = asset_id,
            anomaly_class= classification_class,
            telemetry = telemetry,
            severity_bands = severity_bands,
            failure = primary_failure_mode,
            action_taken = action_taken
        )
        final_response = (
            f"Asset: Pump-{asset_id}, {classification_class}-Anomaly detected at {telemetry_timestamp_str}\n"
            f"Telemetry: {telemetry}\n"
            f"Severity Bands: {severity_bands}\n"
            f"Failure: {primary_failure_mode}\n"
            f"Root Cause: {root_cause_analysis}\n"
            f"Suggested Action: {action}\n"
            f"Action Taken: {action_taken}"
        )

        return {'response': final_response}
    except Exception as e:
        logger.error(f"Error in ltm_update_node: {str(e)}")
        return {'response': 'Internal Error', "error":  str(e)}
