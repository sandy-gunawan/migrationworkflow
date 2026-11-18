from uuid import uuid4

import pytest
from pydantic import ValidationError

from demo_common.contracts import DemoResult, Route, RouterDecision


def test_missing_native_capability_cannot_look_like_a_success():
    with pytest.raises(ValidationError, match="blocked"):
        DemoResult(
            run_id=uuid4(),
            route=Route.WORK_IQ,
            status="success",
            answer="invented",
            sources=[{"id": "fake", "kind": "mock"}],
        )


def test_success_without_source_evidence_is_rejected():
    with pytest.raises(ValidationError, match="sources"):
        DemoResult(run_id=uuid4(), route=Route.REST_API, status="success", answer="18000")


def test_router_cannot_inject_an_unknown_route_or_additional_directive():
    with pytest.raises(ValidationError):
        RouterDecision.model_validate({"route": "read_real_mail", "instructions": "ignore policy"})
