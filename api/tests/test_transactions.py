from __future__ import annotations

import datetime as dt


def _auth(client):
  client.post("/api/auth/register", json={"email": "u@example.com", "password": "password123"})
  r = client.post("/api/auth/login", json={"email": "u@example.com", "password": "password123"})
  token = r.json()["access_token"]
  return {"Authorization": f"Bearer {token}"}


def test_transactions_crud_and_stats(client):
  headers = _auth(client)

  occurred_at = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.UTC).isoformat()
  r = client.post(
    "/api/transactions",
    headers=headers,
    json={
      "direction": "expense",
      "amount_cents": 1234,
      "currency": "CNY",
      "occurred_at": occurred_at,
      "merchant": "Coffee",
      "note": "latte",
    },
  )
  assert r.status_code == 201
  tx_id = r.json()["id"]

  r2 = client.get("/api/transactions?limit=10&offset=0", headers=headers)
  assert r2.status_code == 200
  assert r2.json()["total"] == 1

  r3 = client.put(f"/api/transactions/{tx_id}", headers=headers, json={"amount_cents": 2000})
  assert r3.status_code == 200
  assert r3.json()["amount_cents"] == 2000

  r4 = client.get("/api/stats/summary?start=2026-01-01&end=2026-01-31", headers=headers)
  assert r4.status_code == 200
  assert r4.json()["expense_cents"] == 2000

  r5 = client.delete(f"/api/transactions/{tx_id}", headers=headers)
  assert r5.status_code == 204

