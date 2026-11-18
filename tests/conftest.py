import json

import pytest

from demo_common.fabric import US_WORKSPACE


@pytest.fixture
def specialist_responses():
    common = {"demo_id": "48254cc6", "synthetic": True}
    cases = {
        "mcp": (
            "kppdemo-mcp", "1", "get_work_orders", "WO001 is open for TRK001.",
            {
                **common,
                "data": [{"order_id": "WO001", "equipment_id": "TRK001"}],
                "sources": [{"kind": "demo_fixture", "id": "urn:kppdemo:maintenance/TRK001"}],
            },
        ),
        "rest_api": (
            "kppdemo-rest", "4", "read_synthetic_stock_api", "MS01 has 18000 litres of DIESEL.",
            {
                **common, "upstream_protocol": "https_rest", "outbound_auth": "managed_identity",
                "data": {
                    "site_id": "MS01", "item_id": "DIESEL", "quantity": 18000, "unit": "litres",
                },
                "sources": [{"kind": "demo_fixture", "id": "urn:kppdemo:stock/MS01/DIESEL"}],
            },
        ),
        "knowledge": (
            "kppdemo-knowledge", "2", "search_synthetic_documents",
            "Copper Ridge MS01: DEMO-COPPER-17, document DMO-DOC-01.",
            {
                "upstream_protocol": "azure_ai_search_rest", "outbound_auth": "managed_identity",
                "documents": [{**common, "id": "DMO-DOC-01", "content": "DEMO-COPPER-17"}],
                "sources": [{"kind": "demo_document", "id": "urn:kppdemo:knowledge/DMO-DOC-01"}],
            },
        ),
        "foundry_iq": (
            "kppdemo-foundry-iq", "2", "retrieve_native_demo_knowledge",
            "Copper Ridge MS01: DEMO-COPPER-17, document DMO-DOC-01.",
            {
                "upstream_protocol": "native_knowledge_base_rest",
                "outbound_auth": "managed_identity", "knowledge_base": "kppdemo-mining-knowledge",
                "result": {"references": [{"docKey": "DMO-DOC-01"}]},
            },
        ),
        "fabric_data": (
            "kppdemo-fabric-data", "1", "DataAgent_kpp_mining_data_us_48254cc6",
            "MS01 produced 1250 tonnes.",
            {
                "response": json.dumps({
                    "status": "success", "site_id": "MS01", "date": "2026-11-01",
                    "shift": "day", "tonnes": 1250, "source_table": "dbo.production",
                }),
                "documents": [{
                    "title": "kpp_mining_data_us_48254cc6",
                    "url": f"https://app.fabric.microsoft.com/groups/{US_WORKSPACE}/aiskills/fixture",
                }],
            },
        ),
    }
    responses = {}
    for route, (name, version, tool, answer, payload) in cases.items():
        binding = {"type": "agent_reference", "name": name, "version": version}
        responses[route] = {
            "id": f"resp_synthetic_{route}", "status": "completed", "agent_reference": binding,
            "output": [
                {
                    "type": "mcp_call", "status": "completed", "agent_reference": binding,
                    "name": tool, "output": json.dumps(payload),
                },
                {
                    "type": "message", "agent_reference": binding,
                    "content": [{"type": "output_text", "text": answer}],
                },
            ],
        }
    return responses
