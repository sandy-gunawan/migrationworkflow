import json
import logging
from dataclasses import dataclass

from agent_framework import Case, Default, Executor, WorkflowBuilder, WorkflowContext, handler
from trial_support import SPECIALISTS

logger = logging.getLogger(__name__)

TERMINAL_ACTIVITIES = {
    "fabric_iq": (
        "KPP_ROUTE:fabric_iq\nKPP_STATUS:blocked\n"
        "Native Fabric ontology is unavailable: FeatureNotAvailable."
    ),
    "work_iq": (
        "KPP_ROUTE:work_iq\nKPP_STATUS:blocked\n"
        "A separate Work IQ sandbox has not been supplied. No workplace data was accessed."
    ),
    "clarification": (
        "KPP_ROUTE:clarification\nKPP_STATUS:clarification\n"
        "Please specify one topic: production, maintenance, stock, document lookup, "
        "or native knowledge retrieval."
    ),
    "unsupported": (
        "KPP_ROUTE:unsupported\nKPP_STATUS:unsupported\n"
        "Only read-only questions about the new synthetic mining demo are supported. "
        "Live systems and writes are not accessed."
    ),
}


@dataclass
class Run:
    question: str
    route: str = ""


class Router(Executor):
    def __init__(self, agents):
        super().__init__(id="classify_question")
        self.agents = agents

    @handler
    async def classify(self, run: Run, ctx: WorkflowContext[Run, str]) -> None:
        response = await self.agents["kppdemo-router"].run(run.question)
        try:
            decision = json.loads(response.text)
        except json.JSONDecodeError as exc:
            logger.warning("The router returned invalid JSON: %s", exc)
            decision = {}
        if isinstance(decision, dict) and isinstance(decision.get("route"), str):
            run.route = decision["route"]
        await ctx.send_message(run)


class Specialist(Executor):
    def __init__(self, route: str, agent):
        super().__init__(id=f"invoke_{route}")
        self.route = route
        self.agent = agent

    @handler
    async def retrieve(self, run: Run, ctx: WorkflowContext[None, str]) -> None:
        await ctx.yield_output(f"KPP_ROUTE:{self.route}")
        response = await self.agent.run(run.question)
        await ctx.yield_output(response.text)


class Finish(Executor):
    def __init__(self, route: str | None):
        super().__init__(id=f"finish_{route or 'invalid_router'}")
        self.route = route

    @handler
    async def finish(self, run: Run, ctx: WorkflowContext[None, str]) -> None:
        if self.route is None:
            activity = (
                "KPP_ROUTE:unsupported\nKPP_STATUS:failed\n"
                "The router returned an unrecognized route. No specialist was invoked."
            )
        else:
            activity = TERMINAL_ACTIVITIES[self.route]
        await ctx.yield_output(activity)


def build_workflow(agents):
    router = Router(agents)
    cases = []
    for route, name in SPECIALISTS.items():
        target = Specialist(route, agents[name])
        cases.append(
            Case(
                condition=lambda run, selected=route: run.route == selected,
                target=target,
            )
        )
    for route in TERMINAL_ACTIVITIES:
        target = Finish(route)
        cases.append(
            Case(
                condition=lambda run, selected=route: run.route == selected,
                target=target,
            )
        )
    cases.append(Default(target=Finish(None)))
    return (
        WorkflowBuilder(
            start_executor=router,
            name="toolkit-guided-mining-codegen",
            max_iterations=4,
            output_from="all",
        )
        .add_switch_case_edge_group(router, cases)
        .build()
    )
