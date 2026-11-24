"""Unit test "[Tỉnh Bắc Ninh] Xác nhận tiếp tục sử dụng đất nông nghiệp" (1.115462).

Theo file mapping 24/11/2026 (eform 2869): ô Đơn Mẫu 09 khớp NAME element_773xx, nhiều thửa ghi danh sách cùng thứ tự;
khối doiTuongKhac* = bên ủy quyền, đủ 60 tuổi → "Người cao tuổi". Đính kèm theo ảnh ánh xạ: Đơn (kèm trang xác nhận
UBND xã) → TP-H05.000053, GCN → TP-H05.000040, Giấy ủy quyền + lời chứng → File đính kèm khác. Dữ liệu trong test là bịa.
"""

import asyncio
import base64
import json
from datetime import date

import fitz

from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_bac_ninh import attach
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_bac_ninh.attach import catalog, phan_trang
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_bac_ninh.process import mapper, runner, schema
from app.process.schemas import FileItem

_KEY = "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-bac-ninh"

_SAMPLE = {
    "Don_NoiKhai": "Đông Phong",
    "Don_NgayKhai": "05/03/2026",
    "Don_KinhGui": "Văn phòng đăng ký đất đai liên phường, xã Yên Phong",
    "Don_NguoiSuDungDat": "Lê Văn An",
    "Don_DiaChiLienHe": "Thôn Đông, xã Đông Phong, tỉnh Bắc Ninh, điện thoại: 0912.345.678",
    "Don_ThuaSo": "12; 45\n7",
    "Don_ToBanDo": "III, IV, IV",
    "Don_DienTich": "240, 360,5, 180",
    "Don_MucDich": "Canh tác",
    "Don_ThoiHan": "tháng 10/2013",
    "Don_TaiSan": "Không",
    "Don_DiaDiem": "Thôn Đông, xã Đông Phong, tỉnh Bắc Ninh",
    "Gcn_SoPhatHanh": "M 123456",
    "Gcn_SoVaoSo": "00123 QSDĐ/100 QĐCT",
    "Gcn_NgayCap": "15/06/1999",
    "Don_NoiDungDeNghi": "……………",
    "Don_DenThang": "10.",
    "Don_DenNam": "2063",
    "Xn_NoiDung": "Thửa đất số 12, tờ bản đồ số III chưa có thông báo thu hồi.\nCác thửa đất sử dụng ổn định.",
    "Xn_NgayXacNhan": "06/03/2026",
    "ChuHoSo_SoDinhDanh": "0270.600.01234",
}


def _fields(values: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in values.items()]


def _ui(values: dict) -> dict:
    return {f["name"]: f for f in mapper.enrich(_fields(values))}


# ── Điền đơn ──

def test_than_don_khop_name_element_cua_eform_2869():
    ui = _ui(_SAMPLE)
    assert ui["element_77320"]["value"] == "Đông Phong"
    assert ui["element_77321"]["value"] == "05/03/2026"
    assert ui["element_77323"]["value"] == "Văn phòng đăng ký đất đai liên phường, xã Yên Phong"
    assert ui["element_77325"]["value"] == "Thôn Đông, xã Đông Phong, tỉnh Bắc Ninh, điện thoại: 0912.345.678"
    assert ui["element_77330"]["value"] == "Canh tác"
    assert ui["element_77331"]["value"] == "tháng 10/2013"
    assert ui["element_77332"]["value"] == "Không"
    assert ui["element_77335"]["value"] == "M 123456"
    assert ui["element_77336"]["value"] == "00123 QSDĐ/100 QĐCT"
    assert ui["element_77337"]["value"] == "15/06/1999"
    assert all(f["comp"] == "bn-input" for f in ui.values())
    assert set(ui) <= set(schema.UI_COMP_BY_NAME)
    # Nơi xác nhận của UBND xã: giấy không ghi địa danh → không phát.
    assert "element_77346" not in ui


def test_nhieu_thua_giu_thu_tu_va_phan_thap_phan():
    ui = _ui(_SAMPLE)
    assert ui["element_77327"]["value"] == "12, 45, 7"
    assert ui["element_77328"]["value"] == "III, IV, IV"
    assert ui["element_77329"]["value"] == "240, 360,5, 180"


def test_muc_4_cham_giu_cho_bo_va_chi_giu_chu_so():
    ui = _ui(_SAMPLE)
    assert "element_77338" not in ui and "element_77339" not in ui
    assert ui["element_77340"]["value"] == "10"
    assert ui["element_77341"]["value"] == "2063"


def test_xac_nhan_ubnd_xa_mot_dong_va_ngay_chi_khi_co_noi_dung():
    ui = _ui(_SAMPLE)
    assert ui["element_77344"]["value"] == (
        "Thửa đất số 12, tờ bản đồ số III chưa có thông báo thu hồi. Các thửa đất sử dụng ổn định.")
    assert ui["element_77347"]["value"] == "06/03/2026"
    values = {k: v for k, v in _SAMPLE.items() if k != "Xn_NoiDung"}
    assert not {"element_77344", "element_77347"} & set(_ui(values))


def test_nguoi_nhan_ket_qua_la_chu_ho_so():
    ui = _ui(_SAMPLE)
    assert ui["nhanTaiNhahoTen"]["value"] == "Lê Văn An"
    assert ui["nhanTaiNhasoCCCD"]["value"] == "027060001234"
    assert ui["nhanTaiNhasoDienThoai"]["value"] == "0912345678"  # rút từ ô địa chỉ liên hệ
    assert ui["nhanTaiNhadiaChi"]["value"] == "Thôn Đông"


def test_fallback_ocr_bo_sung_dong_thua_va_so_gcn():
    text = (
        "3.1. Thông tin về tờ, thửa, diện tích:\n"
        "Thửa đất số: 12 Tờ bản đồ số: III Diện tích (m2): 240\n"
        "Thửa đất số: 45 Tờ bản đồ số: IV Diện tích (m²): 360\n"
        "Thửa đất số: 7 Tờ bản đồ số: IV Diện tích (m2): 180\n"
        "3.8. Giấy chứng nhận về quyền sử dụng đất đã cấp:\n"
        "- Số phát hành: M 123456; Số vào sổ: 00123 QSDĐ/100 QĐCT, Ngày cấp: 15/06/1999\n"
    )
    out = runner.apply_ocr_fallback({"Don_ThuaSo": "12", "Don_ToBanDo": "III", "Don_DienTich": "240"},
                                    [{"text": text}])
    assert out["Don_ThuaSo"] == "12, 45, 7"
    assert out["Don_ToBanDo"] == "III, IV, IV"
    assert out["Don_DienTich"] == "240, 360, 180"
    assert out["Gcn_SoPhatHanh"] == "M 123456"
    assert out["Gcn_SoVaoSo"] == "00123 QSDĐ/100 QĐCT"
    # OCR Đơn rớt vế sau "/" của số vào sổ → lấy số đủ in trên GCN / Giấy ủy quyền (cùng phần đầu).
    gcn = "Vào sổ cấp giấy chứng nhận\nSố … 00123-QSDĐ/100-QĐCT\nGiấy chứng nhận số 00999 QSDD/5QĐCT"
    out = runner.apply_ocr_fallback({"Gcn_SoVaoSo": "00123 QSDĐ"}, [{"text": gcn}])
    assert out["Gcn_SoVaoSo"] == "00123 QSDĐ/100 QĐCT"
    assert runner.apply_ocr_fallback({"Gcn_SoVaoSo": "00777 QSDĐ"}, [{"text": gcn}])["Gcn_SoVaoSo"] == "00777 QSDĐ"
    # LLM đã đủ dòng → giữ nguyên bản LLM.
    full = {"Don_ThuaSo": "12, 45, 7", "Don_ToBanDo": "3, 4, 4", "Don_DienTich": "1, 2, 3"}
    assert runner.apply_ocr_fallback(full, [{"text": text}])["Don_ToBanDo"] == "3, 4, 4"


# ── Khối ủy quyền (purpose="authorized_person") ──

_UQ = {
    "ChuHoSo_HoTen": "Lê Văn An",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_SoDinhDanh": "027060001234",
    "ChuHoSo_NgaySinh": "20/04/1960",
    "ChuHoSo_NgayCap": "10/05/2021",
    "ChuHoSo_NoiCap": "Cục cảnh sát",
    "ChuHoSo_DienThoai": "0912 345 678",
    "ChuHoSo_ThuongTru": {"tinh": "Bắc Ninh", "xa": "Xã Đông Phong", "chiTietDuoiXa": "Thôn Đông"},
}


def test_khoi_uy_quyen_la_ben_uy_quyen():
    out, warnings = mapper.enrich_authorized(_fields(_UQ))
    assert warnings == []
    by = {f["name"]: f for f in out}
    assert by["doiTuongKhachoTen"]["value"] == "Lê Văn An"
    assert by["doiTuongKhacgioiTinhId"]["comp"] == "bn-select"
    assert by["doiTuongKhacsoDinhDanh"]["value"] == "027060001234"
    assert by["doiTuongKhacnoiCap"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["doiTuongKhacsoDienThoai"]["value"] == "0912345678"
    assert by["doiTuongKhacdiaChiChiTiet"]["value"] == "Thôn Đông"
    names = [f["name"] for f in out]
    assert names.index("doiTuongKhactinhThanhId") < names.index("doiTuongKhacphuongXaId")
    out, warnings = mapper.enrich_authorized(_fields({"ChuHoSo_HoTen": "Lê Văn An"}))
    assert out == [] and warnings


def test_loai_nguoi_uy_quyen_theo_tuoi():
    today = date(2026, 11, 24)
    assert mapper.authorized_subject(_fields(_UQ), today) == "Người cao tuổi"
    young = {**_UQ, "ChuHoSo_NgaySinh": "25/11/1966"}  # còn 1 ngày nữa mới đủ 60
    assert mapper.authorized_subject(_fields(young), today) is None
    assert mapper.authorized_subject(_fields({**_UQ, "ChuHoSo_NgaySinh": "1960"}), today) is None


def test_runner_tach_luot_theo_purpose(monkeypatch):
    calls = []

    async def fake_run(files_by_role, **kwargs):
        calls.append(kwargs)
        if kwargs["fields"] is schema.FIELDS_UYQUYEN:
            return {"fields": [{"name": "ChuHoSo_HoTen", "value": "Lê Văn An"},
                               {"name": "ChuHoSo_SoDinhDanh", "value": "027060001234"},
                               {"name": "ChuHoSo_NgaySinh", "value": "01/01/1950"}]}
        return {"fields": [{"name": "Don_KinhGui", "value": "Văn phòng đăng ký đất đai tỉnh Bắc Ninh"}]}

    monkeypatch.setattr(runner.runner, "run", fake_run)
    res = asyncio.run(runner.run({}, {"purpose": "authorized_person"}))
    assert calls[-1]["fields"] is schema.FIELDS_UYQUYEN
    assert {f["name"] for f in res["fields"]} == {"doiTuongKhachoTen", "doiTuongKhacsoDinhDanh",
                                                  "doiTuongKhacngaySinh"}
    assert res["authorizedSubject"] == "Người cao tuổi"
    res = asyncio.run(runner.run({}, {}))
    assert calls[-1]["fields"] is schema.FIELDS
    assert calls[-1]["compact_field_fallback"] is runner.apply_ocr_fallback
    assert [f["name"] for f in res["fields"]] == ["element_77323"]
    assert "authorizedSubject" not in res


# ── Đính kèm: bộ mẫu scan chung (chữ bịa) ──
_TRANG = [
    ("Mẫu số 09. Đơn xin xác nhận tục sử dụng đất nông nghiệp CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN XIN XÁC NHẬN LẠI "
     "THỜI HẠN SỬ DỤNG ĐẤT NÔNG NGHIỆP", 1),
    ("II- XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ (Nội dung xác nhận về tình trạng sử dụng đất)", 0),
    ("GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT Số M 123456", 1),
    ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ỦY BAN NHÂN DÂN CHỨNG NHẬN Theo bảng liệt kê dưới đây", 0),
    ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM GIẤY ỦY QUYỀN (Dành cho cá nhân) I. BÊN ỦY QUYỀN", 1),
    ("việc ủy quyền thay cho bên ủy quyền. IV. CAM KẾT", 0),
    ("Mẫu số 05 Lời chứng chứng thực chữ ký, điểm chỉ của nhiều người trong một giấy tờ", 0),
    ("CĂN CƯỚC CÔNG DÂN Số / No.: 027060001234 Họ và tên / Full name: LÊ VĂN AN", 1),
    ("|", 0),
]
_LOAI = ["don_09", "gcn", "uy_quyen", "cccd"]
_STARTS = [i + 1 for i, (_, opens) in enumerate(_TRANG) if opens]
_BO = "\n".join(f"───── Trang {i}/{len(_TRANG)} ─────\n{body} " + ("x" * 60 if body != "|" else "")
                for i, (body, _) in enumerate(_TRANG, 1))


def _pdf(pages: int) -> str:
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def _bo_ho_so():
    return [FileItem(name="ho-so-chung.pdf", type="application/pdf", dataUrl=_pdf(len(_TRANG)), role="")]


def _patch(monkeypatch, calls: list, fail: bool = False):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": _BO} for f in files]

    async def fake_chat(messages, *_a, **_k):
        calls.append(messages[0]["content"])
        if fail:
            raise RuntimeError("LLM hỏng")
        return json.dumps({"giayTo": [{"fileIndex": 0, "trangDau": p, "loai": loai, "ten": ""}
                                      for p, loai in zip(_STARTS, _LOAI)]})

    monkeypatch.setattr(phan_trang, "ocr_files", fake_ocr)
    monkeypatch.setattr(phan_trang.client, "chat", fake_chat)


# Không tách: tệp chung → mỗi dòng có giấy nhận NGUYÊN tệp; ủy quyền + CCCD chung một mục File đính kèm khác.
_DONG = [("existing", "TP-H05.000053"), ("existing", "TP-H05.000040"), ("supplementary", "")]


def test_khong_tach_dinh_nguyen_tep_vao_moi_dong_co_giay(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"},
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        res = asyncio.run(attach.plan(_bo_ho_so(), options))
        assert [(a["target"], a["componentName"]) for a in res["attachments"]] == _DONG
        assert all(a["slotKey"] == "banChinh" for a in res["attachments"])
        assert all(a["fileIndex"] == 0 and "sourceSegments" not in a for a in res["attachments"])
        assert res["extracted"]["attachmentMode"] == "whole_files"
    assert calls and all(c == phan_trang.SEGMENT_SYSTEM_PROMPT for c in calls)  # MỘT lượt LLM cho cả bộ


def test_tach_moi_giay_mot_muc_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch(monkeypatch, [])
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    rows = [(a["componentName"], a["sourceSegments"][0]["pageIndexes"]) for a in res["attachments"]]
    assert rows == [
        ("TP-H05.000053", [0, 1]),     # Đơn + trang xác nhận UBND xã, không tách
        ("TP-H05.000040", [2, 3]),     # bìa + trang chứng nhận
        ("", [4, 5, 6]),               # Giấy ủy quyền + lời chứng chứng thực, cùng một mục
        ("", [7, 8]),                  # CCCD + mặt sau trắng
    ]
    assert sorted(p for _, ps in rows for p in ps) == list(range(len(_TRANG)))
    assert res["extracted"]["attachmentMode"] == "split_documents"


def test_tach_loi_thi_dinh_nguyen_tep_theo_tieu_de_trang(monkeypatch):
    _patch(monkeypatch, [], fail=True)
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    assert all("sourceSegments" not in a for a in res["attachments"])
    assert [(a["target"], a["componentName"]) for a in res["attachments"]] == _DONG
    assert [d["label"] for d in res["extracted"]["giayTo"]] == _LOAI  # từ khoá: xác nhận UBND / lời chứng không mở giấy
    assert any("đính nguyên tệp" in e for e in res["errors"])


def test_ba_tep_rieng_nhu_ho_so_mau(monkeypatch):
    texts = {
        "don.pdf": "ĐƠN XIN XÁC NHẬN LẠI THỜI HẠN SỬ DỤNG ĐẤT NÔNG NGHIỆP " + "x" * 50,
        "gcn.pdf": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT " + "x" * 50,
        "uq.pdf": "GIẤY ỦY QUYỀN (Dành cho cá nhân) " + "x" * 50,
    }

    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_chat(*_a, **_k):
        return json.dumps({"giayTo": [{"fileIndex": i, "trangDau": 1, "loai": loai, "ten": ""}
                                      for i, loai in enumerate(["don_09", "gcn", "uy_quyen"])]})

    monkeypatch.setattr(phan_trang, "ocr_files", fake_ocr)
    monkeypatch.setattr(phan_trang.client, "chat", fake_chat)
    files = [FileItem(name=n, type="application/pdf", dataUrl=_pdf(1), role="") for n in texts]
    for options in ({}, {"splitDocuments": True}):
        res = asyncio.run(attach.plan(files, options))
        assert [(a["fileIndex"], a["componentName"], "sourceSegments" in a) for a in res["attachments"]] == [
            (0, "TP-H05.000053", False), (1, "TP-H05.000040", False), (2, "", False)]


def test_bang_dong_dung_2_thanh_phan_cua_mapping_va_prompt():
    codes = {code for _, code, _, _ in catalog.CATALOG if code}
    assert codes == {"TP-H05.000053", "TP-H05.000040"}
    assert catalog.resolve("uy_quyen") == ("supplementary", "", "banChinh")
    assert catalog.resolve("la_lam") == ("supplementary", "", "banChinh")
    prompt = phan_trang.SEGMENT_SYSTEM_PROMPT
    assert all(label in prompt for label in catalog.LABELS)
    assert "XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ" in prompt and "Lời chứng chứng thực" in prompt


# ── Registry lõi + trợ lý ──

def test_registry_loi_va_link_ke_khai_cung_key():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS
    from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

    proc = get_procedure(_KEY)
    assert proc["detect"] == {"urlScope": ["dichvucong.bacninh.gov.vn"],
                              "urlIncludes": ["maThuTucHanhChinh=1.115462"]}
    assert proc["supportsSplitDocuments"] is True
    assert get_pipeline(_KEY) is not None and get_attach_pipeline(_KEY) is not None
    trung = [p["key"] for p in PROCEDURES
             if "maThuTucHanhChinh=1.115462" in ((p.get("detect") or {}).get("urlIncludes") or [])]
    assert trung == [_KEY]
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert link["code"] == "1.115462" and link["selectSo"] is True and link["provinceOnlyAgency"] is True
    assert proc["label"] == "[Tỉnh Bắc Ninh] " + link["label"].removeprefix("Bắc Ninh - ")


def test_tro_ly_co_the_bac_ninh_chon_so_va_khoi_uy_quyen_chu_ho_so():
    from app.channels.handfree.chat.field_review import registry
    from app.channels.handfree.procedure_registry import _HOAN_THIEN_THEO_TINH, get_procedure, procedure_code

    tl = get_procedure(_KEY)
    assert procedure_code(tl) == "1.115462"
    assert tl["provinceOnly"] == ["bacninh"]
    assert tl["agencyProvinceOnly"] is True and tl["agencySoFirst"] is True
    assert tl["samePageAttach"] is True and tl["bacNinhTabFlow"]
    assert tl["supportsSplitDocuments"] is True
    assert tl["bacNinhAuthorizedPerson"]["subjectOption"] == "Cá nhân khác là Công dân Việt Nam"
    assert tl["bacNinhAuthorizedAsk"] is True
    assert "KinhGui" in registry.get(_KEY)["noAsk"]
    assert _HOAN_THIEN_THEO_TINH[_KEY] == frozenset({"bacninh"})
