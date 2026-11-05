"""Optional LangChain + Chroma conversational orchestrator for JARVIS.

Install its optional dependencies with:
    python -m pip install -r requirements-agent.txt

The plugin uses Mark's configured model through core.gemini and stores history
locally under memory/agent_chroma. Its read-only tools include the manually
maintained localhost inventory API; it does not scan network devices.
"""
from pathlib import Path
import threading

PLUGIN = {
    "name": "agent_orchestrator",
    "description": (
        "Route a request through the local LangChain/Chroma context helper. Use it "
        "to search conversation history, list names inside the user's home folder, "
        "check basic system status, or read the manually maintained Mark-LVI local "
        "device inventory. It does not scan or contact network devices."
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

_ORCHESTRATOR = None
_ORCHESTRATOR_LOCK = threading.Lock()


def _get_orchestrator():
    """Create Chroma once per process; avoid reopening its database per request."""
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        with _ORCHESTRATOR_LOCK:
            if _ORCHESTRATOR is None:
                from plugins._agent_orchestrator import AgentOrchestrator
                root = Path(__file__).resolve().parents[1]
                _ORCHESTRATOR = AgentOrchestrator(root / "memory" / "agent_chroma")
    return _ORCHESTRATOR


def run(parameters: dict, player=None, session_memory=None) -> str:
    """Plugin entry point called by Mark's existing PluginRegistry on a worker."""
    task = str((parameters or {}).get("task") or "").strip()
    if not task:
        return "Please provide a task for the agent orchestrator."
    try:
        return _get_orchestrator().run(task, player=player)
    except ImportError as exc:
        missing = getattr(exc, "name", None) or "LangChain/Chroma dependency"
        return (
            "The agent orchestrator needs optional dependencies. Install them with "
            f"'python -m pip install -r requirements-agent.txt' (missing: {missing})."
        )
    except Exception as exc:
        return f"The agent orchestrator could not complete the request: {exc}"
