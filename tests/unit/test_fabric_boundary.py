import pytest

from demo_common.fabric import WORKSPACE, require_demo_fabric_path


@pytest.mark.parametrize(
    "path",
    [
        "/workspaces/00000000-0000-0000-0000-000000000001/items",
        f"/workspaces/{WORKSPACE}/../other",
        f"/workspaces/{WORKSPACE}/items?workspace=other",
        f"/workspaces/{WORKSPACE}/dataAgents/x/staging/reset",
        f"/workspaces/{WORKSPACE}/dataAgents/x/staging/datasources/y/fewshots/deleteAll",
        "https://unrelated.example/",
    ],
)
def test_native_fabric_setup_cannot_escape_into_existing_or_destructive_paths(path):
    with pytest.raises(ValueError):
        require_demo_fabric_path(path)
