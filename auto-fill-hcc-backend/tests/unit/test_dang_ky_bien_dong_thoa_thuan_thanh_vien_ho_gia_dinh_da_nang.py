"""Unit test "[Đà Nẵng] Đăng ký biến động 1.013980" — mapper (Phần I hai vai + Phần II thửa đất) và attach planner
(bảng 12 dòng, file gộp cả bộ hồ sơ đính một lần ở dòng 1). Dữ liệu trong test đều là ví dụ bịa."""

import asyncio
import base64
import json

import fitz
import pytest

from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.attach import planner as P
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process import mapper as M
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.process.schemas import FileItem

_KEY = "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-da-nang"


def _fields(**values) -> list[dict]:
    return [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]


def _ui(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


_UY_QUYEN = dict(
    ChuHoSo_LoaiChuThe="Tổ chức",
    ChuHoSo_HoTen="Công ty TNHH Thương mại Sông Hàn Xanh",
    ChuHoSo_SoDinhDanh="0401 234 567",
    ChuHoSo_DiaChi={"quocGia": "Việt Nam", "tinh": "Thành phố Đà Nẵng", "xa": "Phường Thanh Khê",
                    "chiTietDuoiXa": "12 Đường Số Ba"},
    NoiDungBienDong="Mua tài sản đấu giá theo Hợp đồng mua bán tài sản đấu giá số 000111/2025 và cấp đổi giấy chứng nhận.",
    DienThoaiLienHe="0236.3 111 222",
    GhiChu="Theo Đơn cam kết ngày 01/10/2026: V/v không đăng ký biến động tài sản gắn liền với đất",
    NguoiNop_HoTen="TRẦN THỊ MẪU",
    NguoiNop_SoDinhDanh="048 190 000 111",
    NguoiNop_NgayCap="05/06/2022",
    NguoiNop_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    NguoiNop_DiaChi={"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Thanh Khê Tây", "chiTietDuoiXa": "Tổ 9"},
    ThuaDat_DiaChi={"quocGia": "Việt Nam", "tinh": "Thành phố Đà Nẵng", "xa": "Xã Hòa Phước",
                    "chiTietDuoiXa": "Quốc lộ 1A"},
    ThuaDat_SoTo="tờ bản đồ số 275",
    ThuaDat_SoThua="Thửa đất số 173",
)


# ---------------------------------------------------------------- mapper

def test_uy_quyen_to_chuc_dien_ca_hai_vai_va_thua_dat():
    out, warnings = M.enrich(_fields(**_UY_QUYEN))
    ui = _ui(out)
    assert ui["data[ownerFullname]"] == "Công ty TNHH Thương mại Sông Hàn Xanh"
    # Mapping: chủ hồ sơ là doanh nghiệp → "Tổ chức" dù người nộp là cá nhân được ủy quyền.
    assert ui["data[chonDoiTuong]"] == "Tổ chức"
    assert ui["data[taxCode]"] == "0401234567"
    assert ui["data[isOwnerDossier]"] is False
    assert ui["data[fullname]"] == "TRẦN THỊ MẪU"
    assert ui["data[identityNumber]"] == "048190000111"
    assert ui["data[identityDate]"] == "05/06/2022"
    assert ui["data[identityAgency]"]
    # Số thứ 4 của CCCD = 1 → Nữ (TT 59/2021) khi giấy tờ không ghi giới tính.
    assert ui["data[gender]"] == "Nữ"
    # Địa chỉ nhóm Phần I = nơi cư trú NGƯỜI NỘP (không phải trụ sở công ty), địa danh cũ đã quy đổi.
    assert ui["data[province]"] == "Thành phố Đà Nẵng"
    assert ui["data[district]"] == "Phường Thanh Khê"
    assert ui["data[address]"] == "Tổ 9"
    assert ui["data[phoneNumber]"] == "02363111222"
    assert ui["data[noidungyeucaugiaiquyet]"].startswith("Mua tài sản đấu giá")
    assert ui["data[note]"].startswith("Theo Đơn cam kết")
    # Phần II: xã cũ Hòa Phước → Phường Hòa Xuân; ô địa chỉ thửa ghép lại bằng tên MỚI.
    assert ui["data[province2]"] == "Thành phố Đà Nẵng"
    assert ui["data[district2]"] == "Phường Hòa Xuân"
    assert ui["data[diaChiThuaDat]"] == "Quốc lộ 1A, Phường Hòa Xuân, Thành phố Đà Nẵng"
    assert ui["data[SoToBanDo]"] == "275"
    assert ui["data[SoThuaDat]"] == "173"
    assert ui["data[nation2]"] == "Việt Nam"
    # Không có ngày sinh → để trống và nhắc cán bộ (cổng điền sẵn ngày sinh tài khoản).
    assert "data[birthday]" not in ui
    assert any("Ngày sinh" in w for w in warnings)


def test_moi_field_ui_deu_co_trong_schema():
    out, _ = M.enrich(_fields(**_UY_QUYEN, NguoiNop_NgaySinh="01/02/1990", NguoiNop_Email="mau@example.com"))
    assert {f["name"] for f in out} <= set(UI_COMP_BY_NAME)
    for f in out:
        assert f["comp"] == UI_COMP_BY_NAME[f["name"]]
    assert _ui(out)["data[birthday]"] == "01/02/1990"


def test_gioi_tinh_tren_giay_to_thang_suy_tu_cccd():
    out, _ = M.enrich(_fields(**{**_UY_QUYEN, "NguoiNop_GioiTinh": "Nam"}))
    assert _ui(out)["data[gender]"] == "Nam"


def test_ca_nhan_tu_nop_tich_chu_ho_so_la_nguoi_nop():
    out, _ = M.enrich(_fields(
        ChuHoSo_LoaiChuThe="Cá nhân",
        ChuHoSo_HoTen="LÊ VĂN VÍ DỤ",
        ChuHoSo_DiaChi={"tinh": "Đà Nẵng", "xa": "Phường Hải Châu", "chiTietDuoiXa": "5 Đường Mẫu"},
        NoiDungBienDong="Nhận quyền sử dụng đất theo văn bản thỏa thuận của vợ và chồng",
        NguoiNop_SoDinhDanh="048092000222",
        ThuaDat_DiaChi="Tổ 3, Phường Hải Châu, Thành phố Đà Nẵng",
        ThuaDat_SoTo="10",
        ThuaDat_SoThua="20",
    ))
    ui = _ui(out)
    assert ui["data[isOwnerDossier]"] is True
    assert ui["data[fullname]"] == "LÊ VĂN VÍ DỤ"
    assert ui["data[chonDoiTuong]"] == "Cá nhân"
    assert "data[taxCode]" not in ui
    assert ui["data[gender]"] == "Nam"
    # Người nộp = chủ hồ sơ → dùng địa chỉ chủ hồ sơ khi không có địa chỉ riêng.
    assert ui["data[district]"] == "Phường Hải Châu"
    assert ui["data[address]"] == "5 Đường Mẫu"
    # Địa chỉ thửa đất dạng chuỗi vẫn tách được.
    assert ui["data[district2]"] == "Phường Hải Châu"
    assert ui["data[diaChiThuaDat]"] == "Tổ 3, Phường Hải Châu, Thành phố Đà Nẵng"


def test_to_chuc_khong_uy_quyen_de_trong_nguoi_nop():
    out, warnings = M.enrich(_fields(
        ChuHoSo_HoTen="Công ty Cổ phần Mẫu Thử",
        ChuHoSo_SoDinhDanh="0400000001",
        NoiDungBienDong="Nhận chuyển nhượng do xử lý tài sản thế chấp",
        DienThoaiLienHe="0905000111",
        # Người ký đơn là giám đốc, KHÔNG có CCCD trong hồ sơ → không được dùng làm người nộp.
        NguoiNop_HoTen="PHẠM GIÁM ĐỐC",
    ))
    ui = _ui(out)
    assert ui["data[chonDoiTuong]"] == "Tổ chức"
    assert ui["data[isOwnerDossier]"] is False
    for name in ("data[fullname]", "data[identityNumber]", "data[gender]", "data[province]", "data[district]"):
        assert name not in ui
    assert any("không có giấy ủy quyền" in w for w in warnings)


def test_thieu_noi_dung_va_so_dien_thoai_thi_canh_bao():
    out, warnings = M.enrich(_fields(ChuHoSo_HoTen="NGÔ THỊ THỬ", NguoiNop_SoDinhDanh="048300000333"))
    ui = _ui(out)
    assert "data[noidungyeucaugiaiquyet]" not in ui
    assert "data[phoneNumber]" not in ui
    assert any("Nội dung biến động" in w for w in warnings)
    assert any("điện thoại" in w for w in warnings)


def test_phuong_cu_khong_con_trong_danh_muc_thi_de_trong_va_canh_bao():
    values = {**_UY_QUYEN, "NguoiNop_DiaChi": {"tinh": "Đà Nẵng", "xa": "Phường Không Tồn Tại", "chiTietDuoiXa": "Tổ 9"}}
    out, warnings = M.enrich(_fields(**values))
    ui = _ui(out)
    assert "data[district]" not in ui
    assert ui["data[province]"] == "Thành phố Đà Nẵng" and ui["data[address]"] == "Tổ 9"
    assert any("Phường Không Tồn Tại" in w and "chọn tay" in w for w in warnings)


@pytest.mark.parametrize("dia_chi,district,address,stale", [
    # LLM lấy QUẬN cũ làm xa, phường cũ dính vào chi tiết → tách lại; phường cũ quy đổi được thì điền phường mới.
    ({"tinh": "Đà Nẵng", "xa": "Thanh Khê", "diaChi": "Tổ 9 Thanh Khê Tây"}, "Phường Thanh Khê", "Tổ 9", None),
    # Phường cũ chưa có trong bảng quy đổi → để trống ô Phường, giữ nguyên chi tiết, cảnh báo đúng tên cũ.
    ({"tinh": "Đà Nẵng", "xa": "Thanh Khê", "diaChi": "Tổ 11 Phường Cũ Giả"}, None, "Tổ 11 Phường Cũ Giả", "Cũ Giả"),
    # xa có tiền tố "Phường" là model đã tách đúng → không đụng.
    ({"tinh": "Đà Nẵng", "xa": "Phường An Khê", "diaChi": "Tổ 11 Khu Mẫu"}, "Phường An Khê", "Tổ 11 Khu Mẫu", None),
])
def test_dia_chi_cu_4_cap_bi_lay_quan_lam_phuong(dia_chi, district, address, stale):
    out, warnings = M.enrich(_fields(**{**_UY_QUYEN, "NguoiNop_DiaChi": dia_chi}))
    ui = _ui(out)
    assert ui.get("data[district]") == district
    assert ui["data[address]"] == address
    if stale:
        assert any(stale in w and "chọn tay" in w for w in warnings)


def test_ten_phuong_tran_lay_ten_day_du_theo_danh_muc():
    values = {**_UY_QUYEN, "ThuaDat_DiaChi": {"tinh": "Đà Nẵng", "xa": "Hòa Xuân", "chiTietDuoiXa": "Quốc lộ 1A"}}
    ui = _ui(M.enrich(_fields(**values))[0])
    assert ui["data[district2]"] == "Phường Hòa Xuân"
    assert ui["data[diaChiThuaDat]"] == "Quốc lộ 1A, Phường Hòa Xuân, Thành phố Đà Nẵng"


@pytest.mark.parametrize("raw,expected", [
    ("tờ bản đồ số 275", "275"), ("Thửa 12a", "12a"), ("173", "173"), ("không có", None),
])
def test_so_to_so_thua_bo_nhan(raw, expected):
    assert M._parcel_number(raw) == expected


def test_schema_compact_khong_lan_field_ui():
    assert not any(name.startswith("data[") for name in ALLOWED)


# ---------------------------------------------------------------- attach planner

def _plan(texts: list[str], llm: dict[int, str] | None = None, pages: dict[int, int] | None = None):
    files = [{"name": f"f{i}.pdf"} for i in range(len(texts))]
    ocr = [{"name": f"f{i}.pdf", "text": t} for i, t in enumerate(texts)]
    return P.build_plan_items(files, ocr, llm or {}, pages or {})


_DON = "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\nKính gửi: Văn phòng Đăng ký đất đai"


def test_file_gop_ca_bo_ho_so_chi_dinh_dong_1():
    items, warnings, cls = _plan([_DON + "\nMẫu số 25"], {0: "don_bien_dong"}, {0: 75})
    assert len(items) == 1
    assert items[0]["componentIndex"] == 1
    assert items[0]["componentName"] == "(1) Đơn đăng ký biến động đất đai"
    assert items[0]["loaiBan"] == "Bản chính" and items[0]["target"] == "attp-row"
    assert any("gộp 75 trang" in w and "dòng 1" in w for w in warnings)
    assert cls[0]["source"] == "llm"


def test_file_gop_llm_doan_nham_van_ve_don():
    items, _, cls = _plan([_DON + "\nGiấy chứng nhận quyền sử dụng đất"], {0: "giay_chung_nhan"}, {0: 40})
    assert items[0]["detectedType"] == "don_bien_dong"
    assert cls[0]["source"] == "priority-don"


def test_tach_rieng_tung_giay_to_vao_dung_dong_dau():
    texts = [
        _DON,
        "GIẤY ỦY QUYỀN\nTại đây ủy quyền cho bà ...",
        "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nQUYỀN SỞ HỮU NHÀ Ở",
        "HỢP ĐỒNG MUA BÁN TÀI SẢN ĐẤU GIÁ\nBên bán: Chi cục Thi hành án dân sự\nquyền sử dụng đất",
        "QUYẾT ĐỊNH về việc giao tài sản\nCHI CỤC THI HÀNH ÁN DÂN SỰ",
        "TỜ KHAI LỆ PHÍ TRƯỚC BẠ NHÀ, ĐẤT",
        "CĂN CƯỚC CÔNG DÂN\nSocialist Republic of Viet Nam",
        "HỢP ĐỒNG MUA BÁN TÀI SẢN CÔNG\nquyền sử dụng đất",
        "VĂN BẢN THỎA THUẬN của vợ và chồng về quyền sử dụng đất",
    ]
    items, warnings, cls = _plan(texts)
    rows = {it["fileName"]: it["componentIndex"] for it in items}
    assert rows == {"f0.pdf": 1, "f1.pdf": 3, "f2.pdf": 5, "f3.pdf": 6, "f4.pdf": 12, "f5.pdf": 1,
                    "f7.pdf": 2, "f8.pdf": 1}
    assert cls[6]["skipped"] is True                     # CCCD không đính
    shared = [w for w in warnings if w.startswith("Dòng 1 đính kèm chung 2 tệp")]
    assert shared and "f5.pdf" in shared[0] and "f8.pdf" in shared[0]
    # Dòng trùng (8-11) không bao giờ được chọn; componentName của các dòng chính khác nhau từng đôi.
    assert {it["componentIndex"] for it in items} <= {1, 2, 3, 4, 5, 6, 7, 12}
    names = [r["componentName"] for r in P._ROWS.values()]
    assert len(set(names)) == len(names)


@pytest.mark.parametrize("text,expected", [
    # Giấy tiếp nhận hồ sơ liệt kê "Đơn đăng ký biến động" nhưng bản thân nó không phải Đơn.
    ("GIẤY TIẾP NHẬN HỒ SƠ VÀ HẸN TRẢ KẾT QUẢ\n1. Đơn đăng ký biến động", "other"),
    ("BẢN VẼ TÁCH THỬA ĐẤT, HỢP THỬA ĐẤT", "ban_ve_tach_hop_thua"),
    ("MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH", "manh_trich_do"),
    ("BẢN ÁN SỐ 01/2026/DS-ST\nTÒA ÁN NHÂN DÂN", "van_ban_giai_quyet_tranh_chap"),
    ("BIÊN BẢN HÒA GIẢI THÀNH", "van_ban_giai_quyet_tranh_chap"),
    ("HỢP ĐỒNG SỬA ĐỔI, BỔ SUNG hợp đồng mua bán tài sản đấu giá quyền sử dụng đất", "hop_dong_chuyen_quyen"),
    ("BIÊN BẢN CUỘC ĐẤU GIÁ", "hop_dong_chuyen_quyen"),
])
def test_rule_doc_type(text, expected):
    assert P._rule_doc_type(text) == expected


def test_llm_bao_other_thi_rule_quyet():
    items, _, cls = _plan(["GIẤY ỦY QUYỀN\nbên được ủy quyền"], {0: "other"})
    assert items[0]["componentIndex"] == 3 and cls[0]["source"] == "rule"


def test_khong_doc_duoc_thi_canh_bao_dinh_tay():
    items, warnings, _ = _plan([""])
    assert items == []
    assert any("đính kèm thủ công" in w for w in warnings)


def _pdf_data_url(pages: int) -> str:
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"Trang {i + 1}")
    data = doc.tobytes()
    doc.close()
    return "data:application/pdf;base64," + base64.b64encode(data).decode("ascii")


def test_plan_chi_ocr_2_trang_dau_va_bao_file_gop(monkeypatch):
    from app.services import ocr
    from app.services.llm import client

    seen_pages: list[int] = []

    async def fake_ocr(files, **_):
        for f in files:
            raw = base64.b64decode(f["dataUrl"].partition(",")[2])
            with fitz.open(stream=raw, filetype="pdf") as d:
                seen_pages.append(d.page_count)
        return [{"name": f["name"], "text": _DON} for f in files]

    async def fake_chat(messages, **_):
        return json.dumps({"documents": [{"index": 0, "docType": "don_bien_dong"}]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(client, "chat", fake_chat)
    files = [FileItem(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(9), role="")]
    res = asyncio.run(P.plan(files))
    assert seen_pages == [2]                                  # OCR phân loại chỉ 2 trang đầu
    assert [a["componentIndex"] for a in res["attachments"]] == [1]
    assert any("gộp 9 trang" in e for e in res["errors"])


def test_ocr_pdf_lon_chia_phan_song_song_va_ghep_dung_thu_tu(monkeypatch):
    from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process import runner as R
    from app.services import ocr

    calls: list[list[str]] = []

    async def fake_ocr(files, **_):
        calls.append([f["name"] for f in files])
        out = []
        for f in files:
            raw = base64.b64decode(f["dataUrl"].partition(",")[2])
            with fitz.open(stream=raw, filetype="pdf") as d:
                out.append({"name": f["name"], "type": f["type"],
                            "text": "\n".join(p.get_text().strip() for p in d), "provider": "tiengnoi"})
        return out

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    files = [
        {"name": "anh.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AAAA"},
        {"name": "gop.pdf", "type": "application/pdf", "dataUrl": _pdf_data_url(75)},
        {"name": "nho.pdf", "type": "application/pdf", "dataUrl": _pdf_data_url(3)},
    ]

    def fake_whole(files_, **_):
        calls.append([f["name"] for f in files_])
        return [{"name": f["name"], "type": f["type"], "text": f"text {f['name']}"} for f in files_]

    async def router(files_, **kw):
        if any(f["name"].startswith("gop.pdf#") for f in files_):
            return await fake_ocr(files_, **kw)
        return fake_whole(files_, **kw)

    monkeypatch.setattr(ocr, "ocr_per_file", router)
    res = asyncio.run(R._ocr_split_large_pdfs(files))
    assert [r["name"] for r in res] == ["anh.jpg", "gop.pdf", "nho.pdf"]
    # Ảnh + PDF ít trang đi chung một lượt như cũ; PDF 75 trang tách 6 phần gửi riêng.
    assert ["anh.jpg", "nho.pdf"] in calls
    assert sum(1 for c in calls if c[0].startswith("gop.pdf#")) == 6
    lines = res[1]["text"].splitlines()
    assert lines[0] == "Trang 1" and lines[-1] == "Trang 75" and len(lines) == 75


def test_pdf_it_trang_khong_chia():
    from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process import runner as R

    assert R._split_pdf({"name": "a.pdf", "dataUrl": _pdf_data_url(15)}) is None
    assert len(R._split_pdf({"name": "b.pdf", "dataUrl": _pdf_data_url(16)})) == 2


# ---------------------------------------------------------------- registry / ke_khai_links

def test_registry_va_link_ke_khai_cung_key():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS
    from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES
    from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang import attach, process

    proc = next(p for p in PROCEDURES if p["key"] == _KEY)
    assert proc["detect"]["urlScope"] == ["dichvucong.danang.gov.vn"]
    assert proc["hasAttachmentStep"] is True
    assert _PIPELINE[_KEY] is process.run
    assert _ATTACH_PIPELINE[_KEY] is attach.plan
    link = next(l for l in KE_KHAI_LINKS if l["key"] == _KEY)
    assert link["code"] == "1.013980" and link["selectSo"] is True and link["submitCardIndex"] == 2


def test_chi_hien_cho_tai_khoan_da_nang():
    from app.procedures.registry import PROCEDURES
    from app.procedures.ke_khai_links import procedure_province_slugs

    proc = next(p for p in PROCEDURES if p["key"] == _KEY)
    assert procedure_province_slugs(proc) == ["danang"]
