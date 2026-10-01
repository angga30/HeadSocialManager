"""Agent trace plugin — human-readable logs of the multi-agent process.

Logs, per conversation invocation:
  ▶/◀ agent enter/exit (nesting), · llm call + iteration, · tool call w/ args,
  ← tool result (ok/error + duration), ⇄ agent transfer, ✅ run summary
  (duration, model calls, tool calls, agent path).

Registered on the ADK App so it applies to every agent/tool/model in the run.
Output goes to logger "headofsocial.agent_trace" (see logging_config).
"""

import logging
import time
from typing import Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.models.llm_request import LlmRequest
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger("headofsocial.agent_trace")


def _short(value: Any, limit: int = 48) -> str:
    if isinstance(value, str):
        return value if len(value) <= limit else value[: limit - 3] + "..."
    return str(value)


def _compact_args(args: dict | None) -> str:
    if not args:
        return ""
    parts: list[str] = []
    for key, val in args.items():
        if isinstance(val, (list, tuple)):
            parts.append(f"{key}=[{len(val)} item]")
        elif isinstance(val, dict):
            parts.append(f"{key}={{{len(val)} field}}")
        elif isinstance(val, str):
            parts.append(f"{key}={_short(val)!r}")
        else:
            parts.append(f"{key}={_short(val)}")
    return ", ".join(parts)


def _result_summary(result: Any) -> str:
    if isinstance(result, dict):
        if result.get("ok") is False:
            return f"ERROR: {_short(result.get('error', ''), 80)}"
        keys = [k for k in ("id", "status", "created", "count", "asset_id", "post_id")]
        bits = [f"{k}={result[k]}" for k in keys if k in result]
        return ", ".join(bits) if bits else f"ok ({len(result)} field)"
    return _short(result)


class AgentTracePlugin(BasePlugin):
    """Logs the agent/model/tool flow for each invocation."""

    def __init__(self, name: str = "agent_trace") -> None:
        super().__init__(name=name)
        self._runs: dict[str, dict] = {}

    # --- helpers ---------------------------------------------------------
    @staticmethod
    def _key(ctx: Any) -> str:
        iid = getattr(ctx, "invocation_id", None)
        if iid:
            return str(iid)
        try:
            sess = getattr(ctx, "session", None)
            sid = getattr(sess, "id", None)
            if sid:
                return str(sid)
        except Exception:  # noqa: BLE001 - some contexts raise if session is unavailable
            pass
        return "default"

    def _run(self, ctx: Any) -> dict | None:
        return self._runs.get(self._key(ctx))

    def _current_agent(self, ctx: Any) -> str:
        rec = self._run(ctx)
        if rec and rec["stack"]:
            return rec["stack"][-1]
        return "?"

    # --- run lifecycle ---------------------------------------------------
    async def before_run_callback(self, *, invocation_context: InvocationContext):
        key = str(invocation_context.invocation_id)
        session_id = getattr(getattr(invocation_context, "session", None), "id", "?")
        self._runs[key] = {
            "start": time.monotonic(),
            "models": 0,
            "tools": 0,
            "agents": [],
            "stack": [],
            "agent_iters": {},
            "tool_starts": {},
        }
        logger.info("▶ RUN start | session=%s inv=%s", session_id, key[:8])
        return None

    async def after_run_callback(self, *, invocation_context: InvocationContext):
        key = str(invocation_context.invocation_id)
        rec = self._runs.pop(key, None)
        if rec is None:
            return None
        dur = time.monotonic() - rec["start"]
        path = " → ".join(rec["agents"]) or "-"
        logger.info(
            "✅ RUN done in %.1fs | llm=%d | tool=%d | agents=[%s]",
            dur, rec["models"], rec["tools"], path,
        )
        return None

    # --- agent lifecycle -------------------------------------------------
    async def before_agent_callback(self, *, agent: BaseAgent, callback_context: CallbackContext):
        rec = self._run(callback_context)
        if rec is not None:
            rec["stack"].append(agent.name)
            rec["agents"].append(agent.name)
            depth = len(rec["stack"]) - 1
            logger.info("%s▶ agent: %s", "  " * (depth + 1), agent.name)
        return None

    async def after_agent_callback(self, *, agent: BaseAgent, callback_context: CallbackContext):
        rec = self._run(callback_context)
        if rec is not None and rec["stack"]:
            rec["stack"].pop()
            depth = len(rec["stack"])
            logger.info("%s◀ agent: %s", "  " * (depth + 1), agent.name)
        return None

    # --- model calls -----------------------------------------------------
    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ):
        rec = self._run(callback_context)
        if rec is not None:
            rec["models"] += 1
            agent = self._current_agent(callback_context)
            rec["agent_iters"][agent] = rec["agent_iters"].get(agent, 0) + 1
            logger.info(
                "%s· llm call #%d (agent=%s, iterasi ke-%d)",
                "  " * (len(rec["stack"]) + 1), rec["models"], agent, rec["agent_iters"][agent],
            )
        return None

    async def on_model_error_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest, error: Exception
    ):
        rec = self._run(callback_context)
        indent = "  " * ((len(rec["stack"]) if rec else 0) + 1)
        logger.warning(
            "%s✖ model error (agent=%s): %s",
            indent, self._current_agent(callback_context), _short(error, 120),
        )
        return None

    # --- tool calls ------------------------------------------------------
    async def before_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext
    ):
        rec = self._run(tool_context)
        if rec is not None:
            rec["tools"] += 1
            call_id = getattr(tool_context, "function_call_id", None) or tool.name
            rec["tool_starts"][(tool.name, str(call_id))] = time.monotonic()
            logger.info(
                "%s· tool: %s(%s)",
                "  " * (len(rec["stack"]) + 1), tool.name, _compact_args(tool_args),
            )
        return None

    async def after_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, result: dict
    ):
        rec = self._run(tool_context)
        dur = ""
        if rec is not None:
            call_id = getattr(tool_context, "function_call_id", None) or tool.name
            started = rec["tool_starts"].pop((tool.name, str(call_id)), None)
            if started:
                dur = f" ({time.monotonic() - started:.2f}s)"
            logger.info(
                "%s← %s%s → %s",
                "  " * (len(rec["stack"]) + 1), tool.name, dur, _result_summary(result),
            )
        return None

    async def on_tool_error_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, error: Exception
    ):
        logger.warning("✖ tool error %s: %s", tool.name, _short(error, 120))
        return None

    # --- events (transfers) ---------------------------------------------
    async def on_event_callback(self, *, invocation_context: InvocationContext, event: Event):
        target = getattr(getattr(event, "actions", None), "transfer_to_agent", None)
        if target:
            logger.info("    ⇄ transfer: %s → %s", event.author or "?", target)
        return None