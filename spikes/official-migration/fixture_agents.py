import json

from agent_framework import AgentResponse, Message
from trial_support import PINNED_AGENTS


class FixtureAgent:
    def __init__(self, name: str, route: str, calls: list[dict]):
        self.id = name
        self.name = name
        self.route = route
        self.calls = calls

    async def run(self, messages, *, options=None, **kwargs) -> AgentResponse:
        texts = [messages] if isinstance(messages, str) else [item.text for item in messages]
        self.calls.append({"name": self.name, "messages": texts})
        text = (
            json.dumps({"route": self.route})
            if self.name == "kppdemo-router"
            else f"OFFLINE FIXTURE ONLY: {self.name}"
        )
        return AgentResponse(messages=[Message(role="assistant", contents=[text])])


def fixtures(route: str) -> tuple[dict[str, FixtureAgent], list[dict]]:
    calls: list[dict] = []
    return {name: FixtureAgent(name, route, calls) for name in PINNED_AGENTS}, calls
