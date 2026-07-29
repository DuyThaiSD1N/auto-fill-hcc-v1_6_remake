# API lập kế hoạch đính kèm tài liệu bước 3

Tài liệu này mô tả backend API dùng cho extension khi cần đính kèm tài liệu vào bảng "Thành phần hồ sơ" ở bước 3.

Backend không thao tác DOM trên trang Dịch vụ công. Backend chỉ nhận file, OCR/LLM hoặc dùng session bước 2 để phân loại tài liệu, sau đó trả về `attachments[]` là kế hoạch để FE action.

## Endpoint

Base URL:

```text
http://160.250.216.28:12005
```

```http
POST http://160.250.216.28:12005/api/v1/attachments/plan
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Request

```json
{
  "procedure": "ket-hon",
  "options": {
    "sessionId": "request-session-id",
    "attachmentContext": {
      "components": [
        {
          "index": 1,
          "componentName": "Mẫu hộ tịch điện tử tương tác đăng ký kết hôn",
          "required": true,
          "hasFile": true
        }
      ]
    }
  },
  "files": [
    {
      "name": "cccd_nam.pdf",
      "type": "application/pdf",
      "dataUrl": "data:application/pdf;base64,...",
      "role": "doc"
    }
  ]
}
```

## Request fields

| Field | Type | Bắt buộc | Ý nghĩa |
| --- | --- | --- | --- |
| `procedure` | string | Có | Key thủ tục. Ví dụ: `chung-thuc-ban-sao`, `khai-sinh-dang-ky-thuong`, `khai-sinh-dang-ky-lai`, `khai-tu`, `ket-hon`, `xac-nhan-tinh-trang-hon-nhan`. |
| `options.sessionId` | string | Không | Session bước 2 do `/api/v1/process` trả về. Dùng cho thủ tục có bước auto-fill trước bước đính kèm. |
| `options.attachmentContext` | object | Không | Context bảng thành phần hồ sơ hiện tại do content script đọc từ trang. |
| `files[]` | array | Có | Danh sách file người dùng chọn trong extension. |
| `files[].name` | string | Có | Tên file gốc. |
| `files[].type` | string | Có | MIME type. |
| `files[].dataUrl` | string | Có | Data URL base64. |
| `files[].role` | string | Không | Role nội bộ extension, thường là `doc`. |

## Response

```json
{
  "attachments": [
    {
      "fileIndex": 0,
      "fileName": "cccd_nam.pdf",
      "documentName": "Căn cước công dân bên nam",
      "componentName": "Căn cước công dân bên nam",
      "target": "new",
      "componentIndex": null,
      "needsAddComponent": true,
      "detectedType": "Căn cước công dân bên nam"
    }
  ],
  "extracted": {
    "documents": ["cccd_nam.pdf"],
    "ocrDocuments": ["cccd_nam.pdf"],
    "sessionId": "request-session-id"
  },
  "stats": {
    "ocr_latency_ms": 1200,
    "llm_latency_ms": 0,
    "total_latency_ms": 1200
  },
  "errors": []
}
```

## Response fields

| Field | Type | Ý nghĩa |
| --- | --- | --- |
| `attachments[]` | array | Kế hoạch đính kèm từng file. FE chỉ action theo mảng này. |
| `fileIndex` | number | Index của file trong `request.files`. |
| `fileName` | string | Tên file gốc backend nhận được. |
| `documentName` | string | Tên tài liệu sẽ điền vào ô `Tên tài liệu` trong modal ví giấy tờ. |
| `componentName` | string | Tên thành phần hồ sơ cần đính file. |
| `target` | `"existing"` hoặc `"new"` | `existing` là đính vào dòng có sẵn, `new` là cần thêm thành phần hồ sơ mới. |
| `componentIndex` | number/null | Dòng thành phần hồ sơ có sẵn, bắt đầu từ 1. Dùng khi `target=existing`. |
| `needsAddComponent` | boolean | `true` nếu FE phải bấm `Thêm thành phần hồ sơ`. |
| `detectedType` | string/null | Loại giấy tờ backend nhận diện. Dùng để debug và fallback tên. |
| `extracted` | object | Thông tin phụ để debug: OCR file nào, session nào, phân loại ra sao. |
| `stats` | object | Thời gian OCR/LLM. |
| `errors` | array | Cảnh báo không fatal. Nếu lỗi fatal, API trả HTTP error. |

## Quy ước lập plan

### `target = "existing"`

FE tìm dòng hồ sơ có sẵn theo:

1. `componentIndex`, nếu có.
2. `componentName`, so khớp bỏ dấu và khoảng trắng.
3. Fallback dòng bắt buộc mặc định với thủ tục chứng thực bản sao.

Ví dụ:

```json
{
  "fileIndex": 0,
  "documentName": "Giấy CNQSD đất",
  "componentName": "Bản chính giấy tờ, văn bản làm cơ sở để chứng thực bản sao và bản sao cần chứng thực...",
  "target": "existing",
  "componentIndex": 1,
  "needsAddComponent": false,
  "detectedType": "Giấy chứng nhận quyền sử dụng đất"
}
```

### `target = "new"`

FE phải:

1. Bấm `Thêm thành phần hồ sơ`.
2. Điền `componentName`.
3. Bấm `Chọn tệp đính kèm` ở dòng mới.
4. Upload file vào modal ví giấy tờ.

Ví dụ:

```json
{
  "fileIndex": 1,
  "documentName": "Căn cước công dân bên nữ",
  "componentName": "Căn cước công dân bên nữ",
  "target": "new",
  "componentIndex": null,
  "needsAddComponent": true,
  "detectedType": "Căn cước công dân bên nữ"
}
```

## Thủ tục hiện hỗ trợ

| Procedure | Kiểu | Ghi chú |
| --- | --- | --- |
| `chung-thuc-ban-sao` | `mode=attach` | Nút chính trong popup là đính kèm hồ sơ. Backend dùng OCR/LLM để phân loại tài liệu. |
| `khai-sinh-dang-ky-thuong` | `hasAttachmentStep=true` | Thủ tục đăng ký khai sinh thường. Bước 3 đính giấy chứng sinh vào dòng có sẵn; CCCD bố/mẹ là thành phần hồ sơ mới. |
| `khai-sinh-dang-ky` | `hasAttachmentStep=true` | Thủ tục đăng ký khai sinh liên thông. Bước 3 dùng cùng planner khai sinh. |
| `khai-sinh-dang-ky-lai` | `hasAttachmentStep=true` | Bước 3 đính giấy khai sinh bản sao vào dòng 2; giấy tờ cá nhân đầu tiên vào dòng 3, các giấy tờ cá nhân tiếp theo là thành phần mới. |
| `khai-tu` | `hasAttachmentStep=true` | Bước 3 đính giấy báo tử/chứng tử vào dòng có sẵn; CCCD người yêu cầu và tờ khai bản giấy là thành phần hồ sơ mới. |
| `ket-hon` | `hasAttachmentStep=true` | Bước 2 auto-fill trước, bước 3 dùng session để phân biệt CCCD nam/nữ. |
| `xac-nhan-tinh-trang-hon-nhan` | `hasAttachmentStep=true` | Bước 3 dùng OCR/LLM để phân loại CCCD, ly hôn, ghi chú ly hôn, giấy xác nhận cũ/ủy quyền. |

## Mẫu response theo thủ tục

### Đăng ký khai sinh thường: `khai-sinh-dang-ky-thuong`

Danh sách thành phần hồ sơ mặc định ở bước 3:

| STT | Thành phần hồ sơ | Cách map |
| --- | --- | --- |
| 1 | Mẫu hộ tịch điện tử tương tác đăng ký khai sinh | E-form có sẵn, không upload bằng attachment plan. |
| 2 | Giấy chứng sinh hoặc văn bản người làm chứng/giấy cam đoan việc sinh | `target=existing`, `componentIndex=2`. |
| 3 | Biên bản trẻ bị bỏ rơi | `target=existing`, `componentIndex=3`. |
| 4 | Văn bản mang thai hộ hoặc văn bản ủy quyền của cha/mẹ trẻ | `target=existing`, `componentIndex=4`. |

CCCD bố/mẹ không nằm trong danh sách mặc định thì backend trả `target=new`, FE bấm `Thêm thành phần hồ sơ`.

### Đăng ký lại khai sinh: `khai-sinh-dang-ky-lai`

Danh sách thành phần hồ sơ mặc định ở bước 3:

| STT | Thành phần hồ sơ | Cách map |
| --- | --- | --- |
| 1 | Mẫu hộ tịch điện tử tương tác đăng ký lại khai sinh | E-form có sẵn, không upload bằng attachment plan. |
| 2 | Bản sao Giấy khai sinh hoặc giấy tờ có giá trị thay thế Giấy khai sinh | `target=existing`, `componentIndex=2`. |
| 3 | Giấy tờ cá nhân thay thế khi không có Giấy khai sinh: CCCD/CMND/Hộ chiếu, cư trú, bằng tốt nghiệp, giấy chứng nhận, chứng chỉ, học bạ, hồ sơ học tập, văn bản xác nhận | File đầu tiên thuộc nhóm này dùng `target=existing`, `componentIndex=3`; các file tiếp theo dùng `target=new` với tên đúng loại giấy. |
| 5 | Văn bản ủy quyền | `target=existing`, `componentIndex=5`. |

Tờ khai đăng ký lại khai sinh bản giấy không nằm trong danh sách mặc định thì backend trả `target=new`, `componentName="Tờ khai bản giấy"`.

### Đăng ký khai tử: `khai-tu`

Danh sách thành phần hồ sơ mặc định ở bước 3:

| STT | Thành phần hồ sơ | Cách map |
| --- | --- | --- |
| 1 | Mẫu hộ tịch điện tử tương tác đăng ký khai tử | E-form có sẵn, không upload bằng attachment plan. |
| 2 | Giấy báo tử hoặc giấy tờ thay Giấy báo tử | `target=existing`, `componentIndex=2`. |
| 3 | Giấy tờ/tài liệu/chứng cứ chứng minh sự kiện chết hoặc văn bản ủy quyền liên quan | `target=existing`, `componentIndex=3`. |
| 5 | Giấy tờ chứng minh nơi người đó chết hoặc nơi phát hiện thi thể | `target=existing`, `componentIndex=5`. |

CCCD người yêu cầu và tờ khai đăng ký khai tử bản giấy không nằm trong danh sách mặc định thì backend trả `target=new`.

Ví dụ response:

```json
{
  "attachments": [
    {
      "fileIndex": 0,
      "fileName": "giay_chung_sinh.pdf",
      "documentName": "Giấy chứng sinh",
      "componentName": "- Giấy chứng sinh; trường hợp không có Giấy chứng sinh thì nộp văn bản của người làm chứng xác nhận về việc sinh; nếu không có người làm chứng thì phải có giấy cam đoan về việc sinh.",
      "target": "existing",
      "componentIndex": 2,
      "needsAddComponent": false,
      "detectedType": "Giấy chứng sinh"
    },
    {
      "fileIndex": 1,
      "fileName": "cccd_bo.pdf",
      "documentName": "Căn cước công dân bố",
      "componentName": "Căn cước công dân bố",
      "target": "new",
      "componentIndex": null,
      "needsAddComponent": true,
      "detectedType": "Căn cước công dân bố"
    },
    {
      "fileIndex": 2,
      "fileName": "cccd_me.pdf",
      "documentName": "Căn cước công dân mẹ",
      "componentName": "Căn cước công dân mẹ",
      "target": "new",
      "componentIndex": null,
      "needsAddComponent": true,
      "detectedType": "Căn cước công dân mẹ"
    }
  ],
  "extracted": {
    "documents": ["giay_chung_sinh.pdf", "cccd_bo.pdf", "cccd_me.pdf"],
    "ocrDocuments": ["giay_chung_sinh.pdf", "cccd_bo.pdf", "cccd_me.pdf"],
    "sessionId": "request-session-id"
  },
  "stats": {
    "ocr_latency_ms": 1200,
    "llm_latency_ms": 900,
    "total_latency_ms": 2100
  },
  "errors": []
}
```

Nếu là biên bản trẻ bị bỏ rơi:

```json
{
  "fileIndex": 0,
  "fileName": "bien_ban_tre_bo_roi.pdf",
  "documentName": "Biên bản về việc trẻ bị bỏ rơi",
  "componentName": "- Trường hợp trẻ em bị bỏ rơi thì phải có biên bản về việc trẻ bị bỏ rơi do cơ quan có thẩm quyền lập.",
  "target": "existing",
  "componentIndex": 3,
  "needsAddComponent": false,
  "detectedType": "Biên bản về việc trẻ bị bỏ rơi"
}
```

Nếu là văn bản mang thai hộ hoặc ủy quyền:

```json
{
  "fileIndex": 0,
  "fileName": "van_ban_uy_quyen.pdf",
  "documentName": "Văn bản mang thai hộ hoặc văn bản ủy quyền",
  "componentName": "- Trường hợp khai sinh cho trẻ em sinh ra do mang thai hộ phải có văn bản xác nhận của cơ sở y tế đã thực hiện kỹ thuật hỗ trợ sinh sản cho việc mang thai hộ. phải có văn bản ủy quyền của cha, mẹ trẻ em, nhưng phải thống nhất với cha, mẹ trẻ em về nội dung khai sinh",
  "target": "existing",
  "componentIndex": 4,
  "needsAddComponent": false,
  "detectedType": "Văn bản mang thai hộ hoặc văn bản ủy quyền"
}
```

### Đăng ký kết hôn: `ket-hon`

Danh sách thành phần hồ sơ mặc định ở bước 3:

| STT | Thành phần hồ sơ | Cách map |
| --- | --- | --- |
| 1 | Mẫu hộ tịch điện tử tương tác đăng ký kết hôn | E-form có sẵn, không upload bằng attachment plan. |
| 2 | Giấy tờ tùy thân của cả hai bên | Hiện tại không dùng dòng mặc định; backend trả thành phần hồ sơ mới để tên rõ bên nam/bên nữ. |
| 3 | Giấy tờ chứng minh nơi cư trú | Không tự đính CCCD vào dòng này. |

Ví dụ 2 file CCCD riêng:

```json
{
  "attachments": [
    {
      "fileIndex": 0,
      "fileName": "cccd_nam.pdf",
      "documentName": "Căn cước công dân bên nam",
      "componentName": "Căn cước công dân bên nam",
      "target": "new",
      "componentIndex": null,
      "needsAddComponent": true,
      "detectedType": "Căn cước công dân bên nam"
    },
    {
      "fileIndex": 1,
      "fileName": "cccd_nu.pdf",
      "documentName": "Căn cước công dân bên nữ",
      "componentName": "Căn cước công dân bên nữ",
      "target": "new",
      "componentIndex": null,
      "needsAddComponent": true,
      "detectedType": "Căn cước công dân bên nữ"
    }
  ],
  "extracted": {
    "documents": ["cccd_nam.pdf", "cccd_nu.pdf"],
    "ocrDocuments": ["cccd_nam.pdf", "cccd_nu.pdf"],
    "sessionId": "request-session-id"
  },
  "stats": {
    "ocr_latency_ms": 1000,
    "llm_latency_ms": 0,
    "total_latency_ms": 1000
  },
  "errors": []
}
```

Ví dụ 1 file gộp CCCD của cả hai bên:

```json
{
  "fileIndex": 0,
  "fileName": "cccd_ca_hai.pdf",
  "documentName": "Căn cước công dân của cả bên nam và bên nữ",
  "componentName": "Căn cước công dân của cả bên nam và bên nữ",
  "target": "new",
  "componentIndex": null,
  "needsAddComponent": true,
  "detectedType": "Căn cước công dân của cả bên nam và bên nữ"
}
```

## Validate file

Backend đang validate:

- MIME type thuộc allowlist: PDF, ảnh, XML, audio, video.
- Mỗi file không vượt `MAX_FILE_SIZE_MB`.
- Tổng payload không vượt `MAX_TOTAL_PAYLOAD_MB`.

Nếu vi phạm, API trả lỗi:

```json
{
  "code": "FILE_TOO_LARGE",
  "message": "File abc.pdf vượt quá 30MB"
}
```

## Cách thêm thủ tục mới

1. Thêm thủ tục vào registry:

```python
{
    "key": "thu-tuc-moi",
    "label": "Tên thủ tục",
    "mode": "agent",
    "hasAttachmentStep": True,
}
```

2. Viết planner riêng:

```python
async def plan_thu_tuc_moi_attachments(files, options, session=None) -> dict:
    return {
        "attachments": [...],
        "extracted": {...},
        "stats": {...},
        "errors": [],
    }
```

3. Import planner vào `app/attachments/router.py`.

4. Thêm procedure vào allowlist `/attachments/plan`.

5. Viết test tối thiểu:

- API reject procedure chưa hỗ trợ.
- API trả đúng `attachments[]`.
- `target=new` và `target=existing` đúng theo yêu cầu nghiệp vụ.
