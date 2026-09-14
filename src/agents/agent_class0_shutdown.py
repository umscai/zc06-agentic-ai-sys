
from langchain_core.runnables import RunnableConfig
from agents.agent_common import AgentState
import logging
logger = logging.getLogger(__name__)

def class0_shutdown_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph Node responsible for Class-1 anomaly (shutdown procedure)
    Args:
        state (AgentState): Current state of the workflow graph.
        config (RunnableConfig): Runtime configuration (e.g., configurable LLM instance).
    Returns:
        AgentState: Partial state update dict for LangGraph.
    """
    try:
        action_taken = (
                f"System is SHUTDOWN with standard procedures.\n"
                f"All parties are informed including standard guidelines and procedures."
            )
        logger.info(f"shutdown procedure is activated")
        logger.debug(f"XXX shutdown procedure is activated: action taken={action_taken}")
        return {'action_taken': action_taken}
    except Exception as e:
        logger.error(f"Error in class0_shutdown_node: {str(e)}")
        action_taken = (
            f"Encounter some internal error\n"
            f"No action is taken, wait for next evaluation."
        )
        return {'action_taken': action_taken, "error":  str(e)}
