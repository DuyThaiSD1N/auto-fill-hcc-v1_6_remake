"""Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp xã) 1.010386 (Cổng DVC Bộ Công an): mapper ô form + đính kèm +
nối registry / link kê khai + trợ lý người dân."""
import asyncio
import base64
import json

from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_xa.process import mapper
from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_xa.process.schema import ALLOWED, COMPACT_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "trinh-bao-mat-ho-chieu-pho-thong-cap-xa"
LY_DO = ("Năm 2023 tôi được cấp một cuốn hộ chiếu, chưa dùng lần nào nên cất trong tủ cùng giấy tờ khác của gia đình.\n"
         "Đến ngày 02/11/2026 cần dùng thì tìm không thấy nữa. Nay tôi làm đơn trình báo để xin cấp lại hộ chiếu.")
# Hồ sơ mẫu bịa cùng khuôn bộ mẫu 19/11: đơn TK05 (xã viết hoa lẫn thường, không nhớ ngày cấp hộ chiếu) + tờ khai TK01
# (ngày cấp số định danh) — không có ảnh thẻ căn cước.
HO_SO = {
    "DonTrinhBao_KinhGui": "Công an xã Tà Tổng",
    "DonTrinhBao_Ho": "VÀNG", "DonTrinhBao_ChuDemTen": "A SÚA", "DonTrinhBao_SoDinhDanh": "0120 9000 0099",
    "DonTrinhBao_NoiCuTru": {"tinh": "tỉnh Lai Châu", "xa": "XÃ TÀ Tổng", "chiTietDuoiXa": "Bản Nậm Ngà"},
    "DonTrinhBao_DienThoai": "0912.000.111",
    "DonTrinhBao_CoQuanCapHoChieu": "Cục quản lý XNC",
    "DonTrinhBao_NgayMat": "02/11/2026",
    "DonTrinhBao_LyDo": LY_DO,
    "ToKhai_Ho": "VÀNG", "ToKhai_ChuDemTen": "A SÚA", "ToKhai_SoDinhDanh": "012090000099", "ToKhai_NgayCap": "15/08/2022",
    "ToKhai_DienThoai": "0912000222",
    "ToKhai_ThuongTru": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Tà Tổng", "chiTietDuoiXa": "Bản Nậm Ngà"},
    "ToKhai_NoiDungDeNghi": "Cấp lại hộ chiếu do bị mất.",
}


def _enrich(values: dict, options: dict | None = None):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options or {})


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_dien_dung_mapping_bo_mau():
    out, warnings = _enrich(HO_SO)
    assert _by(out) == {
        "CongDan__fsNgayCapCMND": "15/08/2022",  # đơn TK05 không có → tờ khai TK01 mục 4
        "CongDan__fsNoiCapCMND": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",  # CCCD 12 số cấp 2022 → suy
        "CongDan_diDong": "0912000111",  # đơn trước tờ khai
        "CongDan__fs_BCATinhTamTru": "Tỉnh Lai Châu",
        "CongDan__fs_BCAXaTamTru": "Xã Tà Tổng",  # "XÃ TÀ Tổng" viết lẫn hoa → chuẩn như danh mục
        "CongDan__fs_BCADiaChiTamTru": "Bản Nậm Ngà",
        "CongDan__fs_BCACoQuanCap": "Cục quản lý XNC",
        "CongDan__fs_BCAThoiGianMatHC": "02/11/2026",
        # Nguyên văn mục 9, chỉ nối dòng xuống theo khổ giấy.
        "CongDan__fs_BCALyDoMatHC": " ".join(LY_DO.split()),
    }
    by_comp = {f["name"]: f for f in out}
    assert by_comp["CongDan__fs_BCAXaTamTru"]["comp"] == "dom-select" and by_comp["CongDan__fs_BCAXaTamTru"]["waitMs"]
    assert by_comp["CongDan__fs_BCALyDoMatHC"]["comp"] == "dom-input"
    # Ô khoá theo VNeID + khối nơi tiếp nhận không phát.
    for name in ("CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_ngaySinhCongDan", "CongDan__fs_BCAGioiTinhCd",
                 "CongDan_maTinhThanh", "CongDan_maPhuongXa", "CongDan__fs_BCANoiNopHS"):
        assert name not in by_comp
    assert mapper.EMAIL_WARNING in warnings and mapper.AGENCY_WARNING in warnings
    assert any("không ghi số hộ chiếu bị mất" in w for w in warnings)
    assert not any("Ngày cấp ĐDCN" in w for w in warnings)


def test_cccd_uu_tien_khong_nho_so_va_ly_do_du_phong_to_khai():
    values = {**HO_SO, "DonTrinhBao_SoHoChieu": "không nhớ", "ToKhai_HoChieuCu_So": "C7654321",
              "ToKhai_HoChieuCu_NgayCap": "01/03/2023",
              "Cccd_HoTen": "Vàng A Súa", "Cccd_SoDinhDanh": "012090000099", "Cccd_NgayCap": "20/09/2024",
              "Cccd_NoiCap": "BỘ CÔNG AN / MINISTRY OF PUBLIC SECURITY"}
    values.pop("DonTrinhBao_LyDo")
    by, warnings = (lambda r: (_by(r[0]), r[1]))(_enrich(values))
    assert by["CongDan__fsNgayCapCMND"] == "20/09/2024" and by["CongDan__fsNoiCapCMND"] == "Bộ Công an"
    # Đơn ghi "không nhớ" → không lấy số hộ chiếu gần nhất của tờ khai (có thể là cuốn khác), báo người dùng.
    assert "CongDan__fs_BCASoHoChieu" not in by and mapper.NOT_REMEMBER_WARNING in warnings
    assert "CongDan__fs_BCANgayCapHoChieu" not in by
    # Thiếu mục 9 → tạm lấy nội dung đề nghị tờ khai (ô bắt buộc) kèm nhắc ghi rõ hoàn cảnh.
    assert by["CongDan__fs_BCALyDoMatHC"] == "Cấp lại hộ chiếu do bị mất."
    assert any("tạm lấy nội dung đề nghị của tờ khai" in w for w in warnings)

    # Đơn để trống số → dùng mục 13 tờ khai cùng ngày cấp.
    values.pop("DonTrinhBao_SoHoChieu")
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCASoHoChieu"] == "C7654321" and by["CongDan__fs_BCANgayCapHoChieu"] == "01/03/2023"
    # Đơn ghi số khác tờ khai → theo đơn, ngày cấp tờ khai (của cuốn khác) không dùng.
    out, warnings = _enrich({**values, "DonTrinhBao_SoHoChieu": "C1112223"})
    by = _by(out)
    assert by["CongDan__fs_BCASoHoChieu"] == "C1112223" and "CongDan__fs_BCANgayCapHoChieu" not in by
    assert any("khác số hộ chiếu gần nhất ở tờ khai" in w for w in warnings)


def test_the_cua_nguoi_khac_bo_qua_va_kinh_gui_cap_tinh():
    values = {**HO_SO, "Cccd_HoTen": "LÒ THỊ MAI", "Cccd_SoDinhDanh": "012190000001", "Cccd_NgayCap": "01/01/2025",
              "DonTrinhBao_KinhGui": "PHÒNG QUẢN LÝ XUẤT NHẬP CẢNH LAI CHÂU"}
    out, warnings = _enrich(values)
    assert _by(out)["CongDan__fsNgayCapCMND"] == "15/08/2022"
    assert any("không phải của người trình báo" in w for w in warnings)
    assert any("(cấp tỉnh)" in w and "1.001445" in w for w in warnings)
    # Không có giấy nào ghi ngày cấp → nhắc nhập tay; dữ liệu địa chỉ dự phòng theo thẻ căn cước.
    bare = {"Cccd_HoTen": "Vàng A Súa", "Cccd_SoDinhDanh": "012090000099",
            "Cccd_NoiThuongTru": {"tinh": "Lai Châu", "xa": "Xã Tà Tổng", "chiTietDuoiXa": "Bản Nậm Ngà"}}
    out, warnings = _enrich(bare)
    by = _by(out)
    assert by["CongDan__fs_BCATinhTamTru"] == "Tỉnh Lai Châu" and by["CongDan__fs_BCADiaChiTamTru"] == "Bản Nậm Ngà"
    assert any("Ngày cấp ĐDCN/CMND" in w for w in warnings)


def test_tai_khoan_khac_nguoi_tren_giay_khong_chan_nhung_bo_ngay_noi_cap():
    other = {"formContext": {"applicantFullname": "VÀNG A PÁO", "applicantIdentityNumber": "012070000001"}}
    out, warnings = _enrich(HO_SO, other)
    by = _by(out)
    # Cha / mẹ khai thay cho con: vẫn điền thông tin trình báo, chỉ bỏ ngày cấp / nơi cấp CCCD của người khác.
    assert "CongDan__fsNgayCapCMND" not in by and "CongDan__fsNoiCapCMND" not in by
    assert by["CongDan__fs_BCALyDoMatHC"] and by["CongDan__fs_BCAXaTamTru"] == "Xã Tà Tổng"
    assert any(w.startswith("Giấy tờ ghi người trình báo là VÀNG A SÚA, còn tài khoản VNeID đang đăng nhập là của "
                            "VÀNG A PÁO") for w in warnings)
    # Đúng chủ tài khoản (số trùng) → điền đủ; lệch số nhưng trùng tên (OCR) → cũng không cảnh báo.
    for context in ({"applicantFullname": "Vàng A Súa", "applicantIdentityNumber": "012090000099"},
                    {"applicantFullname": "VÀNG A SÚA", "applicantIdentityNumber": "012090000098"}):
        out, warnings = _enrich(HO_SO, {"formContext": context})
        assert "CongDan__fsNgayCapCMND" in _by(out)
        assert not any("tài khoản VNeID" in w for w in warnings)


def test_ocr_du_phong_muc_8_9_va_so_ho_chieu():
    ocr = ("Mẫu TK05\nĐƠN TRÌNH BÁO MẤT HỘ CHIẾU PHỔ THÔNG\nKính gửi: Công an xã Tà Tổng\n"
           "7. Thông tin về hộ chiếu bị mất:\nSố hộ chiếu: C 2223334 ngày cấp ……/……/……\n"
           "8. Hộ chiếu trên đã bị mất vào hồi …… giờ ……. phút, ngày 02/11/2026\n"
           "9. Hoàn cảnh và lý do cụ thể bị mất hộ chiếu:\nĐi chợ phiên bị rơi túi xách\ncó hộ chiếu bên trong.\n"
           "Làm tại Lai Châu, ngày 3 tháng 11 năm 2026\nNgười trình báo")
    fields = mapper.ocr_fallback([{"name": "DonTrinhBao_Ho", "value": "VÀNG"}], [{"text": ocr}])
    assert fields["DonTrinhBao_LyDo"] == "Đi chợ phiên bị rơi túi xách có hộ chiếu bên trong."
    assert fields["DonTrinhBao_NgayMat"] == "02/11/2026" and fields["DonTrinhBao_SoHoChieu"] == "C2223334"
    # LLM đã đọc → giữ của LLM; giấy không phải đơn trình báo → không dò.
    kept = mapper.ocr_fallback({"DonTrinhBao_LyDo": "Bị mất cắp"}, [{"text": ocr}])
    assert kept["DonTrinhBao_LyDo"] == "Bị mất cắp"
    assert mapper.ocr_fallback({}, [{"text": "TỜ KHAI\n9. Hoàn cảnh và lý do cụ thể bị mất hộ chiếu: x"}]) == {}


def test_schema_registry_link_va_detect():
    assert {"DonTrinhBao_LyDo", "DonTrinhBao_NgayMat", "ToKhai_NgayCap", "Cccd_NoiCap"} <= ALLOWED
    assert COMPACT_COMP_BY_NAME["DonTrinhBao_NoiCuTru"] == "x-select-area"
    assert COMPACT_COMP_BY_NAME["DonTrinhBao_NgayMat"] == "x-date"
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"] and proc["detect"]["codeOnPage"] is True
    # Trang trình báo cũng có chữ "hộ chiếu phổ thông" (dòng đơn TK05) → cụm của thủ tục này phải dài hơn cụm của hộ
    # chiếu 1.001456 để bước textPriority của extension chọn đúng.
    ho_chieu = registry.get_procedure("cap-ho-chieu-pho-thong-o-trong-nuoc")["detect"]["textIncludes"]
    assert sum(map(len, proc["detect"]["textIncludes"])) > sum(map(len, ho_chieu))
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.010386" and link["label"] == proc["label"]
    assert link["needsAgencySelect"] is False and link["directSubmit"] is True and link["bcaSubmit"] is True
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert "matthc=1.010386" in public["detect"]["urlIncludes"]


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
    assert proc["requiresCapability"] == "supportsBcaThiThuc" and proc["bcaTthcCode"] == "1.010386"
    assert proc["keKhaiUrl"] == next(item for item in KE_KHAI_LINKS if item["key"] == KEY)["url"]
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    assert hf.get_attach_pipeline(KEY) is registry.get_attach_pipeline(KEY) and "provinceOnly" not in proc
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert KEY in PROCEDURE_HINTS and KEY in PROCEDURE_HMONG

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
    page = lambda payload: flow._handle_guide_login(conv, Intent("event", "page_status", payload))  # noqa: E731
    assert page({"loggedIn": True, "agencyBlock": True, "formKind": ""}).actions == [
        {"type": "select_agency", "direct": True, "province": "", "ward": ""}]
    flow._handle_guide_login(conv, Intent("event", "agency_selected", {}))
    r = page({"loggedIn": True, "bcaTthcPage": True, "bcaTthcCode": "1.010386"})
    assert r.actions == [{"type": "bca_tthc_submit", "code": "1.010386"}]


def test_tro_ly_tu_chon_tinh_thanh_pho_o_trang_chon_truong_hop():
    # Ảnh 19/11: trang "Chọn trường hợp hồ sơ" chỉ có ô "Tỉnh/Thành phố" (option "Công an Tỉnh …"). User: trợ lý tự chọn
    # theo tỉnh như hộ chiếu, không bày dãy nút tỉnh cho công dân bấm.
    caps = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
    conv = {"_id": "c1", "state": "greet", "procedure_key": None, "client_capabilities": caps,
            "auth_user": {"tinh": "Khánh Hòa", "province_slug": "khanhhoa"},
            "location": {"province": "Tỉnh Khánh Hòa", "province_slug": "khanhhoa", "ward": "Phường Nam Nha Trang"}}
    flow._to_confirm_procedure(conv, KEY)
    flow._start_guide_login(conv)
    turn = lambda kind, value, payload=None: asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))  # noqa: E731
    r = turn("event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}],
                          "presets": [{"label": "Tỉnh/Thành phố", "match": "khanh hoa", "prefer": "cong an"}]}]
    province = {"name": "maCoQuan", "present": True, "value": "Công an Tỉnh Khánh Hòa",
                "options": ["Công an Tỉnh Nghệ An", "Công an Tỉnh Khánh Hòa"], "fixed": False,
                "label": "Tỉnh/Thành phố", "required": True}
    r = turn("action", "lc_result_report", {"groups": [province], "prepared": ["preset:maCoQuan"]})
    assert "Tôi đã chọn sẵn **Tỉnh/Thành phố**: **Công an Tỉnh Khánh Hòa**" in r.display_md
    rows = {row["name"]: row for row in r.cards[0]["rows"]} if r.cards else {}
    assert not rows or rows["maCoQuan"]["options"] == []  # không bày dãy nút tỉnh


# ── Đính kèm: bảng Thành phần hồ sơ 1 dòng (đơn TK05) ──
from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_xa.attach import planner as attach_planner  # noqa: E402
from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_xa.attach.dinh_kem_khong_tach import (  # noqa: E402
    planner as whole_planner,
)
from app.process.schemas import FileItem  # noqa: E402
from app.services import ocr as ocr_service  # noqa: E402
from app.services.llm import client as llm_client  # noqa: E402

DON = ("Mẫu TK05\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN TRÌNH BÁO MẤT HỘ CHIẾU PHỔ THÔNG\nKính gửi: Công an xã Tà Tổng\n"
       "1. Họ VÀNG Chữ đệm và tên A SÚA\n9. Hoàn cảnh và lý do cụ thể bị mất hộ chiếu: đánh rơi")
TO_KHAI = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI\n(Dùng cho công dân Việt Nam đề nghị cấp hộ chiếu phổ thông ở "
           "trong nước)\n1. Họ VÀNG Chữ đệm và tên A SÚA\n14. Nội dung đề nghị: Cấp lại hộ chiếu do bị mất.")
CCCD = "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố / No.: 012090000099\nHọ và tên / Full name: VÀNG A SÚA"
ROW = ["don trinh bao mat ho chieu pho thong"]


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


def test_dinh_kem_khong_tach_chi_don_trinh_bao_vao_dong_1(monkeypatch):
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
    assert row["fileIndex"] == 1 and row["slotIndex"] == 0 and row["target"] == "fixed-slot"
    assert row["slotKeywords"] == ROW and row["tickRow"] is True and "sourceFileIndexes" not in row
    note = next(e for e in result["errors"] if e.startswith("Chưa đính kèm"))
    assert "to-khai.pdf" in note and "cccd.pdf" in note


def test_dinh_kem_luat_tieu_de_khi_llm_hong_va_thieu_don(monkeypatch):
    files = [_file("a.pdf"), _file("b.pdf")]
    _mock_io(monkeypatch, {"a.pdf": TO_KHAI, "b.pdf": DON}, "không phải JSON")  # LLM hỏng → luật theo tiêu đề
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    assert [a["fileIndex"] for a in result["attachments"]] == [1]
    # Không có đơn: tệp không rõ loại vẫn đính vào dòng bắt buộc kèm cảnh báo; chỉ có tờ khai → dòng trống, cảnh báo.
    files = [_file("scan.pdf"), _file("tk.pdf"), _file("to.pdf", 7 * 1024 * 1024)]
    _mock_io(monkeypatch, {"scan.pdf": "ảnh mờ không đọc được", "tk.pdf": TO_KHAI}, "{}")
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    assert [a["fileIndex"] for a in result["attachments"]] == [0]
    assert any("Không nhận ra đơn trình báo" in e and "'scan.pdf'" in e for e in result["errors"])
    assert any("vượt giới hạn 6 MB" in e for e in result["errors"])
    _mock_io(monkeypatch, {"tk.pdf": TO_KHAI}, "{}")
    result = asyncio.run(whole_planner.plan([_file("tk.pdf")], {}, {}))
    assert result["attachments"] == []
    assert any("Hồ sơ chưa có đơn trình báo mất hộ chiếu" in e for e in result["errors"])


def test_dinh_kem_tach_dung_dong_khong_sot_trang(monkeypatch):
    # Một PDF gộp: tờ khai (1 trang) + đơn trình báo (2 trang) + CCCD + trang trắng.
    files = [_file("ho-so.pdf")]
    texts = {"ho-so.pdf": _pdf_text(TO_KHAI, DON, "Người trình báo\nVÀNG A SÚA", CCCD, "~ . ~")}
    llm = json.dumps({
        "tep": [{"fileIndex": 0, "tieuDeTrang": ["Tờ khai đề nghị cấp hộ chiếu", "Đơn trình báo mất hộ chiếu phổ thông",
                                                  "", "Căn cước công dân", ""]}],
        "documents": [
            {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai"},
            {"fileIndex": 0, "pages": [2, 3], "docType": "trinh_bao_mat", "documentName": "Đơn trình báo"},
            {"fileIndex": 0, "pages": [4], "docType": "identity", "documentName": "Căn cước công dân"},
            {"fileIndex": 0, "pages": [5], "docType": "blank_page", "documentName": ""},
        ],
    })
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["extracted"]["attachmentMode"] == "split"
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}]
    # Không sót trang có chữ: trang của đơn vào dòng, tờ khai + CCCD được kê trong câu "Chưa đính kèm"; trang 5 không có
    # chữ là trang trắng → bỏ (khung chia trang dùng chung).
    segments = {tuple(s["pages"]) if isinstance(s["pages"], list) else s["pages"]: s["docType"]
                for s in result["extracted"]["segments"]}
    assert segments == {(1,): "to_khai", (2, 3): "trinh_bao_mat", (4,): "identity"}
    note = next(e for e in result["errors"] if e.startswith("Chưa đính kèm"))
    assert "(trang 1)" in note and "(trang 4)" in note


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
