"""Mapper/context tất định cho "Thay đổi, cải chính hộ tịch"."""

import asyncio

from app.pipelines.thay_doi_ho_tich.process import declaration, mapper, runner
from app.pipelines.thay_doi_ho_tich.process.prompt import EXTRA_RULES
from app.pipelines.thay_doi_ho_tich.process.schema import COMPACT_COMP_BY_NAME
from app.procedures.registry import get_procedure


def _fields(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _by_name(out: list[dict]) -> dict:
    return {f["name"]: f for f in out}


def test_defaults_yellow_always_present():
    out = _by_name(mapper.enrich(_fields({})))
    for name, value in (
        ("nycLoaiCuTru", "Thường trú"),
        ("nycNoiCuTru", "Trong Nước"),
        ("TraKQ", "Trực tiếp"),
    ):
        assert out[name]["value"] == value
        assert out[name]["default"] is True
    assert out["nycNoiCuTru_TrongNuoc"]["value"] == {"quocGia": "Việt Nam"}
    assert out["nycNoiCuTru_TrongNuoc"]["default"] is True
    assert "CapBanSao" not in out
    assert "SoLuong" not in out


def test_birth_subject_is_child_no_identity_doc_block():
    out = _by_name(mapper.enrich(_fields({
        "LoaiSuKien": "birth",
        "TenGiayTo": "Giấy khai sinh",
        "ChuThe_HoTen": "Nguyễn Diệp Chi",
        "ChuThe_NgaySinh": "30/07/2021",
        "ChuThe_GioiTinh": "Nữ",
        "ChuThe_DanToc": "Kinh",
        "ChuThe_SoDinhDanh": "012321003442",
        "HoSo_So": "123",
        "HoSo_QuyenSo": "01/2020",
        "HoSo_NgayDangKy": "12/02/2020",
        "HoSo_NoiDangKy": "UBND xã Tam Hợp",
    })))
    assert out["ntdHoTen"]["value"] == "Nguyễn Diệp Chi"
    assert out["ntdNgaySinh"]["value"] == "30/07/2021"
    assert out["ntdGioiTinh"]["value"] == "Nữ"
    assert out["ntdSoDDCN"]["value"] == "012321003442"
    assert out["nghiepVuDK"]["value"] == "Hồ sơ khai sinh"
    assert out["soDangKyHSGoc"]["value"] == "123"
    assert out["noiDangKyHSGoc"]["value"] == "UBND xã Tam Hợp"
    # Con KHÔNG có CCCD → khối giấy tờ tùy thân phải BỎ TRỐNG.
    for f in ("ntdLoaiGiayToTuyThan", "ntdSoGiayToTuyThan", "ntdNgayCapGiayToTuyThan", "ntdNoiCapGiayToTuyThan"):
        assert f not in out
    # default-yellow KHÔNG dính vào field lấy từ giấy tờ.
    assert "default" not in out["ntdHoTen"]


def test_correction_declaration_residence_overrides_matching_cccd():
    out = _by_name(mapper.enrich(_fields({
        "LoaiSuKien": "birth",
        "ViecDangKy": "Cải chính",
        "ChuThe_HoTen": "TRẦN LÊ BẢO TRÂM",
        "ChuThe_NgaySinh": "07/07/1989",
        "ChuThe_SoDinhDanh": "068189005332",
        "ChuThe_NoiCuTru": {
            "quocGia": "Việt Nam",
            "tinh": "Lâm Đồng",
            "xa": "Phường Xuân Trường",
            "diaChi": "Tổ Tự Tạo",
        },
        "DanhSachCccd": [{
            "HoTen": "TRẦN LÊ BẢO TRÂM",
            "SoDinhDanh": "068189005332",
            "NgaySinh": "07/07/1989",
            "NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "Phường 11",
                "diaChi": "Tổ 16, Khu Phố 2",
            },
        }],
    })))

    assert out["ntdNoiCuTru_TrongNuoc"]["value"] == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Xuân Trường",
        "diaChi": "Tổ Tự Tạo",
    }


def test_matching_cccd_residence_used_without_correction_declaration():
    out = _by_name(mapper.enrich(_fields({
        "LoaiSuKien": "birth",
        "ChuThe_HoTen": "NGƯỜI CÓ CCCD",
        "ChuThe_NgaySinh": "01/01/1990",
        "ChuThe_NoiCuTru": {
            "quocGia": "Việt Nam",
            "tinh": "Tỉnh cũ",
            "xa": "Xã cũ",
            "diaChi": "Địa chỉ cũ",
        },
        "DanhSachCccd": [{
            "HoTen": "NGƯỜI CÓ CCCD",
            "SoDinhDanh": "012345678901",
            "NgaySinh": "01/01/1990",
            "NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh mới",
                "xa": "Phường mới",
                "diaChi": "Địa chỉ mới",
            },
        }],
    })))

    assert out["ntdNoiCuTru_TrongNuoc"]["value"] == {
        "quocGia": "Việt Nam",
        "tinh": "Tỉnh mới",
        "xa": "mới",
        "diaChi": "Địa chỉ mới",
    }


def test_requester_id_card_number_filled_from_form_context():
    out = _by_name(mapper.enrich(
        _fields({"LoaiSuKien": "birth", "ChuThe_HoTen": "Bé A"}),
        options={"formContext": {"applicantIdentityNumber": "040203015844"}},
    ))
    assert out["SoGiayToTuyThanC"]["value"] == "040203015844"
    assert "default" not in out["SoGiayToTuyThanC"]


def test_quyen_so_not_computed_from_registration_number():
    out = _by_name(mapper.enrich(_fields({
        "LoaiSuKien": "birth", "ChuThe_HoTen": "Bé A",
        "HoSo_So": "119", "HoSo_NgayDangKy": "05/03/2026",
    })))
    assert "quyenDangKyHSGoc" not in out


def test_quyen_so_not_computed_when_number_contains_year():
    a = _by_name(mapper.enrich(_fields({"LoaiSuKien": "birth", "ChuThe_HoTen": "X", "HoSo_So": "201/2026"})))
    b = _by_name(mapper.enrich(_fields({"LoaiSuKien": "birth", "ChuThe_HoTen": "X", "HoSo_So": "400/2025"})))
    assert "quyenDangKyHSGoc" not in a
    assert "quyenDangKyHSGoc" not in b


def test_quyen_so_real_value_not_yellow():
    out = _by_name(mapper.enrich(_fields({
        "LoaiSuKien": "birth", "ChuThe_HoTen": "X",
        "HoSo_So": "119", "HoSo_QuyenSo": "05/2026",
    })))
    assert out["quyenDangKyHSGoc"]["value"] == "05/2026"
    assert "default" not in out["quyenDangKyHSGoc"]


def test_death_subject_is_deceased():
    out = _by_name(mapper.enrich(_fields({
        "LoaiSuKien": "death",
        "TenGiayTo": "Trích lục khai tử",
        "ChuThe_HoTen": "Trần Thị Mất",
        "ChuThe_GioiTinh": "Nữ",
        "ChuThe_SoDinhDanh": "040180000999",
        "HoSo_So": "55",
    })))
    assert out["ntdHoTen"]["value"] == "Trần Thị Mất"
    assert out["ntdSoDDCN"]["value"] == "040180000999"
    assert out["ntdLoaiGiayToTuyThan"]["value"] == "Căn cước công dân"
    assert out["nghiepVuDK"]["value"] == "Hồ sơ khai tử"


def test_marriage_cccd_matches_husband():
    base = {
        "LoaiSuKien": "marriage",
        "TenGiayTo": "Trích lục kết hôn",
        "Chong_HoTen": "Lê Văn Chồng",
        "Chong_SoDinhDanh": "040190000111",
        "Chong_DanToc": "Mông",
        "Vo_HoTen": "Phạm Thị Vợ",
        "Vo_SoDinhDanh": "040190000222",
        "Vo_DanToc": "H'Mông",
    }
    # CCCD trùng số chồng → người thay đổi là chồng.
    out = _by_name(mapper.enrich(_fields({**base, "Cccd_SoDinhDanh": "040190000111", "Cccd_HoTen": "Lê Văn Chồng"})))
    assert out["ntdHoTen"]["value"] == "Lê Văn Chồng"
    assert out["ntdDanToc"]["value"] == "Mông"
    assert out["nghiepVuDK"]["value"] == "Hồ sơ kết hôn"


def test_marriage_requester_cccd_matches_wife():
    base = {
        "LoaiSuKien": "marriage",
        "Chong_HoTen": "Lê Văn Chồng",
        "Chong_SoDinhDanh": "040190000111",
        "Vo_HoTen": "Phạm Thị Vợ",
        "Vo_SoDinhDanh": "040190000222",
        "Vo_DanToc": "H'Mông",
    }
    out = _by_name(mapper.enrich(_fields({**base, "Cccd_SoDinhDanh": "040190000222", "Cccd_HoTen": "Phạm Thị Vợ"})))
    assert out["ntdHoTen"]["value"] == "Phạm Thị Vợ"
    # "H'Mông" → option "Mông (Hmông)"; KHÔNG lấy dân tộc chồng.
    assert out["ntdDanToc"]["value"] == "Mông (Hmông)"


def test_marriage_third_party_requester_uses_only_enriched_wife_cccd():
    """Người nộp là con; CCCD thứ hai khớp vợ thì Mục II phải lấy đủ CCCD của vợ."""
    out = _by_name(mapper.enrich(
        _fields({
            "LoaiSuKien": "marriage",
            "Cccd_HoTen": "BÙI ĐỨC TÂN",
            "Cccd_SoDinhDanh": "068089002701",
            "Cccd_NgayCap": "01/04/2023",
            "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "DanhSachCccd": [
                {
                    "HoTen": "BÙI ĐỨC TÂN",
                    "SoDinhDanh": "068089002701",
                    "NgaySinh": "11/10/1989",
                    "GioiTinh": "Nam",
                    "QuocTich": "Việt Nam",
                    "NgayCap": "01/04/2023",
                    "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
                    "NoiCuTru": {
                        "quocGia": "Việt Nam",
                        "tinh": "Lâm Đồng",
                        "xa": "Phường 8",
                        "diaChi": "105A/7 Đông Tĩnh",
                    },
                },
                {
                    "HoTen": "HUỲNH THỊ LŨY",
                    "SoDinhDanh": "051159001356",
                    "NgaySinh": "10/09/1959",
                    "GioiTinh": "Nữ",
                    "QuocTich": "Việt Nam",
                    "NgayCap": "19/04/2021",
                    "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
                    "NoiCuTru": {
                        "quocGia": "Việt Nam",
                        "tinh": "Lâm Đồng",
                        "xa": "Phường 8",
                        "diaChi": "105A/7 Đông Tĩnh",
                    },
                },
            ],
            "Chong_HoTen": "BÙI ĐỒNG",
            "Chong_NgaySinh": "20/10/1953",
            "Vo_HoTen": "HUỲNH-THỊ-LŨY",
            "Vo_NgaySinh": "10/09/1959",
            "Vo_GioiTinh": "Nữ",
            "Vo_QuocTich": "Việt Nam",
            "Vo_SoDinhDanh": "051159001356",
            "Vo_NgayCapGiayTo": "19/04/2021",
            "Vo_NoiCapGiayTo": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Vo_NoiCuTru": {
                "quocGia": "Việt Nam",
                "tinh": "Lâm Đồng",
                "xa": "Đà Lạt",
                "diaChi": "44 Nguyễn Công Trứ, khóm Đa Hòa",
            },
        }),
        options={"formContext": {
            "applicantFullname": "BÙI ĐỨC TÂN",
            "applicantIdentityNumber": "068089002701",
        }},
    ))

    assert out["ntdHoTen"]["value"] == "HUỲNH THỊ LŨY"
    assert out["ntdNgaySinh"]["value"] == "10/09/1959"
    assert out["ntdGioiTinh"]["value"] == "Nữ"
    assert out["ntdSoDDCN"]["value"] == "051159001356"
    assert out["ntdSoGiayToTuyThan"]["value"] == "051159001356"
    assert out["ntdNgayCapGiayToTuyThan"]["value"] == "19/04/2021"
    assert out["ntdNoiCapGiayToTuyThan"]["value"] == (
        "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    )
    assert out["ntdNoiCuTru_TrongNuoc"]["value"] == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "8",
        "diaChi": "105A/7 Đông Tĩnh",
    }


def test_marriage_unrelated_requester_without_subject_cccd_stays_blank():
    """Không suy diễn 'không khớp chồng thì là vợ' khi CCCD chỉ thuộc người nộp."""
    out = _by_name(mapper.enrich(_fields({
        "LoaiSuKien": "marriage",
        "Cccd_HoTen": "NGƯỜI NỘP KHÁC",
        "Cccd_SoDinhDanh": "068089002701",
        "Chong_HoTen": "BÙI ĐỒNG",
        "Chong_NgaySinh": "20/10/1953",
        "Vo_HoTen": "HUỲNH-THỊ-LŨY",
        "Vo_NgaySinh": "10/09/1959",
    })))

    assert "ntdHoTen" not in out
    assert "ntdSoDDCN" not in out


def test_identity_context_separates_requester_and_other_cccd():
    context = asyncio.run(runner._identity_context(
        [
            {
                "name": "CCCD bản thân.pdf",
                "text": (
                    "CĂN CƯỚC CÔNG DÂN\nSố: 068089002701\n"
                    "Họ và tên: BÙI ĐỨC TÂN\nNgày sinh: 11/10/1989"
                ),
            },
            {
                "name": "CCCD mẹ.pdf",
                "text": (
                    "CĂN CƯỚC CÔNG DÂN\nSố: 051159001356\n"
                    "Họ và tên: HUỲNH THỊ LŨY\nNgày sinh: 10/09/1959"
                ),
            },
            {
                "name": "ĐKKH.pdf",
                "text": "GIẤY CHỨNG NHẬN TẠM THAY HÔN THÚ",
            },
        ],
        {"formContext": {
            "applicantFullname": "BÙI ĐỨC TÂN",
            "applicantIdentityNumber": "068089002701",
        }},
    ))

    assert "Tài liệu CCCD/CMND đã upload: 1, 2" in context
    assert "một object riêng trong DanhSachCccd" in context
    assert "CCCD khớp người yêu cầu trên UI: 1" in context
    assert "CCCD khác người yêu cầu: 2" in context


def test_prompt_recognizes_old_hon_thu_and_requires_all_cccd():
    from app.pipelines.thay_doi_ho_tich.attach.prompt import SYSTEM_PROMPT
    from app.pipelines.thay_doi_ho_tich.process.prompt import EXTRA_RULES

    assert '"GIẤY CHỨNG NHẬN TẠM THAY HÔN THÚ"' in EXTRA_RULES
    assert "tuyệt đối KHÔNG lấy CCCD/CMND làm" in EXTRA_RULES
    assert "DanhSachCccd là bảng nguồn độc lập và BẮT BUỘC" in EXTRA_RULES
    assert "GIẤY CHỨNG NHẬN TẠM THAY HÔN THÚ" in SYSTEM_PROMPT


# Tờ khai thật (hồ sơ Quách Mẫn Trung xin cải chính hộ tịch CHO MẸ là Nguyễn Thị Thân), kèm
# GIẤY KHAI SINH của chính người yêu cầu làm giấy tờ chứng minh — agent hay lấy nhầm chủ thể
# sang người của giấy khai sinh đó.
TO_KHAI_CAI_CHINH_CHO_ME = """Họ, chữ đệm, tên người yêu cầu: QUÁCH MAN TRUNG
Ngày, tháng, năm sinh: 04-05-1971
Nơi cư trú: (2) K48/33 Phan Châu Trinh TP ĐÀ NẴNG
Giấy tờ tùy thân: (3) 048071007708
Ngày cấp 10-08-2021 Nơi cấp CCS QLHC về trật tự xã hội
Quan hệ với người được thay đổi, cải chính, xác định lại dân tộc, bổ sung thông tin hộ tịch:
Con
Đề nghị cơ quan đăng ký việc (4) Cải Chính hộ tịch
cho người có tên dưới đây:
Họ, chữ đệm, tên: NGUYỄN THỊ THÂN
Ngày, tháng, năm sinh: 02-02-1943
Giới tính: (2) Nữ Dân tộc: (2) Quốc tịch: (2) Việt Nam
Nơi cư trú: (2) K48/33 Phan Châu Trinh TP ĐÀ NẴNG
Giấy tờ tùy thân: (3) 049143000144
Ngày cấp 31-03-2021 Nơi cấp CCS QLHC về trật tự xã hội
Đã đăng ký (5) Khai sinh
tại Ủy Ban Nhân Dân Phường Hải Châu I
ngày 07 tháng 04 năm 1989 số: 114 Quyền số:
Nội dung: (6) Cải chính năm sinh của mẹ
Lý do: Sai sót khi đăng ký
"""


def test_declaration_subject_block_read_deterministically():
    assert declaration.subject_fields(TO_KHAI_CAI_CHINH_CHO_ME) == {
        "ChuThe_HoTen": "NGUYỄN THỊ THÂN",
        "ChuThe_NgaySinh": "02/02/1943",
        "ChuThe_GioiTinh": "Nữ",
        "ChuThe_QuocTich": "Việt Nam",
        "ChuThe_SoDinhDanh": "049143000144",
        "ChuThe_NgayCapGiayTo": "31/03/2021",
        "ChuThe_NoiCapGiayTo": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    }
    # Không có tờ khai → không suy diễn chủ thể.
    assert declaration.subject_fields("GIẤY KHAI SINH\nHọ và tên: QUÁCH MAN TRUNG") == {}


def test_declaration_subject_replaces_agent_subject_from_attached_paper():
    """Agent lấy chủ thể từ GIẤY KHAI SINH nộp kèm → phải bị khối tờ khai thay TOÀN BỘ."""
    fields = declaration.fill_missing(
        _fields({
            # Chủ thể agent trích nhầm: chính người yêu cầu (chủ giấy khai sinh nộp kèm).
            "ChuThe_HoTen": "QUÁCH MAN TRUNG",
            "ChuThe_NgaySinh": "04/05/1971",
            "ChuThe_GioiTinh": "Nam",
            "ChuThe_DanToc": "Hán",
            "ChuThe_SoDinhDanh": "048071007708",
            "ChuThe_SoGiayTo": "201245776",
        }),
        TO_KHAI_CAI_CHINH_CHO_ME,
        COMPACT_COMP_BY_NAME,
    )
    values = {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}
    assert values["ChuThe_HoTen"] == "NGUYỄN THỊ THÂN"
    assert values["ChuThe_SoDinhDanh"] == "049143000144"
    assert values["ChuThe_NgaySinh"] == "02/02/1943"
    assert values["ChuThe_GioiTinh"] == "Nữ"
    # Dữ kiện của người bị lấy nhầm phải biến mất hoàn toàn, kể cả ô tờ khai để trống.
    assert "ChuThe_DanToc" not in values
    assert "ChuThe_SoGiayTo" not in values


def test_declaration_subject_only_fills_gaps_when_same_person():
    """Cùng một người thì tôn trọng giá trị agent, chỉ bù ô còn thiếu."""
    fields = declaration.fill_missing(
        _fields({
            "ChuThe_HoTen": "NGUYỄN THỊ THÂN",
            "ChuThe_SoDinhDanh": "049143000144",
            "ChuThe_DanToc": "Kinh",
        }),
        TO_KHAI_CAI_CHINH_CHO_ME,
        COMPACT_COMP_BY_NAME,
    )
    values = {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}
    assert values["ChuThe_DanToc"] == "Kinh"
    assert values["ChuThe_NgayCapGiayTo"] == "31/03/2021"


def test_subject_from_declaration_flows_into_muc_ii_and_relationship():
    """Toàn tuyến: tờ khai chốt Mục II, CCCD của đúng chủ thể được hợp nhất, quan hệ = Khác."""
    fields = declaration.fill_missing(
        _fields({
            "LoaiSuKien": "birth",
            "ViecDangKy": "Cải chính",
            "NguoiYeuCau_HoTen": "QUÁCH MAN TRUNG",
            "NguoiYeuCau_SoDinhDanh": "048071007708",
            "NguoiYeuCau_QuanHe": "Khác",
            "ChuThe_HoTen": "QUÁCH MAN TRUNG",
            "ChuThe_DanToc": "Hán",
            "ChuThe_SoDinhDanh": "048071007708",
            "DanhSachCccd": [
                {"HoTen": "NGUYỄN THỊ THÂN", "SoDinhDanh": "049143000144", "NgaySinh": "02/02/1943",
                 "GioiTinh": "Nữ", "NgayCap": "31/03/2021"},
                {"HoTen": "QUÁCH MẪN TRUNG", "SoDinhDanh": "048071007708", "NgaySinh": "04/05/1971",
                 "GioiTinh": "Nam", "NgayCap": "10/08/2021"},
            ],
        }),
        TO_KHAI_CAI_CHINH_CHO_ME,
        COMPACT_COMP_BY_NAME,
    )
    out = _by_name(mapper.enrich(fields))
    assert out["ntdHoTen"]["value"] == "NGUYỄN THỊ THÂN"
    assert out["ntdSoDDCN"]["value"] == "049143000144"
    assert out["ntdNgaySinh"]["value"] == "02/02/1943"
    # Dân tộc của người bị lấy nhầm KHÔNG được rơi sang chủ thể thật.
    assert "ntdDanToc" not in out
    assert out["nycQuanHe"]["value"] == "Khác"
    assert out["SoDinhDanhC"]["value"] == "048071007708"


def test_same_identity_number_forces_ban_than_over_declaration_checkbox():
    """Người yêu cầu và Mục II CÙNG số định danh → "Bản thân", dù LLM đọc ô tích ra "Khác"."""
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "QUÁCH MAN TRUNG",
        "NguoiYeuCau_SoDinhDanh": "048071007708",
        "NguoiYeuCau_QuanHe": "Khác",
        "ChuThe_HoTen": "QUÁCH MAN TRUNG",
        "ChuThe_NgaySinh": "04/05/1971",
        "ChuThe_SoDinhDanh": "048071007708",
    })))
    assert out["nycQuanHe"]["value"] == "Bản thân"
    assert "default" not in out["nycQuanHe"]


def test_different_identity_number_forces_khac_over_declaration_checkbox():
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "QUÁCH MAN TRUNG",
        "NguoiYeuCau_SoDinhDanh": "048071007708",
        "NguoiYeuCau_QuanHe": "Bản thân",
        "ChuThe_HoTen": "NGUYỄN THỊ THÂN",
        "ChuThe_SoDinhDanh": "049143000144",
    })))
    assert out["nycQuanHe"]["value"] == "Khác"


def test_declaration_checkbox_used_when_identity_number_missing():
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "TRẦN VĂN A",
        "NguoiYeuCau_QuanHe": "Bản thân",
        "ChuThe_HoTen": "TRẦN VĂN B",
    })))
    assert out["nycQuanHe"]["value"] == "Bản thân"
    assert "default" not in out["nycQuanHe"]


def test_ban_than_requester_id_prefers_cccd_card_over_declaration():
    """Bản thân: ô (2) lấy số trên THẺ CCCD; tờ khai chép CMND cũ chỉ là fallback."""
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "QUÁCH MẪN TRUNG",
        "NguoiYeuCau_SoDinhDanh": "201245776",
        "ChuThe_HoTen": "QUÁCH MẪN TRUNG",
        "ChuThe_NgaySinh": "04/05/1971",
        "DanhSachCccd": [{
            "HoTen": "QUÁCH MẪN TRUNG",
            "SoDinhDanh": "048071007708",
            "NgaySinh": "04/05/1971",
            "NgayCap": "10/08/2021",
        }],
    })))
    assert out["nycQuanHe"]["value"] == "Bản thân"
    assert out["SoDinhDanhC"]["value"] == "048071007708"
    assert out["SoGiayToTuyThanC"]["value"] == "048071007708"
    assert out["__requesterInfo"]["value"]["soDinhDanh"] == "048071007708"
    # Các ô còn lại của Mục I vẫn ưu tiên tờ khai.
    assert out["HoVaTenC"]["value"] == "QUÁCH MẪN TRUNG"


def test_khac_requester_id_still_prefers_declaration():
    """Quan hệ "Khác": ô (2) giữ nguyên thứ tự ưu tiên cũ — tờ khai trước CCCD."""
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "QUÁCH MẪN TRUNG",
        "NguoiYeuCau_SoDinhDanh": "201245776",
        "ChuThe_HoTen": "NGUYỄN THỊ THÂN",
        "ChuThe_SoDinhDanh": "049143000144",
        "DanhSachCccd": [{
            "HoTen": "QUÁCH MẪN TRUNG",
            "SoDinhDanh": "048071007708",
            "NgaySinh": "04/05/1971",
        }],
    })))
    assert out["nycQuanHe"]["value"] == "Khác"
    assert out["SoDinhDanhC"]["value"] == "201245776"


def test_relationship_placed_before_muc_ii_fields():
    """Cổng chỉ nhận input Mục II sau khi chọn quan hệ → nycQuanHe phải đứng trước ntd*."""
    out = mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "QUÁCH MAN TRUNG",
        "NguoiYeuCau_SoDinhDanh": "048071007708",
        "ChuThe_HoTen": "NGUYỄN THỊ THÂN",
        "ChuThe_SoDinhDanh": "049143000144",
    }))
    names = [f["name"] for f in out]
    assert names.index("nycQuanHe") < names.index("ntdHoTen")
    assert names.index("SoDinhDanhC") < names.index("nycQuanHe")


def test_prompt_makes_declaration_win_over_attached_birth_certificate():
    assert "<source_priority>" in EXTRA_RULES
    assert "CHỈ ÁP DỤNG KHI KHÔNG CÓ TỜ KHAI" in EXTRA_RULES


def test_procedure_registered_agent_mode():
    proc = get_procedure("thay-doi-cai-chinh-ho-tich")
    assert proc["mode"] == "agent"
    assert proc["detect"]["urlIncludes"] == ["maThuTuc=1.004859"]
