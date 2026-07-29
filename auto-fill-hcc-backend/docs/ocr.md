# OCR API — Hướng dẫn gọi

3 model OCR (chuẩn **OpenAI** `/v1/chat/completions`) + 1 web so sánh, expose public qua **Tailscale Funnel**.

**Base URL (public, gọi từ bất kỳ đâu):**
```
https://spark-abf9.tail0f2e98.ts.net
```

> Trong tailnet (máy đã cài Tailscale) có thể gọi thẳng IP: `http://100.106.147.89:<port>` (8011/8012/8000/8013).
> ⚠️ Funnel là **public, KHÔNG có auth** — ai biết URL đều gọi được. Chỉ dùng cho dev/test.

## Endpoints

| Model | URL | `model` id |
|---|---|---|
| Vintern-1B-v3.5 | `…/vintern/v1/chat/completions` | `Vintern-1B-v3.5` |
| HunyuanOCR | `…/hunyuan/v1/chat/completions` | `HunyuanOCR` |
| Qwen3.6-35B | `…/llm/v1/chat/completions` | `Qwen/Qwen3.6-35B-A3B` |
| Web so sánh (cả 3, có PDF) | `…/ocr/ocr` | (multipart) |

---

## 1) Health
```bash
curl https://spark-abf9.tail0f2e98.ts.net/hunyuan/v1/models
```

## 2) HunyuanOCR — OCR 1 ảnh
```bash
IMG=$(base64 -w0 anh.png)        # macOS: base64 -i anh.png
curl -s https://spark-abf9.tail0f2e98.ts.net/hunyuan/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "HunyuanOCR",
    "messages": [{"role":"user","content":[
      {"type":"image_url","image_url":{"url":"data:image/png;base64,'"$IMG"'"}},
      {"type":"text","text":"Trích xuất toàn bộ văn bản trong ảnh này."}
    ]}],
    "max_tokens": 2048, "temperature": 0
  }' | jq -r '.choices[0].message.content'
```

## 3) Vintern-1B-v3.5 — thêm `repetition_penalty`
```bash
IMG=$(base64 -w0 anh.png)
curl -s https://spark-abf9.tail0f2e98.ts.net/vintern/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Vintern-1B-v3.5",
    "messages": [{"role":"user","content":[
      {"type":"image_url","image_url":{"url":"data:image/png;base64,'"$IMG"'"}},
      {"type":"text","text":"Bạn là máy OCR. Chép lại y nguyên chữ trong ảnh, không bình luận."}
    ]}],
    "max_tokens": 2048, "temperature": 0, "repetition_penalty": 1.1
  }' | jq -r '.choices[0].message.content'
```

## 4) Qwen3.6-35B — nhớ tắt thinking
```bash
IMG=$(base64 -w0 anh.png)
curl -s https://spark-abf9.tail0f2e98.ts.net/llm/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3.6-35B-A3B",
    "messages": [{"role":"user","content":[
      {"type":"image_url","image_url":{"url":"data:image/png;base64,'"$IMG"'"}},
      {"type":"text","text":"Trích xuất toàn bộ văn bản trong ảnh, chỉ xuất text."}
    ]}],
    "max_tokens": 2048, "temperature": 0,
    "chat_template_kwargs": {"enable_thinking": false}
  }' | jq -r '.choices[0].message.content'
```

## 5) Web so sánh — gọi cả 3 cùng lúc, hỗ trợ ảnh & PDF
```bash
curl -s https://spark-abf9.tail0f2e98.ts.net/ocr/ocr \
  -F 'image=@tailieu.pdf' \
  -F 'max_tokens=2048' \
  -F 'config={"selected":["Vintern-1B-v3.5","HunyuanOCR","Qwen3.6-35B"],"prompts":{}}' \
  | jq
```
- Chọn ít model hơn: sửa mảng `selected`.
- Prompt riêng từng model: `"prompts":{"HunyuanOCR":"...","Qwen3.6-35B":"..."}` (bỏ trống = dùng mặc định).
- PDF nhiều trang tự tách từng trang OCR rồi ghép.

---

## Ghi chú
- **Ảnh JPG**: đổi `data:image/png` → `data:image/jpeg`.
- **`max_tokens`**: 2048–4096 cho tài liệu dày; trang rất nhiều chữ tăng thêm.
- **Ảnh qua URL** (thay vì base64): `"image_url":{"url":"https://.../anh.jpg"}`.
- **Lấy mỗi text**: nối ` | jq -r '.choices[0].message.content'`.
- **Python (openai SDK)**: `OpenAI(base_url="https://spark-abf9.tail0f2e98.ts.net/hunyuan/v1", api_key="x")` rồi `client.chat.completions.create(...)`.
