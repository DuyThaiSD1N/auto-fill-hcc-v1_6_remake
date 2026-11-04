"""[Bộ VHTTDL] Thủ tục tổ chức biểu diễn nghệ thuật (1.009397).

Khoá: nhận diện ở cả trang DVCQG lẫn trang nộp cổng Bộ VHTTDL (Auto Fill + trợ lý); tổ chức đề nghị vào khối "Thông
tin người ủy quyền" (tích khi có tên + mã số đủ 10 số); khối đề nghị điền theo Văn bản đề nghị, Kịch bản bù khi
thiếu; ô ngày chỉ nhận một ngày; 2 dòng đính kèm dò theo chữ, GCN + giấy tiếp nhận địa điểm đính chung dòng a).
"""

from pathlib import Path

from app.channels.handfree.chat.field_review import registry as field_review_registry
from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG
from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE_PROCEDURES
from app.pipelines.to_chuc_bieu_dien_nghe_thuat.attach import planner
from app.pipelines.to_chuc_bieu_dien_nghe_thuat.process import mapper
from app.pipelines.to_chuc_bieu_dien_nghe_thuat.process.schema import (
    LABEL_DIA_DIEM,
    LABEL_DUYET_DIA_DIEM,
    LABEL_DUYET_THOI_GIAN,
    LABEL_LIEN_KET,
    LABEL_NGUOI_CHIU_TN,
    LABEL_TAI_LIEU,
    LABEL_TEN_CT,
    LABEL_THOI_GIAN,
    LABEL_TON_VINH,
    S_DN,
    S_UQ,
    UI_FIELDS,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

_KEY = "to-chuc-bieu-dien-nghe-thuat"
_ROOT = Path(__file__).resolve().parents[2].parent
# URL trang nộp sau khi bấm "Nộp trực tuyến" trên DVCQG (popup so khớp trên URL đã lower-case).
_APPLY_URL = ("https://dichvucong.bvhttdl.gov.vn/nop-ho-so?MaTTHC=1.009397&MaCoQuanThucHien=H00.01"
              "&MaDVC=1.009397.01&MaTTHCDP=1.009397&vneid=1").lower()
_DIA_DIEM = "Nhà Văn hóa Mẫu, số 1 đường Mẫu, phường Mẫu Mới, Tỉnh Mẫu."


def _facts(**extra) -> list[dict]:
    base = {
        "DonVi_Ten": "CÔNG TY TNHH NGHỆ THUẬT MẪU",
        "DonVi_MaSo": "0109999999",
        "DonVi_NgayCap": "02/03/2020",
        "DonVi_NoiCap": "Phòng Đăng ký kinh doanh - Sở Tài chính Thành phố Hà Nội",
        "DonVi_DienThoai": "024 3999 9999",
        "DonVi_TruSo": {"tinh": "Hà Nội", "xa": "Phường Hoàn Kiếm", "chiTietDuoiXa": "Số 9 phố Mẫu"},
        "DeNghi_KinhGui": "Sở Văn hóa, Thể thao và Du lịch Tỉnh Mẫu",
        "DeNghi_TenChuongTrinh": "Đêm nhạc Mẫu - Hòa tấu (Thời lượng: 90 phút)",
        "DeNghi_ThoiGian": "Từ 19h30 – 21h00 ngày 05, 06 tháng 12 năm 2026",
        "DeNghi_DiaDiem": _DIA_DIEM,
        "DeNghi_DuyetThoiGian": "Lúc14h00 đến 16h00 ngày 05/12/2026",
        "DeNghi_DuyetDiaDiem": _DIA_DIEM,
        "DeNghi_NguoiChiuTrachNhiem": "Ông: Lê Văn Mẫu - Chức vụ: Giám đốc",
        "DeNghi_LienKet": "(Không có)",
        "DeNghi_TonVinh": "(Không có)",
        "DeNghi_TaiLieuKemTheo": [
            "Nội dung chương trình biểu diễn, Giấy đăng ký kinh doanh.",
            "• Giấy tiếp nhận Nhà Văn hóa Mẫu",
        ],
        "KichBan_ThoiGian": "Từ 19h30 - 21h00 ngày 06 tháng 12 năm 2026",
        "KichBan_DiaDiem": "Nhà Văn hóa Mẫu, số 1 đường Mẫu.",
    }
    base.update(extra)
    return [{"name": k, "value": v} for k, v in base.items() if v is not None]


def _ui(fields: list[dict]) -> dict:
    return {(f["section"], f["name"]): f["value"] for f in fields}


def test_ke_khai_link_va_registry_cung_key():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.009397" and link["selectSo"] is True
    proc = registry.get_procedure(_KEY)
    assert proc["label"] == link["label"]
    assert proc["hasAttachmentStep"] is True and proc["fillWithAttach"] is True
    assert registry.get_pipeline(_KEY) is not None
    assert registry.get_attach_pipeline(_KEY) is not None


def test_nhan_dien_ca_trang_dvcqg_lan_trang_nop_bvhttdl():
    core = next(p for p in with_ke_khai_detect_urls(registry.public_list()) if p["key"] == _KEY)
    handfree = next(p for p in HANDFREE_PROCEDURES if p["key"] == _KEY)
    for detect in (core["detect"], handfree["detect"]):
        assert set(detect["urlScope"]) == {"dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"}
        url_includes = [u.lower() for u in detect["urlIncludes"]]
        assert any(part in _APPLY_URL for part in url_includes)
        assert "019d2bfd-e44a-7705-a455-6f7239cfe9de" in url_includes
    assert handfree["lizFlow"] and handfree["agencyProvinceOnly"] is True and handfree["agencySoFirst"] is True
    assert handfree["keKhaiUrl"].endswith("019d2bfd-e44a-7705-a455-6f7239cfe9de")
    assert PROCEDURE_HMONG[_KEY]


def test_co_gcn_tich_uy_quyen_truoc_roi_dien_to_chuc():
    fields, warnings = mapper.enrich(_facts(), {})
    assert fields[0] == {"name": "Thông tin người ủy quyền", "comp": "liz-checkbox", "value": True, "section": ""}
    ui = _ui(fields)
    assert ui[(S_UQ, "Tên người / Tên đơn vị ủy quyền")] == "CÔNG TY TNHH NGHỆ THUẬT MẪU"
    assert ui[(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp")] == "0109999999"
    assert ui[(S_UQ, "Ngày cấp")] == "02/03/2020"
    assert ui[(S_UQ, "Số điện thoại")] == "02439999999"
    assert ui[(S_UQ, "Địa chỉ hành chính")] == "Phường Hoàn Kiếm, Thành phố Hà Nội"
    assert ui[(S_UQ, "Địa chỉ chi tiết")] == "Số 9 phố Mẫu"
    assert not any("còn trống" in w or "con dấu" in w for w in warnings)


def test_khoi_de_nghi_dien_theo_van_ban():
    fields, warnings = mapper.enrich(_facts(), {})
    ui = _ui(fields)
    assert ui[(S_DN, LABEL_TEN_CT)] == "Đêm nhạc Mẫu - Hòa tấu (Thời lượng: 90 phút)"
    assert ui[(S_DN, LABEL_DIA_DIEM)] == _DIA_DIEM
    assert ui[(S_DN, LABEL_THOI_GIAN)] == "05/12/2026", "ô ngày chỉ nhận một ngày → ngày đầu"
    assert ui[(S_DN, LABEL_DUYET_THOI_GIAN)] == "05/12/2026"
    assert ui[(S_DN, LABEL_DUYET_DIA_DIEM)].startswith("Nhà Văn hóa Mẫu")
    assert ui[(S_DN, LABEL_NGUOI_CHIU_TN)] == "Ông: Lê Văn Mẫu - Chức vụ: Giám đốc"
    assert ui[(S_DN, LABEL_LIEN_KET)] == "Không có" and ui[(S_DN, LABEL_TON_VINH)] == "Không có"
    assert ui[(S_DN, LABEL_TAI_LIEU)] == (
        "Nội dung chương trình biểu diễn, Giấy đăng ký kinh doanh; Giấy tiếp nhận Nhà Văn hóa Mẫu"
    )
    assert any("có 2 ngày" in w and "05/12/2026" in w for w in warnings)
    assert not any("Kịch bản ghi thời gian" in w for w in warnings), "06/12 nằm trong các ngày của văn bản"
    assert any("Tỉnh Mẫu" in w and "Cơ quan giải quyết" in w for w in warnings)


def test_khong_gcn_ma_so_tu_con_dau_va_canh_bao_o_trong():
    fields, warnings = mapper.enrich(
        _facts(DonVi_MaSo=None, DonVi_MaSoConDau="0109999999", DonVi_NgayCap=None, DonVi_NoiCap=None,
               DonVi_DienThoai=None, DonVi_TruSo=None),
        {},
    )
    ui = _ui(fields)
    assert fields[0]["comp"] == "liz-checkbox"
    assert ui[(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp")] == "0109999999"
    assert any("con dấu" in w for w in warnings)
    assert any("còn trống" in w and "Số điện thoại" in w and "Địa chỉ chi tiết" in w for w in warnings)


def test_ma_so_thieu_so_thi_khong_tich():
    fields, warnings = mapper.enrich(_facts(DonVi_MaSo=None, DonVi_MaSoConDau="01099"), {})
    assert not any(f["comp"] == "liz-checkbox" or f["section"] == S_UQ for f in fields)
    assert any("Không tích" in w and "\"01099\"" in w for w in warnings)
    assert (S_DN, LABEL_TEN_CT) in _ui(fields), "khối đề nghị vẫn điền"


def test_tai_khoan_la_chinh_to_chuc_thi_khong_tich():
    ctx = {"formContext": {"applicantFullname": "Công ty TNHH Nghệ thuật Mẫu", "applicantIdentityNumber": ""}}
    fields, warnings = mapper.enrich(_facts(), ctx)
    assert not any(f["section"] == S_UQ or f["comp"] == "liz-checkbox" for f in fields)
    assert any("chính tổ chức đề nghị" in w for w in warnings)


def test_van_ban_thieu_muc_thi_bu_tu_kich_ban_va_canh_bao_lech():
    fields, warnings = mapper.enrich(
        _facts(DeNghi_DiaDiem=None, DeNghi_ThoiGian="Từ 19h30 ngày 07/12/2026"), {},
    )
    ui = _ui(fields)
    assert ui[(S_DN, LABEL_DIA_DIEM)] == "Nhà Văn hóa Mẫu, số 1 đường Mẫu."
    assert ui[(S_DN, LABEL_THOI_GIAN)] == "07/12/2026"
    assert any("Kịch bản ghi thời gian" in w for w in warnings)


def test_khong_doc_duoc_gi_thi_canh_bao_nhap_tay():
    fields, warnings = mapper.enrich([], {})
    assert fields == []
    assert any("Chưa đọc được" in w and "Địa điểm tổ chức" in w and "Tài liệu kèm theo" in w for w in warnings)


def test_doc_ngay_nhieu_dang():
    assert mapper._dates("Từ 20h00 – 21h20 ngày 20, 21 tháng 11 năm 2026") == ["20/11/2026", "21/11/2026"]
    assert mapper._dates("từ ngày 3 đến ngày 5 tháng 1 năm 2027") == ["03/01/2027", "05/01/2027"]
    assert mapper._dates("Lúc16h00 đến 18h20 ngày 20/11/2026") == ["20/11/2026"]
    assert mapper._dates("ngày 20 và 21 tháng 11 năm 2026") == ["20/11/2026", "21/11/2026"]
    assert mapper._dates("tháng 11 năm 2026") == []


def test_moi_field_emit_co_trong_ui_fields():
    known = {(s, l): c for s, l, c, _a in UI_FIELDS}
    for facts in (_facts(), _facts(DonVi_MaSo=None, DonVi_MaSoConDau="0109999999")):
        fields, _ = mapper.enrich(facts, {})
        for f in fields:
            if f["comp"] != "liz-checkbox":
                assert known[(f["section"], f["name"])] == f["comp"]


def test_hai_dong_dinh_kem_gcn_va_giay_tiep_nhan_vao_dong_a_khong_dinh_cccd():
    names = ["van_ban.pdf", "kich_ban.pdf", "gcn.pdf", "tiep_nhan.pdf", "cccd.jpg"]
    types = {0: "van_ban_de_nghi", 1: "kich_ban", 2: "gcn_dkdn", 3: "giay_tiep_nhan_dia_diem", 4: "cccd"}
    texts = {1: "KỊCH BẢN … Tác giả: Mẫu; Người chịu trách nhiệm nội dung: Mẫu"}
    items, warnings, classified = planner.build_plan_items([{"name": n} for n in names], types, texts)
    assert [(i["fileName"], i["slotIndex"]) for i in items] == [
        ("van_ban.pdf", 0), ("kich_ban.pdf", 1), ("gcn.pdf", 0), ("tiep_nhan.pdf", 0),
    ]
    assert all(i["target"] == "fixed-slot" and i["sectionHeader"] == "Thành phần hồ sơ" for i in items)
    assert len({i["slotKey"] for i in items if i["slotIndex"] == 0}) == 1, "cùng dòng → chung slotKey"
    assert {c["fileName"] for c in classified if c.get("target") == "skip"} == {"cccd.jpg"}
    assert any("gcn.pdf" in w and "dòng a)" in w for w in warnings)
    assert not any("Chưa thấy" in w or "tác giả" in w for w in warnings)


def test_canh_bao_kich_ban_thieu_tac_gia_va_van_ban_neu_giay_chua_co():
    texts = {
        0: "V/v: Đề nghị tổ chức biểu diễn nghệ thuật … Tài liệu kèm theo: Nội dung chương trình, Giấy đăng ký kinh "
           "doanh. Giấy tiếp nhận Nhà Văn hóa Mẫu",
        1: "KỊCH BẢN - NỘI DUNG CHI TIẾT CHƯƠNG TRÌNH\nThời gian | Hoạt động | Chi tiết hoạt động",
    }
    _, warnings, _ = planner.build_plan_items(
        [{"name": "van_ban.pdf"}, {"name": "kich_ban.pdf"}], {0: "van_ban_de_nghi", 1: "kich_ban"}, texts,
    )
    assert any("chưa thấy ghi tác giả" in w for w in warnings)
    assert any("Giấy chứng nhận đăng ký doanh nghiệp" in w and "chưa có" in w for w in warnings)
    assert any("giấy tiếp nhận" in w and "chưa có" in w for w in warnings)


def test_thieu_thanh_phan_va_tep_la_vao_dong_a():
    items, warnings, _ = planner.build_plan_items([{"name": "la.pdf"}], {})
    assert [i["slotIndex"] for i in items] == [0]
    assert any("la.pdf" in w for w in warnings)
    assert any("VĂN BẢN ĐỀ NGHỊ" in w for w in warnings) and any("KỊCH BẢN" in w for w in warnings)


def test_slot_keywords_moi_dong_mot_cum_rieng():
    """Mỗi cụm chỉ khớp đúng dòng của nó trên chữ thật của 2 dòng thành phần (đã fold như engine)."""
    rows = [
        "1 a) Văn bản đề nghị tổ chức biểu diễn nghệ thuật (Mẫu số 02 Phụ lục ban hành kèm theo Nghị định số "
        "144/2020/NĐ-CP);",
        "2 b) Kịch bản, danh mục tác phẩm gắn với tác giả, người chịu trách nhiệm chính về nội dung chương trình (đối "
        "với tác phẩm nước ngoài phải kèm bản dịch tiếng Việt có chứng thực chữ ký người dịch).",
    ]
    folded = [planner._fold(r) for r in rows]
    for slot, keywords in planner._SLOT_KEYWORDS.items():
        assert [i for i, text in enumerate(folded) if any(k in text for k in keywords)] == [slot]


def test_field_review_tu_kham_pha():
    config = field_review_registry.get(_KEY)
    assert set(config["required"]) == {LABEL_TEN_CT, LABEL_DIA_DIEM, LABEL_THOI_GIAN, LABEL_NGUOI_CHIU_TN,
                                       LABEL_TAI_LIEU}
    assert LABEL_LIEN_KET in config["noAsk"] and "receipt_name" in config["noAsk"]


def test_extension_khong_nhac_thieu_co_cong_tinh_tren_trang_nop():
    src_file = _ROOT / "auto-fill-hcc-extension" / "content" / "portal-quangninh.js"
    if not src_file.exists():
        return
    block = src_file.read_text(encoding="utf-8").split("NO_FLOW_MA_TTHC = new Set(", 1)[1].split(")", 1)[0]
    assert '"1.009397"' in block
