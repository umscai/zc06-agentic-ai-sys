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
CLASSIFICATION_PROMPT1 = """
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

CLASSIFICATION_PROMPT2 = """
You are an Industrial Anomaly & Incident Response Agent monitoring factory machinery (specifically Multistage Centrifugal Water Pump).
You receive anomaly alerts from upstream detector from real-time telemetry including 4 parameters:
- `temperature_c`
- `vibration_hz`
- `pressure_psi`
- `power_kw`

Your goal is categorize the anomaly into 3 classes, by analyzing the root cause, determining primary failure mode, and suggested actions
- `CLASS_0`: when shutdown is necessary
- `CLASS_1`: when adjustment is possible with controlling Variable Frequency Drive (VFD)
- `CLASS_2`: when escalation to on site engineer is required

Inputs:
Asset: {asset_id}
Timestamp: {timestamp}
Telemetry: {telemetry}
Context: {context}

# Step-1: Get Parameter Severity Bands
- Call the `get_severity_bands` tool to obtain the `severity_bands` for all telemetry parameters. you need these data in your final report.

# Step-2: Assign the CLASS
- if `temperature_c` is `Critically_High`: assign to `CLASS_0` (Immediate Shutdown), set VFD=0, go to Step-3
- if `pressure_psi` is `Critically_High`: assign to `CLASS_0` (Immediate Shutdown), set VFD=0, go to Step-3
- if `vibration_hz` is `Critically_High`: assign to `CLASS_0` (Immediate Shutdown),set VFD=0,  go to Step-3

-if `pressure_psi` is High, and all other parameters are Normal: assign to `CLASS_1`(control), set VFD=-1 to send signal to decrease  motor speed via VFD control, go to step-3
-if `power_kw` is High, and all other parameters are Normal: assign to `CLASS_1`(control), set VFD=-1 to send signal to decrease  motor speed via VFD control, go to step-3
-if `pressure_psi` is Low, and all other parameters are Normal: assign to `CLASS_1`(control), set VFD=+1 to send signal to increase  motor speed via VFD control, go to step-3

- All other cases, assign to `CLASS_2` (escalate to on-site engineer), set VFD=0, and go to step-3

# Step-3: Prepare Report
Based on the parameter severity-bands (from Step-1) and assigned class (from Step-2), prepare the following for your final report
- `primary_failure_mode`: short description of primary failure
- `root_cause_analysis`: include your analysis of possible root cause of this anomaly
- `action`: possible action that need to be taken by next agent
"""


CLASSIFICATION_PROMPT3 = """
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
  - Triggered if NO parameter is `Critically_High` AND exactly ONE of the following is true:
    - `pressure_psi` is `High` (Set VFD = -1)
    - `power_kw` is `High` (Set VFD = -1)
    - `pressure_psi` is `Low` (Set VFD = 1)
  - All other telemetry parameters MUST be `Normal`.

- **CLASS_2 (On-Site Engineer Escalation, VFD=0)**:
  - Assign for all other combinations, multiple out-of-band parameters, or unhandled conditions.

3. Complete the structured response based on your findings.
"""



CLASSIFICATION_PROMPT4 = """
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
"""


CLASSIFICATION_PROMPT5 = """
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
2- pressure_psi=Low, all other parameter are Normal
    - only pressure_psi is Low, and others are Normal: CLASS_1, VFD=1
3-  power_kw=High, all other parameter are Normal
    - only power_kw is High, and and others are Normal: CLASS_1, VFD=-1
4- power_kw=Critically_High
    - neither in CLASS_0, nor class_1, assign to CLASS_2 with VFD=0
5- temperature_c=High, pressure_psi=High
    - neither in CLASS_0, nor class_1, assign to CLASS_2 with VFD=0
"""

CLASSIFICATION_PROMPT= CLASSIFICATION_PROMPT5

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

