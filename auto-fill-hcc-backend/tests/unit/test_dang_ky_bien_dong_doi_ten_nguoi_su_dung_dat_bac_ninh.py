"""Unit test "[Tỉnh Bắc Ninh] Đăng ký biến động do đổi tên / thay đổi thông tin người sử dụng đất" (1.115460).

Theo crawl DOM 21/11/2026 + file mapping Excel và ảnh ánh xạ đính kèm 25/11/2026: Đơn khớp CLASS eform-element-<Key>
(cùng bộ khoá 1.115465), nơi / ngày khai khớp NAME element_77275/77276; Đơn Mẫu 24 hai người ghép một ô; mục II nguyên
văn Đơn; mục IV (2) + mục V lấy từ Văn bản cam kết thành viên hộ; khối doiTuongKhac* = chủ hồ sơ. Đính kèm 7 dòng TP-H05
+ File đính kèm khác: Văn bản cam kết đính CHUNG 000049 + 000051, CCCD vào 000049 Bản sao; không tách thì đính NGUYÊN
tệp vào mọi dòng có giấy; tách thì mỗi giấy một mục có sourceSegments. Dữ liệu trong test là bịa.
"""

import asyncio
import base64
import json
from datetime import date

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
}

# Đơn Mẫu 24 hai người đồng sử dụng + Văn bản cam kết thành viên hộ (khuôn hồ sơ mẫu của mapping, chữ bịa).
_MAU_24 = {
    "Cccd_HoTen": "NGUYỄN VĂN AN",
    "Don_DanhXung": "Ông",
    "Cccd_SoDinhDanh": "027070001234",
    "Don_DiaChi": "Thôn Đông, xã Tân Hồng, tỉnh Bắc Ninh",
    "Don_DienThoai": "…………",
    "Don2_DanhXung": "Bà",
    "Don2_HoTen": "TRẦN THỊ BÌNH",
    "Don2_SoGiayTo": "027172005678",
    "Don2_DiaChi": "Thôn Đông, xã Tân Hồng, tỉnh Bắc Ninh",
    "Don2_DienThoai": "0912 345 678",
    "Don_KinhGui": "Chi nhánh Văn phòng đăng ký đất đai liên phường Tân Hồng",
    "Don_NoiDungBienDong": "....Thay đổi Hộ......",
    "Don_GiayTo2": "........",
    "Don_NoiKhai": ".....",
    "Don_NgayKhai": "05/03/2026",
    "Vbck_TieuDe": "Văn bản cam kết của các thành viên hộ gia đình có chung quyền sử dụng đất",
    "Vbck_ChungThuc": "chứng thực chữ ký, điểm chỉ ngày 05/03/2026 tại Văn phòng Công chứng X, tỉnh Bắc Ninh",
    "Vbck_ThanhVien": [
        {"danhXung": "Ông", "hoTen": "Nguyễn Văn An", "ngaySinh": "01/02/1970", "soDinhDanh": "027070001234",
         "thuongTru": "Thôn Đông, xã Tân Hồng, tỉnh Bắc Ninh"},
        {"danhXung": "Bà", "hoTen": "Nguyễn Thị Cúc", "ngaySinh": "03/04/1995", "soDinhDanh": "027195009999",
         "thuongTru": "Tổ dân phố 2, phường Kinh Bắc, tỉnh Bắc Ninh"},
    ],
    "Vbck_TranhChap": "Không có bất cứ tranh chấp khiếu nại, khiếu kiện gì",
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
    assert ui["GiayToNhanThanphapNhan"]["value"] == "027090001234"  # mapping: chỉ số giấy tờ
    assert ui["DiaChi"]["value"] == "Thôn Đông, Xã Tân Hồng, Huyện Từ Sơn, Tỉnh Bắc Ninh"
    assert ui["DienThoaiLienHeNeuCo"]["value"] == "0912345678"
    assert ui["IINoiDungBienDong3"]["comp"] == "bn-textarea"
    assert ui["nhanTaiNhahoTen"]["value"] == "Nguyễn Văn An"
    assert ui["nhanTaiNhasoCCCD"]["value"] == "027090001234"
    # Tỉnh / xã người nhận là select riêng → ô Địa chỉ liên hệ chỉ phần dưới xã.
    assert ui["nhanTaiNhadiaChi"]["value"] == "Thôn Đông"
    assert set(ui) <= set(schema.UI_COMP_BY_NAME)
    # Ô UBND xác nhận (class trùng) không phát; Đơn không ghi nơi / ngày → để cổng điền sẵn.
    assert not {"NoiKhaiHoSo", "NgayKhaiHoSo", "HienTrangSuDungDatSuDungOnDinh", "element_77275",
                "element_77276"} & set(ui)


def test_khoa_eform_trung_dung_o_cua_ban_crawl_va_mapping():
    crawled = {"KinhGui", "Ten2", "GiayToNhanThanphapNhan", "DiaChi", "MaSoThueNeuCo", "DienThoaiLienHeNeuCo",
               "HopThuDienTuNeuCo", "IINoiDungBienDong3", "IIIThongTinVeDoiTuongDuocMienGiamNghiaVuTaiChinhVe", "2",
               "3", "1ThanhVienHoGiaDinh5", "2TinhTrangTranhChapDatDai",
               "3SuThayDoiRanhGioiSoVoiRanhGioiDuocCapGiayChungNha"}
    keys = {k for k in schema.UI_COMP_BY_NAME if not k.startswith(("nhanTaiNha", "element_"))}
    assert keys == crawled
    # Nơi / ngày khai của người viết đơn (eform 2867); 77279/77281/77282 là phần UBND xác nhận → không phát.
    assert {k for k in schema.UI_COMP_BY_NAME if k.startswith("element_")} == {"element_77275", "element_77276"}


def test_noi_dung_bien_dong_nguyen_van_don_khong_ghep_so_gcn():
    value = _ui({**_SAMPLE, "Gcn_SoVaoSo": "CS01234/T05/Q02"})["IINoiDungBienDong3"]["value"]
    assert value.split("\n") == ["- Thay đổi số CMND 125123456 thành số CCCD 027090001234", "- Thay đổi địa chỉ"]


def test_don_khong_ghi_muc_ii_thi_khong_tu_dat_cau():
    values = {k: v for k, v in _SAMPLE.items() if k != "Don_NoiDungBienDong"}
    assert "IINoiDungBienDong3" not in _ui(values)


def test_o_cham_giu_cho_khong_phat():
    values = {**_SAMPLE, "Don_GiayTo2": "........", "Don_TranhChap": "…", "Don_MaSoThue": "....."}
    ui = _ui(values)
    assert not {"2", "MaSoThueNeuCo", "2TinhTrangTranhChapDatDai"} & set(ui)


def test_don_mau_24_hai_nguoi_ghep_mot_o_theo_mapping():
    ui = _ui(_MAU_24)
    assert ui["Ten2"]["value"] == "Ông: NGUYỄN VĂN AN; Bà: TRẦN THỊ BÌNH"
    assert ui["GiayToNhanThanphapNhan"]["value"] == "027070001234; 027172005678"
    assert ui["DiaChi"]["value"] == "Thôn Đông, xã Tân Hồng, tỉnh Bắc Ninh"  # cùng địa chỉ → ghi một lần
    # Mục 1.1 để trống điện thoại → lấy số của người thứ hai (số duy nhất trong Đơn).
    assert ui["DienThoaiLienHeNeuCo"]["value"] == "0912345678"
    assert ui["IINoiDungBienDong3"]["value"] == "Thay đổi Hộ"
    assert ui["element_77276"]["value"] == "05/03/2026"
    assert "element_77275" not in ui  # địa danh chỉ có chấm → cổng giữ "Bắc Ninh"
    # Người nhận kết quả = người thứ nhất.
    assert ui["nhanTaiNhahoTen"]["value"] == "NGUYỄN VĂN AN"
    assert ui["nhanTaiNhasoCCCD"]["value"] == "027070001234"
    assert ui["nhanTaiNhasoDienThoai"]["value"] == "0912345678"
    assert ui["nhanTaiNhadiaChi"]["value"] == "Thôn Đông"


def test_nguoi_thu_hai_trung_nguoi_thu_nhat_thi_bo():
    ui = _ui({**_MAU_24, "Don2_HoTen": "Nguyễn Văn An", "Don2_SoGiayTo": "027070001234"})
    assert ui["Ten2"]["value"] == "NGUYỄN VĂN AN"
    assert ui["GiayToNhanThanphapNhan"]["value"] == "027070001234"
    assert "DienThoaiLienHeNeuCo" not in ui  # không lấy SĐT của "người thứ hai" bị trùng


def test_muc_iv_va_v_lay_tu_van_ban_cam_ket_khi_don_trong():
    ui = _ui(_MAU_24)
    assert ui["2"]["value"] == ("Văn bản cam kết của các thành viên hộ gia đình có chung quyền sử dụng đất (chứng thực "
                                "chữ ký, điểm chỉ ngày 05/03/2026 tại Văn phòng Công chứng X, tỉnh Bắc Ninh)")
    assert ui["1ThanhVienHoGiaDinh5"]["value"] == (
        "1. Ông Nguyễn Văn An, sinh ngày 01/02/1970, CCCD số 027070001234, thường trú: Thôn Đông, xã Tân Hồng, tỉnh "
        "Bắc Ninh; 2. Bà Nguyễn Thị Cúc, sinh ngày 03/04/1995, CCCD số 027195009999, thường trú: Tổ dân phố 2, phường "
        "Kinh Bắc, tỉnh Bắc Ninh")
    assert ui["2TinhTrangTranhChapDatDai"]["value"] == "Không có bất cứ tranh chấp khiếu nại, khiếu kiện gì"
    assert "3SuThayDoiRanhGioiSoVoiRanhGioiDuocCapGiayChungNha" not in ui
    # Đơn tự ghi thì Đơn thắng.
    ui = _ui({**_MAU_24, "Don_GiayTo2": "Giấy xác nhận thông tin về cư trú", "Don_TranhChap": "Không tranh chấp"})
    assert ui["2"]["value"] == "Giấy xác nhận thông tin về cư trú"
    assert ui["2TinhTrangTranhChapDatDai"]["value"] == "Không tranh chấp"


def test_ngay_khai_sai_dinh_dang_khong_phat():
    assert "element_77276" not in _ui({**_MAU_24, "Don_NgayKhai": "tháng 3 năm 2026"})
    assert _ui({**_MAU_24, "Don_NoiKhai": "Tân Hồng"})["element_77275"]["value"] == "Tân Hồng"


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
    assert by["doiTuongKhacdiaChiChiTiet"]["value"] == "Thôn Đông"  # mapping: chỉ phần dưới xã
    names = [f["name"] for f in out]
    assert names.index("doiTuongKhactinhThanhId") < names.index("doiTuongKhacphuongXaId")
    out, warnings = mapper.enrich_authorized(_fields({"ChuHoSo_HoTen": "Nguyễn Văn An"}))
    assert out == [] and warnings


def test_chu_ho_so_tu_60_tuoi_la_nguoi_cao_tuoi():
    today = date(2026, 11, 25)
    assert mapper.authorized_subject(_fields({"ChuHoSo_NgaySinh": "25/11/1966"}), today) == "Người cao tuổi"
    assert mapper.authorized_subject(_fields({"ChuHoSo_NgaySinh": "26/11/1966"}), today) is None
    assert mapper.authorized_subject(_fields({"ChuHoSo_HoTen": "Nguyễn Văn An"}), today) is None


def test_runner_tach_luot_theo_purpose(monkeypatch):
    calls = []

    async def fake_run(files_by_role, **kwargs):
        calls.append(kwargs)
        if kwargs["fields"] is schema.FIELDS_UYQUYEN:
            return {"fields": [{"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn An"},
                               {"name": "ChuHoSo_SoDinhDanh", "value": "027090001234"},
                               {"name": "ChuHoSo_NgaySinh", "value": "01/01/1950"}]}
        return {"fields": [{"name": "Cccd_HoTen", "value": "Nguyễn Văn An"}]}

    monkeypatch.setattr(runner.runner, "run", fake_run)
    res = asyncio.run(runner.run({}, {"purpose": "authorized_person"}))
    assert calls[-1]["fields"] is schema.FIELDS_UYQUYEN
    assert {f["name"] for f in res["fields"]} == {"doiTuongKhachoTen", "doiTuongKhacsoDinhDanh",
                                                  "doiTuongKhacngaySinh"}
    assert res["authorizedSubject"] == "Người cao tuổi"
    res = asyncio.run(runner.run({}, {}))
    assert calls[-1]["fields"] is schema.FIELDS
    assert calls[-1]["compact_field_fallback"] is runner.ocr_fallback
    assert {f["name"] for f in res["fields"]} == {"Ten2", "nhanTaiNhahoTen"}


def test_fallback_khong_lay_muc_v_tu_van_ban_cam_ket():
    text = ("VĂN BẢN CAM KẾT\nChúng tôi là thành viên hộ gia đình có tên dưới đây:\n1. Ông Nguyễn Văn An\n"
            "- Địa chỉ thường trú: Thôn Đông, xã Tân Hồng, tỉnh Bắc Ninh")
    docs = [{"name": "ho-so.pdf", "text": text}]
    # LLM đã đọc văn bản cam kết → mục V của Đơn KHÔNG vá bằng regex (câu trong văn bản cam kết).
    out = runner.ocr_fallback({"Vbck_ThanhVien": [{"hoTen": "Nguyễn Văn An"}]}, docs)
    assert "Don_ThanhVienHo" not in out
    assert out["Don_DiaChi"] == "Thôn Đông, xã Tân Hồng, tỉnh Bắc Ninh"
    # Không có văn bản cam kết → giữ hành vi fallback chung.
    assert "Don_ThanhVienHo" in runner.ocr_fallback({}, docs)


# ── Đính kèm: bộ mẫu scan chung (chữ bịa) ──
_TRANG = [
    ("Mẫu số 24 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT", 1),
    ("Cam đoan nội dung kê khai trên đơn là đúng sự thật II. XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ", 0),
    ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT QUYỀN SỞ HỮU NHÀ Ở CĐ 123456", 1),
    ("II. Thửa đất, nhà ở và tài sản khác gắn liền với đất Thửa đất số: 12 Tờ bản đồ số: 3", 0),
    ("CÔNG AN PHƯỜNG TÂN HỒNG GIẤY XÁC NHẬN THÔNG TIN VỀ CƯ TRÚ Họ và tên: NGUYỄN VĂN AN", 1),
    ("CĂN CƯỚC CÔNG DÂN Số / No.: 027090001234 Họ và tên / Full name: NGUYỄN VĂN AN", 1),
    ("|", 0),
    ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM VĂN BẢN CAM KẾT Của các thành viên hộ gia đình có chung quyền sử dụng đất", 1),
    ("LỜI CHỨNG CHỨNG THỰC CHỮ KÝ, ĐIỂM CHỈ CỦA NHIỀU NGƯỜI Căn cước công dân số: 027090001234", 0),
    ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM GIẤY ỦY QUYỀN Bên ủy quyền: Nguyễn Văn An", 1),
]
_LOAI = ["don_18", "gcn", "giay_to_thay_doi", "cccd", "vb_cam_ket_ho", "van_ban_dai_dien"]
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


# Nguyên tệp: mỗi dòng nhận tệp một lần — văn bản cam kết trùng dòng 000049 Bản chính với giấy xác nhận cư trú nên chỉ
# thêm dòng 000051.
_DONG = [
    ("TP-H05.000026", "banChinh"),
    ("TP-H05.000040", "banChinh"),
    ("TP-H05.000049", "banChinh"),
    ("TP-H05.000049", "banSao"),
    ("TP-H05.000051", "banChinh"),
    ("TP-H05.000046", "banChinh"),
]


def test_khong_tach_dinh_nguyen_tep_vao_moi_dong_co_giay(monkeypatch):
    calls: list = []
    _patch(monkeypatch, calls)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"},
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        res = asyncio.run(attach.plan(_bo_ho_so(), options))
        assert [(a["componentName"], a["slotKey"]) for a in res["attachments"]] == _DONG
        assert all(a["target"] == "existing" for a in res["attachments"])
        assert all(a["fileIndex"] == 0 and "sourceSegments" not in a for a in res["attachments"])
        assert len({a["documentName"] for a in res["attachments"]}) == len(_DONG)
        assert res["extracted"]["attachmentMode"] == "whole_files"
    assert calls and all(c == phan_trang.SEGMENT_SYSTEM_PROMPT for c in calls)  # MỘT lượt LLM cho cả bộ


def test_tach_moi_giay_mot_muc_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch(monkeypatch, [])
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    rows = [(a["componentName"], a["slotKey"], a["sourceSegments"][0]["pageIndexes"]) for a in res["attachments"]]
    assert rows == [
        ("TP-H05.000026", "banChinh", [0, 1]),   # Đơn + trang cam đoan / xác nhận UBND
        ("TP-H05.000040", "banChinh", [2, 3]),   # GCN nhiều trang
        ("TP-H05.000049", "banChinh", [4]),
        ("TP-H05.000049", "banSao", [5, 6]),     # CCCD + mặt sau trắng → 000049 Bản sao
        ("TP-H05.000049", "banChinh", [7, 8]),   # văn bản cam kết + lời chứng: ĐÍNH KÈM CHUNG hai dòng
        ("TP-H05.000051", "banChinh", [7, 8]),
        ("TP-H05.000046", "banChinh", [9]),
    ]
    assert sorted({p for _, _, ps in rows for p in ps}) == list(range(len(_TRANG)))
    cam_ket = [a for a in res["attachments"] if a["detectedType"] == "vb_cam_ket_ho"]
    assert len({a["documentName"] for a in cam_ket}) == 1  # cùng một giấy, cùng tên
    assert res["extracted"]["attachmentMode"] == "split_documents"


def test_tach_loi_thi_dinh_nguyen_tep_theo_tieu_de_trang(monkeypatch):
    _patch(monkeypatch, [], fail=True)
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    assert all("sourceSegments" not in a for a in res["attachments"])
    assert [(a["componentName"], a["slotKey"]) for a in res["attachments"]] == _DONG
    assert any("đính nguyên tệp" in e for e in res["errors"])


def test_moi_giay_mot_tep_theo_anh_anh_xa(monkeypatch):
    """Hồ sơ mẫu của ảnh ánh xạ: 3 tệp giữ nguyên — Đơn, GCN (trang bổ sung đứng trước bìa), văn bản cam kết."""
    texts = {
        "don.pdf": "Mẫu số 24 ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT " + "x" * 50,
        "gcn.pdf": "TRANG BỔ SUNG GIẤY CHỨNG NHẬN Thửa đất số: 01 " + "x" * 50,
        "vb.pdf": "VĂN BẢN CAM KẾT Của các thành viên hộ gia đình có chung quyền sử dụng đất " + "x" * 50,
    }
    labels = {"don.pdf": "don_18", "gcn.pdf": "gcn", "vb.pdf": "vb_cam_ket_ho"}

    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_chat(*_a, **_k):
        return json.dumps({"giayTo": [{"fileIndex": i, "trangDau": 1, "loai": loai, "ten": ""}
                                      for i, loai in enumerate(labels.values())]})

    monkeypatch.setattr(phan_trang, "ocr_files", fake_ocr)
    monkeypatch.setattr(phan_trang.client, "chat", fake_chat)
    files = [FileItem(name=n, type="application/pdf", dataUrl=_pdf(1), role="") for n in texts]
    for options in ({}, {"splitDocuments": True}):
        res = asyncio.run(attach.plan(files, options))
        assert [(a["fileIndex"], a["componentName"], a["slotKey"], "sourceSegments" in a)
                for a in res["attachments"]] == [
            (0, "TP-H05.000026", "banChinh", False),
            (1, "TP-H05.000040", "banChinh", False),
            (2, "TP-H05.000049", "banChinh", False),
            (2, "TP-H05.000051", "banChinh", False),
        ]


def test_tep_anh_cccd_rieng_vao_dong_ban_sao_000049(monkeypatch):
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
        assert [(a["componentName"], a["slotKey"], "sourceSegments" in a) for a in res["attachments"]] == [
            ("TP-H05.000049", "banSao", False)]


def test_bang_dong_dung_7_thanh_phan_cua_ban_crawl_va_prompt():
    codes = {code for _, code, _, _ in catalog.CATALOG if code}
    assert codes == {"TP-H05.000026", "TP-H05.000049", "TP-H05.000040", "TP-H05.000050", "TP-H05.000046",
                     "TP-H05.000051", "TP-H05.000045"}
    assert catalog.resolve("la_lam") == ("supplementary", "", "banChinh")
    assert catalog.resolve("cccd") == ("existing", "TP-H05.000049", "banSao")
    assert catalog.targets("vb_cam_ket_ho") == [("existing", "TP-H05.000049", "banChinh"),
                                                ("existing", "TP-H05.000051", "banChinh")]
    prompt = phan_trang.SEGMENT_SYSTEM_PROMPT
    assert all(label in prompt for label in catalog.LABELS)
    assert "TRANG BỔ SUNG GIẤY CHỨNG NHẬN" in prompt and "Cam đoan nội dung kê khai" in prompt
    assert "LỜI CHỨNG CHỨNG THỰC" in prompt


def test_tu_khoa_du_phong():
    assert phan_trang.keyword_page_label("CĂN CƯỚC Số định danh cá nhân / Personal identification number " + "x" * 50) \
        == "cccd"
    assert phan_trang.keyword_page_label("GIẤY XÁC NHẬN THÔNG TIN VỀ CƯ TRÚ " + "x" * 50) == "giay_to_thay_doi"
    assert phan_trang.keyword_page_label("Cam đoan nội dung kê khai trên đơn " + "x" * 50) is None
    assert phan_trang.keyword_page_label("Mẫu số 24 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM " + "x" * 50) == "don_18"
    # Văn bản cam kết / lời chứng liệt kê số căn cước nhưng KHÔNG phải thẻ căn cước.
    assert phan_trang.keyword_page_label("VĂN BẢN CAM KẾT Căn cước công dân số: 027090001234 " + "x" * 50) \
        == "vb_cam_ket_ho"
    assert phan_trang.keyword_page_label("LỜI CHỨNG CHỨNG THỰC CHỮ KÝ Căn cước công dân số: 0270 " + "x" * 50) is None
    assert phan_trang.keyword_label_by_filename("van ban cam ket.pdf") == "vb_cam_ket_ho"


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
    assert "văn bản cam kết" in tl["uploadHint"]
