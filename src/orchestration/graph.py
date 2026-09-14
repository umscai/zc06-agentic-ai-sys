import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from agents.agent_common import AgentState
from agents.agent_anomaly_detector import detect_anomaly_node
from agents.agent_classifier import classifier_node
from agents.agent_class0_shutdown import class0_shutdown_node
from agents.agent_class1_control import class1_control_node
from agents.agent_class2_escalate import class2_escalate_node
from agents.agent_ltm_update import ltm_update_node
from config import settings
import logging
logger = logging.getLogger(__name__)



def route_after_anomaly(state: AgentState) -> str:
    """Route based on anomaly detection status."""
    return "ANOMALY" if state.get("is_anomaly") else "NORMAL"

def route_classification(state: AgentState) -> str:
    """Route according to assigned classification class."""
    return state.get("classification_class", "CLASS_2") #Unknown should not happen, fall-back must be decided inside classifier logic


def build_pump_anomaly_workflow() -> CompiledStateGraph:
    builder = StateGraph(AgentState)

    # Add Nodes
    builder.add_node("agent_anomaly_detector", detect_anomaly_node)
    builder.add_node("agent_classifier", classifier_node)
    builder.add_node("agent_class0_shutdown", class0_shutdown_node)
    builder.add_node("agent_class1_control", class1_control_node)
    builder.add_node("agent_class2_escalate", class2_escalate_node)
    builder.add_node("agent_ltm_update", ltm_update_node)

    # Define Graph Edges
    builder.add_edge(START, "agent_anomaly_detector")
    builder.add_conditional_edges(
        "agent_anomaly_detector",
        route_after_anomaly,
        {
            "ANOMALY": "agent_classifier",
            "NORMAL": END,
        }
    )

    builder.add_conditional_edges(
        "agent_classifier",
        route_classification,
        {
            "CLASS_0": "agent_class0_shutdown",
            "CLASS_1": "agent_class1_control",
            "CLASS_2": "agent_class2_escalate",
        }
    )

    # 3. Action Nodes Converge Back to LTM Update
    builder.add_edge("agent_class0_shutdown", "agent_ltm_update")
    builder.add_edge("agent_class1_control", "agent_ltm_update")
    builder.add_edge("agent_class2_escalate", "agent_ltm_update")
    builder.add_edge("agent_ltm_update", END)

    # Checkpointer Setup
    settings.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        settings.CHECKPOINT_DIR / settings.CHECKPOINT_DB,
        check_same_thread=False
    )
    memory = SqliteSaver(conn)

    return builder.compile(checkpointer=memory)


# Single pre-compiled workflow instance
#pump_anomaly_graph = build_pump_anomaly_workflow()


#----------------------------------------------------------------------------------------
def init_checkpoint_db(force_reset:bool=False):
    """
    init and Create a new SQLite database for checkpoint by building the graph
    reset before creating if force_reset=True (also generate graph PNG)
    Args:
        - force_reset: if True, reset existing dB and then init/setup, otherwise no action is taken
    Returns:
        None
    Raises:
        Exception: Re-raises any exception caught during processing after logging.
    """
    try:
        db_path = settings.CHECKPOINT_DIR / settings.CHECKPOINT_DB
        if db_path.exists():
            if force_reset:
                db_path.unlink()
                print(f"Existing database at {db_path} removed.")
            else:
                print(f'database already exist at :{db_path} (no action is taken)')
                return
        else:
            print(f'No database at {db_path}, Init and setup for the first time!')

        # Ensure parent folder exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        pump_anomaly_graph = build_pump_anomaly_workflow()
        print("LanGraph Checkpoint Database created successfully.")

        # Also Generate graph PNG image
        path = settings.IMG_DIR / settings.WORKFLOW_GRAPH
        png_bytes = pump_anomaly_graph.get_graph().draw_mermaid_png()
        with open(path, "wb") as f:
            f.write(png_bytes)
        print(f"Graph successfully rendered and saved to {path}")
    except Exception as e:
        logger.error(f"Error in init_checkpoint_db at {db_path} with force_reset={force_reset}: {e}")
        raise


if __name__ == "__main__":
    init_checkpoint_db(force_reset=True)