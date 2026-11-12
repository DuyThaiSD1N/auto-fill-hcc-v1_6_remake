"""Unit test "[Tỉnh Bắc Ninh] Đăng ký thay đổi biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (1.011442).

Theo Mapping_Don_dang_ky.xlsx / Mapping_Nguoi_uy_quyen.xlsx + ảnh ánh xạ đính kèm ngày 12/11/2026: thân Phiếu 02a khớp
class eform-element-<Key>; khối doiTuongKhac* = bên cấp Giấy giới thiệu (mặc định "Doanh nghiệp"). Đính kèm: tệp scan
chung → không tách thì đính NGUYÊN tệp vào mọi dòng có giấy (Phiếu Bản chính + Bản sao, HĐ sửa đổi, văn bản căn cứ,
GCN, Giấy giới thiệu, File đính kèm khác); tách thì mỗi giấy một mục có sourceSegments. Dữ liệu trong test là bịa.
"""

import asyncio
import base64
import json

import fitz
import pytest

from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_bac_ninh import attach
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_bac_ninh.attach import catalog, phan_trang
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_bac_ninh.process import mapper, runner, schema
from app.process.schemas import FileItem

_KEY = "dang-ky-thay-doi-bien-phap-bao-dam-bac-ninh"

_PHIEU = {
    "Don_NoiKhai": "Bắc Ninh",
    "Don_NgayKhai": "05/11/2026",
    "Don_KinhGui": "Chi nhánh Văn phòng đăng ký đất đai Từ Sơn (2)",
    "NguoiYeuCau_TuCach": "Bên nhận bảo đảm",
    "NguoiYeuCau_TenDayDu": "Ngân hàng TMCP An Phú – Chi nhánh Kinh Bắc",
    "NguoiYeuCau_DiaChi": "12 Lý Thái Tổ, Phường Kinh Bắc, Tỉnh Bắc Ninh",
    "NguoiYeuCau_HoTenLienHe": "Trần Thị Bình",
    "NguoiYeuCau_DienThoai": "0912.000.111",
    "VanBan_Ten": "Hợp đồng sửa đổi, bổ sung Hợp đồng thế chấp số 45/2026/SĐBS, công chứng số 1234 ngày 05/11/2026",
    "VanBan_So": "45/2026/SĐBS",
    "VanBan_ThoiDiem": "05/11/2026",
    "NoiDungThayDoi": "Thay đổi tên bên nhận bảo đảm:\n- Tên cũ: Chi nhánh Đông Bắc\n....\n- Tên mới: Chi nhánh Kinh Bắc",
    "GiayToKemTheo": "- Giấy chứng nhận số phát hành AB 123456;\n- Hợp đồng sửa đổi, bổ sung số 45/2026/SĐBS",
    "CachThucNhan": "Nhận trực tiếp tại cơ quan đăng ký",
}


def _fields(values: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in values.items()]


def _ui(values: dict) -> dict:
    return {f["name"]: f for f in mapper.enrich(_fields(values))}


# ── Điền đơn ──

def test_than_phieu_khop_class_eform_theo_mapping():
    ui = _ui(_PHIEU)
    assert ui["NoiKhaiHoSo"]["value"] == "Bắc Ninh"
    assert ui["NgayKhaiHoSo"]["value"] == "05/11/2026"
    assert ui["KinhGui"]["value"] == "Chi nhánh Văn phòng đăng ký đất đai Từ Sơn"
    assert ui["1NguoiYeuCauDangKy"] == {"name": "1NguoiYeuCauDangKy", "comp": "bn-radio",
                                        "value": ["Bên nhận bảo đảm"]}
    assert ui["HoVaTenDayDuDoiVoiCaNhanTenDayDuDoiVoiToChucVietCh"]["value"] == (
        "NGÂN HÀNG TMCP AN PHÚ – CHI NHÁNH KINH BẮC")
    assert ui["DiaChiDeCoQuanDangKyLienHeKhiCanThiet"]["value"] == "12 Lý Thái Tổ, Phường Kinh Bắc, Tỉnh Bắc Ninh"
    assert ui["HoVaTen"]["value"] == "Trần Thị Bình"
    assert ui["SoDienThoai"]["value"] == "0912000111"
    assert ui["TenVanBan"]["value"].startswith("Hợp đồng sửa đổi, bổ sung Hợp đồng thế chấp số 45/2026/SĐBS")
    assert ui["ThoiDiemCoHieuLucHoacThoiDiemKy9"]["value"] == "05/11/2026"
    # Mục 3 / mục 5 giữ từng dòng, bỏ dòng chỉ có dấu chấm giữ chỗ.
    assert ui["3NoiDungYeuCauDangKyThayDoi10"]["value"].split("\n") == [
        "Thay đổi tên bên nhận bảo đảm:", "- Tên cũ: Chi nhánh Đông Bắc", "- Tên mới: Chi nhánh Kinh Bắc"]
    assert ui["5GiayToKemTheo11"]["value"].count("\n") == 1
    assert ui["6CachThucNhanKetQuaDangKy"]["value"] == ["Nhận trực tiếp tại cơ quan đăng ký"]
    assert ui["noiNhanKetQua"]["value"] == ["Tại nơi nộp hồ sơ"]
    assert set(ui) <= set(schema.UI_COMP_BY_NAME)


def test_o_so_la_so_nguyen_chi_dien_khi_so_toan_chu_so():
    assert "SoNeuCo" not in _ui(_PHIEU)  # "45/2026/SĐBS" gõ vào ô number thành dãy số sai
    assert _ui({**_PHIEU, "VanBan_So": "2026 15"})["SoNeuCo"]["value"] == "202615"


def test_o_khong_nop_phi_chi_tick_khi_phieu_danh_dau():
    assert "4ThuocDoiTuongKhongPhaiNopPhiDangKy" not in _ui(_PHIEU)
    assert _ui({**_PHIEU, "KhongNopPhi": True})["4ThuocDoiTuongKhongPhaiNopPhiDangKy"]["value"] == [
        "Thuộc đối tượng không phải nộp phí đăng ký"]


def test_nhan_qua_buu_chinh_ghi_ro_va_khong_chon_noi_nhan_tai_noi_nop():
    ui = _ui({**_PHIEU, "CachThucNhan": "Nhận qua dịch vụ bưu chính", "CachThucNhan_GhiRo": "Trần Thị Bình, 12 Lý Thái Tổ"})
    assert ui["6CachThucNhanKetQuaDangKy"]["value"] == ["Nhận qua dịch vụ bưu chính"]
    assert ui["CachThucNhanKetQuaDangKy2"]["value"] == "Trần Thị Bình, 12 Lý Thái Tổ"
    assert "noiNhanKetQua" not in ui


@pytest.mark.parametrize("raw, label", [
    ("Bên nhận bảo đảm", "Bên nhận bảo đảm"),
    ("Bên bảo đảm", "Bên bảo đảm"),
    ("bên thế chấp", "Bên bảo đảm"),
    ("Bên kế thừa bên bảo đảm, bên nhận bảo đảm", "Bên kế thừa bên bảo đảm, bên nhận bảo đảm"),
    ("Quản tài viên/Doanh nghiệp quản lý, thanh lý tài sản", "Quản tài viên"),
    ("Chi nhánh của pháp nhân, người đại diện", "Chi nhánh của pháp nhân, người đại diện"),
])
def test_tu_cach_nguoi_yeu_cau_ra_dung_nhan_radio(raw, label):
    assert _ui({**_PHIEU, "NguoiYeuCau_TuCach": raw})["1NguoiYeuCauDangKy"]["value"] == [label]


def test_khong_doc_duoc_tu_cach_thi_khong_tick():
    values = {k: v for k, v in _PHIEU.items() if k != "NguoiYeuCau_TuCach"}
    assert "1NguoiYeuCauDangKy" not in _ui(values)


_OCR_HO_SO = """
PHIẾU YÊU CẦU ĐĂNG KÝ THAY ĐỔI NỘI DUNG BIỆN PHÁP BẢO ĐẢM
Địa chỉ cơ quan đăng ký liên: 21 đường Lý Thái, Kinh Bắc
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
HỢP ĐỒNG SỬA ĐỔI, BỔ SUNG HỢP ĐỒNG THẾ CHẤP QUYỀN SỬ DỤNG ĐẤT
Số: 45/2026/SĐBS
1. BÊN NHẬN THẾ CHẤP (DƯỚI ĐÂY GỌI TẮT LÀ BÊN A):
NGÂN HÀNG TMCP AN PHÚ - CHI NHÁNH KINH BẮC.
Địa chỉ trụ sở: 12 Lý Thái Tổ, Phường Kinh Bắc, Tỉnh Bắc Ninh.
Mã số thuế: 0100999888-012.
2. BÊN THẾ CHẤP (DƯỚI ĐÂY GỌI TẮT LÀ BÊN B)
CÔNG TY TNHH MINH AN
- Địa chỉ trụ sở chính: 5 Ngô Gia Tự, Phường Võ Cường, Tỉnh Bắc Ninh
LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN
HỢP ĐỒNG THẾ CHẤP QUYỀN SỬ DỤNG ĐẤT
BÊN NHẬN THẾ CHẤP: NGÂN HÀNG TMCP AN PHÚ - CHI NHÁNH ĐÔNG BẮC
Địa chỉ: 99 đường cũ, Phường Cũ
"""


def test_dia_chi_lien_he_lay_ban_danh_may_trong_hd_sua_doi_cua_cung_chu_the():
    llm = {"NguoiYeuCau_TenDayDu": "NGÂN HÀNG TMCP AN PHÚ (APB) – CHI NHÁNH KINH BẮC",
           "NguoiYeuCau_TuCach": "Bên nhận bảo đảm", "NguoiYeuCau_DiaChi": "21 đường Lý Thái, Kinh Bắc"}
    fixed = mapper.apply_ocr_fallback(llm, [{"text": _OCR_HO_SO}])
    assert fixed["NguoiYeuCau_DiaChi"] == "12 Lý Thái Tổ, Phường Kinh Bắc, Tỉnh Bắc Ninh"
    # Người yêu cầu là bên thế chấp → khối BÊN THẾ CHẤP của HĐ sửa đổi.
    ben_b = {"NguoiYeuCau_TenDayDu": "CÔNG TY TNHH MINH AN", "NguoiYeuCau_TuCach": "Bên bảo đảm"}
    assert mapper.apply_ocr_fallback(ben_b, [{"text": _OCR_HO_SO}])["NguoiYeuCau_DiaChi"] == (
        "5 Ngô Gia Tự, Phường Võ Cường, Tỉnh Bắc Ninh")
    # Tên không khớp (bên nhận cũ ở HĐ gốc) hoặc không có HĐ sửa đổi → giữ giá trị LLM.
    khac = {**llm, "NguoiYeuCau_TenDayDu": "NGÂN HÀNG TMCP AN PHÚ - CHI NHÁNH ĐÔNG BẮC"}
    assert mapper.apply_ocr_fallback(khac, [{"text": _OCR_HO_SO}])["NguoiYeuCau_DiaChi"] == llm["NguoiYeuCau_DiaChi"]
    no_contract = _OCR_HO_SO.replace("HỢP ĐỒNG SỬA ĐỔI", "HỢP ĐỒNG")
    assert mapper.apply_ocr_fallback(llm, [{"text": no_contract}])["NguoiYeuCau_DiaChi"] == llm["NguoiYeuCau_DiaChi"]


# ── Khối người ủy quyền ──

_UY_QUYEN = {
    "UyQuyen_CoVanBan": True,
    "NguoiUyQuyen_Loai": "Doanh nghiệp",
    "NguoiUyQuyen_Ten": "Ngân hàng TMCP An Phú – Chi nhánh Kinh Bắc",
    "NguoiUyQuyen_SoDinhDanh": "0100 999 888-012",
    "NguoiUyQuyen_GioiTinh": "Nữ",
    "NguoiUyQuyen_SoDienThoai": "0912.000.111",
    "NguoiUyQuyen_DiaChi": {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Kinh Bắc", "chiTietDuoiXa": "12 Lý Thái Tổ"},
}


def test_khoi_uy_quyen_doanh_nghiep_theo_sheet_doanh_nghiep():
    out, warnings = mapper.enrich_authorized(_fields(_UY_QUYEN))
    by = {f["name"]: f["value"] for f in out}
    assert warnings == []
    assert by["doiTuongKhachoTen"] == "NGÂN HÀNG TMCP AN PHÚ – CHI NHÁNH KINH BẮC"
    assert by["doiTuongKhacsoDinhDanh"] == "0100999888-012"  # mã chi nhánh giữ phần sau dấu gạch
    assert by["doiTuongKhacsoDienThoai"] == "0912000111"
    assert "doiTuongKhacgioiTinhId" not in by  # ô cá nhân không có ở khối Doanh nghiệp
    names = [f["name"] for f in out]
    assert names.index("doiTuongKhactinhThanhId") < names.index("doiTuongKhacphuongXaId")
    assert by["doiTuongKhacdiaChiChiTiet"] == "12 Lý Thái Tổ"
    assert mapper.authorized_subject(_fields(_UY_QUYEN)) == "Doanh nghiệp"


def test_khoi_uy_quyen_ca_nhan_co_o_ca_nhan():
    values = {**_UY_QUYEN, "NguoiUyQuyen_Loai": "Cá nhân khác là Công dân Việt Nam",
              "NguoiUyQuyen_Ten": "Lê Văn Cường", "NguoiUyQuyen_SoDinhDanh": "027088001234",
              "NguoiUyQuyen_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"}
    by = {f["name"]: f["value"] for f in mapper.enrich_authorized(_fields(values))[0]}
    assert by["doiTuongKhachoTen"] == "Lê Văn Cường"
    assert by["doiTuongKhacgioiTinhId"] == "Nữ"
    assert by["doiTuongKhacnoiCap"]
    assert mapper.authorized_subject(_fields(values)) == "Cá nhân khác là Công dân Việt Nam"


def test_khong_co_giay_gioi_thieu_thi_khong_dien_khoi_uy_quyen():
    out, warnings = mapper.enrich_authorized(_fields({k: v for k, v in _UY_QUYEN.items() if k != "UyQuyen_CoVanBan"}))
    assert out == [] and warnings
    assert mapper.authorized_subject(_fields({"NguoiUyQuyen_Loai": "Tổ chức"})) is None


def test_runner_tach_luot_theo_purpose(monkeypatch):
    calls = []

    async def fake_run(files_by_role, **kwargs):
        calls.append(kwargs)
        if kwargs["fields"] is schema.FIELDS_UYQUYEN:
            return {"fields": _fields(_UY_QUYEN)}
        return {"fields": _fields(_PHIEU)}

    monkeypatch.setattr(runner.runner, "run", fake_run)
    res = asyncio.run(runner.run({}, {"purpose": "authorized_person"}))
    assert calls[-1]["fields"] is schema.FIELDS_UYQUYEN
    assert calls[-1]["ocr_fn"] is phan_trang.ocr_files  # PDF dài OCR song song cho kịp timeout extension
    assert res["authorizedSubject"] == "Doanh nghiệp"
    assert all(f["name"].startswith("doiTuongKhac") for f in res["fields"])
    res = asyncio.run(runner.run({}, {"purpose": "registration_form"}))
    assert calls[-1]["fields"] is schema.FIELDS
    assert "KinhGui" in {f["name"] for f in res["fields"]}


# ── Chia trang ──

def _pdf(pages: int) -> str:
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def test_ocr_song_song_danh_lai_so_trang_theo_tep_goc(monkeypatch):
    from app.services import ocr

    async def fake_ocr(files, *_a, **_k):
        out = []
        for f in files:
            with fitz.open(stream=base64.b64decode(f["dataUrl"].partition(",")[2]), filetype="pdf") as doc:
                n = doc.page_count
            out.append({"name": f["name"], "text": "\n".join(
                f"───── Trang {i}/{n} ─────\nnội dung {f['name']} {i}" for i in range(1, n + 1))})
        return out

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    res = asyncio.run(phan_trang.ocr_files([{"name": "bo.pdf", "type": "application/pdf", "dataUrl": _pdf(14)}]))
    pages = phan_trang.split_pages(res[0]["text"])
    assert len(pages) == 14 and all(pages)
    assert pages[13].endswith("#trang8 7")  # trang 14 = trang 7 của phần thứ hai


def test_cat_pdf_ra_bytes_co_dinh_de_luot_dien_va_dinh_kem_trung_cache_ocr():
    file = {"name": "bo.pdf", "type": "application/pdf", "dataUrl": _pdf(14)}
    first, second = phan_trang._split_pdf(file), phan_trang._split_pdf(file)
    assert [s for s, _ in first] == [0, 7]
    assert [c["dataUrl"] for _, c in first] == [c["dataUrl"] for _, c in second]


def test_giay_phu_du_moi_trang_va_trang_1_luon_mo_giay():
    pages = {0: ["Phiếu yêu cầu " * 10, "Điều 2 " * 10, "|", "GIẤY GIỚI THIỆU " * 5]}
    docs = phan_trang.documents_from_starts(pages, [
        {"fileIndex": 0, "trangDau": 2, "loai": "phieu_02a", "ten": "Phiếu"},
        {"fileIndex": 0, "trangDau": 3, "loai": "gcn", "ten": "trang trắng"},   # trang trắng không mở giấy
        {"fileIndex": 0, "trangDau": 4, "loai": "la_lam", "ten": ""},            # nhãn lạ → khac
        {"fileIndex": 0, "trangDau": 9, "loai": "gcn", "ten": ""},               # ngoài tệp
    ])
    assert [(d["pages"], d["label"]) for d in docs] == [([0, 1, 2], "phieu_02a"), ([3], "khac")]


# ── Đính kèm: bộ mẫu theo cấu trúc tệp scan chung user gửi 12/11/2026 (chữ bịa) ──
_TRANG = [
    ("Mẫu số 02a CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM PHIẾU YÊU CẦU ĐĂNG KÝ THAY ĐỔI NỘI DUNG BIỆN PHÁP BẢO ĐẢM", 1),
    ("2 6. Cách thức nhận kết quả đăng ký: Nhận trực tiếp tại cơ quan đăng ký", 0),
    ("Mẫu số 02a CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM PHIẾU YÊU CẦU ĐĂNG KÝ THAY ĐỔI NỘI DUNG BIỆN PHÁP BẢO ĐẢM", 1),
    ("2 6. Cách thức nhận kết quả đăng ký: Nhận trực tiếp tại cơ quan đăng ký", 0),
    ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM HỢP ĐỒNG SỬA ĐỔI, BỔ SUNG HỢP ĐỒNG THẾ CHẤP Số: 45/2026/SĐBS", 1),
    ("LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN Hôm nay, ngày 05 tháng 11 năm 2026", 0),
    ("MẪU SỐ 01 CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM HỢP ĐỒNG THẾ CHẤP QUYỀN SỬ DỤNG ĐẤT Số: 99/2023", 1),
    ("LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN Hôm nay, ngày 01 tháng 3 năm 2023", 0),
    ("NGÂN HÀNG TMCP AN PHÚ CHI NHÁNH KINH BẮC GIẤY GIỚI THIỆU Kính gửi: Văn phòng đăng ký đất đai", 1),
    ("Nội dung thay đổi và cơ sở pháp lý GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT Số vào sổ CS 01234", 1),
    ("TRANG BỔ SUNG GIẤY CHỨNG NHẬN Thửa đất số: 12 Tờ bản đồ số: 3", 0),
    ("NGÂN HÀNG TMCP AN PHÚ Số: 123/NH-TCNS Về phương án sắp xếp mạng lưới", 1),
    ("NGÂN HÀNG TMCP AN PHÚ QUYẾT ĐỊNH Về chấm dứt hoạt động Chi nhánh Đông Bắc", 1),
    ("NGÂN HÀNG TMCP AN PHÚ QUYẾT ĐỊNH Về việc thay đổi tên gọi Phòng giao dịch", 1),
]
_LOAI = ["phieu_02a", "phieu_02a", "hd_sua_doi", "hop_dong_the_chap", "van_ban_dai_dien", "gcn",
         "vb_can_cu_khac", "vb_can_cu_khac", "vb_can_cu_khac"]
_STARTS = [i + 1 for i, (_, opens) in enumerate(_TRANG) if opens]
_BO = "\n".join(f"───── Trang {i}/{len(_TRANG)} ─────\n{body} " + "x" * 60 for i, (body, _) in enumerate(_TRANG, 1))


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


_DONG_ANH_XA = [
    ("existing", "KQ003703", "banChinh"),
    ("existing", "KQ003703", "banSao"),
    ("existing", "KQ003704", "banSao"),
    ("supplementary", "", "banChinh"),
    ("existing", "KQ003709", "banSao"),
    ("existing", "KQ003707", "banChinh"),
    ("existing", "KQ003706", "banSao"),
]


def test_khong_tach_dinh_nguyen_tep_vao_moi_dong_co_giay_dung_anh_xa(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"},
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        res = asyncio.run(attach.plan(_bo_ho_so(), options))
        rows = [(a["target"], a["componentName"], a["slotKey"]) for a in res["attachments"]]
        assert rows == _DONG_ANH_XA
        assert all(a["fileIndex"] == 0 and "sourceSegments" not in a for a in res["attachments"])
        assert len({a["documentName"] for a in res["attachments"]}) == len(rows)
    assert calls and all(c == phan_trang.SEGMENT_SYSTEM_PROMPT for c in calls)  # MỘT lượt LLM cho cả bộ


def test_tach_moi_giay_mot_muc_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch(monkeypatch, [])
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    rows = [(a["componentName"], a["slotKey"], a["sourceSegments"][0]["pageIndexes"]) for a in res["attachments"]]
    assert rows == [
        ("KQ003703", "banChinh", [0, 1]),
        ("KQ003703", "banSao", [2, 3]),
        ("KQ003704", "banSao", [4, 5]),        # lời chứng thuộc HĐ sửa đổi
        ("", "banChinh", [6, 7]),               # HĐ thế chấp gốc → File đính kèm khác
        ("KQ003709", "banSao", [8]),
        ("KQ003707", "banChinh", [9, 10]),      # GCN + trang bổ sung
        ("KQ003706", "banSao", [11]),
        ("KQ003706", "banSao", [12]),
        ("KQ003706", "banSao", [13]),
    ]
    pages = sorted(p for _, _, ps in rows for p in ps)
    assert pages == list(range(len(_TRANG)))
    assert res["extracted"]["attachmentMode"] == "split_documents"


def test_tach_loi_thi_dinh_nguyen_tep_theo_tieu_de_trang(monkeypatch):
    _patch(monkeypatch, [], fail=True)
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    assert all("sourceSegments" not in a for a in res["attachments"])
    assert [(a["target"], a["componentName"], a["slotKey"]) for a in res["attachments"]] == _DONG_ANH_XA
    assert any("đính nguyên tệp" in e for e in res["errors"])
    res = asyncio.run(attach.plan(_bo_ho_so(), {}))
    assert [(a["target"], a["componentName"], a["slotKey"]) for a in res["attachments"]] == _DONG_ANH_XA


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


def test_ten_giay_giu_so_hieu_co_dau_gach_cheo():
    from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_bac_ninh.attach.dinh_kem_khong_tach.planner import unique_name

    used: set[str] = set()
    assert unique_name("Văn bản 123/NH-TCNS về sắp xếp mạng lưới", used, "X") == "Văn bản 123 NH-TCNS về sắp xếp mạng lưới"
    assert unique_name("Văn bản 123/NH-TCNS về sắp xếp mạng lưới", used, "X").endswith(" 2")


def test_bang_dong_khong_tu_dinh_kq003708_va_prompt_chia_giay():
    assert "KQ003708" not in {kq for _, kq, _, _ in catalog.CATALOG}
    assert catalog.resolve("phieu_02a", 1) == ("existing", "KQ003703", "banSao")
    assert catalog.resolve("la_lam") == ("supplementary", "", "banChinh")
    prompt = phan_trang.SEGMENT_SYSTEM_PROMPT
    assert "LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN" in prompt and "TRANG BỔ SUNG GIẤY CHỨNG NHẬN" in prompt
    assert all(label in prompt for label in catalog.LABELS)


# ── Registry lõi + trợ lý ──

def test_registry_loi_va_link_ke_khai_cung_key():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS
    from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

    proc = get_procedure(_KEY)
    assert proc["label"] == ("[Tỉnh Bắc Ninh] Đăng ký thay đổi biện pháp bảo đảm bằng quyền sử dụng đất, "
                             "tài sản gắn liền với đất")
    assert proc["detect"] == {"urlScope": ["dichvucong.bacninh.gov.vn"],
                              "urlIncludes": ["maThuTucHanhChinh=1.011442"]}
    assert proc["supportsSplitDocuments"] is True
    assert get_pipeline(_KEY) is not None and get_attach_pipeline(_KEY) is not None
    trung = [p["key"] for p in PROCEDURES
             if "maThuTucHanhChinh=1.011442" in ((p.get("detect") or {}).get("urlIncludes") or [])]
    assert trung == [_KEY]
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert link["code"] == "1.011442" and link["label"].startswith("Bắc Ninh - ")
    assert link["selectSo"] is True


def test_tro_ly_co_the_bac_ninh_khoi_uy_quyen_doanh_nghiep():
    from app.channels.handfree.chat.field_review import registry
    from app.channels.handfree.procedure_registry import _HOAN_THIEN_THEO_TINH, get_procedure, procedure_code
    from app.upload_session.classifier_registry import _CLASSIFIERS

    tl = get_procedure(_KEY)
    assert procedure_code(tl) == "1.011442"
    assert tl["provinceOnly"] == ["bacninh"]
    assert tl["agencyProvinceOnly"] is True and tl["agencySoFirst"] is True
    assert tl["samePageAttach"] is True and tl["bacNinhTabFlow"]
    assert tl["supportsSplitDocuments"] is True
    assert tl["bacNinhAuthorizedPerson"]["subjectOption"] == "Doanh nghiệp"
    assert tl["bacNinhAuthorizedAsk"] is True
    assert registry.get(_KEY)["noAsk"] == ("KinhGui", "SoNeuCo", "CachThucNhanKetQuaDangKy2")
    assert _KEY in _CLASSIFIERS
    assert "bacninh" in _HOAN_THIEN_THEO_TINH[_KEY]
