import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from demo_common.environment import DemoEnvironment, load_environment

ROOT = Path(__file__).resolve().parents[2]


def test_custom_profile_pins_runtime_calls_to_the_new_environment(tmp_path):
    profile = tmp_path / "runtime.local.json"
    profile.write_bytes((ROOT / "config" / "runtime.public.example.json").read_bytes())
    script = """
import httpx
from pathlib import Path
from azure.core.credentials import AccessToken
from backing_service.upstream import BACKING_URL, SEARCH_URL
from demo_common.endpoints import require_demo_app_url
from demo_common.environment import ENVIRONMENT
from demo_common.fabric import US_CAPACITY, US_WORKSPACE
from demo_common.foundry import DemoFoundry
from demo_common.logicapps import NORMALIZER, build_logic_workflow
from demo_common.migration import compile_source

class Credential:
    def get_token(self, *args):
        return AccessToken('synthetic-unit-fixture', 9999999999)

def handle(request):
    assert str(request.url).startswith(ENVIRONMENT.foundry_endpoint + '/openai/v1/')
    return httpx.Response(200, json={'id': 'conv_custom_fixture'})

with httpx.Client(transport=httpx.MockTransport(handle)) as client:
    native = DemoFoundry(Credential(), client)
    assert native.start_conversation('Synthetic question', 'unit') == 'conv_custom_fixture'
assert BACKING_URL == 'https://example-demo-data.azurewebsites.net'
assert SEARCH_URL == 'https://example-demo-search.search.windows.net'
assert US_WORKSPACE == '00000000-0000-0000-0000-000000000005'
assert '/resourceGroups/example-demo-rg/' in US_CAPACITY
assert NORMALIZER == 'https://example-demo-maf.azurewebsites.net/api/normalize-result'
mapping = compile_source(
    (Path('source') / 'foundry' / 'workflow.yaml').read_text(encoding='utf-8')
)
definition = build_logic_workflow(mapping)
case = definition['actions']['Execute']['actions']['route_question']['cases']['mcp']
assert case['actions']['invoke_mcp']['inputs']['uri'].startswith(
    ENVIRONMENT.foundry_endpoint + '/'
)
assert case['actions']['normalize_mcp']['inputs']['uri'] == NORMALIZER
try:
    require_demo_app_url('https://unrelated.azurewebsites.net', ENVIRONMENT.backing_app)
except ValueError:
    pass
else:
    raise AssertionError('The configured endpoint guard was bypassed.')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "DEMO_ENVIRONMENT_FILE": str(profile)},
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_incomplete_custom_profile_cannot_fall_back_to_original_resources(tmp_path):
    profile = tmp_path / "runtime.local.json"
    profile.write_text('{"resource_group": "new-demo"}', encoding="utf-8")
    with pytest.raises(ValueError, match="must specify every field"):
        load_environment(profile)


def test_invalid_profile_diagnostics_never_echo_unknown_credential_values(tmp_path, caplog):
    profile = tmp_path / "runtime.local.json"
    value = DemoEnvironment().model_dump()
    value["unexpected_credential"] = "synthetic-sensitive-input-do-not-echo"
    profile.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        load_environment(profile)
    assert "unexpected_credential" in str(error.value)
    assert value["unexpected_credential"] not in str(error.value) + caplog.text
