from __future__ import annotations


def test_register_and_login(client):
  r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "password123"})
  assert r.status_code == 200
  user = r.json()
  assert user["email"] == "a@example.com"

  r2 = client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})
  assert r2.status_code == 200
  token = r2.json()["access_token"]
  assert token

  r3 = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
  assert r3.status_code == 200
  assert r3.json()["email"] == "a@example.com"

