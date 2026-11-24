"""Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp tỉnh) 1.001445 (Cổng DVC Bộ Công an): mapper ô form + đính kèm 2
dòng + nối registry / link kê khai + trợ lý người dân."""
import asyncio
import base64
import json

from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_tinh.process import mapper
from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_tinh.process.schema import ALLOWED, COMPACT_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "trinh-bao-mat-ho-chieu-pho-thong-cap-tinh"
LY_DO = ("Năm 2022 tôi được cấp hộ chiếu, chưa đi đâu nên cất trong tủ cùng giấy tờ khác của gia đình.\n"
         "Đến ngày 03/11/2026 cần dùng thì tìm không thấy nữa. Nay tôi làm đơn trình báo để xin cấp lại hộ chiếu.")
# Hồ sơ bịa cùng khuôn bộ mẫu 20/11: đơn TK05 kính gửi Phòng QLXNC tỉnh (xã viết hoa lẫn thường, không ghi số / ngày cấp
# hộ chiếu) + tờ khai TK01 (ngày cấp số định danh) — không có ảnh thẻ căn cước.
HO_SO = {
    "DonTrinhBao_KinhGui": "PHÒNG QUẢN LÝ XUẤT NHẬP CẢNH LAI CHÂU",
    "DonTrinhBao_Ho": "LÊ", "DonTrinhBao_ChuDemTen": "VĂN AN", "DonTrinhBao_SoDinhDanh": "0120 8500 0123",
    "DonTrinhBao_NoiCuTru": {"tinh": "tỉnh Lai Châu", "xa": "XÃ TÀ Tổng", "chiTietDuoiXa": "Bản Nậm Ngà"},
    "DonTrinhBao_DienThoai": "0912.000.333",
    "DonTrinhBao_CoQuanCapHoChieu": "Cục quản lý XNC",
    "DonTrinhBao_NgayMat": "03/11/2026",
    "DonTrinhBao_LyDo": LY_DO,
    "ToKhai_Ho": "LÊ", "ToKhai_ChuDemTen": "VĂN AN", "ToKhai_SoDinhDanh": "012085000123", "ToKhai_NgayCap": "10/05/2022",
    "ToKhai_DienThoai": "0912000444",
    "ToKhai_ThuongTru": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Tà Tổng", "chiTietDuoiXa": "Bản Nậm Ngà"},
    "ToKhai_NoiDungDeNghi": "Cấp lại hộ chiếu do bị mất.",
}


def _enrich(values: dict, options: dict | None = None):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options or {})


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_dien_dung_mapping_bo_mau():
    out, warnings = _enrich(HO_SO)
    by = _by(out)
    agency = by.pop("CongDan__fs_BCANoiNopHS")
    assert by == {
        "CongDan__fsNgayCapCMND": "10/05/2022",  # đơn TK05 không có → tờ khai TK01 mục 4
        "CongDan__fsNoiCapCMND": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",  # CCCD 12 số cấp 2022 → suy
        "CongDan_diDong": "0912000333",  # đơn trước tờ khai
        "CongDan__fs_BCATinhTamTru": "Tỉnh Lai Châu",
        "CongDan__fs_BCAXaTamTru": "Xã Tà Tổng",  # "XÃ TÀ Tổng" viết lẫn hoa → chuẩn như danh mục
        "CongDan__fs_BCADiaChiTamTru": "Bản Nậm Ngà",
        "CongDan__fs_BCACoQuanCap": "Cục quản lý XNC",
        "CongDan__fs_BCAThoiGianMatHC": "03/11/2026",
        # Nguyên văn mục 9, chỉ nối dòng xuống theo khổ giấy.
        "CongDan__fs_BCALyDoMatHC": " ".join(LY_DO.split()),
    }
    fields = {f["name"]: f for f in out}
    assert fields["CongDan__fs_BCAXaTamTru"]["comp"] == "dom-select" and fields["CongDan__fs_BCAXaTamTru"]["waitMs"]
    assert fields["CongDan__fs_BCALyDoMatHC"]["comp"] == "dom-input"
    # Ô 17 Cơ quan tiếp nhận: chỉ có Phòng QLXNC tỉnh đã chọn ở bước trước → chọn mục thật đầu tiên, phát cuối form.
    assert out[-1]["name"] == "CongDan__fs_BCANoiNopHS" and agency
    assert out[-1]["firstOption"] is True and out[-1]["comp"] == "dom-select"
    # Ô khoá theo VNeID không phát.
    for name in ("CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_ngaySinhCongDan", "CongDan__fs_BCAGioiTinhCd"):
        assert name not in fields
    assert mapper.EMAIL_WARNING in warnings and mapper.AGENCY_WARNING in warnings
    assert any("không ghi số hộ chiếu bị mất" in w for w in warnings)
    # Đơn gửi Phòng QLXNC tỉnh là đúng nơi nộp → không cảnh báo sai cấp.
    assert not any("1.010386" in w for w in warnings)
    assert not any("Ngày cấp ĐDCN" in w for w in warnings)


def test_kinh_gui_cong_an_xa_goi_y_thu_tuc_cap_xa_va_khong_doc_duoc_gi():
    out, warnings = _enrich({**HO_SO, "DonTrinhBao_KinhGui": "Công an xã Tà Tổng"})
    assert any("(Công an cấp xã)" in w and "1.010386" in w for w in warnings)
    # Không đọc được gì → không phát riêng ô Cơ quan tiếp nhận.
    out, _ = _enrich({})
    assert out == []


def test_cccd_uu_tien_khong_nho_so_va_ly_do_du_phong_to_khai():
    values = {**HO_SO, "DonTrinhBao_SoHoChieu": "không nhớ", "ToKhai_HoChieuCu_So": "C7654321",
              "ToKhai_HoChieuCu_NgayCap": "01/03/2022",
              "Cccd_HoTen": "Lê Văn An", "Cccd_SoDinhDanh": "012085000123", "Cccd_NgayCap": "20/09/2024",
              "Cccd_NoiCap": "BỘ CÔNG AN / MINISTRY OF PUBLIC SECURITY"}
    values.pop("DonTrinhBao_LyDo")
    out, warnings = _enrich(values)
    by = _by(out)
    assert by["CongDan__fsNgayCapCMND"] == "20/09/2024" and by["CongDan__fsNoiCapCMND"] == "Bộ Công an"
    # Đơn ghi "không nhớ" → không lấy số hộ chiếu gần nhất của tờ khai (có thể là cuốn khác), báo người dùng.
    assert "CongDan__fs_BCASoHoChieu" not in by and mapper.NOT_REMEMBER_WARNING in warnings
    # Thiếu mục 9 → tạm lấy nội dung đề nghị tờ khai (ô bắt buộc) kèm nhắc ghi rõ hoàn cảnh.
    assert by["CongDan__fs_BCALyDoMatHC"] == "Cấp lại hộ chiếu do bị mất."
    assert any("tạm lấy nội dung đề nghị của tờ khai" in w for w in warnings)
    # Đơn để trống số → dùng mục 13 tờ khai cùng ngày cấp.
    values.pop("DonTrinhBao_SoHoChieu")
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCASoHoChieu"] == "C7654321" and by["CongDan__fs_BCANgayCapHoChieu"] == "01/03/2022"


OTHER_ACCOUNT = {"formContext": {"applicantFullname": "TRẦN VĂN HÙNG", "applicantIdentityNumber": "001204000777"}}


def test_tai_khoan_khac_nguoi_tren_giay_thi_chan_khong_dien():
    # Ảnh chạy thật 20/11: khối Người đề nghị khoá theo VNeID của người khác mà SĐT / địa chỉ vẫn lấy theo giấy → form
    # trộn hai người. User: chặn như hộ chiếu 1.001456, kể cả SĐT và email.
    values = {**HO_SO, "DonTrinhBao_NgaySinh": "01/01/1985", "ToKhai_Email": "levanan@gmail.com"}
    out, warnings = _enrich(values, OTHER_ACCOUNT)
    assert out == [] and len(warnings) == 1
    assert warnings[0].startswith("Chưa điền: giấy tờ tải lên là của LÊ VĂN AN, còn tài khoản VNeID đang đăng nhập là "
                                  "của TRẦN VĂN HÙNG")
    blocked = mapper.account_block(values, OTHER_ACCOUNT)
    assert blocked["code"] == "account_mismatch" and blocked["accountName"] == "TRẦN VĂN HÙNG"
    # Không đọc được ngày sinh → coi như người thành niên, vẫn chặn.
    assert _enrich(HO_SO, OTHER_ACCOUNT)[0] == []
    # Đúng chủ tài khoản (số trùng) → điền đủ cả SĐT, email; lệch số nhưng trùng tên (OCR) → cũng không chặn.
    for context in ({"applicantFullname": "Lê Văn An", "applicantIdentityNumber": "012085000123"},
                    {"applicantFullname": "LÊ VĂN AN", "applicantIdentityNumber": "012085000124"}):
        out, warnings = _enrich(values, {"formContext": context})
        by = _by(out)
        assert by["CongDan_diDong"] == "0912000333" and by["CongDan_email"] == "levanan@gmail.com"
        assert "CongDan__fsNgayCapCMND" in by and not any("tài khoản VNeID" in w for w in warnings)
    # Không đọc được ô khoá trên form → điền như cũ + nhắc đối chiếu.
    out, warnings = _enrich(values)
    assert _by(out)["CongDan_diDong"] == "0912000333" and mapper.NO_ACCOUNT_WARNING in warnings


def test_runner_gan_blocked(monkeypatch):
    from app.pipelines._shared.compact_agent import runner as compact_runner
    from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_tinh.process import runner as tinh_runner

    async def fake_run(*_args, **_kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()]}

    monkeypatch.setattr(compact_runner, "run", fake_run)
    res = asyncio.run(tinh_runner.run({}, OTHER_ACCOUNT))
    assert res["fields"] == [] and res["blocked"]["documentName"] == "LÊ VĂN AN"
    res = asyncio.run(tinh_runner.run({}, {}))
    assert res["fields"] and "blocked" not in res


def test_cha_me_trinh_bao_thay_tre_duoi_14_tuoi():
    # Người trên giấy dưới 14 tuổi → cha / mẹ đăng nhập trình báo thay: điền nơi cư trú + thông tin trình báo; các ô của
    # người đề nghị (ngày cấp / nơi cấp CCCD, SĐT, email) là của chủ tài khoản → bỏ, nhắc nhập tay.
    child = {**HO_SO, "DonTrinhBao_ChuDemTen": "MINH KHANG", "ToKhai_ChuDemTen": "MINH KHANG",
             "DonTrinhBao_NgaySinh": "15/06/2020", "ToKhai_Email": "a@gmail.com"}
    out, warnings = _enrich(child, OTHER_ACCOUNT)
    by = _by(out)
    for name in ("CongDan__fsNgayCapCMND", "CongDan__fsNoiCapCMND", "CongDan_diDong", "CongDan_email"):
        assert name not in by, name
    assert by["CongDan__fs_BCALyDoMatHC"] and by["CongDan__fs_BCAXaTamTru"] == "Xã Tà Tổng"
    assert by["CongDan__fs_BCANoiNopHS"]
    assert any("LÊ MINH KHANG (dưới 14 tuổi)" in w and "TRẦN VĂN HÙNG" in w and "Số điện thoại" in w for w in warnings)
    assert mapper.account_block(child, OTHER_ACCOUNT) is None


def test_the_cua_nguoi_khac_bo_qua():
    out, warnings = _enrich({**HO_SO, "Cccd_HoTen": "LÒ THỊ MAI", "Cccd_SoDinhDanh": "012190000001",
                             "Cccd_NgayCap": "01/01/2025"})
    assert _by(out)["CongDan__fsNgayCapCMND"] == "10/05/2022"
    assert any("không phải của người trình báo" in w for w in warnings)


def test_ocr_du_phong_muc_8_9_va_so_ho_chieu():
    ocr = ("Mẫu TK05\nĐƠN TRÌNH BÁO MẤT HỘ CHIẾU PHỔ THÔNG\nKính gửi: PHÒNG QUẢN LÝ XUẤT NHẬP CẢNH\n"
           "7. Thông tin về hộ chiếu bị mất:\nSố hộ chiếu: C 2223334 ngày cấp ……/……/……\n"
           "8. Hộ chiếu trên đã bị mất vào hồi …… giờ ……. phút, ngày 03/11/2026\n"
           "9. Hoàn cảnh và lý do cụ thể bị mất hộ chiếu:\nĐi chợ phiên bị rơi túi xách\ncó hộ chiếu bên trong.\n"
           "Làm tại Lai Châu, ngày 4 tháng 11 năm 2026\nNgười trình báo")
    fields = mapper.ocr_fallback([{"name": "DonTrinhBao_Ho", "value": "LÊ"}], [{"text": ocr}])
    assert fields["DonTrinhBao_LyDo"] == "Đi chợ phiên bị rơi túi xách có hộ chiếu bên trong."
    assert fields["DonTrinhBao_NgayMat"] == "03/11/2026" and fields["DonTrinhBao_SoHoChieu"] == "C2223334"
    assert mapper.ocr_fallback({}, [{"text": "TỜ KHAI\n9. Hoàn cảnh và lý do cụ thể bị mất hộ chiếu: x"}]) == {}


def test_muc_7_viet_chen_dau_cham_va_so_khong_theo_khuon():
    # Chạy thật 24/11: mục 7 ghi "....<9 chữ số>.... ngày cấp ...dd/mm/yyyy" + "Cơ quan cấp: Cục quản lý XNC" mà LLM bỏ
    # cả ba field → dự phòng OCR đọc lại trong mục 7, mapper nhận số đúng như người viết ghi.
    ocr = ("Mẫu TK05\nĐƠN TRÌNH BÁO MẤT HỘ CHIẾU PHỔ THÔNG\n4. Số định danh cá nhân:\n| 0 | 1 | 2 |\n"
           "7. Thông tin về hộ chiếu bị mất(4):\nSố hộ chiếu: ....012345678.... ngày cấp ...15/06/2023\n"
           "Cơ quan cấp: Cục quản lý XNC\n8. Hộ chiếu trên đã bị mất vào hồi ....9... giờ ...10.... phút, ngày "
           "03/11/2026\n9. Hoàn cảnh và lý do cụ thể bị mất hộ chiếu:\nĐể quên trên xe khách.\nLàm tại Lai Châu")
    fields = mapper.ocr_fallback([{"name": "DonTrinhBao_Ho", "value": "LÊ"}], [{"text": ocr}])
    assert fields["DonTrinhBao_SoHoChieu"] == "012345678"
    assert fields["DonTrinhBao_NgayCapHoChieu"] == "15/06/2023"
    assert fields["DonTrinhBao_CoQuanCapHoChieu"] == "Cục quản lý XNC"
    by = _by(_enrich({**HO_SO, **{k: fields[k] for k in fields if k.startswith("DonTrinhBao_") and "HoChieu" in k}})[0])
    assert by["CongDan__fs_BCASoHoChieu"] == "012345678"
    assert by["CongDan__fs_BCANgayCapHoChieu"] == "15/06/2023"
    assert by["CongDan__fs_BCACoQuanCap"] == "Cục quản lý XNC"
    # LLM trả nguyên chuỗi kẹp dấu chấm → mapper bỏ dấu chấm; khuôn chữ + 7 số vẫn qua sửa chữ OCR như cũ.
    by = _by(_enrich({**HO_SO, "DonTrinhBao_SoHoChieu": "....C 1234567....", "DonTrinhBao_NgayCapHoChieu": "...15/06/2023",
                      "DonTrinhBao_CoQuanCapHoChieu": "Cục Quản lý xuất nhập cảnh ...."})[0])
    assert by["CongDan__fs_BCASoHoChieu"] == "C1234567" and by["CongDan__fs_BCANgayCapHoChieu"] == "15/06/2023"
    assert by["CongDan__fs_BCACoQuanCap"] == "Cục Quản lý xuất nhập cảnh"
    # Mục 7 để trống → không bịa; "ngày cấp" ngoài mục 7 (của CCCD) không lấy làm ngày cấp hộ chiếu.
    blank = ("ĐƠN TRÌNH BÁO MẤT HỘ CHIẾU PHỔ THÔNG\n4. Số ĐDCN: 012085000123 Ngày cấp: 10/05/2022\n"
             "7. Thông tin về hộ chiếu bị mất:\nSố hộ chiếu: ………… ngày cấp ……/……/……\nCơ quan cấp: ……………\n"
             "8. Hộ chiếu trên đã bị mất vào hồi …… giờ …… phút, ngày 03/11/2026")
    fields = mapper.ocr_fallback({}, [{"text": blank}])
    assert not {"DonTrinhBao_SoHoChieu", "DonTrinhBao_NgayCapHoChieu", "DonTrinhBao_CoQuanCapHoChieu"} & set(fields)


def test_schema_registry_link_va_detect():
    assert {"DonTrinhBao_LyDo", "DonTrinhBao_NgayMat", "ToKhai_NgayCap", "Cccd_NoiCap"} <= ALLOWED
    assert COMPACT_COMP_BY_NAME["DonTrinhBao_NoiCuTru"] == "x-select-area"
    assert COMPACT_COMP_BY_NAME["DonTrinhBao_NgayMat"] == "x-date"
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    # Pipeline RIÊNG, không dùng chung bản cấp xã (user 20/11).
    assert registry.get_pipeline(KEY) is not registry.get_pipeline("trinh-bao-mat-ho-chieu-pho-thong-cap-xa")
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"] and proc["detect"]["codeOnPage"] is True
    assert proc["collectFormContext"] is True
    # Form trùng ô với bản cấp xã: trang cấp tỉnh khớp cả hai → cụm của bản cấp tỉnh phải dài hơn (bước textPriority) và
    # chứa đủ cụm cấp xã; cụm thêm của dòng người đại diện thì trang cấp xã không có.
    cap_xa = registry.get_procedure("trinh-bao-mat-ho-chieu-pho-thong-cap-xa")["detect"]["textIncludes"]
    assert set(cap_xa) < set(proc["detect"]["textIncludes"])
    assert sum(map(len, proc["detect"]["textIncludes"])) > sum(map(len, cap_xa))
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.001445" and link["label"] == proc["label"]
    assert link["needsAgencySelect"] is False and link["directSubmit"] is True and link["bcaSubmit"] is True
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert "matthc=1.001445" in public["detect"]["urlIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaThiThuc": True}


def test_tro_ly_cung_key_hien_moi_tinh_nop_thang_nhu_auto_fill():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    proc = hf.get_procedure(KEY)
    assert proc["detect"] == registry.get_procedure(KEY)["detect"] and proc["label"] == registry.get_procedure(KEY)["label"]
    assert proc["requiresCapability"] == "supportsBcaThiThuc" and proc["bcaTthcCode"] == "1.001445"
    assert proc["keKhaiUrl"] == next(item for item in KE_KHAI_LINKS if item["key"] == KEY)["url"]
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    assert hf.get_attach_pipeline(KEY) is registry.get_attach_pipeline(KEY) and "provinceOnly" not in proc
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert KEY in PROCEDURE_HINTS and KEY in PROCEDURE_HMONG

    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == proc["keKhaiUrl"]
    page = lambda payload: flow._handle_guide_login(conv, Intent("event", "page_status", payload))  # noqa: E731
    assert page({"loggedIn": True, "agencyBlock": True, "formKind": ""}).actions == [
        {"type": "select_agency", "direct": True, "province": "", "ward": ""}]
    flow._handle_guide_login(conv, Intent("event", "agency_selected", {}))
    r = page({"loggedIn": True, "bcaTthcPage": True, "bcaTthcCode": "1.001445"})
    assert r.actions == [{"type": "bca_tthc_submit", "code": "1.001445"}]


# ── Đính kèm: bảng Thành phần hồ sơ 2 dòng (người đại diện / đơn TK05 + tờ khai) ──
from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_tinh.attach import planner as attach_planner  # noqa: E402
from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_tinh.attach.dinh_kem_khong_tach import (  # noqa: E402
    planner as whole_planner,
)
from app.process.schemas import FileItem  # noqa: E402
from app.services import ocr as ocr_service  # noqa: E402
from app.services.llm import client as llm_client  # noqa: E402

DON = ("Mẫu TK05\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN TRÌNH BÁO MẤT HỘ CHIẾU PHỔ THÔNG\nKính gửi: PHÒNG QUẢN LÝ "
       "XUẤT NHẬP CẢNH\n1. Họ LÊ Chữ đệm và tên VĂN AN\n9. Hoàn cảnh và lý do cụ thể bị mất hộ chiếu: đánh rơi")
TO_KHAI = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI\n(Dùng cho công dân Việt Nam đề nghị cấp hộ chiếu phổ thông ở "
           "trong nước)\n1. Họ LÊ Chữ đệm và tên VĂN AN\n14. Nội dung đề nghị: Cấp lại hộ chiếu do bị mất.")
CCCD = "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố / No.: 012085000123\nHọ và tên / Full name: LÊ VĂN AN"
KHAI_SINH = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY KHAI SINH\nHọ, chữ đệm, tên: LÊ MINH KHANG"
ROW1 = ["giay to chung minh la cha"]
ROW2 = ["don trinh bao mat ho chieu"]


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


def test_dinh_kem_khong_tach_don_va_to_khai_chung_dong_2(monkeypatch):
    # Ảnh ánh xạ 20/11: TK05.jpg tệp chính dòng 2, TK01.pdf đính chung; dòng 1 không áp dụng; CCCD không đính.
    files = [_file("to-khai.pdf"), _file("don.jpg"), _file("cccd.pdf")]
    texts = {"to-khai.pdf": TO_KHAI, "don.jpg": DON, "cccd.pdf": CCCD}
    llm = json.dumps({"documents": [{"index": 0, "docType": "to_khai", "documentName": ""},
                                    {"index": 1, "docType": "trinh_bao_mat", "documentName": ""},
                                    {"index": 2, "docType": "identity", "documentName": ""}]})
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": False}, {}))
    assert result["extracted"]["attachmentMode"] == "whole"
    assert len(result["attachments"]) == 1
    row = result["attachments"][0]
    assert row["slotIndex"] == 1 and row["target"] == "fixed-slot" and row["slotKeywords"] == ROW2
    assert row["fileIndex"] == 1 and row["sourceFileIndexes"] == [1, 0]  # đơn trước, tờ khai sau
    assert row["tickRow"] is True
    assert any("đính kèm chung 2 giấy" in e for e in result["errors"])
    note = next(e for e in result["errors"] if e.startswith("Chưa đính kèm"))
    assert "cccd.pdf" in note and "to-khai.pdf" not in note


def test_dinh_kem_nguoi_dai_dien_dong_1_va_luat_tieu_de(monkeypatch):
    files = [_file("don.pdf"), _file("khai-sinh.pdf")]
    _mock_io(monkeypatch, {"don.pdf": DON, "khai-sinh.pdf": KHAI_SINH}, "không phải JSON")  # LLM hỏng → luật tiêu đề
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    rows = {a["slotIndex"]: a for a in result["attachments"]}
    assert rows[0]["fileIndex"] == 1 and rows[0]["slotKeywords"] == ROW1
    assert rows[1]["fileIndex"] == 0 and rows[1]["slotKeywords"] == ROW2


def test_dinh_kem_thieu_don(monkeypatch):
    # Không nhận ra đơn: tệp không rõ loại vẫn đính vào dòng bắt buộc kèm cảnh báo; tệp quá 6 MB bị loại.
    files = [_file("scan.pdf"), _file("tk.pdf"), _file("to.pdf", 7 * 1024 * 1024)]
    _mock_io(monkeypatch, {"scan.pdf": "ảnh mờ không đọc được", "tk.pdf": TO_KHAI}, "{}")
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    assert [(a["slotIndex"], a["fileIndex"]) for a in result["attachments"]] == [(1, 0)]
    assert result["attachments"][0]["sourceFileIndexes"] == [0, 1]
    assert any("Không nhận ra đơn trình báo" in e and "'scan.pdf'" in e for e in result["errors"])
    assert any("vượt giới hạn 6 MB" in e for e in result["errors"])
    # Chỉ có tờ khai → không đính tờ khai thay đơn, dòng trống + cảnh báo.
    _mock_io(monkeypatch, {"tk.pdf": TO_KHAI}, "{}")
    result = asyncio.run(whole_planner.plan([_file("tk.pdf")], {}, {}))
    assert result["attachments"] == []
    assert any("Hồ sơ chưa có đơn trình báo mất hộ chiếu" in e for e in result["errors"])


def test_dinh_kem_tach_dung_dong_khong_sot_trang(monkeypatch):
    # Một PDF gộp: đơn trình báo (2 trang) + tờ khai (1 trang) + CCCD + trang trắng.
    files = [_file("ho-so.pdf")]
    texts = {"ho-so.pdf": _pdf_text(DON, "Người trình báo\nLÊ VĂN AN", TO_KHAI, CCCD, "~ . ~")}
    llm = json.dumps({
        "tep": [{"fileIndex": 0, "tieuDeTrang": ["Đơn trình báo mất hộ chiếu phổ thông", "",
                                                  "Tờ khai đề nghị cấp hộ chiếu", "Căn cước công dân", ""]}],
        "documents": [
            {"fileIndex": 0, "pages": [1, 2], "docType": "trinh_bao_mat", "documentName": "Đơn trình báo"},
            {"fileIndex": 0, "pages": [3], "docType": "to_khai", "documentName": "Tờ khai"},
            {"fileIndex": 0, "pages": [4], "docType": "identity", "documentName": "Căn cước công dân"},
            {"fileIndex": 0, "pages": [5], "docType": "blank_page", "documentName": ""},
        ],
    })
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["extracted"]["attachmentMode"] == "split"
    assert len(result["attachments"]) == 1
    row = result["attachments"][0]
    assert row["slotIndex"] == 1
    assert row["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 1]}, {"fileIndex": 0, "pageIndexes": [2]}]
    # Không sót trang có chữ: đơn + tờ khai vào dòng 2, CCCD kê trong câu "Chưa đính kèm"; trang 5 trắng → bỏ.
    segments = {tuple(s["pages"]) if isinstance(s["pages"], list) else s["pages"]: s["docType"]
                for s in result["extracted"]["segments"]}
    assert segments == {(1, 2): "trinh_bao_mat", (3,): "to_khai", (4,): "identity"}
    note = next(e for e in result["errors"] if e.startswith("Chưa đính kèm"))
    assert "(trang 4)" in note


def test_dinh_kem_tach_loi_quay_ve_khong_tach(monkeypatch):
    files = [_file("don.pdf"), _file("tk.pdf")]
    texts = {"don.pdf": DON, "tk.pdf": TO_KHAI}

    def broken(_messages):
        raise RuntimeError("LLM sập")

    _mock_io(monkeypatch, texts, broken)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["errors"][0].startswith("attachment_agent (tách)")
    assert result["extracted"]["attachmentMode"] == "whole"
    assert [a["fileIndex"] for a in result["attachments"]] == [0]
    assert not any(a.get("sourceSegments") for a in result["attachments"])
