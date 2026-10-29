"""Mapper tests for parent-child recognition process."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.nhan_cha_me_con import process as agent
from app.pipelines.nhan_cha_me_con.process import mapper
from app.pipelines.nhan_cha_me_con.process.prompt import EXTRA_RULES
from app.pipelines.nhan_cha_me_con.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped}


def test_nhan_cha_me_con_registered():
    key = "dang-ky-nhan-cha-me-con"
    proc = get_procedure(key)

    assert proc
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["label"] == "Thủ tục đăng ký nhận cha, mẹ, con"
    assert get_pipeline(key) is agent.run


def test_nhan_cha_me_con_maps_father_recognizes_child():
    fields = [
        _field("Requester_FullName", "Đèo Ngọc Hiếu"),
        _field("Requester_IdNumber", "012098005476"),
        _field("Requester_IdIssueDate", "27/06/2021"),
        _field("Requester_IdIssuePlace", "Cục Cảnh sát QLHC về TTXH"),
        _field(
            "Requester_ResidenceDomestic",
            {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Mường So", "diaChi": "Thôn Tây Sơn"},
        ),
        _field("Requester_RelationshipToRecognized", "Bố"),
        _field("Registration_Type", "Đăng ký mới"),
        _field("Parent_FullName", "Đèo Ngọc Hiếu"),
        _field("Parent_BirthDate", "18/01/1998"),
        _field("Parent_Gender", "Nam"),
        _field("Parent_Ethnicity", "Thái"),
        _field("Parent_Nationality", "Việt Nam"),
        _field("Parent_IdNumber", "012098005476"),
        _field("Parent_IdIssueDate", "27/06/2021"),
        _field("Parent_IdIssuePlace", "CQLHC VTTXH"),
        _field(
            "Parent_ResidenceDomestic",
            "Thôn Tây Sơn, Mường So, Phong Thổ, Lai Châu",
        ),
        _field("Child_FullName", "Vũ My An"),
        _field("Child_BirthDate", "18/12/2025"),
        _field("Child_Gender", "Nữ"),
        _field("Child_Ethnicity", "Kinh"),
        _field("Child_Nationality", "Việt Nam"),
        _field("Child_ResidenceDomestic", "TDP 4, phường Đoàn Kết, tỉnh Lai Châu"),
        _field("Child_BirthDocumentType", "Giấy chứng sinh"),
        _field("Child_BirthDocumentNumber", "02020.GCS.12096.25"),
        _field("Child_BirthDocumentIssueDate", "23/12/2025"),
        _field("Child_BirthDocumentIssuePlace", "Bệnh viện đa khoa tỉnh Lai Châu"),
        _field("CopyRequest_WantsCopy", "Không"),
    ]

    d = _values(mapper.enrich(fields, {}))

    assert d["HoVaTenC"] == "ĐÈO NGỌC HIẾU"
    assert d["SoDinhDanhC"] == "012098005476"
    assert d["LoaiGiayToDinhDanhC"] == "Căn cước công dân"
    assert d["SoGiayToDinhDanhC"] == "012098005476"
    assert d["NgayCapDDC"] == "27/06/2021"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["DiaChiC"] == "Thôn Tây Sơn"
    assert d["TT_TinhThanhC"] == "Tỉnh Lai Châu"
    assert d["TT_PhuongXaC"] == "Xã Phong Thổ"  # Mường So đã sáp nhập
    assert d["Quanhe"] == "Cha"
    assert d["LoaiDangKy"] == "Đăng ký mới"
    assert d["loaiXacNhan"] == "Cha nhận con"

    assert d["HotenA"] == "ĐÈO NGỌC HIẾU"
    assert d["ngaysinhA"] == "18/01/1998"
    assert d["gioitinhA"] == "Nam"
    assert d["sodinhdanhA"] == "012098005476"
    assert d["loaigiaytoA"] == "Căn cước công dân"
    assert d["sogiaytodinhdanhA"] == "012098005476"
    assert d["NoiCapA"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["noicutruA"] == "Trong nước"
    assert d["noicutruA_TrongNuoc"]["diaChi"] == "Thôn Tây Sơn"

    assert d["hotenB"] == "VŨ MY AN"
    assert d["ngaysinhB"] == "18/12/2025"
    assert d["gioitinhB"] == "Nữ"
    assert d["loaigiaytoB"] == "Các loại giấy tờ tùy thân khác"
    assert d["tengiaytoB"] == "Giấy chứng sinh"
    assert "NhaptengiaytoB" not in d
    assert d["sogiaytodinhdanhB"] == "02020.GCS.12096.25"
    assert d["ngaycapB"] == "23/12/2025"
    assert d["noicapB"] == "Bệnh viện đa khoa tỉnh Lai Châu"
    assert d["noicutruB"] == "Trong nước"
    assert d["CapBanSao"] == "Không"
    assert "ThongTin" not in d


def test_nhan_cha_me_con_derives_confirmation_for_child_requester():
    d = _values(
        mapper.enrich(
            [
                _field("Requester_RelationshipToRecognized", "Con"),
                _field("Parent_Gender", "Nữ"),
                _field("Child_FullName", "Nguyễn Văn A"),
            ],
            {},
        )
    )

    assert d["Quanhe"] == "Con"
    assert d["loaiXacNhan"] == "Con nhận mẹ"


def test_nhan_cha_me_con_does_not_fill_defaults_without_source_fields():
    assert mapper.enrich([], {}) == []


def test_nhan_cha_me_con_does_not_emit_thongtin_for_copy_quantity():
    d = _values(
        mapper.enrich(
            [
                _field("Requester_FullName", "Nguyễn Văn A"),
                _field("CopyRequest_WantsCopy", "Có"),
                _field("CopyRequest_Quantity", "2"),
            ],
            {},
        )
    )

    assert d["CapBanSao"] == "Có"
    assert "ThongTin" not in d


def test_nhan_cha_me_con_prompt_locks_confirmation_options():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Cha nhận con" in system_prompt
    assert "Mẹ nhận con" in system_prompt
    assert "Con nhận cha" in system_prompt
    assert "Con nhận mẹ" in system_prompt
    assert "Không lấy các giá trị có sẵn trong HTML tĩnh" in system_prompt


def test_nhan_cha_me_con_bac_ninh_la_thanh_pho_truc_thuoc_tw():
    # eForm chỉ còn option "Thành phố Bắc Ninh": gửi "Tỉnh Bắc Ninh" thì ô tỉnh trượt, ô xã trống theo.
    area = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Phường Võ Cường", "diaChi": "Khu 3"}
    fields = [
        _field("Requester_FullName", "Nguyễn Văn An"),
        _field("Requester_ResidenceDomestic", area),
        _field("Parent_FullName", "Nguyễn Văn An"),
        _field("Parent_ResidenceDomestic", {**area, "tinh": "Tỉnh Bắc Ninh"}),
        _field("Child_FullName", "Nguyễn Văn Bình"),
        _field("Child_ResidenceDomestic", {**area, "tinh": "Thành phố Bắc Ninh"}),
    ]

    d = _values(mapper.enrich(fields, {}))

    assert d["TT_TinhThanhC"] == "Thành phố Bắc Ninh"
    assert d["TT_PhuongXaC"] == "Phường Võ Cường"
    assert d["noicutruA_TrongNuoc"]["tinh"] == "Thành phố Bắc Ninh"
    assert d["noicutruB_TrongNuoc"]["tinh"] == "Thành phố Bắc Ninh"


def test_nhan_cha_me_con_province_label_giu_dung_loai_don_vi():
    assert mapper._province_label("Lai Châu") == "Tỉnh Lai Châu"
    assert mapper._province_label("Tỉnh Lai Châu") == "Tỉnh Lai Châu"
    assert mapper._province_label("TP. Hồ Chí Minh") == "Thành phố Hồ Chí Minh"
    assert mapper._province_label("Hà Nội") == "Thành phố Hà Nội"
    assert mapper._province_label("") == ""
    # Lên TP trực thuộc TW năm 2026: giấy tờ cũ ghi "Tỉnh X" vẫn phải ra option "Thành phố X".
    assert mapper._province_label("Tỉnh Quảng Ninh") == "Thành phố Quảng Ninh"
    assert mapper._province_label("Đồng Nai") == "Thành phố Đồng Nai"
    assert mapper._province_label("Tỉnh Bắc Ninh") == "Thành phố Bắc Ninh"


def test_tinh_xa_viet_tat_ra_nhan_danh_muc():
    from app.pipelines.nhan_cha_me_con.process.mapper import _commune_label, _province_label

    # Danh mục cổng chỉ có tên đầy đủ: viết tắt trượt option, ô xã phía dưới trống theo.
    for raw in ("TP Đà Nẵng", "TP. Đà Nẵng", "T.P Đà Nẵng", "Đà Nẵng"):
        assert _province_label(raw) == "Thành phố Đà Nẵng", raw
    assert _province_label("Lai Châu") == "Tỉnh Lai Châu"
    assert [_commune_label(x) for x in ("P. Hòa Cường", "X.Tân Phong", "TT Tam Đường", "Pa Tần")] == [
        "Phường Hòa Cường", "Xã Tân Phong", "Thị trấn Tam Đường", "Pa Tần"]


def test_giay_khai_sinh_chon_thang_option_va_xa_cu_quy_ve_xa_moi():
    # Danh mục giấy tờ tùy thân của eForm có sẵn "Giấy khai sinh" (không cần ô tên giấy tờ); xã trước
    # sáp nhập ("Xã Hòa Phong", Đà Nẵng) không có trên cổng → phải quy về "Xã Hòa Vang".
    area = {"quocGia": "Việt Nam", "tinh": "Thành phố Đà Nẵng", "xa": "Xã Hòa Phong", "diaChi": "Thôn Một"}
    fields = [
        _field("Requester_FullName", "Trần Văn Bình"),
        _field("Requester_IdNumber", "048090001234"),
        _field("Requester_ResidenceDomestic", area),
        _field("Requester_RelationshipToRecognized", "Cha"),
        _field("Parent_ResidenceDomestic", area),
        _field("Child_FullName", "Trần Thị Cúc"),
        _field("Child_IdNumber", "048322001234"),
        _field("Child_BirthDocumentType", "Giấy khai sinh"),
        _field("Child_BirthDocumentNumber", "12"),
        _field("Child_BirthDocumentIssueDate", "15/12/2022"),
        _field("Child_BirthDocumentIssuePlace", "UBND xã Hòa Liên"),
    ]

    d = _values(mapper.enrich(fields, {}))

    assert d["loaigiaytoB"] == "Giấy khai sinh"
    assert "tengiaytoB" not in d
    assert d["sogiaytodinhdanhB"] == "12"
    assert d["TT_TinhThanhC"] == "Thành phố Đà Nẵng"
    assert d["TT_PhuongXaC"] == "Xã Hòa Vang"
    assert d["DiaChiC"] == "Thôn Một"
    assert d["noicutruA_TrongNuoc"]["xa"] == "Xã Hòa Vang"
