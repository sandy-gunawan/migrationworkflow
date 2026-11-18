import os

import pytest

from tools.verify_source_workflow import main

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("KPP_RUN_LIVE_TESTS") != "1",
        reason="Set KPP_RUN_LIVE_TESTS=1 explicitly for real owned Azure/Fabric calls.",
    ),
]


def test_native_router_branches_retrieve_real_facts_and_block_unavailable_data():
    main()
