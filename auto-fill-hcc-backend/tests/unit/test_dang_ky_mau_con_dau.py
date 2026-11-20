"""Đăng ký mẫu con dấu mới (thực hiện tại cấp tỉnh) 2.001428 (Cổng DVC Bộ Công an): mapper ô form + nối registry /
link kê khai + trợ lý người dân."""
from app.pipelines.dang_ky_mau_con_dau.process import mapper
from app.pipelines.dang_ky_mau_con_dau.process.schema import (
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    TRUONG_HOP_OPTIONS,
    UI_COMP_BY_NAME,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "dang-ky-mau-con-dau"
# Hồ sơ mẫu bịa cùng khuôn bộ mẫu: đảng ủy trường học mới thành lập, văn bản đề nghị không ghi số định danh cơ quan,
# người đứng đầu tự đi nộp, không có thẻ căn cước.
HO_SO = {
    "VanBan_KinhGui": "Công an tỉnh Lai Châu",
    "VanBan_TenCoQuanBanHanh": "ĐẢNG UỶ TRƯỜNG PTDTBT THCS AN BÌNH",
    "VanBan_TenToChuc": "Đảng uỷ Trường PTDTBT THCS An Bình;",
    "VanBan_DiaChiToChuc": {"tinh": "tỉnh Lai Châu", "xa": "xã Hồng Thu", "chiTietDuoiXa": "Bản Nậm Mạ Thái"},
    "VanBan_NguoiDungDau_HoTen": "Lê Văn An", "VanBan_NguoiDungDau_NgaySinh": "01/02/1980",
    "VanBan_NguoiDungDau_GioiTinh": "Nam", "VanBan_NguoiDungDau_SoGiayTo": "001080000001",
    "VanBan_NoiDungDeNghi": "Đăng ký mẫu con dấu mới",
    "VanBan_LyDo": "Thành lập Đảng bộ Trường PTDTBT THCS An Bình",
    "VanBan_TaiLieuKemTheo": (
        "- Công văn số 12-CV/BTCTU, ngày 15/9/2026 của Ban Tổ chức Tỉnh uỷ Lai Châu về việc khắc mới con dấu cho các "
        "đảng uỷ trực thuộc;\n"
        "- Quyết định số 34-QĐ/ĐU, ngày 26/8/2026 của Đảng uỷ xã Hồng Thu về việc thành lập Đảng bộ Trường PTDTBT THCS "
        "An Bình."
    ),
    "VanBan_NguoiNop_HoTen": "Lê Văn An", "VanBan_NguoiNop_NgaySinh": "1/2/1980", "VanBan_NguoiNop_GioiTinh": "Nam",
    "VanBan_NguoiNop_SoGiayTo": "0010 8000 0001", "VanBan_NguoiNop_NgayCap": "20/8/2021",
    "VanBan_NguoiNop_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "VanBan_NguoiNop_DienThoai": "0912.345.678",
    "QuyetDinh_So": "34-QĐ/ĐU", "QuyetDinh_Ngay": "26/08/2026", "QuyetDinh_CoQuanBanHanh": "Đảng ủy xã Hồng Thu",
    "QuyetDinh_TrichYeu": "thành lập Đảng bộ Trường PTDTBT THCS An Bình trực thuộc Đảng ủy xã Hồng Thu",
    "CongVan_So": "12-CV/BTCTU", "CongVan_Ngay": "15/09/2026", "CongVan_CoQuanBanHanh": "Ban Tổ chức Tỉnh ủy Lai Châu",
    "CongVan_TrichYeu": "khắc mới con dấu cho các đảng ủy trực thuộc",
}


def _enrich(values: dict, options=None):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_ho_so_mau_dien_du_o_theo_mapping():
    out, warnings = _enrich(HO_SO)
    by = _by(out)
    assert all(f["comp"] == UI_COMP_BY_NAME[f["name"]] for f in out)
    names = [f["name"] for f in out]
    # Loại hình (2) trước Mã định danh (3); Tỉnh (7) trước Xã (8) — script cổng phụ thuộc thứ tự.
    assert names.index("CongDan__fsLoaiHinhToChuc") < names.index("CongDan__fs_BCATenCQDangKy")
    assert names.index("CongDan__fs_BCAQueQuanMaTinh") < names.index("CongDan__fs_BCAQueQuanMaPX")
    assert by["CongDan__fs_BCANoiNopHS"] == "Công an tỉnh Lai Châu"
    assert by["CongDan__fsLoaiHinhToChuc"] == "Cơ quan tổ chức khác" and "CongDan__fs_BCAMaDinhDanh" not in by
    assert by["CongDan__fs_BCATenCQDangKy"] == "Đảng uỷ Trường PTDTBT THCS An Bình"
    assert by["CongDan__fs_BCATruongHop"] == "Tổ chức Đảng"
    assert by["CongDan__fs_BCADiaChiCQDangKy"] == "Bản Nậm Mạ Thái"
    assert by["CongDan__fs_BCAQueQuanMaTinh"] == "Tỉnh Lai Châu" and by["CongDan__fs_BCAQueQuanMaPX"] == "Xã Hồng Thu"
    assert by["CongDan_tenCongDan"] == "Lê Văn An" and by["CongDan_diDong"] == "0912345678"
    assert "CongDan_email" not in by
    assert by["CongDan_soCmnd"] == "001080000001"
    assert by["CongDan__fs_BCANgayCapCMND"] == "20/08/2021"
    assert by["CongDan__fs_BCANoiCapCMND"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["CongDan__fsNgaySinh"] == "01/02/1980" and by["CongDan__fsDangKyDauGioiTinh"] == "Nam"
    assert by["CongDan__fs_BCALoaiHinhConDau"] == "Con dấu của các cơ quan, tổ chức khác."
    assert by["CongDan__fs_BCANoiDungYeuCauGQ"] == (
        "Đăng ký mẫu con dấu mới\nLý do: Thành lập Đảng bộ Trường PTDTBT THCS An Bình"
    )
    assert by["CongDan__fs_BCATenGiayToTaiLieu"] == HO_SO["VanBan_TaiLieuKemTheo"]
    # Ô cổng tự điền / người nộp tự chọn không phát.
    assert not {"CongDan__fs_BCACoSoSanXuat", "CongDan__fs_BCADiaChiCSSanXuat", "CongDan__fsNhanKetQuaBuuChinh",
                "CongDan__fsDiaChiNhanKetQua", "CongDan__fsLePhiBuuChinh"} & set(by)
    joined = " ".join(warnings)
    assert "Cơ quan tổ chức khác" in joined and "Hình thức nhận kết quả" in joined and "Đồng ý và tiếp tục" in joined
    assert "Loại hình con dấu" in joined


def test_co_so_dinh_danh_va_email_co_quan():
    out, warnings = _enrich({**HO_SO, "VanBan_SoDinhDanhToChuc": "G12.34.56.000", "VanBan_EmailToChuc": "abc@xyz.vn"})
    by = _by(out)
    assert by["CongDan__fsLoaiHinhToChuc"] == "Cơ quan tổ chức có mã định danh"
    assert by["CongDan__fs_BCAMaDinhDanh"] == "G12.34.56.000" and by["CongDan_email"] == "abc@xyz.vn"
    assert not any("Cơ quan tổ chức khác" in w for w in warnings)
    # Website không phải email → bỏ.
    out, _ = _enrich({**HO_SO, "VanBan_EmailToChuc": "www.xyz.vn"})
    assert "CongDan_email" not in _by(out)


def test_cccd_cung_nguoi_uu_tien_the_cua_nguoi_khac_bi_bo():
    the = {"Cccd_HoTen": "LÊ VĂN AN", "Cccd_SoDinhDanh": "001080000001", "Cccd_NgaySinh": "01/02/1980",
           "Cccd_GioiTinh": "Nam", "Cccd_NgayCap": "10/03/2025", "Cccd_NoiCap": "BỘ CÔNG AN"}
    van_ban = {k: v for k, v in HO_SO.items() if k not in ("VanBan_NguoiNop_NgayCap",)}
    by = _by(_enrich({**van_ban, **the})[0])
    # Ngày cấp theo thẻ; nơi cấp theo dòng "Nơi cấp" của văn bản (cùng số giấy tờ, mapping ưu tiên đúng nhãn).
    assert by["CongDan__fs_BCANgayCapCMND"] == "10/03/2025"
    assert by["CongDan__fs_BCANoiCapCMND"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["CongDan_tenCongDan"] == "Lê Văn An"
    # Văn bản không ghi nơi cấp → lấy nơi cấp trên thẻ.
    van_ban.pop("VanBan_NguoiNop_NoiCap")
    assert _by(_enrich({**van_ban, **the})[0])["CongDan__fs_BCANoiCapCMND"] == "Bộ Công an"
    # Thẻ của người khác (văn thư) → bỏ cả bộ thẻ, giữ số theo văn bản, có cảnh báo.
    out, warnings = _enrich({**HO_SO, **the, "Cccd_HoTen": "TRẦN THỊ BÌNH", "Cccd_SoDinhDanh": "001190000002"})
    by = _by(out)
    assert by["CongDan_soCmnd"] == "001080000001" and by["CongDan__fs_BCANgayCapCMND"] == "20/08/2021"
    assert any("không phải của người nộp" in w for w in warnings)


def test_khong_co_muc_6_lay_nguoi_dung_dau():
    values = {k: v for k, v in HO_SO.items() if not k.startswith("VanBan_NguoiNop_")}
    out, warnings = _enrich(values)
    by = _by(out)
    assert by["CongDan_tenCongDan"] == "Lê Văn An" and by["CongDan_soCmnd"] == "001080000001"
    assert by["CongDan__fsNgaySinh"] == "01/02/1980" and "CongDan_diDong" not in by
    assert any("Số điện thoại liên hệ" in w for w in warnings)
    # Số điện thoại cơ quan (mục 1) dùng khi mục 6 không có.
    assert _by(_enrich({**values, "VanBan_DienThoaiToChuc": "0213 3876 543"})[0])["CongDan_diDong"] == "02133876543"


def test_danh_sach_tai_lieu_mot_dong_va_dung_tu_quyet_dinh_cong_van():
    one_line = HO_SO["VanBan_TaiLieuKemTheo"].replace(";\n", "; ")
    by = _by(_enrich({**HO_SO, "VanBan_TaiLieuKemTheo": one_line})[0])
    assert by["CongDan__fs_BCATenGiayToTaiLieu"] == HO_SO["VanBan_TaiLieuKemTheo"]
    # Văn bản không có danh sách → dựng từ số / ngày / cơ quan / trích yếu của công văn + quyết định.
    values = {k: v for k, v in HO_SO.items() if k != "VanBan_TaiLieuKemTheo"}
    assert _by(_enrich(values)[0])["CongDan__fs_BCATenGiayToTaiLieu"] == (
        "- Công văn số 12-CV/BTCTU, ngày 15/9/2026 của Ban Tổ chức Tỉnh ủy Lai Châu về việc khắc mới con dấu cho các "
        "đảng ủy trực thuộc;\n"
        "- Quyết định số 34-QĐ/ĐU, ngày 26/8/2026 của Đảng ủy xã Hồng Thu về việc thành lập Đảng bộ Trường PTDTBT THCS "
        "An Bình trực thuộc Đảng ủy xã Hồng Thu."
    )
    # Thiếu dòng nội dung nhưng có lý do → nội dung mặc định của thủ tục.
    values = {k: v for k, v in HO_SO.items() if k != "VanBan_NoiDungDeNghi"}
    assert _by(_enrich(values)[0])["CongDan__fs_BCANoiDungYeuCauGQ"].startswith("Đăng ký mẫu con dấu mới\nLý do: ")


def test_ocr_doc_truong_thanh_truong_va_van_ban_de_nghi_bi_doc_nham_thanh_cong_van():
    # Bộ mẫu thật: OCR dòng tên ở mục 1 ra "Trưởng" (dòng tiêu đề vẫn đúng "Trường").
    by = _by(_enrich({**HO_SO, "VanBan_TenToChuc": "Đảng uỷ Trưởng PTDTBT THCS An Bình"})[0])
    assert by["CongDan__fs_BCATenCQDangKy"] == "Đảng uỷ Trường PTDTBT THCS An Bình"
    assert _by(_enrich({**HO_SO, "VanBan_TenToChuc": "Chi bộ Trưởng Tiểu học An Bình"})[0])[
        "CongDan__fs_BCATenCQDangKy"] == "Chi bộ Trường Tiểu học An Bình"
    # "Trưởng" không đứng trước tên loại trường → giữ nguyên.
    assert _by(_enrich({**HO_SO, "VanBan_TenToChuc": "Văn phòng Trưởng Thôn An Bình"})[0])[
        "CongDan__fs_BCATenCQDangKy"] == "Văn phòng Trưởng Thôn An Bình"
    # Chỉ tải văn bản đề nghị (OCR rơi danh sách tài liệu): LLM đọc chính văn bản đó thành "công văn" → bỏ, không dựng
    # dòng "Công văn số <số văn bản đề nghị> về việc đề nghị đăng ký mẫu con dấu".
    only_request = {k: v for k, v in HO_SO.items()
                    if k.startswith("VanBan_") and k != "VanBan_TaiLieuKemTheo"}
    for letter in ({"CongVan_So": "05-CV/ĐU", "CongVan_TrichYeu": "đề nghị đăng ký mẫu con dấu"},
                   {"CongVan_So": "05-CV/ĐU", "CongVan_TrichYeu": "khắc dấu", "VanBan_So": "05-CV/ĐU"}):
        out, warnings = _enrich({**only_request, **letter, "CongVan_Ngay": "28/10/2026"})
        assert "CongDan__fs_BCATenGiayToTaiLieu" not in _by(out), letter
        assert any("Các giấy tờ tài liệu" in w for w in warnings)
    # Có quyết định thật thì vẫn dựng dòng quyết định.
    qd = {k: v for k, v in HO_SO.items() if k.startswith("QuyetDinh_")}
    by = _by(_enrich({**only_request, **qd, "CongVan_So": "05-CV/ĐU", "VanBan_So": "05-CV/ĐU"})[0])
    assert by["CongDan__fs_BCATenGiayToTaiLieu"].startswith("- Quyết định số 34-QĐ/ĐU, ngày 26/8/2026")
    assert "Công văn" not in by["CongDan__fs_BCATenGiayToTaiLieu"]


def test_loai_hinh_to_chuc_va_con_dau():
    def pick(name, llm=None):
        by = _by(_enrich({**HO_SO, "VanBan_TenToChuc": name, "VanBan_LoaiHinhToChuc": llm})[0])
        return by.get("CongDan__fs_BCATruongHop"), by.get("CongDan__fs_BCALoaiHinhConDau")

    assert pick("Chi bộ Thôn Nà Hừ") == ("Tổ chức Đảng", "Con dấu của các cơ quan, tổ chức khác.")
    assert pick("Tỉnh ủy An Bình") == ("Tổ chức Đảng",
                                       "Con dấu của các Đảng ủy và các cơ quan Đảng trực thuộc Trung ương")
    # "Đăng kiểm" bỏ dấu cũng ra "dang" — không được nhận là tổ chức đảng.
    assert pick("Trung tâm Đăng kiểm xe cơ giới An Bình", "Tổ chức sự nghiệp") == (
        "Tổ chức sự nghiệp", "Con dấu của các cơ quan, tổ chức khác.")
    # Cơ quan nhà nước có thể dùng dấu Quốc huy → không đoán ô (17).
    truong_hop, con_dau = pick("Ủy ban nhân dân xã An Bình", TRUONG_HOP_OPTIONS[1])
    assert truong_hop == TRUONG_HOP_OPTIONS[1] and con_dau is None
    # LLM trả chữ ngoài danh sách → không chọn, cảnh báo chọn tay.
    out, warnings = _enrich({**HO_SO, "VanBan_TenToChuc": "Hội Người cao tuổi xã An Bình",
                             "VanBan_LoaiHinhToChuc": "Hội"})
    assert "CongDan__fs_BCATruongHop" not in _by(out)
    assert any("Loại hình Cơ quan/Tổ chức" in w for w in warnings)


def test_noi_tiep_nhan_va_dia_chi():
    by = _by(_enrich({**HO_SO, "VanBan_KinhGui": "Phòng Cảnh sát QLHC về TTXH, Công an tỉnh Lai Châu"})[0])
    assert by["CongDan__fs_BCANoiNopHS"] == "Công an tỉnh Lai Châu"
    # Không có dòng Kính gửi → suy theo tỉnh của địa chỉ cơ quan (thành phố trực thuộc TW giữ chữ "thành phố").
    values = {k: v for k, v in HO_SO.items() if k != "VanBan_KinhGui"}
    values["VanBan_DiaChiToChuc"] = {"tinh": "Hà Nội", "xa": "Phường Hoàn Kiếm", "chiTietDuoiXa": "Số 1 phố A"}
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCANoiNopHS"] == "Công an thành phố Hà Nội"
    assert by["CongDan__fs_BCAQueQuanMaTinh"] == "Thành phố Hà Nội"
    # Địa chỉ là chuỗi trần không tách được tỉnh/xã → không đổ cả dòng vào ô chi tiết.
    out, warnings = _enrich({**HO_SO, "VanBan_DiaChiToChuc": "Bản A, xã B, tỉnh C"})
    assert "CongDan__fs_BCADiaChiCQDangKy" not in _by(out)
    assert any("Không tách được tỉnh, xã" in w for w in warnings)


def test_schema_registry_link_va_detect():
    assert {"VanBan_TenToChuc", "VanBan_TaiLieuKemTheo", "QuyetDinh_So", "CongVan_So", "Cccd_SoDinhDanh"} <= ALLOWED
    assert COMPACT_COMP_BY_NAME["VanBan_DiaChiToChuc"] == "x-select-area"
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"]
    assert proc["detect"]["textIncludes"] == ["đăng ký mẫu con dấu"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.001428" and link["label"] == proc["label"]
    # Auto Fill: trang DVCQG không chọn tỉnh/xã → "Nộp hồ sơ" → "Nộp trực tuyến" → "Nộp hồ sơ" bên Bộ Công an.
    assert link["needsAgencySelect"] is False and link["directSubmit"] is True and link["bcaSubmit"] is True
    assert link["autoConfirm"] is False
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    # Trang thủ tục cổng Bộ Công an mang ?MaTTHC=2.001428 → khớp mã.
    assert "matthc=2.001428" in public["detect"]["urlIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaConDau": True}


def test_tro_ly_cung_key_detect_hien_moi_tinh_va_mo_thang_trang_chon_truong_hop():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat.router import _clean_client_capabilities

    proc = hf.get_procedure(KEY)
    assert proc["detect"] == registry.get_procedure(KEY)["detect"] and proc["label"] == registry.get_procedure(KEY)["label"]
    assert proc["requiresCapability"] == "supportsBcaConDau" and proc["hasAttachmentStep"] is True
    assert proc["supportsSplitDocuments"] is True and hf.get_attach_pipeline(KEY) is registry.get_attach_pipeline(KEY)
    assert proc["keKhaiUrl"].startswith("https://dichvucong.bocongan.gov.vn/bo-cong-an/tiep-nhan-online/chon-truong-hop")
    step = proc["laiChauFeeStep"]
    assert {k: step[k] for k in ("capability", "caseOnly", "caseGroups")} == {
        "capability": "supportsBcaCaseStep", "caseOnly": True, "caseGroups": "auto"}
    assert "Cơ quan giải quyết hồ sơ" in step["caseHint"] and proc["resultMethodHint"] is True
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    assert "provinceOnly" not in proc
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert _clean_client_capabilities({"supportsBcaConDau": True})["supportsBcaConDau"] is True

    # Bản trợ lý chưa khai cờ: không dẫn vào cổng.
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert "chưa hỗ trợ" in r.display_md and not r.actions
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Xã Hồng Thu"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == proc["keKhaiUrl"]
    # Trang chọn trường hợp: extension báo formKind rỗng → chưa xin giấy tờ.
    flow._handle_guide_login(conv, Intent("event", "page_status", {"loggedIn": True, "formKind": ""}))
    assert conv["state"] == "guide_login"
    # Trang nhập thông tin: form kê khai → xin giấy tờ.
    flow._handle_guide_login(conv, Intent("event", "page_status", {"loggedIn": True, "formKind": "standard"}))
    assert conv["state"] in ("ask_doc_method", "consent")


def test_tro_ly_trang_chon_truong_hop_dan_nhu_trang_1():
    import asyncio

    from app.channels.handfree.chat import lai_chau

    caps = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
    conv = {"_id": "c1", "state": "greet", "procedure_key": None, "client_capabilities": caps,
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Xã Hồng Thu"}}
    flow._to_confirm_procedure(conv, KEY)
    flow._start_guide_login(conv)
    r = asyncio.run(flow._handle_turn_inner(conv, Intent("event", "page_status",
                                                          {"loggedIn": True, "formKind": "", "lcStep": 1})))
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}]}] and conv["state"] == "guide_login"
    # Bản trợ lý chưa có cờ trang chọn trường hợp → giữ luồng cũ (công dân tự chọn).
    from app.channels.handfree import procedure_registry as hf

    assert not lai_chau.enabled({**conv, "client_capabilities": {**CAPS, "supportsLaiChauFeeStep": True}},
                                hf.get_procedure(KEY))


def test_o_nap_cham_mang_wait_ms_va_khong_nhac_dinh_kem():
    out, warnings = _enrich(HO_SO)
    fields = {f["name"]: f for f in out}
    # Bản chạy thật 18/11: hụt Loại hình Cơ quan/Tổ chức + Phường/xã vì danh sách nạp chậm → extension chờ thêm.
    assert fields["CongDan__fs_BCATruongHop"]["waitMs"] == 6000
    assert fields["CongDan__fs_BCAQueQuanMaPX"]["waitMs"] == 8000
    assert "waitMs" not in fields["CongDan__fs_BCAQueQuanMaTinh"] and "waitMs" not in fields["CongDan_tenCongDan"]
    joined = " ".join(warnings)
    assert "Hình thức nhận kết quả" in joined and "Địa chỉ nhận kết quả" in joined and "Thành phần hồ sơ" in joined


def test_tro_ly_dien_xong_nhac_hinh_thuc_nhan_ket_qua_roi_moi_sang_dinh_kem():
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import tracing

    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {},
            "client_capabilities": dict(CAPS)}
    with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 17})))
    # User 20/11/2026: điền xong DỪNG ở rà soát như hộ chiếu / thị thực (askBeforeAttach), không tự đính; câu đuôi vẫn nhắc
    # chọn Hình thức nhận kết quả + địa chỉ, công dân bấm "Đính kèm giấy tờ" mới đính.
    assert conv["state"] == "reviewing" and conv.get("pipeline_status") != "waiting_attachment_page"
    assert "Hình thức nhận kết quả" in r.display_md and "Địa chỉ nhận kết quả" in r.display_md
    assert "tôi tự đính kèm" not in r.display_md and "Đính kèm giấy tờ" in r.display_md
    assert "__action:confirm_review" in [c["send"] for c in r.chips]
    # Không tự đính sau điền: câu đuôi bảo bấm Đính kèm giấy tờ trong Trợ lý, vẫn nhắc nhận kết quả.
    conv = {**conv, "state": "filling", "auto_attach_after_fill": False}
    with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 17})))
    assert conv["state"] == "reviewing" and "Hình thức nhận kết quả" in r.display_md
    assert "__action:confirm_review" in [c["send"] for c in r.chips]


def test_tro_ly_trang_chon_truong_hop_noi_ro_phai_chon_co_quan_giai_quyet():
    import asyncio

    caps = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
    conv = {"_id": "c1", "state": "greet", "procedure_key": None, "client_capabilities": caps,
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Xã Hồng Thu"}}
    flow._to_confirm_procedure(conv, KEY)
    flow._start_guide_login(conv)
    turn = lambda kind, value, payload=None: asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))  # noqa: E731
    r = turn("event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    assert "**Cơ quan giải quyết hồ sơ**" in r.display_md and "Đồng ý và tiếp tục" in r.display_md
    # Không đọc được ô nào (ảnh 18/11) → vẫn nói rõ phải chọn gì.
    r = turn("action", "lc_result_report", {"groups": [], "prepared": []})
    assert "**Cơ quan giải quyết hồ sơ**" in r.display_md and "chưa đọc được" in r.display_md
    # Đọc được ô (cổng tự chọn sẵn khi chỉ có một cơ quan) → thẻ chọn như đăng ký xe.
    group = {"name": "maCoQuan", "present": True, "value": "Công an tỉnh Lai Châu", "options": ["Công an tỉnh Lai Châu"],
             "fixed": False, "label": "Cơ quan giải quyết hồ sơ", "required": True}
    r = turn("action", "lc_result_report", {"groups": [group], "prepared": ["auto:maCoQuan"]})
    assert [row["label"] for row in r.cards[0]["rows"]] == ["Cơ quan giải quyết hồ sơ"]


# ── Đính kèm: trang "Thông tin hồ sơ" (bảng Thành phần hồ sơ 2 dòng + Giấy tờ khác) ──
import asyncio  # noqa: E402
import base64  # noqa: E402
import json  # noqa: E402

from app.pipelines.dang_ky_mau_con_dau.attach import planner as attach_planner  # noqa: E402
from app.pipelines.dang_ky_mau_con_dau.attach.dinh_kem_khong_tach import planner as whole_planner  # noqa: E402
from app.process.schemas import FileItem  # noqa: E402
from app.services import ocr as ocr_service  # noqa: E402
from app.services.llm import client as llm_client  # noqa: E402

DON = ("ĐẢNG BỘ XÃ AN BÌNH\nĐẢNG UỶ TRƯỜNG THCS AN BÌNH\nSố 05-CV/ĐU\nV/v đề nghị đăng ký mẫu con dấu\nKính gửi: Công an "
       "tỉnh An Bình\n1. Cơ quan, tổ chức đề nghị đăng ký mẫu con dấu")
DON_2 = "5. Nội dung đề nghị\n6. Người được giới thiệu/uỷ quyền liên hệ nộp hồ sơ\nHọ và tên: Lê Văn An"
QD = "ĐẢNG ỦY XÃ AN BÌNH\nSố 12-QĐ/ĐU\nQUYẾT ĐỊNH\nthành lập Đảng bộ Trường THCS An Bình"
QD_2 = "Điều 3. Quyết định có hiệu lực\nT/M ĐẢNG ỦY"
QD_DS = "DANH SÁCH\nđảng viên các chi bộ (Kèm theo Quyết định số 12-QĐ/ĐU)"
CV = "TỈNH ỦY AN BÌNH\nBAN TỔ CHỨC\nSố 34-CV/BTCTU\nV/v khắc mới con dấu cho các đảng ủy trực thuộc"
CCCD = "CĂN CƯỚC CÔNG DÂN\nSố: 001080000001\nHọ và tên / Full name:\nLÊ VĂN AN"
CV_NAME = "Công văn số 34-CV/BTCTU, ngày 5/9/2026 của Ban Tổ chức Tỉnh ủy An Bình V/v khắc mới con dấu"


def _file(name: str, size: int = 10) -> FileItem:
    data = base64.b64encode(b"x" * size).decode()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}", role="other")


def _pdf_text(*pages: str) -> str:
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{text}" for i, text in enumerate(pages, 1))


def _mock_io(monkeypatch, texts: dict[str, str], llm):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, **_):
        return llm(messages) if callable(llm) else llm

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", fake_chat)


def _slots(result) -> dict:
    return {a["slotIndex"]: a for a in result["attachments"] if a["target"] == "fixed-slot"}


def _others(result) -> list[dict]:
    return [a for a in result["attachments"] if a["target"] == "new"]


def test_dinh_kem_khong_tach_dung_dong_va_giay_to_khac(monkeypatch):
    files = [_file("QD.pdf"), _file("Don.pdf"), _file("CV.pdf"), _file("cccd.jpg")]
    texts = {"QD.pdf": QD, "Don.pdf": DON, "CV.pdf": CV, "cccd.jpg": CCCD}
    llm = json.dumps({"documents": [
        {"index": 0, "docType": "quyet_dinh_thanh_lap", "documentName": ""},
        {"index": 1, "docType": "van_ban_de_nghi", "documentName": ""},
        {"index": 2, "docType": "van_ban_dong_y", "documentName": CV_NAME},
        {"index": 3, "docType": "identity", "documentName": ""},
    ]})
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {}, {}))  # không bật tách → đính nguyên tệp
    slots = _slots(result)
    assert slots[0]["fileIndex"] == 0 and slots[0]["slotKeywords"] == ["quyet dinh cong nhan to chuc"]
    assert slots[1]["fileIndex"] == 1 and slots[1]["slotKeywords"] == ["giay gioi thieu hoac giay uy quyen"]
    assert all(a["tickRow"] and "sourceSegments" not in a for a in slots.values())
    others = {a["fileIndex"]: a["documentName"] for a in _others(result)}
    assert others == {2: CV_NAME, 3: "Căn cước người nộp - Lê Văn An"}
    assert result["extracted"]["attachmentMode"] == "whole"
    assert not [e for e in result["errors"] if "cần bổ sung" in e]


def test_dinh_kem_giay_gioi_thieu_rieng_vao_dong_2_van_ban_de_nghi_sang_giay_to_khac(monkeypatch):
    files = [_file("Don.pdf"), _file("GT.pdf"), _file("QD.pdf")]
    texts = {"Don.pdf": DON, "GT.pdf": "GIẤY GIỚI THIỆU\nTrân trọng giới thiệu ông Lê Văn An", "QD.pdf": QD}
    _mock_io(monkeypatch, texts, "không phải JSON")  # LLM hỏng → luật theo tiêu đề
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": False}, {}))
    slots = _slots(result)
    assert slots[0]["fileIndex"] == 2 and slots[1]["fileIndex"] == 1
    assert [(a["fileIndex"], a["documentName"]) for a in _others(result)] == [
        (0, "Văn bản đề nghị đăng ký mẫu con dấu")]
    # Thiếu quyết định → cảnh báo bổ sung dòng 1; tệp > 6 MB bị loại kèm cảnh báo.
    files = [_file("Don.pdf"), _file("to.pdf", 7 * 1024 * 1024)]
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    assert [a["fileIndex"] for a in result["attachments"]] == [0]
    assert any("Quyết định công nhận tổ chức" in e for e in result["errors"])
    assert any("vượt giới hạn 6 MB" in e for e in result["errors"])


def test_dinh_kem_tach_dung_dong_khong_sot_trang(monkeypatch):
    # Một PDF gộp: Đơn (2 trang) + Quyết định (2 trang + danh sách kèm theo) + Công văn; CCCD riêng một tệp.
    files = [_file("ho-so.pdf"), _file("cccd.jpg")]
    texts = {"ho-so.pdf": _pdf_text(DON, DON_2, QD, QD_2, QD_DS, CV), "cccd.jpg": CCCD}
    llm = json.dumps({
        "tep": [{"fileIndex": 0, "tieuDeTrang": ["Văn bản đề nghị đăng ký mẫu con dấu", "", "Quyết định thành lập Đảng bộ",
                                                 "", "", CV_NAME]}],
        "documents": [
            {"fileIndex": 0, "pages": [1, 2], "docType": "van_ban_de_nghi", "documentName": "Văn bản đề nghị"},
            {"fileIndex": 0, "pages": [3, 4, 5], "docType": "quyet_dinh_thanh_lap", "documentName": "Quyết định"},
            {"fileIndex": 0, "pages": [6], "docType": "van_ban_dong_y", "documentName": CV_NAME},
            {"fileIndex": 1, "pages": [1], "docType": "identity", "documentName": "Thẻ căn cước"},
        ],
    })
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["extracted"]["attachmentMode"] == "split"
    slots = _slots(result)
    assert slots[0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2, 3, 4]}]
    assert slots[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 1]}]
    others = _others(result)
    assert [(a["documentName"], a.get("sourceSegments")) for a in others] == [
        (CV_NAME, [{"fileIndex": 0, "pageIndexes": [5]}]),
        ("Căn cước người nộp - Lê Văn An", None),
    ]
    # Không sót trang: mọi trang của tệp gộp nằm trong đúng một mục.
    pages = sorted(p for a in result["attachments"] for s in a.get("sourceSegments") or [] if s["fileIndex"] == 0
                   for p in s["pageIndexes"])
    assert pages == list(range(6))


def test_dinh_kem_tach_loi_quay_ve_khong_tach(monkeypatch):
    files = [_file("QD.pdf"), _file("Don.pdf")]
    texts = {"QD.pdf": QD, "Don.pdf": DON}

    def broken(_messages):
        raise RuntimeError("LLM sập")

    _mock_io(monkeypatch, texts, broken)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["errors"][0].startswith("attachment_agent (tách)")
    assert result["extracted"]["attachmentMode"] == "whole"
    slots = _slots(result)
    assert slots[0]["fileIndex"] == 0 and slots[1]["fileIndex"] == 1
    assert not any(a.get("sourceSegments") for a in result["attachments"])
