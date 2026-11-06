"""[Bộ VHTTDL] Thủ tục cấp Giấy chứng nhận khóa cập nhật kiến thức cho hướng dẫn viên du lịch (1.004605, QT-123).

Khoá: nhận diện ở cả trang DVCQG lẫn trang nộp cổng Bộ VHTTDL (Auto Fill + trợ lý); tài khoản trùng người đăng ký (CCCD,
đơn để số mẫu thì họ tên) → điền khối người nộp, khác người → tích "Thông tin người ủy quyền" rồi điền vào đó; khối đơn đề nghị điền thẻ HDV + công văn + ngày khóa (Nơi cấp/Ngày cấp thẻ có
`after` = ô Số thẻ); đơn điền mẫu (số 0, @example.com) không dùng; 2 bộ nơi cấp/ngày cấp thẻ lấy bộ hợp lệ; đính kèm 1
dòng dò theo chữ, CCCD/thẻ HDV không đính.
"""

from datetime import date
from pathlib import Path

from app.channels.handfree.chat.field_review import registry as field_review_registry
from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG
from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE_PROCEDURES
from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.attach import planner
from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.process import mapper
from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.process.schema import (
    LABEL_GIOI_TINH,
    LABEL_LOAI_THE,
    LABEL_NGAY_BAT_DAU,
    LABEL_NGAY_CAP_THE,
    LABEL_NGAY_KET_THUC,
    LABEL_NGAY_THONG_BAO,
    LABEL_NOI_CAP_THE,
    LABEL_SO_THE,
    LABEL_THONG_BAO_SO,
    S_DON,
    S_NOP,
    S_UQ,
    UI_FIELDS,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

_KEY = "cap-giay-chung-nhan-khoa-cap-nhat-kien-thuc-huong-dan-vien-du-lich"
_UUID = "019d2bfd-d4aa-756f-b5fc-8a172aa4633a"
_ROOT = Path(__file__).resolve().parents[2].parent
# URL trang nộp sau khi bấm "Nộp trực tuyến" trên DVCQG (popup so khớp trên URL đã lower-case).
_APPLY_URL = ("https://dichvucong.bvhttdl.gov.vn/nop-ho-so?MaTTHC=1.004605&MaCoQuanThucHien=H32.25"
              "&MaDVC=1.004605.01&MaTTHCDP=1.004605&vneid=1").lower()
_TODAY = date(2026, 3, 20)
_CCCD = "001090012345"


def _facts(**extra) -> list[dict]:
    base = {
        "NguoiDeNghi_HoTen": "TRẦN VĂN MẪU",
        "NguoiDeNghi_SoDinhDanh": _CCCD,
        "NguoiDeNghi_NgaySinh": "05/06/1990",
        "NguoiDeNghi_GioiTinh": "Nam",
        "NguoiDeNghi_DiaChi": {"tinh": "Khánh Hòa", "xa": "Phường Nha Trang", "chiTietDuoiXa": ""},
        "NguoiDeNghi_DienThoai": "0912 345 678",
        "NguoiDeNghi_Email": "tranvanmau@gmail.com",
        "The_Loai": "nội địa",
        "The_So": "156123456",
        "The_NoiCap": "Sở VHTTDL Khánh Hòa",
        "The_NgayCap": "01/01/2025",
        "CongVan_So": "1234 /SVHTTDL- QLDL",
        "CongVan_Ngay": "05/03 /2026",
        "Khoa_TuNgay": "10/04/2026",
        "Khoa_DenNgay": "12/04/2026",
        "Don_CoQuanNhan": "Sở Văn hóa, Thể thao và Du lịch tỉnh Khánh Hòa",
    }
    base.update(extra)
    return [{"name": k, "value": v} for k, v in base.items() if v is not None]


def _ui(fields: list[dict]) -> dict:
    return {(f["section"], f["name"]): f["value"] for f in fields}


def _ctx(identity: str = _CCCD) -> dict:
    return {"formContext": {"applicantFullname": "Trần Văn Mẫu", "applicantIdentityNumber": identity}}


def test_ke_khai_link_va_registry_cung_key():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.004605" and link["selectSo"] is True
    assert link["url"].endswith(_UUID)
    proc = registry.get_procedure(_KEY)
    assert proc["label"] == link["label"]
    assert proc["hasAttachmentStep"] is True and proc["fillWithAttach"] is True
    assert registry.get_pipeline(_KEY) is not None
    assert registry.get_attach_pipeline(_KEY) is not None


def test_nhan_dien_ca_trang_dvcqg_lan_trang_nop_bvhttdl_va_len_tro_ly():
    core = next(p for p in with_ke_khai_detect_urls(registry.public_list()) if p["key"] == _KEY)
    handfree = next(p for p in HANDFREE_PROCEDURES if p["key"] == _KEY)
    for detect in (core["detect"], handfree["detect"]):
        assert set(detect["urlScope"]) == {"dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"}
        url_includes = [u.lower() for u in detect["urlIncludes"]]
        assert any(part in _APPLY_URL for part in url_includes)
        assert _UUID in url_includes
        assert not any(part in _APPLY_URL.replace("1.004605", "1.004623") for part in url_includes), "không bắt thẻ HDV"
    assert handfree["label"] == registry.get_procedure(_KEY)["label"]
    assert handfree["lizFlow"] and handfree["agencyProvinceOnly"] is True and handfree["agencySoFirst"] is True
    assert handfree["agencyDeptLabel"] == "Sở Văn hóa, Thể thao và Du lịch"
    assert handfree["keKhaiUrl"].endswith(_UUID)
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]


def test_tai_khoan_trung_cccd_thi_dien_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_facts(), _ctx(), today=_TODAY)
    ui = _ui(fields)
    assert ui[(S_NOP, "Ngày sinh")] == "05/06/1990"
    assert ui[(S_NOP, "Số điện thoại")] == "0912345678"
    assert ui[(S_NOP, "Email")] == "tranvanmau@gmail.com"
    assert ui[(S_NOP, "Địa chỉ hành chính")] == "Phường Nha Trang, Tỉnh Khánh Hòa"
    assert ui[(S_NOP, "Địa chỉ chi tiết")] == "Phường Nha Trang, Tỉnh Khánh Hòa", "đơn chỉ ghi tới phường"
    assert (S_NOP, "Ngày cấp") not in ui and (S_NOP, "Nơi cấp") not in ui, "đơn không có ngày/nơi cấp CCCD"
    assert any("Địa chỉ chi tiết" in w and "số nhà" in w for w in warnings)
    assert not any("Không điền khối" in w for w in warnings)
    assert not any(f["comp"] == "liz-checkbox" or f["section"] == S_UQ for f in fields)


def test_khong_co_moc_tai_khoan_chi_dien_khoi_don():
    fields, warnings = mapper.enrich(_facts(), {}, today=_TODAY)
    ui = _ui(fields)
    assert not any(f["section"] in (S_NOP, S_UQ) or f["comp"] == "liz-checkbox" for f in fields)
    assert ui[(S_DON, LABEL_LOAI_THE)] == "Nội địa"
    assert ui[(S_DON, LABEL_GIOI_TINH)] == "Nam"
    assert ui[(S_DON, LABEL_SO_THE)] == "156123456"
    assert ui[(S_DON, LABEL_NOI_CAP_THE)] == "Sở VHTTDL Khánh Hòa"
    assert ui[(S_DON, LABEL_NGAY_CAP_THE)] == "01/01/2025"
    assert ui[(S_DON, LABEL_THONG_BAO_SO)] == "1234/SVHTTDL-QLDL"
    assert ui[(S_DON, LABEL_NGAY_THONG_BAO)] == "05/03/2026"
    assert ui[(S_DON, LABEL_NGAY_BAT_DAU)] == "10/04/2026"
    assert ui[(S_DON, LABEL_NGAY_KET_THUC)] == "12/04/2026"
    # Nơi cấp / Ngày cấp thẻ trùng nhãn khối người nộp → engine còn có đường lùi theo vị trí sau ô Số thẻ.
    by_label = {f["name"]: f for f in fields if f["section"] == S_DON}
    for label in (LABEL_NOI_CAP_THE, LABEL_NGAY_CAP_THE):
        assert by_label[label]["after"][0] == LABEL_SO_THE
    assert any("Không điền khối \"Thông tin người nộp hồ sơ\"" in w and "chưa có thông tin tài khoản" in w
               for w in warnings)
    assert any("Khánh Hòa" in w and "Cơ quan giải quyết" in w for w in warnings)
    assert not any("Chưa đọc được trên Đơn" in w for w in warnings)


def test_tai_khoan_khac_cccd_thi_tich_uy_quyen_va_dien_nguoi_dang_ky():
    ctx = {"formContext": {"applicantFullname": "Lê Thị Cán Bộ", "applicantIdentityNumber": "001190099999"}}
    fields, warnings = mapper.enrich(_facts(), ctx, today=_TODAY)
    assert fields[0] == {"name": "Thông tin người ủy quyền", "comp": "liz-checkbox", "value": True, "section": ""}
    ui = _ui(fields)
    assert not any(f["section"] == S_NOP for f in fields), "khối người nộp giữ thông tin tài khoản"
    assert ui[(S_UQ, "Tên người / Tên đơn vị ủy quyền")] == "TRẦN VĂN MẪU"
    assert ui[(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp")] == _CCCD
    assert ui[(S_UQ, "Ngày sinh")] == "05/06/1990"
    assert ui[(S_UQ, "Số điện thoại")] == "0912345678"
    assert ui[(S_UQ, "Email")] == "tranvanmau@gmail.com"
    assert ui[(S_UQ, "Địa chỉ hành chính")] == "Phường Nha Trang, Tỉnh Khánh Hòa"
    assert ui[(S_UQ, "Địa chỉ chi tiết")] == "Phường Nha Trang, Tỉnh Khánh Hòa"
    assert any("nộp thay" in w and "số CCCD" in w for w in warnings)
    assert not any("còn trống ô bắt buộc" in w for w in warnings)
    assert (S_DON, LABEL_SO_THE) in ui, "khối đơn vẫn điền"


def test_trung_cccd_ma_ten_tai_khoan_viet_khac_van_la_tu_nop():
    ctx = {"formContext": {"applicantFullname": "Trần Văn Mẫu Khác", "applicantIdentityNumber": _CCCD}}
    fields, _ = mapper.enrich(_facts(), ctx, today=_TODAY)
    assert (S_NOP, "Ngày sinh") in _ui(fields)
    assert not any(f["section"] == S_UQ for f in fields), "có số CCCD thật thì so số, không so tên"


def test_don_so_mau_ten_khac_tai_khoan_thi_tich_uy_quyen_bo_trong_cmnd():
    ctx = {"formContext": {"applicantFullname": "Lê Thị Cán Bộ", "applicantIdentityNumber": "001190099999"}}
    facts = _facts(NguoiDeNghi_SoDinhDanh="000000000000", NguoiDeNghi_DienThoai="0000000000")
    fields, warnings = mapper.enrich(facts, ctx, today=_TODAY)
    assert fields[0]["comp"] == "liz-checkbox"
    ui = _ui(fields)
    assert ui[(S_UQ, "Tên người / Tên đơn vị ủy quyền")] == "TRẦN VĂN MẪU"
    assert (S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp") not in ui and (S_UQ, "Số điện thoại") not in ui
    assert any("nộp thay" in w and "họ tên" in w for w in warnings)
    assert any("ủy quyền\" còn trống ô bắt buộc" in w and "CMND/Hộ chiếu" in w and "Số điện thoại" in w
               for w in warnings)


def test_don_dien_mau_ten_trung_tai_khoan_la_tu_nop_khong_dung_so_0_va_email_example():
    facts = _facts(NguoiDeNghi_SoDinhDanh="000000000000", NguoiDeNghi_DienThoai="0000000000",
                   NguoiDeNghi_Email="mau@example.com", NguoiDeNghi_EmailKhac="tranvanmau@gmail.com")
    fields, warnings = mapper.enrich(facts, _ctx(), today=_TODAY)
    ui = _ui(fields)
    assert ui[(S_NOP, "Email")] == "tranvanmau@gmail.com", "dãy số 0 không so được → so họ tên, trùng → tự nộp"
    assert (S_NOP, "Số điện thoại") not in ui
    assert not any(f["section"] == S_UQ for f in fields)
    assert ui[(S_DON, LABEL_GIOI_TINH)] == "Nam", "giới tính vẫn lấy theo ô đánh dấu"
    mau = next(w for w in warnings if "giá trị điền MẪU" in w)
    assert "000000000000" in mau and "0000000000" in mau and "mau@example.com" in mau
    assert any("hai email" in w and "đã dùng \"tranvanmau@gmail.com\"" in w for w in warnings)


def test_hai_email_that_lay_email_dau_va_canh_bao():
    fields, warnings = mapper.enrich(_facts(NguoiDeNghi_EmailKhac="mau.khac@gmail.com"), _ctx(), today=_TODAY)
    assert _ui(fields)[(S_NOP, "Email")] == "tranvanmau@gmail.com"
    assert any("hai email" in w for w in warnings)


def test_hai_bo_noi_cap_ngay_cap_the_bo_tuong_lai_bi_bo():
    fields, warnings = mapper.enrich(
        _facts(The_NoiCapKhac="Phường Mẫu, Thành phố Hà Nội", The_NgayCapKhac="03/12/2026"), {}, today=_TODAY,
    )
    ui = _ui(fields)
    assert ui[(S_DON, LABEL_NOI_CAP_THE)] == "Sở VHTTDL Khánh Hòa"
    assert ui[(S_DON, LABEL_NGAY_CAP_THE)] == "01/01/2025"
    assert any("hai nơi cấp" in w for w in warnings)
    assert any("03/12/2026" in w and "tương lai" in w for w in warnings)

    # Bộ đầu là ngày tương lai, bộ sau hợp lệ → lấy bộ sau.
    fields, _ = mapper.enrich(_facts(The_NgayCap="03/12/2026", The_NgayCapKhac="01/01/2025"), {}, today=_TODAY)
    assert _ui(fields)[(S_DON, LABEL_NGAY_CAP_THE)] == "01/01/2025"


def test_the_tai_diem_va_ngay_khoa_nguoc_thi_canh_bao():
    fields, warnings = mapper.enrich(
        _facts(The_Loai="tại điểm", Khoa_TuNgay="12/04/2026", Khoa_DenNgay="10/04/2026"), {}, today=_TODAY,
    )
    assert _ui(fields)[(S_DON, LABEL_LOAI_THE)] == "Tại điểm"
    assert any("TẠI ĐIỂM" in w for w in warnings)
    assert any("Ngày kết thúc khóa" in w for w in warnings)


def test_gioi_tinh_suy_tu_cccd_khi_don_khong_danh_dau():
    fields, _ = mapper.enrich(_facts(NguoiDeNghi_GioiTinh=None, NguoiDeNghi_SoDinhDanh="001190012345"), {},
                              today=_TODAY)
    assert _ui(fields)[(S_DON, LABEL_GIOI_TINH)] == "Nữ"


def test_khong_doc_duoc_gi_thi_canh_bao_nhap_tay():
    fields, warnings = mapper.enrich([], {}, today=_TODAY)
    assert fields == []
    missing = next(w for w in warnings if "Chưa đọc được trên Đơn Mẫu 06" in w)
    assert "Số thẻ" in missing and "Căn cứ Thông báo số" in missing and "Ngày kết thúc" in missing


def test_moi_field_emit_co_trong_ui_fields():
    known = {(s, l): c for s, l, c, _a in UI_FIELDS}
    nop_thay = {"formContext": {"applicantFullname": "Lê Thị Cán Bộ", "applicantIdentityNumber": "001190099999"}}
    for facts, options in ((_facts(), _ctx()), (_facts(), {}), (_facts(), nop_thay)):
        fields, _ = mapper.enrich(facts, options, today=_TODAY)
        assert fields
        for f in fields:
            if f["comp"] != "liz-checkbox":
                assert known[(f["section"], f["name"])] == f["comp"]


def test_dinh_kem_don_vao_dong_1_khong_dinh_cccd_the_hdv():
    names = ["don.pdf", "cccd.jpg", "the.jpg", "la.pdf"]
    types = {0: "don_dang_ky", 1: "cccd", 2: "the_hdv", 3: "other"}
    items, warnings, classified = planner.build_plan_items([{"name": n} for n in names], types, {0: "ĐĂNG KÝ …"})
    assert [(i["fileName"], i["slotIndex"]) for i in items] == [("don.pdf", 0), ("la.pdf", 0)]
    assert all(i["target"] == "fixed-slot" and i["sectionHeader"] == "Thành phần hồ sơ" for i in items)
    assert len({i["slotKey"] for i in items}) == 1, "cùng dòng → chung slotKey"
    assert items[0]["loaiBan"] == "Bản chính"
    assert {c["fileName"] for c in classified if c.get("target") == "skip"} == {"cccd.jpg", "the.jpg"}
    assert any("la.pdf" in w and "dòng (1)" in w for w in warnings)
    assert not any("Chưa thấy" in w or "BẢN MẪU" in w for w in warnings)


def test_dinh_kem_thieu_don_hai_don_va_don_ban_mau():
    _, warnings, _ = planner.build_plan_items([{"name": "cccd.jpg"}], {0: "cccd"})
    assert any("Chưa thấy ĐƠN ĐĂNG KÝ" in w for w in warnings)

    texts = {0: "ĐĂNG KÝ THAM DỰ …\nBẢN MẪU THAM KHẢO – THÔNG TIN ĐIỀN MẪU, CẦN ĐỐI CHIẾU TRƯỚC KHI SỬ DỤNG"}
    _, warnings, _ = planner.build_plan_items(
        [{"name": "don.pdf"}, {"name": "don2.pdf"}], {0: "don_dang_ky", 1: "don_dang_ky"}, texts,
    )
    assert any("Có 2 tệp Đơn đăng ký" in w for w in warnings)
    assert any("don.pdf" in w and "BẢN MẪU" in w for w in warnings)


def test_slot_keywords_khop_chu_that_cua_dong_thanh_phan():
    row = ("1 (1) Đăng ký tham dự khóa cập nhật kiến thức cho hướng dẫn viên du lịch (Mẫu số 06 Phụ lục II ban hành "
           "đính kèm theo Thông tư 04/2024/TT-BVHTTDL ngày 26 tháng 6 năm 2024).")
    assert all(keyword in planner._fold(row) for keyword in planner._SLOT_KEYWORDS)


def test_field_review_tu_kham_pha():
    config = field_review_registry.get(_KEY)
    assert set(config["required"]) == {LABEL_THONG_BAO_SO, LABEL_NGAY_BAT_DAU, LABEL_NGAY_KET_THUC}
    assert "receipt_name" in config["noAsk"] and "cccd_tu_van" in config["noAsk"]


def test_extension_khai_ma_tthc_va_moc_tai_khoan():
    portal = _ROOT / "auto-fill-hcc-extension" / "content" / "portal-quangninh.js"
    popup = _ROOT / "auto-fill-hcc-extension" / "popup.js"
    if not portal.exists() or not popup.exists():
        return
    block = portal.read_text(encoding="utf-8").split("NO_FLOW_MA_TTHC = new Set(", 1)[1].split(")", 1)[0]
    assert '"1.004605"' in block
    assert f'cfg.key === "{_KEY}"' in popup.read_text(encoding="utf-8")
