from fastapi.testclient import TestClient
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import luki_modules_cognitive.main as cognitive_main

app = cognitive_main.app


def test_recommendations_blocked_when_policy_denies(monkeypatch) -> None:
    async def fake_enforce_cognitive_policy(user_id: str, requested_scopes=None, context=None):  # type: ignore[override]
        return {"allowed": False, "error": "consent_denied"}

    monkeypatch.setattr(cognitive_main, "_enforce_cognitive_policy", fake_enforce_cognitive_policy)

    client = TestClient(app)
    response = client.post("/recommendations", json={"user_id": "test_user"})

    assert response.status_code == 403
    data = response.json()
    assert isinstance(data.get("detail"), dict)
    assert data["detail"].get("error") == "consent_denied"
