import logging
from typing import Literal, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import PromptTemplate

from agents.agent_common import AgentState, invoke_react_agent, SeverityBand
from tools.severity_bands_tools import get_severity_bands
from utils import get_val

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Tools & Structured Output Schema
# ------------------------------------------------------------------------------
TOOLS = [get_severity_bands]

class ClassificationOutput(BaseModel):
    classification_class: Literal["CLASS_0", "CLASS_1", "CLASS_2"] = Field(
        description="CLASS_0: Immediate Shutdown, CLASS_1: Control Adjust, CLASS_2: Engineer Dispatch"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    primary_failure_mode: str = Field(description="Name of the failure mechanism")
    root_cause_analysis: str = Field(description="Short technical narrative explaining root cause")
    action: str = Field(description="Details of action needed to be taken by next agent")
    severity_bands: Dict[str, SeverityBand] = Field(
        description="Map of sensor telemetry metrics to their respective severity bands"
    )
    # ONLY USED BY CLASS_1 agent: VFD= Variable Frequency Drive
    VFD:Literal[-1,0,1] = Field(description="-1: motor speed decrease, +1: motor speed increase, and 0:  otherwise")


# ------------------------------------------------------------------------------
# Prompt Design
# ------------------------------------------------------------------------------
CLASSIFICATION_PROMPT = """
You are an Industrial Anomaly Classification Agent. An upstream detector has already confirmed the anomaly.
Your job is to categorize the anomaly and prepare an action statement for the downstream agent.

Inputs:
Asset: {asset_id}
Timestamp: {timestamp}
Telemetry: {telemetry}
Context: {context}

# Step-1:
- Call the `get_severity_bands` tool to obtain the `severity_bands` for all telemetry parameters.

# Step-2:
- CLASS_0 (Immediate Shutdown):
  - If any of `temperature_c`, `vibration_hz`, or `pressure_psi` severity bands is `Critically_High`, assign `CLASS_0`. The asset requires an immediate shutdown.(VFD=0)
- CLASS_1 (Automated Control Adjustment):
  - If ONLY ONE of `pressure_psi` or `power_kw` is `High` (and all other severity bands are Normal):
    - Action: "Send a signal to decrease motor speed via Variable Frequency Drive (VFD)", set VFD=-1 for next agent.
  - If ONLY `pressure_psi` is `Low` (and all other severity bands are Normal):
    - Action: "Send a signal to increase motor speed via Variable Frequency Drive (VFD)" set VFD=+1 for next agent.
- CLASS_2 (Field Escalation):
  - All other anomaly conditions fall into `CLASS_2` and must be escalated to an on-site engineer (VFD=0)

# Step-3:
- For all scenarios, prepare a concise technical analysis, to set:
- `primary_failure_mode`, `root_cause_analysis`, and the specific `action` required for the downstream agent.
"""

CLASSIFICATION_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["asset_id", "timestamp", "telemetry", "context"],
    template=CLASSIFICATION_PROMPT
)
# ------------------------------------------------------------------------------
# LangGraph Node Function
# ------------------------------------------------------------------------------
def classifier_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph Node responsible for classifying high-severity anomalies (Z-score > 4)
    routed from the upstream detection agent.

    Args:
        state (AgentState): Current state of the workflow graph.
        config (RunnableConfig): Runtime configuration (e.g., configurable LLM instance).

    Returns:
        AgentState: Partial state update dict for LangGraph.
    """
    try:
        # Safely extract configurable settings
        llm = config.get("configurable").get("llm")
        #configurable = config.get("configurable", {}) if config else {}
        #llm = configurable.get("llm")

        # Long-Term Memory / Context placeholder
        context = state.get("context", "")

        # Format System Prompt
        sys_message = CLASSIFICATION_PROMPT_TEMPLATE.format(
            asset_id=state.get("asset_id", "UNKNOWN"),
            timestamp=state.get("timestamp", ""),
            telemetry=state.get("telemetry", {}),
            context=context
        )

        messages = [
            {"role": "system", "content": sys_message}
        ]

        # Invoke Agent with ReAct loop & Structured Output
        result, tools_used = invoke_react_agent(ClassificationOutput, messages, llm, TOOLS)

        data = result.get("structured_response") if isinstance(result, dict) else result
        ai_msg = result.get("messages", []) if isinstance(result, dict) else []

        logging_dict = {
            "asset_id": state.get("asset_id"),
            "classification_class": get_val(data, "classification_class"),
            "action": get_val(data, "action") or "",
            "tools_used": tools_used,
        }
        logger.info(logging_dict)

        # Return state update dictionary matching AgentState keys
        return {
            "classification_class": get_val(data, "classification_class"),
            "confidence": get_val(data, "confidence") or 0.0,
            "primary_failure_mode": get_val(data, "primary_failure_mode") or "",
            "root_cause_analysis": get_val(data, "root_cause_analysis") or "",
            "action": get_val(data, "action") or "",
            "VFD": get_val(data, "VFD") or 0,
            "severity_bands": get_val(data, "severity_bands") or {},
            "tools_used": tools_used,
            "messages": ai_msg,
            "error": None
        }

    except Exception as e:
        logger.error(f"Error in classify_node for asset {state.get('asset_id')}: {str(e)}", exc_info=True)

        # Consistent fallback return dict matching AgentState
        return {
            "classification_class": "CLASS_2",
            "confidence": 0.0,
            "primary_failure_mode": "Internal System Error",
            "root_cause_analysis": f"Classification node failed due to error: {str(e)}",
            "action": "On-site Engineer to check asset status and inspect classification agent logs.",
            "VFD": None,
            "severity_bands": {},
            "tools_used": [],
            "messages": [],
            "error": str(e)
        }

