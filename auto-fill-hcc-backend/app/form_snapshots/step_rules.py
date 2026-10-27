"""Nhận diện cú bấm RỜI BƯỚC KÊ KHAI (sang đính kèm) — mốc chụp giá trị form cán bộ đã chốt.

Cùng dạng luật với portal_submit.py: khớp = URL đúng (pathname + hash) VÀ (id trùng HOẶC nhãn
bỏ dấu trùng nguyên văn HOẶC el.matches(buttonSelector)); có `dialogText` thì nút còn phải nằm
trong [role=dialog] chứa cụm đó. Mỗi cổng là DANH SÁCH luật (một cổng có thể có vài nút rời bước).

Cổng một trang (form + đính kèm cùng trang) không có nút rời bước → dùng nút nộp.
"""
from app.procedures.portal_submit import PORTAL_SUBMIT, _FORMIO

# Panel bước 1 luôn có id cdk-step-content-<n>-0 (n đổi mỗi lần Angular dựng lại stepper) và
# đúng một nút btn_next / btn_next_new (Ninh Bình); "Tiếp tục" trơn thì bước 2, 3 cũng có.
_FORMIO_STEP = [{
    "urlPattern": _FORMIO["urlPattern"],
    "buttonSelector": '[id^="cdk-step-content-"][id$="-0"] button.btn_next, '
                      '[id^="cdk-step-content-"][id$="-0"] button.btn_next_new',
}]

# Tờ khai nằm trong iframe tokhaidientu; nút ở trang ngoài. "Xác nhận" của hộp thoại xem trước
# mới sang bước đính kèm, nhưng bước 1 cũng có hộp thoại "Ghi đè…" mang nút "Xác nhận" → buộc
# theo chữ hộp thoại. Lấy cả "Xem trước": khi đó cán bộ đã kê khai xong.
_NOP_HO_SO_STEP = [
    {"urlPattern": r"^/nop-ho-so/\d+$", "buttonIds": ["xem-truoc-to-khai"]},
    {"urlPattern": r"^/nop-ho-so/\d+$", "buttonText": ["xac nhan"], "dialogText": "xem to khai"},
]

# id="next" chỉ có ở trang người nộp; "btn-next" cùng nhãn là các bước sau. Bấm là POST tải lại trang.
_LAI_CHAU_STEP = [{
    "urlPattern": r"^/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-nguoi-nop-ho-so$",
    "buttonIds": ["next"],
}]

PORTAL_STEP: dict[str, list[dict]] = {
    "dichvucongnganhtuphap.moj.gov.vn": _NOP_HO_SO_STEP,
    "dichvucong.quangninh.gov.vn": _NOP_HO_SO_STEP,
    "dichvucong.laichau.gov.vn": _LAI_CHAU_STEP,
    "dichvucong.laocai.gov.vn": [
        *_LAI_CHAU_STEP,
        # Trang gộp form + đính kèm: chỉ có nút "Nộp hồ sơ".
        {"urlPattern": r"^/dich-vu-cong/tiep-nhan-online/nhapThongTinHoSo1bBKN$", "buttonIds": ["btn-next"]},
    ],
    # id="next" dùng chung 6 bước và hash không đổi; class active cộng dồn nên bước 2 = có
    # li thứ 2 active mà li thứ 3 chưa.
    "lienthong.dichvucong.gov.vn": [{
        "urlPattern": PORTAL_SUBMIT["lienthong.dichvucong.gov.vn"]["urlPattern"],
        "buttonSelector": "body:has(.head_steps li.item:nth-child(2).active)"
                          ":not(:has(.head_steps li.item:nth-child(3).active)) button#next",
    }],
    # Tab đính kèm: closest() trả thẻ <a> trong li; nút "Bước tiếp theo" dùng chung một id cho mọi
    # lần chuyển, tab đích nằm ở ĐUÔI href.
    "dichvucong.bacninh.gov.vn": [
        {"urlPattern": r"^/web/guest/eform$", "buttonSelector": 'li[data-tab-name="taithanhphan"] > a'},
        {"urlPattern": r"^/web/guest/eform$",
         "buttonSelector": "#_org_bn_hoso_noptructuyen_btnBuocTiepTheo[href$=\"'taithanhphan');\"]"},
        PORTAL_SUBMIT["dichvucong.bacninh.gov.vn"],
    ],
    "dichvucong.gov.vn": [PORTAL_SUBMIT["dichvucong.gov.vn"]],
    "dichvucong.bvhttdl.gov.vn": [PORTAL_SUBMIT["dichvucong.bvhttdl.gov.vn"]],
    **{host: _FORMIO_STEP for host, rule in PORTAL_SUBMIT.items() if rule is _FORMIO},
}


def portal_step_rules() -> dict[str, list[dict]]:
    return PORTAL_STEP


def form_snapshot_config(request_id: str) -> dict:
    return {"requestId": request_id, "stepRules": PORTAL_STEP}
