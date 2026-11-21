"""Unit test "[Tỉnh Bắc Ninh] Đăng ký biến động do đổi tên / thay đổi thông tin người sử dụng đất" (1.115460).

Theo crawl DOM 21/11/2026: Đơn Mẫu 18 khớp CLASS eform-element-<Key> (cùng bộ khoá 1.115465); số vào sổ / số phát hành
GCN đã cấp ghép vào "II. Nội dung biến động"; khối doiTuongKhac* = chủ hồ sơ. Đính kèm 7 dòng TP-H05 + File đính kèm
khác: không tách thì đính NGUYÊN tệp vào mọi dòng có giấy; tách thì mỗi giấy một mục có sourceSegments. Dữ liệu trong
test là bịa.
"""

import asyncio
import base64
import json

import fitz

from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh import attach
from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh.attach import catalog, phan_trang
from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh.process import mapper, runner, schema
from app.process.schemas import FileItem

_KEY = "dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-bac-ninh"

_SAMPLE = {
    "Cccd_HoTen": "Nguyễn Văn An",
    "Cccd_SoDinhDanh": "0270.900.01234",
    "Cccd_NgayCap": "10/05/2022",
    "Cccd_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "Don_KinhGui": "Văn phòng đăng ký đất đai tỉnh Bắc Ninh",
    "Don_DiaChi": "Thôn Đông - Xã Tân Hồng - Huyện Từ Sơn - Tỉnh Bắc Ninh",
    "Don_DienThoai": "0912.345.678",
    "Don_NoiDungBienDong": "- Thay đổi số CMND 125123456 thành số CCCD 027090001234\n- Thay đổi địa chỉ ......",
    "Gcn_SoVaoSo": "CS01234/T05/Q02",
    "Gcn_SoPhatHanh": "CĐ 123456",
}


def _fields(values: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in values.items()]


def _ui(values: dict) -> dict:
    return {f["name"]: f for f in mapper.enrich(_fields(values))}


# ── Điền đơn ──

def test_than_don_khop_class_eform_theo_crawl_va_nguoi_nhan_khop_name():
    ui = _ui(_SAMPLE)
    assert ui["KinhGui"]["value"] == "Văn phòng đăng ký đất đai tỉnh Bắc Ninh"
    assert ui["Ten2"]["value"] == "Nguyễn Văn An"
    assert ui["GiayToNhanThanphapNhan"]["value"] == (
        "CCCD số 027090001234, cấp 10/05/2022, Cục Cảnh sát quản lý hành chính về trật tự xã hội")
    assert ui["DiaChi"]["value"] == "Thôn Đông, Xã Tân Hồng, Huyện Từ Sơn, Tỉnh Bắc Ninh"
    assert ui["DienThoaiLienHeNeuCo"]["value"] == "0912345678"
    assert ui["IINoiDungBienDong3"]["comp"] == "bn-textarea"
    assert ui["nhanTaiNhahoTen"]["value"] == "Nguyễn Văn An"
    assert ui["nhanTaiNhasoCCCD"]["value"] == "027090001234"
    assert ui["nhanTaiNhadiaChi"]["value"] == ui["DiaChi"]["value"]
    assert set(ui) <= set(schema.UI_COMP_BY_NAME)
    # Ô cổng điền sẵn / phần UBND xác nhận (class trùng) không phát.
    assert not {"NoiKhaiHoSo", "NgayKhaiHoSo", "HienTrangSuDungDatSuDungOnDinh"} & set(ui)


def test_khoa_eform_trung_dung_19_o_cua_ban_crawl():
    # 19 ô eform-element trong bản crawl 21/11/2026, trừ 3 ô không phát (nơi/ngày khai ×2, hiện trạng sử dụng đất).
    crawled = {"KinhGui", "Ten2", "GiayToNhanThanphapNhan", "DiaChi", "MaSoThueNeuCo", "DienThoaiLienHeNeuCo",
               "HopThuDienTuNeuCo", "IINoiDungBienDong3", "IIIThongTinVeDoiTuongDuocMienGiamNghiaVuTaiChinhVe", "2",
               "3", "1ThanhVienHoGiaDinh5", "2TinhTrangTranhChapDatDai",
               "3SuThayDoiRanhGioiSoVoiRanhGioiDuocCapGiayChungNha"}
    eform_keys = {k for k in schema.UI_COMP_BY_NAME if not k.startswith("nhanTaiNha")}
    assert eform_keys == crawled


def test_noi_dung_bien_dong_giu_dong_va_ghep_so_gcn_da_cap():
    value = _ui(_SAMPLE)["IINoiDungBienDong3"]["value"]
    assert value.split("\n") == [
        "- Thay đổi số CMND 125123456 thành số CCCD 027090001234",
        "- Thay đổi địa chỉ",
        "Giấy chứng nhận đã cấp: Số vào sổ cấp Giấy chứng nhận: CS01234/T05/Q02; Số phát hành (số seri): CĐ 123456",
    ]


def test_don_da_ghi_so_gcn_thi_khong_ghi_lai():
    values = {**_SAMPLE, "Don_NoiDungBienDong": "Đổi tên trên GCN số phát hành CĐ123456, số vào sổ CS01234/T05/Q02"}
    assert _ui(values)["IINoiDungBienDong3"]["value"] == values["Don_NoiDungBienDong"]


def test_don_khong_ghi_muc_ii_thi_khong_tu_dat_cau():
    values = {k: v for k, v in _SAMPLE.items() if k != "Don_NoiDungBienDong"}
    assert "IINoiDungBienDong3" not in _ui(values)


def test_o_cham_giu_cho_khong_phat():
    values = {**_SAMPLE, "Don_GiayTo2": "........", "Don_TranhChap": "…", "Don_MaSoThue": "....."}
    ui = _ui(values)
    assert not {"2", "MaSoThueNeuCo", "2TinhTrangTranhChapDatDai"} & set(ui)


# ── Khối ủy quyền (purpose="authorized_person") ──

def test_khoi_uy_quyen_la_chu_ho_so():
    out, warnings = mapper.enrich_authorized(_fields({
        "ChuHoSo_HoTen": "Nguyễn Văn An",
        "ChuHoSo_GioiTinh": "Nam",
        "ChuHoSo_SoDinhDanh": "027090001234",
        "ChuHoSo_NoiCap": "Cục CS QLHC về TTXH",
        "ChuHoSo_DienThoai": "0912 345 678",
        "ChuHoSo_ThuongTru": {"tinh": "Bắc Ninh", "xa": "Phường Tân Hồng", "chiTietDuoiXa": "Thôn Đông"},
    }))
    assert warnings == []
    by = {f["name"]: f for f in out}
    assert by["doiTuongKhachoTen"]["value"] == "Nguyễn Văn An"
    assert by["doiTuongKhacgioiTinhId"]["comp"] == "bn-select"
    assert by["doiTuongKhacnoiCap"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    names = [f["name"] for f in out]
    assert names.index("doiTuongKhactinhThanhId") < names.index("doiTuongKhacphuongXaId")
    out, warnings = mapper.enrich_authorized(_fields({"ChuHoSo_HoTen": "Nguyễn Văn An"}))
    assert out == [] and warnings


def test_runner_tach_luot_theo_purpose(monkeypatch):
    calls = []

    async def fake_run(files_by_role, **kwargs):
        calls.append(kwargs)
        if kwargs["fields"] is schema.FIELDS_UYQUYEN:
            return {"fields": [{"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn An"},
                               {"name": "ChuHoSo_SoDinhDanh", "value": "027090001234"}]}
        return {"fields": [{"name": "Cccd_HoTen", "value": "Nguyễn Văn An"}]}

    monkeypatch.setattr(runner.runner, "run", fake_run)
    res = asyncio.run(runner.run({}, {"purpose": "authorized_person"}))
    assert calls[-1]["fields"] is schema.FIELDS_UYQUYEN
    assert {f["name"] for f in res["fields"]} == {"doiTuongKhachoTen", "doiTuongKhacsoDinhDanh"}
    res = asyncio.run(runner.run({}, {}))
    assert calls[-1]["fields"] is schema.FIELDS
    # Fallback OCR dùng chung với 1.115465 (cùng Đơn Mẫu 18).
    assert calls[-1]["compact_field_fallback"].__module__.endswith("cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.process.fallback")
    assert {f["name"] for f in res["fields"]} == {"Ten2", "nhanTaiNhahoTen"}


# ── Đính kèm: bộ mẫu scan chung (chữ bịa) ──
_TRANG = [
    ("Mẫu số 18 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT", 1),
    ("Cam đoan nội dung kê khai trên đơn là đúng sự thật II. XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ", 0),
    ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT QUYỀN SỞ HỮU NHÀ Ở CĐ 123456", 1),
    ("II. Thửa đất, nhà ở và tài sản khác gắn liền với đất Thửa đất số: 12 Tờ bản đồ số: 3", 0),
    ("CÔNG AN PHƯỜNG TÂN HỒNG GIẤY XÁC NHẬN THÔNG TIN VỀ CƯ TRÚ Họ và tên: NGUYỄN VĂN AN", 1),
    ("CĂN CƯỚC CÔNG DÂN Số / No.: 027090001234 Họ và tên / Full name: NGUYỄN VĂN AN", 1),
    ("|", 0),
    ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM GIẤY ỦY QUYỀN Bên ủy quyền: Nguyễn Văn An", 1),
]
_LOAI = ["don_18", "gcn", "giay_to_thay_doi", "cccd", "van_ban_dai_dien"]
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


_DONG = [
    ("existing", "TP-H05.000026"),
    ("existing", "TP-H05.000040"),
    ("existing", "TP-H05.000049"),
    ("supplementary", ""),
    ("existing", "TP-H05.000046"),
]


def test_khong_tach_dinh_nguyen_tep_vao_moi_dong_co_giay(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"},
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        res = asyncio.run(attach.plan(_bo_ho_so(), options))
        assert [(a["target"], a["componentName"]) for a in res["attachments"]] == _DONG
        assert all(a["slotKey"] == "banChinh" for a in res["attachments"])
        assert all(a["fileIndex"] == 0 and "sourceSegments" not in a for a in res["attachments"])
        assert len({a["documentName"] for a in res["attachments"]}) == len(_DONG)
        assert res["extracted"]["attachmentMode"] == "whole_files"
    assert calls and all(c == phan_trang.SEGMENT_SYSTEM_PROMPT for c in calls)  # MỘT lượt LLM cho cả bộ


def test_tach_moi_giay_mot_muc_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch(monkeypatch, [])
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    rows = [(a["componentName"], a["sourceSegments"][0]["pageIndexes"]) for a in res["attachments"]]
    assert rows == [
        ("TP-H05.000026", [0, 1]),   # Đơn + trang cam đoan / xác nhận UBND
        ("TP-H05.000040", [2, 3]),   # GCN nhiều trang
        ("TP-H05.000049", [4]),
        ("", [5, 6]),                # CCCD + mặt sau trắng → File đính kèm khác
        ("TP-H05.000046", [7]),
    ]
    assert sorted(p for _, ps in rows for p in ps) == list(range(len(_TRANG)))
    assert res["extracted"]["attachmentMode"] == "split_documents"


def test_tach_loi_thi_dinh_nguyen_tep_theo_tieu_de_trang(monkeypatch):
    _patch(monkeypatch, [], fail=True)
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    assert all("sourceSegments" not in a for a in res["attachments"])
    assert [(a["target"], a["componentName"]) for a in res["attachments"]] == _DONG
    assert any("đính nguyên tệp" in e for e in res["errors"])


def test_tep_anh_cccd_rieng_vao_file_dinh_kem_khac(monkeypatch):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân 027088001234 Họ và tên " + "x" * 50}
                for f in files]

    async def fake_chat(*_a, **_k):
        return json.dumps({"giayTo": [{"fileIndex": 0, "trangDau": 1, "loai": "cccd", "ten": "Căn cước công dân"}]})

    monkeypatch.setattr(phan_trang, "ocr_files", fake_ocr)
    monkeypatch.setattr(phan_trang.client, "chat", fake_chat)
    files = [FileItem(name="cccd.jpg", type="image/jpeg", dataUrl="data:image/jpeg;base64,AAAA", role="")]
    for options in ({}, {"splitDocuments": True}):
        res = asyncio.run(attach.plan(files, options))
        assert [(a["target"], "sourceSegments" in a) for a in res["attachments"]] == [("supplementary", False)]


def test_bang_dong_dung_7_thanh_phan_cua_ban_crawl_va_prompt():
    codes = {code for _, code, _, _ in catalog.CATALOG if code}
    assert codes == {"TP-H05.000026", "TP-H05.000049", "TP-H05.000040", "TP-H05.000050", "TP-H05.000046",
                     "TP-H05.000051", "TP-H05.000045"}
    assert catalog.resolve("la_lam") == ("supplementary", "", "banChinh")
    assert catalog.resolve("cccd") == ("supplementary", "", "banChinh")
    prompt = phan_trang.SEGMENT_SYSTEM_PROMPT
    assert all(label in prompt for label in catalog.LABELS)
    assert "TRANG BỔ SUNG GIẤY CHỨNG NHẬN" in prompt and "Cam đoan nội dung kê khai" in prompt


def test_tu_khoa_du_phong_khong_nham_the_can_cuoc_moi_la_giay_thay_doi():
    assert phan_trang.keyword_page_label("CĂN CƯỚC Số định danh cá nhân / Personal identification number " + "x" * 50) \
        == "cccd"
    assert phan_trang.keyword_page_label("GIẤY XÁC NHẬN THÔNG TIN VỀ CƯ TRÚ " + "x" * 50) == "giay_to_thay_doi"
    assert phan_trang.keyword_page_label("Cam đoan nội dung kê khai trên đơn " + "x" * 50) is None


# ── Registry lõi + trợ lý ──

def test_registry_loi_va_link_ke_khai_cung_key():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS
    from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

    proc = get_procedure(_KEY)
    assert proc["label"].startswith("[Tỉnh Bắc Ninh] Đăng ký biến động đối với trường hợp đổi tên")
    assert proc["detect"] == {"urlScope": ["dichvucong.bacninh.gov.vn"],
                              "urlIncludes": ["maThuTucHanhChinh=1.115460"]}
    assert proc["supportsSplitDocuments"] is True
    assert get_pipeline(_KEY) is not None and get_attach_pipeline(_KEY) is not None
    trung = [p["key"] for p in PROCEDURES
             if "maThuTucHanhChinh=1.115460" in ((p.get("detect") or {}).get("urlIncludes") or [])]
    assert trung == [_KEY]
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert link["code"] == "1.115460" and link["label"].startswith("Bắc Ninh - ")
    assert link["selectSo"] is True and link["provinceOnlyAgency"] is True
    assert proc["label"] == "[Tỉnh Bắc Ninh] " + link["label"].removeprefix("Bắc Ninh - ")


def test_tro_ly_co_the_bac_ninh_chon_so_va_khoi_uy_quyen_chu_ho_so():
    from app.channels.handfree.chat.field_review import registry
    from app.channels.handfree.procedure_registry import _HOAN_THIEN_THEO_TINH, get_procedure, procedure_code

    tl = get_procedure(_KEY)
    assert procedure_code(tl) == "1.115460"
    assert tl["provinceOnly"] == ["bacninh"]
    assert tl["agencyProvinceOnly"] is True and tl["agencySoFirst"] is True
    assert tl["samePageAttach"] is True and tl["bacNinhTabFlow"]
    assert tl["supportsSplitDocuments"] is True
    assert tl["bacNinhAuthorizedPerson"]["subjectOption"] == "Cá nhân khác là Công dân Việt Nam"
    assert tl["bacNinhAuthorizedAsk"] is True
    assert registry.get(_KEY)["noAsk"] == ("KinhGui",)
    assert "bacninh" in _HOAN_THIEN_THEO_TINH[_KEY]
