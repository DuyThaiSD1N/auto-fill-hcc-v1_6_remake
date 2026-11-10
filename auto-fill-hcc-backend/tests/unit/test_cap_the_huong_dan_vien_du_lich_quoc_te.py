"""[Bộ VHTTDL] Thủ tục cấp thẻ hướng dẫn viên du lịch quốc tế (1.004628, QT-120).

Khoá: nhận diện cả trang DVCQG (uuid) lẫn trang nộp cổng Bộ VHTTDL, không bắt nhầm thẻ nội địa/cấp đổi; tài khoản trùng
người đề nghị → khối người nộp, khác người → tích "Thông tin người ủy quyền"; Phần IV điền giới tính + trình độ chuyên môn
+ trình độ ngoại ngữ (đơn trống thì lấy chứng chỉ); cảnh báo lệch loại thẻ, chứng chỉ ngoại ngữ hết hạn, thiếu chứng chỉ
nghiệp vụ; đính kèm 4 dòng: ảnh 0, Đơn 1, ngoại ngữ 2, văn bằng + chứng chỉ nghiệp vụ CHUNG 3.
"""

from datetime import date
from pathlib import Path

from app.channels.handfree.chat.field_review import registry as field_review_registry
from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG
from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE_PROCEDURES
from app.channels.handfree.procedure_registry import _HOAN_THIEN_THEO_TINH
from app.pipelines.cap_the_huong_dan_vien_du_lich_quoc_te.attach import planner
from app.pipelines.cap_the_huong_dan_vien_du_lich_quoc_te.process import mapper
from app.pipelines.cap_the_huong_dan_vien_du_lich_quoc_te.process.schema import (
    LABEL_CHUYEN_MON,
    LABEL_GIOI_TINH,
    LABEL_NGOAI_NGU,
    S_NOP,
    S_THE,
    S_UQ,
    UI_FIELDS,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

_KEY = "cap-the-huong-dan-vien-du-lich-quoc-te"
_UUID = "019d7fa8-0b23-732b-a247-5012a7de5171"
_ROOT = Path(__file__).resolve().parents[2].parent
_APPLY_URL = ("https://dichvucong.bvhttdl.gov.vn/nop-ho-so?MaTTHC=1.004628&MaCoQuanThucHien=H32.25"
              "&MaDVC=1.004628.01&MaTTHCDP=1.004628&vneid=1").lower()
_TODAY = date(2026, 11, 10)
_CCCD = "001095012345"


def _facts(**extra) -> list[dict]:
    base = {
        "NguoiDeNghi_HoTen": "LÊ THỊ MẪU",
        "NguoiDeNghi_SoDinhDanh": _CCCD,
        "NguoiDeNghi_NgaySinh": "02/09/1995",
        "NguoiDeNghi_GioiTinh": "Nữ",
        "NguoiDeNghi_DiaChi": {"tinh": "Thành phố Hà Nội", "xa": "Phường Láng", "chiTietDuoiXa": "Số 5, ngõ 10 phố Mẫu"},
        "NguoiDeNghi_DienThoai": "0987 654 321",
        "NguoiDeNghi_Email": "lethimau.hdv@gmail.com",
        "NguoiDeNghi_TrinhDoChuyenMon": "Cử nhân Quản trị dịch vụ du lịch và lữ hành",
        "NguoiDeNghi_TrinhDoNgoaiNgu": "Tiếng Anh – Chứng chỉ IELTS Academic 7.0",
        "Don_LoaiThe": "quốc tế",
        "Don_CoQuanNhan": "Sở Văn hóa, Thể thao và Du lịch thành phố Hà Nội",
        "VanBang_TrinhDo": "Đại học",
        "VanBang_ChuyenNganh": "Quản trị dịch vụ du lịch và lữ hành",
        "ChungChi_Ten": "Chứng chỉ nghiệp vụ hướng dẫn du lịch quốc tế",
    }
    base.update(extra)
    return [{"name": k, "value": v} for k, v in base.items() if v is not None]


def _ui(fields: list[dict]) -> dict:
    return {(f["section"], f["name"]): f["value"] for f in fields}


def _ctx(identity: str = _CCCD, name: str = "Lê Thị Mẫu") -> dict:
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": identity}}


def test_ke_khai_link_va_registry_cung_key():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.004628" and link["selectSo"] is True
    assert link["url"].endswith(_UUID)
    proc = registry.get_procedure(_KEY)
    assert proc["label"] == link["label"]
    assert proc["hasAttachmentStep"] is True and proc["fillWithAttach"] is True
    assert registry.get_pipeline(_KEY) is not None
    assert registry.get_attach_pipeline(_KEY) is not None


def test_nhan_dien_ca_hai_trang_khong_bat_nham_the_khac_va_len_tro_ly():
    core = next(p for p in with_ke_khai_detect_urls(registry.public_list()) if p["key"] == _KEY)
    handfree = next(p for p in HANDFREE_PROCEDURES if p["key"] == _KEY)
    for detect in (core["detect"], handfree["detect"]):
        assert set(detect["urlScope"]) == {"dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"}
        url_includes = [u.lower() for u in detect["urlIncludes"]]
        assert any(part in _APPLY_URL for part in url_includes)
        assert _UUID in url_includes
        for other in ("1.004623", "1.001432", "1.004614", "1.001440", "1.004605"):
            assert not any(part in _APPLY_URL.replace("1.004628", other) for part in url_includes), other
    assert handfree["label"] == registry.get_procedure(_KEY)["label"]
    assert handfree["lizFlow"] and handfree["agencyProvinceOnly"] is True and handfree["agencySoFirst"] is True
    assert handfree["agencyDeptLabel"] == "Sở Văn hóa, Thể thao và Du lịch"
    assert handfree["keKhaiUrl"].endswith(_UUID)
    assert "provinceOnly" not in handfree, "cổng bộ dùng chung toàn quốc"
    assert _KEY in _HOAN_THIEN_THEO_TINH
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]


def test_tai_khoan_trung_cccd_thi_dien_khoi_nguoi_nop_va_phan_the():
    fields, warnings = mapper.enrich(_facts(), _ctx(), today=_TODAY)
    ui = _ui(fields)
    assert ui[(S_NOP, "Ngày sinh")] == "02/09/1995"
    assert ui[(S_NOP, "Số điện thoại")] == "0987654321"
    assert ui[(S_NOP, "Email")] == "lethimau.hdv@gmail.com"
    assert ui[(S_NOP, "Địa chỉ hành chính")] == "Phường Láng, Thành phố Hà Nội"
    assert ui[(S_NOP, "Địa chỉ chi tiết")] == "Số 5, ngõ 10 phố Mẫu"
    assert ui[(S_THE, LABEL_GIOI_TINH)] == "Nữ"
    assert ui[(S_THE, LABEL_CHUYEN_MON)] == "Cử nhân Quản trị dịch vụ du lịch và lữ hành"
    assert ui[(S_THE, LABEL_NGOAI_NGU)] == "Tiếng Anh – Chứng chỉ IELTS Academic 7.0"
    assert not any(f["section"] == S_UQ or f["comp"] == "liz-checkbox" for f in fields)
    assert not any(f["section"] == S_THE and f["name"] == "Email" for f in fields), "Phần IV thẻ QT không có ô Email"
    assert not any("LỆCH THỦ TỤC" in w or "chứng chỉ nghiệp vụ" in w for w in warnings)
    assert any("Cơ quan giải quyết" in w for w in warnings)


def test_tai_khoan_khac_cccd_thi_tich_uy_quyen():
    fields, warnings = mapper.enrich(_facts(), _ctx(identity="001090099999", name="Trần Văn Khác"), today=_TODAY)
    ui = _ui(fields)
    assert fields[0]["comp"] == "liz-checkbox" and fields[0]["value"] is True, "tích trước để khối ủy quyền hiện ra"
    assert ui[(S_UQ, "Tên người / Tên đơn vị ủy quyền")] == "LÊ THỊ MẪU"
    assert ui[(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp")] == _CCCD
    assert not any(f["section"] == S_NOP for f in fields)
    assert any("nộp thay" in w for w in warnings)


def test_don_khong_doc_duoc_so_thi_so_ho_ten():
    fields, _ = mapper.enrich(_facts(NguoiDeNghi_SoDinhDanh="0010950"), _ctx(name="Lê Thị Mẫu"), today=_TODAY)
    assert any(f["section"] == S_NOP for f in fields)


def test_khong_co_moc_tai_khoan_chi_dien_phan_the():
    fields, warnings = mapper.enrich(_facts(), {}, today=_TODAY)
    assert {f["section"] for f in fields} == {S_THE}
    assert any("Không điền khối" in w for w in warnings)


def test_don_trong_ngoai_ngu_lay_chung_chi_va_chuyen_mon_lay_van_bang():
    fields, warnings = mapper.enrich(
        _facts(NguoiDeNghi_TrinhDoNgoaiNgu=None, NguoiDeNghi_TrinhDoChuyenMon=None,
               NgoaiNgu_ChungChi="Tiếng Anh – IELTS Academic 7.0"),
        {}, today=_TODAY,
    )
    ui = _ui(fields)
    assert ui[(S_THE, LABEL_NGOAI_NGU)] == "Tiếng Anh – IELTS Academic 7.0"
    assert ui[(S_THE, LABEL_CHUYEN_MON)] == "Đại học chuyên ngành Quản trị dịch vụ du lịch và lữ hành"
    assert not any("TRÌNH ĐỘ NGOẠI NGỮ" in w for w in warnings)


def test_canh_bao_thieu_ngoai_ngu_het_han_lech_loai_the_va_thieu_chung_chi():
    _, warnings = mapper.enrich(
        _facts(NguoiDeNghi_TrinhDoNgoaiNgu=None, Don_LoaiThe="nội địa", ChungChi_Ten=None), {}, today=_TODAY,
    )
    assert any("TRÌNH ĐỘ NGOẠI NGỮ" in w for w in warnings)
    assert any("LỆCH THỦ TỤC" in w and "NỘI ĐỊA" in w for w in warnings)
    assert any("chứng chỉ nghiệp vụ hướng dẫn du lịch quốc tế" in w for w in warnings)

    _, warnings = mapper.enrich(_facts(NgoaiNgu_NgayHetHan="01/03/2026"), {}, today=_TODAY)
    assert any("HẾT HẠN" in w for w in warnings)

    _, warnings = mapper.enrich(
        _facts(ChungChi_Ten="Chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa"), {}, today=_TODAY,
    )
    assert any("chứng chỉ nội địa không thay được" in w for w in warnings)

    _, warnings = mapper.enrich(_facts(VanBang_ChuyenNganh="Hướng dẫn du lịch", ChungChi_Ten=None), {}, today=_TODAY)
    assert not any("chứng chỉ nghiệp vụ" in w for w in warnings), "bằng ngành hướng dẫn du lịch không cần chứng chỉ"


def test_moi_field_emit_co_trong_ui_fields():
    known = {(s, label) for s, label, _c, _a in UI_FIELDS}
    for ctx in (_ctx(), _ctx(identity="001090099999"), {}):
        fields, _ = mapper.enrich(_facts(), ctx, today=_TODAY)
        for f in fields:
            assert f["comp"] == "liz-checkbox" or (f["section"], f["name"]) in known, f


def _files(*names_types):
    return [{"name": n, "type": t} for n, t in names_types]


def test_dinh_kem_bon_dong_dung_slot():
    files = _files(("anh.jpg", "image/jpeg"), ("don.pdf", "application/pdf"), ("ielts.pdf", "application/pdf"),
                   ("bang.pdf", "application/pdf"), ("chung_chi.pdf", "application/pdf"))
    llm = {0: ("anh_chan_dung", []), 1: ("don_de_nghi", []), 2: ("chung_chi_ngoai_ngu", []),
           3: ("van_bang", []), 4: ("chung_chi_nghiep_vu", [])}
    items, warnings, _ = planner.build_plan_items(files, llm)
    slots = {i["fileName"]: i["slotIndex"] for i in items}
    assert slots == {"anh.jpg": 0, "don.pdf": 1, "ielts.pdf": 2, "bang.pdf": 3, "chung_chi.pdf": 3}
    loai = {i["slotIndex"]: i["loaiBan"] for i in items}
    assert loai == {0: "Bản chính", 1: "Bản chính", 2: "Bản sao", 3: "Bản sao"}
    assert len({i["slotKey"] for i in items if i["slotIndex"] == 3}) == 1, "văn bằng + chứng chỉ chung một lần gán"
    assert warnings == []


def test_dinh_kem_tep_gop_bang_va_chung_chi_dinh_nguyen_tep_dong_4():
    files = _files(("anh.png", "image/png"), ("don.pdf", "application/pdf"), ("ielts.pdf", "application/pdf"),
                   ("bang_cn_va_cc.pdf", "application/pdf"))
    llm = {0: ("anh_chan_dung", []), 1: ("don_de_nghi", []), 2: ("chung_chi_ngoai_ngu", []),
           3: ("van_bang", ["chung_chi_nghiep_vu"])}
    items, warnings, _ = planner.build_plan_items(files, llm)
    assert [i["slotIndex"] for i in items] == [0, 1, 2, 3]
    assert warnings == []


def test_dinh_kem_thieu_thanh_phan_va_tep_la():
    files = _files(("don.pdf", "application/pdf"), ("cccd.jpg", "image/jpeg"))
    items, warnings, _ = planner.build_plan_items(files, {0: ("don_de_nghi", []), 1: ("other", [])})
    assert {i["fileName"]: i["slotIndex"] for i in items} == {"don.pdf": 1, "cccd.jpg": 1}
    joined = " ".join(warnings)
    assert "ẢNH CHÂN DUNG" in joined and "NGOẠI NGỮ" in joined and "BẰNG TỐT NGHIỆP" in joined
    assert "cccd.jpg" in joined


def test_bang_ngoai_ngu_vao_dong_3_va_nhac_dinh_them_dong_4():
    files = _files(("anh.jpg", "image/jpeg"), ("don.pdf", "application/pdf"), ("cn_ngon_ngu_anh.pdf", "application/pdf"),
                   ("chung_chi.pdf", "application/pdf"))
    llm = {0: ("anh_chan_dung", []), 1: ("don_de_nghi", []), 2: ("van_bang_ngoai_ngu", []),
           3: ("chung_chi_nghiep_vu", [])}
    items, warnings, _ = planner.build_plan_items(files, llm)
    assert {i["fileName"]: i["slotIndex"] for i in items}["cn_ngon_ngu_anh.pdf"] == 2
    assert any("dòng (4)" in w and "ngoại ngữ" in w for w in warnings)


def test_field_review_tu_kham_pha():
    config = field_review_registry.get(_KEY)
    assert set(config["required"]) == {LABEL_GIOI_TINH, LABEL_CHUYEN_MON, LABEL_NGOAI_NGU}
    assert "receipt_name" in config["noAsk"] and "cccd_tu_van" in config["noAsk"]


def test_extension_khai_ma_tthc_va_moc_tai_khoan():
    portal = _ROOT / "auto-fill-hcc-extension" / "content" / "portal-quangninh.js"
    popup = _ROOT / "auto-fill-hcc-extension" / "popup.js"
    if not portal.exists() or not popup.exists():
        return
    block = portal.read_text(encoding="utf-8").split("NO_FLOW_MA_TTHC = new Set(", 1)[1].split(")", 1)[0]
    assert '"1.004628"' in block
    assert f'cfg.key === "{_KEY}"' in popup.read_text(encoding="utf-8")
