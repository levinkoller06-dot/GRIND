import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

SECRET = "test-secret-mit-mindestens-32-zeichen!!"
URL = "https://test.supabase.co"


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: Settings(
        supabase_url=URL, supabase_jwt_secret=SECRET
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_token(**overrides) -> str:
    claims = {
        "sub": "user-123",
        "email": "levin@example.com",
        "aud": "authenticated",
        "iss": f"{URL}/auth/v1",
        "exp": int(time.time()) + 3600,
    } | overrides
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_me_ohne_token(client):
    assert client.get("/me").status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 10},
        {"aud": "anon"},
        {"iss": "https://fremd.supabase.co/auth/v1"},
    ],
)
def test_me_ungueltiges_token(client, overrides):
    res = client.get("/me", headers={"Authorization": f"Bearer {make_token(**overrides)}"})
    assert res.status_code == 401


def test_decode_token_gueltig():
    from app.auth import decode_token

    claims = decode_token(make_token(), Settings(supabase_url=URL, supabase_jwt_secret=SECRET))
    assert claims["sub"] == "user-123"


def test_falsche_signatur(client):
    token = jwt.encode(
        {"sub": "x", "aud": "authenticated", "iss": f"{URL}/auth/v1", "exp": int(time.time()) + 60},
        "anderes-secret-mit-mindestens-32-zeichen",
        algorithm="HS256",
    )
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
