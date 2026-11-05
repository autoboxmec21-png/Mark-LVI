"""Optional LangChain + Chroma conversational orchestrator for JARVIS.

Install its optional dependencies with:
    pip install langchain-core langchain-chroma chromadb

The plugin uses Mark's configured model through core.gemini and stores history
locally under memory/agent_chroma. Its router may call only the read-only tools
listed in plugins/_agent_orchestrator.py; it does not run arbitrary scripts.
"""
from pathlib import Path

PLUGIN = {
    "name": "agent_orchestrator",
    "description": (
        "Route a user request through the local LangChain/Chroma context helper. "
        "Use for searching relevant conversation history, listing names in the "
        "user's home directory, or checking basic system status. Only registered "
        "read-only tools are available; never use this to execute scripts."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {
                "type": "STRING",
                "description": "The user's request to route using local context and tools.",
            },
        },
        "required": ["task"],
    },
    "tier": "extra",
    "brief": "Route a request using local Chroma history and read-only tools.",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    task = str((parameters or {}).get("task") or "").strip()
    if not task:
        return "Please provide a task for the agent orchestrator."
    try:
        from plugins._agent_orchestrator import AgentOrchestrator
        root = Path(__file__).resolve().parents[1]
        orchestrator = AgentOrchestrator(root / "memory" / "agent_chroma")
        return orchestrator.run(task, player=player)
    except ImportError as exc:
        missing = getattr(exc, "name", None) or "LangChain/Chroma dependency"
        return (
            f"The agent orchestrator needs optional dependencies. Install them with "
            f"'pip install langchain-core langchain-chroma chromadb' (missing: {missing})."
        )
    except Exception as exc:
        return f"The agent orchestrator could not complete the request: {exc}"
