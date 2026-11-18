import os
import subprocess
import sys

import pytest


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("KPP_RUN_LIVE_TESTS") != "1", reason="Explicit live opt-in required."
)
def test_original50_on_actual_logic_apps_with_native_action_history():
    run_id = os.environ.get("KPP_LOGIC_VALIDATED_RUN_ID")
    if not run_id:
        pytest.fail("Validate a fresh owned job, then set KPP_LOGIC_VALIDATED_RUN_ID.")
    subprocess.run(
        [
            sys.executable, "-m", "tools.run_azure_job", "--mode", "verify-logic",
            "--run-id", run_id,
        ],
        check=True,
    )
