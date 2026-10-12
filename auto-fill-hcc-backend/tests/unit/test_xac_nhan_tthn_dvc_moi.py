"""Cấp Giấy XNTTHN trên Cổng DVC quốc gia mới: mapper ra câu hỏi SurveyJS + planner đính kèm."""

import re
from pathlib import Path

import pytest

from app.pipelines.xac_nhan_tthn_dvc_moi.attach.dinh_kem_khong_tach import planner
from app.pipelines.xac_nhan_tthn_dvc_moi.process import mapper
from app.pipelines.xac_nhan_tthn_dvc_moi.process.schema import UI_COMP_BY_NAME

SNAPSHOT = Path(__file__).resolve().parents[3] / "html mới" / "tình trạng hôn nhân" / "tình trạng hôn nhân form mới.html"
ACCOUNT = {"applicantFullname": "NGUYEN VAN B", "applicantIdentityNumber": "001090000002"}
BASE = {
    "NguoiDuocCap_HoTen": "Nguyễn Văn B",
    "NguoiDuocCap_NgaySinh": "5/3/1990",
    "NguoiDuocCap_SoDinhDanh": "001090000002",
    "NguoiDuocCap_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 1"},
}


def _context(relation="Bản thân", loai="khac", noi_dung="Bổ sung hồ sơ vay vốn", chac="cao", co_trong_ho_so="Có"):
    return (
        "<phan_vai_da_xac_dinh>\n"
        f"<nguoi_nop>\nCó trong hồ sơ: {co_trong_ho_so}\n</nguoi_nop>\n"
        "<nguoi_duoc_cap>\nHọ tên: NGUYEN VAN B\n</nguoi_duoc_cap>\n"
        f"<quan_he>\nKết luận: {relation}\n</quan_he>\n"
        f"<muc_dich>\nLoại: {loai}\nNội dung: {noi_dung}\nĐộ chắc: {chac}\n</muc_dich>\n"
        "</phan_vai_da_xac_dinh>"
    )


def _enrich(values: dict, context: str = "", account=ACCOUNT):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    out, warnings = mapper.enrich(fields, {"formContext": account, "_reasoning_context": context})
    return {f["name"]: f for f in out}, warnings


def test_ban_than_tra_cuu_dan_cu_va_dia_chi():
    v, warnings = _enrich(BASE, _context())
    assert (v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["code"], warnings) == ("1", [])
    assert v["citizenNDKNgaythangnamsinh"]["code"] == "1990-03-05"
    assert all(v[n].get("lookup") for n in
               ("citizenNDKHochudemtenngdccap", "citizenNDKNgaythangnamsinh", "citizenNDKSoDinhDanh"))
    assert v["citizenNDKnoicutru"]["code"] == "1" and v["citizenNDKLoaicutru"]["default"] is True
    assert "citizenField13" not in v


def test_quan_he_khac_ghi_o_moi_quan_he():
    v, _ = _enrich(BASE, _context(relation="Người được ủy quyền"))
    assert v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["code"] == "2"
    assert v["citizenField13"]["value"] == "Người được ủy quyền"


def test_khong_ket_luan_quan_he_thi_doi_chieu_tai_khoan():
    v, warnings = _enrich(BASE, "")
    assert v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["default"] is True
    v, warnings = _enrich({**BASE, "NguoiDuocCap_HoTen": "Trần Thị C", "NguoiDuocCap_SoDinhDanh": "001190000003",
                           "NguoiDuocCap_NgaySinh": "01/01/1999"}, "")
    assert "citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan" not in v and warnings


def test_ma_tinh_trang_theo_cong_moi():
    # Cổng mới: 1 = chưa đăng ký, 2 = đang có vợ/chồng (ngược eForm cũ).
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "chua_ket_hon"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "1"
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "co_vo_chong", "Marriage_SpouseName": "Trần Thị C",
                    "Marriage_Number": "12", "Marriage_Date": "1/2/2020", "Marriage_Agency": "UBND xã A"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "2"
    assert v["citizenHovatencuavochongnguoicoyeucauxacnhantinhtranghonnhan"]["value"] == "TRẦN THỊ C"
    assert (v["citizenField40"]["value"], v["citizenField41"]["code"]) == ("12", "2020-02-01")


def test_chua_ket_hon_nhung_co_ban_an_thi_ly_hon_theo_van_ban():
    values = {**BASE, "TinhTrangHonNhan": "chua_ket_hon", "DivorceDecision_Number": "5/2011/HNGĐ-ST",
              "DivorceDecision_Date": "15/07/2021", "BanAn_Date": "15/07/2011", "BanAn_Agency": "Tòa án nhân dân A"}
    v, _ = _enrich(values, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "3"
    assert v["citizenSoBananQuyetdinhlyhon"]["value"] == "5/2011/HNGĐ-ST"
    assert (v["citizenField46"]["value"], v["citizenField47"]["value"]) == ("15/07/2011", "Tòa án nhân dân A")


def test_goa_va_khoang_thoi_gian():
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "goa", "DeathCert_Number": "167/TLKT-BS",
                    "DeathCert_Date": "07/11/2024", "DeathCert_Agency": "UBND xã A"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "4" and v["citizenField50"]["code"] == "2024-11-07"
    v, _ = _enrich({**BASE, "Period_TuNgay": "27/04/2016", "Period_DenNgay": "14/09/2016",
                    "Marriage_SpouseName": "Trần Thị C"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "5"
    assert (v["citizenField56"]["code"], v["citizenField57"]["code"]) == ("2016-04-27", "2016-09-14")


def test_muc_dich_khac_va_khong_chac_thi_to_vang():
    v, _ = _enrich(BASE, _context(chac="thap"))
    assert v["citizenField60"]["code"] == "3"
    assert v["citizenField69"]["value"] == "Bổ sung hồ sơ vay vốn" and v["citizenField69"]["default"] is True


def test_muc_dich_ket_hon_nuoc_ngoai_dien_nguoi_du_dinh_ket_hon():
    v, _ = _enrich({**BASE, "KetHonVoi_HoTen": "John Smith", "KetHonVoi_LoaiGiayTo": "Hộ chiếu"},
                   _context(loai="ket_hon_nuoc_ngoai", noi_dung="Để đăng ký kết hôn tại Hoa Kỳ"))
    assert v["citizenField60"]["code"] == "2" and "citizenField69" not in v
    assert v["citizenHochudemtendaiienncngoai"]["value"] == "JOHN SMITH"
    assert v["citizenDaidiengiaytotuythan"]["code"] == "6"


def test_so_dien_thoai_va_so_ban_sao():
    v, _ = _enrich({**BASE, "NguoiNop_SoDienThoai": "0912.345.678"}, _context())
    assert v["citizenPhone"]["value"] == "0912345678"
    assert v["citizenField70"]["value"] == "0" and v["citizenField70"]["default"] is True
    v, _ = _enrich({**BASE, "NguoiNop_SoDienThoai": "0912345678", "SoLuongBanSao": "02"},
                   _context(co_trong_ho_so="Không"))
    assert "citizenPhone" not in v and v["citizenField70"]["value"] == "2"


def test_planner_to_khai_vao_dong_to_khai_con_lai_vao_dong_giay_to():
    items = planner.build_plan_items(["a.pdf", "b.pdf", "c.pdf"],
                                     {0: "declaration", 1: "identity", 2: "la_qua"}, {})
    assert [i["slotIndex"] for i in items] == [2, 1, 1]
    assert [i["detectedType"] for i in items] == ["declaration", "identity", "other"]


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="thiếu snapshot cổng")
def test_static_ui_keys_exist_in_snapshot():
    data_names = set(re.findall(r'data-name="([A-Za-z0-9_]+?)__\d+"', SNAPSHOT.read_text(encoding="utf-8")))
    always = {"citizenPhone", "citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan",
              "citizenNDKHochudemtenngdccap", "citizenNDKNgaythangnamsinh", "citizenNDKSoDinhDanh",
              "citizenNDKLoaicutru", "citizenNDKnoicutru", "citizenNDKTinh_ThTru", "citizenNDKXa_ThTru",
              "citizenNDKDiaChi_ThTru", "citizenTinhtranghonnhan", "citizenField60", "citizenField69", "citizenField70"}
    assert always <= data_names and always <= set(UI_COMP_BY_NAME)


def test_khoang_thoi_gian_ma_khong_co_hon_nhan_hien_tai_thi_chua_ket_hon():
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "khoang_thoi_gian", "Period_TuNgay": "19/06/2000",
                    "Period_DenNgay": "12/10/2024"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "1" and "citizenField56" not in v
