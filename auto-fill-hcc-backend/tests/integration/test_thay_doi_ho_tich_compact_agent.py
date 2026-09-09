"""Mapper/context tất định cho "Thay đổi, cải chính hộ tịch"."""

import asyncio

from app.pipelines.thay_doi_ho_tich.process import mapper, runner
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
    assert out["ntdHoTen"]["value"] == "NGUYỄN DIỆP CHI"
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
    assert out["ntdHoTen"]["value"] == "TRẦN THỊ MẤT"
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
    assert out["ntdHoTen"]["value"] == "LÊ VĂN CHỒNG"
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
    assert out["ntdHoTen"]["value"] == "PHẠM THỊ VỢ"
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


def test_procedure_registered_agent_mode():
    proc = get_procedure("thay-doi-cai-chinh-ho-tich")
    assert proc["mode"] == "agent"
    assert proc["detect"]["urlIncludes"] == ["maThuTuc=1.004859"]
