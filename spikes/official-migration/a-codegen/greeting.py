from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler


class Greeting(Executor):
    def __init__(self):
        super().__init__(id="send_greeting")

    @handler
    async def greet(self, name: str, ctx: WorkflowContext[None, str]) -> None:
        await ctx.yield_output(f"Hello, {name}!")


def build_greeting():
    return WorkflowBuilder(start_executor=Greeting(), name="codegen-greeting").build()
