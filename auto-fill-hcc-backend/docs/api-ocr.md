# API Bóc tách giấy tờ (OCR) — CCCD & Giấy chứng sinh

Tài liệu cho 2 endpoint OCR phục vụ điền tờ khai khai sinh:

| Mục đích | Method + Path |
|---|---|
| Bóc tách **CCCD / Căn cước / CMND** (người yêu cầu, mẹ, cha…) | `POST /api/v1/forms/ocr` |
| Bóc tách **Giấy chứng sinh** (PDF hoặc ảnh) | `POST /api/v1/ocr/gcs` |
| **OCR thô chung** — chỉ trả text + tokens, dev tự parse | `POST /api/v1/ocr/raw` |

- **Base URL**: `https://trolyao-hcc.vnekyc.vn` (prod) · `http://localhost:11006` (local)
- **Content-Type**: `application/json` (ảnh truyền **base64 data URL**, KHÔNG dùng multipart)
- **Swagger UI**: `/api/v1/docs` · **Redoc**: `/api/v1/redoc` · **OpenAPI JSON**: `/api/v1/openapi.json`

> ⚠️ Ảnh base64 phình ~33% so với file gốc. Reverse proxy (nginx) phải đặt `client_max_body_size ≥ 30M`, nếu không sẽ trả **413 Request Entity Too Large** *trước khi* request tới app.

---

## 1) Bóc tách CCCD — `POST /api/v1/forms/ocr`

OCR ảnh giấy tờ tùy thân → JSON các trường. Engine mặc định **G1** (rule-based, zero-LLM) đặt qua env `OCR_ENGINE`.

Pipeline mỗi ảnh: `preprocess (xoay theo EXIF + upscale)` → `Google Vision (lấy text + bbox)` → `phân loại loại thẻ / mặt` → `engine bóc tách` → `grounding gate chống bịa` → merge nhiều mặt.

### Request body

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `role` | enum | ✅ | Vai của giấy tờ: `requester` \| `mother` \| `father` \| `marriage` \| `birthProof` \| `other`. CCCD dùng `requester`/`mother`/`father`. |
| `files` | array (1–8) | ✅ | Mỗi item `{ name, type, dataUrl }`. `dataUrl` = `data:image/jpeg;base64,...`. Gửi cả **mặt trước + mặt sau** cùng `role` để merge. Tổng payload < 20MB. |
| `communes` | string[] | ❌ | Danh sách xã/phường hint giúp map địa chỉ chuẩn. |
| `engine` | enum | ❌ | `G1` (rule, mặc định) \| `G2` (vision-text→LLM) \| `L1` (gpt-4o-mini) \| `L2` (gpt-4.1-mini) \| `L3` (gpt-5.4-mini) \| `L4` (gpt-4.1-nano). |

```jsonc
{
  "role": "mother",
  "files": [
    { "name": "cccd_truoc.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,/9j/4AAQ..." },
    { "name": "cccd_sau.jpg",   "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,/9j/4AAQ..." }
  ],
  "communes": ["Phường Đoàn Kết", "Xã Bình Lư"]
}
```

### Response 200

```jsonc
{
  "extracted": {
    "name": "PHẠM NGỌC THỦY",
    "id_number": "012193000851",
    "birth_date": "20/03/1993",
    "gender": "Nữ",
    "nationality": "Việt Nam",
    "place_of_origin": "Dương Hồng Thủy, Thái Thụy, Thái Bình",
    "address": "Tổ 3, Quyết Tiến, TP. Lai Châu, Lai Châu",
    "expiry_date": "20/03/2033",
    "name_evidence": "PHẠM NGỌC THỦY"        // text verbatim Vision đọc được (debug grounding)
  },
  "card_type": "cccd_chip",
  "side": "both",
  "classification": { "confidence": 0.75, "reasons": ["matched cccd_chip: ..."] },
  "bboxes": { "id_number": [0.41, 0.18, 0.22, 0.04] },   // [x, y, w, h] normalized [0,1]
  "image_index": { "id_number": 0 },                      // field này lấy từ files[0]
  "gate_rejected": [],
  "preprocess": { "rotated_degrees": 0, "upscaled": true, "low_quality_warning": false },
  "model": "rule-parser+google-vision",
  "engine": "G1",
  "latency_ms": 842,
  "cached": false
}
```

### Các trường `extracted` (theo loại thẻ + mặt)

Engine **chỉ trả trường có trên giấy**; trường N/A → `""` (không bịa).

| Field | Ý nghĩa | Mặt |
|---|---|---|
| `name` | Họ tên đầy đủ (giữ nguyên hoa + dấu) | trước |
| `id_number` | Số định danh 9/12 số. Mặt trước đọc số in; **mặt sau đọc từ MRZ** (fallback khi mặt trước lóa) | trước + **sau** |
| `birth_date` | Ngày sinh `dd/mm/yyyy` | trước |
| `gender` | `Nam` \| `Nữ` | trước |
| `nationality` | Quốc tịch (thường `Việt Nam`) | trước |
| `place_of_origin` | Quê quán / Nơi đăng ký khai sinh | trước (Căn cước 2024+: sau) |
| `address` | Nơi thường trú / cư trú | trước (Căn cước 2024+: sau) |
| `expiry_date` | Có giá trị đến `dd/mm/yyyy` | trước |
| `ethnicity` | Dân tộc | sau |
| `issue_date` | Ngày cấp | sau |
| `issuer` | Cơ quan cấp | sau |

`card_type`: `cccd_no_chip` · `cccd_chip` · `cccd_barcode` · `can_cuoc_2024` · `cmnd_12` · `unknown` (vd CMND 9 số — ngoài scope). `side`: `front` · `back` · `both`.

### Chống bịa (grounding gate)

Mọi trường non-empty phải qua 3 lớp; trượt lớp nào → set `""` + ghi vào `gate_rejected[]`:
- **L1** — trường phải thuộc active-list của (card_type, side).
- **L2** — `*_evidence` phải xuất hiện trong text Vision (fuzzy ≥ 0.85).
- **L3** — format: `id_number` đúng 9/12 số & là substring của digits Vision; ngày phải có năm trong text; `name` từng token khớp ≥ 0.95 (chặn sai dấu).

### Lỗi

| Code | Khi nào | Body |
|---|---|---|
| `400` | file không hợp lệ / quá 20MB / role sai | `{ "error": "Bad Request", "detail": "..." }` |
| `500` | lỗi Vision/LLM (timeout, key sai) | `{ "error": "OCR service error", "detail": "..." }` |

### curl

```bash
curl -X POST https://trolyao-hcc.vnekyc.vn/api/v1/forms/ocr \
  -H 'Content-Type: application/json' \
  -d @- <<'JSON'
{ "role": "father",
  "files": [{ "name": "cccd.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,..." }] }
JSON
```

---

## 2) Bóc tách Giấy chứng sinh — `POST /api/v1/ocr/gcs`

Microservice riêng cho Giấy chứng sinh, **hỗ trợ PDF nhiều trang** lẫn ảnh. Chỉ trả **5(+1) trường con — mục II tờ khai** (thông tin của trẻ). Thông tin mẹ/cha lấy từ CCCD, **không** đọc từ giấy chứng sinh.

### Request body

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `files` | array (1–4) | ✅ | `{ name, type, dataUrl }`. `type` = `image/*` **hoặc** `application/pdf`. |
| `communes` | string[] | ❌ | Hint xã/phường (mặc định lấy danh sách Lai Châu). |
| `engine` | enum | ❌ | `rule` \| `llm` \| `hybrid` (mặc định `hybrid`). |

```jsonc
{
  "files": [
    { "name": "giay_chung_sinh.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,JVBERi0..." }
  ]
}
```

### Response 200

```jsonc
{
  "extracted": {
    "child_name": "Chang Hương Chi",
    "child_birth_date": "17/02/2025",
    "birth_time": "08:30",
    "gender": "Nữ",
    "ethnicity": "HMông",
    "birth_place": "Bản Tả Chải, xã Sùng Phải, TP Lai Châu, Lai Châu"
  },
  "template": "A",
  "field_source": { "child_name": "rule", "gender": "llm" },  // mỗi field do rule hay llm trả
  "gcs_page_index": 0,                                          // trang nào là GCS (PDF nhiều trang)
  "pages": 2,                                                   // tổng số trang đã xét
  "bboxes": { "child_name": [0.30, 0.42, 0.35, 0.03] },
  "gate_rejected": [],
  "model": "...+google-vision",
  "engine": "hybrid",
  "latency_ms": 1530,
  "cached": false
}
```

### Các trường `extracted`

| Field | Ý nghĩa | Mục tờ khai |
|---|---|---|
| `child_name` | Dự định đặt tên con (có thể rỗng) | 10/(6) |
| `child_birth_date` | Ngày sinh con `dd/mm/yyyy` | 11/(7) |
| `birth_time` | Giờ:phút sinh (phụ, không bắt buộc) | 11/(7) |
| `gender` | Giới tính con: `Nam` \| `Nữ` | 12/(8) |
| `ethnicity` | Dân tộc (theo mẹ trên GCS) | 13/(9) |
| `birth_place` | Nơi sinh / tên cơ sở y tế | 15/(11) |

`template`: `A` · `B` · `C` (3 mẫu phổ biến) · `custom` · `unknown`.

### Lỗi

| Code | Khi nào | Body |
|---|---|---|
| `400` | file không hợp lệ / quá size | `{ "error": "Bad Request", "detail": "..." }` |
| `500` | lỗi Vision/LLM | `{ "error": "OCR error", "detail": "..." }` |

### curl

```bash
curl -X POST https://trolyao-hcc.vnekyc.vn/api/v1/ocr/gcs \
  -H 'Content-Type: application/json' \
  -d '{ "files": [{ "name": "gcs.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,..." }] }'
```

---

## 3) OCR thô chung — `POST /api/v1/ocr/raw`

Trả về **text + tokens THÔ** từ Google Vision (`DOCUMENT_TEXT_DETECTION`), **KHÔNG** phân loại giấy tờ, **KHÔNG** map trường, **KHÔNG** grounding gate. Dùng khi dev muốn tự parse/format lại theo nhu cầu riêng. Hỗ trợ ảnh (`image/*`) và PDF (`application/pdf`).

### Request body

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `files` | array (1–10) | ✅ | `{ name, type, dataUrl }`. `type` = `image/*` hoặc `application/pdf`. PDF ≤ 5 trang (giới hạn Vision sync). |
| `include_tokens` | boolean | ❌ | Có trả mảng `tokens` (bbox + confidence theo từng từ) hay không. Mặc định `true`. |

```jsonc
{
  "files": [
    { "name": "trang1.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,/9j/4AAQ..." }
  ],
  "include_tokens": true
}
```

### Response 200

```jsonc
{
  "ok": true,
  "fullText": "GIẤY CHỨNG SINH\nHọ và tên mẹ ...\n---\n...",   // tất cả trang nối lại, phân tách bằng \n---\n
  "pages": [
    {
      "file_index": 0,        // index trong mảng files
      "name": "trang1.jpg",
      "type": "image/jpeg",
      "page": 0,              // index trang trong file (ảnh luôn 0; PDF tăng dần)
      "fullText": "GIẤY CHỨNG SINH\nHọ và tên mẹ ...",
      "tokens": [
        { "text": "GIẤY", "bbox": [0.12, 0.05, 0.08, 0.03], "confidence": 0.99 },
        { "text": "CHỨNG", "bbox": [0.21, 0.05, 0.10, 0.03], "confidence": 0.98 }
      ]
    }
  ],
  "latency_ms": 1180
}
```

| Field response | Mô tả |
|---|---|
| `fullText` | Text toàn bộ các trang nối lại (phân tách `\n---\n`). |
| `pages[].fullText` | Text của riêng từng trang/ảnh. |
| `pages[].tokens[]` | Từng "từ" Vision đọc: `text`, `bbox` = `[x, y, w, h]` normalized [0,1], `confidence`. Bỏ qua nếu `include_tokens=false`. |

> ⚠️ **PDF không có tokens/bbox**: Vision `files.annotate` cho PDF không trả pixel-size để tính bbox → `tokens` rỗng (nhưng `fullText` đầy đủ). Cần bbox để vẽ ô → gửi dạng **ảnh** `image/*`.

### Lỗi

| Code | Khi nào | Body |
|---|---|---|
| `400` | files invalid | (zod validation) |
| `500` | lỗi Vision | `{ "error": "OCR error", "detail": "..." }` |

### curl

```bash
curl -X POST https://trolyao-hcc.vnekyc.vn/api/v1/ocr/raw \
  -H 'Content-Type: application/json' \
  -d '{ "files": [{ "name": "anh.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,..." }] }'
```

---

## Phụ lục: dùng OCR trong luồng chatbot

Khi tích hợp qua chatbot (upload ảnh trong khung chat), dùng các endpoint bọc sẵn — tự cache theo `conversation_id` (TTL 24h) và gộp vào tờ khai:

| Path | Mô tả |
|---|---|
| `POST /api/v1/chatbot/attach/classify` | Vision LLM đoán `role` cho từng ảnh (gợi ý loại giấy tờ). |
| `POST /api/v1/chatbot/attach` | Upload ảnh kèm `role` → OCR (gọi nội bộ 2 endpoint trên) → cache theo `conversation_id` + trả `progress` + `fill_panel`. |
| `GET  /api/v1/forms/chat-uploads/{conversation_id}` | Lấy `merged_fields` + ảnh đã OCR (data **trước** khi gửi hồ sơ). |
| `GET  /api/v1/forms/by-code/{code}` | Lấy `fields` của hồ sơ **đã gửi** theo mã `HS-...` (data **sau** khi submit). |

> Lưu ý phân biệt: `chat-uploads` key theo **`conversation_id`** (vd `chatbot-c5b4...`), `by-code` key theo **mã hồ sơ `HS-...`**. Gọi nhầm → 404.
