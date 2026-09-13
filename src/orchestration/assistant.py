import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from config import settings
from orchestration.graph import build_pump_anomaly_workflow

logger = logging.getLogger(__name__)


class PumpAnomalyAssistant:
    """Orchestrates pump telemetry processing across persistent asset threads."""

    def __init__(
        self,
        api_key: str = settings.OPENAI_API_KEY,
        model_name: str = settings.MODEL_NAME,
        temperature: float = settings.TEMPERATURE,
    ):
        # Initialize LLM

        try:
            #ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.MODEL_NAME)
            self.llm = ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)
        except Exception as e:
            raise RuntimeError(f"LLM Initialization failed: {e}")

        # Build workflow graph (with checkpointer enabled)
        try:
            self.workflow = build_pump_anomaly_workflow()
        except Exception as e:
            raise RuntimeError(f"Agent Graph creation failed: {e}")

    def run(self, asset_id: int, telemetry: Dict[str, float]) -> Dict[str, Any]:
        """
        Processes incoming telemetry for a specific pump asset.

        Uses asset_id as thread_id so SqliteSaver automatically tracks history
        per pump.
        """
        # 1. Thread configuration mapping asset_id -> thread_id
        config = {
            "configurable": {
                "thread_id": str(asset_id),
                "llm": self.llm
            }
        }

        # 2. Format telemetry input into a HumanMessage
        user_msg = HumanMessage(content=f"Telemetry payload for {asset_id}: {telemetry}")

        # 3. Payload state input
        # Note: LangGraph checkpointer will merge this input with existing state for this thread_id
        input_state = {
            "asset_id": asset_id,
            "telemetry": telemetry,
            "messages": [user_msg]
        }

        try:
            # Invoke graph with checkpointer configuration
            ## SqliteSaver handles thread lookup, state re-hydration, and merging automatically (benefit of using persistence checkpointer instead of RAM)
            final_state = self.workflow.invoke(input_state, config=config)
            final_resp = final_state.get("response", "")

            return {
                "success": True,
                "response": final_resp,
                "state": final_state,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error in PumpAnomalyAssistant.run for {asset_id}: [{type(e).__name__}] {str(e) or repr(e)}", exc_info=True)
            #logger.error(f"Error in PumpAnomalyAssistant.run for {asset_id}: {str(e)}")
            return {
                "success": False,
                "response": None,
                "state": {},
                "error": str(e)
            }


