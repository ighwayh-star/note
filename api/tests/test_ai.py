from __future__ import annotations

import datetime as dt


def _auth(client):
  client.post("/api/auth/register", json={"email": "ai@example.com", "password": "password123"})
  r = client.post("/api/auth/login", json={"email": "ai@example.com", "password": "password123"})
  token = r.json()["access_token"]
  return {"Authorization": f"Bearer {token}"}


def test_ai_chat_summary_rule(client):
  headers = _auth(client)

  occurred_at = dt.datetime(2026, 1, 10, 12, 0, tzinfo=dt.UTC).isoformat()
  r = client.post(
    "/api/transactions",
    headers=headers,
    json={
      "direction": "expense",
      "amount_cents": 3000,
      "currency": "CNY",
      "occurred_at": occurred_at,
      "merchant": "Lunch",
      "note": "noodles",
    },
  )
  assert r.status_code == 201

  r2 = client.post("/api/ai/chat", headers=headers, json={"message": "2026-01-01 到 2026-01-31 支出多少"})
  assert r2.status_code == 200
  data = r2.json()
  assert data["mode"] == "rule"
  assert data["cards"][0]["type"] == "stats_summary"
  assert data["cards"][0]["expense_cents"] == 3000


def test_ai_chat_by_category_rule(client):
  headers = _auth(client)

  occurred_at = dt.datetime(2026, 1, 10, 12, 0, tzinfo=dt.UTC).isoformat()
  r = client.post(
    "/api/transactions",
    headers=headers,
    json={
      "direction": "expense",
      "amount_cents": 1200,
      "currency": "CNY",
      "occurred_at": occurred_at,
      "merchant": "Coffee",
      "note": "latte",
    },
  )
  assert r.status_code == 201

  r2 = client.post("/api/ai/chat", headers=headers, json={"message": "2026-01-01 到 2026-01-31 按分类统计"})
  assert r2.status_code == 200
  data = r2.json()
  assert data["cards"][0]["type"] == "stats_by_category"
  assert data["cards"][0]["direction"] == "expense"


def test_ai_write_propose_and_confirm_rule(client):
  headers = _auth(client)

  r = client.post("/api/ai/chat", headers=headers, json={"message": "新增支出 12.34"})
  assert r.status_code == 200
  data = r.json()
  assert data["mode"] == "rule"
  assert len(data["proposed_actions"]) == 1
  assert data["proposed_actions"][0]["payload"]["fields"]["merchant"] is None
  assert data["proposed_actions"][0]["payload"]["fields"]["occurred_at"] is None
  action_id = data["proposed_actions"][0]["id"]
  assert data["proposed_actions"][0]["kind"] == "transaction_create"

  r2 = client.post("/api/ai/confirm", headers=headers, json={"action_id": action_id})
  assert r2.status_code == 200
  out = r2.json()
  assert out["ok"] is True

  r3 = client.get("/api/transactions?limit=10&offset=0", headers=headers)
  assert r3.status_code == 200
  assert r3.json()["total"] == 1

  r4 = client.post("/api/ai/undo-last", headers=headers)
  assert r4.status_code == 200
  r5 = client.get("/api/transactions?limit=10&offset=0", headers=headers)
  assert r5.status_code == 200
  assert r5.json()["total"] == 0


def test_ai_write_natural_language_time_and_merchant(client):
  headers = _auth(client)

  r = client.post("/api/ai/chat", headers=headers, json={"message": "我今天下午四点在肯德基花了50元，帮我添加一下"})
  assert r.status_code == 200
  data = r.json()
  assert len(data["proposed_actions"]) == 1
  action_id = data["proposed_actions"][0]["id"]

  r2 = client.post("/api/ai/confirm", headers=headers, json={"action_id": action_id})
  assert r2.status_code == 200

  r3 = client.get("/api/transactions?limit=10&offset=0", headers=headers)
  assert r3.status_code == 200
  assert r3.json()["total"] == 1
  assert r3.json()["items"][0]["amount_cents"] == 5000


def test_ai_memory_conversation_id_keeps_context(client):
  headers = _auth(client)

  r1 = client.post("/api/ai/chat", headers=headers, json={"message": "我在肯德基花了50元"})
  assert r1.status_code == 200
  d1 = r1.json()
  cid = d1["conversation_id"]
  assert cid
  assert len(d1["proposed_actions"]) == 1

  r2 = client.post("/api/ai/chat", headers=headers, json={"message": "帮我添加一下", "conversation_id": cid})
  assert r2.status_code == 200
  d2 = r2.json()
  assert d2["conversation_id"] == cid


def test_ai_category_create_propose_and_confirm(client):
  headers = _auth(client)

  r = client.post("/api/ai/chat", headers=headers, json={"message": "新增分类 餐饮"})
  assert r.status_code == 200
  data = r.json()
  assert len(data["proposed_actions"]) == 1
  assert data["proposed_actions"][0]["kind"] == "category_create"
  action_id = data["proposed_actions"][0]["id"]

  r2 = client.post("/api/ai/confirm", headers=headers, json={"action_id": action_id})
  assert r2.status_code == 200
  out = r2.json()
  assert out["ok"] is True
  assert out["entity_id"] is not None

  r3 = client.get("/api/categories", headers=headers)
  assert r3.status_code == 200
  names = [c["name"] for c in r3.json()]
  assert "餐饮" in names


def test_ai_classify_by_category_name_without_tx_id(client):
  headers = _auth(client)

  cat = client.post("/api/categories", headers=headers, json={"name": "餐饮", "type": "expense"})
  assert cat.status_code == 201
  cat_id = cat.json()["id"]

  occurred_at = dt.datetime(2026, 4, 2, 15, 0, tzinfo=dt.UTC).isoformat()
  tx = client.post(
    "/api/transactions",
    headers=headers,
    json={
      "direction": "expense",
      "amount_cents": 5000,
      "currency": "CNY",
      "occurred_at": occurred_at,
      "merchant": "肯德基",
      "note": "",
    },
  )
  assert tx.status_code == 201
  tx_id = tx.json()["id"]

  r = client.post("/api/ai/chat", headers=headers, json={"message": "帮我把那笔肯德基的消费归类到餐饮里"})
  assert r.status_code == 200
  data = r.json()
  assert len(data["proposed_actions"]) == 1
  assert data["proposed_actions"][0]["kind"] == "transaction_update"
  action_id = data["proposed_actions"][0]["id"]

  r2 = client.post("/api/ai/confirm", headers=headers, json={"action_id": action_id})
  assert r2.status_code == 200

  r3 = client.get(f"/api/transactions?limit=10&offset=0", headers=headers)
  assert r3.status_code == 200
  assert r3.json()["items"][0]["id"] == tx_id
  assert r3.json()["items"][0]["category_id"] == cat_id


def test_ai_classify_under_zhong_phrase(client):
  headers = _auth(client)

  cat = client.post("/api/categories", headers=headers, json={"name": "餐饮", "type": "expense"})
  assert cat.status_code == 201

  occurred_at = dt.datetime(2026, 4, 2, 15, 0, tzinfo=dt.UTC).isoformat()
  tx = client.post(
    "/api/transactions",
    headers=headers,
    json={
      "direction": "expense",
      "amount_cents": 5000,
      "currency": "CNY",
      "occurred_at": occurred_at,
      "merchant": "肯德基",
      "note": "",
    },
  )
  assert tx.status_code == 201

  r = client.post("/api/ai/chat", headers=headers, json={"message": "帮我把下午肯德基那笔消费归类到餐饮当中去"})
  assert r.status_code == 200
  data = r.json()
  assert len(data["proposed_actions"]) == 1


def test_ai_category_create_and_assign(client):
  headers = _auth(client)

  occurred_at = dt.datetime(2026, 4, 2, 15, 0, tzinfo=dt.UTC).isoformat()
  tx = client.post(
    "/api/transactions",
    headers=headers,
    json={
      "direction": "expense",
      "amount_cents": 5000,
      "currency": "CNY",
      "occurred_at": occurred_at,
      "merchant": "肯德基",
      "note": "",
    },
  )
  assert tx.status_code == 201
  tx_id = tx.json()["id"]

  r = client.post("/api/ai/chat", headers=headers, json={"message": f"新建分类 餐饮 然后把交易ID {tx_id} 加进去"})
  assert r.status_code == 200
  data = r.json()
  assert len(data["proposed_actions"]) == 1
  assert data["proposed_actions"][0]["kind"] == "category_create_and_assign"
  action_id = data["proposed_actions"][0]["id"]

  r2 = client.post("/api/ai/confirm", headers=headers, json={"action_id": action_id})
  assert r2.status_code == 200
  out = r2.json()
  assert out["ok"] is True
  cat_id = out["entity_id"]
  assert cat_id is not None

  r3 = client.get("/api/transactions?limit=10&offset=0", headers=headers)
  assert r3.status_code == 200
  assert r3.json()["items"][0]["id"] == tx_id
  assert r3.json()["items"][0]["category_id"] == cat_id


def test_ai_create_category_typed_phrase(client):
  headers = _auth(client)

  r = client.post("/api/ai/chat", headers=headers, json={"message": "帮我新建支出分类 股票"})
  assert r.status_code == 200
  data = r.json()
  assert len(data["proposed_actions"]) == 1
  assert data["proposed_actions"][0]["kind"] in ["category_create", "category_create_and_assign"]


def test_ai_text_confirm_last_action(client):
  headers = _auth(client)

  r1 = client.post("/api/ai/chat", headers=headers, json={"message": "新增分类 餐饮"})
  assert r1.status_code == 200
  data1 = r1.json()
  assert len(data1["proposed_actions"]) == 1

  r2 = client.post(
    "/api/ai/chat",
    headers=headers,
    json={"message": "确认", "conversation_id": data1["conversation_id"]},
  )
  assert r2.status_code == 200
  assert "已为你执行上一条提案" in r2.json()["reply"]
