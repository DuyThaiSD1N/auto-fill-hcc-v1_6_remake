"""[Bộ VHTTDL] Thủ tục cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (1.001822, QT-09).

Khoá: nhận diện ở cả trang DVCQG lẫn trang nộp cổng Bộ VHTTDL (Auto Fill + trợ lý); ba chế độ người nộp theo mốc
tài khoản (tự nộp / nộp thay → tích ủy quyền / thiếu mốc); Đơn Mẫu 51 luôn điền; 3 dòng đính kèm dò theo chữ, chứng
chỉ bồi dưỡng + CCCD không đính.
"""

from datetime import date
from pathlib import Path

from app.channels.handfree.chat.field_review import registry as field_review_registry
from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE_PROCEDURES
from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.attach import planner
from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process import mapper
from app.pipelines.cap_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.schema import (
    LABEL_HO_TEN,
    LABEL_HOAT_DONG,
    LABEL_KINH_NGHIEM,
    LABEL_SO_DINH_DANH,
    LABEL_TRINH_DO,
    S_DON,
    S_NOP,
    S_UQ,
    UI_FIELDS,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

_KEY = "cap-chung-chi-hanh-nghe-bao-quan-tu-bo-phuc-hoi-di-tich"
_ROOT = Path(__file__).resolve().parents[2].parent
_TODAY = date(2026, 11, 3)
# URL trang nộp sau khi bấm "Nộp trực tuyến" trên DVCQG (popup so khớp trên URL đã lower-case).
_APPLY_URL = ("https://dichvucong.bvhttdl.gov.vn/nop-ho-so?MaTTHC=1.001822&MaCoQuanThucHien=H00.01"
              "&MaDVC=1.001822.01&MaTTHCDP=1.001822&vneid=1").lower()


def _facts(**extra) -> list[dict]:
    base = {
        "NguoiDeNghi_HoTen": "Trần Văn Mẫu",
        "NguoiDeNghi_NgaySinh": "05/06/1980",
        "NguoiDeNghi_SoDinhDanh": "001080000123",
        "NguoiDeNghi_NgayCap": "10/10/2021",
        "NguoiDeNghi_NoiCap": "Cục trưởng cục cảnh sát quản lý hành chính về trật tự xã hội",
        "NguoiDeNghi_DiaChiLienHe": "Tổ 1, phường Mẫu Cũ, Lào Cai (Nay là: Tổ 2, phường Cam Đường, tỉnh Lào Cai)",
        "NguoiDeNghi_DiaChiHienNay": {"tinh": "Lào Cai", "xa": "phường Cam Đường", "chiTietDuoiXa": "Tổ 2"},
        "NguoiDeNghi_TrinhDoChuyenMon": "Trường Đại học Mẫu – ngành: Kiến trúc",
        "NguoiDeNghi_KinhNghiem": [
            "a. Công trình: Đền Mẫu A. Thời gian thực hiện: 2020. Công việc: Lập quy hoạch.",
            "b. Công trình: Chùa Mẫu B. Thời gian thực hiện: 2022. Công việc: Thiết kế.",
        ],
        "Don_HoatDongDeNghi": [
            "- Lập quy hoạch bảo quản, tu bổ, phục hồi di tích.",
            "- Thiết kế bảo quản, tu bổ, phục hồi di tích.",
        ],
    }
    base.update(extra)
    return [{"name": k, "value": v} for k, v in base.items()]


def _ctx(identity: str, name: str = "Tài khoản Mẫu") -> dict:
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": identity}}


def _ui(fields: list[dict]) -> dict:
    return {(f["section"], f["name"]): f["value"] for f in fields}


def test_ke_khai_link_va_registry_cung_key():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.001822" and link["selectSo"] is True
    proc = registry.get_procedure(_KEY)
    assert proc["label"] == link["label"]
    assert proc["hasAttachmentStep"] is True and proc["fillWithAttach"] is True
    assert registry.get_pipeline(_KEY) is not None
    assert registry.get_attach_pipeline(_KEY) is not None


def test_nhan_dien_ca_trang_dvcqg_lan_trang_nop_bvhttdl():
    """Cơ chế 2 trang như quảng cáo băng-rôn: uuid DVCQG + MaTTHC trên trang /nop-ho-so, ở cả Auto Fill lẫn trợ lý."""
    core = next(p for p in with_ke_khai_detect_urls(registry.public_list()) if p["key"] == _KEY)
    handfree = next(p for p in HANDFREE_PROCEDURES if p["key"] == _KEY)
    for detect in (core["detect"], handfree["detect"]):
        assert set(detect["urlScope"]) == {"dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"}
        url_includes = [u.lower() for u in detect["urlIncludes"]]
        assert any(part in _APPLY_URL for part in url_includes)
        assert "019d2bfd-b558-70ee-a2f5-fb4c232b41dd" in url_includes
    assert handfree["lizFlow"] and handfree["agencySoFirst"] is True


def test_tu_nop_dien_khoi_nguoi_nop_va_don_mau_51():
    fields, warnings = mapper.enrich(_facts(), _ctx("001080000123"), today=_TODAY)
    ui = _ui(fields)
    assert ui[(S_NOP, "Ngày sinh")] == "05/06/1980"
    assert ui[(S_NOP, "Nơi cấp")] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert ui[(S_NOP, "Địa chỉ hành chính")] == "Phường Cam Đường, Tỉnh Lào Cai"
    assert ui[(S_NOP, "Địa chỉ chi tiết")] == "Tổ 2"
    assert not any(f["comp"] == "liz-checkbox" for f in fields)
    assert not any(f["section"] == S_UQ for f in fields)
    assert ui[(S_DON, LABEL_HO_TEN)] == "TRẦN VĂN MẪU"
    assert ui[(S_DON, LABEL_SO_DINH_DANH)] == "001080000123", "số trần, không ghép ngày cấp/nơi cấp"
    assert ui[(S_DON, "Địa chỉ liên hệ")].endswith("(Nay là: Tổ 2, phường Cam Đường, tỉnh Lào Cai)")
    assert ui[(S_DON, LABEL_TRINH_DO)] == "Trường Đại học Mẫu – ngành: Kiến trúc"
    assert ui[(S_DON, LABEL_KINH_NGHIEM)].startswith("a. Công trình: Đền Mẫu A.")
    assert " b. Công trình: Chùa Mẫu B." in ui[(S_DON, LABEL_KINH_NGHIEM)]
    assert "\n" not in ui[(S_DON, LABEL_KINH_NGHIEM)], "ô một dòng — trình duyệt xoá ký tự xuống dòng"
    assert ui[(S_DON, LABEL_HOAT_DONG)] == (
        "Lập quy hoạch bảo quản, tu bổ, phục hồi di tích; Thiết kế bảo quản, tu bổ, phục hồi di tích"
    )
    assert any("Số điện thoại" in w and "Email" in w for w in warnings)


def test_nop_thay_tich_uy_quyen_truoc_roi_dien_nguoi_de_nghi():
    fields, warnings = mapper.enrich(_facts(), _ctx("001090000999", "Cán Bộ Mẫu"), today=_TODAY)
    assert fields[0] == {"name": "Thông tin người ủy quyền", "comp": "liz-checkbox", "value": True, "section": ""}
    ui = _ui(fields)
    assert ui[(S_UQ, "Tên người / Tên đơn vị ủy quyền")] == "TRẦN VĂN MẪU"
    assert ui[(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp")] == "001080000123"
    assert ui[(S_UQ, "Địa chỉ chi tiết")] == "Tổ 2"
    assert not any(f["section"] == S_NOP for f in fields)
    assert (S_DON, LABEL_HO_TEN) in ui
    assert any("nộp thay" in w and "Số điện thoại" in w for w in warnings)


def test_nop_thay_thieu_dia_chi_thi_khong_tich():
    fields, warnings = mapper.enrich(
        _facts(NguoiDeNghi_DiaChiHienNay=None), _ctx("001090000999"), today=_TODAY,
    )
    assert not any(f["comp"] == "liz-checkbox" or f["section"] == S_UQ for f in fields)
    assert any("không tích" in w and "Địa chỉ chi tiết" in w for w in warnings)


def test_khong_co_moc_tai_khoan_chi_dien_don():
    fields, warnings = mapper.enrich(_facts(), {}, today=_TODAY)
    assert fields and all(f["section"] == S_DON for f in fields)
    assert any("chỉ điền Đơn Mẫu 51" in w for w in warnings)


def test_so_bi_che_khong_dien_va_khong_coi_la_tu_nop():
    fields, warnings = mapper.enrich(_facts(NguoiDeNghi_SoDinhDanh="00108"), _ctx("001080000123"), today=_TODAY)
    ui = _ui(fields)
    assert (S_DON, LABEL_SO_DINH_DANH) not in ui
    assert not any(f["section"] in (S_NOP, S_UQ) for f in fields)
    assert any("\"00108\"" in w for w in warnings)


def test_don_trong_trinh_do_thi_ghep_tu_van_bang_va_canh_bao_chung_chi_het_han():
    facts = _facts(
        NguoiDeNghi_TrinhDoChuyenMon=None, VanBang_CoSoDaoTao="Trường Đại học Mẫu", VanBang_Nganh="Kiến trúc",
        ChungChi_ThoiHan=[
            {"ten": "Chứng chỉ hành nghề hoạt động xây dựng", "so": "MAU-0001", "denNgay": "01/01/2026"},
            {"ten": "Chứng chỉ hành nghề kiến trúc", "so": "MAU-0002", "denNgay": "01/01/2031"},
        ],
    )
    fields, warnings = mapper.enrich(facts, {}, today=_TODAY)
    assert _ui(fields)[(S_DON, LABEL_TRINH_DO)] == "Trường Đại học Mẫu – ngành: Kiến trúc"
    het_han = [w for w in warnings if "hết hạn" in w]
    assert len(het_han) == 1 and "MAU-0001" in het_han[0] and "MAU-0002" not in het_han[0]


def test_moi_field_emit_co_trong_ui_fields():
    known = {(s, l): c for s, l, c, _a in UI_FIELDS}
    for ctx in (_ctx("001080000123"), _ctx("001090000999"), {}):
        fields, _ = mapper.enrich(_facts(), ctx, today=_TODAY)
        for f in fields:
            if f["comp"] != "liz-checkbox":
                assert known[(f["section"], f["name"])] == f["comp"]


def test_ba_dong_dinh_kem_boi_duong_vao_dong_2_khong_dinh_cccd():
    """Trace req_ddac8c0e0653: chứng chỉ bồi dưỡng bị bỏ ngoài bảng → thiếu 1 tệp. Nay đính chung dòng (2)."""
    names = ["don.pdf", "bang.pdf", "cc_kt.pdf", "cc_xd.pdf", "anh1.jpg", "anh2.jpg", "boi_duong.pdf", "cccd.jpg"]
    types = {0: "don_de_nghi", 1: "van_bang", 2: "cchn_kien_truc", 3: "cchn_xay_dung", 4: "anh_the", 5: "anh_the",
             6: "chung_chi_boi_duong", 7: "cccd"}
    items, warnings, classified = planner.build_plan_items([{"name": n} for n in names], types)
    assert [(i["fileName"], i["slotIndex"]) for i in items] == [
        ("don.pdf", 0), ("bang.pdf", 1), ("cc_kt.pdf", 1), ("cc_xd.pdf", 1), ("anh1.jpg", 2), ("anh2.jpg", 2),
        ("boi_duong.pdf", 1),
    ]
    assert all(i["target"] == "fixed-slot" and i["sectionHeader"] == "Thành phần hồ sơ" for i in items)
    assert len({i["slotKey"] for i in items if i["slotIndex"] == 1}) == 1, "cùng dòng → chung slotKey"
    skipped = {c["fileName"] for c in classified if c.get("target") == "skip"}
    assert skipped == {"cccd.jpg"}
    assert not any("boi_duong.pdf" in w for w in warnings)
    assert not any("ít nhất 02 ảnh" in w for w in warnings)


def test_thieu_anh_va_tep_la_vao_dong_ban_sao_kem_canh_bao():
    items, warnings, _ = planner.build_plan_items(
        [{"name": "don.pdf"}, {"name": "la.pdf"}, {"name": "anh.jpg"}], {0: "don_de_nghi", 2: "anh_the"},
    )
    assert [i["slotIndex"] for i in items] == [0, 1, 2]
    assert any("la.pdf" in w for w in warnings)
    assert any("mới có 1 ảnh" in w for w in warnings)


def test_anh_khong_chu_nhan_tat_dinh():
    assert planner._looks_like_photo({"type": "image/jpeg"}, "  ")
    assert not planner._looks_like_photo({"type": "image/jpeg"}, "ĐƠN ĐỀ NGHỊ CẤP CHỨNG CHỈ HÀNH NGHỀ BẢO QUẢN")


def test_anh_pdf_ky_so_chi_co_dau_chu_ky_van_la_anh():
    text = "Ký hiệu: Nguyễn Văn Mẫu\nHỌC PHỔ THÔNG VÀ\nNHÂN DÂN TỈNH\nNĂM 2026\nNgày ký: 05-05-2026\n13:48:41 - 07:00"
    assert planner._looks_like_photo({"type": "application/pdf"}, text)
    don = (
        "Ký bởi: Nguyễn Văn Mẫu\nĐƠN ĐỀ NGHỊ CẤP CHỨNG CHỈ HÀNH NGHỀ BẢO QUẢN, TU BỔ, PHỤC HỒI DI TÍCH\n"
        "Kính gửi: Giám đốc Sở Văn hóa, Thể thao và Du lịch"
    )
    assert not planner._looks_like_photo({"type": "application/pdf"}, don)


def test_slot_keywords_moi_dong_mot_cum_rieng():
    """Mỗi cụm chỉ khớp đúng dòng của nó trên chữ thật của 3 dòng thành phần (đã fold như engine)."""
    rows = [
        "1 Đơn đề nghị cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích theo Mẫu số 51 tại Phụ lục I",
        "2 Bản sao có chứng thực … Chứng chỉ hành nghề thiết kế quy hoạch xây dựng, bằng tốt nghiệp đại học trở lên "
        "thuộc các chuyên ngành xây dựng, kiến trúc liên quan đến hoạt động đề nghị cấp Chứng chỉ hành nghề bảo quản",
        "3 Ít nhất 02 ảnh màu khổ 4 cm x 6 cm chụp trong vòng 06 tháng gần nhất",
    ]
    folded = [planner._fold(r) for r in rows]
    for slot, keywords in planner._SLOT_KEYWORDS.items():
        assert [i for i, text in enumerate(folded) if any(k in text for k in keywords)] == [slot]


def test_field_review_tu_kham_pha():
    config = field_review_registry.get(_KEY)
    assert set(config["required"]) == {LABEL_TRINH_DO, LABEL_KINH_NGHIEM, LABEL_HOAT_DONG}
    assert LABEL_HO_TEN in config["noAsk"], "nhãn trùng biểu mẫu thủ tục khác trên cùng trang — không hỏi"


def test_extension_khong_nhac_thieu_co_cong_tinh_tren_trang_nop():
    src_file = _ROOT / "auto-fill-hcc-extension" / "content" / "portal-quangninh.js"
    if not src_file.exists():
        return
    block = src_file.read_text(encoding="utf-8").split("NO_FLOW_MA_TTHC = new Set(", 1)[1].split(")", 1)[0]
    assert '"1.001822"' in block
