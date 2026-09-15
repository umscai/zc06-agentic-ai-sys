from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sqlalchemy import create_engine, inspect

from config import settings
from orchestration.graph import build_pump_anomaly_workflow


class GetWorkflowAnalytics:
    """Get and plot token usage, tool usage, func usage, and confidence scores of Assets."""

    def __init__(self, checkpoint_db_path: Path = settings.CHECKPOINT_DIR / settings.CHECKPOINT_DB):
        self.graph = build_pump_anomaly_workflow()
        self.engine = create_engine(f"sqlite:///{checkpoint_db_path}", echo=False)
        inspector = inspect(self.engine)
        table_names = inspector.get_table_names()
        self.table = "checkpoints" if "checkpoints" in table_names else None
        self.df_usage = None

    def get_asset_ids(self):
        if self.table:
            df = pd.read_sql_table(self.table, self.engine)
            aids = df["thread_id"].unique()
            return aids
        return None

    def get_token_usage(self, msg_list: list) -> dict:
        """
        Extracts a token usage in the message history.
        Args:
            msg_list(list): list of LangChain/LangGraph-formatted messages
        Returns:
            A dict contain input, output and total usage
        """
        results = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        for msg in msg_list:
            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                for k in results:
                    results[k] += msg.usage_metadata.get(k, 0)
        return results

    def get_tool_usage(self, msg_list: list) -> list:
        """
        Extracts a list of all tool names invoked in the message history.
        Args:
            msg_list(list): list of LangChain/LangGraph-formatted messages
        Returns:
            A list, preserving order and allowing for multiple calls to the same tool.
        """
        tool_names = []
        for msg in msg_list:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    name = tool_call.get("name")
                    if name:
                        tool_names.append(name)
        return tool_names

    def get_usage_per_asset(self):
        """ Get usage per asset from Checkpoint dB"""
        aids = self.get_asset_ids()
        if aids is None:
            return None

        usage_data = []
        for aid in aids:
            config = {"configurable": {"thread_id": aid}}
            state = self.graph.get_state(config)

            # Extract state values
            messages = state.values.get("messages", [])
            confidence = state.values.get("confidence")
            func_used = state.values.get("func_used") or []

            # Get Token Metrics & Tool Usage
            tokens = self.get_token_usage(messages)
            tools_called = self.get_tool_usage(messages)

            # Combine data
            entry = {
                "asset_id": aid,
                "tools_used": tools_called,
                "tool_count": len(tools_called),
                "func_used": func_used,
                "func_count": len(func_used),
                "confidence": confidence,
                **tokens,
            }

            if tokens["total_tokens"] > 0 or len(tools_called) > 0 or len(func_used) > 0:
                usage_data.append(entry)

        self.df_usage = pd.DataFrame(usage_data)
        return self.df_usage

    def get_df_usage(self):
        if self.df_usage is None:
            return self.get_usage_per_asset()
        return self.df_usage

    def plot_token_usage_per_aid(self):
        """Plot Token usage by AI/LLM."""
        df_usage = self.get_df_usage()
        df_usage.plot(
            x="asset_id",
            y=["input_tokens", "output_tokens"],
            kind="bar",
            stacked=True,
            figsize=(10, 6),
            color=["#3498db", "#e74c3c"],
            rot=0,
        )
        plt.title("Token Usage Breakdown per Asset")
        plt.ylabel("Token Count")
        plt.xlabel("Asset ID")
        plt.tight_layout()
        plt.savefig(settings.IMG_DIR / "token_usage.png", dpi=300)
        plt.show()

    def plot_tool_usage_count(self):
        """Plot frequency of workflow tool usage by AI/LLM."""
        df_usage = self.get_df_usage()
        all_tools = [tool for sublist in df_usage["tools_used"] for tool in sublist]
        tool_counts = pd.Series(all_tools).value_counts(sort=True, ascending=True)

        tool_counts.plot(kind="barh", color="#2ecc71", figsize=(8, 5))
        plt.title("Most Frequently Called Tools")
        plt.xlabel("Total Number of Invocations")
        plt.tight_layout()
        plt.savefig(settings.IMG_DIR / "tool_usage.png", dpi=300)
        plt.show()

    def plot_func_usage_count(self):
        """Plot frequency of workflow functions used."""
        df_usage = self.get_df_usage()
        all_funcs = [func for sublist in df_usage["func_used"] for func in sublist]

        if not all_funcs:
            print("No function usage data available to plot.")
            return

        func_counts = pd.Series(all_funcs).value_counts(sort=True, ascending=True)

        func_counts.plot(kind="barh", color="#9b59b6", figsize=(8, 5))
        plt.title("Most Frequently Used Node Functions")
        plt.xlabel("Total Number of Executions")
        plt.tight_layout()
        plt.savefig(settings.IMG_DIR / "func_usage.png", dpi=300)
        plt.show()

    def plot_confidence_distribution(self):
        """Plot histogram with KDE for state confidence scores."""
        df_usage = self.get_df_usage()
        df_confidence = df_usage["confidence"].dropna()

        if df_confidence.empty:
            print("No confidence score data available to plot.")
            return

        plt.figure(figsize=(8, 5))
        sns.histplot(df_confidence, kde=True, color="#e67e22", bins=10)
        plt.title("Confidence Score Distribution")
        plt.xlabel("Confidence")
        plt.ylabel("Density / Count")
        plt.xlim(0, 1.0)  # Adjust range if confidence isn't bounded [0, 1]
        plt.tight_layout()
        plt.savefig(settings.IMG_DIR / "confidence_distribution.png", dpi=300)
        plt.show()


if __name__ == "__main__":
    analytics = GetWorkflowAnalytics()
    analytics.plot_token_usage_per_aid()
    analytics.plot_tool_usage_count()
    analytics.plot_func_usage_count()
    analytics.plot_confidence_distribution()