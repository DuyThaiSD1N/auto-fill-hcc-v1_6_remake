"""Nhận diện thao tác NỘP HỒ SƠ trên cổng — khoá theo CỔNG, không theo thủ tục.

Dùng để chấm mốc "công dân đã bấm Gửi hồ sơ": căn cứ phân biệt hồ sơ THẬT với hồ sơ làm
dở/thử, và là mốc kết thúc để tính thời gian làm hồ sơ (xem app/dossiers/repo.py).

Tách khỏi registry.py vì đây là đặc tính NỀN TẢNG của cổng, không phải metadata thủ tục:
một luật phục vụ mọi thủ tục chạy trên cùng cổng đó.

Khai ở BE để thêm cổng mới KHÔNG phải phát hành lại extension — content script nhận luật
qua action `arm_submit_watch`.

Đã đối chiếu 15 snapshot thật của cổng tư pháp (8 thủ tục, đủ 4 bước):
    bước 1  id=kt_buoc-tiep-theo-cho-ban-than  "Bước tiếp theo"
    bước 2  id=xem-truoc-to-khai               "Xem trước"
    bước 3  (không có nút btn-next trong snapshot)
    bước 4  id=kt_gui-ho-so                    "Gửi hồ sơ"   ← chỉ bước cuối mới có

BẪY 1: data-e2e="btn-next" DÙNG CHUNG mọi bước → tuyệt đối không khớp theo thuộc tính đó,
       bấm "Bước tiếp theo" ở bước 1 sẽ bị tính là đã nộp.
BẪY 2: id sinh từ nhãn nút (kt_ + slug) nên đổi nhãn là đổi CẢ id lẫn text, không cái nào
       cứu cái nào → giữ sẵn cả hai biến thể "gửi/nộp hồ sơ" trong buttonText.

Cách khớp ở content script: URL đúng VÀ (id trùng HOẶC nhãn trùng).
"""

# urlPattern khớp NGUYÊN pathname (không phải "contains"): trang chủ, hồ sơ của tôi,
# tra cứu… đều bị loại. Group 1 = mã hồ sơ nháp của cổng, lưu để đối chiếu về sau.
#
# Sai kiểu "thiếu" (cổng đổi nhãn → ngừng ghi) chấp nhận được vì vá là sửa 1 dòng ở đây;
# sai kiểu "thừa" (tính nhầm cú bấm khác thành nộp) thì làm hỏng báo cáo mà không ai biết.
# urlPattern khớp `pathname + hash` (KHÔNG có query): cổng SPA như liên thông để đường dẫn
# trong hash, bỏ hash là không phân biệt được trang nào.
#
# Khớp = URL đúng VÀ (buttonSelector khớp HOẶC id trùng HOẶC nhãn trùng).
#
# `successText` (tùy chọn) — LƯỚI ĐỠ khi cú bấm rớt: dò chữ trên MÀN KẾT QUẢ sau khi nộp.
# Danh sách các NHÓM cụm đã bỏ dấu; trang khớp khi chứa ĐỦ mọi cụm của ÍT NHẤT một nhóm, và
# vẫn phải qua urlPattern. Chỉ khai cho cổng mà màn kết quả không có câu "nộp/gửi hồ sơ thành
# công" (extension đã dò sẵn câu đó cho mọi cổng). Mỗi cụm phải là câu RIÊNG của màn kết quả —
# "thành công" hay "mã hồ sơ" trơn thì màn tra cứu cũng có.
_FORMIO = {
    # Nền tảng Form.io/Angular dùng chung ở 10 cổng (xem danh sách cuối file): nút cuối KHÔNG có
    # id, và NHÃN đổi theo từng cổng/thủ tục — đã gặp đủ ba biến thể "Nộp hồ sơ", "Tiếp tục",
    # "Thanh toán" (có phí). Thứ ổn định duy nhất là form="captchaForm"; đã kiểm snapshot màn cuối
    # của CẢ MƯỜI cổng: mỗi trang đúng MỘT phần tử mang thuộc tính này, và nó luôn nằm trong khối
    # captcha của bước cuối.
    # KHÔNG khớp theo class btn_next — class đó dùng chung với nút "Tiếp tục" của các bước trước
    # (snapshot Bộ Y tế/MAE có tới 4 nút btn_next, chỉ 1 nút mang form="captchaForm").
    #
    # BẪY TÊN BƯỚC — đừng "sửa" luật cho khớp muộn hơn. Stepper 4 bước:
    #     1 Thông tin hồ sơ · 2 Thành phần hồ sơ
    #     3 Phí, lệ phí / Hình thức nhận kết quả  ← captcha + NÚT NỘP nằm ở ĐÂY
    #     4 "Nộp hồ sơ"                           ← màn BÁO KẾT QUẢ, KHÔNG có nút nào
    # Bước 4 mang tên "Nộp hồ sơ" nhưng là bước ĐÃ nộp xong, không phải bước ĐỂ nộp: đã soi
    # panel cdk-step-content-0-3 của cả 10 snapshot — 0 nút, nội dung là "Nộp hồ sơ thành công
    # / Hồ sơ đang chờ tiếp nhận". Nút captchaForm nằm ở panel bước 3 và KHÔNG bị ẩn.
    "urlPattern": r"^/vi/padsvc/apply-online/[0-9a-f]{24}$",
    "buttonSelector": 'button[form="captchaForm"]',
    # LƯỚI THỨ HAI cho ngày cổng nâng cấp Angular và bỏ mất thuộc tính form= — mất nó là
    # MƯỜI cổng tắt tiếng cùng lúc. Đã đếm trên toàn bộ snapshot Form.io (10 cổng, cả bước
    # giữa lẫn màn cuối): hai nhãn này xuất hiện ĐÚNG ở nút cuối và không ở đâu khác.
    # TUYỆT ĐỐI KHÔNG thêm "tiep tuc": nhãn đó có 206 lần ở các BƯỚC GIỮA — thêm vào là mỗi
    # hồ sơ bị đếm thành cả chục lần nộp.
    "buttonText": ["nop ho so", "thanh toan"],
}

# Nền eForm "nộp hồ sơ theo mã" — cổng ngành tư pháp và Quảng Ninh dùng CHUNG: cùng dạng URL
# /nop-ho-so/<số>, cùng id nút cuối kt_gui-ho-so (id sinh từ nhãn: kt_ + slug).
# BẪY: data-e2e="btn-next" có mặt ở MỌI bước nên tuyệt đối không khớp theo thuộc tính đó —
# snapshot Quảng Ninh cho thấy chính nút "Gửi hồ sơ" cũng mang data-e2e="btn-next".
_NOP_HO_SO = {
    "urlPattern": r"^/nop-ho-so/(\d+)$",
    "buttonIds": ["kt_gui-ho-so"],
    "buttonText": ["gui ho so", "nop ho so"],
}

PORTAL_SUBMIT: dict[str, dict] = {
    # Cổng ngành tư pháp — wizard 4 bước cùng một URL; id nút đổi theo từng bước.
    "dichvucongnganhtuphap.moj.gov.vn": _NOP_HO_SO,
    # Quảng Ninh — cùng nền eForm với cổng tư pháp, đã đối chiếu snapshot màn cuối
    # (/nop-ho-so/145156): <button id="kt_gui-ho-so">Gửi hồ sơ</button>.
    "dichvucong.quangninh.gov.vn": _NOP_HO_SO,
    # Lai Châu — nền RIÊNG, wizard 4 bước mỗi bước một pathname.
    # BẪY: id="btn-next" và nhãn "Đồng ý và tiếp tục" DÙNG CHUNG với bước 2 (nhap-thong-tin-ho-so),
    # nên pathname là thứ DUY NHẤT tách được bước cuối — bỏ urlPattern là bước 2 bị tính thành nộp.
    "dichvucong.laichau.gov.vn": {
        "urlPattern": r"^/dich-vu-cong/tiep-nhan-online/nhap-le-phi-ho-so$",
        "buttonIds": ["btn-next"],
        "buttonText": ["dong y va tiep tuc"],
    },
    # Liên thông khai sinh (Angular, định tuyến bằng hash). id="next" DÙNG CHUNG mọi bước nên
    # tuyệt đối không khai buttonIds — chỉ bước cuối mới đổi nhãn thành "Hoàn thành".
    "lienthong.dichvucong.gov.vn": {
        "urlPattern": r"^/#/ke-khai/([\d.]+)$",
        "buttonText": ["hoan thanh"],
        # Màn kết quả KHÔNG có chữ "thành công" nên câu dò chung của extension trượt hẳn —
        # cú bấm mà rớt là mất dấu hồ sơ. Màn này giữ nguyên URL /#/ke-khai/<mã> và chỉ hiện:
        #   "Vui lòng ghi nhớ các thông tin bên dưới để theo dõi tình hình xử lý…
        #    Số hồ sơ: G22.99.08-… · Ngày hẹn trả dự kiến: dd/mm/yyyy"
        # Đã soát cả 10 snapshot bước 1→5: không bước nào chứa cụm nào trong ba cụm này.
        # Bắt buộc ĐỦ cả ba. "Ngày hẹn trả dự kiến" là mỏ neo chặt nhất: chỉ hồ sơ ĐÃ tiếp nhận
        # mới có ngày hẹn trả — lưu nháp nếu có hiện "ghi nhớ… số hồ sơ" cũng không có dòng này.
        "successText": [[
            "vui long ghi nho cac thong tin ben duoi",
            "so ho so",
            "ngay hen tra du kien",
        ]],
    },
    # Bắc Ninh (Liferay portlet). Cả 4 tab nằm sẵn trong DOM, chỉ ẩn/hiện — nhưng ta bắt CLICK
    # nên tab ẩn không bấm được, không cần gác thêm bước.
    "dichvucong.bacninh.gov.vn": {
        "urlPattern": r"^/web/guest/eform$",
        "buttonIds": ["_org_bn_hoso_noptructuyen_nopTrucTuyen"],
        "buttonText": ["nop ho so"],
    },
    # Đăng ký hộ kinh doanh (HkdOnline, ASP.NET WebForms). Mỗi bước là MỘT trang .aspx riêng
    # nên pathname đủ khoá bước cuối: ConfirmPrepare.aspx chỉ xuất hiện ở màn xác nhận nộp.
    # Nút là <input type="submit"> — không phải <button>/<a> — và nhãn nằm ở value.
    # LƯU Ý: nút này bung confirm() của trình duyệt. Ta bắt ở pha capture nên vẫn ghi kể cả khi
    # cán bộ bấm Cancel → đếm THỪA ở cổng này. Chấp nhận: bấm rồi huỷ là chuyện hiếm.
    "hokinhdoanh.dkkd.gov.vn": {
        "urlPattern": r"^/HkdOnline/Forms/APP/ConfirmPrepare\.aspx$",
        "buttonIds": ["ctl00_C_BtnSave"],
        "buttonText": ["nop ho so vao co quan dkkd"],
    },
    # Bộ VHTTDL — nền RIÊNG (Angular Material liz-*), KHÔNG phải Form.io: không có captcha, và
    # pathname /nop-ho-so dùng chung cho mọi bước (bước nằm ở query + stepper) nên URL không tách
    # được bước. Mỏ neo duy nhất là NHÃN: cả trang chỉ có nút này mang chữ "nộp hồ sơ", không hề
    # có nút "Tiếp tục"/"Bước tiếp theo" để lẫn. Nút cũng không có id.
    # Bấm sớm không sợ đếm thừa: snapshot cho thấy nút ở trạng thái disabled="" khi chưa đủ điều
    # kiện, mà <button disabled> thì không phát sự kiện click.
    "dichvucong.bvhttdl.gov.vn": {
        "urlPattern": r"^/nop-ho-so$",
        "buttonText": ["luu va nop ho so"],
        # Lưới thứ hai phòng khi cổng đổi nhãn nút. Đã soi cả hai snapshot (bước điền và màn
        # cuối): class `style_btn` CHỈ có ở nút nộp — nút "Đóng" mang `style_btn_close`, là
        # token class khác nên selector không dính.
        "buttonSelector": "button.style_btn",
    },
    # Mười cổng dưới đây chạy CÙNG nền Form.io/iGate, mỗi cổng đã đối chiếu snapshot màn cuối riêng.
    "dichvucong.danang.gov.vn": _FORMIO,
    "dvc.moc.gov.vn": _FORMIO,
    "dichvucong.ninhbinh.gov.vn": _FORMIO,      # nhãn nút cuối: "Thanh toán"
    "dichvucong.lamdong.gov.vn": _FORMIO,       # nhãn nút cuối: "Thanh toán"
    "dichvucongnnmt.mae.gov.vn": _FORMIO,       # nhãn nút cuối: "Tiếp tục"
    "dichvucongbyt.moh.gov.vn": _FORMIO,        # nhãn nút cuối: "Tiếp tục"
    "dichvucong.quangngai.gov.vn": _FORMIO,     # nhãn nút cuối: "Tiếp tục"
    "dichvucongbnv.moha.gov.vn": _FORMIO,       # nhãn nút cuối: "Tiếp tục"
    "dvc.moet.gov.vn": _FORMIO,                 # nhãn nút cuối: "Tiếp tục"
    "dichvucong-tthc.moit.gov.vn": _FORMIO,     # nhãn nút cuối: "Nộp hồ sơ"
}


def portal_submit_rules() -> dict[str, dict]:
    """Bộ luật đẩy xuống content script qua action arm_submit_watch."""
    return PORTAL_SUBMIT
