import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from starlette.datastructures import Headers

from demo_common.auth import Authorizer, AuthSettings

TENANT = "020201e2-0ae9-446c-8981-55a2bdecc00d"
AUDIENCE = "551b356f-3265-4a3e-8b87-95704b5f503c"
CALLER = "50d57e04-3ed5-4123-bf9f-e3a8739009c9"


@pytest.fixture(scope="module")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(signing_key, **overrides):
    now = int(time.time())
    claims = {
        "tid": TENANT,
        "oid": CALLER,
        "aud": AUDIENCE,
        "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return jwt.encode(claims, signing_key, algorithm="RS256")


def test_valid_token_still_requires_the_demo_caller_allowlist(signing_key):
    settings = AuthSettings(TENANT, AUDIENCE, frozenset({CALLER}))
    authorizer = Authorizer(settings, lambda _: signing_key.public_key())
    assert (
        authorizer.authorize(Headers({"authorization": f"Bearer {token(signing_key)}"})) == CALLER
    )
    unauthorized = token(signing_key, oid="00000000-0000-0000-0000-000000000001")
    with pytest.raises(HTTPException) as error:
        authorizer.authorize(Headers({"authorization": f"Bearer {unauthorized}"}))
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    "override",
    [
        {"aud": "00000000-0000-0000-0000-000000000002"},
        {"exp": 1},
        {"tid": "00000000-0000-0000-0000-000000000003"},
    ],
)
def test_invalid_scope_or_expired_token_is_rejected(signing_key, override):
    authorizer = Authorizer(
        AuthSettings(TENANT, AUDIENCE, frozenset({CALLER})),
        lambda _: signing_key.public_key(),
    )
    with pytest.raises(HTTPException) as error:
        authorizer.authorize(Headers({"authorization": f"Bearer {token(signing_key, **override)}"}))
    assert error.value.status_code == 401


def test_empty_allowlist_is_a_configuration_error():
    with pytest.raises(ValueError, match="allowlist"):
        AuthSettings(TENANT, AUDIENCE, frozenset())
