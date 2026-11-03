"""[Bộ VHTTDL] Thủ tục cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (1.002003, QT-10).

Khoá: nhận diện cả trang DVCQG lẫn trang nộp cổng Bộ VHTTDL; khối người nộp/ủy quyền dùng chung bản cấp mới; khối
Mẫu 51 (trình độ, kinh nghiệm) + khối cấp lại (số/ngày cấp chứng chỉ cũ, đúng một ô lý do); lý do hết hạn ghi "Ghi
chú"; 3 dòng đính kèm dò theo chữ, chứng chỉ đã cấp + văn bằng tạm đính dòng (2), ảnh mang dấu ký số vẫn nhận là ảnh.
"""

from datetime import date
from pathlib import Path

from app.channels.handfree.chat.field_review import registry as field_review_registry
from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE_PROCEDURES
from app.pipelines.cap_lai_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.attach import planner
from app.pipelines.cap_lai_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process import mapper
from app.pipelines.cap_lai_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.schema import (
    LABEL_BI_HONG,
    LABEL_BI_MAT,
    LABEL_BO_SUNG,
    LABEL_DIA_CHI_LIEN_HE,
    LABEL_DIEN_THOAI,
    LABEL_GHI_CHU,
    LABEL_HO_TEN,
    LABEL_KINH_NGHIEM,
    LABEL_NGAY_CAP_CC_CU,
    LABEL_NGAY_SINH,
    LABEL_SO_CC_CU,
    LABEL_SO_DINH_DANH,
    LABEL_TEN_CAP_LAI,
    LABEL_TRINH_DO,
    S_CAP_LAI,
    S_CHUNG,
    S_DON,
    S_NOP,
    S_UQ,
    UI_FIELDS,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

_KEY = "cap-lai-chung-chi-hanh-nghe-bao-quan-tu-bo-phuc-hoi-di-tich"
_ROOT = Path(__file__).resolve().parents[2].parent
_TODAY = date(2026, 11, 3)
_APPLY_URL = ("https://dichvucong.bvhttdl.gov.vn/nop-ho-so?MaTTHC=1.002003&MaCoQuanThucHien=H00.01"
              "&MaDVC=1.002003.01&MaTTHCDP=1.002003&vneid=1").lower()
_LY_DO_HET_HAN = (
    "+ Chứng chỉ hành nghề thi công tu bổ di tích số 12/SVHTT-QLDT cấp ngày 01/02/2021 đã hết hạn sử dụng ngày "
    "31/01/2026."
)


def _facts(**extra) -> list[dict]:
    base = {
        "NguoiDeNghi_HoTen": "Trần Văn Mẫu",
        "NguoiDeNghi_NgaySinh": "05/06/1980",
        "NguoiDeNghi_SoDinhDanh": "001080000123",
        "NguoiDeNghi_NgayCap": "10/10/2021",
        "NguoiDeNghi_NoiCap": "Cục QLHC về TTXH",
        "NguoiDeNghi_DiaChiLienHe": "Tổ 2 Thôn Mẫu, phường Cam Đường, tỉnh Lào Cai.",
        "NguoiDeNghi_DiaChiHienNay": {"tinh": "Lào Cai", "xa": "phường Cam Đường", "chiTietDuoiXa": "Tổ 2 Thôn Mẫu"},
        "NguoiDeNghi_DienThoai": "0912 345678",
        "NguoiDeNghi_TrinhDoChuyenMon": [
            "+ Bằng kỹ sư do Trường Đại học Mẫu cấp – chuyên ngành xây dựng dân dụng.",
            "+ Chứng chỉ hành nghề giám sát công tác xây dựng hạng II.",
        ],
        "NguoiDeNghi_KinhNghiem": [
            "- Thời gian có kinh nghiệm nghề nghiệp: 10 năm.",
            "- Đơn vị công tác: Công ty Mẫu A",
            "01. Tháng 03/2024 | Công ty Mẫu A | Thi công tu bổ đình Mẫu | Ban quản lý di tích Mẫu",
            "02. Tháng 05/2025 | Công ty Mẫu A | Lập báo cáo kinh tế - kỹ thuật chùa Mẫu | Sở Mẫu",
        ],
        "Don_HoatDongDeNghi": ["+ Thi công bảo quản, tu bổ, phục hồi di tích."],
        "Don_LyDoCapLai": _LY_DO_HET_HAN,
        "ChungChiCu_So": "12/SVHTT-QLDT",
        "ChungChiCu_NgayCap": "01/02/2021",
        "ChungChiCu_DenNgay": "31/01/2026",
    }
    base.update(extra)
    return [{"name": k, "value": v} for k, v in base.items() if v is not None]


def _ctx(identity: str, name: str = "Tài khoản Mẫu") -> dict:
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": identity}}


def _ui(fields: list[dict]) -> dict:
    return {(f["section"], f["name"]): f["value"] for f in fields}


def test_ke_khai_link_va_registry_cung_key():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.002003" and link["selectSo"] is True
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
        assert "019d2bfd-b5a1-72a9-a768-957fc952b946" in url_includes
        assert not any("1.001822" in part for part in url_includes), "không bắt nhầm trang cấp mới"
    assert handfree["lizFlow"] and handfree["agencySoFirst"] is True


def test_tu_nop_dien_khoi_mau_51_va_khoi_cap_lai():
    fields, warnings = mapper.enrich(_facts(), _ctx("001080000123"), today=_TODAY)
    ui = _ui(fields)
    assert ui[(S_NOP, "Nơi cấp")] == "Cục QLHC về TTXH"
    assert ui[(S_NOP, "Địa chỉ hành chính")] == "Phường Cam Đường, Tỉnh Lào Cai"
    assert not any(f["section"] == S_UQ for f in fields)
    # Khối Mẫu 51: số định danh trần (mapping QT-10), trình độ + kinh nghiệm một dòng.
    assert ui[(S_DON, LABEL_HO_TEN)] == "TRẦN VĂN MẪU"
    assert ui[(S_DON, LABEL_SO_DINH_DANH)] == "001080000123"
    assert ui[(S_DON, LABEL_DIA_CHI_LIEN_HE)] == "Tổ 2 Thôn Mẫu, phường Cam Đường, tỉnh Lào Cai."
    assert ui[(S_DON, LABEL_TRINH_DO)].startswith("+ Bằng kỹ sư do Trường Đại học Mẫu cấp")
    assert " + Chứng chỉ hành nghề giám sát" in ui[(S_DON, LABEL_TRINH_DO)]
    kinh_nghiem = ui[(S_DON, LABEL_KINH_NGHIEM)]
    assert "\n" not in kinh_nghiem and "02. Tháng 05/2025 | Công ty Mẫu A" in kinh_nghiem
    # Khối cấp lại.
    assert ui[(S_CAP_LAI, LABEL_TEN_CAP_LAI)] == "TRẦN VĂN MẪU"
    assert ui[(S_CAP_LAI, LABEL_SO_DINH_DANH)] == "001080000123"
    assert ui[(S_CAP_LAI, LABEL_NGAY_SINH)] == "05/06/1980"
    assert ui[(S_CAP_LAI, LABEL_DIEN_THOAI)] == "0912345678"
    assert ui[(S_CAP_LAI, LABEL_SO_CC_CU)] == "12/SVHTT-QLDT"
    assert ui[(S_CAP_LAI, LABEL_NGAY_CAP_CC_CU)] == "01/02/2021"
    # Hết hạn: không ô lý do nào của khối cấp lại, lý do vào Ghi chú (bỏ dấu "+").
    assert not any((S_CAP_LAI, label) in ui for label in (LABEL_BO_SUNG, LABEL_BI_HONG, LABEL_BI_MAT))
    assert ui[(S_CHUNG, LABEL_GHI_CHU)].startswith("Chứng chỉ hành nghề thi công tu bổ di tích số 12/SVHTT-QLDT")
    assert any("HẾT HẠN" in w and "Ghi chú" in w for w in warnings)
    assert any("Email" in w for w in warnings)


def test_nop_thay_tich_uy_quyen_van_dien_hai_khoi_don():
    fields, warnings = mapper.enrich(_facts(), _ctx("001090000999", "Cán Bộ Mẫu"), today=_TODAY)
    assert fields[0]["comp"] == "liz-checkbox" and fields[0]["name"] == "Thông tin người ủy quyền"
    ui = _ui(fields)
    assert ui[(S_UQ, "Tên người / Tên đơn vị ủy quyền")] == "TRẦN VĂN MẪU"
    assert ui[(S_UQ, "Số điện thoại")] == "0912345678"
    assert (S_DON, LABEL_HO_TEN) in ui and (S_CAP_LAI, LABEL_TEN_CAP_LAI) in ui
    assert any("nộp thay" in w for w in warnings)


def test_ly_do_bi_mat_bo_sung_bi_hong_vao_dung_o():
    cases = (
        ("Chứng chỉ số 12/SVHTT-QLDT đã bị mất do hỏa hoạn.", LABEL_BI_MAT),
        ("Chứng chỉ bị hư hỏng do ngập nước.", LABEL_BI_HONG),
        ("Đề nghị bổ sung nội dung hành nghề thiết kế tu bổ di tích.", LABEL_BO_SUNG),
    )
    for ly_do, label in cases:
        fields, warnings = mapper.enrich(_facts(Don_LyDoCapLai=ly_do), {}, today=_TODAY)
        ui = _ui(fields)
        assert ui[(S_CAP_LAI, label)].startswith(ly_do), label
        others = {LABEL_BO_SUNG, LABEL_BI_HONG, LABEL_BI_MAT} - {label}
        assert not any((S_CAP_LAI, o) in ui for o in others), label
        assert (S_CHUNG, LABEL_GHI_CHU) not in ui
        assert not any("HẾT HẠN" in w for w in warnings)
    fields, _ = mapper.enrich(_facts(Don_LyDoCapLai=cases[2][0]), {}, today=_TODAY)
    assert "Các hoạt động đề nghị: Thi công bảo quản, tu bổ, phục hồi di tích." in _ui(fields)[(S_CAP_LAI, LABEL_BO_SUNG)]


def test_ten_rieng_hong_va_mat_truoc_khong_bi_hieu_la_ly_do():
    assert mapper.loai_ly_do("Cấp tại phường Hồng Hải, mặt trước có dấu") is None
    assert mapper.loai_ly_do("đã hết hạn sử dụng") == mapper.LY_DO_HET_HAN


def test_don_khong_doc_duoc_ly_do_thi_ghep_tu_han_chung_chi():
    fields, warnings = mapper.enrich(_facts(Don_LyDoCapLai=None), {}, today=_TODAY)
    assert _ui(fields)[(S_CHUNG, LABEL_GHI_CHU)] == (
        "Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích số 12/SVHTT-QLDT cấp ngày 01/02/2021 đã hết hạn sử "
        "dụng ngày 31/01/2026."
    )
    assert any("HẾT HẠN" in w for w in warnings)

    fields, warnings = mapper.enrich(
        _facts(Don_LyDoCapLai=None, ChungChiCu_DenNgay="31/01/2031"), {}, today=_TODAY,
    )
    assert (S_CHUNG, LABEL_GHI_CHU) not in _ui(fields)
    assert any("Chưa đọc được \"Lý do cấp lại\"" in w for w in warnings)


def test_khong_co_moc_tai_khoan_va_thieu_chung_chi_cu():
    fields, warnings = mapper.enrich(_facts(ChungChiCu_So=None, ChungChiCu_NgayCap=None), {}, today=_TODAY)
    assert not any(f["section"] in (S_NOP, S_UQ) for f in fields)
    assert any("chỉ điền Đơn Mẫu 51" in w for w in warnings)
    assert any("Số chứng chỉ đã cấp" in w and "Ngày cấp chứng chỉ đã cấp" in w for w in warnings)


def test_moi_field_emit_co_trong_ui_fields():
    known = {(s, l): c for s, l, c, _a in UI_FIELDS}
    for ctx in (_ctx("001080000123"), _ctx("001090000999"), {}):
        fields, _ = mapper.enrich(_facts(), ctx, today=_TODAY)
        for f in fields:
            if f["comp"] != "liz-checkbox":
                assert known[(f["section"], f["name"])] == f["comp"]


def test_ba_dong_dinh_kem_chung_chi_cu_va_van_bang_tam_dong_2():
    names = ["don.pdf", "van_bang.pdf", "chung_chi_cu.pdf", "anh1.pdf", "anh2.pdf", "cccd.jpg"]
    types = {0: "don_de_nghi", 1: "van_bang", 2: "chung_chi_da_cap", 3: "anh_the", 4: "anh_the", 5: "cccd"}
    files = [{"name": n, "dataUrl": "data:application/pdf;base64,QUFB" if n.startswith("anh") else f"x-{n}"}
             for n in names]
    items, warnings, classified = planner.build_plan_items(files, types)
    assert [(i["fileName"], i["slotIndex"]) for i in items] == [
        ("don.pdf", 0), ("van_bang.pdf", 1), ("chung_chi_cu.pdf", 1), ("anh1.pdf", 2), ("anh2.pdf", 2),
    ]
    assert all(i["target"] == "fixed-slot" and i["sectionHeader"] == "Thành phần hồ sơ" for i in items)
    assert len({i["slotKey"] for i in items if i["slotIndex"] == 1}) == 1, "cùng dòng → chung slotKey"
    assert {c["fileName"] for c in classified if c.get("target") == "skip"} == {"cccd.jpg"}
    assert any("tạm đính" in w and "van_bang.pdf" in w and "chung_chi_cu.pdf" in w for w in warnings)
    assert any("giống hệt nhau" in w and "anh1.pdf" in w for w in warnings)
    assert not any("mới có" in w for w in warnings)
    assert not any("Chưa thấy" in w for w in warnings)


def test_thieu_don_chung_chi_cu_va_anh():
    items, warnings, _ = planner.build_plan_items([{"name": "la.pdf"}, {"name": "anh.jpg"}], {1: "anh_the"})
    assert [i["slotIndex"] for i in items] == [1, 2]
    assert any("ĐƠN ĐỀ NGHỊ CẤP LẠI" in w for w in warnings)
    assert any("CHỨNG CHỈ HÀNH NGHỀ đã được cấp" in w for w in warnings)
    assert any("la.pdf" in w and "Chưa nhận ra" in w for w in warnings)
    assert any("mới có 1 ảnh" in w for w in warnings)


def test_anh_chi_co_dau_ky_so_van_nhan_la_anh():
    dau = ("Ký bởi: Nguyễn Văn Mẫu Cơ quan: \"SỞ VĂN HÓA, THỂ THAO VÀ DU LỊCH\", ỦY BAN NHÂN DÂN TỈNH MẪU "
           "Ngày ký: 30-10-2026 14:53:01 +07:00")
    assert planner._looks_like_photo({"type": "application/pdf"}, planner._bo_dau_ky_so(dau))
    don = dau + " ĐƠN ĐỀ NGHỊ CẤP LẠI CHỨNG CHỈ HÀNH NGHỀ BẢO QUẢN, TU BỔ, PHỤC HỒI DI TÍCH"
    assert not planner._looks_like_photo({"type": "application/pdf"}, planner._bo_dau_ky_so(don))


def test_slot_keywords_moi_dong_mot_cum_rieng():
    rows = [
        "1 Đơn đề nghị cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích theo Mẫu số 51 tại Phụ lục I "
        "ban hành kèm theo Nghị định số 308/2025/NĐ-CP",
        "2 Trường hợp bổ sung nội dung hành nghề đã được ghi nhận trong Chứng chỉ hành nghề bảo quản, tu bổ, phục "
        "hồi di tích đã cấp, phải gửi kèm theo hồ sơ các bản sao có chứng thực … đối với nội dung hành nghề bổ sung.",
        "3 Ít nhất 02 ảnh màu khổ 4 cm x 6 cm chụp trong vòng 06 tháng gần nhất, độ phân giải tối thiểu 300 dpi",
    ]
    folded = [planner._fold(r) for r in rows]
    for slot, keywords in planner._SLOT_KEYWORDS.items():
        assert [i for i, text in enumerate(folded) if any(k in text for k in keywords)] == [slot]


def test_field_review_tu_kham_pha():
    config = field_review_registry.get(_KEY)
    assert set(config["required"]) == {LABEL_SO_CC_CU, LABEL_NGAY_CAP_CC_CU, LABEL_TRINH_DO, LABEL_KINH_NGHIEM}
    assert LABEL_HO_TEN in config["noAsk"] and LABEL_BO_SUNG in config["noAsk"]
    assert LABEL_TEN_CAP_LAI not in config["noAsk"] and LABEL_SO_CC_CU not in config["noAsk"]


def test_extension_khong_nhac_thieu_co_va_gui_moc_tai_khoan():
    ext = _ROOT / "auto-fill-hcc-extension"
    portal, popup = ext / "content" / "portal-quangninh.js", ext / "popup.js"
    if not portal.exists() or not popup.exists():
        return
    block = portal.read_text(encoding="utf-8").split("NO_FLOW_MA_TTHC = new Set(", 1)[1].split(")", 1)[0]
    assert '"1.002003"' in block
    assert f'cfg.key === "{_KEY}"' in popup.read_text(encoding="utf-8")
