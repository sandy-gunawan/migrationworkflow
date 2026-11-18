import os

import pytest

from tools.run_source_baseline import main

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("KPP_RUN_LIVE_TESTS") != "1",
        reason="Set KPP_RUN_LIVE_TESTS=1 explicitly for the real 50-case source baseline.",
    ),
]


def test_fifty_native_cases_preserve_facts_sources_and_explicit_unavailable_routes():
    main()
