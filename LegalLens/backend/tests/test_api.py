def test_health_includes_request_id(client):
    response = client.get("/health", headers={"X-Request-ID": "ci-check-1"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "ci-check-1"


def test_conversation_create_update_and_read(client):
    created = client.post("/api/v1/conversations", json={"title": "Initial review"})

    assert created.status_code == 201
    conversation_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/conversations/{conversation_id}",
        json={"title": "Updated review", "jurisdiction": "California"},
    )

    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated review"
    assert updated.json()["jurisdiction"] == "California"

    detail = client.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.status_code == 200
    assert detail.json()["messages"] == []


def test_invalid_request_returns_consistent_validation_error(client):
    response = client.post("/api/v1/conversations", json={"title": "", "extra": True})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert body["error"]["details"]


def test_missing_conversation_returns_not_found(client):
    response = client.get("/api/v1/conversations/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
