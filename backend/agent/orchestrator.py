from __future__ import annotations

import json
import logging
from typing import Any, Optional

import litellm

from backend.agent.conversation import store
from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tool_schemas import TOOL_SCHEMAS
from backend.agent.tools import (
    compare_airports,
    get_airport_stats,
    get_demand_analysis,
    get_flight_breakdown,
    score_airports,
    search_airports,
)
from backend.config import settings
from backend.data.loader import get_data_vintage

logger = logging.getLogger(__name__)

TOOL_MAP = {
    "search_airports": search_airports,
    "get_airport_stats": get_airport_stats,
    "compare_airports": compare_airports,
    "score_airports": score_airports,
    "get_flight_breakdown": get_flight_breakdown,
    "get_demand_analysis": get_demand_analysis,
}

MAX_TOOL_ROUNDS = 6


def _execute_tool(name: str, arguments: dict[str, Any]) -> str:
    fn = TOOL_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(**arguments)
        return json.dumps(result, default=str)
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return json.dumps({"error": str(e)})


async def run_agent(
    message: str,
    conversation_id: Optional[str] = None,
) -> dict:
    cid, history = store.get_or_create(conversation_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    store.append(cid, {"role": "user", "content": message})

    tools_called: list[str] = []
    assumptions: list[str] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = await litellm.acompletion(
            model=settings.llm_model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        assistant_msg = choice.message

        if not assistant_msg.tool_calls:
            content = assistant_msg.content or ""
            store.append(cid, {"role": "assistant", "content": content})

            vintage = get_data_vintage()
            return {
                "response": content,
                "conversation_id": cid,
                "tools_called": tools_called,
                "data_vintage": vintage.get("latest_period", "unknown"),
                "assumptions": assumptions,
            }

        messages.append(assistant_msg.model_dump())

        for tc in assistant_msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            tools_called.append(fn_name)
            logger.info("Tool call: %s(%s)", fn_name, fn_args)

            result_str = _execute_tool(fn_name, fn_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

    final_content = "I reached the maximum number of tool calls for this query. Here is what I found so far based on the data retrieved."
    store.append(cid, {"role": "assistant", "content": final_content})
    vintage = get_data_vintage()
    return {
        "response": final_content,
        "conversation_id": cid,
        "tools_called": tools_called,
        "data_vintage": vintage.get("latest_period", "unknown"),
        "assumptions": assumptions,
    }
