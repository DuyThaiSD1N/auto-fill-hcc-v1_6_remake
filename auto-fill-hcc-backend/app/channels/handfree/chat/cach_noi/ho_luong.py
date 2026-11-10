"""Họ luồng (nhóm cổng) của thủ tục + mô tả bước — kiến thức nghiệp vụ cho hai lớp LLM.

Lớp 1 nhận mô tả NGẮN của bước (MO_TA_BUOC) để hiểu câu nói trong ngữ cảnh; lớp 2 nhận khối kiến thức của đúng họ luồng
(MO_TA_HO + ví dụ) để chọn đúng nút / lệnh. Tách theo họ để thêm cổng mới không làm nhiễu prompt của cổng cũ.
Chỉ đọc khoá registry (không import field_review/flow — tránh vòng import).
"""

TU_PHAP = "tu_phap"
TU_PHAP_MOI = "tu_phap_moi"
LIEN_THONG = "lien_thong"
MAE = "mae"
BAC_NINH = "bac_ninh"
HKD = "hkd"
CHUNG = "chung"


def ho(proc: dict | None) -> str:
    proc = proc or {}
    if proc.get("businessWorkflow"):
        return HKD
    if proc.get("bacNinhTabFlow"):
        return BAC_NINH
    if proc.get("lienThongFlow"):
        return LIEN_THONG
    if proc.get("bxdFlow") or proc.get("maePortal"):
        return MAE
    if proc.get("flowProfile") == "tu-phap-moi" or proc.get("lizFlow"):
        return TU_PHAP_MOI
    if proc.get("wizard") or proc.get("flowProfile") == "tu-phap":
        return TU_PHAP
    return CHUNG


# Bước của trợ lý → một dòng mô tả việc đang diễn ra và điều trợ lý thường vừa hỏi / mời.
XEM_TRUOC = ("bản XEM TRƯỚC tờ khai đang mở trên cổng. Ở đây chỉ có HAI việc: nút \"Sửa lại tờ khai\" (đóng xem trước, về "
             "tờ khai để sửa / bổ sung) hoặc nút \"Xác nhận, sang Thành phần hồ sơ\". \"quay lại\", \"sửa lại\", \"tắt / đóng xem "
             "trước\", \"về tờ khai\" đều là tra_loi nút Sửa lại tờ khai — KHÔNG phải quay_lai, KHÔNG phải lam_lai (trừ khi nói "
             "rõ điền lại từ đầu theo giấy tờ). \"đúng rồi\", \"ok\", \"xác nhận\", \"tiếp\" là nút Xác nhận")


def mo_ta_buoc(state: str, conv: dict | None) -> str:
    """Mô tả bước cho prompt; bước có ngữ cảnh con khác hẳn (xem trước đang mở) thì mô tả theo ngữ cảnh đó."""
    if state == "reviewing" and ((conv or {}).get("field_review") or {}).get("preview_open"):
        return XEM_TRUOC
    return MO_TA_BUOC.get(state, "bước khác")


MO_TA_BUOC: dict[str, str] = {
    "greet": "màn chào: trợ lý mời chọn hoặc nói tên thủ tục; chưa có hồ sơ nào",
    "confirm_procedure": "trợ lý vừa đọc lại thủ tục + nơi làm (tỉnh, xã) + người làm và hỏi 'đúng không?'",
    "choose_variant": "trợ lý hỏi chọn trường hợp giải quyết của thủ tục (cấp mới / cấp lại / nhà ở / công trình…)",
    "choose_mae_dialog": "cổng mở hộp thoại chọn nơi xử lý / trường hợp; trợ lý đọc danh sách và hỏi chọn số mấy",
    "guide_login": "trợ lý đang chờ công dân đăng nhập VNeID trên cổng (quét QR, nhập mã); hoặc đang ở bước Thông "
                   "tin chủ hồ sơ của cổng",
    "consent": "trợ lý hỏi công dân có đồng ý cho đọc giấy tờ và tự điền không",
    "ask_doc_method": "trợ lý hỏi gửi giấy tờ bằng cách nào: chụp bằng điện thoại (QR) hay scan / chọn tệp tại quầy",
    "qr_waiting": "đang chờ công dân chụp giấy tờ bằng điện thoại qua mã QR",
    "collecting_docs": "đang nhận giấy tờ (scan / chọn tệp); hoặc đang mở lại danh sách giấy để điều chỉnh (thêm, xoá) "
                       "trước khi điền lại",
    "choosing_attach_mode": "trợ lý hỏi đính kèm các tệp vào một hồ sơ hay tách mỗi tệp một hồ sơ",
    "owner_filling": "trợ lý đang đọc giấy tờ và điền khối Thông tin chủ hồ sơ (đang chạy, chưa xong)",
    "owner_waiting_next": "đã điền xong Thông tin chủ hồ sơ; trợ lý mời kiểm tra rồi sang bước kê khai",
    "filling": "trợ lý đang đọc giấy tờ và điền tờ khai (đang chạy, chưa xong)",
    "reviewing": "đã điền xong tờ khai; trợ lý báo số ô đã điền / còn trống và mời: bổ sung ô trống, xem trước tờ "
                 "khai, điền lại, hoặc điều chỉnh giấy tờ",
    "attaching": "đang / vừa đính kèm giấy tờ vào Thành phần hồ sơ",
    "done": "đã đính kèm xong; công dân rà lại rồi tự bấm Bước tiếp theo / chọn cách nhận kết quả / Gửi hồ sơ; hoặc "
            "đã nộp xong (đánh giá, đăng xuất)",
}

# Kiến thức theo họ luồng cho lớp 2: các bước trên cổng, nghĩa thật của từng nút / lệnh hay bị lẫn.
MO_TA_HO: dict[str, str] = {
    TU_PHAP: """Cổng tư pháp (dichvucongnganhtuphap.moj.gov.vn), wizard 4 bước: 1 Thông tin chủ hồ sơ → 2 Kê khai thông tin
(tờ khai điện tử trong iframe) → 3 Thành phần hồ sơ (đính kèm) → 4 Thông tin nhận kết quả (chọn cách nhận, Gửi hồ sơ).
Nghĩa các nút / lệnh:
- "Bổ sung các thông tin còn thiếu" (field_review_start): trợ lý hỏi lần lượt từng ô trống rồi điền; cũng là đường SỬA
  một ô đã điền ("sửa tên vợ", "chỉnh lại ngày sinh").
- "Xem trước tờ khai" (field_review_preview): mở bản xem trước trên cổng — đây là bước ĐI TIẾP sau khi điền xong.
- "Xác nhận, sang Thành phần hồ sơ" (field_review_confirm): xác nhận bản xem trước, cổng sang bước 3, trợ lý tự đính kèm.
- "Điền lại thông tin" (refill): đọc lại giấy tờ và ĐIỀN LẠI CẢ TỜ KHAI — mất phần đã bổ sung. Chỉ khi công dân nói rõ
  tờ khai sai nhiều, muốn làm lại từ đầu.
- "Điều chỉnh giấy tờ" (add_documents): mở lại danh sách giấy đã nhận để xem / xoá / thêm giấy. Chỉ khi công dân nói về
  GIẤY TỜ (thiếu giấy, thêm giấy, chụp lại, xoá tệp).
- "Hoàn tất điều chỉnh, điền lại tờ khai" (docs_done khi đang điều chỉnh): chốt giấy mới → đọc lại và điền lại cả tờ khai.
- "Đã đưa đủ giấy tờ, điền tờ khai đi" (docs_done / docs_complete): chốt giấy lần đầu → bắt đầu đọc và điền.
- "Xong, sang bước điền tờ khai" (field_review_owner_next) / "Xong, sang bước nhận kết quả" (guided_next): bấm nút chuyển
  bước của cổng.
- "Quay lại bước trước" (step_back): bấm nút Quay lại của cổng (3 → 2, 2 → 1).
- "đính kèm đi" (request_attach) / "đúng rồi, đã kiểm tra" (confirm_review): ở bước 2 chỉ nhắc sang bước 3; ở bước 3 chạy đính kèm.""",
    TU_PHAP_MOI: """Cổng DVC quốc gia nộp một trang (dichvucong.gov.vn): tờ khai, đính kèm và cách nhận kết quả nằm CÙNG một trang;
không có nút Quay lại bước. Sau khi điền: "Bổ sung các thông tin còn thiếu" hỏi ô trống; đủ ô bắt buộc thì nút đính kèm
thành phần hồ sơ (tpm_attach) → chọn cách nhận kết quả → nút nộp (tpm_submit, chỉ chạy sau khi hỏi xác nhận).
"Điền lại thông tin" (refill) đọc lại giấy và điền lại cả trang; "Điều chỉnh giấy tờ" (add_documents) mở lại danh sách giấy.""",
    LIEN_THONG: """Cổng liên thông (lienthong.dichvucong.gov.vn), 6 bước Angular: chọn cơ quan → kê khai → xem lại tờ khai chi
tiết → đính kèm → cách nhận kết quả → nộp. Nút đi tiếp: "Sang bước Kê khai" (lt_agency), "Xem lại tờ khai" (lt_next),
"Sang bước đính kèm", "Chọn cách nhận kết quả", "Nộp hồ sơ" (hỏi xác nhận). "Quay lại sửa tờ khai" (lt_back) lùi một bước
trên cổng. "Thử chuyển bước lại" (lt_retry) khi cổng chặn.""",
    MAE: """Cổng iGate (Bộ Y tế, Nội vụ, Công thương, Xây dựng…), stepper 4 bước: Thông tin hồ sơ → Thành phần hồ sơ → Thông
tin phí → Nộp hồ sơ. Hộp thoại "Thông tin chung" chọn nơi xử lý / trường hợp giải quyết bằng SỐ THỨ TỰ (mae_pick_N) hoặc
tên. Nút đi tiếp: "Sang Thành phần hồ sơ" (bxd_next), "Sang hình thức nhận kết quả", "Nộp hồ sơ" (hỏi xác nhận).""",
    BAC_NINH: """Cổng Bắc Ninh (Liferay, nhiều tab): tab thông tin → tab thành phần hồ sơ → tab nhận kết quả → nộp. Trợ lý hỏi cơ
quan tiếp nhận bằng thẻ; nút đi tiếp theo tab (bn_next), "Lưu và sang bước tiếp theo", "Chọn gửi / nhận kết quả qua bưu
điện"; "Đính kèm lại" (bn_attach_retry) khi đính hỏng.""",
    HKD: """Đăng ký hộ kinh doanh (HkdOnline), 8 trang điền liên tiếp. Trợ lý hỏi đáp từng mục khi không có tờ khai; "Điền lại"
(business_refill) chạy lại máy điền với dữ liệu đã đọc; "Tải tờ khai bản giấy" tải docx.""",
    CHUNG: """Thủ tục chưa khai họ luồng riêng: dùng nghĩa chung của nút / lệnh như cổng tư pháp.""",
}

# Ví dụ cho lớp 2 — MÔ TẢ tình huống, không dữ liệu thật. Mỗi dòng: câu nói → nút / lệnh đúng (hoặc không rõ).
VI_DU_HO: dict[str, list[str]] = {
    TU_PHAP: [
        'Điền xong tờ khai, nút hiện: Bổ sung · Xem trước · Điền lại · Điều chỉnh giấy tờ. Câu "chuyển sang bước tiếp theo" '
        '→ nút Xem trước tờ khai (đi tiếp), KHÔNG phải Điều chỉnh giấy tờ.',
        'Cùng màn, câu "tên vợ sai rồi, sửa giúp" → nút Bổ sung các thông tin còn thiếu (sửa một ô), KHÔNG phải Điền lại.',
        'Cùng màn, câu "điền sai hết rồi, làm lại từ đầu đi" → Điền lại thông tin.',
        'Cùng màn, câu "tôi quên chưa đưa giấy khai sinh" → Điều chỉnh giấy tờ.',
        'Đang điều chỉnh giấy tờ, nút hiện: Hoàn tất điều chỉnh, điền lại tờ khai · Chọn thêm tệp. Câu "chuyển sang bước" → '
        'không rõ (có thể muốn điền lại hoặc bỏ qua điều chỉnh) → khong_ro.',
        'Ở Thành phần hồ sơ, nút hiện: Xong, sang bước nhận kết quả. Câu "ok xong rồi sang tiếp đi" → nút đó.',
        'Ở Thành phần hồ sơ, câu "quay về sửa tờ khai" → lệnh step_back.',
        'Thông tin chủ hồ sơ đã điền, nút hiện: Xong, sang bước điền tờ khai · Điền lại thông tin chủ hồ sơ. Câu "đúng rồi đấy" → '
        'nút Xong, sang bước điền tờ khai.',
    ],
    TU_PHAP_MOI: [
        'Điền xong, nút hiện: Bổ sung · Đính kèm thành phần hồ sơ. Câu "xong rồi tiếp đi" → Đính kèm thành phần hồ sơ.',
        'Câu "sửa lại số điện thoại" → Bổ sung các thông tin còn thiếu.',
    ],
    LIEN_THONG: [
        'Kê khai xong, nút hiện: Xem lại tờ khai · Quay lại sửa tờ khai. Câu "tiếp tục đi" → Xem lại tờ khai.',
        'Câu "cho tôi sửa lại tờ khai" → Quay lại sửa tờ khai.',
    ],
    MAE: [
        'Hộp thoại chọn trường hợp, trợ lý đọc 3 lựa chọn. Câu "cái thứ hai" → mae_pick_2.',
        'Thông tin hồ sơ xong, nút hiện: Sang Thành phần hồ sơ. Câu "sang bước tiếp" → nút đó.',
    ],
    BAC_NINH: [
        'Tab thông tin xong, nút hiện: Lưu và sang bước tiếp theo. Câu "lưu rồi đi tiếp" → nút đó.',
    ],
    HKD: [
        'Trợ lý vừa đọc lại dữ liệu đã điền, nút hiện: Điền lại · Tải tờ khai bản giấy. Câu "làm lại đi" → Điền lại.',
    ],
    CHUNG: [
        'Câu khớp rõ việc của một nút → chọn nút đó; không nút nào khớp rõ → khong_ro.',
    ],
}
