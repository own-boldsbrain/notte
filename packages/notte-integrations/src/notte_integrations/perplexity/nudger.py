import json
import os
from typing import Any

import requests
from loguru import logger
from requests.sessions import Session

TASK_SYSTEM_PROMPT = """Break down web tasks into simple steps that a basic web ai agent can follow. For each task:
1) State the main goal in one sentence
2) Build 1-3 plans for how the task can be achieved
-> Those plans need to be quite simple: agents have a restricted action set, such as: click, type, scroll, or select
3) Use plain language and specify elements that might come up
4) Avoid complex reasoning or edge cases unless absolutely critical

Keep your entire response under 10 sentences. Focus only on the minimum actions needed.
Remember: The agent can only click, type, scroll, and select specific elements on a webpage.
"""

NUDGE_SYSTEM_PROMPT = """Help web ai agents solve simple problems by providing clear, direct guidance:

1) Identify any issue the agent might be facing in 1-2 sentences
2) Try to reason about simple fixes, or other approaches that the agent might have missed.
3) Suggest 1-2 simple alternative approaches that should be easily implementable

Your goal is to help in reasoning, think outside the box and challenge a bit the information that the original agent collected.
Do not focus on the technical aspect, your goal is to work similarly to a human with clear mind,
that can effortlessly navigate the web, but without deep technical knowledge.

Keep suggestions under 5 sentences each. Avoid complex explanations.
Always prioritize the simplest possible solution that will work.
The next messages will come from the web ai agent: help them solve their task.
"""


class PerplexityModule:
    def __init__(self):
        ENV_VAR = "PERPLEXITY_API_KEY"
        self.api_key: str | None = os.getenv(ENV_VAR)
        if self.api_key is None:
            raise ValueError(f"Set env variable {ENV_VAR}")

        self.session: Session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def task_breakdown(self, task: str) -> str:
        messages = [
            {"role": "system", "content": TASK_SYSTEM_PROMPT},
            {"role": "user", "content": f"The task is: {task}"},
        ]

        data = {"model": "sonar", "messages": messages}
        resp = self.session.post("https://api.perplexity.ai/chat/completions", json=data)

        return resp.json()["choices"][0]["message"]["content"]

    def nudge(self, task: str, messages: list[dict[Any, Any]]) -> None:
        perp_messages = [
            f"The task of the agent is: {task}",
            "\nThe following messages are all messages from the web ai agent that you need to help:",
        ]

        for message in messages:
            content = message.get("content")
            role = message.get("role")
            if role != "system" and isinstance(content, str):
                perp_messages.append(json.dumps(message))

        perplexity_messages = [
            {"role": "system", "content": NUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(perp_messages)},
        ]

        logger.warning(f"input: {json.dumps(perp_messages, indent=2)}")
        with open("perplexity_input.json", "w") as f:
            json.dump(perp_messages, f)

        data = {"model": "sonar", "messages": perplexity_messages}
        resp = self.session.post("https://api.perplexity.ai/chat/completions", json=data)
        logger.warning(f"out: {json.dumps(resp.json())}")
        return resp.json()
