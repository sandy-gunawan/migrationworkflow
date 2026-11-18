import os

import pytest

from tools.run_maf_baseline import main

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("KPP_RUN_LIVE_TESTS") != "1",
        reason="Set KPP_RUN_LIVE_TESTS=1 for the real local MAF HTTP/corpus tests.",
    ),
]


def test_authenticated_local_maf_service_matches_the_frozen_fifty_native_cases():
    main()
