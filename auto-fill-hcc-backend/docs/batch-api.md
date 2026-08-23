# Batch extraction API

API batch dành cho module nội bộ chạy nhiều hồ sơ qua đúng pipeline của `/api/v1/process`.
Nó không tạo `traces` hay `process_requests`, vì dữ liệu chạy chiến dịch không phải lượt dùng
thực tế của cán bộ.

## Luồng xử lý

1. Tạo một batch cho một thủ tục.
2. Gửi từng hồ sơ vào batch bằng multipart. Khuyến nghị phía gọi chỉ tải đồng thời 2-5 hồ sơ.
3. Gọi `start` sau khi tải đủ hồ sơ.
4. Worker riêng lấy tối đa `BATCH_WORKER_CONCURRENCY` hồ sơ cùng lúc để OCR + LLM.
5. Poll trạng thái batch khoảng 2-5 giây/lần hoặc lấy kết quả từng hồ sơ/theo trang.

MongoDB giữ trạng thái hàng đợi. File được ghi tại `BATCH_STORAGE_DIR`; API và worker phải dùng
chung volume này. Lease + heartbeat ngăn hai worker xử lý cùng một hồ sơ. Lỗi tạm thời được retry
tối đa `BATCH_MAX_ATTEMPTS`; `clientDossierId`, `Idempotency-Key` và hash toàn bộ danh sách file
được dùng để chống gửi trùng trong cùng batch.

`BATCH_WORKER_CONCURRENCY` là số hồ sơ đồng thời trên **mỗi process worker**. Nếu chạy nhiều
container worker thì tổng tải OCR/LLM bằng số container nhân với giá trị này.

## Xác thực

Mọi endpoint dùng header:

```text
Authorization: Bearer <BATCH_API_SECRET>
```

Để trống `BATCH_API_SECRET` sẽ khóa API batch với mã `503 BATCH_AUTH_NOT_CONFIGURED`.

## API

Tạo batch:

```bash
curl -X POST http://localhost:8000/api/v1/batch/jobs \
  -H "Authorization: Bearer $BATCH_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"name":"Trích lục hộ tịch 22-08","procedure":"trich-luc-ks"}'
```

Thêm một hồ sơ (lặp lại cho từng hồ sơ):

```bash
curl -X POST http://localhost:8000/api/v1/batch/jobs/<jobId>/items \
  -H "Authorization: Bearer $BATCH_API_SECRET" \
  -H "Idempotency-Key: campaign-01-hoso-0001" \
  -F 'metadata={"clientDossierId":"hoso-0001","options":{},"files":[{"name":"cccd.pdf","type":"application/pdf","role":"doc"}]}' \
  -F 'files=@/duong-dan/cccd.pdf;type=application/pdf'
```

Khởi chạy và xem tiến độ:

```bash
curl -X POST http://localhost:8000/api/v1/batch/jobs/<jobId>/start \
  -H "Authorization: Bearer $BATCH_API_SECRET"

curl http://localhost:8000/api/v1/batch/jobs/<jobId> \
  -H "Authorization: Bearer $BATCH_API_SECRET"
```

Kết quả:

```bash
curl http://localhost:8000/api/v1/batch/items/<itemId>/result \
  -H "Authorization: Bearer $BATCH_API_SECRET"

curl 'http://localhost:8000/api/v1/batch/jobs/<jobId>/results?page=1&pageSize=100' \
  -H "Authorization: Bearer $BATCH_API_SECRET"
```

Điều khiển khác: `POST /jobs/{jobId}/pause`, `/resume`, `/cancel`,
`POST /items/{itemId}/retry`. Sau khi đã tải kết quả, gọi
`DELETE /jobs/{jobId}` để xóa metadata và file của batch đã hoàn tất/đã hủy.
