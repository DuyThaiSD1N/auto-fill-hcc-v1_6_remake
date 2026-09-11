"""Mapper tests cho thủ tục "Cấp lại Chứng chỉ hành nghề thú y" (mã 1.005319).

Hồ sơ đi qua HAI bước, mỗi bước là một form Form.io riêng:
  Bước 1 — Phần I "Thông tin người nộp hồ sơ" (cổng tự đổ tài khoản đăng nhập, ta không động vào) và
           Phần II "Thông tin chủ hồ sơ" = người đứng đơn.
  Bước 2 — tờ đơn 03.HNTY, mục "Thông tin chung" cũng là người đứng đơn.
Hai bước dùng CHUNG field-key data[fullname], data[birthday]… nên ô của tờ đơn phải kèm scope.
"""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.cap_lai_CCHN_thu_y import process as agent
from app.pipelines.cap_lai_CCHN_thu_y.attach import plan as attach_plan
from app.pipelines.cap_lai_CCHN_thu_y.process import mapper
from app.pipelines.cap_lai_CCHN_thu_y.process.prompt import EXTRA_RULES
from app.pipelines.cap_lai_CCHN_thu_y.process.schema import (
    DON_SCOPE,
    DON_SCOPE_NEAR,
    FIELDS,
    NGUOI_NOP_MARKERS,
    PHAM_VI_FIELD_KEY,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "cap-lai-chung-chi-hanh-nghe-thu-y"


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped if f["name"] != PHAM_VI_FIELD_KEY}


def _pham_vi_labels(mapped: list[dict]) -> list[str]:
    return [f["optionLabel"] for f in mapped if f["name"] == PHAM_VI_FIELD_KEY]


def _nguoi_de_nghi() -> list[dict]:
    return [
        _field("NguoiDeNghi_HoTen", "TRẦN THỊ BÍCH THUỶ"),
        _field("NguoiDeNghi_NgaySinh", "19/5/1989"),
        _field("NguoiDeNghi_SoDinhDanh", "012345678901"),
        _field("NguoiDeNghi_NgayCapCCCD", "20/5/2012"),
        _field(
            "NguoiDeNghi_ThuongTru",
            {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Xã Tân Uyên", "diaChi": "Tổ 5, khu 2"},
        ),
        _field("NguoiDeNghi_DienThoai", "0974313188"),
    ]


def _don() -> list[dict]:
    return [
        _field("Don_KinhGui", "Chi cục Chăn nuôi và Thú y tỉnh Lai Châu"),
        _field("Don_LaNguoiNuocNgoai", "Không"),
        _field("Don_BangCapChuyenMon", "Bác sĩ thú y"),
        _field("Don_PhamViHanhNghe", "Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn"),
        _field("Don_LyDoCapLai", "Chứng chỉ bị hư hỏng"),
        _field("Don_DiaDiem", "Lai Châu"),
        _field("Don_NgayLamDon", "15/10/2025"),
        _field("Don_NguoiLamDon", "TRẦN THỊ BÍCH THUỶ"),
    ]


def test_cap_lai_cchn_thu_y_registered():
    proc = get_procedure(KEY)

    assert proc
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["label"] == "Cấp lại Chứng chỉ hành nghề thú y"
    assert get_pipeline(KEY) is agent.run
    assert get_attach_pipeline(KEY) is attach_plan


def test_cap_lai_cchn_thu_y_ke_khai_link_nop_tai_so():
    link = next((item for item in KE_KHAI_LINKS if item.get("key") == KEY), None)

    assert link
    assert link["code"] == "1.005319"
    assert link["needsAgencySelect"] is True
    assert link["selectSo"] is True


# Ô nhân thân của Phần I "Thông tin người nộp hồ sơ" — cổng tự đổ tài khoản đăng nhập vào đây. Tờ đơn
# ở bước sau dùng CHUNG field-key với các ô này, nên mọi ô mang tên trùng BẮT BUỘC phải có scope tờ đơn;
# thiếu scope là extension sẽ điền cả sang khối người nộp ở bước trước.
_PHAN_I_NHAN_THAN = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[idIssuePlace]", "data[province]", "data[district]",
    "data[address]", "data[phoneNumber]", "data[email]",
)

# Ô của riêng Phần I: không dùng chung field-key với tờ đơn nên chỉ cần KHÔNG phát ra là an toàn.
_PHAN_I_RIENG = ("data[chonDoiTuong]",)


def _khong_co_o_nao_ro_ri_sang_nguoi_nop(mapped: list[dict]) -> bool:
    if any(field["name"] in _PHAN_I_RIENG for field in mapped):
        return False
    return all(
        field.get("scope") == DON_SCOPE
        and field.get("scopeNear") == DON_SCOPE_NEAR
        and field.get("scopeAway") == list(NGUOI_NOP_MARKERS)
        for field in mapped
        if field["name"] in _PHAN_I_NHAN_THAN
    )


def test_cap_lai_cchn_thu_y_dien_nguoi_de_nghi_vao_khoi_chu_ho_so():
    out, _ = mapper.enrich(_nguoi_de_nghi() + _don(), {})
    d = _values(out)

    assert d["data[kinhGui]"] == "Chi cục Chăn nuôi và Thú y tỉnh Lai Châu"
    # "Đối tượng nộp hồ sơ" thuộc Phần I (thuộc tính tài khoản VNeID) → không đụng vào.
    assert "data[chonDoiTuong]" not in d
    # Bỏ tích thì cổng mới mở khoá khối "Thông tin chủ hồ sơ".
    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[ownerFullname]"] == "TRẦN THỊ BÍCH THUỶ"
    assert d["data[ownerBirthday]"] == "19/05/1989"
    assert d["data[ownerIdentityNumber]"] == "012345678901"
    assert d["data[ownerIdentityDate]"] == "20/05/2012"
    assert d["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert d["data[ownerDistrict]"] == "Xã Tân Uyên"
    assert d["data[ownerAddress]"] == "Tổ 5, khu 2"
    assert d["data[ownerPhoneNumber]"] == "0974313188"
    assert d["data[ownerNation]"] == "Việt Nam"
    assert d["data[bangCapChuyenMon]"] == "Bác sĩ thú y"
    assert d["data[lyDo]"] == "Chứng chỉ bị hư hỏng"
    assert d["data[diaDiem]"] == "Lai Châu"
    assert d["data[thoiGian]"] == "15/10/2025"
    assert d["data[nguoiLD]"] == "TRẦN THỊ BÍCH THUỶ"
    # Người trong hồ sơ TUYỆT ĐỐI không được chảy lên khối người nộp hồ sơ.
    assert _khong_co_o_nao_ro_ri_sang_nguoi_nop(out)


def test_cap_lai_cchn_thu_y_dien_thong_tin_chung_cua_to_don():
    """Mục "Thông tin chung" trong tờ đơn cũng là người đề nghị, và chỉ điền ở đúng bước tờ đơn."""
    out, _ = mapper.enrich(_nguoi_de_nghi() + _don(), {})
    d = _values(out)
    scopes = {f["name"]: f.get("scope") for f in out}

    assert d["data[fullname]"] == "TRẦN THỊ BÍCH THUỶ"
    assert d["data[birthday]"] == "19/05/1989"
    assert d["data[identityNumber]"] == "012345678901"
    assert d["data[identityDate]"] == "20/05/2012"
    assert d["data[province]"] == "Tỉnh Lai Châu"
    assert d["data[district]"] == "Xã Tân Uyên"
    assert d["data[address]"] == "Tổ 5, khu 2"
    assert d["data[phoneNumber]"] == "0974313188"
    # Trùng field-key với Phần I → bắt buộc kèm scope panel tờ đơn.
    assert scopes["data[fullname]"] == DON_SCOPE
    assert scopes["data[province]"] == DON_SCOPE
    # Khối chủ hồ sơ có field-key riêng, không cần scope.
    assert scopes["data[ownerFullname]"] is None
    assert scopes["data[isOwnerDossierCheck]"] is None


def test_cap_lai_cchn_thu_y_o_to_don_mang_moc_chan_khoi_nguoi_nop():
    """Panel tờ đơn có thể bọc cả trang → phải kèm ô neo + mốc khối cấm để extension tự thu hẹp."""
    out, _ = mapper.enrich(_nguoi_de_nghi() + _don(), {})
    fullname = next(f for f in out if f["name"] == "data[fullname]")

    assert fullname["scopeNear"] == DON_SCOPE_NEAR
    assert fullname["scopeAway"] == list(NGUOI_NOP_MARKERS)
    # Ô neo phải là ô CHỈ có trong tờ đơn, không nằm trong danh sách mốc khối cấm.
    assert DON_SCOPE_NEAR not in NGUOI_NOP_MARKERS
    assert DON_SCOPE_NEAR not in _PHAN_I_NHAN_THAN


def test_cap_lai_cchn_thu_y_khong_phat_o_nhan_than_nao_cua_phan_i():
    """Mọi ô phát ra hoặc thuộc Phần II / tờ đơn, hoặc là ô tích mở khoá — không có ô nào của Phần I."""
    out, _ = mapper.enrich(_nguoi_de_nghi() + _don(), {})

    for field in out:
        if field["name"] in _PHAN_I_NHAN_THAN:
            assert field.get("scope") == DON_SCOPE, field["name"]
        assert field["name"] not in _PHAN_I_RIENG, field["name"]


def test_cap_lai_cchn_thu_y_gioi_tinh_va_noi_cap_vao_khoi_chu_ho_so():
    fields = _nguoi_de_nghi() + _don() + [
        _field("NguoiDeNghi_GioiTinh", "Nữ"),
        _field("NguoiDeNghi_NoiCapCCCD", "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"),
    ]

    d = _values(mapper.enrich(fields, {})[0])

    assert d["data[ownerGender]"] == "Nữ"
    assert d["data[ownerIdIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_cap_lai_cchn_thu_y_khong_ghi_de_prefill_cua_tai_khoan_khi_nop_thay():
    """Nộp thay: khối người nộp giữ nguyên tài khoản đăng nhập, người đứng đơn xuống khối chủ hồ sơ."""
    ctx = {"applicantFullname": "Nguyễn Duy Thái", "applicantIdentityNumber": "001204018566"}
    fields = _nguoi_de_nghi() + _don() + [
        _field("NguoiNop_HoTen", "NGUYỄN DUY THÁI"),
        _field("NguoiNop_SoDinhDanh", "001204018566"),
    ]

    out, _ = mapper.enrich(fields, {"formContext": ctx})
    d = _values(out)

    assert d["data[ownerFullname]"] == "TRẦN THỊ BÍCH THUỶ"
    assert d["data[ownerIdentityNumber]"] == "012345678901"
    assert d["data[nguoiLD]"] == "TRẦN THỊ BÍCH THUỶ"
    assert _khong_co_o_nao_ro_ri_sang_nguoi_nop(out)


def test_cap_lai_cchn_thu_y_tich_pham_vi_hanh_nghe():
    out, warnings = mapper.enrich(_nguoi_de_nghi() + _don(), {})

    assert _pham_vi_labels(out) == ["Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn."]
    ticked = [f for f in out if f["name"] == PHAM_VI_FIELD_KEY]
    assert ticked[0]["comp"] == "dom-checkbox"
    assert ticked[0]["value"] is True
    assert not [w for w in warnings if "phạm vi" in w]


def test_cap_lai_cchn_thu_y_tich_nhieu_pham_vi():
    fields = [f for f in _nguoi_de_nghi() + _don() if f["name"] != "Don_PhamViHanhNghe"]
    fields.append(
        _field(
            "Don_PhamViHanhNghe",
            "Buôn bán thuốc thú y dùng trong thú y cho động vật thủy sản.; "
            "Khảo nghiệm thuốc thú y dùng trong thú y cho động vật trên cạn",
        )
    )

    labels = _pham_vi_labels(mapper.enrich(fields, {})[0])

    assert labels == [
        "Buôn bán thuốc thú y dùng trong thú y cho động vật thủy sản.",
        "Khảo nghiệm thuốc thú y dùng trong thú y cho động vật trên cạn.",
    ]


def test_cap_lai_cchn_thu_y_pham_vi_ghi_tat_thi_canh_bao():
    fields = [f for f in _nguoi_de_nghi() + _don() if f["name"] != "Don_PhamViHanhNghe"]
    fields.append(_field("Don_PhamViHanhNghe", "Buôn bán thuốc thú y"))

    out, warnings = mapper.enrich(fields, {})

    # Ghi tắt khớp cả "trên cạn" lẫn "thủy sản" → không đoán, để cán bộ tự tích.
    assert _pham_vi_labels(out) == []
    assert any("Buôn bán thuốc thú y" in w for w in warnings)


def test_cap_lai_cchn_thu_y_khong_co_chung_chi_cu():
    out, _ = mapper.enrich(_nguoi_de_nghi() + _don(), {})
    d = _values(out)

    # Không có chứng chỉ cũ → để trống hai ô đó cho cán bộ nhập tay, không bịa.
    assert "data[soDK]" not in d
    assert "data[ngayCC]" not in d


def test_cap_lai_cchn_thu_y_so_dang_ky_bo_duoi_cchnty():
    fields = _nguoi_de_nghi() + _don() + [
        _field("CCHNCu_SoDangKy", "123/CCHN-TY"),
        _field("CCHNCu_NgayHetHan", "31/12/2026"),
    ]

    d = _values(mapper.enrich(fields, {})[0])

    # Ô trên form đã in sẵn đuôi "-CCHNTY" → chỉ điền phần số đứng trước.
    assert d["data[soDK]"] == "123"
    assert d["data[ngayCC]"] == "31/12/2026"


def test_cap_lai_cchn_thu_y_thieu_so_dinh_danh_thi_canh_bao():
    fields = [f for f in _nguoi_de_nghi() if f["name"] != "NguoiDeNghi_SoDinhDanh"]

    out, warnings = mapper.enrich(fields + _don(), {})

    assert "data[ownerIdentityNumber]" not in _values(out)
    assert any("căn cước" in w for w in warnings)


def test_cap_lai_cchn_thu_y_nguoi_nuoc_ngoai_thi_tick():
    fields = [f for f in _nguoi_de_nghi() + _don() if f["name"] != "Don_LaNguoiNuocNgoai"]
    fields.append(_field("Don_LaNguoiNuocNgoai", "Có"))

    d = _values(mapper.enrich(fields, {})[0])

    assert d["data[toiLaNguoiNuocNgoai]"] is True


def test_cap_lai_cchn_thu_y_dia_diem_bo_tien_to_cap_hanh_chinh():
    fields = [f for f in _nguoi_de_nghi() + _don() if f["name"] != "Don_DiaDiem"]

    d = _values(mapper.enrich(fields, {})[0])

    # Không có địa danh trong đơn → lấy tỉnh thường trú nhưng ghi trần, không kèm "Tỉnh".
    assert d["data[diaDiem]"] == "Lai Châu"


def test_cap_lai_cchn_thu_y_remap_xa_sau_sap_nhap():
    fields = [f for f in _nguoi_de_nghi() if f["name"] != "NguoiDeNghi_ThuongTru"]
    fields.append(
        _field(
            "NguoiDeNghi_ThuongTru",
            {"quocGia": "Việt Nam", "tinh": "Bình Thuận", "xa": "Hàm Kiệm", "diaChi": "Tổ 3"},
        )
    )

    d = _values(mapper.enrich(fields + _don(), {})[0])

    # Xã/tỉnh cũ phải quy đổi theo đợt sáp nhập, nếu không select không có option để chọn.
    assert d["data[ownerProvince]"] == "Tỉnh Lâm Đồng"
    assert d["data[ownerDistrict]"] == "Xã Hàm Kiệm"


def test_cap_lai_cchn_thu_y_tinh_thanh_pho_truc_thuoc_tw():
    fields = [f for f in _nguoi_de_nghi() if f["name"] != "NguoiDeNghi_ThuongTru"]
    fields.append(
        _field(
            "NguoiDeNghi_ThuongTru",
            {"quocGia": "Việt Nam", "tinh": "T.P Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "12 Bạch Đằng"},
        )
    )

    d = _values(mapper.enrich(fields + _don(), {})[0])

    # Tiền tố OCR trả kèm ("T.P") phải bị bóc trước khi gắn nhãn, tránh "Tỉnh T.P Đà Nẵng".
    assert d["data[ownerProvince]"] == "Thành phố Đà Nẵng"


def test_cap_lai_cchn_thu_y_prompt_locks_sources():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*)" in system_prompt
    assert "KHÔNG trả field UI dạng data[...]" in system_prompt
    assert "Don_PhamViHanhNghe" in system_prompt
    assert "CCHNCu_NgayHetHan" in system_prompt
