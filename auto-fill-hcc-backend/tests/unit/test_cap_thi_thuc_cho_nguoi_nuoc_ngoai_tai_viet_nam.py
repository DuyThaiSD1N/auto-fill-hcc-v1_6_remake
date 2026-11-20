"""Cấp thị thực cho người nước ngoài tại Việt Nam 1.001194 (Cổng DVC Bộ Công an): mapper ô form + đính kèm + nối
registry / link kê khai + trợ lý người dân."""
import asyncio
import base64
import json

from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.attach import planner as attach_planner
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.attach.dinh_kem_khong_tach import (
    planner as whole_planner,
)
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process import mapper
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.schema import ALLOWED, COMPACT_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.services import ocr as ocr_service
from app.services.llm import client as llm_client

KEY = "cap-thi-thuc-cho-nguoi-nuoc-ngoai-tai-viet-nam"


def _mrz(number: str, nation: str, dob: str, sex: str, expiry: str, surname: str, given: str) -> str:
    """Dựng hai dòng MRZ TD3 đúng chữ số kiểm tra cho hộ chiếu bịa."""
    num = number.ljust(9, "<")
    line2 = (f"{num}{mapper._check_digit(num)}{nation}{dob}{mapper._check_digit(dob)}{sex}{expiry}"
             f"{mapper._check_digit(expiry)}").ljust(42, "<") + "00"
    line1 = f"P<{nation}{surname}<<{given.replace(' ', '<')}".ljust(44, "<")
    return f"{line1}\n{line2}"


MRZ = _mrz("XK204417", "CAN", "880605", "M", "330203", "DUPONT", "LUC ANDRE")
# Hồ sơ mẫu bịa cùng khuôn bộ mẫu: chồng người nước ngoài thăm vợ là công dân Việt Nam, vợ đứng bảo lãnh.
HO_SO = {
    "ToKhai_HoTen": "DUPONT LUC ANDRE", "ToKhai_GioiTinh": "Nam", "ToKhai_NgaySinh": "05/06/1988",
    "ToKhai_QuocTichGoc": "Ca-na-đa", "ToKhai_QuocTichHienNay": "Ca-na-đa", "ToKhai_NgheNghiep": "Kỹ sư phần mềm",
    "ToKhai_SoHoChieu": "XK204417", "ToKhai_LoaiHoChieu": "Hộ chiếu phổ thông", "ToKhai_HoChieu_CoQuanCap": "OTTAWA",
    "ToKhai_HoChieu_DenNgay": "03/02/2033", "ToKhai_NgayNhapCanh": "20/09/2026",
    "ToKhai_CuaKhau": "Cửa khẩu Sân bay quốc tế Nội Bài", "ToKhai_MucDichNhapCanh": "Thăm thân (thăm vợ)",
    "ToKhai_TamTruDen": "15/12/2026",
    "ToKhai_DiaChiTamTru": {"tinh": "tỉnh Lai Châu", "xa": "phường Đoàn Kết", "chiTietDuoiXa": "Số 8, tổ dân phố số 4"},
    "ToKhai_DienThoai": "+84 912 345 678", "ToKhai_Email": "luc.dupont@example.com",
    "ToKhai_BaoLanh_HoTen": "LÊ THỊ HOA", "ToKhai_BaoLanh_SoGiayTo": "Căn cước số 012190000001",
    "ToKhai_BaoLanh_NgayCap": "01/08/2025", "ToKhai_BaoLanh_CoQuanCap": "Bộ Công an", "ToKhai_BaoLanh_QuanHe": "Vợ (5)",
    "ToKhai_BaoLanh_DiaChi": {"tinh": "tỉnh Lai Châu", "xa": "phường Đoàn Kết", "chiTietDuoiXa": "Số 8, tổ dân phố số 4"},
    "ToKhai_BaoLanh_DienThoai": "0983 000 111", "ToKhai_BaoLanh_Email": "hoa.le@example.com",
    "ToKhai_LoaiThiThuc": "nhieu_lan", "ToKhai_ThiThuc_DenNgay": "19/11/2027",
    "ToKhai_LyDo": "Thăm thân – ở cùng vợ là công dân Việt Nam (ký hiệu TT)",
    "HoChieu_So": "XK204417", "HoChieu_MRZ": MRZ, "HoChieu_Ho": "DUPONT", "HoChieu_Ten": "LUC ANDRE",
    "HoChieu_QuocTich": "CANADA", "HoChieu_MaQuocGia": "CAN", "HoChieu_Loai": "P", "HoChieu_NgaySinh": "05/06/1988",
    "HoChieu_GioiTinh": "M", "HoChieu_NgayHetHan": "03/02/2033", "HoChieu_CoQuanCap": "GATINEAU",
    "HoChieu_NhapCanh_Ngay": "22/09/2026", "HoChieu_NhapCanh_CuaKhau": "Cửa khẩu Sân bay quốc tế Nội Bài",
    "HoChieu_TamTruDen": "18/12/2026",
    "KetHon_Chong_HoTen": "DUPONT LUC ANDRE", "KetHon_Vo_HoTen": "LÊ THỊ HOA",
    "KetHon_Vo_NoiCuTru": {"tinh": "tỉnh Lai Châu", "xa": "phường Tân Phong", "chiTietDuoiXa": "Số 8, tổ dân phố số 4"},
    "Cccd_HoTen": "Lê Thị Hoa", "Cccd_SoDinhDanh": "012190000001", "Cccd_NgayCap": "22/07/2025",
    "Cccd_NoiCap": "BỘ CÔNG AN", "Cccd_NoiCuTru": {"tinh": "Tỉnh Lai Châu", "xa": "Phường Đoàn Kết",
                                                  "chiTietDuoiXa": "Số 8, Tổ dân phố số 4"},
}


def _enrich(values: dict):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {})


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_dien_dung_mapping_bo_mau():
    out, warnings = _enrich(HO_SO)
    assert _by(out) == {
        # Cơ quan tiếp nhận: extension chọn mục thật đầu tiên (firstOption, user 19/11/2026).
        "CongDan__fs_BCANoiNopHS": "Cơ quan đã chọn ở bước chọn trường hợp hồ sơ",
        "CongDan_tenCongDan": "DUPONT LUC ANDRE",
        "CongDan_ngaySinhCongDan": "05/06/1988",
        "CongDan__fs_BCAGioiTinhCd": "Nam",
        "CongDan__fs_BCAQuocTichHienNay": "Canada",      # danh mục cổng ghi tên nước tiếng Anh
        "CongDan__fs_BCAQuocTichGoc": "Canada",
        "CongDan__fs_BCANgheNghiep": "Kỹ sư phần mềm",
        "CongDan__fs_BCASoHoChieu": "XK204417",
        "CongDan__fs_BCALoaiHoChieu": "Hộ chiếu phổ thông",
        "CongDan__fs_BCACoQuanCap": "GATINEAU",           # hộ chiếu thắng tờ khai
        "CongDan__fs_BCAHoChieuDenNgay": "03/02/2033",
        "CongDan__fs_BCANgayNhapCanh": "22/09/2026",      # dấu kiểm chứng trên hộ chiếu thắng tờ khai
        "CongDan__fs_BCAQuaCuaKhau": "SBQT Nội Bài",
        "CongDan__fs_BCATamTruDen": "18/12/2026",
        "CongDan__fs_BCAMucDichNhapCanh": "thăm thân",
        "CongDan__fs_BCATinhTamTru": "Tỉnh Lai Châu",
        "CongDan__fs_BCAXaTamTru": "Phường Đoàn Kết",
        "CongDan__fs_BCADiaChiTamTru": "Số 8, tổ dân phố số 4",
        "CongDan_diDong": "0912345678",
        "CongDan_email": "luc.dupont@example.com",
        "CongDan__fs_BCANgayCapCMNDBaoLanh": "22/07/2025",  # thẻ căn cước thắng tờ khai
        "CongDan__fs_BCACoQuanCapCMNDBaoLanh": "Bộ Công an",
        "CongDan__fs_BCAQuanHeNguoiDeNghi": "Vợ",           # bỏ số chú thích (5)
        "CongDan__fs_BCATinhThuongTru": "Tỉnh Lai Châu",
        "CongDan__fs_BCAXaThuongTru": "Phường Đoàn Kết",     # CCCD (địa giới mới) thắng giấy kết hôn
        "CongDan__fs_BCADiaChiThuongTruVNBaoLanh": "Số 8, Tổ dân phố số 4",
        "CongDan__fs_BCATinhTamTruBaoLanh": "Tỉnh Lai Châu",
        "CongDan__fs_BCAXaTamTruBaoLanh": "Phường Đoàn Kết",
        "CongDan__fs_BCADiaChiTamTruBaoLanh": "Số 8, Tổ dân phố số 4",
        "CongDan__fs_BCADiDongBaoLanh": "0983000111",
        "CongDan__fs_BCAEmailBaoLanh": "hoa.le@example.com",
        "CongDan__fs_BCACapThiThucLan": "Nhiều lần",
        "CongDan__fs_BCAThiThucDenNgay": "19/11/2027",
        "CongDan__fs_BCALyDoDeNghiCapThiThuc": "Thăm thân – ở cùng vợ là công dân Việt Nam (ký hiệu TT)",
    }
    fields = {f["name"]: f for f in out}
    for ward in ("CongDan__fs_BCAXaTamTru", "CongDan__fs_BCAXaThuongTru", "CongDan__fs_BCAXaTamTruBaoLanh"):
        assert fields[ward]["waitMs"] == 8000, ward
    # Ô readonly cổng lấy từ tài khoản người bảo lãnh + nơi nhận: không phát (cơ quan tiếp nhận: firstOption, 19/11).
    for locked in ("CongDan__fs_BCAThanNhanBaoLanh", "CongDan__fs_BCANgaySinhBaoLanh", "CongDan_soCmnd",
                   "CongDan__fs_BCANoiNhanHoChieu", "CongDan__fs_BCA_CoQuanThanNhan"):
        assert locked not in fields
    joined = " ".join(warnings)
    assert "Ảnh chân dung 4x6" in joined and "Trang nhân thân hộ chiếu" in joined
    assert "Cơ quan tiếp nhận" in joined and "điền trùng địa chỉ thường trú" in joined
    assert "nhập tay các ô bắt buộc" not in joined  # bộ đủ giấy → không thiếu ô bắt buộc


def test_mrz_doc_dung_va_ho_chieu_nguoi_khac():
    parsed = mapper.parse_mrz(MRZ)
    assert parsed == {"so": "XK204417", "maQuocGia": "CAN", "ngaySinh": "05/06/1988", "ngayHetHan": "03/02/2033",
                      "gioiTinh": "M", "ho": "DUPONT", "ten": "LUC ANDRE"}
    # MRZ đúng chữ số kiểm tra thắng số OCR đọc nhầm trên trang; sai chữ số kiểm tra thì bỏ MRZ.
    by = _by(_enrich({**HO_SO, "HoChieu_So": "XK2O4417"})[0])
    assert by["CongDan__fs_BCASoHoChieu"] == "XK204417"
    assert mapper.parse_mrz(MRZ.replace("XK204417<", "XK204418<")).get("so") is None
    # Tên trên hộ chiếu đảo thứ tự Surname / Given names vẫn là cùng người.
    by = _by(_enrich({**HO_SO, "ToKhai_HoTen": "LUC ANDRE DUPONT"})[0])
    assert by["CongDan__fs_BCASoHoChieu"] == "XK204417" and by["CongDan_tenCongDan"] == "DUPONT LUC ANDRE"
    # Hộ chiếu của người khác (khác tên, khác số) → bỏ, điền theo tờ khai.
    other = {**HO_SO, "HoChieu_Ho": "SMITH", "HoChieu_Ten": "ANNA", "HoChieu_So": "ZZ9999999",
             "HoChieu_MRZ": _mrz("ZZ999999", "USA", "900101", "F", "300101", "SMITH", "ANNA")}
    out, warnings = _enrich(other)
    by = _by(out)
    assert by["CongDan__fs_BCASoHoChieu"] == "XK204417" and by["CongDan__fs_BCACoQuanCap"] == "OTTAWA"
    assert by["CongDan__fs_BCANgayNhapCanh"] == "20/09/2026" and by["CongDan__fs_BCATamTruDen"] == "15/12/2026"
    assert any("Hộ chiếu tải lên không phải của người đề nghị" in w for w in warnings)


def test_quoc_tich_cua_khau_muc_dich_va_quan_he_suy_tu_giay_ket_hon():
    assert mapper._country("Hoa Kỳ") == "United States" and mapper._country("D") == "Germany"
    assert mapper._country("Nhật Bản") == "Japan" and mapper._country("FRANCE") == "France"
    # Tên danh mục cổng (mapping thẻ tạm trú 19/11): Hàn Quốc = "Republic of Korea", không chọn nhầm Triều Tiên.
    assert mapper._country("Hàn Quốc") == "Republic of Korea" and mapper._country("KOR") == "Republic of Korea"
    assert mapper._country("REPUBLIC OF KOREA") == "Republic of Korea"
    assert mapper._border_gate("Sân bay quốc tế Tân Sơn Nhất") == "SBQT Tân Sơn Nhất"
    assert mapper._border_gate("Cửa khẩu quốc tế Mộc Bài") == "Mộc Bài"
    assert mapper._purpose("Du lịch") == "du lịch" and mapper._purpose("Làm việc với doanh nghiệp") == "làm việc"
    # Tờ khai bỏ trống quan hệ → suy từ giấy kết hôn (người bảo lãnh đứng cột vợ). Không có CCCD → địa chỉ giấy kết hôn.
    values = {k: v for k, v in HO_SO.items() if not k.startswith("Cccd_") and k != "ToKhai_BaoLanh_QuanHe"}
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCAQuanHeNguoiDeNghi"] == "Vợ"
    assert by["CongDan__fs_BCAXaThuongTru"] == "Phường Tân Phong"
    assert by["CongDan__fs_BCANgayCapCMNDBaoLanh"] == "01/08/2025"  # theo tờ khai mục II.2
    # Căn cước của người khác → bỏ, cảnh báo.
    _, warnings = _enrich({**HO_SO, "Cccd_HoTen": "Trần Văn Bình", "Cccd_SoDinhDanh": "012190009999"})
    assert any("Thẻ căn cước tải lên không phải của người bảo lãnh" in w for w in warnings)


def test_thieu_o_bat_buoc_va_gia_han_canh_bao():
    values = {k: v for k, v in HO_SO.items()
              if k not in ("ToKhai_Email", "ToKhai_QuocTichGoc", "ToKhai_LoaiThiThuc", "ToKhai_BaoLanh_Email")}
    out, warnings = _enrich({**values, "ToKhai_GiaHan_DenNgay": "01/03/2027", "ToKhai_CoQuanBaoLanh": "Công ty TNHH ABC"})
    by = _by(out)
    assert "CongDan__fs_BCACapThiThucLan" not in by and "CongDan__fs_BCAQuocTichGoc" not in by
    joined = " ".join(warnings)
    assert "Quốc tịch gốc" in joined and "Email liên hệ (người bảo lãnh)" in joined
    assert "một lần / nhiều lần" in joined and "Gia hạn tạm trú đến ngày" in joined
    assert "cơ quan, tổ chức bảo lãnh \"Công ty TNHH ABC\"" in joined


def test_fallback_ocr_mrz_va_o_mot_lan_nhieu_lan():
    to_khai = ("TỜ KHAI ĐỀ NGHỊ CẤP THỊ THỰC, GIA HẠN TẠM TRÚ\nIII. Nội dung đề nghị:\n"
               "1. Cấp thị thực: một lần nhiều lần có giá trị đến ngày: ☐ ☒ 19/11/2027\n")
    ho_chieu = "CANADA PASSPORT\nPassport No. XK204417\n" + MRZ.replace("\n", "\n ")
    fields = mapper.ocr_fallback([{"name": "ToKhai_HoTen", "value": "DUPONT LUC ANDRE"}],
                                 [{"name": "tk.pdf", "text": to_khai}, {"name": "hc.jpg", "text": ho_chieu}])
    assert fields["ToKhai_LoaiThiThuc"] == "nhieu_lan"
    assert mapper.parse_mrz(fields["HoChieu_MRZ"])["so"] == "XK204417"
    fields = mapper.ocr_fallback({"ToKhai_LoaiThiThuc": "mot_lan"}, [{"text": to_khai}])
    assert fields["ToKhai_LoaiThiThuc"] == "mot_lan"
    fields = mapper.ocr_fallback({}, [{"text": to_khai.replace("☐ ☒", "☒ ☐")}])
    assert fields["ToKhai_LoaiThiThuc"] == "mot_lan"


def test_schema_registry_link_va_detect():
    assert {"ToKhai_HoTen", "ToKhai_BaoLanh_QuanHe", "HoChieu_MRZ", "KetHon_Vo_HoTen", "Cccd_NgayCap"} <= ALLOWED
    assert COMPACT_COMP_BY_NAME["ToKhai_DiaChiTamTru"] == "x-select-area"
    assert COMPACT_COMP_BY_NAME["ToKhai_ThiThuc_DenNgay"] == "x-date"
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"]
    # Ô Loại hộ chiếu điền xong hiện "Hộ chiếu phổ thông" → cụm của thị thực phải dài hơn cụm của 1.001456.
    ho_chieu = registry.get_procedure("cap-ho-chieu-pho-thong-o-trong-nuoc")["detect"]["textIncludes"]
    assert sum(map(len, proc["detect"]["textIncludes"])) > sum(map(len, ho_chieu))
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.001194" and link["label"] == proc["label"]
    assert link["needsAgencySelect"] is False and link["directSubmit"] is True and link["bcaSubmit"] is True
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert "matthc=1.001194" in public["detect"]["urlIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow, lai_chau  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaThiThuc": True}


def test_tro_ly_cung_key_detect_hien_moi_tinh_va_can_co_rieng():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat.router import _clean_client_capabilities

    proc = hf.get_procedure(KEY)
    assert proc["detect"] == registry.get_procedure(KEY)["detect"] and proc["label"] == registry.get_procedure(KEY)["label"]
    assert proc["requiresCapability"] == "supportsBcaThiThuc" and proc["hasAttachmentStep"] is True
    assert proc["supportsSplitDocuments"] is True and hf.get_attach_pipeline(KEY) is registry.get_attach_pipeline(KEY)
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY) and "provinceOnly" not in proc
    assert proc["laiChauFeeStep"]["caseAgencyByProvince"]["label"] == "Cơ quan giải quyết hồ sơ"
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert _clean_client_capabilities({"supportsBcaThiThuc": True})["supportsBcaThiThuc"] is True

    # Bản trợ lý chưa khai cờ: không dẫn vào cổng.
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert "chưa hỗ trợ" in r.display_md and not r.actions
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == proc["keKhaiUrl"]
    flow._handle_guide_login(conv, Intent("event", "page_status", {"loggedIn": True, "formKind": "standard"}))
    assert conv["state"] in ("ask_doc_method", "consent")


def test_tro_ly_nop_thang_nhu_auto_fill_khong_chon_tinh_xa():
    # User 18/11: trợ lý phải đi như Auto Fill (directSubmit + bcaSubmit) — trang DVCQG có khối chọn cơ quan nhưng KHÔNG
    # chọn Tỉnh/Xã: bấm Nộp hồ sơ → Nộp trực tuyến, sang trang thủ tục cổng Bộ Công an bấm tiếp Nộp hồ sơ.
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Khánh Hòa", "province_slug": "khanhhoa", "ward": "Phường Nam Nha Trang"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert "**Nộp hồ sơ** → **Nộp trực tuyến**" in r.display_md and "Nam Nha Trang" not in r.display_md
    page = lambda payload: flow._handle_guide_login(conv, Intent("event", "page_status", payload))  # noqa: E731
    r = page({"loggedIn": True, "agencyBlock": True, "formKind": ""})
    assert r.actions == [{"type": "select_agency", "direct": True, "province": "", "ward": ""}]
    assert "tỉnh, xã" not in (r.display_md or "")
    assert page({"loggedIn": True, "agencyBlock": True}).actions == []  # watcher báo nhịp kế: không bấm trùng
    flow._handle_guide_login(conv, Intent("event", "agency_selected", {}))
    # Sang trang thủ tục cổng Bộ Công an đúng mã → bấm Nộp hồ sơ; trang thủ tục khác → không bấm.
    r = page({"loggedIn": True, "bcaTthcPage": True, "bcaTthcCode": "1.001194"})
    assert r.actions == [{"type": "bca_tthc_submit", "code": "1.001194"}]
    conv["bca_tthc_dispatched_at"] = 0
    assert page({"loggedIn": True, "bcaTthcPage": True, "bcaTthcCode": "1.001456"}).actions == []
    # Bấm hỏng → dặn bấm tay đúng nút, không bảo chọn tỉnh/xã.
    r = flow._handle_guide_login(conv, Intent("event", "bca_tthc_failed", {"value": "không thấy nút"}))
    assert "**Nộp hồ sơ**" in r.display_md
    conv["agency_done"] = False  # lượt bấm trên DVCQG hỏng (chưa từng sang được cổng Bộ Công an)
    r = flow._handle_guide_login(conv, Intent("event", "agency_failed", {"value": "không thấy nút"}))
    assert "Nộp trực tuyến" in r.display_md and "Nam Nha Trang" not in r.display_md


async def _no_save(_conv):
    return None


def test_tro_ly_dien_truoc_roi_moi_dinh_kem_tren_eform_bo_cong_an(monkeypatch):
    # Chạy thật 18/11: bảng Thành phần hồ sơ 3 dòng nằm NGAY DƯỚI form kê khai trên cùng một trang (dưới "Nơi nhận thị
    # thực"). Lần 1 trợ lý đính kèm trước khi điền; lần 2 điền xong lại chờ sang trang khác nên không đính. Đúng: điền
    # trước, điền xong đính NGAY trên trang đó; còn eForm nào bảng nằm trang sau thì chờ sang trang đó.
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat import pipeline_runner

    proc = hf.get_procedure(KEY)
    same_page = {"pageContextCaptured": True, "formKind": "standard", "attachmentTarget": True,
                 "attachmentComponentCount": 3, "bcaKeKhaiForm": True}
    form_only = {"pageContextCaptured": True, "formKind": "standard", "attachmentTarget": False,
                 "attachmentComponentCount": 0, "bcaKeKhaiForm": True}
    attach_page = {"pageContextCaptured": True, "formKind": "standard", "attachmentTarget": True,
                   "attachmentComponentCount": 3, "bcaKeKhaiForm": False}
    old_ext = {"pageContextCaptured": True, "formKind": "standard", "attachmentTarget": True,
               "attachmentComponentCount": 3}  # extension cũ chưa báo bcaKeKhaiForm
    assert flow._resolve_docs_target(proc, same_page, {}) == "declaration"
    assert flow._resolve_docs_target(proc, form_only, {}) == "declaration"
    assert flow._resolve_docs_target(proc, attach_page, {}) == "attachment"
    assert flow._resolve_docs_target(proc, old_ext, {}) == "declaration"
    assert flow._resolve_docs_target(proc, old_ext, {"main_processing_started": True}) == "attachment"
    # Hộ chiếu, mẫu con dấu cùng nền eForm Nth → cùng chốt; thủ tục cổng khác giữ nguyên.
    assert flow._resolve_docs_target(hf.get_procedure("cap-ho-chieu-pho-thong-o-trong-nuoc"), same_page, {}) == \
        "declaration"
    assert flow._resolve_docs_target(hf.get_procedure("chung-thuc-ban-sao"), same_page, {}) == "attachment"

    calls = []

    async def progress(_sid):
        return {"received": 3, "total": 3, "files_count": 1}

    # spawn(run_xxx(...)): ghi lại pipeline nào được khởi chạy, không chạy thật.
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a: calls.append("process"))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a: calls.append("attach"))
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)
    monkeypatch.setattr(flow.upload_service, "progress_of", progress)

    def new_conv():
        return {"_id": "t-thi-thuc", "state": "collecting_docs", "history": [], "procedure_key": KEY,
                "upload_session_id": "s1", "docs_target": "attachment",
                "client_capabilities": {"supportsPageBoundDocsComplete": True, **CAPS}}

    # 1) "Đã đưa đủ giấy tờ" bấm trên trang có form + bảng → chạy pipeline ĐIỀN trước, chưa lập kế hoạch đính kèm.
    conv = new_conv()
    asyncio.run(flow._docs_complete(conv, same_page))
    assert conv["docs_target"] == "declaration" and conv["state"] == "filling"
    assert calls == ["process"] and conv["auto_attach_after_fill"] is True
    assert not conv.get("attachment_plan_started")
    # 2) Điền xong (fill_report) trên trang đó → user 19/11: KHÔNG tự đính, dừng ở rà soát và hỏi đính kèm (nút "Đính kèm
    # giấy tờ"), nhắc nói "điền lại tờ khai" nếu chưa đúng.
    calls.clear()
    conv["pipeline_status"] = "fields_ready"  # run_process chạy xong (spawn giả không chạy)
    r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 33, "notFound": []})))
    assert conv["state"] == "reviewing" and not conv.get("attachment_plan_started") and calls == []
    assert "Thành phần hồ sơ** ngay bên dưới" in r.display_md and "điền lại tờ khai" in r.display_md
    assert "__action:confirm_review" in [c["send"] for c in r.chips]
    # "Điền lại tờ khai" lúc này còn ở phiên điền → chạy lại lượt điền, không đính.
    monkeypatch.setattr(flow.conv_store, "save", _no_save)
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "refill", {})))
    assert calls == ["process"] and conv["state"] == "filling" and conv["docs_target"] == "declaration"
    calls.clear()
    conv["pipeline_status"] = "fields_ready"
    asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 34, "notFound": []})))
    assert conv["state"] == "reviewing" and calls == []
    # Bấm "Đính kèm giấy tờ" → lập kế hoạch đính NGAY trên trang này (bảng cùng trang, không chờ trang khác).
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "confirm_review", {})))
    assert conv["state"] == "attaching" and conv["attachment_plan_started"] is True and calls == ["attach"]
    # Watcher của chính trang này cũng tính là đã tới chỗ đính kèm (kế hoạch về thì phát lệnh đính).
    assert flow._attachment_page_reached(conv, proc, same_page) is True

    # 3) eForm mà bảng nằm TRANG SAU (form không kèm bảng): điền xong cũng dừng hỏi, nhắc "Đồng ý và tiếp tục".
    conv = new_conv()
    calls.clear()
    asyncio.run(flow._docs_complete(conv, form_only))
    calls.clear()
    r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 33, "notFound": []})))
    assert conv["state"] == "reviewing" and calls == []
    assert "Đồng ý và tiếp tục" in r.display_md
    conv["attachment_context"] = {"hasAttachmentTableHeader": True, "hasFileControl": True,
                                  "components": [{"index": i, "componentName": f"Dòng {i}"} for i in (1, 2, 3)]}
    assert flow._attachment_page_reached(conv, proc, form_only) is False
    assert flow._attachment_page_reached(conv, proc, attach_page) is True

    # 4) Đính xong trên trang cùng form: nhắc chọn Nơi nhận + nút cam "Đồng ý và tiếp tục" (trợ lý bấm hộ, user 18/11).
    def attach_done(caps: dict, errors: list[str]):
        conv = new_conv()
        conv["client_capabilities"].update(caps)
        conv.update(state="attaching", docs_page_context=flow._docs_page_context(same_page),
                    attach_plan=[{"fileIndex": 0, "target": "fixed-slot", "slotIndex": 0}],
                    attach_action_in_progress=True, attach_action_dispatch_id="d1", fill_report={"filled": 33})
        return asyncio.run(flow._handle_attaching(conv, Intent("action", "attach_report",
                                                             {"attached": 2, "skipped": 0, "errors": errors,
                                                              "dispatch_id": "d1"})))

    lc_caps = {"supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
    r = attach_done(lc_caps, [])
    assert "Nơi nhận" in r.display_md and "Đồng ý và tiếp tục" in r.display_md
    cta = [c for c in r.chips if c.get("cta")]
    assert cta == [lai_chau.next_chip()] and cta[0]["send"] == "__action:lc_next"
    # Bấm nút → trợ lý bấm "Đồng ý và tiếp tục" của cổng (lệnh lc_next cho extension).
    conv = new_conv()
    conv["client_capabilities"].update(lc_caps)
    conv["state"] = "done"
    r = asyncio.run(flow._handle_turn_inner(conv, Intent("action", "lc_next", {})))
    assert r.actions == [{"type": "lc_next"}]
    # Đính lỗi → không mời đi tiếp; extension chưa có lệnh lc_next → không hiện nút.
    assert not [c for c in attach_done(lc_caps, ["Không thấy dòng tờ khai"]).chips if c.get("cta")]
    assert not [c for c in attach_done({}, []).chips if c.get("cta")]


def test_tro_ly_trang_xac_nhan_dan_nhap_ma_tich_o_roi_hien_nut_nop_ho_so():
    # Ảnh 18/11: bấm "Đồng ý và tiếp tục" xong cổng sang trang xác nhận thông tin nộp (Mã xác nhận + ô "Tôi xin chịu trách
    # nhiệm…" + Nộp hồ sơ). Trợ lý dặn công dân nhập mã + tích ô rồi hiện nút Nộp hồ sơ; bấm nút → extension soát rồi nộp.
    nth_caps = {**CAPS, "supportsBcaNthSubmit": True}

    def conv_with(caps):
        return {"_id": "t-nth", "state": "done", "history": [], "procedure_key": KEY, "client_capabilities": dict(caps)}

    def turn(conv, kind, value, payload=None):
        return asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))

    confirm_page = {"loggedIn": True, "formKind": "", "bcaConfirmPage": True}
    conv = conv_with(nth_caps)
    r = turn(conv, "event", "page_status", confirm_page)
    assert "**Mã xác nhận**" in r.display_md and "Tôi xin chịu trách nhiệm" in r.display_md
    assert r.chips == [flow._bca_nth_submit_chip()] and r.chips[0]["send"] == "__action:bca_nth_submit"
    # Watcher báo lại trang (gõ mã, tích ô) → im, không lặp câu dặn.
    r = turn(conv, "event", "page_status", confirm_page)
    assert not r.display_md and not r.chips
    # Bấm nút → lệnh cho extension.
    r = turn(conv, "action", "bca_nth_submit")
    assert r.actions == [{"type": "bca_nth_submit"}]
    # Kết quả lượt bấm.
    report = lambda payload: turn(conv, "action", "bca_nth_submit_report", payload)  # noqa: E731
    r = report({"clicked": False, "missing": ["captcha"]})
    assert "Mã xác nhận" in r.display_md and r.chips == [flow._bca_nth_submit_chip()]
    r = report({"clicked": False, "missing": ["commit"]})
    assert "Tôi xin chịu trách nhiệm" in r.display_md and r.chips == [flow._bca_nth_submit_chip()]
    r = report({"clicked": True, "confirm": True})
    assert "**Đồng ý**" in r.display_md and not r.chips
    r = report({"clicked": True, "message": "Mã xác nhận không đúng"})
    assert "Mã xác nhận không đúng" in r.display_md and r.chips == [flow._bca_nth_submit_chip()]
    r = report({"clicked": True, "message": ""})
    assert not r.display_md and not r.chips  # cổng nhận, trang tự chuyển
    r = report({"noEngine": True})
    assert "Nộp hồ sơ" in r.display_md and not r.chips
    # Extension chưa có lệnh nộp → chỉ dặn công dân tự bấm Nộp hồ sơ trên trang, không có nút.
    conv = conv_with(CAPS)
    r = turn(conv, "event", "page_status", confirm_page)
    assert "cuối trang" in r.display_md and not r.chips
    # Thủ tục cổng khác không dính.
    assert flow._bca_nth_confirm_handle({"client_capabilities": nth_caps}, {"key": "x"},
                                        Intent("event", "page_status", confirm_page)) is None


# ── Đính kèm: bảng Thành phần hồ sơ 3 dòng (dòng 2 gia hạn tạm trú không dùng) ──
BIA = ("HỒ SƠ THỦ TỤC HÀNH CHÍNH\nCẤP THỊ THỰC CHO NGƯỜI NƯỚC NGOÀI TẠI VIỆT NAM\nDANH MỤC THÀNH PHẦN HỒ SƠ\n"
       "1 Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5)\n3 Giấy chứng nhận kết hôn")
TO_KHAI = ("Mẫu (Form) NA5\nTỜ KHAI ĐỀ NGHỊ CẤP THỊ THỰC, GIA HẠN TẠM TRÚ\nAPPLICATION FORM FOR VISA ISSUANCE, STAY "
           "EXTENSION\nI. Người đề nghị:\n1. Họ tên (chữ in hoa): DUPONT LUC ANDRE")
TO_KHAI_2 = "Địa chỉ thường trú/tạm trú tại Việt Nam: Số 8\nIII. Nội dung đề nghị:\nIV. Những điều cần trình bày thêm"
HO_CHIEU = "CANADA\nPASSPORT\nPassport No. XK204417\nSurname DUPONT\n" + MRZ
KET_HON = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY CHỨNG NHẬN KẾT HÔN\nNgười chồng DUPONT LUC ANDRE Người vợ LÊ THỊ HOA"
CAN_CUOC = "CĂN CƯỚC\nIDENTITY CARD\nSố định danh cá nhân: 012190000001\nLÊ THỊ HOA"
ROW1 = ["to khai de nghi cap thi thuc"]
ROW3 = ["chung minh ly do duoc cap thi thuc"]


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


def test_dinh_kem_khong_tach_mot_tep_gop_dinh_ca_dong_1_va_dong_3(monkeypatch):
    # Ảnh ánh xạ: cả bộ trong MỘT PDF → đính nguyên tệp vào dòng 1 và dòng 3, dòng 2 không tick. LLM chỉ thấy 4000 ký
    # tự đầu nên trả to_khai — tiêu đề giấy kết hôn IN HOA ở trang sau vẫn đưa tệp về loại gộp.
    files = [_file("ho-so.pdf")]
    texts = {"ho-so.pdf": _pdf_text(BIA, TO_KHAI, TO_KHAI_2, HO_CHIEU, KET_HON, CAN_CUOC)}
    _mock_io(monkeypatch, texts, json.dumps({"documents": [{"index": 0, "docType": "to_khai", "documentName": ""}]}))
    result = asyncio.run(attach_planner.plan(files, {}, {}))
    assert result["extracted"]["attachmentMode"] == "whole"
    assert result["extracted"]["classified"] == [{"fileName": "ho-so.pdf", "docType": "ho_so_gop"}]
    slots = _slots(result)
    assert list(slots) == [0, 2] and len(result["attachments"]) == 2
    assert slots[0]["fileIndex"] == 0 and slots[0]["slotKeywords"] == ROW1 and slots[0]["tickRow"] is True
    assert slots[2]["fileIndex"] == 0 and slots[2]["slotKeywords"] == ROW3
    assert not any("sourceFileIndexes" in a or "sourceSegments" in a for a in result["attachments"])
    # Hồ sơ đủ, đính đúng ảnh ánh xạ → KHÔNG cảnh báo gì (user 18/11: bỏ câu "tệp gộp…" và "dòng gia hạn tạm trú…").
    assert result["errors"] == []
    # Chạy thật bộ mẫu 18/11: OCR làm rơi dòng tiêu đề in hoa của tờ khai (chỉ còn "Mẫu (Form NA5", "APPLICATION FORM
    # FOR VISISA"), LLM thấy trang bìa đầu tệp nên trả bia_ho_so → vẫn phải nhận là tệp gộp.
    ocr_to_khai = ("Thành phần hồ sơ 1/4: Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5) Mẫu (Form NA5 Kèm theo "
                   "Thông tư APPLICATION FORM FOR VISISA ISSUANCE, STAY EXTENSION I. Người đề nghị:")
    texts = {"ho-so.pdf": _pdf_text(BIA, ocr_to_khai, TO_KHAI_2, HO_CHIEU, KET_HON, CAN_CUOC)}
    _mock_io(monkeypatch, texts, json.dumps({"documents": [{"index": 0, "docType": "bia_ho_so", "documentName": ""}]}))
    result = asyncio.run(attach_planner.plan(files, {}, {}))
    assert result["extracted"]["classified"][0]["docType"] == "ho_so_gop" and list(_slots(result)) == [0, 2]
    # Chỉ có bìa (danh mục ghi "(Mẫu NA5)", tên giấy chữ thường) → không phải tệp gộp.
    assert whole_planner.is_combined(BIA) is False


def test_dinh_kem_khong_tach_nhieu_tep_dung_dong(monkeypatch):
    # Hộ chiếu theo tờ khai vào dòng 1, căn cước theo giấy kết hôn vào dòng 3; LLM hỏng → luật theo tiêu đề.
    files = [_file("cccd.pdf"), _file("hc.pdf"), _file("kh.pdf"), _file("tk.pdf")]
    texts = {"cccd.pdf": CAN_CUOC, "hc.pdf": HO_CHIEU, "kh.pdf": KET_HON, "tk.pdf": TO_KHAI + "\n" + TO_KHAI_2}
    _mock_io(monkeypatch, texts, "không phải JSON")
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": False}, {}))
    slots = _slots(result)
    assert slots[0]["fileIndex"] == 3 and slots[0]["sourceFileIndexes"] == [3, 1]
    assert slots[2]["fileIndex"] == 2 and slots[2]["sourceFileIndexes"] == [2, 0]
    # Thiếu giấy chứng minh lý do → cảnh báo; tệp > 6 MB bị loại.
    files = [_file("tk.pdf"), _file("hc.pdf"), _file("to.pdf", 7 * 1024 * 1024)]
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    assert list(_slots(result)) == [0]
    assert any("chưa có giấy tờ chứng minh lý do" in e for e in result["errors"])
    assert any("vượt giới hạn 6 MB" in e for e in result["errors"])


def test_dinh_kem_tach_dung_dong_khong_sot_trang(monkeypatch):
    files = [_file("ho-so.pdf")]
    texts = {"ho-so.pdf": _pdf_text(BIA, TO_KHAI, TO_KHAI_2, HO_CHIEU, KET_HON, CAN_CUOC)}
    llm = json.dumps({
        "tep": [{"fileIndex": 0, "tieuDeTrang": ["Hồ sơ thủ tục hành chính", "Tờ khai đề nghị cấp thị thực", "",
                                                 "Hộ chiếu", "Giấy chứng nhận kết hôn", "Căn cước"]}],
        "documents": [
            {"fileIndex": 0, "pages": [1], "docType": "bia_ho_so", "documentName": "Hồ sơ thủ tục hành chính"},
            {"fileIndex": 0, "pages": [2, 3], "docType": "to_khai", "documentName": "Tờ khai"},
            {"fileIndex": 0, "pages": [4], "docType": "ho_chieu", "documentName": "Hộ chiếu"},
            {"fileIndex": 0, "pages": [5], "docType": "chung_minh", "documentName": "Giấy chứng nhận kết hôn"},
            {"fileIndex": 0, "pages": [6], "docType": "identity", "documentName": "Căn cước"},
        ],
    })
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["extracted"]["attachmentMode"] == "split"
    slots = _slots(result)
    assert list(slots) == [0, 2]
    assert slots[0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}, {"fileIndex": 0, "pageIndexes": [1, 2]},
                                          {"fileIndex": 0, "pageIndexes": [3]}]
    assert slots[2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [4]}, {"fileIndex": 0, "pageIndexes": [5]}]
    pages = sorted(p for a in result["attachments"] for s in a.get("sourceSegments") or [] for p in s["pageIndexes"])
    assert pages == [0, 1, 2, 3, 4, 5]  # không sót trang


def test_dinh_kem_tach_loi_quay_ve_khong_tach(monkeypatch):
    files = [_file("tk.pdf"), _file("kh.pdf")]
    texts = {"tk.pdf": TO_KHAI, "kh.pdf": KET_HON}

    def broken(_messages):
        raise RuntimeError("LLM sập")

    _mock_io(monkeypatch, texts, broken)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["errors"][0].startswith("attachment_agent (tách)")
    assert result["extracted"]["attachmentMode"] == "whole"
    slots = _slots(result)
    assert slots[0]["fileIndex"] == 0 and slots[2]["fileIndex"] == 1
    assert not any(a.get("sourceSegments") for a in result["attachments"])


# ── Ảnh chân dung 4x6 (ô filename46 đầu trang kê khai), user 19/11/2026: tự gắn như hộ chiếu / thẻ tạm trú ──
def _portrait(name: str = "IMG_0001.jpg") -> dict:
    import io

    from PIL import Image

    image = Image.new("RGB", (400, 600), (255, 255, 255))
    image.paste((120, 90, 70), (100, 150, 300, 600))  # "người" giữa nền sáng
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return {"name": name, "type": "image/jpeg",
            "dataUrl": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()}


def test_dinh_kem_khong_dinh_anh_chan_dung_va_tra_o_anh(monkeypatch):
    # Trước đây ảnh chân dung (OCR rỗng) rơi "other" → bị gộp vào dòng 3 giấy chứng minh. Nay: không đính, trả ô ảnh.
    photo = _portrait()
    files = [_file("tk.pdf"), _file("kh.pdf"),
             FileItem(name=photo["name"], type=photo["type"], dataUrl=photo["dataUrl"], role="other")]
    _mock_io(monkeypatch, {"tk.pdf": TO_KHAI, "kh.pdf": KET_HON, photo["name"]: "VÀNG"}, "không phải JSON")
    for split in (False, True):
        result = asyncio.run(attach_planner.plan(files, {"splitDocuments": split}, {}))
        slots = _slots(result)
        used = {i for a in result["attachments"] for i in [a["fileIndex"], *(a.get("sourceFileIndexes") or []),
                                                          *(s["fileIndex"] for s in a.get("sourceSegments") or [])]}
        assert 2 not in used, split
        assert list(slots) == [0, 2], split
        assert [f["name"] for f in result["pageFields"]] == ["filename46"], split
        assert result["pageFields"][0]["comp"] == "bca-photo"


def test_runner_gan_anh_chan_dung_dau_danh_sach(monkeypatch):
    from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process import runner as tt_runner

    files = [{"name": "tk.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,eA=="}, _portrait()]

    async def fake_ocr(ocr_files):
        return [{"name": f["name"], "text": TO_KHAI if f["name"] == "tk.pdf" else ""} for f in ocr_files]

    async def fake_run(files_by_role, **kwargs):
        await kwargs["ocr_fn"](tt_runner.runner.flatten(files_by_role))
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()], "errors": [], "extracted": {}}

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tt_runner.runner, "run", fake_run)
    res = asyncio.run(tt_runner.run({"": files}, {}))
    assert res["fields"][0]["name"] == "filename46" and res["fields"][0]["comp"] == "bca-photo"
    assert mapper.PHOTO_WARNING not in res["errors"] and mapper.PASSPORT_PAGE_WARNING in res["errors"]
    assert any("Đã gắn ảnh 'IMG_0001.jpg'" in e for e in res["errors"])
    # Không có ảnh → giữ câu nhắc 2 ô ảnh tải tay như cũ.
    res = asyncio.run(tt_runner.run({"": files[:1]}, {}))
    assert not any(f["name"] == "filename46" for f in res["fields"]) and mapper.PHOTO_WARNING in res["errors"]


def test_email_ocr_dinh_dau_phay_lam_sach_moi_thu_tuc_bo_cong_an():
    # Chạy thật 19/11: ô Email liên hệ ra "lethihoa,0615@example.com" (OCR đọc dấu chấm thành dấu phẩy). User: mọi thủ tục
    # Bộ Công an có ô email đều phải ra đúng khuôn.
    import importlib

    from app.pipelines._shared.formatting import clean_email

    by = _by(_enrich({**HO_SO, "ToKhai_Email": "lethihoa,0615@example.com",
                      "ToKhai_BaoLanh_Email": "Email: le thi hoa @ gmail,com"})[0])
    assert by["CongDan_email"] == "lethihoa.0615@example.com"
    assert by["CongDan__fs_BCAEmailBaoLanh"] == "lethihoa@gmail.com"
    cases = {
        "abc@gmailcom": "abc@gmail.com", "abc@gmai.com": "abc@gmail.com", "abc@gmail.con": "abc@gmail.com",
        ".an..binh,@gmail.com": "an.binh@gmail.com", "đặng.văn@yahoo.com.vn": "dang.van@yahoo.com.vn",
        "a@mail.com": "a@mail.com", "a@ymail.com": "a@ymail.com", "lan_anh@outlook. com": "lan_anh@outlook.com",
        "không có": None, "a@b@c.com": None, None: None,
    }
    for raw, want in cases.items():
        assert clean_email(raw) == want, raw
    for folder in ("dang_ky_tam_tru", "dang_ky_thuong_tru", "dieu_chinh_thong_tin_ve_cu_tru",
                   "xac_nhan_thong_tin_ve_cu_tru", "cap_doi_the_can_cuoc", "cap_the_can_cuoc_duoi_14_tuoi",
                   "cap_the_can_cuoc_tu_du_14_tuoi", "dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc",
                   "dang_ky_mau_con_dau", "cap_ho_chieu_pho_thong_o_trong_nuoc",
                   "trinh_bao_mat_ho_chieu_pho_thong_cap_xa", "cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam",
                   "cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam"):
        module = importlib.import_module(f"app.pipelines.{folder}.process.mapper")
        assert module._email("lethihoa,0615@gmail,com") == "lethihoa.0615@gmail.com", folder


def test_co_quan_tiep_nhan_chon_muc_that_dau_tien_ca_ba_thu_tuc():
    # Ảnh chạy thật 19/11: ô "Cơ quan tiếp nhận" chỉ có "-- Chưa chọn --" + cơ quan đã chọn ở bước chọn trường hợp (tên đổi
    # theo tỉnh). User: "luôn chọn cái ở dưới" → phát ô với cờ firstOption, extension chọn mục thật đầu tiên.
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process import mapper as ho_chieu
    from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.process import mapper as the_tam_tru

    agency = [f for f in _enrich(HO_SO)[0] if f["name"] == "CongDan__fs_BCANoiNopHS"]
    assert agency == [ho_chieu.agency_field()]
    assert agency[0]["comp"] == "dom-select" and agency[0]["firstOption"] is True
    assert agency[0]["firstOptionLabel"] == "Cơ quan tiếp nhận"
    out, _ = the_tam_tru.enrich([{"name": "ToKhai_HoTen", "value": "KIM MIN SU"}], {})
    assert out[-1] == ho_chieu.agency_field()
    out, _ = ho_chieu.enrich([{"name": "ToKhai_Ho", "value": "NGUYỄN"}, {"name": "ToKhai_ChuDemTen", "value": "VĂN AN"}], {})
    assert out and out[-1] == ho_chieu.agency_field()
    # Không đọc được gì (out rỗng) → không phát riêng ô cơ quan.
    assert thi_thuc_empty() == []


def thi_thuc_empty():
    return mapper.enrich([], {})[0]


def test_tro_ly_co_o_anh_chan_dung():
    from app.channels.handfree import procedure_registry as hf

    docs = {d["key"]: d for d in hf.get_procedure(KEY)["requiredDocs"]}
    assert docs["anh_chan_dung"]["sides"] == 1 and not docs["anh_chan_dung"].get("optional")
    assert "Ảnh chân dung 4x6" in hf.get_procedure(KEY)["uploadHint"]
