import importlib

from fastapi.testclient import TestClient


def load_app(monkeypatch, **env):
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_version_returns_expected_fields(monkeypatch):
    client = load_app(
        monkeypatch,
        APP_IMAGE_VERSION="sha-a13f92",
        APP_BUILD_SHA="a13f92",
        APP_DEPLOYED_AT="2026-05-18T14:00:00Z",
    )

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "version": "sha-a13f92",
        "commit": "a13f92",
        "deployed_at": "2026-05-18T14:00:00Z",
    }


def test_version_truncates_full_commit_sha(monkeypatch):
    client = load_app(
        monkeypatch,
        APP_IMAGE_VERSION="latest",
        APP_BUILD_SHA="abcdef1234567890abcdef1234567890abcdef12",
        APP_DEPLOYED_AT="2026-05-18T14:00:00Z",
    )

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["commit"] == "abcdef1"


def test_version_defaults_when_env_vars_absent(monkeypatch):
    client = load_app(
        monkeypatch,
        APP_IMAGE_VERSION=None,
        APP_BUILD_SHA=None,
        APP_DEPLOYED_AT=None,
        APP_BUILD_TIMESTAMP=None,
    )

    response = client.get("/version")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "dev"
    assert data["commit"] == "unknown"
    assert data["deployed_at"]
