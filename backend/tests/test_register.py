from app.database import SessionLocal
from app.models import User


def test_register_ok(client):
    r = client.post("/api/register", json={"login": "alice", "password": "Qwerty!123"})
    assert r.status_code == 201
    assert r.json() == {"message": "user создан"}

    db = SessionLocal()
    user = db.query(User).filter(User.login == "alice").first()
    db.close()
    assert user.password_hash.startswith("$argon2id$")
    assert "Qwerty!123" not in user.password_hash


def test_register_duplicate(client):
    client.post("/api/register", json={"login": "alice", "password": "Qwerty!123"})
    r = client.post("/api/register", json={"login": "alice", "password": "Other!1234"})
    assert r.status_code == 409


def test_register_weak_password(client):
    r = client.post("/api/register", json={"login": "bob", "password": "qwerty123"})
    assert r.status_code == 422
    assert "заглавная буква" in r.json()["detail"]
