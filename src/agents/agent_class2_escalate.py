from langchain_core.runnables import RunnableConfig
from agents.agent_common import AgentState


def class2_escalate_node(state: AgentState, config: RunnableConfig) -> AgentState:
    return state
