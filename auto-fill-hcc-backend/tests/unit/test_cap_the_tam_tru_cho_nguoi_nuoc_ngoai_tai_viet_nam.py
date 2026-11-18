"""Cấp thẻ tạm trú cho người nước ngoài tại Việt Nam 1.003460 (Cổng DVC Bộ Công an): mapper ô form + Ghi chú + đính kèm
+ nối registry / link kê khai + trợ lý người dân."""
import asyncio
import base64
import json

from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.attach import planner as attach_planner
from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.attach.dinh_kem_khong_tach import (
    planner as whole_planner,
)
from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.process import mapper, runner
from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.schema import (
    ALLOWED,
    COMPACT_COMP_BY_NAME,
)
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process import mapper as thi_thuc
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.services import ocr as ocr_service
from app.services.llm import client as llm_client

KEY = "cap-the-tam-tru-cho-nguoi-nuoc-ngoai-tai-viet-nam"


def _mrz(number: str, nation: str, dob: str, sex: str, expiry: str, surname: str, given: str) -> str:
    """Hai dòng MRZ TD3 đúng chữ số kiểm tra cho hộ chiếu bịa."""
    num = number.ljust(9, "<")
    line2 = (f"{num}{thi_thuc._check_digit(num)}{nation}{dob}{thi_thuc._check_digit(dob)}{sex}{expiry}"
             f"{thi_thuc._check_digit(expiry)}").ljust(42, "<") + "00"
    line1 = f"P<{nation}{surname}<<{given.replace(' ', '<')}".ljust(44, "<")
    return f"{line1}\n{line2}"


MRZ = _mrz("M12345678", "KOR", "850204", "M", "340312", "KIM", "MIN SU")
# Hồ sơ mẫu bịa cùng khuôn bộ mẫu: chuyên gia người Hàn Quốc, công ty Việt Nam bảo lãnh (NA6), có giấy phép lao động.
HO_SO = {
    "ToKhai_HoTen": "KIM MIN SU", "ToKhai_GioiTinh": "Nam", "ToKhai_NgaySinh": "04/02/1985",
    "ToKhai_QuocTichGoc": "Hàn Quốc", "ToKhai_QuocTichHienNay": "Hàn Quốc", "ToKhai_NgheNghiep": "Chuyên gia kỹ thuật",
    "ToKhai_SoHoChieu": "M12345678", "ToKhai_LoaiHoChieu": "Phổ thông",
    "ToKhai_HoChieu_CoQuanCap": "MINISTRY OF FOREIGN AFFAIRS", "ToKhai_HoChieu_DenNgay": "12/03/2034",
    "ToKhai_DiaChiCuTruNuocNgoai": "12, Teheran-ro, Gangnam-gu, Seoul, Republic of Korea",
    "ToKhai_NoiLamViecNuocNgoai": "Sao Mai Co., Ltd., Busan, Republic of Korea",
    "ToKhai_NgayNhapCanh": "20/10/2026", "ToKhai_CuaKhau": "Cửa khẩu Sân bay quốc tế Nội Bài",
    "ToKhai_MucDichNhapCanh": "Làm việc tại Công ty TNHH Sao Mai Lai Châu (thị thực LĐ2)", "ToKhai_TamTruDen": "18/01/2027",
    "ToKhai_DiaChiTamTru": {"tinh": "tỉnh Lai Châu", "xa": "xã Tân Uyên", "chiTietDuoiXa": "Khu nhà ở chuyên gia, bản Nà Ơ"},
    "ToKhai_DienThoai": "+84 912 000 222", "ToKhai_Email": "kim.minsu@example.com", "ToKhai_The_DenNgay": "30/09/2028",
    "ToKhai_LyDo": "Lao động – làm việc theo Giấy phép lao động số LC-26-0999 (kèm theo)",
    "VanBan_Loai": "NA6", "VanBan_BenBaoLanh": "CÔNG TY TNHH SAO MAI LAI CHÂU (1)", "VanBan_So": "12/CV-SM",
    "VanBan_Ngay": "13/11/2026",
    "VanBan_DiaChi": {"tinh": "tỉnh Lai Châu", "xa": "xã Tân Uyên", "chiTietDuoiXa": "Khu chế biến chè bản Nà Ơ"},
    "VanBan_DienThoai": "0213 3786 000", "VanBan_ViTriCongViec": "Chuyên gia kỹ thuật",
    "HoChieu_So": "M12345678", "HoChieu_MRZ": MRZ, "HoChieu_Ho": "KIM", "HoChieu_Ten": "MIN SU",
    "HoChieu_QuocTich": "REPUBLIC OF KOREA", "HoChieu_MaQuocGia": "KOR", "HoChieu_Loai": "P",
    "HoChieu_NgaySinh": "04/02/1985", "HoChieu_GioiTinh": "M", "HoChieu_NgayHetHan": "12/03/2034",
    "HoChieu_CoQuanCap": "MINISTRY OF FOREIGN AFFAIRS", "HoChieu_ThiThuc_KyHieu": "LĐ2",
    "HoChieu_NhapCanh_Ngay": "20/10/2026", "HoChieu_NhapCanh_CuaKhau": "Cửa khẩu Sân bay quốc tế Nội Bài",
    "HoChieu_TamTruDen": "18/01/2027",
    "GPLD_So": "LC-26-0999", "GPLD_CoQuanCap": "Sở Nội vụ tỉnh Lai Châu", "GPLD_NgayCap": "28/09/2026",
    "GPLD_HoTen": "KIM MIN SU", "GPLD_SoHoChieu": "M12345678", "GPLD_ChucDanh": "Chuyên gia kỹ thuật chế biến",
    "GPLD_TuNgay": "01/10/2026", "GPLD_DenNgay": "30/09/2028",
    "Bia_KyHieuThe": "LĐ2 – lao động thuộc diện phải có giấy phép lao động", "Bia_MaSoDoanhNghiep": "6200000000",
}
TRINH_BAY = ("Đề nghị cấp thẻ tạm trú ký hiệu LĐ2 theo Văn bản đề nghị số 12/CV-SM ngày 13/11/2026 của CÔNG TY TNHH SAO MAI "
             "LAI CHÂU (mã số doanh nghiệp 6200000000); Giấy phép lao động số LC-26-0999 do Sở Nội vụ tỉnh Lai Châu cấp "
             "ngày 28/09/2026, thời hạn từ 01/10/2026 đến 30/09/2028.")


def _enrich(values: dict, **kw):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {}, **kw)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_dien_dung_mapping_bo_mau():
    out, warnings = _enrich(HO_SO, ghi_chu="Hồ sơ gồm 01 file PDF (6 trang): ho-so.pdf. Tr.1: Danh mục thành phần hồ sơ.")
    assert _by(out) == {
        "CongDan_tenCongDan": "KIM MIN SU",
        "CongDan__fs_BCAGioiTinhCd": "Nam",
        "CongDan_ngaySinhCongDan": "04/02/1985",
        "CongDan__fs_BCAQuocTichGoc": "Republic of Korea",   # tên danh mục cổng (mapping), không chọn nhầm Triều Tiên
        "CongDan__fs_BCAQuocTichHienNay": "Republic of Korea",
        "CongDan__fs_BCANgheNghiep": "Chuyên gia kỹ thuật",   # NA8 thắng chức danh GPLĐ
        "CongDan__fs_BCASoHoChieu": "M12345678",
        "CongDan__fs_BCALoaiHoChieu": "Hộ chiếu phổ thông",
        "CongDan__fs_BCACoQuanCap": "MINISTRY OF FOREIGN AFFAIRS",
        "CongDan__fs_BCAHoChieuDenNgay": "12/03/2034",
        "CongDan__fsDCCUTRU_NUOCNGOAI": "12, Teheran-ro, Gangnam-gu, Seoul, Republic of Korea",
        "CongDan__fsDCLAMVIEC_NUOCNGOAI": "Sao Mai Co., Ltd., Busan, Republic of Korea",
        "CongDan__fs_BCANgayNhapCanh": "20/10/2026",
        "CongDan__fs_BCAQuaCuaKhau": "SBQT Nội Bài",
        "CongDan__fs_BCAMucDichNhapCanh": "lao động",         # ký hiệu LĐ2 (mapping: đề xuất "lao động")
        "CongDan__fs_BCATamTruDen": "18/01/2027",
        "CongDan__fs_BCATinhTamTru": "Tỉnh Lai Châu",
        "CongDan__fs_BCAXaTamTru": "Xã Tân Uyên",
        "CongDan__fs_BCADiaChiTamTru": "Khu nhà ở chuyên gia, bản Nà Ơ",
        "CongDan_diDong": "0912000222",
        "CongDan_email": "kim.minsu@example.com",
        "CongDan__fs_BCAQuanHeNguoiDeNghi": "Người sử dụng lao động – CÔNG TY TNHH SAO MAI LAI CHÂU",
        "CongDan__fs_BCATinhThuongTru": "Tỉnh Lai Châu",       # không có căn cước → trụ sở trên văn bản NA6
        "CongDan__fs_BCAXaThuongTru": "Xã Tân Uyên",
        "CongDan__fs_BCADiaChiThuongTruVNBaoLanh": "Khu chế biến chè bản Nà Ơ",
        "CongDan__fs_BCADiDongBaoLanh": "02133786000",
        "CongDan__fs_BCAGiaHanTamTruDenNgay": "30/09/2028",
        "CongDan__fs_BCALyDoDeNghiCapThiThuc": "Lao động – làm việc theo Giấy phép lao động số LC-26-0999 (kèm theo)",
        "CongDan__fs_BCADieuCanTrinhBayThem": TRINH_BAY,
        "HoSoOnline_ghiChu": "Hồ sơ gồm 01 file PDF (6 trang): ho-so.pdf. Tr.1: Danh mục thành phần hồ sơ.",
    }
    fields = {f["name"]: f for f in out}
    assert fields["CongDan__fs_BCAXaTamTru"]["waitMs"] == 8000 and fields["CongDan__fs_BCAXaThuongTru"]["waitMs"] == 8000
    for locked in ("CongDan__fs_BCAThanNhanBaoLanh", "CongDan__fs_BCANgaySinhBaoLanh", "CongDan_soCmnd",
                   "CongDan__fsBCACoQuanBaoLanh", "CongDan__fs_BCANoiNopHS", "CongDan__fs_BCANoiNhanHoChieu",
                   "HoSoOnline_veViec"):
        assert locked not in fields
    joined = " ".join(warnings)
    assert "form khoá \"Thân nhân\"" in joined and "không có thẻ căn cước" in joined
    assert "Email liên hệ (bên bảo lãnh)" in joined and "Ảnh chân dung" in joined


def test_ben_bao_lanh_co_can_cuoc_va_bao_lanh_ca_nhan_na7():
    values = {**HO_SO, "Cccd_HoTen": "Trần Văn Bình", "Cccd_SoDinhDanh": "012190000002", "Cccd_NgayCap": "01/07/2025",
              "Cccd_NoiCap": "BỘ CÔNG AN",
              "Cccd_NoiCuTru": {"tinh": "Tỉnh Lai Châu", "xa": "Phường Đoàn Kết", "chiTietDuoiXa": "Tổ dân phố số 3"}}
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCANgayCapCMNDBaoLanh"] == "01/07/2025" and by["CongDan__fs_BCACoQuanCapCMNDBaoLanh"] == "Bộ Công an"
    assert by["CongDan__fs_BCAXaThuongTru"] == "Phường Đoàn Kết"  # căn cước của người đăng nhập thắng trụ sở NA6
    # NA7 (cá nhân bảo lãnh): quan hệ theo văn bản, không gán "người sử dụng lao động".
    values = {**HO_SO, "VanBan_Loai": "NA7", "VanBan_BenBaoLanh": "LÊ THỊ HOA", "VanBan_QuanHe": "Vợ"}
    out, warnings = _enrich(values)
    assert _by(out)["CongDan__fs_BCAQuanHeNguoiDeNghi"] == "Vợ"
    assert not any("form khoá" in w for w in warnings)


def test_ky_hieu_muc_dich_va_ngay_the():
    assert mapper._visa_symbol(("LĐ2",)) == "LĐ2" and mapper._purpose_by_symbol("LĐ2") == "lao động"
    assert mapper._purpose_by_symbol("DN1") == "làm việc" and mapper._purpose_by_symbol("TT") == "thăm thân"
    # Câu tự do: chỉ nhận ký hiệu sau "thị thực" / "ký hiệu" — "DU LỊCH" đầu câu không phải ký hiệu.
    assert mapper._visa_symbol((), ("Du lịch",)) is None
    assert mapper._visa_symbol((), ("Làm việc tại công ty (thị thực DN1)",)) == "DN1"
    values = {k: v for k, v in HO_SO.items() if k not in ("HoChieu_ThiThuc_KyHieu", "Bia_KyHieuThe")}
    by = _by(_enrich({**values, "ToKhai_MucDichNhapCanh": "Du lịch"})[0])
    assert by["CongDan__fs_BCAMucDichNhapCanh"] == "du lịch"
    # Tờ khai không ghi ngày đề nghị → theo thời hạn GPLĐ; ghi vượt GPLĐ → cảnh báo.
    values = {k: v for k, v in HO_SO.items() if k != "ToKhai_The_DenNgay"}
    out, warnings = _enrich(values)
    assert _by(out)["CongDan__fs_BCAGiaHanTamTruDenNgay"] == "30/09/2028"
    assert any("theo thời hạn giấy phép lao động" in w for w in warnings)
    _, warnings = _enrich({**HO_SO, "ToKhai_The_DenNgay": "30/09/2029"})
    assert any("vượt thời hạn giấy phép lao động" in w for w in warnings)


def test_giay_nguoi_khac_bi_bo():
    other_passport = {**HO_SO, "HoChieu_Ho": "LEE", "HoChieu_Ten": "SO YEON", "HoChieu_So": "M99999999",
                      "HoChieu_MRZ": _mrz("M99999999", "KOR", "900101", "F", "300101", "LEE", "SO YEON")}
    out, warnings = _enrich(other_passport)
    by = _by(out)
    assert by["CongDan__fs_BCASoHoChieu"] == "M12345678" and by["CongDan__fs_BCANgayNhapCanh"] == "20/10/2026"
    assert any("Hộ chiếu tải lên không phải của người đề nghị" in w for w in warnings)
    other_permit = {**HO_SO, "GPLD_HoTen": "LEE SO YEON", "GPLD_SoHoChieu": "M99999999"}
    out, warnings = _enrich(other_permit)
    assert "LC-26-0999" not in _by(out)["CongDan__fs_BCADieuCanTrinhBayThem"]
    assert any("Giấy phép lao động tải lên không phải của người đề nghị" in w for w in warnings)


# ── Ghi chú: trang nào của tệp hồ sơ gộp là giấy gì (ảnh ánh xạ mục 6) ──
BIA = ("HỒ SƠ THỦ TỤC HÀNH CHÍNH\nCẤP THẺ TẠM TRÚ CHO NGƯỜI NƯỚC NGOÀI TẠI VIỆT NAM\nDANH MỤC THÀNH PHẦN HỒ SƠ\n"
       "1 Văn bản đề nghị cấp thẻ tạm trú (Mẫu NA6)\n2 Tờ khai đề nghị cấp thẻ tạm trú (Mẫu NA8)\n4 Giấy phép lao động")
VAN_BAN = ("Mẫu (Form) NA6\nCÔNG TY TNHH SAO MAI LAI CHÂU(1)\nSố: 12/CV-SM\nV/v đề nghị cấp thẻ tạm trú cho người nước "
           "ngoài\nĐề nghị quý cơ quan xem xét cấp thẻ tạm trú\nKIM MIN SU Hộ chiếu số M12345678\n(Tờ khai đề nghị cấp thẻ "
           "tạm trú kèm theo)")
TO_KHAI = ("Mẫu (Form) NA8\nTỜ KHAI ĐỀ NGHỊ CẤP THẺ TẠM TRÚ\nINFORMATION FORM FOR A TEMPORARY RESIDENT CARD\n1. Họ tên: KIM "
           "MIN SU\n7. Hộ chiếu số: M12345678 Passport Number")
TO_KHAI_2 = ("Người đề nghị The applicant\nKIM MIN SU\nGhi chú/Notes: (1) Mỗi người khai 01 bản kèm hộ chiếu. Submit in "
             "person one completed application form enclosed with passport and the sponsoring application")
HO_CHIEU = ("REPUBLIC OF KOREA\nPASSPORT\nType P\nPassport No. M12345678\n" + MRZ
            + "\nTHỊ THỰC VIỆT NAM / VIET NAM VISA\nKý hiệu / Type LĐ2\nVIỆT NAM – NHẬP CẢNH / ARRIVAL")
GPLD = ("SỞ NỘI VỤ\nGIẤY PHÉP LAO ĐỘNG\nWORK PERMIT\nSố / No.: LC-26-0999\n1. Họ và tên: KIM MIN SU\n5. Số hộ chiếu / "
        "Passport No.: M12345678")
CAN_CUOC = "CĂN CƯỚC\nIDENTITY CARD\nSố định danh cá nhân: 012190000002\nTRẦN VĂN BÌNH"


def _pdf_text(*pages: str) -> str:
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{text}" for i, text in enumerate(pages, 1))


def test_ghi_chu_trang_cua_tep_ho_so_gop():
    text = _pdf_text(BIA, VAN_BAN, TO_KHAI, TO_KHAI_2, HO_CHIEU, GPLD)
    # Trang ghi chú của tờ khai có chữ "passport" vẫn thuộc tờ khai.
    assert whole_planner.page_types(text) == ["bia_ho_so", "van_ban", "to_khai", "to_khai", "ho_chieu", "chung_minh"]
    note = runner.ghi_chu(f"===== ho-so.pdf (tiengnoi) =====\n{text}", ["ho-so.pdf"],
                          {"VanBan_Loai": "NA6", "VanBan_So": "12/CV-SM", "GPLD_So": "LC-26-0999"})
    assert note == ("Hồ sơ gồm 01 file PDF (6 trang): ho-so.pdf. Tr.1: Danh mục thành phần hồ sơ; Tr.2: Văn bản đề nghị "
                    "NA6 số 12/CV-SM; Tr.3–4: Tờ khai NA8; Tr.5: Hộ chiếu (nhân thân, thị thực, dấu nhập cảnh); Tr.6: "
                    "Giấy phép lao động số LC-26-0999.")
    # Mỗi tệp một giấy → không cần ghi chú.
    many = "\n\n---\n\n".join(f"===== {n} =====\n{t}" for n, t in (("tk.pdf", TO_KHAI), ("hc.jpg", HO_CHIEU)))
    assert runner.ghi_chu(many, ["tk.pdf", "hc.jpg"], {}) is None


def test_schema_registry_link_va_detect():
    assert {"ToKhai_DiaChiCuTruNuocNgoai", "ToKhai_The_DenNgay", "VanBan_BenBaoLanh", "GPLD_So", "Bia_KyHieuThe"} <= ALLOWED
    assert COMPACT_COMP_BY_NAME["ToKhai_DiaChiTamTru"] == "x-select-area"
    assert COMPACT_COMP_BY_NAME["GPLD_DenNgay"] == "x-date"
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"]
    # Trang thẻ tạm trú có thể mang cả chữ của thị thực / hộ chiếu → cụm của thủ tục này phải dài nhất.
    for other in ("cap-thi-thuc-cho-nguoi-nuoc-ngoai-tai-viet-nam", "cap-ho-chieu-pho-thong-o-trong-nuoc"):
        assert sum(map(len, proc["detect"]["textIncludes"])) > \
            sum(map(len, registry.get_procedure(other)["detect"]["textIncludes"])), other
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.003460" and link["label"] == proc["label"]
    assert link["needsAgencySelect"] is False and link["directSubmit"] is True and link["bcaSubmit"] is True
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert "matthc=1.003460" in public["detect"]["urlIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaThiThuc": True}


def test_tro_ly_cung_key_nop_thang_nhu_auto_fill():
    from app.channels.handfree import procedure_registry as hf

    proc = hf.get_procedure(KEY)
    assert proc["detect"] == registry.get_procedure(KEY)["detect"] and proc["label"] == registry.get_procedure(KEY)["label"]
    assert proc["requiresCapability"] == "supportsBcaThiThuc" and proc["agencyDirectSubmit"] is True
    assert proc["bcaTthcCode"] == "1.003460" and proc["keKhaiUrl"] == next(
        item["url"] for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert proc["supportsSplitDocuments"] is True and hf.get_attach_pipeline(KEY) is registry.get_attach_pipeline(KEY)
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY) and "provinceOnly" not in proc
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug

    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Xã Tân Uyên"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert "**Nộp hồ sơ** → **Nộp trực tuyến**" in r.display_md and r.actions[0]["url"] == proc["keKhaiUrl"]
    page = lambda payload: flow._handle_guide_login(conv, Intent("event", "page_status", payload))  # noqa: E731
    assert page({"loggedIn": True, "agencyBlock": True}).actions == [
        {"type": "select_agency", "direct": True, "province": "", "ward": ""}]
    assert page({"loggedIn": True, "bcaTthcPage": True, "bcaTthcCode": "1.003460"}).actions == [
        {"type": "bca_tthc_submit", "code": "1.003460"}]


# ── Đính kèm: 3 dòng + "Giấy tờ khác" hộ chiếu ──
ROW1 = ["chung minh thuoc dien xem xet cap the tam tru"]
ROW2 = ["to khai de nghi cap the tam tru"]
ROW3 = ["van ban de nghi cap the tam tru"]
PASSPORT_ITEM = "Hộ chiếu của KIM MIN SU (trang nhân thân, trang thị thực, dấu kiểm chứng nhập cảnh)"


def _file(name: str, size: int = 10) -> FileItem:
    data = base64.b64encode(b"x" * size).decode()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}", role="other")


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


def test_dinh_kem_khong_tach_mot_tep_gop_dinh_ca_ba_dong_va_giay_to_khac(monkeypatch):
    # Ảnh ánh xạ: cả bộ trong MỘT PDF → nguyên tệp vào dòng 1, 2, 3 và "Giấy tờ khác" hộ chiếu. LLM chỉ thấy 4000 ký tự
    # đầu (bìa + văn bản) nên trả van_ban — tiêu đề từng trang vẫn đưa tệp về loại gộp.
    files = [_file("ho-so.pdf")]
    texts = {"ho-so.pdf": _pdf_text(BIA, VAN_BAN, TO_KHAI, TO_KHAI_2, HO_CHIEU, GPLD)}
    _mock_io(monkeypatch, texts, json.dumps({"documents": [{"index": 0, "docType": "van_ban", "documentName": ""}]}))
    result = asyncio.run(attach_planner.plan(files, {}, {}))
    assert result["extracted"]["attachmentMode"] == "whole"
    assert result["extracted"]["classified"] == [{"fileName": "ho-so.pdf", "docType": "ho_so_gop"}]
    slots = _slots(result)
    assert list(slots) == [0, 1, 2]
    assert [slots[i]["slotKeywords"] for i in (0, 1, 2)] == [ROW1, ROW2, ROW3]
    assert all(slots[i]["fileIndex"] == 0 and slots[i]["tickRow"] is True for i in (0, 1, 2))
    others = _others(result)
    assert [(o["fileIndex"], o["componentName"]) for o in others] == [(0, PASSPORT_ITEM)]
    assert not any("sourceFileIndexes" in a or "sourceSegments" in a for a in result["attachments"])
    assert result["errors"] == []  # đúng ánh xạ → không cảnh báo (user 18/11)


def test_dinh_kem_khong_tach_nhieu_tep_dung_dong(monkeypatch):
    files = [_file("cccd.pdf"), _file("hc.pdf"), _file("gpld.pdf"), _file("vb.pdf"), _file("tk.pdf")]
    texts = {"cccd.pdf": CAN_CUOC, "hc.pdf": HO_CHIEU, "gpld.pdf": GPLD, "vb.pdf": VAN_BAN,
             "tk.pdf": _pdf_text(TO_KHAI, TO_KHAI_2)}
    _mock_io(monkeypatch, texts, "không phải JSON")  # LLM hỏng → luật theo tiêu đề
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": False}, {}))
    slots = _slots(result)
    assert (slots[0]["fileIndex"], slots[1]["fileIndex"], slots[2]["fileIndex"]) == (2, 4, 3)
    assert [(o["fileIndex"], o["componentName"]) for o in _others(result)] == [(0, "Thẻ căn cước"), (1, PASSPORT_ITEM)]
    # Chỉ còn dòng ghi lỗi LLM giả lập; hồ sơ đủ giấy → không cảnh báo thiếu.
    assert [e for e in result["errors"] if not e.startswith("attachment_agent")] == []
    # Thiếu văn bản đề nghị + giấy chứng minh → cảnh báo; tệp > 6 MB bị loại.
    files = [_file("tk.pdf"), _file("to.pdf", 7 * 1024 * 1024)]
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    assert list(_slots(result)) == [1]
    joined = " ".join(result["errors"])
    assert "chưa có Văn bản đề nghị" in joined and "chưa có giấy tờ chứng minh" in joined and "vượt giới hạn 6 MB" in joined


def test_dinh_kem_tach_dung_dong_khong_sot_trang(monkeypatch):
    files = [_file("ho-so.pdf")]
    texts = {"ho-so.pdf": _pdf_text(BIA, VAN_BAN, TO_KHAI, TO_KHAI_2, HO_CHIEU, GPLD)}
    llm = json.dumps({
        "tep": [{"fileIndex": 0, "tieuDeTrang": ["Hồ sơ thủ tục hành chính", "Văn bản đề nghị cấp thẻ tạm trú",
                                                 "Tờ khai đề nghị cấp thẻ tạm trú", "", "Hộ chiếu",
                                                 "Giấy phép lao động"]}],
        "documents": [
            {"fileIndex": 0, "pages": [1], "docType": "bia_ho_so", "documentName": "Hồ sơ thủ tục hành chính"},
            {"fileIndex": 0, "pages": [2], "docType": "van_ban", "documentName": "Văn bản đề nghị"},
            {"fileIndex": 0, "pages": [3, 4], "docType": "to_khai", "documentName": "Tờ khai"},
            {"fileIndex": 0, "pages": [5], "docType": "ho_chieu", "documentName": "Hộ chiếu"},
            {"fileIndex": 0, "pages": [6], "docType": "chung_minh", "documentName": "Giấy phép lao động"},
        ],
    })
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["extracted"]["attachmentMode"] == "split"
    slots = _slots(result)
    assert slots[0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [5]}]
    assert slots[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}, {"fileIndex": 0, "pageIndexes": [2, 3]}]
    assert slots[2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    others = _others(result)
    assert [(o["componentName"], o["sourceSegments"]) for o in others] == [
        (PASSPORT_ITEM, [{"fileIndex": 0, "pageIndexes": [4]}])]
    pages = sorted(p for a in result["attachments"] for s in a.get("sourceSegments") or [] for p in s["pageIndexes"])
    assert pages == [0, 1, 2, 3, 4, 5]  # không sót trang


def test_dinh_kem_tach_loi_quay_ve_khong_tach(monkeypatch):
    files = [_file("tk.pdf"), _file("vb.pdf"), _file("gpld.pdf")]
    texts = {"tk.pdf": TO_KHAI, "vb.pdf": VAN_BAN, "gpld.pdf": GPLD}

    def broken(_messages):
        raise RuntimeError("LLM sập")

    _mock_io(monkeypatch, texts, broken)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["errors"][0].startswith("attachment_agent (tách)")
    assert result["extracted"]["attachmentMode"] == "whole"
    slots = _slots(result)
    assert (slots[0]["fileIndex"], slots[1]["fileIndex"], slots[2]["fileIndex"]) == (2, 0, 1)
    assert not any(a.get("sourceSegments") for a in result["attachments"])
