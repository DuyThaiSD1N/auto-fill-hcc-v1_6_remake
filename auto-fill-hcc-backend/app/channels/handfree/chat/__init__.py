"""Não hội thoại toàn trình — POST /api/v1/assistant/chat.

Triển khai ở Bước 3 (docs/03-chat-orchestrator.md + docs/03a-thiet-ke-phien-hoi-thoai.md):
  router.py  — endpoint assistant/chat + conversations/{id}
  flow.py    — state machine 8 bước (tất định, LLM không quyết flow)
  intents.py — LLM hiểu ý định trong ngữ cảnh state
  store.py   — conversation store Mongo TTL 24h
  script_vi.py — lời thoại tiếng Việt (tách khỏi logic)
"""
