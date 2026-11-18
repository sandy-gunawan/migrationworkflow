import json
import os
import re
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from azure.identity import AzureCliCredential

from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric
from demo_common.foundry import DemoFoundry, DemoFoundryError
from demo_common.normalization import normalize_source_result

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("KPP_RUN_LIVE_TESTS") != "1",
        reason="Set KPP_RUN_LIVE_TESTS=1 for native Fabric semantic regression tests.",
    ),
]


@pytest.fixture(scope="module")
def native_source():
    source = json.loads((ROOT / "config" / "source-workflow.json").read_text(encoding="utf-8"))
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=300, follow_redirects=False) as client,
    ):
        fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
        with fabric.active_capacity():
            yield source, DemoFoundry(credential, client)


@pytest.mark.parametrize("case_id", ["FAB01", "FAB06"])
def test_native_site_is_not_misread_as_equipment_and_requires_actual_tonnage(
    native_source, case_id
):
    source, foundry = native_source
    corpus = json.loads((ROOT / "tests" / "golden" / "cases.json").read_text(encoding="utf-8"))
    case = next(item for item in corpus["cases"] if item["id"] == case_id)
    target = ROOT / "evidence" / "foundry" / f"fabric-semantic-{case_id}-{int(time.time())}.json"
    try:
        response = foundry.invoke(source["name"], case["question"], source["version"])
    except DemoFoundryError as exc:
        target.write_text(exc.detail + "\n", encoding="utf-8")
        raise
    target.write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
    result = normalize_source_result(response, uuid4(), source)
    assert result.route.value == case["route"]
    assert result.status == "success", result.error
    normalized = re.sub(r"(?<=\d),(?=\d)", "", result.model_dump_json()).upper()
    assert all(fact.upper() in normalized for fact in case["facts"])
    assert set(case["sources"]) <= {item.id for item in result.sources}
