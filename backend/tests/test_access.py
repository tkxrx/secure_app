PASSWORD = "Qwerty!123"


def login_as(client, login):
    client.post("/api/register", json={"login": login, "password": PASSWORD})
    r = client.post("/api/login", json={"login": login, "password": PASSWORD})
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_access_allowed_after_grant(client):
    alice = login_as(client, "alice")
    bob = login_as(client, "bob")
    rid = client.post("/api/resources", json={"title": "doc", "content": "secret"}, headers=alice).json()["id"]

    r = client.post(f"/api/resources/{rid}/permissions", json={"login": "bob", "can_read": True}, headers=alice)
    assert r.status_code == 200

    r = client.get(f"/api/resources/{rid}", headers=bob)
    assert r.status_code == 200
    assert r.json()["content"] == "secret"


def test_access_denied_without_permission(client):
    alice = login_as(client, "alice")
    eve = login_as(client, "eve")
    rid = client.post("/api/resources", json={"title": "doc", "content": "secret"}, headers=alice).json()["id"]

    assert client.get(f"/api/resources/{rid}", headers=eve).status_code == 403
    assert client.put(f"/api/resources/{rid}", json={"content": "x"}, headers=eve).status_code == 403
    assert client.delete(f"/api/resources/{rid}", headers=eve).status_code == 403


def test_read_permission_does_not_allow_delete(client):
    alice = login_as(client, "alice")
    bob = login_as(client, "bob")
    rid = client.post("/api/resources", json={"title": "doc"}, headers=alice).json()["id"]
    client.post(f"/api/resources/{rid}/permissions", json={"login": "bob", "can_read": True}, headers=alice)

    assert client.delete(f"/api/resources/{rid}", headers=bob).status_code == 403


def test_only_owner_can_grant(client):
    alice = login_as(client, "alice")
    bob = login_as(client, "bob")
    login_as(client, "eve")
    rid = client.post("/api/resources", json={"title": "doc"}, headers=alice).json()["id"]

    r = client.post(f"/api/resources/{rid}/permissions", json={"login": "eve", "can_read": True}, headers=bob)
    assert r.status_code == 403
