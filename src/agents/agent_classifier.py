import logging
from typing import Literal, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage, ToolMessage

from agents.agent_common import AgentState, invoke_react_agent, SeverityBand
from tools.severity_bands_tools import get_severity_bands
from tools.ltm_db_tools import get_anomaly_history, format_anomaly_context
from utils import get_val
from config import settings

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
CLASSIFICATION_PROMPT6 = """
You are an Industrial Anomaly & Incident Response Agent monitoring a Multistage Centrifugal Water Pump.

### Operational Context
Asset: {asset_id}
Timestamp: {timestamp}
Telemetry: {telemetry}
Context: {context}

### Instructions
1. Call `get_severity_bands` using the provided telemetry and asset_id.
2. Evaluate the returned severity bands against the following logic rules (in order of priority):

#### Logic Rules:
- **CLASS_0 (Immediate Shutdown, VFD=0)**:
  - Triggered if ANY of `temperature_c`, `pressure_psi`, or `vibration_hz` is `Critically_High`.

- **CLASS_1 (VFD Adjustment)**:
  - Triggered only in 3 cases:
    - ONLY `pressure_psi` is `High`, and other parameters are `Normal` (Set VFD = -1)
    - ONLY `power_kw` is `High`, and other parameters are `Normal` (Set VFD = -1)
    - ONLY `pressure_psi` is `Low`, , and other parameters are `Normal` (Set VFD = 1)

- **CLASS_2 (On-Site Engineer Escalation, VFD=0)**:
  - Assign for all other combinations, or unhandled conditions.

3. Complete the structured response based on your findings.


### EXAMPLES
1- vibration_hz=Critically_High
    - one of temperature_c, pressure_psi, or vibration_hz is Critically_High: CLASS_0, VFD=0, Immediate Shutdown.
2- pressure_psi=Critically_High
    - one of temperature_c, pressure_psi, or vibration_hz is Critically_High: CLASS_0, VFD=0, Immediate Shutdown.
3- temperature_c=Critically_High
    - one of temperature_c, pressure_psi, or vibration_hz is Critically_High: CLASS_0, VFD=0, Immediate Shutdown.
4- pressure_psi=Low, all other parameter are Normal
    - only pressure_psi is Low, and others are Normal: CLASS_1, VFD=1
5-  power_kw=High, all other parameter are Normal
    - only power_kw is High, and and others are Normal: CLASS_1, VFD=-1
6- pressure_psi=High, all other parameter are Normal
    - only pressure_psi is High, and others are Normal: CLASS_1, VFD=-1
7- power_kw=Critically_High
    - neither in CLASS_0, nor class_1, assign to CLASS_2 with VFD=0
5- temperature_c=High, pressure_psi=High
    - neither in CLASS_0, nor class_1, assign to CLASS_2 with VFD=0
7- vibration_hz= Critically_Low
    - neither in CLASS_0, nor class_1, assign to CLASS_2 with VFD=0
"""

CLASSIFICATION_PROMPT= CLASSIFICATION_PROMPT6

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
        #context = state.get("context", "")
        if settings.USE_CONTEXT:
            history_list = get_anomaly_history(asset_id=str(state.get("asset_id")), k=3)
            context_str = format_anomaly_context(history_list)
            func_used = ['get_anomaly_history', 'format_anomaly_context']
        else:
            context_str =""
            func_used = []

        # Format System Prompt
        sys_message = CLASSIFICATION_PROMPT_TEMPLATE.format(
            asset_id=state.get("asset_id", "UNKNOWN"),
            timestamp=state.get("timestamp", ""),
            telemetry=state.get("telemetry", {}),
            context=context_str
        )

        #messages = [{"role": "system", "content": sys_message}]
        messages = [SystemMessage(content=sys_message)]

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
            "context": context_str,
            "func_used":func_used,
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
            "func_used": [],
            "messages": [],
            "context": "",
            "error": str(e)
        }

