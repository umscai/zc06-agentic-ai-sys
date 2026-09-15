
from langchain_core.runnables import RunnableConfig
from agents.agent_common import AgentState
from tools.severity_bands_tools import get_telemetry_normal_range
import logging
logger = logging.getLogger(__name__)

def class1_control_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    LangGraph Node responsible for Class-1 Anomaly (Control)
    Args:
        state (AgentState): Current state of the workflow graph.
        config (RunnableConfig): Runtime configuration (e.g., configurable LLM instance).
    Returns:
        AgentState: Partial state update dict for LangGraph.
    """
    try:
        telemetry = state.get("telemetry", {})
        severity_bands = state.get("severity_bands", {})
        asset_id = state.get("asset_id", 0)
        VFD =state.get("VFD", 0)

        # assert only 1 Low or 1 High in severity band (the rest are normal)
        bands = list(severity_bands.values())
        low_count = bands.count("Low")
        high_count = bands.count("High")
        normal_count= bands.count("Normal")
        is_only_one_low_or_one_high= (high_count == 1 and normal_count == 3) or (low_count == 1 and normal_count == 3)
        if not is_only_one_low_or_one_high:
            action_taken = (
                f"Expect only one telemetry to be High or Low for VFD control with the rest to be Normal\n"
                f"But severity_bands = {severity_bands}\n"
                f"No action is taken, wait for next evaluation."
            )
            logger.warning(f"Invalid scenario route to class1: anomaly count:normal={normal_count}, high={high_count}, low={low_count}")
            return {'action_taken': action_taken}

        if VFD == 1 and severity_bands.get('pressure_psi','Normal')=='Low':
            n_min, n_max = get_telemetry_normal_range('pressure_psi', asset_id)
            n_mean = (n_min+n_max)/2
            current = telemetry.get('pressure_psi', n_min)
            target = n_mean # move to mean value instead of min(n_min*1.2, n_max) # move 20% above min normal_value
            action_taken = (
                f"set VFD control to increase pressure_psi\n"
                f"from {current}-Low pressure to {target} (mean Normal value)."
            )
            logger.info("pressure increase is activated.")
            return {'action_taken': action_taken, "func_used":['get_telemetry_normal_range']}
        if VFD==-1:
            if severity_bands.get('pressure_psi','Normal')=='High':
                n_min, n_max = get_telemetry_normal_range('pressure_psi', asset_id)
                n_mean = (n_min+n_max)/2
                current = telemetry.get('pressure_psi', n_max)
                target = n_mean # move to mean value instead of max(n_max*0.8, n_min) # move 20% below max normal_value
                action_taken = (
                    f"set VFD control to decrease pressure_psi\n"
                    f"from {current}-High pressure to {target} (mean Normal value)."
                )
                logger.info("pressure decrease is activated.")
                return {'action_taken': action_taken, "func_used":['get_telemetry_normal_range']}
            elif severity_bands.get('power_kw','Normal')=='High':
                n_min, n_max = get_telemetry_normal_range('power_kw', asset_id)
                n_mean = (n_min+n_max)/2
                current = telemetry.get('power_kw', n_max)
                target = n_mean # move to mean value instead of max(n_max*0.8, n_min) # move 20% below max normal_value
                action_taken = (
                    f"set VFD control to decrease power_kw\n"
                    f"from {current}-High power_kw to {target} (mean Normal value)."
                )
                logger.info("power decrease is activated.")
                return {'action_taken': action_taken, "func_used":['get_telemetry_normal_range']}
            else:
                action_taken = (
                    f"Expect Low/High pressure_psi or High power_kw for VFD control\n"
                    f"But severity_bands = {severity_bands}\n"
                    f"No action is taken, wait for next evaluation."
                )
                logger.warning(f"Invalid scenario with VFD=-1 route to class-1:severity-bands={severity_bands}")
                return {'action_taken': action_taken}

    except Exception as e:
        logger.error(f"Error in class1_control_node: {str(e)}")
        action_taken = (
            f"Encounter some internal error\n"
            f"No action is taken, wait for next evaluation."
        )
        return {'action_taken': action_taken, "error":  str(e)}