import asyncio
from pathlib import Path
from uuid import UUID

import pytest
from agent_framework import AgentContext, AgentResponse, Message
from fixture_agents import fixtures
from trial_support import PINNED_AGENTS, RecordAgent

from demo_common.contracts import DemoRequest
from spikes.declarative_ui.loader import WorkflowFile
from spikes.declarative_ui.runtime import canonical_result

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "spikes" / "official-migration" / "b-declarative" / "source.workflow.yaml"


def test_external_yaml_is_snapshotted_once_and_each_request_gets_a_fresh_workflow(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(
        "spikes.declarative_ui.loader.ENVIRONMENT", tmp_path / "not-distributed.env",
    )
    source = tmp_path / "downloaded.workflow.yaml"
    source.write_bytes(SOURCE.read_bytes())
    snapshot = WorkflowFile.load(source)
    source.write_text("changed after startup", encoding="utf-8")
    for route in ("work_iq", "unsupported"):
        agents, calls = fixtures(route)
        workflow = snapshot.create(agents)
        output = asyncio.run(workflow.run("Show work orders for equipment TRK001."))
        assert f"KPP_ROUTE:{route}" in "\n".join(output.get_outputs())
        assert [call["name"] for call in calls] == ["kppdemo-router"]
    with pytest.raises(ValueError, match="integrity|approved"):
        WorkflowFile.load(source)


def test_unapproved_yaml_fails_before_runtime_agent_binding(tmp_path):
    source = tmp_path / "unapproved.yaml"
    source.write_text("kind: workflow\ntrigger: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity|approved"):
        WorkflowFile.load(source)


def test_progress_observer_sees_agent_start_before_the_actual_continuation():
    async def exercise():
        agents, _ = fixtures("work_iq")
        observed, calls = [], []
        context = AgentContext(
            agent=agents["kppdemo-router"],
            messages=[Message(role="user", contents=["TRK001"])],
        )

        async def continuation():
            assert observed[0][0] == "agent_started"
            context.result = AgentResponse(
                messages=[Message(role="assistant", contents=['{"route":"work_iq"}'])],
                raw_representation={
                    "id": "resp_fixture",
                    "status": "completed",
                    "error": None,
                    "agent_reference": {
                        "type": "agent_reference",
                        "name": "kppdemo-router",
                        "version": PINNED_AGENTS["kppdemo-router"],
                    },
                    "conversation": {"id": "conv_fixture"},
                    "output": [],
                },
            )

        await RecordAgent(
            "kppdemo-router",
            "1",
            calls,
            lambda event, data: observed.append((event, data)),
        ).process(context, continuation)
        assert [event for event, _ in observed] == ["agent_started", "agent_completed"]
        assert calls[0]["native"]["id"] == "resp_fixture"

    asyncio.run(exercise())


def test_blocked_yaml_output_becomes_a_real_blocked_dto_not_an_answer():
    request = DemoRequest(
        question="A synthetic Work IQ question.",
        run_id=UUID("00000000-0000-4000-8000-000000000001"),
    )
    report = {
        "route": "work_iq",
        "result": {
            "route": "work_iq",
            "status": "blocked",
            "answer": "KPP_ROUTE:work_iq\nKPP_STATUS:blocked\nSeparate sandbox is unavailable.",
        },
    }
    result = canonical_result(request, report)
    assert result.run_id == request.run_id
    assert result.status == "blocked" and result.answer is None
    assert result.sources == []
    assert result.error == "Separate sandbox is unavailable."
