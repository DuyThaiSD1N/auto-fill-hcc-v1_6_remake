"""Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia (cổng Bộ Xây dựng, 1.002877).

Dữ liệu trong test là dữ liệu giả."""

import asyncio
import base64
import json
import re
import unicodedata

import fitz
import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process.runner import _apply_vision
from app.pipelines.cap_giay_phep_lien_van_viet_lao_campuchia.attach import planner as dieu_phoi
from app.pipelines.cap_giay_phep_lien_van_viet_lao_campuchia.attach.dinh_kem_tach import planner as tach
from app.pipelines.cap_giay_phep_lien_van_viet_lao_campuchia.process import mapper, vision
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.process.schemas import FileItem

KEY = "cap-giay-phep-lien-van-viet-lao-campuchia"
P = "data[panel_caNhanToChuc]"


def _values(**overrides):
    values = {
        "NguoiNop_LoaiDoiTuong": "Tổ chức",
        "NguoiNop_HoTen": "CÔNG TY TNHH MẪU THỬ",
        "NguoiNop_SoDinhDanh": "048090000001",  # CCCD của giám đốc — không phải mã số thuế đơn vị.
        "NguoiNop_NgaySinh": "01/01/1990",
        "NguoiNop_ThuongTru": "Tổ 1 , Khu Mẫu, thị trấn Ái Nghĩa, huyện Đại Lộc, tỉnh Quảng Nam, Việt Nam",
        "NguoiNop_DienThoai": "0900 000 001",
        "DeNghi_DichVu": "ptm_moi",
        "DeNghi_KinhGui": "Sở Xây dựng thành phố Đà Nẵng",
        "DeNghi_Tai": "Đà Nẵng",
        "DeNghi_MucDich": "Mục đích khác",
        "DeNghi_NguoiKy": "GIÁM ĐỐC Nguyễn Văn A",
        "DeNghi_PhuongTien": [{
            "bienSo": "92A-123.45", "trongTai": "5 ghế", "namSanXuat": "2019", "nhanHieu": "MẪU", "soKhung": "KHUNG0001",
            "soMay": "MAY0001", "mauSon": "xanh", "cuaKhau": "Tất cả các cửa khẩu", "tuNgay": "24/11/2026",
            "denNgay": "23/12/2026",
        }],
    }
    values.update(overrides)
    return values


def _run(values):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()])
    return fields, {f["name"]: f["value"] for f in fields}, warnings


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.002877" and link["selectSo"] is True
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    assert proc["supportsSplitDocuments"] is True and proc["hasAttachmentStep"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    assert tach.__name__.split(".")[2] == KEY.replace("-", "_")


def test_to_chuc_dien_theo_giay_de_nghi():
    fields, by_name, warnings = _run(_values())
    assert by_name["data[chonDoiTuong]"] == "Tổ chức"
    assert by_name["data[fullname]"] == "CÔNG TY TNHH MẪU THỬ"
    # Tổ chức: không ngày sinh / giới tính; CCCD giám đốc không vào ô CCCD/CMND/MST → xoá trắng + cảnh báo nhập MST.
    cleared = {f["name"] for f in fields if f.get("clear")}
    assert {"data[birthday]", "data[identityNumber]", "data[identityDate]", "data[email]"} <= cleared
    assert "data[gender]" not in by_name
    assert any("mã số doanh nghiệp" in w for w in warnings)
    # Địa chỉ cũ (Quảng Nam / thị trấn Ái Nghĩa) → địa giới mới.
    assert by_name["data[province]"] == "Thành phố Đà Nẵng"
    assert by_name["data[district]"] == "Xã Đại Lộc"
    assert by_name["data[address]"] == "Tổ 1, Khu Mẫu"
    assert by_name["data[phoneNumber]"] == "0900000001"
    assert by_name[f"{P}[dichVu]"].endswith("phi thương mại [1.002877.B1]")
    assert by_name[f"{P}[T_CoQuan]"] == "Sở Xây dựng TP Đà Nẵng"
    assert by_name[f"{P}[TinTTTe]"] == "Thành phố Đà Nẵng"
    assert by_name[f"{P}[mucdich_04]"] is True
    assert not any(k in by_name for k in (f"{P}[mucdich_01]", f"{P}[mucdich_02]", f"{P}[mucdich_03]"))
    assert by_name[f"{P}[nguoiLamDon]"] == "Nguyễn Văn A"
    vehicle = next(f for f in fields if f["comp"] == "dom-vehicle-add")
    assert vehicle["addButtonName"] == f"{P}[themxe]"
    assert json.loads(vehicle["value"]) == [{
        "bienSo": "92A12345", "trongTai": "5", "namSanXuat": "2019", "nhanHieu": "MẪU", "soKhung": "KHUNG0001",
        "soMay": "MAY0001", "mauSon": "xanh", "cuaKhau": "Tất cả cửa khẩu", "tuNgay": "24/11/2026",
        "denNgay": "23/12/2026",
    }]


def test_to_chuc_co_ma_so_thue_du_thi_dien():
    _, by_name, warnings = _run(_values(NguoiNop_SoDinhDanh="0400000001"))
    assert by_name["data[identityNumber]"] == "0400000001"
    assert not any("mã số doanh nghiệp" in w for w in warnings)


def test_ca_nhan_lay_cccd_va_muc_dich_c():
    _, by_name, _ = _run(_values(
        NguoiNop_LoaiDoiTuong="Cá nhân", NguoiNop_HoTen="NGUYỄN VĂN A", NguoiNop_GioiTinh="Nam",
        NguoiNop_NgayCapCccd="1/7/2021", NguoiNop_NoiCapCccd="BỘ CÔNG AN", DeNghi_NguoiKy="",
        NguoiNop_ThuongTru={"tinh": "Đồng Nai", "xa": "Phường Mẫu", "chiTietDuoiXa": "Số 1 đường Mẫu"},
        DeNghi_MucDich="Phục vụ hoạt động của tổ chức/cá nhân",
    ))
    assert by_name["data[chonDoiTuong]"] == "Cá nhân"
    assert by_name["data[identityNumber]"] == "048090000001"
    assert by_name["data[birthday]"] == "01/01/1990" and by_name["data[identityDate]"] == "01/07/2021"
    assert by_name["data[gender]"] == "Nam"
    assert by_name["data[province]"] == "Thành phố Đồng Nai"
    assert by_name["data[address]"] == "Số 1 đường Mẫu"
    # Nhãn c) có chữ "cá nhân" vẫn phải là checkbox c), không phải b).
    assert by_name[f"{P}[mucdich_03]"] is True and f"{P}[mucdich_02]" not in by_name
    assert by_name[f"{P}[nguoiLamDon]"] == "NGUYỄN VĂN A"


@pytest.mark.parametrize(("raw", "suffix"), [
    ("ptm_moi", "[1.002877.B1]"), ("ptm_huhong", "[1.002877.B2]"), ("ptm_matmat", "[1.002877.B3]"),
    ("ptm_hethan", "[1.002877.B4]"), ("tm_moi", "[1.002877.A1]"), ("tm_hethan", "[1.002877.A2]"),
    ("tm_huhong", "[1.002877.A3]"), ("tm_matmat", "[1.002877.A4]"),
    ("Cấp lại giấy phép cho phương tiện phi thương mại do mất mát", "[1.002877.B3]"),
    ("cấp, cấp lại giấy phép liên vận cho phương tiện thương mại", "[1.002877.A1]"),
    ("1.002877.A3", "[1.002877.A3]"),
])
def test_dich_vu_ra_dung_option(raw, suffix):
    assert mapper.dich_vu(raw).endswith(suffix)
    assert mapper.dich_vu(raw) in mapper.DICH_VU.values()


@pytest.mark.parametrize(("raw", "want"), [
    ("Sở Xây dựng tỉnh Cao Bằng", "Sở Xây dựng tỉnh Cao Bằng"),
    ("Sở Xây dựng Đà Nẵng", "Sở Xây dựng TP Đà Nẵng"),
    ("Sở Giao thông vận tải tỉnh Quảng Nam", "Sở Xây dựng TP Đà Nẵng"),
    ("Sở Xây dựng Thành phố Hồ Chí Minh", "Sở Xây dựng TP Hồ Chí Minh"),
])
def test_kinh_gui_khop_option_so_xay_dung(raw, want):
    assert mapper.kinh_gui(raw) == want


def test_vision_doc_o_danh_dau_va_ghep_vao_ket_qua():
    parsed = vision.parse({
        "dia_chi": {"tinh": "", "xa": ""}, "dien_thoai": "", "muc_dich": "c",
        "phuong_tien": [{"bienSo": "92A-123.45", "mauSon": "trắng", "soKhung": "KHUNG 0001"}],
        "giay_xe": [{"bienSo": "92A-123.45", "soKhung": "KHUNGIN01", "soMay": "MAYIN01"}],
    })
    assert parsed["purpose"] == "Hoạt động kinh doanh"
    assert vision.purpose("b") == "Cá nhân" and vision.purpose("Phục vụ hoạt động của tổ chức/cá nhân") == \
        "Hoạt động kinh doanh"
    fields = [{"name": k, "value": v} for k, v in _values(DeNghi_MucDich="").items()]
    _apply_vision(fields, parsed)
    _, by_name, _ = _run({f["name"]: f["value"] for f in fields})
    assert by_name[f"{P}[mucdich_03]"] is True
    car = json.loads(by_name[f"{P}[BienSoXeData]"])[0]
    assert car["mauSon"] == "trắng" and car["soKhung"] == "KHUNGIN01" and car["soMay"] == "MAYIN01"


# ---------------- Đính kèm ----------------
_DE_NGHI_PTM = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY ĐỀ NGHỊ CẤP, CẤP LẠI GIẤY PHÉP LIÊN VẬN GIỮA VIỆT NAM, LÀO VÀ "
                "CAMPUCHIA CHO PHƯƠNG TIỆN PHI THƯƠNG MẠI\nKính gửi: Sở Xây dựng")
_DE_NGHI_TM = _DE_NGHI_PTM.replace("PHI THƯƠNG MẠI", "THƯƠNG MẠI")
_CA_VET = "GIẤY CHỨNG NHẬN ĐĂNG KÝ XE Ô TÔ\nBiển số đăng ký: 92A-123.45\nSố khung: KHUNG0001\nSố máy: MAY0001"


def _gop(de_nghi):
    return (f"Trang 1/4\n{de_nghi}\nTrang 2/4\n*Chú ý: Tổ chức, đơn vị kinh doanh vận tải phải ký, đóng dấu\n"
            f"Trang 3/4\n{_CA_VET}\nTrang 4/4\nCĂN CƯỚC CÔNG DÂN\nSố định danh cá nhân: 048090000001")


_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "giay_de_nghi"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "other"},  # trang "Chú ý" nối tiếp Giấy đề nghị
    {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "dang_ky_xe"},
    {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "cccd"},
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "hop_dong_du_an"},
]
_TYPES = [{"index": 0, "docTypes": ["giay_de_nghi", "dang_ky_xe", "cccd"]}, {"index": 1, "docTypes": ["hop_dong_du_an"]}]


def _pdf(name, pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    doc.close()
    return FileItem(name=name, type="application/pdf", role="doc", dataUrl=f"data:application/pdf;base64,{data}")


def _plan(monkeypatch, options, *, split_fails=False, texts=None, segments=None, types=None, files=None):
    texts = texts or {"ho-so.pdf": _gop(_DE_NGHI_PTM), "hop-dong.png": "HỢP ĐỒNG thi công công trình tại Lào"}

    async def fake_ocr(items):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in items]

    async def fake_chat(messages, **_kwargs):
        if "docTypes" in messages[0]["content"]:  # prompt chế độ không tách
            return json.dumps({"documents": types or _TYPES})
        if split_fails:
            raise RuntimeError("LLM hết giờ")
        return json.dumps({"documents": segments or _SEGMENTS})

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr)
    monkeypatch.setattr("app.services.llm.client.chat", fake_chat)
    files = files or [_pdf("ho-so.pdf", 4),
                      FileItem(name="hop-dong.png", type="image/png", role="doc", dataUrl="data:image/png;base64,AAAA")]
    out = asyncio.run(dieu_phoi.plan(files, options))
    AttachmentPlanResp.model_validate(out)
    return out


# Tên 7 dòng bảng "Thành phần hồ sơ" theo mapping (rút gọn đuôi dài).
_ROW_TEXTS = [
    "- Thành phần hồ sơ đối với phương tiện phi thương mại:",
    "[Phương tiện thương mại]Giấy đề nghị cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia cho phương tiện "
    "thương mại theo mẫu (Click chuột vào đây để mở Biểu mẫu giấy tờ)",
    "[Phương tiện phi thương mại]Giấy đề nghị cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia cho phương "
    "tiện phi thương mại theo mẫu (Click chuột vào đây để mở Biểu mẫu giấy tờ)",
    "[Phương tiện phi thương mại]Đối với doanh nghiệp thực hiện công trình, dự án hoặc hoạt động kinh doanh trên lãnh thổ "
    "Lào hoặc Campuchia thì kèm theo hợp đồng hoặc tài liệu chứng minh doanh nghiệp đang thực hiện công trình",
    "- Thành phần hồ sơ đối với phương tiện thương mại:",
    "[Phương tiện thương mại]Giấy chứng nhận đăng ký xe ô tô hoặc giấy hẹn nhận giấy chứng nhận đăng ký xe ô tô của cơ quan "
    "có thẩm quyền cấp giấy chứng nhận đăng ký xe ô tô(Bản sao hoặc bản sao có chứng thực). Trường hợp phương tiện không "
    "thuộc quyền sở hữu của đơn vị kinh doanh vận tải phải xuất trình thêm: Hợp đồng thuê phương tiện",
    "[Phương tiện phi thương mại]Giấy chứng nhận đăng ký xe ô tô cho phương tiện phi thương mại (Bản sao hoặc bản sao có "
    "chứng thực). Trường hợp phương tiện không thuộc sở hữu của tổ chức, cá nhân thì phải kèm theo tài liệu chứng minh",
]


def _fe_fold(value):
    """foldChoiceText của content.js: bỏ dấu, Đ→D, gộp dấu gạch thành khoảng trắng, chữ thường."""
    text = unicodedata.normalize("NFD", str(value).replace("Đ", "D").replace("đ", "d"))
    text = re.sub(r"\s*[-–—]+\s*", " ", "".join(c for c in text if unicodedata.category(c) != "Mn"))
    return " ".join(text.lower().split())


def _fe_rows_matching(component_name):
    want = _fe_fold(component_name)
    return [i + 1 for i, row in enumerate(_ROW_TEXTS) if want in _fe_fold(row) or _fe_fold(row) in want]


def test_ten_dong_chi_khop_dung_mot_dong_tren_cong():
    # untickRows dò dòng KHÔNG kèm STT → mỗi componentName phải khớp đúng một dòng (hai dòng Giấy đề nghị / đăng ký xe
    # chỉ khác chữ "phi").
    for index, row in tach.ROWS.items():
        assert _fe_rows_matching(row["componentName"]) == [index], row["componentName"]


def test_bat_tach_phi_thuong_mai_cat_dung_dong_khong_sot_trang(monkeypatch):
    out = _plan(monkeypatch, {"splitDocuments": True})
    attachments = out["attachments"]
    gop = [(a["componentIndex"], a["detectedType"], a["sourceSegments"][0]["pageIndexes"], a["loaiBan"])
           for a in attachments if a["fileIndex"] == 0]
    assert gop == [(3, "giay_de_nghi", [0, 1], "Bản chính"), (3, "cccd", [3], "Bản chính"),
                   (7, "dang_ky_xe", [2], "Bản sao")]
    assert sorted(p for a in attachments if a["fileIndex"] == 0 for s in a["sourceSegments"] for p in s["pageIndexes"]) \
        == [0, 1, 2, 3]
    hop_dong = next(a for a in attachments if a["fileIndex"] == 1)
    assert hop_dong["componentIndex"] == 4 and hop_dong["loaiBan"] == "Bản sao" and not hop_dong.get("sourceSegments")
    assert all(a["target"] == "attp-row" for a in attachments)
    # Bỏ tick dòng nhóm thương mại (dòng 2 cổng tích sẵn); dòng 1 tiêu đề phi thương mại giữ tick.
    assert attachments[0]["untickRows"] == [tach.ROWS[r]["componentName"] for r in (2, 5, 6)]
    assert out["extracted"]["thuongMai"] is False
    assert not any("Chưa có" in e or "Không có hợp đồng" in e for e in out["errors"])


def test_bat_tach_thuong_mai_vao_dong_2_va_6(monkeypatch):
    texts = {"ho-so.pdf": _gop(_DE_NGHI_TM), "hop-dong.png": "HỢP ĐỒNG thi công công trình tại Lào"}
    out = _plan(monkeypatch, {"splitDocuments": True}, texts=texts)
    rows = {(a["componentIndex"], a["detectedType"]) for a in out["attachments"]}
    assert rows == {(2, "giay_de_nghi"), (2, "cccd"), (6, "dang_ky_xe"), (2, "hop_dong_du_an")}
    assert out["attachments"][0]["untickRows"] == [tach.ROWS[r]["componentName"] for r in (1, 3, 4, 7)]
    assert out["extracted"]["thuongMai"] is True


def test_thieu_dang_ky_xe_va_hop_dong_thi_canh_bao_va_bo_tick_dong_4(monkeypatch):
    texts = {"de-nghi.pdf": "Trang 1/1\n" + _DE_NGHI_PTM}
    out = _plan(monkeypatch, {"splitDocuments": True}, texts=texts, files=[_pdf("de-nghi.pdf", 1)],
                segments=[{"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "giay_de_nghi"}])
    assert [a["componentIndex"] for a in out["attachments"]] == [3]
    assert out["attachments"][0]["untickRows"] == [tach.ROWS[r]["componentName"] for r in (2, 4, 5, 6)]
    assert any("Giấy chứng nhận đăng ký xe ô tô (dòng 7, bắt buộc)" in e for e in out["errors"])
    assert any("đã bỏ tick dòng 4" in e for e in out["errors"])


@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
def test_tat_tach_moi_tep_nguyen_mot_lan(monkeypatch, options):
    out = _plan(monkeypatch, options)
    attachments = out["attachments"]
    assert sorted(a["fileIndex"] for a in attachments) == [0, 1]
    assert not any(a.get("sourceSegments") for a in attachments)
    by_file = {a["fileIndex"]: a for a in attachments}
    # Tệp gộp: dòng Giấy đề nghị phi thương mại nhận nguyên tệp, giữ tên gốc; hợp đồng vào dòng 4.
    assert by_file[0]["componentIndex"] == 3 and by_file[0]["documentName"] == "ho-so"
    assert by_file[1]["componentIndex"] == 4 and by_file[1]["loaiBan"] == "Bản sao"
    assert any("ho-so.pdf" in e and "gộp nhiều giấy" in e for e in out["errors"])
    # Đăng ký xe nằm trong tệp gộp → không báo thiếu; dòng 7 không có tệp → vẫn không bỏ tick (dòng của nhóm mình).
    assert not any("Chưa có Giấy chứng nhận đăng ký xe" in e for e in out["errors"])
    assert attachments[0]["untickRows"] == [tach.ROWS[r]["componentName"] for r in (2, 5, 6)]


def test_bat_tach_ma_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    out = _plan(monkeypatch, {"splitDocuments": True}, split_fails=True)
    assert out["errors"][0].startswith("attachment_agent (tách)")
    assert sorted(a["fileIndex"] for a in out["attachments"]) == [0, 1]
    assert not any(a.get("sourceSegments") for a in out["attachments"])


def test_rule_type_nhan_theo_tieu_de():
    assert tach._rule_type(_DE_NGHI_PTM) == "giay_de_nghi"
    assert tach._rule_type(_CA_VET) == "dang_ky_xe"
    assert tach._rule_type("HỢP ĐỒNG THUÊ XE Ô TÔ\nBên cho thuê …") == "quyen_su_dung_xe"
    assert tach._rule_type("HỢP ĐỒNG thi công công trình tại Campuchia") == "hop_dong_du_an"
    assert tach._normalize_type("hợp đồng thuê phương tiện") == "quyen_su_dung_xe"
    assert tach.route("quyen_su_dung_xe", False) == 7 and tach.route("quyen_su_dung_xe", True) == 6


# ---------------- Trợ lý người dân ----------------
def test_tro_ly_toan_quoc_chon_so_xay_dung():
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(KEY)
    assert proc["supportsSplitDocuments"] is True and proc["keKhaiUrl"].endswith("05871a46a2dc")
    assert proc["agencySoFirst"] is True and proc["agencyDeptLabel"] == "Sở Xây dựng"
    assert "provinceOnly" not in proc and proc["bxdFlow"]["resultGroups"][0]["name"] == "receivingKind"
