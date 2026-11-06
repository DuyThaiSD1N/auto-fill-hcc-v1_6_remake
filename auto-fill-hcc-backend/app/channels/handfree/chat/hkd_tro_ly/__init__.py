"""Trợ lý hộ kinh doanh: thành lập hộ kinh doanh bằng hỏi đáp, đi lần lượt TỪNG KHỐI trên cổng HkdOnline.

Mỗi khối: mở khối (extension bấm menu) → điền sẵn ô đã biết → trỏ từng ô còn thiếu, hỏi, điền ngay ô đó → đọc lại
và chờ công dân xác nhận "Lưu khối này" (khối không phải hỏi gì thì tự lưu) → extension chạy máy điền HkdOnline cho
đúng MỘT trang (pageOrder 1 trang: thêm mã ngành, chọn địa chỉ tỉnh → xã, sao chép tài khoản, tạo thành viên… như
luồng có tờ khai) và báo business_report → sang khối kế. Cổng reload toàn trang sau mỗi postback nên BE giữ trạng thái
(khối nào, ô nào); extension chỉ làm từng thao tác nhỏ và báo trang đang đứng qua page_status (businessPageKey).

Hai mức, cùng một vòng:
- Không có giấy tờ (nút trên thẻ đồng ý): hỏi mọi ô, kể cả ô không bắt buộc (bỏ qua được).
- Có giấy tờ: pipeline đọc như cũ; mỗi khối điền sẵn từ giấy, chỉ hỏi ô bắt buộc còn thiếu; ngành chỉ có tên → agent
  tra mã. Tệp đính kèm chạy cùng lần lưu khối cuối.

Chỉ bật khi extension khai supportsHkdTroLy và không ở chế độ tiếng Mông (câu thoại mới chưa có bản dịch). Bản extension
cũ trên chợ không khai cờ → luồng tải tờ khai như trước.
"""
import json
import logging
import re
import time

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.hkd_tro_ly import hoi_dap, nganh_nghe
from app.channels.handfree.chat.intents import Intent, fold
from app.pipelines.dang_ky_kinh_doanh.process import mapper

logger = logging.getLogger(__name__)

CAPABILITY = "supportsHkdTroLy"
NAME_CHECK_CAPABILITY = "supportsHkdCheckName"
PREPARE_CAPABILITY = "supportsHkdPrepare"
SUBMIT_CAPABILITY = "supportsHkdSubmit"
SUBMIT_SEND = "__action:hkd_submit"
# Lối vào "không có tờ khai, giấy tờ — làm cùng trợ lý" (nút thẻ đồng ý, nút chọn cách gửi giấy, ý định nói) tạm tắt:
# công dân luôn phải đưa giấy tờ. Logic hỏi đáp không giấy giữ nguyên, bật lại = True.
NO_DOCS_ENABLED = False
MEMBERS_PAGE = "thong-tin-ve-thanh-vien"
AUTH_PAGE = "thong-tin-uy-quyen"
_OWNER_PAGE = "chu-ho-kinh-doanh"
_REG_TYPE_PAGE = "hinh-thuc-dang-ky"
_SUBMITTER_PAGE = "nguoi-nop-ho-so"
_NGANH_PAGE = "nganh-nghe-kinh-doanh"
_CONFIRM = "__xac_nhan__"
_CONFIRM_LIST = "__xac_nhan_danh_sach__"
_ACTIONS = {"hkd_no_docs", "hkd_answer", "hkd_value", "hkd_pick", "hkd_skip", "hkd_save", "hkd_resume",
            "hkd_fill_block", "hkd_fill_missing", "hkd_prepare", "hkd_submit"}
# Khối thêm dòng vào bảng của cổng (không điền ngay từng ô được): xác nhận danh sách → điền lên trang → xác nhận lưu.
_LIST_PAGES = (_NGANH_PAGE, MEMBERS_PAGE)
_SKIP_WORDS = {"khong", "khong co", "khong co a", "khong a", "bo qua", "khong co gi", "khong can"}
# Địa chỉ hỏi lần lượt từng phần (đúng thứ tự ô trên cổng: chọn tỉnh mới nạp danh sách xã). Tỉnh luôn hỏi dù cổng để
# sẵn tỉnh của tài khoản — hộ có thể kinh doanh / ở tỉnh khác.
_ADDR_PARTS = ("tinh", "xa", "diaChi")
_OPEN_RETRY_SECONDS = 8
_OPEN_MAX_TRIES = 3

# Thứ tự khối = menu "Khối dữ liệu" của cổng. "Hình thức đăng ký" không hỏi: chọn mặc định "Thành lập mới" rồi lưu.
# Khối thành viên chỉ có khi chủ thể là các thành viên hộ gia đình; khối ủy quyền chỉ có khi người nộp là người được ủy
# quyền.
_BLOCKS = [
    (_REG_TYPE_PAGE, []),
    ("dia-chi", ["dia_chi_kd", "dien_thoai", "email", "fax", "website", "khong_kd_tru_so"]),
    (_NGANH_PAGE, []),
    ("ten-ho-kinh-doanh", ["ten_ho", "ten_ho_giu", "ten_nuoc_ngoai", "ten_nuoc_ngoai_giu", "ten_viet_tat"]),
    (_OWNER_PAGE, ["chu_the", "chu_ho_la_ban", "chu_ho_ho_ten", "chu_ho_gioi_tinh", "chu_ho_ngay_sinh",
                   "chu_ho_so_dinh_danh", "noi_o"]),
    (MEMBERS_PAGE, []),
    ("thong-tin-ve-von", ["von"]),
    ("thong-tin-ve-thue", ["dia_chi_thue", "dia_chi_thue_khac", "ngay_bat_dau", "so_lao_dong"]),
    (_SUBMITTER_PAGE, ["nguoi_nop_noi_o"]),
    (AUTH_PAGE, []),
]

# Mục hỏi: loại giá trị (hoi_dap.check), "skip" = ô không bắt buộc (bỏ qua được), "optional" = chỉ hỏi khi không có
# giấy tờ (có tờ khai mà ô trống nghĩa là không kê khai), "same" = nhận "giống …".
_SLOTS = {
    "dia_chi_kd": {"kind": "address"},
    "dien_thoai": {"kind": "phone"},
    "email": {"kind": "email", "skip": True},
    "fax": {"kind": "text", "skip": True, "optional": True},
    "website": {"kind": "text", "skip": True, "optional": True},
    "khong_kd_tru_so": {"kind": "yesno", "skip": True, "optional": True},
    "ten_ho": {"kind": "text"},
    "ten_nuoc_ngoai": {"kind": "text", "skip": True, "optional": True},
    "ten_viet_tat": {"kind": "text", "skip": True, "optional": True},
    # Cổng báo có tên trùng / tương tự → hỏi giữ tên hay đổi (true = giữ).
    "ten_ho_giu": {"kind": "yesno"},
    "ten_nuoc_ngoai_giu": {"kind": "yesno"},
    "chu_ho_la_ban": {"kind": "yesno"},
    "chu_ho_ho_ten": {"kind": "text"},
    "chu_ho_gioi_tinh": {"kind": "gender"},
    "chu_ho_ngay_sinh": {"kind": "date"},
    "chu_ho_so_dinh_danh": {"kind": "id12"},
    "chu_the": {"kind": "chu_the"},
    "noi_o": {"kind": "address", "same": True},
    "von": {"kind": "money"},
    "dia_chi_thue": {"kind": "yesno"},
    "dia_chi_thue_khac": {"kind": "address"},
    "ngay_bat_dau": {"kind": "date", "skip": True},
    "so_lao_dong": {"kind": "int", "skip": True},
    "nguoi_nop_noi_o": {"kind": "address"},
}
_MEMBER_SLOTS = {
    "tv_ho_ten": {"kind": "text"},
    "tv_gioi_tinh": {"kind": "gender"},
    "tv_ngay_sinh": {"kind": "date"},
    "tv_so_dinh_danh": {"kind": "id12"},
    "tv_noi_o": {"kind": "address", "same": True},
    "tv_them": {"kind": "yesno"},
}
# Mục → field tờ khai (schema pipeline): có giấy tờ mà field đã có thì không hỏi.
_FROM_DOCS = {
    "dia_chi_kd": ("TruSo_DiaChi",),
    "dien_thoai": ("TruSo_DienThoai", "ChuHo_DienThoai"),
    "email": ("ChuHo_Email", "TruSo_Email"),
    "ten_ho": ("HoKinhDoanh_Ten",),
    "von": ("Von_SoTien",),
    "ngay_bat_dau": ("Thue_NgayBatDau",),
    "so_lao_dong": ("Thue_SoLaoDong",),
    "noi_o": ("ChuHo_DiaChi",),
    "fax": ("TruSo_Fax",),
    "website": ("TruSo_Website",),
    "ten_nuoc_ngoai": ("HoKinhDoanh_TenNuocNgoai",),
    "ten_viet_tat": ("HoKinhDoanh_TenVietTat",),
}
# Tên kiểm trùng bằng API của nút "Kiểm tra trùng tên" (extension gọi): mục tên → (loại API, field tờ khai).
_NAME_CHECK = {"ten_ho": ("vi", "HoKinhDoanh_Ten"), "ten_nuoc_ngoai": ("f", "HoKinhDoanh_TenNuocNgoai")}
# Có giấy tờ: hình thức đăng ký đã chọn lúc điền luôn → vòng bổ sung không mở lại. Người nộp vẫn đi đủ bước (sao chép
# tài khoản, so chủ hộ trên giấy, chọn vai trò, hỏi nơi ở người nộp thay), kéo theo khối Ủy quyền khi cần.
_NO_REVIEW_PAGES = (_REG_TYPE_PAGE,)
_P = "ctl00$C$"
_OWN = _P + "OWN_PCtl$PERSCtl$"
_TAX = _P + "UC_DW_TAXEditCtl$"
# Ô trên cổng của từng mục: trỏ (tô sáng) khi hỏi; mục không có _FILL_RE thì cũng là field điền ngay khi có câu trả lời.
_DOM = {
    "dia_chi_kd": [_P + "ADDRCtl$CITY_IDFld", _P + "ADDRCtl$WARD_IDFld", _P + "ADDRCtl$STREET_NUMBERFld"],
    "dien_thoai": [_P + "DCONTClt$HO_PHONEFld"],
    "email": [_P + "DCONTClt$HO_EMAILFld"],
    "fax": [_P + "DCONTClt$HO_FAXFld"],
    "website": [_P + "DCONTClt$HO_URLFld"],
    "khong_kd_tru_so": [_P + "NO_BUSINESS_HEADOFFICEld"],
    "ten_ho": [_P + "NAMEFld"],
    "ten_nuoc_ngoai": [_P + "NAME_FFld"],
    "ten_viet_tat": [_P + "SHORT_NAMEFld"],
    "chu_ho_la_ban": [_P + "OWN_PCtl$btnIS_SIGNER"],
    "chu_ho_ho_ten": [_OWN + "FULL_NAMEFld"],
    "chu_ho_gioi_tinh": [_OWN + "GENDER_IDFld"],
    "chu_ho_ngay_sinh": [_OWN + "DATE_OF_BIRTHFld"],
    "chu_ho_so_dinh_danh": [_OWN + "PERS_DOC_NOFld"],
    "chu_the": [_P + "OWNER_TYPE_RbBox"],
    "noi_o": [_OWN + "ADDRCCtl$CITY_IDFld", _OWN + "ADDRCCtl$WARD_IDFld", _OWN + "ADDRCCtl$STREET_NUMBERFld"],
    "von": [_P + "CPT_CHARTER_AMOUNTFld"],
    "dia_chi_thue": [_TAX + "REP_RECV_ADDR_TYPEFld"],
    "dia_chi_thue_khac": [_TAX + "ADDRCtl$CITY_IDFld", _TAX + "ADDRCtl$WARD_IDFld", _TAX + "ADDRCtl$STREET_NUMBERFld"],
    "ngay_bat_dau": [_TAX + "BUSINESS_START_DATEFld"],
    "so_lao_dong": [_TAX + "TOTAL_OF_LABORSFld"],
    "nguoi_nop_noi_o": [_P + "PERSCtl$ADDRCCtl$CITY_IDFld", _P + "PERSCtl$ADDRCCtl$WARD_IDFld",
                        _P + "PERSCtl$ADDRCCtl$STREET_NUMBERFld"],
}
# Mục gồm nhiều field (khối địa chỉ: quốc gia, tỉnh, xã, số nhà; nút sao chép tài khoản).
_FILL_RE = {
    "dia_chi_kd": re.compile(r"^ctl00\$C\$ADDRCtl\$"),
    "noi_o": re.compile(r"OWN_PCtl\$PERSCtl\$ADDRCCtl\$"),
    "dia_chi_thue": re.compile(r"UC_DW_TAXEditCtl\$(REP_RECV_ADDR_TYPEFld|ADDRCtl\$)"),
    "dia_chi_thue_khac": re.compile(r"UC_DW_TAXEditCtl\$(REP_RECV_ADDR_TYPEFld|ADDRCtl\$)"),
    "ten_ho": re.compile(r"\$(NAMEFld|DROP_NAME_TYPE)$"),
    "chu_ho_la_ban": re.compile(r"^__copyAccount$"),
    "nguoi_nop_noi_o": re.compile(r"^ctl00\$C\$PERSCtl\$ADDRCCtl\$"),
}


def _slot_of(name: str, key: str) -> bool:
    rx = _FILL_RE.get(key)
    return bool(rx.search(name)) if rx else name in _DOM.get(key, [])


# ── Bật / trạng thái ──

def active(conv: dict, proc: dict | None) -> bool:
    return bool(proc and proc.get("businessWorkflow") == "create"
                and (conv.get("client_capabilities") or {}).get(CAPABILITY)
                and (conv.get("lang") or "vi") != "hmong")


def asking(conv: dict) -> bool:
    st = conv.get("hkd") or {}
    return st.get("phase") in ("ask", "confirm", "confirm_list") and not st.get("paused")


def no_docs_on(conv: dict, proc: dict | None) -> bool:
    return NO_DOCS_ENABLED and active(conv, proc)


def consent_card_extra(conv: dict, proc: dict | None) -> dict:
    """Nút "không có giấy tờ" trên thẻ đồng ý — extension cũ không biết khoá này nên không vẽ."""
    return {"no_docs_label": vi.HKD_NO_DOCS_LABEL} if no_docs_on(conv, proc) else {}


def no_docs_chip(conv: dict, proc: dict | None) -> dict | None:
    if not no_docs_on(conv, proc) or conv.get("hkd"):
        return None
    return {"label": vi.HKD_NO_DOCS_LABEL, "send": "__action:hkd_no_docs"}


def needs_review(conv: dict, proc: dict | None) -> bool:
    """Pipeline đọc giấy tờ xong (business_ready) mà chưa vào vòng đi từng khối."""
    return (active(conv, proc) and conv.get("pipeline_status") == "business_ready"
            and not conv.get("hkd_checked") and not conv.get("business_action_started"))


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _join(*parts: tuple[str, str]) -> tuple[str, str]:
    return "".join(p[0] for p in parts), "".join(p[1] for p in parts)


def _reply(text: tuple[str, str], chips: list | None = None, actions: list | None = None):
    from app.channels.handfree.chat.flow import Reply
    r = Reply(text[0], text[1])
    r.actions = list(actions or [])
    r.chips = list(chips or [])
    return r


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _location(conv: dict) -> str:
    loc = conv.get("location") or {}
    return ", ".join(x for x in (loc.get("ward"), loc.get("province")) if x)


def _has(value) -> bool:
    if isinstance(value, dict):
        return bool(value.get("xa") or value.get("tinh"))
    return value not in (None, "", [])


def _spec(key: str) -> dict:
    return _SLOTS.get(key) or _MEMBER_SLOTS.get(key) or {}


def _current(st: dict, key: str):
    return (st.get("member") or {}).get(key) if key.startswith("tv_") else st["values"].get(key)


def _addr_part(value) -> str:
    """Phần địa chỉ còn phải hỏi ("" = đủ, "giống …", hoặc lấy theo giấy)."""
    if not isinstance(value, dict):
        return "" if value else "tinh"
    return next((p for p in _ADDR_PARTS if not value.get(p)), "")


def _merge_addr(old, new):
    """Ghép phần địa chỉ vừa nghe vào phần đã có; đổi sang tỉnh khác thì bỏ xã, số nhà cũ (không thuộc tỉnh mới)."""
    if not isinstance(new, dict) or not isinstance(old, dict):
        return new
    if new.get("tinh") and old.get("tinh") and fold(mapper._clean_city(new["tinh"])) != fold(
            mapper._clean_city(old["tinh"])):
        old = {}
    return {**old, **{k: v for k, v in new.items() if v}}


def _blocks(st: dict) -> list[str]:
    return [page for page, _ in _BLOCKS
            if (page != MEMBERS_PAGE or st["values"].get("chu_the") == "ho_gia_dinh")
            and (page != AUTH_PAGE or _submitter_authorized(st))]


def _submitter_authorized(st: dict) -> bool:
    """Người nộp chọn "Người được ủy quyền": người đăng nhập khác chủ hộ (trừ địa bàn ép "Người có thẩm quyền ký")."""
    return st.get("submitter_owner") is False and not st.get("force_self")


def _page(st: dict) -> str:
    return _blocks(st)[st["block"]]


def _label(page: str) -> str:
    return vi.HKD_BLOCK_LABELS.get(page, page)


# ── Mục còn phải hỏi trong khối ──

def _needed(st: dict, key: str) -> bool:
    values, skipped = st["values"], set(st.get("skipped") or [])
    value = values.get(key)
    done = not _addr_part(value) if _SLOTS[key]["kind"] == "address" else _has(value)
    if key in skipped or done or value is False:
        return False
    if key == "dia_chi_thue_khac":
        return values.get("dia_chi_thue") is False
    if key.endswith("_giu"):
        check = (st.get("name_check") or {}).get(key[:-4]) or {}
        return bool(check.get("count")) and check.get("name") == _name_value(st, key[:-4])
    if key == "nguoi_nop_noi_o":
        owner = st.get("submitter_owner")
        # Người nộp thay → luôn hỏi; chủ hộ tự nộp → lấy nơi ở chủ hộ, chỉ hỏi khi chưa có đủ (giấy không ghi nơi ở).
        return owner is False or (owner is True and _owner_address(st) is None)
    if key.startswith("chu_ho_") and key != "chu_ho_la_ban":
        return values.get("chu_ho_la_ban") is False
    if key == "chu_ho_la_ban":
        return st["mode"] == "khong_giay" or not st.get("owner_from_docs")
    if key == "chu_the":
        return st["mode"] == "khong_giay"
    if key == "ngay_bat_dau" and st.get("skip_start_date"):
        return False
    return True


def _nganh_step(st: dict) -> str:
    rows = st.get("nganh") or []
    if st.get("from_docs_codes"):
        return ""
    if not rows:
        return "nganh"
    if any(r.get("ma") and not r.get("chac") for r in rows):
        return "nganh_chon"
    if any(not r.get("ma") for r in rows):
        # Cổng chỉ nhận ngành theo mã (ghi chữ chỉ khi KHÔNG có mã nào) → dòng chưa có mã phải rõ mã hoặc bỏ.
        return "nganh_ro"
    if not st.get("nganh_done"):
        return "nganh_them"  # hỏi tới khi công dân nói hết ngành
    if len(rows) > 1 and not st.get("chinh"):
        return "nganh_chinh"  # ngành chính phải hỏi, không tự chọn (một ngành thì chính là ngành đó)
    return ""


def _member_step(st: dict) -> str:
    if st.get("members_done"):
        return ""
    member = st.get("member") or {}
    for key in ("tv_ho_ten", "tv_gioi_tinh", "tv_ngay_sinh", "tv_so_dinh_danh", "tv_noi_o"):
        value = member.get(key)
        if _addr_part(value) if key == "tv_noi_o" else not _has(value):
            return key
    return "tv_them"


def _next_field(st: dict) -> str:
    page = _page(st)
    if page == _NGANH_PAGE:
        return _nganh_step(st)
    if page == MEMBERS_PAGE:
        return _member_step(st)
    return next((k for k in dict(_BLOCKS)[page] if _needed(st, k)), "")


# ── Câu hỏi + nút ──

def _question(st: dict, key: str) -> tuple[str, str]:
    if key == "nganh_chon":
        row = next(r for r in st["nganh"] if r.get("ma") and not r.get("chac"))
        return _say(vi.HKD_QUESTIONS[key], hoat_dong=row.get("hoatDong") or "")
    if key == "nganh_ro":
        row = next(r for r in st["nganh"] if not r.get("ma"))
        return _say(vi.HKD_QUESTIONS[key], hoat_dong=row.get("hoatDong") or "")
    if key == "nganh_chinh":
        return _say(vi.HKD_QUESTIONS[key], n=len(st["nganh"]))
    if key == "nganh_them":
        names = [r.get("chiTiet") or nganh_nghe.ten(r["ma"][0]) for r in st["nganh"] if r.get("chac")]
        return _say(vi.HKD_QUESTIONS[key], list=", ".join(names))
    if key.endswith("_giu"):
        return _say(vi.HKD_QUESTIONS["ten_giu"])
    if key == "chu_ho_la_ban" and st.get("account_name"):
        return _say(vi.HKD_OWNER_IS_ACCOUNT, name=st["account_name"])
    name = (st.get("member") or {}).get("tv_ho_ten") or ""
    if _spec(key).get("kind") == "address":
        value = _current(st, key)
        part = _addr_part(value)
        if part != "tinh":
            return _say(vi.HKD_ADDR_QUESTIONS[part], what=vi.HKD_ADDR_WHAT[key].format(name=name))
    if key.startswith("tv_"):
        return _say(vi.HKD_QUESTIONS[key], i=len(st.get("members") or []) + 1, name=name)
    return _say(vi.HKD_QUESTIONS[key])


def _chips(st: dict, key: str) -> list:
    def value(label, v):
        return {"label": label, "send": f'__action:hkd_value:{{"v":{_json(v)}}}'}

    if key == "nganh_chon":
        i, row = next((i, r) for i, r in enumerate(st["nganh"]) if r.get("ma") and not r.get("chac"))
        return [{"label": f"{ma} · {nganh_nghe.ten(ma)}", "send": f'__action:hkd_pick:{{"row":{i},"ma":"{ma}"}}'}
                for ma in row["ma"]]
    if key == "nganh_ro":
        i = next(i for i, r in enumerate(st["nganh"]) if not r.get("ma"))
        return [{"label": vi.HKD_DROP_ACTIVITY_LABEL, "send": f'__action:hkd_pick:{{"row":{i},"drop":true}}'}]
    if key == "nganh_them":
        return [value(vi.HKD_NO_MORE_LABEL, False)]
    if key == "nganh_chinh":
        return [{"label": f"{r['ma'][0]} · {nganh_nghe.ten(r['ma'][0])}",
                 "send": f'__action:hkd_pick:{{"chinh":"{r["ma"][0]}"}}'} for r in st["nganh"] if r.get("chac")]
    spec = _spec(key)
    chips = []
    if key.endswith("_giu"):
        chips = [value(vi.HKD_NAME_KEEP_LABEL, True), value(vi.HKD_NAME_CHANGE_LABEL, False)]
    elif spec.get("kind") == "yesno":
        chips = [value(vi.HKD_YES_LABEL, True), value(vi.HKD_NO_LABEL, False)]
    elif spec.get("kind") == "gender":
        chips = [value(vi.HKD_MALE_LABEL, "Nam"), value(vi.HKD_FEMALE_LABEL, "Nữ")]
    elif spec.get("kind") == "chu_the":
        chips = [value(vi.HKD_INDIVIDUAL_LABEL, "ca_nhan"), value(vi.HKD_HOUSEHOLD_LABEL, "ho_gia_dinh")]
    elif spec.get("kind") == "address":
        current, loc = _current(st, key), st.get("loc") or {}
        part = _addr_part(current)
        if part == "tinh":
            if key == "noi_o":
                chips.append(value(vi.HKD_SAME_HEAD_OFFICE_LABEL, "giong"))
            elif key == "tv_noi_o":
                chips.append(value(vi.HKD_SAME_OWNER_LABEL, "giong"))
            if loc.get("province"):
                chips.append(value(loc["province"], {"tinh": loc["province"]}))  # bấm nhanh tỉnh của quầy
        elif part == "xa" and loc.get("ward") and fold(mapper._clean_city(current.get("tinh"))) == fold(
                mapper._clean_city(loc.get("province"))):
            chips.append(value(loc["ward"], {"xa": loc["ward"]}))
    if spec.get("skip"):
        chips.append({"label": vi.HKD_SKIP_LABEL, "send": "__action:hkd_skip"})
    return chips


# ── Hiển thị giá trị ──

def _addr_text(value, key: str = "") -> str:
    if value == "giong":
        return vi.HKD_VALUE_TEXT["same_owner" if key == "tv_noi_o" else "same_head_office"]
    if not isinstance(value, dict):
        return ""
    return ", ".join(v for v in (value.get("diaChi"), value.get("xa"), value.get("tinh")) if v)


def _show(key: str, value) -> tuple[str, str]:
    """(chữ hiển thị, chữ đọc) của một giá trị đã ghi."""
    kind = _spec(key).get("kind")
    if kind == "address":
        text = _addr_text(value, key)
        return text, text
    if kind in ("phone", "id12"):
        return str(value), " ".join(str(value))  # đọc từng chữ số để công dân soát
    if kind == "money":
        text = f"{int(value):,}".replace(",", ".") + " đồng"
        return text, text
    if kind == "yesno":
        if key == "chu_ho_la_ban":
            text = vi.HKD_VALUE_TEXT["account_owner" if value else "other_person"]
        elif key == "dia_chi_thue":
            text = vi.HKD_VALUE_TEXT["same_head_office" if value else "other_address"]
        elif key.endswith("_giu"):
            text = vi.HKD_NAME_KEEP_LABEL if value else vi.HKD_NAME_CHANGE_LABEL
        elif key == "khong_kd_tru_so":
            text = vi.HKD_VALUE_TEXT["at_head_office" if value else "not_at_head_office"]
        else:
            text = vi.HKD_YES_LABEL if value else vi.HKD_NO_LABEL
        return text, text
    if kind == "chu_the":
        text = vi.HKD_VALUE_TEXT["individual" if value == "ca_nhan" else "household"]
        return text, text
    return str(value), str(value)


def _noted_current(st: dict, key: str, value) -> tuple[str, str]:
    """Đọc lại giá trị sau khi ghi (địa chỉ: cả phần đã có, không chỉ phần vừa nghe)."""
    return _noted(key, _current(st, key) if _spec(key).get("kind") == "address" else value)


def _noted(key: str, value) -> tuple[str, str]:
    shown, spoken = _show(key, value)
    return _say(vi.HKD_NOTED, label=vi.HKD_LABELS.get(key, key), value=shown, value_tts=spoken)


def _nganh_lines(st: dict) -> list[str]:
    out = []
    for r in st.get("nganh") or []:
        if not r.get("chac"):
            continue
        ma = r["ma"][0]
        main = vi.HKD_VALUE_TEXT["main"] if ma == st.get("chinh") or len(st["nganh"]) == 1 else ""
        detail = f" — {vi.HKD_LABELS['chi_tiet']}: {r['chiTiet']}" if r.get("chiTiet") else ""
        out.append(f"{ma} · {nganh_nghe.ten(ma)}{main}{detail}")
    return out


def _noted_nganh(st: dict) -> tuple[str, str]:
    sure = [r for r in st.get("nganh") or [] if r.get("chac")]
    if not sure:
        return "", ""
    return _say(vi.HKD_NOTED, label=vi.HKD_LABELS["nganh"], value="; ".join(_nganh_lines(st)),
                value_tts="; ".join(r.get("chiTiet") or nganh_nghe.ten(r["ma"][0]) for r in sure))


def _block_rows(st: dict, page: str) -> list[str]:
    if page == _NGANH_PAGE:
        return [f"- {line}" for line in _nganh_lines(st)]
    if page == MEMBERS_PAGE:
        return [f"- **{vi.HKD_LABELS['thanh_vien']} {i}:** " + ", ".join(
            p for p in (m.get("tv_ho_ten"), m.get("tv_gioi_tinh"), m.get("tv_ngay_sinh"), m.get("tv_so_dinh_danh"),
                        _addr_text(m.get("tv_noi_o"), "tv_noi_o")) if p)
                for i, m in enumerate(st.get("members") or [], 1)]
    rows = []
    values, skipped = st["values"], set(st.get("skipped") or [])
    if page == _SUBMITTER_PAGE and st.get("submitter_owner") is not None:
        rows.append(f"- **{vi.HKD_LABELS['vai_tro']}:** " + (
            mapper._PERS_SUB_SELF_LABEL if st["submitter_owner"] or st.get("force_self")
            else mapper._PERS_SUB_AUTHORIZED_LABEL))
        if st["submitter_owner"] and not values.get("nguoi_nop_noi_o") and _owner_address(st):
            rows.append(f"- **{vi.HKD_LABELS['nguoi_nop_noi_o']}:** {_addr_text(_owner_address(st))} "
                        f"_({vi.HKD_VALUE_TEXT['owner_address']})_")
    for key in dict(_BLOCKS)[page]:
        if key == "dia_chi_thue_khac" or key.endswith("_giu"):
            continue
        if key in skipped:
            rows.append(f"- **{vi.HKD_LABELS[key]}:** _{vi.HKD_VALUE_TEXT['skipped']}_")
        elif values.get(key) not in (None, "__docs__") and (_has(values.get(key)) or values.get(key) is False):
            shown, _ = _show(key, values[key])
            if key == "dia_chi_thue" and values[key] is False:
                shown = _addr_text(values.get("dia_chi_thue_khac"))
            rows.append(f"- **{vi.HKD_LABELS.get(key, key)}:** {shown}")
    if st["mode"] == "bo_sung":
        rows.append(f"- _{vi.HKD_VALUE_TEXT['from_docs']}_")
    return rows


# ── Dựng field cho trang ──

def _schema_facts(st: dict) -> dict:
    facts = {k: v for k, v in (st.get("base") or {}).items() if v not in (None, "", [], {})}
    f = {k: v for k, v in st["values"].items() if v != "__docs__"}

    def put(name, value, *, only_if_empty=False):
        if value in (None, "", {}) or (only_if_empty and _has(facts.get(name))):
            return
        facts[name] = value

    put("HoKinhDoanh_Ten", f.get("ten_ho"))
    put("HoKinhDoanh_TenNuocNgoai", f.get("ten_nuoc_ngoai"))
    put("HoKinhDoanh_TenVietTat", f.get("ten_viet_tat"))
    put("TruSo_DiaChi", f.get("dia_chi_kd"))
    put("TruSo_DienThoai", f.get("dien_thoai"))
    put("ChuHo_DienThoai", f.get("dien_thoai"), only_if_empty=True)
    put("Thue_DienThoai", f.get("dien_thoai"), only_if_empty=True)
    put("TruSo_Email", f.get("email"))
    put("ChuHo_Email", f.get("email"), only_if_empty=True)
    put("Thue_Email", f.get("email"), only_if_empty=True)
    put("TruSo_Fax", f.get("fax"))
    put("TruSo_Website", f.get("website"))
    if f.get("von"):
        put("Von_SoTien", str(f["von"]))
    put("Thue_NgayBatDau", f.get("ngay_bat_dau"))
    if f.get("so_lao_dong") is not None:
        put("Thue_SoLaoDong", str(f["so_lao_dong"]))
    if f.get("dia_chi_thue") is True:
        facts.pop("Thue_DiaChiNhanThongBao", None)  # trống = giống trụ sở (mapper)
    elif f.get("dia_chi_thue") is False:
        put("Thue_DiaChiNhanThongBao", f.get("dia_chi_thue_khac"))
    put("ChuHo_HoTen", f.get("chu_ho_ho_ten"))
    put("ChuHo_GioiTinh", f.get("chu_ho_gioi_tinh"))
    put("ChuHo_NgaySinh", f.get("chu_ho_ngay_sinh"))
    put("ChuHo_SoDinhDanh", f.get("chu_ho_so_dinh_danh"))
    put("ChuHo_DiaChi", facts.get("TruSo_DiaChi") if f.get("noi_o") == "giong" else f.get("noi_o"))
    rows = [r for r in st.get("nganh") or [] if r.get("chac")]
    if rows and not st.get("from_docs_codes"):
        chinh = st.get("chinh") or (rows[0]["ma"][0] if len(rows) == 1 else "")
        # Tên gửi cho mapper = chữ ghi vào ô chi tiết của dòng ngành (extension ghi khi khác tên chuẩn của mã).
        facts["NganhNghe_DanhSach"] = [{"ma": r["ma"][0], "ten": r.get("chiTiet") or nganh_nghe.ten(r["ma"][0]),
                                        "chinh": r["ma"][0] == chinh} for r in rows]
        facts["NganhNghe_MaChinh"] = chinh
        facts.pop("NganhNghe_TenChinh", None)
    return facts


def _member_fields(member: dict, owner_address) -> list[dict]:
    prefix = "ctl00$C$MEM_PCtl$PERSCtl$"
    out = [
        {"name": f"{prefix}FULL_NAMEFld", "comp": "dom-input", "value": mapper._proper_name(member.get("tv_ho_ten"))},
        {"name": f"{prefix}GENDER_IDFld", "comp": "dom-radio", "value": mapper._gender_code(member.get("tv_gioi_tinh"))},
        {"name": f"{prefix}DATE_OF_BIRTHFld", "comp": "dom-date", "value": member.get("tv_ngay_sinh") or ""},
        {"name": f"{prefix}PERS_DOC_NOFld", "comp": "dom-input", "value": member.get("tv_so_dinh_danh") or ""},
    ]
    address = mapper._addr(owner_address if member.get("tv_noi_o") == "giong" else member.get("tv_noi_o"))
    if address:
        out += [
            {"name": f"{prefix}ADDRCCtl$COUNTRY_IDFld", "comp": "dom-select", "value": address.get("quocGia") or "Việt Nam"},
            {"name": f"{prefix}ADDRCCtl$CITY_IDFld", "comp": "dom-select", "value": address.get("tinh")},
            {"name": f"{prefix}ADDRCCtl$WARD_IDFld", "comp": "dom-select", "value": address.get("xa")},
            {"name": f"{prefix}ADDRCCtl$STREET_NUMBERFld", "comp": "dom-input", "value": address.get("diaChi")},
        ]
    return [f for f in out if f["value"]]


def page_fields(st: dict, page: str) -> list[dict]:
    """Field của một khối từ mọi giá trị đã có (mapper của pipeline + phần riêng của luồng hỏi đáp)."""
    if page == MEMBERS_PAGE:
        owner_address = _schema_facts(st).get("ChuHo_DiaChi")
        return [{"name": "__members", "comp": "raw",
                 "value": [_member_fields(m, owner_address) for m in st.get("members") or []]}]
    if page == AUTH_PAGE:
        return []
    facts = _schema_facts(st)
    fields = mapper.enrich([{"name": k, "value": v} for k, v in facts.items()], page=page,
                           skip_start_date=bool(st.get("skip_start_date")))
    values = st["values"]
    if page == "dia-chi" and isinstance(values.get("khong_kd_tru_so"), bool):
        # Ô cổng mang nghĩa NGƯỢC câu hỏi ("Không kinh doanh tại trụ sở"); gửi cả khi "có" để bỏ tích nếu vừa sửa lại.
        fields.append({"name": _P + "NO_BUSINESS_HEADOFFICEld", "comp": "dom-checkbox",
                       "value": values["khong_kd_tru_so"] is False})
    if page == _SUBMITTER_PAGE and st.get("submitter_owner") is not None:
        owner = st["submitter_owner"]
        role = mapper._PERS_SUB_SELF_LABEL if owner or st.get("force_self") else mapper._PERS_SUB_AUTHORIZED_LABEL
        prefix = _P + "PERSCtl$ADDRCCtl$"
        asked = values.get("nguoi_nop_noi_o")  # nơi ở người nộp vừa hỏi (người nộp thay / chủ hộ mà giấy thiếu nơi ở)
        fields = [{**f, "value": role} if f["name"] == _P + "PERS_SUBGroup" else f for f in fields
                  if not f["name"].startswith(prefix) or (owner and not asked)]  # người nộp thay: không lấy nơi ở chủ hộ
        plan = next((f["value"] for f in fields if f["name"] == "__applicantAddress"), None) or {}
        plan = {**plan, "role": "self" if owner else "authorized"}
        if asked:
            address = mapper._addr(asked)
            fields += _submitter_address_fields(asked)
            if address:
                # Máy điền lấy nơi ở người nộp từ đây: "other" (người nộp thay, không dò CCCD) / "self" (chủ hộ tự nộp).
                plan["other" if not owner else "self"] = address
        fields = [f for f in fields if f["name"] != "__applicantAddress"] + [
            {"name": "__applicantAddress", "comp": "raw", "value": plan}]
    if page == _OWNER_PAGE:
        if values.get("chu_ho_la_ban") is True:
            # Chủ hộ là người đang đăng nhập: nhân thân lấy bằng nút "Sao chép thông tin đăng ký tài khoản" (khớp CSDL
            # dân cư) thay vì hỏi bằng lời; nơi ở / điện thoại / email đã hỏi vẫn điền đè sau đó.
            fields.insert(0, {"name": "__copyAccount", "comp": "raw", "value": True})
        if values.get("chu_the") == "ho_gia_dinh":
            for f in fields:
                if f["name"] == _P + "OWNER_TYPE_RbBox":
                    f["value"] = "M"
    return fields


def _fill_now(st: dict, keys: list[str]) -> list[dict]:
    """Lệnh điền NGAY các mục vừa có câu trả lời (chỉ mục thuộc khối đang mở; mục khối khác điền khi tới khối đó)."""
    page = _page(st)
    own = dict(_BLOCKS).get(page) or []
    keys = [k for k in keys if k in own]
    fields = [f for f in page_fields(st, page) if any(_slot_of(f["name"], k) for k in keys)] if keys else []
    return [{"type": "hkd_fill", "page": page, "fields": fields}] if fields else []


def _prefill_fields(st: dict, page: str) -> list[dict]:
    """Điền sẵn lúc vào khối: mọi field đã có giá trị, trừ ô của mục còn phải hỏi (hỏi tới đâu điền tới đó)."""
    pending = [k for k in dict(_BLOCKS).get(page) or [] if _needed(st, k)]
    return [f for f in page_fields(st, page)
            if not f["name"].startswith("__") and not any(_slot_of(f["name"], k) for k in pending)]


# ── Chuyển khối ──

def _asking(st: dict, names: list | None = None) -> dict:
    """Lệnh trỏ ô kèm mọi câu hỏi: sidebar thấy hkd_focus mới thôi coi là "bot đang mở / lưu khối" và mở lại mic rảnh
    tay (câu hỏi không có nút như "kinh doanh gì" từng làm mic tắt mãi)."""
    return {"type": "hkd_focus", "page": _page(st), "names": names or []}


def _open_action(page: str) -> dict:
    return {"type": "hkd_open_block", "page": page, "label": _label(page)}


def _go_block(conv: dict, index: int, lead: tuple[str, str] = ("", "")):
    st = conv["hkd"]
    blocks = _blocks(st)
    if st.get("only_missing"):
        # Vòng bổ sung sau khi đã điền luôn theo giấy tờ: chỉ mở khối còn thiếu.
        while index < len(blocks) and not _missing_items(st, blocks[index]):
            index += 1
    if index >= len(blocks):
        return _finish(conv, lead)
    st.update(block=index, phase="open", field="", asked=False, open_tries=1, opened_at=time.time(),
              open_failed_said=False, list_filled=False)
    page = blocks[index]
    if page == _SUBMITTER_PAGE and not st.get("copied"):
        st["submitter_owner"] = None  # vào khối mới sao chép tài khoản rồi so với chủ hộ
    if not _next_field(st) and (page != _SUBMITTER_PAGE or st.get("copied")) and not (
            page == "ten-ho-kinh-doanh" and _name_to_check(st)):
        # Khối không phải hỏi gì: lưu thẳng — máy điền tự mở khối, không tốn một lượt mở + chờ báo đã tới khối.
        if page == _REG_TYPE_PAGE:
            lead = _join(lead, _say(vi.HKD_REG_TYPE_DEFAULT))
        elif page == AUTH_PAGE:
            lead = _join(lead, _say(vi.HKD_AUTH_SAVE))
        return _save(conv, lead)
    return _reply(lead, actions=[_open_action(blocks[index])])


def _arrive(conv: dict):
    """Extension báo đã đứng đúng khối: điền sẵn ô đã biết, rồi hỏi ô đầu tiên còn thiếu (hoặc tự lưu)."""
    st = conv["hkd"]
    page = _page(st)
    if page == _SUBMITTER_PAGE and not st.get("copied"):
        # Người nộp mặc định = tài khoản đăng nhập: bấm "Sao chép thông tin đăng ký tài khoản", extension so nhân thân
        # vừa sao chép với chủ hộ rồi báo hkd_copied → chọn vai trò người nộp.
        st["phase"] = "copy"
        copy = {"name": "__copySubmitter", "comp": "raw", "value": {"owner": _owner_identity(st)}}
        text = _join(_say(vi.HKD_BLOCK_OPEN_PLAIN, label=_label(page)), _say(vi.HKD_SUBMITTER_COPY))
        return _reply(text, actions=[{"type": "hkd_fill", "page": page, "fields": [copy]}])
    st["phase"] = "ask"
    prefill = _prefill_fields(st, page)
    actions = [{"type": "hkd_fill", "page": page, "fields": prefill}] if prefill else []
    return _ask_next(conv, _block_intro(st, page), actions)


def _block_intro(st: dict, page: str) -> tuple[str, str]:
    """"Đã vào khối X. Ở khối này công dân cung cấp cho em …" — nói gọn những gì sắp hỏi trong khối."""
    if page in _LIST_PAGES:
        keys = [page]
    else:
        keys = [k for k in dict(_BLOCKS)[page] if _needed(st, k)]
    items = list(dict.fromkeys(vi.HKD_INTRO_ITEMS[k] for k in keys))
    if not items:
        return _say(vi.HKD_BLOCK_OPEN_PLAIN, label=_label(page))
    text = items[0] if len(items) == 1 else vi.HKD_INTRO_BLOCKS.get(page) or items[0]
    return _say(vi.HKD_BLOCK_OPEN, label=_label(page), items=text)


def _submitter_address_fields(address) -> list[dict]:
    """Field nơi ở của khối người nộp (cổng không sao chép nơi ở khi bấm "Sao chép thông tin đăng ký tài khoản")."""
    address = mapper._addr(address)
    prefix = _P + "PERSCtl$ADDRCCtl$"
    return [{"name": prefix + suffix, "comp": comp, "value": address[part]}
            for suffix, comp, part in (("COUNTRY_IDFld", "dom-select", "quocGia"), ("CITY_IDFld", "dom-select", "tinh"),
                                       ("WARD_IDFld", "dom-select", "xa"), ("STREET_NUMBERFld", "dom-input", "diaChi"))
            if address.get(part)]


def _owner_address(st: dict) -> dict | None:
    """Nơi ở chủ hộ đủ tỉnh, xã, số nhà (từ giấy hoặc câu trả lời); thiếu phần nào → None."""
    address = _schema_facts(st).get("ChuHo_DiaChi")
    return address if isinstance(address, dict) and not _addr_part(address) else None


def _owner_identity(st: dict) -> dict | None:
    """Chủ hộ để so với tài khoản vừa sao chép. None = chủ hộ chính là người đăng nhập (đã nói) hoặc chưa biết."""
    if st["values"].get("chu_ho_la_ban") is True:
        return None
    facts = _schema_facts(st)
    name = str(facts.get("ChuHo_HoTen") or "").strip()
    number = re.sub(r"\D", "", str(facts.get("ChuHo_SoDinhDanh") or ""))
    return {"hoTen": name, "soDinhDanh": number} if name or number else None


def _copy_owner(conv: dict, lead: tuple[str, str], actions: list):
    """Chủ hộ là người đăng nhập: bấm "Sao chép thông tin đăng ký tài khoản" ở khối chủ hộ. Nút này reload cả trang →
    chưa hỏi gì thêm, chờ extension báo hkd_copied (trang mới đã có nhân thân) rồi mới hỏi nơi ở."""
    st = conv["hkd"]
    st["phase"] = "copy"
    return _reply(_join(lead, _say(vi.HKD_OWNER_COPY)), actions=actions)


def _on_owner_copied(conv: dict, payload: dict):
    st = conv["hkd"]
    st.update(phase="ask", owner_copied=True)
    lead = _say(vi.HKD_OWNER_COPIED if payload.get("copied") is not False else vi.HKD_OWNER_COPY_FAILED)
    return _ask_next(conv, lead)


def _on_copied(conv: dict, payload: dict):
    """Đã sao chép tài khoản vào khối người nộp: trùng chủ hộ → Người có thẩm quyền ký + nơi ở chủ hộ; khác → Người
    được ủy quyền, hỏi nơi ở người nộp (cổng không sao chép địa chỉ), lưu thêm khối Thông tin Ủy quyền."""
    st = conv["hkd"]
    same = payload.get("same")
    if st["values"].get("chu_ho_la_ban") is True:
        owner = True
    elif isinstance(same, bool):
        owner = same
    elif isinstance(st["values"].get("chu_ho_la_ban"), bool):
        owner = st["values"]["chu_ho_la_ban"]
    else:
        owner = True  # không có gì để so → giữ vai trò mặc định của cổng như máy điền
    st.update(copied=True, submitter_owner=owner, phase="ask", asked=False)
    if owner:
        lead = _say(vi.HKD_SUBMITTER_OWNER if _owner_address(st) else vi.HKD_SUBMITTER_OWNER_ASK)
    elif st.get("force_self"):
        lead = _say(vi.HKD_SUBMITTER_OTHER_FORCED)
    else:
        lead = _say(vi.HKD_SUBMITTER_OTHER)
    if payload.get("copied") is False:
        lead = _join(_say(vi.HKD_SUBMITTER_COPY_FAILED), lead)
    actions = []
    if not owner and not st.get("force_self"):
        role = {"name": _P + "PERS_SUBGroup", "comp": "dom-radio", "value": mapper._PERS_SUB_AUTHORIZED_LABEL}
        actions.append({"type": "hkd_fill", "page": _SUBMITTER_PAGE, "fields": [role]})
    if owner and _owner_address(st):
        # Điền NGAY nơi ở chủ hộ vào khối người nộp rồi chờ công dân xác nhận Lưu: để máy điền làm lúc Lưu thì các
        # postback (sao chép, chọn tỉnh → xã) hay trả khối về tỉnh của tài khoản, xã / số nhà trống mà vẫn lưu.
        actions.append({"type": "hkd_fill", "page": _SUBMITTER_PAGE,
                        "fields": _submitter_address_fields(_owner_address(st))})
        st["asked"] = True
    return _ask_next(conv, lead, actions)


def _ask_next(conv: dict, lead: tuple[str, str] = ("", ""), actions: list | None = None):
    st = conv["hkd"]
    page = _page(st)
    actions = list(actions or [])
    check = _name_to_check(st) if page == "ten-ho-kinh-doanh" else ""
    if check:
        # Vừa có tên (lời nói hoặc giấy) → kiểm trùng trên cổng trước khi hỏi tiếp; extension báo hkd_name_checked.
        st.update(phase="check_name", field="", asked=True)
        actions.append({"type": "hkd_check_name", "page": page, "slot": check, "kind": _NAME_CHECK[check][0],
                        "name": _name_value(st, check)})
        return _reply(_join(lead, _say(vi.HKD_NAME_CHECKING, name=_name_value(st, check))), actions=actions)
    key = _next_field(st)
    if key:
        st.update(phase="ask", field=key, asked=True)
        names = _DOM.get(key) or []
        if _spec(key).get("kind") == "address" and len(names) == len(_ADDR_PARTS):
            names = [names[_ADDR_PARTS.index(_addr_part(_current(st, key)))]]  # trỏ đúng ô tỉnh / xã / số nhà
        actions.append(_asking(st, names))
        return _reply(_join(lead, _question(st, key)), _chips(st, key), actions)
    if not st.get("asked"):
        return _save(conv, lead, actions)  # khối không phải hỏi gì → tự lưu
    if page in _LIST_PAGES and not st.get("list_filled"):
        # Bước 1: xác nhận danh sách trước khi thêm dòng vào bảng trên cổng.
        st.update(phase="confirm_list", field=_CONFIRM_LIST)
        text = _say(vi.HKD_LIST_CONFIRM, label=_label(page), rows="\n".join(_block_rows(st, page)))
        return _reply(_join(lead, text), [{"label": vi.HKD_LIST_FILL_LABEL, "send": "__action:hkd_fill_block",
                                           "solid": True}], actions)
    st.update(phase="confirm", field=_CONFIRM)
    if page in _LIST_PAGES:
        # Bước 2: đã điền lên trang (máy điền đã thêm dòng) → công dân xem trên trang, đúng thì lưu.
        return _reply(_join(lead, _say(vi.HKD_LIST_FILLED, label=_label(page))),
                      [{"label": vi.HKD_BLOCK_SAVE_LABEL, "send": "__action:hkd_save", "solid": True}], actions)
    actions.append({"type": "hkd_focus", "page": page, "names": []})
    text = _say(vi.HKD_BLOCK_CONFIRM, label=_label(page), rows="\n".join(_block_rows(st, page)))
    return _reply(_join(lead, text), [{"label": vi.HKD_BLOCK_SAVE_LABEL, "send": "__action:hkd_save", "solid": True}],
                  actions)


def _save(conv: dict, lead: tuple[str, str] = ("", ""), actions: list | None = None):
    """Lưu khối = máy điền HkdOnline chạy đúng một trang (điền lại toàn khối rồi bấm Lưu), báo business_report."""
    from app.channels.handfree.chat import flow
    st = conv["hkd"]
    page = _page(st)
    filling = st.get("phase") == "confirm_list"  # khối danh sách: lượt này là ĐIỀN lên trang, chưa sang khối kế
    st.update(phase="saving", field="", saving_at=time.time(), fill_only=filling)
    last = st["block"] == len(_blocks(st)) - 1
    action = {
        "type": "start_business_registration",
        "pages": {page: page_fields(st, page)},
        # Tệp đính kèm (có giấy tờ) chạy cùng lần lưu khối cuối — máy điền đính sau khi xong trang cuối.
        "attachments": (conv.get("attach_plan") or []) if last and not st.get("filled_all") else [],
        "session_id": (conv.get("upload_session_id") or "") if last and not st.get("filled_all") else "",
        "businessDefaults": flow._business_defaults(conv),
        "workflow": "create",
        "businessFlow": {"pageOrder": [page]},
    }
    owner = _owner_identity(st) if page == _SUBMITTER_PAGE else None
    if owner:
        # Máy điền tự đối chiếu tài khoản với chủ hộ ở trang người nộp — lưu từng khối nên trang chủ hộ không đi kèm.
        action["businessFlow"]["owner"] = owner
    text = _say(vi.HKD_LIST_FILLING if filling else vi.HKD_BLOCK_SAVING, label=_label(page))
    return _reply(_join(lead, text), actions=[*(actions or []), action])


def _missing_items(st: dict, page: str) -> list[str]:
    """Mục còn thiếu của một khối (khóa trong vi.HKD_INTRO_ITEMS)."""
    if page in _NO_REVIEW_PAGES:
        return []
    if page == _NGANH_PAGE:
        return [page] if _nganh_step(st) else []
    if page == MEMBERS_PAGE:
        return [page] if _member_step(st) else []
    if page == _SUBMITTER_PAGE and not st.get("copied"):
        return [page]
    if page == AUTH_PAGE:
        return [page]  # chỉ có trong danh sách khối khi người nộp là người được ủy quyền
    items = [k for k in dict(_BLOCKS)[page] if _needed(st, k)]
    if page == "ten-ho-kinh-doanh" and _name_to_check(st):
        items.append("kiem_tra_ten")  # tên lấy từ giấy chưa kiểm trùng trên cổng
    return items


def _name_value(st: dict, key: str) -> str:
    value = st["values"].get(key)
    if value == "__docs__":
        value = (st.get("base") or {}).get(_NAME_CHECK[key][1])
    return str(value or "").strip().upper() if isinstance(value, str) else ""


def _name_to_check(st: dict) -> str:
    """Mục tên đã có giá trị mà chưa kiểm trùng với đúng tên đó (chỉ khi extension khai biết gọi API kiểm)."""
    if not st.get("name_check_on"):
        return ""
    return next((k for k in _NAME_CHECK if _name_value(st, k)
                 and ((st.get("name_check") or {}).get(k) or {}).get("name") != _name_value(st, k)), "")


def _on_name_checked(conv: dict, payload: dict):
    """Kết quả "Kiểm tra trùng tên": không trùng → hỏi tiếp; có trùng / tương tự → đọc danh sách, hỏi giữ hay đổi."""
    st = conv["hkd"]
    key = str(payload.get("slot") or "")
    if key not in _NAME_CHECK:
        return _reply(("", ""))
    text = str(payload.get("text") or "")
    names = [str(n).strip() for n in payload.get("names") or [] if str(n).strip()][:50]
    m = re.search(r"\bCó\s+(\d+)\s+Hộ", text)
    count = int(m.group(1)) if m else (0 if "Không có" in text else len(names))
    name = str(payload.get("name") or "")
    exact = sum(1 for n in names if fold(n) == fold(name))
    st.setdefault("name_check", {})[key] = {"name": name, "count": count if payload.get("ok") else 0,
                                           "names": names, "exact": exact}
    st["phase"] = "ask"
    if not payload.get("ok"):
        return _ask_next(conv, _say(vi.HKD_NAME_CHECK_FAILED))
    if not count:
        return _ask_next(conv, _say(vi.HKD_NAME_FREE, name=name))
    shown = "; ".join(names[:5]) + ("…" if len(names) > 5 else "")
    exact_md = vi.HKD_NAME_EXACT.format(n=exact) if exact else ""
    return _ask_next(conv, _say(vi.HKD_NAME_TAKEN, n=count, name=name, names=shown, exact=exact_md))


def _fill_all(conv: dict):
    """Có giấy tờ: điền + lưu LUÔN mọi khối theo giấy (máy điền của luồng tờ khai), xong mới báo ô còn thiếu."""
    from app.channels.handfree.chat import flow
    st = conv["hkd"]
    pages = dict(conv.get("business_pages") or {}) or {p: page_fields(st, p) for p in _blocks(st)}
    if any(r.get("chac") for r in st.get("nganh") or []):
        pages[_NGANH_PAGE] = page_fields(st, _NGANH_PAGE)  # mã agent tra từ tên ngành ghi trên giấy
    st.update(block=0, phase="saving", field="", saving_at=time.time(), fill_all=True)
    action = {
        "type": "start_business_registration",
        "pages": pages,
        "attachments": conv.get("attach_plan") or [],
        "session_id": conv.get("upload_session_id") or "",
        "businessDefaults": flow._business_defaults(conv),
        "workflow": "create",
        "businessFlow": conv.get("business_flow") or None,
    }
    return _reply(_say(vi.HKD_REVIEW_START), actions=[action])


def _after_fill_all(conv: dict, payload: dict):
    """Điền luôn xong: đọc danh sách ô còn thiếu theo khối, mời bổ sung (nói "bổ sung thông tin" hoặc bấm nút)."""
    st = conv["hkd"]
    st["filled_all"] = True
    st["attached"] = max(0, int(payload.get("attached") or 0))
    lead = ("", "")
    if payload.get("ok") is not True:
        errors = [str(e) for e in payload.get("errors") or [] if e]
        lead = _say(vi.HKD_FILL_ALL_PARTIAL, error=errors[0] if errors else "cổng chưa nhận hết")
    rows, spoken = [], []
    for page in _blocks(st):
        items = list(dict.fromkeys(vi.HKD_INTRO_ITEMS[k] for k in _missing_items(st, page)))
        if items:
            rows.append(f"- **{_label(page)}:** " + ", ".join(items))
            spoken.append(f"khối {_label(page)} thiếu " + ", ".join(items))
    if not rows:
        return _finish(conv, lead)
    st.update(phase="offer", field="")
    text = _join(lead, _say(vi.HKD_MISSING_LIST, rows="\n".join(rows), items="; ".join(spoken)))
    return _reply(text, [{"label": vi.FR_CHIP, "send": "__action:hkd_fill_missing", "solid": True,
                          "desc": "bổ sung / điền các thông tin còn thiếu"}])


def _finish(conv: dict, lead: tuple[str, str]):
    st = conv["hkd"]
    attached = int(st.get("attached") or 0)
    attached_md = vi.HKD_DONE_ATTACHED.format(n=attached) if attached else ""
    if st.get("prepare_on"):
        # Lưu đủ khối → công dân rà, sửa nốt rồi bấm "Chuẩn bị hồ sơ" (Khối dữ liệu → Chuẩn bị): cổng kiểm cả hồ sơ,
        # lỗi hiện thành danh sách.
        st.update(phase="ready_prepare", field="")
        return _reply(_join(lead, _say(vi.HKD_READY_PREPARE, attached=attached_md)), [_prepare_chip()])
    return _done(conv, _join(lead, _say(vi.HKD_DONE, attached=attached_md)))


def _done(conv: dict, text: tuple[str, str]):
    st = conv["hkd"]
    st.update(phase="done", field="")
    conv["state"] = "done"
    conv["attach_done"] = True
    conv["pipeline_status"] = "business_done"
    return _reply(text)


def _prepare_chip() -> dict:
    return {"label": vi.HKD_PREPARE_LABEL, "send": "__action:hkd_prepare", "solid": True,
            "desc": "chuẩn bị hồ sơ / kiểm tra hồ sơ trên cổng"}


def _submit_chip() -> dict:
    return {"label": vi.HKD_SUBMIT_LABEL, "send": SUBMIT_SEND, "solid": True, "cta": True}


def _on_prepared(conv: dict, payload: dict):
    """Kết quả "Chuẩn bị": sang Trang xác nhận → xong (công dân tự bấm Nộp); cổng báo lỗi → đọc lỗi, mời chuẩn bị lại."""
    st = conv["hkd"]
    if payload.get("ok") is True:
        if not st.get("submit_on"):
            return _done(conv, _say(vi.HKD_PREPARED))
        r = _done(conv, _say(vi.HKD_PREPARED_SUBMIT))
        st["phase"] = "ready_submit"  # hội thoại xong (state done) nhưng còn nút Nộp hồ sơ của luồng này
        r.chips = [_submit_chip()]
        return r
    errors = [re.sub(r"\s+", " ", str(e)).strip() for e in payload.get("errors") or [] if str(e).strip()][:20]
    st.update(phase="prepare_failed", field="")
    rows = "\n".join(f"- {e}" for e in errors) or f"- {vi.HKD_PREPARE_UNKNOWN}"
    return _reply(_say(vi.HKD_PREPARE_ERRORS, rows=rows, n=len(errors) or 1),
                  [{**_prepare_chip(), "label": vi.HKD_PREPARE_RETRY_LABEL}])


async def _on_report(conv: dict, payload: dict):
    st = conv["hkd"]
    page = _page(st)
    if st.pop("fill_all", False):
        return _after_fill_all(conv, payload)
    if payload.get("ok") is True:
        st["attached"] = int(st.get("attached") or 0) + max(0, int(payload.get("attached") or 0))
        if st.pop("fill_only", False):
            st["list_filled"] = True
            return _ask_next(conv)  # đã điền danh sách lên trang → chờ công dân xác nhận lưu
        return _go_block(conv, st["block"] + 1, _say(vi.HKD_BLOCK_SAVED, label=_label(page)))
    retry = "hkd_fill_block" if st.pop("fill_only", False) else "hkd_save"
    st["phase"] = "confirm_list" if retry == "hkd_fill_block" else "confirm"
    errors = [str(e) for e in payload.get("errors") or [] if e]
    text = _say(vi.HKD_BLOCK_SAVE_FAILED, label=_label(page), error=errors[0] if errors else "cổng chưa nhận")
    return _reply(text, [{"label": vi.HKD_BLOCK_RETRY_LABEL, "send": f"__action:{retry}", "solid": True}])


def _on_page(conv: dict, here: str):
    """page_status trong lúc chờ mở khối: đúng khối → vào khối; sai khối quá lâu → mở lại (có trần)."""
    st = conv["hkd"]
    page = _page(st)
    if here == page:
        return _arrive(conv)
    if time.time() - float(st.get("opened_at") or 0) < _OPEN_RETRY_SECONDS:
        return _reply(("", ""))
    if int(st.get("open_tries") or 0) >= _OPEN_MAX_TRIES:
        if not st.get("open_failed_said"):
            st["open_failed_said"] = True
            return _reply(_say(vi.HKD_BLOCK_OPEN_FAILED, label=_label(page)), actions=[_asking(st)])
        return _reply(("", ""))
    st["open_tries"] = int(st.get("open_tries") or 0) + 1
    st["opened_at"] = time.time()
    return _reply(("", ""), actions=[_open_action(page)])


# ── Trả lời ──

def _open_slots(st: dict) -> list[dict]:
    def label(k):
        return vi.HKD_PROMPT_LABELS.get(k) or vi.HKD_LABELS.get(k, k)

    if _page(st) == MEMBERS_PAGE:
        # Khối thành viên: chỉ mục của thành viên — "ở cùng chủ hộ" không được rơi vào nơi ở của chủ hộ.
        return [{"key": k, "label": label(k), **spec} for k, spec in _MEMBER_SLOTS.items()]
    # Chỉ mục của khối đang mở: câu "giống địa chỉ kinh doanh" ở ô nơi ở không được rơi sang mục địa chỉ thuế của
    # khối sau. Câu nhiều ý trong cùng khối (địa chỉ kèm điện thoại) vẫn ghi đủ; ý của khối khác tới khối đó mới hỏi.
    keys = [k for k in dict(_BLOCKS).get(_page(st)) or []
            if (k != "chu_the" or st["mode"] == "khong_giay") and (not k.endswith("_giu") or _needed(st, k))]
    return [{"key": k, "label": label(k), **_SLOTS[k]} for k in keys]


def _apply(st: dict, key: str, value) -> None:
    if _spec(key).get("kind") == "address":
        value = _merge_addr(_current(st, key), value)
    if key.startswith("tv_"):
        if key == "tv_them":
            # Chốt thành viên đang nhập; "còn nữa" → thành viên mới, "hết" → xong vòng thành viên.
            if st.get("member"):
                st.setdefault("members", []).append(dict(st["member"]))
            st["member"] = {}
            st["members_done"] = not value
            return
        st.setdefault("member", {})[key] = value
        return
    if key.endswith("_giu"):
        check = (st.get("name_check") or {}).get(key[:-4]) or {}
        if value:
            check["count"] = 0  # công dân giữ tên dù cổng báo trùng / tương tự
        else:
            st["values"].pop(key[:-4], None)  # đổi tên → hỏi lại tên, tên mới kiểm trùng lại
        return
    st["values"][key] = value
    if key in (st.get("skipped") or []):
        st["skipped"].remove(key)


async def _lookup(st: dict, text: str) -> tuple[str, str]:
    """Agent tra mã cập nhật danh sách ngành. Trả câu hỏi lại của agent / báo lỗi (nếu có)."""
    res = await nganh_nghe.tra_cuu(text, st.get("nganh") or [])
    st.setdefault("trace", []).append({"text": text[:300], "steps": res.steps[-6:], "error": res.error})
    if res.error:
        return _say(vi.HKD_NGANH_FAILED)
    old_detail = {r["ma"][0]: r.get("chiTiet") for r in st.get("nganh") or [] if r.get("chac") and r.get("chiTiet")}
    st["nganh"] = [n.to_dict() for n in res.nganh]
    for r in st["nganh"]:
        # Dòng đã chốt từ trước giữ nguyên chi tiết công dân đã nói (model hay "chuẩn hoá" lại khi thêm ngành khác).
        if r.get("chac") and r["ma"][0] in old_detail:
            r["chiTiet"] = old_detail[r["ma"][0]]
    st.pop("from_docs_codes", None)
    sure = [r["ma"][0] for r in st["nganh"] if r.get("chac")]
    if res.chinh:
        st["chinh"] = res.chinh
    elif st.get("chinh") not in sure:
        st["chinh"] = ""  # ngành chính chỉ khi công dân nói rõ / chọn — không tự chọn
    if res.hoi_lai and not st["nganh"]:
        return res.hoi_lai, res.hoi_lai
    return "", ""


def _skip(conv: dict, lead: tuple[str, str] = ("", ""), actions: list | None = None):
    st = conv["hkd"]
    key = st.get("field") or ""
    if not _spec(key).get("skip"):
        return _ask_next(conv, _join(lead, _say(vi.HKD_REQUIRED)), actions)
    if key not in st.setdefault("skipped", []):
        st["skipped"].append(key)
    return _ask_next(conv, lead, actions)


async def _answer_nganh_them(conv: dict, text: str):
    """"Còn ngành nào khác không?": kể thêm → agent thêm dòng, hỏi tiếp; "không" → hết danh sách ngành."""
    st = conv["hkd"]
    slot = [{"key": "nganh_them", "label": "Còn kinh doanh ngành nào khác nữa không (true = còn)", "kind": "yesno"}]
    parsed = await hoi_dap.interpret(text, "nganh_them", _question(st, "nganh_them")[0], slot, {}, _location(conv))
    more = parsed.values.get("nganh_them")
    if more is False or parsed.action == "bo_qua":
        # "Không / hết rồi" trước: model đôi khi chép luôn câu đó vào nganhMoTa — không được tra thành ngành mới.
        st["nganh_done"] = True
        return _ask_next(conv)
    if parsed.nganh_text:
        lead = await _lookup(st, parsed.nganh_text)
        if lead == _say(vi.HKD_NGANH_FAILED):
            return _reply(lead, actions=[_asking(st)])
        return _ask_next(conv, _join(lead, _noted_nganh(st)) if lead[0] else _noted_nganh(st))
    if parsed.action == "dong_y":
        st["nganh_done"] = True
        return _ask_next(conv)
    if more is True:
        return _reply(_say(vi.HKD_QUESTIONS["nganh_them_gi"]), actions=[_asking(st)])  # "có" mà chưa nói ngành gì → hỏi ngành gì
    return _ask_next(conv, _say(vi.HKD_UNCLEAR))


async def _answer(conv: dict, text: str):
    st = conv["hkd"]
    key = st["field"]
    if key == "nganh_them":
        return await _answer_nganh_them(conv, text)
    if key == _CONFIRM_LIST and _page(st) == MEMBERS_PAGE:
        parsed = await hoi_dap.interpret(text, "tom_tat", "", [], {}, _location(conv))
        if parsed.action == "dong_y":
            return _save(conv)
        return _ask_next(conv, _say(vi.HKD_UNCLEAR))
    if key == "nganh_chinh":
        # Chọn trong danh sách đang hiện (thứ tự / mã đọc bằng chữ / chi tiết nghe sai) — không đưa agent tra mã, agent
        # coi câu trả lời là ngành mới. Chỉ khi công dân muốn thêm / bỏ ngành mới đi tiếp nhánh tra mã bên dưới.
        rows = [r for r in st["nganh"] if r.get("chac")]
        options = [f"{r['ma'][0]} · {nganh_nghe.ten(r['ma'][0])}" + (f" — chi tiết: {r['chiTiet']}" if r.get("chiTiet")
                                                                      else "") for r in rows]
        index, change = await hoi_dap.pick(text, _question(st, key)[0], options)
        if index is not None:
            st["chinh"] = rows[index]["ma"][0]
            return _ask_next(conv, _noted_nganh(st))
        if not change:
            return _ask_next(conv, _say(vi.HKD_UNCLEAR))
    if key in ("nganh", "nganh_chon", "nganh_ro", "nganh_chinh") or (
            key in (_CONFIRM, _CONFIRM_LIST) and _page(st) == _NGANH_PAGE):
        if key in (_CONFIRM, _CONFIRM_LIST):
            parsed = await hoi_dap.interpret(text, "tom_tat", "", [], {}, _location(conv))
            if parsed.action == "dong_y" and not parsed.nganh_text:
                return _save(conv) if key == _CONFIRM_LIST else _go_block(
                    conv, st["block"] + 1, _say(vi.HKD_BLOCK_SAVED, label=_label(_page(st))))
            st["list_filled"] = False  # sửa danh sách sau khi đã điền → điền lại lên trang
        failed = _say(vi.HKD_NGANH_FAILED)
        lead = await _lookup(st, text)
        if key == "nganh" and st.get("nganh"):
            st["nganh_done"] = False  # vừa có ngành đầu tiên → hỏi "còn ngành nào khác không"
        if lead == failed or (lead[0] and not st.get("nganh")):
            return _reply(lead, actions=[_asking(st)])  # agent lỗi / lời kể còn quá chung → hỏi lại, vẫn đứng ở mục ngành
        return _ask_next(conv, _noted_nganh(st))
    question = _question(st, key)[0] if key != _CONFIRM else ""
    parsed = await hoi_dap.interpret(text, key if key != _CONFIRM else "tom_tat", question, _open_slots(st),
                                     {**st["values"], **(st.get("member") or {})}, _location(conv))
    if parsed.action == "dong_y" and key == _CONFIRM and not parsed.values:
        return _save(conv)
    if parsed.action == "tam_dung":
        st["paused"] = True
        return _reply(_say(vi.HKD_PAUSED), [{"label": vi.HKD_RESUME_LABEL, "send": "__action:hkd_resume", "solid": True}])
    lead = ("", "")
    for k, v in parsed.values.items():
        _apply(st, k, v)
        if not (k == "chu_ho_la_ban" and v is True):
            lead = _join(lead, _noted_current(st, k, v))
    actions = _fill_now(st, list(parsed.values))
    if parsed.values.get("chu_ho_la_ban") is True and _page(st) == _OWNER_PAGE and not st.get("owner_copied"):
        return _copy_owner(conv, lead, actions)
    if (parsed.action == "khong_ro" and not parsed.values and _spec(key).get("skip")
            and fold(text).strip(" .!?") in _SKIP_WORDS):
        parsed.action = "bo_qua"  # dự phòng khi LLM không quyết được (dồn tải): câu trả lời CHỈ là "không có / bỏ qua"
    if parsed.action == "bo_qua" and key not in parsed.values and key != _CONFIRM:
        return _skip(conv, lead, actions)  # "không có email, vốn 50 triệu" → ghi vốn rồi bỏ qua email
    if key in parsed.bad_digits:
        digits = parsed.bad_digits[key]
        lead = _join(lead, _say(vi.HKD_DIGITS_WRONG, n=len(digits), digits=digits,
                                what=vi.HKD_DIGITS_WHAT[_spec(key)["kind"]]))
    elif not parsed.values and parsed.action != "nhac_lai":
        lead = _join(lead, _say(vi.HKD_UNCLEAR))
    return _ask_next(conv, lead, actions)


# ── Bắt đầu ──

async def _base_state(conv: dict, mode: str) -> dict:
    from app.channels.handfree.chat import pipeline_runner
    user = await pipeline_runner._load_owner_user(conv, None)
    from app.channels.handfree.chat import flow
    loc = conv.get("location") or {}
    force_self = bool((flow._business_defaults(conv) or {}).get("forceSelfSubmitter"))
    return {"mode": mode, "values": {}, "nganh": [], "chinh": "", "skipped": [], "members": [], "member": {},
            "force_self": force_self, "block": 0,
            "name_check_on": bool((conv.get("client_capabilities") or {}).get(NAME_CHECK_CAPABILITY)),
            "prepare_on": bool((conv.get("client_capabilities") or {}).get(PREPARE_CAPABILITY)),
            "submit_on": bool((conv.get("client_capabilities") or {}).get(SUBMIT_CAPABILITY)), "phase": "", "field": "", "skip_start_date": mapper.is_bac_ninh_phuong_lieu(user),
            "loc": {"province": loc.get("province") or "", "ward": loc.get("ward") or ""}}


def _begin(conv: dict) -> None:
    conv["hkd_checked"] = True
    conv["state"] = "filling"
    conv["pipeline_status"] = "hkd_hoi"  # chặn nhánh điền cả 8 trang một lượt của luồng tờ khai
    conv["business_action_started"] = False


async def start_no_docs(conv: dict):
    """Công dân không có tờ khai/giấy tờ: đi từng khối, hỏi mọi ô (sau khi đã đồng ý xử lý dữ liệu)."""
    conv["hkd"] = await _base_state(conv, "khong_giay")
    conv["attach_plan"] = []
    _begin(conv)
    return _go_block(conv, 0, _say(vi.HKD_START))


async def start_review(conv: dict):
    """Pipeline đọc giấy tờ xong: điền luôn mọi khối theo giấy, rồi mời bổ sung các ô còn thiếu (từng khối)."""
    base = {f.get("name"): f.get("value") for f in conv.get("business_facts") or [] if f.get("name")}
    st = await _base_state(conv, "bo_sung")
    st["base"] = base
    st["owner_from_docs"] = bool(base.get("ChuHo_HoTen") and base.get("ChuHo_SoDinhDanh"))
    for key, names in _FROM_DOCS.items():
        found = next((base.get(n) for n in names if _has(base.get(n))), None)
        if found is None:
            continue
        if _SLOTS[key]["kind"] == "address" and isinstance(found, dict) and _addr_part(found):
            continue  # địa chỉ trên giấy thiếu xã / số nhà → vòng bổ sung hỏi lại từ tỉnh (cổng hay để sẵn tỉnh tài khoản)
        st["values"][key] = "__docs__"
    st["values"]["dia_chi_thue"] = "__docs__"  # tờ khai không ghi địa chỉ thuế riêng = giống trụ sở (mapper)
    rows = [r for r in base.get("NganhNghe_DanhSach") or [] if isinstance(r, dict)]
    coded = [r for r in rows if mapper._clean_business_code(r.get("ma")) in nganh_nghe.catalog()]
    conv["hkd"] = st
    _begin(conv)
    st["nganh_done"] = True  # tờ khai là nguồn danh sách ngành — không hỏi "còn ngành nào khác"
    if coded:
        st["from_docs_codes"] = True
    elif rows:
        await _lookup(st, "; ".join(str(r.get("ten") or "") for r in rows if r.get("ten")))
    return _fill_all(conv)


# ── Lượt hội thoại ──

async def handle(conv: dict, proc: dict | None, intent: Intent):
    """Lệnh / câu trả lời / sự kiện trang của luồng đi từng khối. None = không thuộc luồng này."""
    if not active(conv, proc):
        return None
    st = conv.get("hkd")
    if intent.kind == "action" and intent.value == "hkd_no_docs":
        if st or not NO_DOCS_ENABLED or not (conv.get("consent") or {}).get("accepted"):
            return None
        return await start_no_docs(conv)
    if not st or st.get("phase") in ("", "done"):
        return None
    phase = st["phase"]
    # Sự kiện trang: chỉ luồng này điều khiển — không để nhánh tờ khai phát lệnh điền cả 8 trang.
    account = str(intent.payload.get("accountName") or "").strip()[:100] if intent.kind == "event" else ""
    if account:
        st["account_name"] = account  # tên người đăng nhập (góc trên cổng) — để hỏi "chủ hộ có phải là … không"
    if intent.kind == "event" and intent.value in ("page_status", "hkd_arrived"):
        result = intent.payload.get("businessResult")
        # Extension giữ kết quả lần chạy gần nhất ~30 phút và gửi kèm mọi page_status → chỉ nhận kết quả sinh SAU lúc
        # bắt đầu lưu khối này, không thì khối mới bị coi là đã lưu theo kết quả của khối trước.
        if (phase == "saving" and isinstance(result, dict) and result
                and float(result.get("createdAt") or 0) / 1000 >= float(st.get("saving_at") or 0) - 1):
            return await _on_report(conv, result)
        if phase == "open":
            if intent.value == "hkd_arrived":
                if intent.payload.get("page") != _page(st):
                    return _reply(("", ""))
                if intent.payload.get("missing") is True:
                    if _page(st) == AUTH_PAGE:
                        return _go_block(conv, st["block"] + 1)  # không có khối ủy quyền = chủ hộ tự nộp
                    # Khối khác vắng trong menu là bất thường (vd khối thành viên khi lưu chủ hộ chưa nhận) → nhờ bấm tay.
                    st["open_failed_said"] = True
                    return _reply(_say(vi.HKD_BLOCK_OPEN_FAILED, label=_label(_page(st))), actions=[_asking(st)])
                return _arrive(conv)
            return _on_page(conv, str(intent.payload.get("businessPageKey") or ""))
        return _reply(("", ""))
    if intent.kind == "event" and intent.value == "hkd_submit_failed":
        if phase != "submitting":
            return _reply(("", ""))
        st["phase"] = "ready_submit"
        return _reply(_say(vi.HKD_SUBMIT_FAILED), [_submit_chip()])
    if intent.kind == "event" and intent.value == "hkd_prepared":
        if phase != "prepare":
            return _reply(("", ""))
        return _on_prepared(conv, intent.payload)
    if intent.kind == "event" and intent.value == "hkd_name_checked":
        if phase != "check_name":
            return _reply(("", ""))
        return _on_name_checked(conv, intent.payload)
    if intent.kind == "event" and intent.value == "hkd_copied":
        if phase != "copy" or intent.payload.get("page") != _page(st):
            return _reply(("", ""))
        if _page(st) == _OWNER_PAGE:
            return _on_owner_copied(conv, intent.payload)
        return _on_copied(conv, intent.payload)
    if intent.kind == "action" and intent.value == "business_report":
        if phase != "saving":
            return _reply(("", ""))  # báo trùng (watcher + sidebar) của khối đã chuyển
        return await _on_report(conv, intent.payload)
    if intent.kind != "action" or intent.value not in _ACTIONS:
        return None
    if intent.value == "hkd_prepare":
        if phase not in ("ready_prepare", "prepare_failed"):
            return _reply(("", ""))
        st["phase"] = "prepare"
        return _reply(_say(vi.HKD_PREPARING), actions=[{"type": "hkd_prepare"}])
    if intent.value == "hkd_submit":
        if phase != "ready_submit":
            return _reply(("", ""))
        # Bấm nút = lệnh nộp; chọn bằng lời thì flow hỏi xác nhận trước (SUBMIT_SEND nằm trong _VOICE_CONFIRM_SENDS).
        st["phase"] = "submitting"
        return _reply(_say(vi.HKD_SUBMITTING), actions=[{"type": "hkd_submit"}])
    if intent.value == "hkd_fill_missing":
        if phase != "offer":
            return _reply(("", ""))
        st["only_missing"] = True
        return _go_block(conv, 0)
    if intent.value == "hkd_resume":
        st["paused"] = False
        return _ask_next(conv)
    if intent.value == "hkd_save":
        if phase != "confirm":
            return _reply(("", ""))
        if _page(st) in _LIST_PAGES and st.get("list_filled"):
            # Khối danh sách: dòng đã được máy điền thêm (cổng lưu từng dòng) → xác nhận xong là sang khối kế.
            return _go_block(conv, st["block"] + 1, _say(vi.HKD_BLOCK_SAVED, label=_label(_page(st))))
        return _save(conv)
    if intent.value == "hkd_fill_block":
        return _save(conv) if phase == "confirm_list" else _reply(("", ""))
    if phase not in ("ask", "confirm", "confirm_list"):
        return _reply(("", ""))
    if intent.value == "hkd_skip":
        return _skip(conv)
    if intent.value == "hkd_value" and st["field"] == "nganh_them":
        if intent.payload.get("v") is False:
            st["nganh_done"] = True
        return _ask_next(conv)
    if intent.value == "hkd_value":
        key = st["field"]
        spec = _spec(key)
        value, _ = hoi_dap.check(spec["kind"], intent.payload.get("v"), "", False, bool(spec.get("same"))) \
            if spec else (None, "")
        if value is None:
            return _ask_next(conv)
        _apply(st, key, value)
        if key == "chu_ho_la_ban" and value is True and not st.get("owner_copied"):
            return _copy_owner(conv, ("", ""), _fill_now(st, [key]))
        return _ask_next(conv, _noted_current(st, key, value), _fill_now(st, [key]))
    if intent.value == "hkd_pick":
        chinh = str(intent.payload.get("chinh") or "")
        if chinh:
            st["chinh"] = chinh
            return _ask_next(conv, _noted_nganh(st))
        try:
            row = st["nganh"][int(intent.payload.get("row"))]
        except (TypeError, ValueError, IndexError):
            return _ask_next(conv)
        if intent.payload.get("drop") is True and not row.get("ma"):
            st["nganh"].remove(row)
        else:
            ma = str(intent.payload.get("ma") or "")
            if ma in row.get("ma") or []:
                row.update({"ma": [ma], "chac": True})
        return _ask_next(conv, _noted_nganh(st))
    text = str(intent.payload.get("text") or "").strip()
    if not text:
        return _ask_next(conv)
    return await _answer(conv, text)
