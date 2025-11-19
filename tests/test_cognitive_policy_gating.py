from fastapi.testclient import TestClient

from luki_modules_cognitive.main import app
import luki_modules_cognitive.main as cognitive_main


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
