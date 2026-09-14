from typing import TypedDict, Annotated, List, Dict, Any, Tuple, Optional, Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph.message import add_messages # or we could use from langgraph.graph.message import MessagesState
#from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent
import json
from typing import Any
import logging
logger = logging.getLogger(__name__)

# Define allowed severity band values
SeverityBand = Literal["Critically_Low", "Low", "Normal", "High", "Critically_High"]

# Define the state object
class AgentState(TypedDict):
    # LangGraph Message History
    messages: Annotated[list[BaseMessage], add_messages] # or remove this line and use class AgentState(MessagesState):

    # Asset Identifiers
    asset_id: int # device/equipment identifier (for simplicity if str version needed we use str(asset_id))

    # Quantitative Telemetry Data
    # temperature_c: float # Temperature in centigrade
    # vibration_hz: float # Vibration in hertz
    # pressure_psi: float # Pressure in pounds per square inch (psi)
    # power_kw: float # Power in kilo-watt
    telemetry: Dict[str, float] # {'temperature_c': val, 'vibration_hz': val, 'pressure_psi': val, 'power_kw': val}
    telemetry_timestamp_str:str # telemetry timestamp when it logged to dB
    z_scores: Dict[str, float] # {'temperature_c': val, 'vibration_hz': val, 'pressure_psi': val, 'power_kw': val}

    # Qualitative / Semantic Interpretation (Answer to Q1)
    severity_bands: Dict[str, SeverityBand]  # {'temperature_c': 'VH', ...}

    #
    is_anomaly: bool # True if anomaly detected otherwise False

    #agentic workflow related info
    #LTM(Long-Term Memory)-related info
    context: str # Long-Term Memory

    # Classification & Diagnostics,(routing info)
    classification_class: Optional[Literal["CLASS_0", "CLASS_1", "CLASS_2"]]
    confidence: Optional[float]
    primary_failure_mode: Optional[str]
    root_cause_analysis: Optional[str]
    action:Optional[str] # the action for agents at class-0, class-1, or class-2
    VFD:Optional[Literal[-1,0,1]] # VFD = Variable Frequency Drive mainly used by CLASS_1


    # Action Tracking & Control Execution
    action_taken:str # reported action taken by agents at class-0, class-1, or class-2
    response:str # final response
    tool_used: List[str] | None

    #
    error: str | None # in case of node error


def invoke_react_agent(response_schema: type[BaseModel], messages: List[BaseMessage], llm, tools) -> Tuple[Dict[str, Any], List[str]]:
    """
    Create react agent based on the given models, and output schema with tools, and return both results and tool_used
    Args:
        response_schema(type[BaseModel]): pydantic schema of the output
        messages(List[BaseMessage]): list of LangChain messages
        llm: LLM to use for creating agent
        tools: tools that can be bind and used by the agent
    Returns:
        return both agent response and the tool used
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        llm_with_tools = llm.bind_tools(tools)
        agent= create_agent(
            model=llm_with_tools,  # Use the bound model
            tools=tools,
            response_format=response_schema,
            )

        result = agent.invoke({"messages": messages})
        tools_used = [t.name for t in result.get("messages", []) if isinstance(t, ToolMessage)]

        return result, tools_used
    except Exception as e:
        logger.error(f"Error in invoke_react_agent: {e}")
        raise
