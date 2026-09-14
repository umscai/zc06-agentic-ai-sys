

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



# def update_memory_node(state: AgentState, config: RunnableConfig) -> AgentState:
#     """
#     This LangGraph Node responsible for Updating LTM with current user interaction

#     Args:
#         state(AgentState): current state of the LangGraph/Workflow graph
#         config(RunnableConfig): Runtime configuration for the runnable (e.g. thread_id)

#     Returns:
#         AgentState: The updated graph state
#     """
#     try:
#         write_user_interaction(
#             user_id=state["ext_user_id"],
#             query= state["user_query"],
#             response=state["response"],
#             sentiment= state["sentiment"])

#         # also update ticket-metadata status as resolved or pending_human
#         ticket_metadata_status='pending_human' if state.get("current_tier","L1") == "Human" else 'resolved'
#         upsert_ticket_metadata(
#             ticket_id=state["ticket_id"],
#             status=ticket_metadata_status
#         )
#         logger.info(f"Update LTM")

#         return{
#             "next_node": "end",
#             "error": None
#         }
#     except Exception as e:
#         logger.error(f"Error in update_memory_node: {str(e)}")
#         return{
#             "next_node": "end",
#             "error": str(e)
#         }