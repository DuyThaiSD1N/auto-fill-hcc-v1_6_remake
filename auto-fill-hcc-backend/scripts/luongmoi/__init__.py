"""THỬ luồng mới cho TTHN — rà soát lần 2 bằng OCR Qwen. Công cụ ở máy dev, KHÔNG chạy trên prod.

Luồng mỗi hồ sơ:
  ┌─ (1) luồng hiện tại: OCR Vintern → LLM trích xuất → mapper  ⇒ OUTPUT 1 (bản v1, giữ nguyên để so)
  └─ (2) OCR Qwen cùng các tệp (chạy song song với 1)
        ↓ cả hai xong
  (3) kiem_tra.goi_y()   — code soát v1: xã không có trong danh mục, số định danh sai độ dài → gợi ý cho agent
  (4) agent rà soát      — prompt.py: rà MỌI field, chỉ trả field cần SỬA (địa chỉ, mục đích, field trống)
                           hoặc CẢNH BÁO (tên khác chữ cái, ngày/số lệch chữ số…)
  (5) kiem_tra.chot()    — code chốt cờ: ngoài địa chỉ/mục đích không được sửa (hạ thành cảnh báo), địa chỉ
                           đổi sang xã khác → cảnh báo, bỏ cảnh báo chỉ khác dấu / chỉ khác định dạng / nơi cấp
  (6) chạy lại fallback + validate + mapper trên v2                 ⇒ OUTPUT 2 (chỉ field có cờ + ô UI đổi)

Tệp:
  du_lieu.py   nạp trace + tệp gốc (thiếu thì tải từ prod, chỉ GET), OCR Vintern đã lưu, OCR Qwen (cache)
  prompt.py    prompt agent rà soát
  kiem_tra.py  phần code: gợi ý trước agent + chốt cờ sau agent
  luong.py     ghép các bước + đo thời gian
  cham.py      đối chiếu với bản chấm tay (phan_tich_claude.json) nếu hồ sơ có
  run.py       dòng lệnh

Chạy từ auto-fill-hcc-backend:
  .venv/bin/python -m scripts.luongmoi.run req_a req_b            # OCR Qwen lấy cache nếu đã có
  .venv/bin/python -m scripts.luongmoi.run req_a --qwen-moi        # OCR Qwen lại (đo thời gian thật)
  .venv/bin/python -m scripts.luongmoi.run req_a --runs 2          # chạy 2 lượt để thấy độ dao động
Kết quả: <PROD_TRACE_OUT>/_luongmoi/<giờ>/<mã>.json + tong_hop.md. Chứa dữ liệu thật, không commit.
"""
