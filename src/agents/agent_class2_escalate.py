from langchain_core.runnables import RunnableConfig
from agents.agent_common import AgentState
import logging
logger = logging.getLogger(__name__)


def class2_escalate_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph Node responsible for Class-2 Anomaly (escalate)
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

        action_taken = (
            f"High Priority Task for On-Site Field Reliability Engineering: \n"
            f"Class-2 Anomaly detected on Asset-{asset_id} at: {telemetry_timestamp_str}\n"
            f"Telemetry: {telemetry}\n"
            f"severity_bands: {severity_bands}\n"
            f"primary_failure_mode: {primary_failure_mode}\n"
            f"root_cause_analysis: {root_cause_analysis}\n"
            f"suggested action: {action}\n"
            f"Please follow standard guideline, and procedure for inspection, and repair/fix"
        )
        logger.info(f"Escalate to on-site engineer is activated")
        return {'action_taken': action_taken}
    except Exception as e:
        logger.error(f"Error in class2_escalate_node: {str(e)}")
        action_taken = (
            f"Encounter some internal error\n"
            f"No action is taken, wait for next evaluation."
        )
        return {'action_taken': action_taken, "error":  str(e)}
