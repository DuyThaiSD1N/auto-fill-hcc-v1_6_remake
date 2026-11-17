# Bộ ca hồi quy

Mỗi lần Agent tự sửa đạt một ca có đụng backend, dịch vụ dựng một **ca hồi quy** vào `cases/<thủ tục>/<mã ca>.json`. Lần sửa sau
phát lại toàn bộ bộ ca này: ca đang đạt mà bản sửa mới làm trượt thì bản sửa không được qua.

## Một ca gồm gì

| Khoá | Nội dung |
| --- | --- |
| `procedure`, `account` | Thủ tục; username, xã, tỉnh của tài khoản test đã chạy lại (router chỉnh options theo tài khoản) |
| `options` | Options của lượt điền, đã bỏ khoá gắn với hồ sơ thật |
| `files[]` | Tên, vai trò, text OCR của từng tệp. **Không có ảnh hay PDF gốc** |
| `llm[]` | Câu trả lời LLM theo thứ tự của một lượt chạy lại đã đạt sau khi sửa (`purpose`, `raw`) |
| `checks[]` | Tiêu chí của trọng tài, chấm bằng `agents/scoring.py` như lúc chạy thật |
| `catchesOldBug` | `true`: phát lại trên code production thì trượt, trên bản sửa thì đạt |

Dữ liệu đã ẩn danh trước khi ghi (`agents/regression_case.py`):
- **Thay bằng dữ liệu bịa:** họ tên, số giấy tờ và điện thoại (từ 9 chữ số, giữ 3 số đầu), email, phần số nhà / thôn / đường của địa chỉ. Một chuỗi thật luôn được thay bằng cùng một chuỗi bịa trong OCR, câu trả lời LLM, options và tiêu chí.
- **Giữ nguyên:** ngày tháng và đơn vị hành chính, vì mapper và remap cần chúng.
- **Quét lại sau khi thay** bằng `codeguard`: còn sót chuỗi thật nào thì không ghi ca.

Phép quét chỉ biết các chuỗi rút ra được từ field và nhãn "Họ và tên". **Phải đọc lại tệp ca trước khi commit.**

## Ca chỉ được ghi khi

1. Phát lại **đạt** trên code đã sửa. Một số ca bị loại ở bước này, vì field lấy từ nguồn không nằm trong ca, hoặc code gọi LLM nhiều lần hơn lúc ghi.
2. Bản sửa có đụng backend. Lỗi chỉ ở extension không bắt được ở tầng này.

Sau đó ca được phát lại thêm trên đúng commit production (một cây tạm từ tag của khu làm việc) để ghi `catchesOldBug`.

## Chạy tay

```powershell
# Cần cài requirements.txt của backend. Không cần mạng, Mongo hay .env.
python auto-test-hcc/regression/run.py --be auto-fill-hcc-backend                 # cả bộ
python auto-test-hcc/regression/run.py --be <cây backend> cases/khai-tu/at_x.json  # một ca
```

Thoát mã 1 nếu có ca trượt. Phát lại đi qua endpoint `/api/v1/process` thật, gồm cả phần chỉnh options theo tài khoản, pipeline và hậu
xử lý. OCR và LLM được thay bằng dữ liệu của ca, mọi kết nối mạng bị chặn, không ghi Mongo hay đĩa. Các điểm cắm giống
`tests/unit/test_monitor_process_flow.py` của backend.

## Chạy trong CI của repo backend

Chép [ci/regression.yml](ci/regression.yml) vào `.github/workflows/` của `dev-f19/auto-fill-hcc-backend`, rồi thêm secret
`AUTOTEST_REPO_TOKEN` (token chỉ đọc repo `dev-f19/test-auto-test-and-fix`, vì repo này private). Mỗi PR sẽ phát lại cả bộ ca trên code
của PR đó.

## Ca trượt thì làm gì

- **Bản sửa mới làm hỏng lại lỗi cũ:** sửa code.
- **Code đổi cách gọi LLM**, ví dụ thêm một lượt gọi hay đổi prompt khiến câu trả lời cũ không còn hợp: chạy lại ca gốc trên web
  Agent tự sửa để ghi lại ca, hoặc xoá tệp ca đó nếu nó không còn đúng.
