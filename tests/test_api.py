def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_chat_returns_session(client):
    r = client.post("/chat", json={"message": "What are your support hours?"})
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] and "Monday to Friday" in body["reply"]
    assert body["sources"][0]["doc"] == "support"


def test_chat_validates_empty_message(client):
    assert client.post("/chat", json={"message": ""}).status_code == 422
