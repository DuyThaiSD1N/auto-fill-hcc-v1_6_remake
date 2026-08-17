"""Voice proxy — WS /ws/asr (bridge gRPC ASR) + /ws/tts (relay provider).

Triển khai ở Bước 4 (docs/04-voice-asr-tts.md):
  ws_asr.py — protocol {"type":"start"|"transcript"|"stop"} + binary PCM S16LE 16k
  ws_tts.py — relay text→audio base64 PCM, giọng settings.tts_voice
  router.py — GET /api/v1/voice/config (asr/tts bật/tắt theo env)
"""
