# API LLM (Qwen / vLLM) — Tài liệu tích hợp

Tài liệu mô tả API LLM đang dùng cho các agent trích xuất (compact agent, reasoning, planner đính kèm).
Nguồn code: [`app/services/llm/client.py`](../app/services/llm/client.py), cấu hình [`app/config.py`](../app/config.py).

---

## 1. Tổng quan

Hệ thống dùng **2 tầng LLM**, tự động fallback:

| Tầng | Provider | Khi dùng |
|------|----------|----------|
| **Primary** | vLLM chạy model **Qwen** (OpenAI-compatible API) | Mặc định mọi request |
| **Fallback** | OpenAI (`chat.completions`) | Chỉ khi primary lỗi **và** có `OPENAI_API_KEY` |

- Primary và fallback dùng CHUNG định dạng messages (OpenAI chat format) → prompt không phải viết lại.
- Nếu primary lỗi mà **không** cấu hình `OPENAI_API_KEY` → ném lỗi gốc (không có fallback).

---

## 2. Endpoint (Primary — Qwen/vLLM)

```
POST {LLM_BASE_URL}/v1/chat/completions
```

- `LLM_BASE_URL`:
  - **Đang chạy (từ `.env`)**: `https://spark-abf9.tail0f2e98.ts.net/llm` → endpoint đầy đủ
    `https://spark-abf9.tail0f2e98.ts.net/llm/v1/chat/completions`.
  - Mặc định trong code (`config.py`, khi không có `.env`): `https://spark-abf9.tail0f2e98.ts.net:8443`.
  - `.env` **ghi đè** default → luôn dùng giá trị `.env`. Code tự `rstrip("/")` rồi nối `/v1/chat/completions`.
- **Không có header Authorization** (server nội bộ qua Tailscale, không đặt API key).
- **`verify=False`**: bỏ qua kiểm chứng chứng chỉ TLS (self-signed / Tailscale cert).
- Timeout: `LLM_TIMEOUT_MS` (mặc định 60000ms = 60s).
- Chuẩn OpenAI-compatible (`/v1/chat/completions`) nên có thể test bằng bất kỳ client OpenAI nào bằng cách đổi `base_url`.

---

## 3. Request

### 3.1. Body (JSON)

```json
{
  "model": "Qwen/Qwen3.6-35B-A3B",
  "messages": [
    { "role": "system", "content": "<system prompt: schema + rules>" },
    { "role": "user",   "content": "<nội dung OCR các tài liệu>" }
  ],
  "temperature": 0.1,
  "max_tokens": 1500,
  "stream": false,
  "chat_template_kwargs": { "enable_thinking": false }
}
```

### 3.2. Mô tả các trường

| Trường | Kiểu | Mặc định | Ý nghĩa |
|--------|------|----------|---------|
| `model` | string | `Qwen/Qwen3.6-35B-A3B` (`LLM_MODEL`) | Tên model trên vLLM. |
| `messages` | array | — | Danh sách message chuẩn OpenAI (`role` ∈ `system`/`user`/`assistant`, `content` là chuỗi). Agent gửi 1 `system` (schema + rules) + 1 `user` (OCR text). |
| `temperature` | float | `0.1` (`LLM_TEMPERATURE`) | Độ ngẫu nhiên. Để thấp cho trích xuất ổn định. |
| `max_tokens` | int | `1500` (`LLM_MAX_TOKENS`) | Giới hạn token output. Runner compact agent có thể override (vd token lớn hơn cho nhiều trang). |
| `stream` | bool | `false` | Không stream — đọc trọn 1 lần. |
| `chat_template_kwargs.enable_thinking` | bool | `false` | **Đặc thù Qwen3**: bật/tắt chế độ "suy nghĩ". `false` = trả thẳng đáp án (nhanh). Xem §5. |

> Ghi chú: `temperature`/`max_tokens` nếu truyền `None` vào `client.chat(...)` sẽ lấy giá trị từ config.

---

## 4. Response

Chuẩn OpenAI chat completion:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "Qwen/Qwen3.6-35B-A3B",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "```json\n{ \"fields\": { ... } }\n```" },
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 }
}
```

- Code lấy: `data["choices"][0]["message"]["content"]`.
- Content **rỗng** → ném lỗi `LLM primary trả content rỗng` (kích hoạt fallback).
- HTTP ≥ 400 → ném `LLM HTTP <status>: <body>` (kích hoạt fallback).

### 4.1. Trích JSON từ content (`extract_json_block`)

Content thường là JSON (đôi khi bọc trong ```` ```json ```` hoặc kèm `<think>`). Thứ tự xử lý:

1. Bỏ mọi khối `<think>...</think>` (khi bật reasoning).
2. Ưu tiên block ```` ```json ... ``` ````.
3. Fallback: cặp `{...}` đầu tiên trong text.
4. Không thấy JSON → ném `ValueError`.

---

## 5. Reasoning / `enable_thinking` (Qwen3)

- Bật bằng config `AGENT_REASONING=true` (`settings.agent_reasoning`) → truyền `enable_thinking=true`.
- Khi bật, model có thể trả kèm khối `<think>...</think>` — `extract_json_block` **tự bóc bỏ** trước khi parse JSON.
- Mặc định **tắt** (`false`) cho nhanh; chỉ bật khi cần lý luận sâu.

---

## 6. Fallback OpenAI

Khi primary lỗi (HTTP ≥400, timeout, content rỗng, cert...) và có `OPENAI_API_KEY`:

```python
client.chat.completions.create(
    model=OPENAI_MODEL,            # vd "gpt-5.4-mini"
    messages=messages,            # dùng lại y nguyên
    temperature=temperature,
    response_format={"type": "json_object"},  # ép JSON object cho ổn định
)
```

- Fallback **ép** `response_format=json_object` (primary Qwen không ép, dựa vào prompt + `extract_json_block`).
- OpenAI client khởi tạo **lazy** (chỉ tạo khi cần) → không bắt buộc có key nếu chỉ dùng Qwen.

---

## 7. Biến môi trường (`.env`)

| Biến | Mặc định | Ghi chú |
|------|----------|---------|
| `LLM_BASE_URL` | `.env`: `https://spark-abf9.tail0f2e98.ts.net/llm` (default code: `...:8443`) | URL gốc vLLM (không kèm `/v1/...`). |
| `LLM_MODEL` | `Qwen/Qwen3.6-35B-A3B` | Tên model trên vLLM. |
| `LLM_TIMEOUT_MS` | `60000` | Timeout request (ms). |
| `LLM_TEMPERATURE` | `0.1` | Nhiệt độ mặc định. |
| `LLM_MAX_TOKENS` | `1500` | Giới hạn output mặc định. |
| `AGENT_REASONING` | `false` | Bật `enable_thinking` cho agent map. |
| `LLM_DEBUG` | `false` | Log chi tiết (model, độ dài, 1500 ký tự đầu content). |
| `OPENAI_API_KEY` | *(trống)* | **Bí mật — KHÔNG commit.** Trống = tắt fallback. |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Model fallback OpenAI. |

> ⚠️ **Không commit `OPENAI_API_KEY` (và bất kỳ khóa bí mật nào) vào git.**

---

## 8. Ví dụ gọi thủ công

### 8.1. `curl` (primary Qwen)

```bash
curl -sk "https://spark-abf9.tail0f2e98.ts.net/llm/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3.6-35B-A3B",
    "messages": [
      {"role":"system","content":"Trả về JSON {\"ok\":true}."},
      {"role":"user","content":"ping"}
    ],
    "temperature": 0.1,
    "max_tokens": 100,
    "stream": false,
    "chat_template_kwargs": {"enable_thinking": false}
  }'
```

> `-k` tương ứng `verify=False` (bỏ qua kiểm chứng TLS).

### 8.2. Python (dùng client trong repo)

```python
from app.services.llm import client

messages = [
    {"role": "system", "content": "Trả về JSON object với khóa 'fields'."},
    {"role": "user", "content": "Nội dung OCR ..."},
]

raw = await client.chat(messages, temperature=0.1, max_tokens=1500, enable_thinking=False)
data = client.extract_json_block(raw)   # dict Python
```

### 8.3. Python (OpenAI SDK trỏ vào vLLM)

```python
from openai import OpenAI

llm = OpenAI(base_url="https://spark-abf9.tail0f2e98.ts.net/llm/v1", api_key="not-needed")
resp = llm.chat.completions.create(
    model="Qwen/Qwen3.6-35B-A3B",
    messages=[{"role": "user", "content": "ping"}],
    temperature=0.1,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
print(resp.choices[0].message.content)
```

---

## 9. Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Xử lý |
|-------------|-------------|-------|
| `LLM HTTP 4xx/5xx` | vLLM lỗi / sai model / quá tải | Kiểm tra server vLLM; bật `LLM_DEBUG`; sẽ tự fallback OpenAI nếu có key. |
| `LLM primary trả content rỗng` | Model trả rỗng (thường do prompt/thinking) | Kiểm tra prompt; fallback tự chạy. |
| Timeout | Mạng Tailscale / model chậm | Tăng `LLM_TIMEOUT_MS`. |
| `Không tìm thấy JSON trong response` | Content không phải JSON | Siết prompt yêu cầu JSON; kiểm tra `<think>` chưa tắt. |
| Cert / SSL | Self-signed | Đã dùng `verify=False` (curl `-k`). |
| Không fallback dù primary lỗi | Thiếu `OPENAI_API_KEY` | Đặt key hoặc chấp nhận lỗi gốc. |
