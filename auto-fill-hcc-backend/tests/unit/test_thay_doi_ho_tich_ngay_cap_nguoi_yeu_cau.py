"""Mục I "Thay đổi, cải chính, bổ sung hộ tịch, xác định lại dân tộc": ngày/cơ quan cấp giấy tờ.

declaration.py đã đọc NguoiYeuCau_NgayCap/NoiCap từ tờ khai và DanhSachCccd luôn có ngày cấp,
nhưng mapper không phát ra ô UI nào nên hai ô "Ngày cấp"/"Cơ quan cấp" của người yêu cầu luôn
trống trên form.
"""

from app.pipelines.thay_doi_ho_tich.process import mapper


def _fields(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _by_name(out: list[dict]) -> dict:
    return {f["name"]: f for f in out}


def test_ngay_cap_nguoi_yeu_cau_uu_tien_to_khai():
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "LƯƠNG ĐỨC THẮNG",
        "NguoiYeuCau_SoDinhDanh": "012091000079",
        "NguoiYeuCau_NgayCap": "25/03/2021",
        "NguoiYeuCau_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
        "ChuThe_HoTen": "LƯƠNG ĐỨC THẮNG",
        "ChuThe_SoDinhDanh": "012091000079",
    })))
    assert out["NgayCapDDC"]["value"] == "25/03/2021"
    assert out["NgayCapDDC"]["comp"] == "x-date"
    assert out["NoiCapDDC"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_ban_than_lay_ngay_cap_tren_the_cccd_khi_to_khai_khong_ghi():
    """Quan hệ "Bản thân": thẻ của người có nội dung thay đổi CHÍNH LÀ thẻ người yêu cầu."""
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "LƯƠNG ĐỨC THẮNG",
        "ChuThe_HoTen": "LƯƠNG ĐỨC THẮNG",
        "ChuThe_SoDinhDanh": "012091000079",
        "DanhSachCccd": [{
            "HoTen": "LƯƠNG ĐỨC THẮNG",
            "SoDinhDanh": "012091000079",
            "NgayCap": "25/03/2021",
            "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        }],
    })))
    assert out["SoDinhDanhC"]["value"] == "012091000079"
    assert out["NgayCapDDC"]["value"] == "25/03/2021"
    assert out["NoiCapDDC"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_co_quan_cap_suy_theo_ngay_cap_khi_the_khong_doc_duoc_noi_cap():
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "LƯƠNG ĐỨC THẮNG",
        "Cccd_HoTen": "LƯƠNG ĐỨC THẮNG",
        "Cccd_SoDinhDanh": "012091000079",
        "Cccd_NgayCap": "12/08/2024",
        "ChuThe_HoTen": "LƯƠNG ĐỨC THẮNG",
        "ChuThe_SoDinhDanh": "012091000079",
    })))
    assert out["NgayCapDDC"]["value"] == "12/08/2024"
    # Thẻ Căn cước cấp từ 01/7/2024 do Bộ Công an cấp.
    assert out["NoiCapDDC"]["value"] == "Bộ Công an"


def test_khong_lay_ngay_cap_cua_the_nguoi_khac():
    """Quan hệ "Khác": thẻ của người được cải chính KHÔNG phải thẻ người yêu cầu."""
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "LƯƠNG ĐỨC THẮNG",
        "NguoiYeuCau_SoDinhDanh": "012091000079",
        "ChuThe_HoTen": "LƯƠNG THỊ HOA",
        "ChuThe_SoDinhDanh": "049143000144",
        "DanhSachCccd": [{
            "HoTen": "LƯƠNG THỊ HOA",
            "SoDinhDanh": "049143000144",
            "NgayCap": "10/04/2021",
            "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        }],
    })))
    assert out["nycQuanHe"]["value"] == "Khác"
    assert "NgayCapDDC" not in out
    assert "NoiCapDDC" not in out


def test_alias_ten_field_duoc_gui_kem():
    """Form legacy đổi tên ô giữa các phiên bản → extension cần danh sách alias để dò tiếp."""
    out = _by_name(mapper.enrich(_fields({
        "NguoiYeuCau_HoTen": "LƯƠNG ĐỨC THẮNG",
        "NguoiYeuCau_SoDinhDanh": "012091000079",
        "NguoiYeuCau_NgayCap": "25/03/2021",
        "ChuThe_HoTen": "LƯƠNG ĐỨC THẮNG",
        "ChuThe_SoDinhDanh": "012091000079",
    })))
    assert "NgayCapGiayToTuyThanC" in out["NgayCapDDC"]["aliases"]
    assert "NoiCapGiayToTuyThanC" in out["NoiCapDDC"]["aliases"]
    assert "LoaiGiayToDinhDanhC" in out["LoaiGiayToTuyThanC"]["aliases"]
    assert "SoGiayToDinhDanhC" in out["SoGiayToTuyThanC"]["aliases"]
