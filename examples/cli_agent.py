from typing import Unpack

import typer
from dotenv import load_dotenv
from notte_agent import Agent
from notte_agent.common.types import AgentResponse
from notte_sdk.types import AgentCreateRequestDict

# Load environment variables
_ = load_dotenv()


def main(headless: bool, task: str, **data: Unpack[AgentCreateRequestDict]) -> AgentResponse:
    agent = Agent(headless=headless, **data)
    return agent.run(task)


if __name__ == "__main__":
    print(typer.run(main))

# export task="open google flights and book cheapest flight from nyc to sf"
# uv run examples/cli_agent.py --task $task --reasoning_model "openai/gpt-4o"
