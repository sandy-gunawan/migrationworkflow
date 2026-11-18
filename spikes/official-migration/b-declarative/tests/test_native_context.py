import asyncio
from unittest.mock import AsyncMock, Mock

from agent_framework import AgentContext, Message
from fixture_agents import fixtures
from trial_support import AgentPool, PreserveNativeContext

QUESTION = "Show work orders for equipment TRK001."


def test_bridge_restores_original_question_and_native_route_activity():
    pool = Mock(spec=AgentPool)
    pool.question = QUESTION
    pool.conversation_id = "conv_owned_fixture"
    pool.append_activity = AsyncMock()
    agents, _ = fixtures("mcp")
    context = AgentContext(
        agent=agents["kppdemo-mcp"],
        messages=[Message(role="user", contents=[str({"role": "user", "text": QUESTION})])],
    )
    continuation = AsyncMock()
    asyncio.run(PreserveNativeContext(pool).process(context, continuation))
    assert [message.text for message in context.messages] == [QUESTION]
    assert context.options["conversation_id"] == "conv_owned_fixture"
    pool.append_activity.assert_awaited_once_with("KPP_ROUTE:mcp")
    continuation.assert_awaited_once_with()


def test_bridge_does_not_invent_a_specialist_activity_for_the_router():
    pool = Mock(spec=AgentPool)
    pool.question = QUESTION
    pool.conversation_id = "conv_owned_fixture"
    pool.append_activity = AsyncMock()
    agents, _ = fixtures("mcp")
    context = AgentContext(
        agent=agents["kppdemo-router"], messages=[Message(role="user", contents=[QUESTION])]
    )
    continuation = AsyncMock()
    asyncio.run(PreserveNativeContext(pool).process(context, continuation))
    pool.append_activity.assert_not_awaited()
    continuation.assert_awaited_once_with()
