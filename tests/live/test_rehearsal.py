import os
import subprocess
import sys

import pytest


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("KPP_RUN_LIVE_TESTS") != "1", reason="Explicit live opt-in required."
)
def test_actual_native_export_migration_and_nine_live_routes_on_three_paths():
    run_id = os.environ.get("KPP_REHEARSAL_VALIDATED_RUN_ID")
    if not run_id:
        pytest.fail("Validate a fresh rehearsal helper and set KPP_REHEARSAL_VALIDATED_RUN_ID.")
    subprocess.run(
        [sys.executable, "-m", "tools.demo.run_rehearsal", "--run-id", run_id],
        check=True,
    )
