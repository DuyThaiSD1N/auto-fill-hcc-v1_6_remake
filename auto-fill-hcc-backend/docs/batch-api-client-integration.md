# API bóc tách hồ sơ theo lô

Tài liệu này dành cho hệ thống bên ngoài gọi Auto Fill HCC để bóc tách nhiều hồ sơ
của cùng một thủ tục.

## 1. Thông tin kết nối

- Base URL: `https://trolyhoso-hcc-admin.vnekyc.vn`
- API prefix: `/api/v1/batch`
- Content type khi tạo batch: `application/json`
- Content type khi tải hồ sơ: `multipart/form-data`
- Xác thực: Bearer token riêng do đội Auto Fill HCC cung cấp

Mọi request phải có header:

```http
Authorization: Bearer <BATCH_API_SECRET>
```

Không dùng JWT đăng nhập của cán bộ hoặc extension cho API này.

## 2. Quy trình tổng quát

Ví dụ cần chạy 100 hồ sơ:

1. Gọi API tạo batch một lần, nhận `jobId`.
2. Gọi API tải hồ sơ 100 lần; mỗi request là một hồ sơ và có thể chứa nhiều file.
3. Sau khi tải đủ, gọi API `start` một lần.
4. Poll trạng thái batch khoảng 2-5 giây/lần.
5. Khi các hồ sơ đã hoàn tất, lấy kết quả theo từng hồ sơ hoặc theo từng trang.
6. Sau khi đã lưu kết quả về hệ thống bên gọi, có thể xóa batch trên Auto Fill HCC.

Không cần tự giới hạn OCR/LLM ở phía gọi. Worker Auto Fill HCC đã giới hạn số hồ sơ
xử lý đồng thời. Tuy nhiên, khi tải file nên chỉ gửi song song khoảng 2-5 hồ sơ để tránh
tạo quá nhiều kết nối upload cùng lúc.

## 3. Tạo batch

### Request

```http
POST /api/v1/batch/jobs
Content-Type: application/json
Authorization: Bearer <BATCH_API_SECRET>
```

```json
{
  "name": "Trích lục hộ tịch ngày 22-08-2026",
  "procedure": "trich-luc-ks"
}
```

Trong đó:

| Thuộc tính | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `name` | Có | Tên chiến dịch để con người dễ nhận biết. |
| `procedure` | Có | Mã thủ tục trong Auto Fill HCC. Tất cả hồ sơ trong batch dùng chung mã này. |

### Response `201 Created`

```json
{
  "jobId": "job_50e402cfbc924761",
  "name": "Trích lục hộ tịch ngày 22-08-2026",
  "procedure": "trich-luc-ks",
  "status": "draft",
  "counts": {
    "total": 0
  },
  "createdAt": "2026-08-22T09:00:00+00:00",
  "startedAt": null,
  "finishedAt": null
}
```

Lưu lại `jobId` để sử dụng cho các API tiếp theo.

## 4. Tải một hồ sơ và danh sách file

### Request

```http
POST /api/v1/batch/jobs/{jobId}/items
Content-Type: multipart/form-data
Authorization: Bearer <BATCH_API_SECRET>
Idempotency-Key: <khóa chống gửi lặp>
```

Multipart gồm:

| Field | Kiểu | Bắt buộc | Ý nghĩa |
| --- | --- | --- | --- |
| `metadata` | Chuỗi JSON | Có | Mã hồ sơ, context của form và mô tả từng file. |
| `files` | Binary file | Có | Có thể lặp field này nhiều lần để gửi nhiều file trong một hồ sơ. |

Ví dụ `metadata`:

```json
{
  "clientDossierId": "hoso-0001",
  "options": {
    "formContext": {}
  },
  "files": [
    {
      "name": "to-khai.pdf",
      "type": "application/pdf",
      "role": "doc",
      "hasHandwriting": false
    },
    {
      "name": "cccd.pdf",
      "type": "application/pdf",
      "role": "doc",
      "hasHandwriting": false
    }
  ]
}
```

Lưu ý quan trọng:

- `clientDossierId` là ID hồ sơ ở hệ thống bên gọi và phải duy nhất trong batch.
- Thứ tự phần tử trong `metadata.files` phải giống thứ tự các multipart field `files`.
- `options` truyền cùng cấu trúc context đang dùng khi gọi `/api/v1/process`; không có thì gửi `{}`.
- `role` thường là `doc`; nếu thủ tục có role riêng thì truyền đúng role từ danh mục thủ tục.
- `hasHandwriting=true` khi tài liệu có nội dung viết tay.
- Chỉ hỗ trợ JPG, PNG, PDF và DOCX.
- Giới hạn mặc định: 80 MB mỗi file và 100 MB cho toàn bộ một hồ sơ.

Ví dụ cURL:

```bash
curl -X POST \
  'https://trolyhoso-hcc-admin.vnekyc.vn/api/v1/batch/jobs/job_50e402cfbc924761/items' \
  -H 'Authorization: Bearer <BATCH_API_SECRET>' \
  -H 'Idempotency-Key: campaign-20260822-hoso-0001' \
  -F 'metadata={"clientDossierId":"hoso-0001","options":{},"files":[{"name":"to-khai.pdf","type":"application/pdf","role":"doc","hasHandwriting":false},{"name":"cccd.pdf","type":"application/pdf","role":"doc","hasHandwriting":false}]}' \
  -F 'files=@/data/hoso-0001/to-khai.pdf;type=application/pdf' \
  -F 'files=@/data/hoso-0001/cccd.pdf;type=application/pdf'
```

### Response `202 Accepted`

```json
{
  "itemId": "item_b218ad08e4ee4cd3",
  "jobId": "job_50e402cfbc924761",
  "clientDossierId": "hoso-0001",
  "procedure": "trich-luc-ks",
  "status": "staged",
  "attempts": 0,
  "fileCount": 2,
  "totalBytes": 1572864,
  "hasErrors": false,
  "error": null,
  "createdAt": "2026-08-22T09:01:00+00:00",
  "startedAt": null,
  "finishedAt": null,
  "duplicate": false
}
```

Lưu `itemId` cùng với `clientDossierId` để tra kết quả sau này.

### Chống gửi trùng

Server chống trùng trong cùng một batch theo ba khóa:

1. `clientDossierId`.
2. Header `Idempotency-Key`.
3. Hash nội dung của toàn bộ danh sách file.

Nếu phía gọi timeout và không biết request trước đã thành công hay chưa, hãy gửi lại với cùng
`Idempotency-Key`. Server trả item đã tạo với:

```json
{
  "duplicate": true
}
```

Đây không phải lỗi; phía gọi tiếp tục dùng `itemId` trong response.

## 5. Bắt đầu xử lý batch

Chỉ gọi sau khi đã tải đủ hồ sơ.

```http
POST /api/v1/batch/jobs/{jobId}/start
Authorization: Bearer <BATCH_API_SECRET>
```

Ví dụ:

```bash
curl -X POST \
  'https://trolyhoso-hcc-admin.vnekyc.vn/api/v1/batch/jobs/job_50e402cfbc924761/start' \
  -H 'Authorization: Bearer <BATCH_API_SECRET>'
```

Batch chuyển từ `draft` sang `running`; các item chuyển từ `staged` sang `queued`.

## 6. Theo dõi tiến độ

```http
GET /api/v1/batch/jobs/{jobId}
Authorization: Bearer <BATCH_API_SECRET>
```

Ví dụ response:

```json
{
  "jobId": "job_50e402cfbc924761",
  "name": "Trích lục hộ tịch ngày 22-08-2026",
  "procedure": "trich-luc-ks",
  "status": "running",
  "counts": {
    "queued": 86,
    "running": 2,
    "done": 11,
    "failed": 1,
    "total": 100,
    "done_with_errors": 0
  },
  "createdAt": "2026-08-22T09:00:00+00:00",
  "startedAt": "2026-08-22T09:05:00+00:00",
  "finishedAt": null
}
```

Các trạng thái batch:

| Trạng thái | Ý nghĩa |
| --- | --- |
| `draft` | Đang nhận hồ sơ, chưa chạy. |
| `running` | Worker đang xử lý. |
| `paused` | Tạm dừng nhận item mới vào worker; item đang chạy được phép hoàn thành. |
| `completed` | Tất cả item đã về trạng thái kết thúc, có thể gồm cả item `failed`. |
| `cancelled` | Batch đã bị hủy. |

Các trạng thái item:

| Trạng thái | Ý nghĩa |
| --- | --- |
| `staged` | Đã tải lên, batch chưa start. |
| `queued` | Đang chờ worker. |
| `running` | Đang OCR/LLM. |
| `paused` | Đang tạm dừng. |
| `done` | Đã có kết quả. |
| `failed` | Xử lý thất bại sau retry hoặc lỗi input không thể retry. |
| `cancelled` | Đã hủy. |

Liệt kê item:

```http
GET /api/v1/batch/jobs/{jobId}/items?page=1&pageSize=100
GET /api/v1/batch/jobs/{jobId}/items?status=failed&page=1&pageSize=100
```

## 7. Lấy kết quả

### Lấy một hồ sơ

```http
GET /api/v1/batch/items/{itemId}/result
Authorization: Bearer <BATCH_API_SECRET>
```

Response chứa metadata item và `result` có cùng cấu trúc chính với `/api/v1/process`:

```json
{
  "itemId": "item_b218ad08e4ee4cd3",
  "clientDossierId": "hoso-0001",
  "status": "done",
  "result": {
    "fields": [
      {
        "name": "HoTen",
        "comp": "x-input",
        "value": "NGUYỄN VĂN A",
        "default": false,
        "occurrence": null
      }
    ],
    "extracted": {},
    "stats": {
      "ocr_latency_ms": 1000,
      "llm_latency_ms": 2500,
      "total_latency_ms": 3500
    },
    "errors": [],
    "sessionId": "item_b218ad08e4ee4cd3",
    "requestId": "item_b218ad08e4ee4cd3",
    "pages": null,
    "businessFlow": null
  }
}
```

### Lấy nhiều kết quả theo trang

```http
GET /api/v1/batch/jobs/{jobId}/results?page=1&pageSize=100
Authorization: Bearer <BATCH_API_SECRET>
```

Endpoint này chỉ trả những item có trạng thái `done`. `pageSize` tối đa là `200`.

Nên dùng `clientDossierId` để ghép kết quả về đúng hồ sơ bên hệ thống gọi, không phụ thuộc
thứ tự item hoàn thành.

## 8. Retry, tạm dừng và hủy

Chạy lại một item `failed`:

```http
POST /api/v1/batch/items/{itemId}/retry
```

Tạm dừng/chạy tiếp/hủy batch:

```http
POST /api/v1/batch/jobs/{jobId}/pause
POST /api/v1/batch/jobs/{jobId}/resume
POST /api/v1/batch/jobs/{jobId}/cancel
```

## 9. Xóa batch sau khi lấy kết quả

```http
DELETE /api/v1/batch/jobs/{jobId}
Authorization: Bearer <BATCH_API_SECRET>
```

Chỉ xóa được batch `completed` hoặc `cancelled` và không còn item đang chạy. Thao tác này xóa
cả metadata và file đã tải lên, vì vậy chỉ gọi sau khi hệ thống bên ngoài đã lưu kết quả cần thiết.

## 10. Mã lỗi thường gặp

Error response chung:

```json
{
  "error": "ERROR_CODE",
  "message": "Mô tả lỗi",
  "code": 400
}
```

| HTTP | `error` | Cách xử lý |
| --- | --- | --- |
| `400` | `UNKNOWN_PROCEDURE` | Kiểm tra lại mã thủ tục. |
| `400` | `BAD_BATCH_METADATA` | Kiểm tra JSON trong field `metadata`. |
| `400` | `BAD_BATCH_FILE_METADATA` | Số mô tả file không bằng số multipart file. |
| `400` | `BAD_FILE_TYPE` | Chuyển file về JPG, PNG, PDF hoặc DOCX. |
| `401` | `INVALID_BATCH_SECRET` | Kiểm tra Bearer secret. |
| `404` | `BATCH_JOB_NOT_FOUND` | `jobId` không tồn tại. |
| `409` | `BATCH_JOB_NOT_DRAFT` | Không tải thêm hồ sơ sau khi batch đã start. |
| `409` | `BATCH_CANNOT_START` | Batch không ở `draft` hoặc chưa có hồ sơ. |
| `413` | `FILE_TOO_LARGE` | Một file vượt giới hạn. |
| `413` | `PAYLOAD_TOO_LARGE` | Tổng dung lượng một hồ sơ vượt giới hạn. |
| `429` | `BATCH_QUEUE_FULL` | Hàng đợi toàn hệ thống đầy; chờ rồi thử lại. |
| `503` | `BATCH_AUTH_NOT_CONFIGURED` | Server production chưa cấu hình secret. |
| `507` | `BATCH_DISK_LOW` | Server không đủ dung lượng lưu batch. |

Quy tắc retry phía gọi:

- Upload timeout hoặc lỗi mạng: gửi lại cùng `Idempotency-Key`.
- HTTP `429`: retry có backoff, ví dụ 5, 10, 20, 40 giây.
- HTTP `4xx` khác: sửa request, không retry liên tục.
- HTTP `5xx`: retry tối đa vài lần với exponential backoff.
- Không tạo batch mới chỉ vì poll tạm thời lỗi; tiếp tục dùng `jobId` cũ.

## 11. Pseudocode cho 100 hồ sơ

```text
job = POST /batch/jobs

for each dossier with concurrency = 3:
    POST /batch/jobs/{job.id}/items
    save mapping dossier.id -> response.itemId

POST /batch/jobs/{job.id}/start

repeat every 3 seconds:
    progress = GET /batch/jobs/{job.id}
until progress.status in [completed, cancelled]

for each result page:
    GET /batch/jobs/{job.id}/results?page=N&pageSize=100
    save result by clientDossierId

for each failed item that should be retried manually:
    POST /batch/items/{itemId}/retry
```
