import os
import sys
from notte_sdk import NotteClient

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quickstart.py '<your task>'")
        sys.exit(1)
    task = sys.argv[1]

    client = NotteClient(api_key=os.getenv("NOTTE_API_KEY"))

    with client.Session(headless=False) as session:
        agent = client.Agent(reasoning_model="gemini/gemini-2.0-flash", max_steps=5, session=session)
        response = agent.run(task=task)
