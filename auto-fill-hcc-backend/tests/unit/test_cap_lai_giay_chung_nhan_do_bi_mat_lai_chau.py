"""[Lai Châu] Cấp lại Giấy chứng nhận do bị mất (mã 1.115557).

Khóa theo file mapping "Mapping_CapLaiGCN_DoBiMat_Buoc2" + ảnh ánh xạ đính kèm:
  - process: bộ ô CongDan_* của người viết Đơn Mẫu 16; địa chỉ theo Đơn (thẻ in địa chỉ cũ), thẻ của vợ/chồng scan chung
    không lẫn sang, thiếu thẻ thì lấy Đơn / Mẫu 09 / Mẫu 03a, ô chữ thiếu thì xoá giá trị cổng đổ sẵn;
  - attach: file scan chung 12 trang nộp 2 bản giống hệt → bản 1 dòng Mẫu 16, bản 2 dòng Giấy chứng nhận đã cấp, dòng
    trích đo không tích, "Giấy tờ khác" trống, Ghi chú đề xuất; tệp vượt 6 MB được nén (replaceFiles).

Dữ liệu trong test là PLACEHOLDER, không phải hồ sơ thật của người dân.
"""

import base64

import pytest

from app.pipelines._shared import fold
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.attach import planner
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.process import mapper, runner
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS, link_province_slugs
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "cap-lai-giay-chung-nhan-do-bi-mat-lai-chau"


def _fields(fields: list[dict]) -> dict:
    return {item["name"]: item for item in fields}


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields if not item.get("clear")}


def _facts(**extra) -> list[dict]:
    """Bộ hồ sơ như mẫu: thẻ CCCD (địa chỉ cũ) + Đơn Mẫu 16 viết tay (địa chỉ mới) + Mẫu 09 + GCN đứng tên vợ chồng."""
    base = {
        "Cccd_HoTen": "LÊ VĂN MẪU",
        "Cccd_SoDinhDanh": "012000000001",
        "Cccd_NgaySinh": "1/2/1990",
        "Cccd_GioiTinh": "Nam",
        "Cccd_NgayCap": "03/12/2021",
        "Cccd_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
        "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Thị trấn Cũ", "chiTietDuoiXa": "Bản Cũ"},
        "Don_HoTen": "LÊ VĂN MẪU",
        "Don_NgaySinh": "01-02-1990",
        "Don_SoGiayTo": "0120.0000.0001",
        "Don_CoQuanCap": "Cục Cảnh Sát",
        "Don_NgayCap": "03-12-2021",
        "Don_DiaChi": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Mẫu", "chiTietDuoiXa": "Bản Mẫu Hai"},
        "Don_DienThoai": "0900.000.001",
        "DonKhac_HoTen": "Lê Văn Mẫu",
        "DonKhac_SoCccd": "012000000001",
        "DonKhac_DienThoai": "0900000002",
        "Gcn_HoTen": "Lê Văn Mẫu",
        "NguoiSdd_GioiTinh": "Nam",
    }
    base.update(extra)
    return [{"name": name, "value": value} for name, value in base.items() if value is not None]


def _enrich(facts: list[dict], options: dict | None = None) -> tuple[dict, list[str], dict]:
    fields, warnings = mapper.enrich(facts, options)
    return _values(fields), warnings, _fields(fields)


_NO_CARD = {key: None for key in (
    "Cccd_HoTen", "Cccd_SoDinhDanh", "Cccd_NgaySinh", "Cccd_GioiTinh", "Cccd_NgayCap", "Cccd_NoiCap", "Cccd_NoiCuTru",
)}


# ---------------------------------------------------------------- process/mapper


def test_mapper_ho_so_mau_the_va_don():
    values, warnings, _ = _enrich(_facts())

    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_soCmnd"] == values["CongDan_soCCCD"] == "012000000001"
    assert values["CongDan_ngayCapCmnd"] == "03/12/2021"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Điện thoại theo Đơn Mẫu 16 trước Mẫu 09.
    assert values["CongDan_diDong"] == "0900000001"
    # Cá nhân, Đơn bỏ trống mã số thuế, thẻ do Cục Cảnh sát cấp; Quốc gia để trống theo mapping.
    for name in ("CongDan_tenCoQuanToChuc", "CongDan_maSoThueNguoiNop", "CongDan_maTinhCapCMND", "CongDan_maDMQuocGia",
                 "CongDan_danTocCongDan"):
        assert name not in values
    assert any("Dân tộc" in warning for warning in warnings)


def test_mapper_dia_chi_theo_don_khong_theo_the_cu():
    values, _, _ = _enrich(_facts())

    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu"
    assert values["CongDan_maPhuongXa"] == "Xã Mẫu"
    assert values["CongDan_diaChi"] == "Bản Mẫu Hai"
    assert values["CongDan_noiOHienTai"] == "Bản Mẫu Hai, Xã Mẫu, Tỉnh Lai Châu"
    assert values["CongDan_diaChiThuongTru"] == "Bản Mẫu Hai, Xã Mẫu, Tỉnh Lai Châu"


def test_mapper_don_viet_tay_rot_chu_cuoi_ten_ban_thi_lay_ban_danh_may():
    # OCR đọc "Bản Mẫu Tình" viết tay thành "Bản Mẫu Tỉnh" → LLM bỏ chữ cuối; Mẫu 03a đánh máy cùng xã ghi đủ.
    facts = _facts(
        Don_DiaChi={"tinh": "Lai Châu", "xa": "Xã Mẫu", "chiTietDuoiXa": "Bản Mẫu"},
        DonKhac_DiaChi={"tinh": "tỉnh Lai Châu", "xa": "xã Mẫu", "chiTietDuoiXa": "Bản Mẫu Tình"},
    )
    values, _, _ = _enrich(facts)
    assert values["CongDan_diaChi"] == "Bản Mẫu Tình"
    assert values["CongDan_diaChiThuongTru"] == "Bản Mẫu Tình, Xã Mẫu, Tỉnh Lai Châu"

    # Khác xã, hoặc chi tiết không phải bản đầy đủ hơn → giữ Đơn.
    for other in ({"tinh": "Lai Châu", "xa": "Xã Khác", "chiTietDuoiXa": "Bản Mẫu Tình"},
                  {"tinh": "Lai Châu", "xa": "Xã Mẫu", "chiTietDuoiXa": "Bản Mẫuu"}):
        values, _, _ = _enrich(_facts(Don_DiaChi={"tinh": "Lai Châu", "xa": "Xã Mẫu", "chiTietDuoiXa": "Bản Mẫu"},
                                      DonKhac_DiaChi=other))
        assert values["CongDan_diaChi"] == "Bản Mẫu"


def test_mapper_khong_the_lay_nhan_than_tu_don_mau_16():
    values, warnings, fields = _enrich(_facts(**_NO_CARD))

    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1990"
    assert values["CongDan_soCmnd"] == "012000000001"
    assert values["CongDan_ngayCapCmnd"] == "03/12/2021"
    # Đơn ghi tắt "Cục Cảnh Sát" → tên cơ quan đầy đủ như mapping.
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Giới tính rơi về danh xưng "Ông" trên Giấy chứng nhận.
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert not any(item.get("markEmpty") for item in fields.values())
    assert not any("Họ và tên" in warning for warning in warnings)


def test_mapper_don_bo_trong_thi_lay_mau_09_03a():
    facts = _facts(
        **_NO_CARD, Don_NgaySinh=None, Don_SoGiayTo=None, Don_CoQuanCap=None, Don_NgayCap=None, Don_DiaChi=None,
        Don_DienThoai=None, DonKhac_NgaySinh="01/02/1990", DonKhac_NgayCap="03/12/2021",
        DonKhac_NoiCap="CCS QLHC về TTXH",
        DonKhac_DiaChi={"tinh": "Lai Châu", "xa": "xã Mẫu", "chiTietDuoiXa": "Bản Mẫu Hai"},
    )
    values, _, _ = _enrich(facts)

    assert values["CongDan_soCmnd"] == "012000000001"
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1990"
    assert values["CongDan_ngayCapCmnd"] == "03/12/2021"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["CongDan_maPhuongXa"] == "Xã Mẫu"
    assert values["CongDan_diaChi"] == "Bản Mẫu Hai"
    assert values["CongDan_diDong"] == "0900000002"


def test_mapper_the_cua_vo_chong_scan_chung_bi_bo():
    # LLM lỡ đọc thẻ của người đồng sử dụng (tên + số khác người viết đơn) → bỏ cả bộ Cccd_*, lấy theo Đơn.
    facts = _facts(Cccd_HoTen="TRẦN THỊ MẪU", Cccd_SoDinhDanh="012000000002", Cccd_GioiTinh="Nữ",
                   Cccd_NgaySinh="05/06/1991")
    values, _, _ = _enrich(facts)

    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"
    assert values["CongDan_soCmnd"] == "012000000001"
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"


def test_mapper_ten_the_ocr_lech_nhung_trung_so_van_dung():
    values, _, _ = _enrich(_facts(Cccd_HoTen="LÊ VĂN MẨU"))

    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẨU"
    assert values["CongDan_ngayCapCmnd"] == "03/12/2021"


def test_mapper_giay_kem_cua_nguoi_khac_va_gcn_cua_vo_bi_bo():
    facts = _facts(
        **_NO_CARD, Don_DienThoai=None, DonKhac_HoTen="Trần Thị Mẫu", DonKhac_SoCccd="012000000002",
        Gcn_HoTen="Trần Thị Mẫu", NguoiSdd_GioiTinh="Nữ",
    )
    values, _, _ = _enrich(facts)

    assert "CongDan_diDong" not in values
    assert "CongDan_gioiTinhCongDan" not in values
    assert values["CongDan_soCmnd"] == "012000000001"


def test_mapper_khong_nguon_thi_xoa_o_cong_do_san():
    facts = _facts(**_NO_CARD, Don_NgaySinh=None, DonKhac_NgaySinh=None, Don_DienThoai=None, DonKhac_DienThoai=None)
    _, warnings, fields = _enrich(facts)

    assert fields["CongDan_ngaySinhCongDan"] == {
        "name": "CongDan_ngaySinhCongDan", "comp": "dom-input", "value": "", "clear": True, "markEmpty": True,
    }
    assert fields["CongDan_diDong"]["clear"] is True and "markEmpty" not in fields["CongDan_diDong"]
    assert fields["CongDan_maSoThueNguoiNop"]["clear"] is True
    # Ô chọn không bao giờ phát clear (trợ lý chưa bỏ chọn được).
    assert all(item["comp"] == "dom-input" for item in fields.values() if item.get("clear"))
    assert any("Ngày sinh" in warning for warning in warnings)


def test_mapper_tai_khoan_la_nguoi_nop_thi_giu_o_cong():
    options = {"formContext": {"applicantIdentityNumber": "012 000 000 001"}}
    _, warnings, fields = _enrich(_facts(Don_DienThoai=None, DonKhac_DienThoai=None), options)

    assert "CongDan_diDong" not in fields
    assert not any(item.get("clear") for item in fields.values())
    assert warnings == []


def test_mapper_ma_so_thue_va_to_chuc():
    values, _, _ = _enrich(_facts(Don_MaSoThue="0100000001", ToChuc_Ten="Hợp tác xã Mẫu", Don_Email="mau @example.com"))
    assert values["CongDan_maSoThueNguoiNop"] == "0100000001"
    assert values["CongDan_tenCoQuanToChuc"] == "Hợp tác xã Mẫu"
    assert values["CongDan_email"] == "mau@example.com"

    values, _, _ = _enrich(_facts(Don_MaSoThue="1234"))
    assert "CongDan_maSoThueNguoiNop" not in values


def test_schema_moi_o_ui_deu_co_comp_va_khong_phat_o_khong_nguon():
    _, _, fields = _enrich(_facts())

    assert set(fields) <= set(UI_COMP_BY_NAME)
    for name in ("CongDan_fax", "CongDan_website", "CongDan_soGCNGP", "CongDan_ngayCapGCNGP",
                 "CongDan_noiCapGCNGP", "CongDan_maDMDiaChi", "CongDan_diaChiNuocNgoai", "CongDan_maDMQuocGia"):
        assert name not in UI_COMP_BY_NAME
    assert not any(name.startswith("ChuHoSo_") for name in UI_COMP_BY_NAME)
    assert {"Don_DiaChi", "Don_SoGiayTo", "DonKhac_DiaChi", "NguoiSdd_GioiTinh", "Don_MaSoThue"} <= ALLOWED


# ---------------------------------------------------------------- process/runner: tệp trùng chỉ OCR một lần


async def test_ocr_tep_trung_chi_mot_lan_va_bo_tai_lieu_trung(monkeypatch):
    from app.services import ocr

    seen: list[list[str]] = []

    async def fake_ocr(files, **_):
        seen.append([item["name"] for item in files])
        return [{"name": item["name"], "text": f"chữ của {item['name']}", "provider": "tiengnoi"} for item in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    files = [
        {"name": "a.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QQ=="},
        {"name": "b.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QQ=="},
        {"name": "c.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,Qg=="},
    ]
    results = await runner.ocr_unique(files)

    assert seen == [["a.pdf", "c.jpg"]]
    assert [item["name"] for item in results] == ["a.pdf", "b.pdf", "c.jpg"]
    assert results[1]["text"] == results[0]["text"]

    documents = [{"name": "a.pdf", "text": "Đơn  mẫu\n16"}, {"name": "b.pdf", "text": "Đơn mẫu 16"},
                 {"name": "c.jpg", "text": "CCCD"}]
    assert [d["name"] for d in runner.drop_duplicate_documents(documents)] == ["a.pdf", "c.jpg"]


# ---------------------------------------------------------------- attach/planner

_PAGES = [
    "Mẫu số 16. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI\n"
    "I. Người sử dụng đất ... lập danh sách theo Bảng 16a đính kèm",
    "(1) Giấy chứng nhận đã cấp;\nCam đoan nội dung kê khai trên đơn\nHướng dẫn kê khai đơn: số vào sổ cấp Giấy "
    "chứng nhận ... Số phát hành Giấy chứng nhận (Số seri)",
    "Bảng 16a: Danh sách những người sử dụng đất, tài sản gắn liền với đất\nSTT Tên người sử dụng đất",
    "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nHọ và tên / Full name:\nLÊ VĂN MẪU",
    "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nHọ và tên / Full name:\nTRẦN THỊ MẪU",
    "Nội dung thay đổi và cơ sở pháp lý\nGIẤY CHỨNG NHẬN\nQUYỀN SỬ DỤNG ĐẤT\nQUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN "
    "LIỀN VỚI ĐẤT",
    "II. Thửa đất, nhà ở và tài sản khác gắn liền với đất\nIII. Sơ đồ thửa đất\nIV. Những thay đổi sau khi cấp giấy "
    "chứng nhận\nSố vào sổ cấp GCN: CH00000",
    "(Tiếp theo trang số: ...) Trang số: 1\nI - NGƯỜI SỬ DỤNG ĐẤT\nII - THỬA ĐẤT\nSố phát hành GCN QSDĐ Số vào sổ "
    "cấp GCN QSDĐ\nIII - NHỮNG THAY ĐỔI TRONG QUÁ TRÌNH SỬ DỤNG ĐẤT VÀ GHI CHÚ",
    "Mẫu số 03a\nPHIẾU YÊU CẦU XÓA ĐĂNG KÝ BIỆN PHÁP BẢO ĐẢM BẰNG QUYỀN SỬ DỤNG ĐẤT\n4. Giấy tờ kèm theo: Giấy chứng "
    "nhận quyền sử dụng đất quyền sở hữu nhà ở và tài sản khác gắn liền với đất số AA 000000",
    "PHẦN CHỨNG NHẬN CỦA CƠ QUAN ĐĂNG KÝ\nChứng nhận đã xóa đăng ký biện pháp bảo đảm theo nội dung được kê khai",
    "Mẫu số 09. Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp\nĐƠN XIN XÁC NHẬN LẠI THỜI HẠN SỬ DỤNG ĐẤT NÔNG "
    "NGHIỆP\n3.7. Địa điểm thửa đất",
    "3.8. Giấy chứng nhận về quyền sử dụng đất đã cấp: Số phát hành ... Số vào sổ ...\n4. Nội dung đề nghị xác nhận "
    "lại thời hạn sử dụng đất:",
]
_COMPOUND = "\n\n".join(f"───── Trang {i}/{len(_PAGES)} ─────\n{page}" for i, page in enumerate(_PAGES, 1))
_TEXTS = {
    "ho-so-1.pdf": _COMPOUND,
    "ho-so-2.pdf": _COMPOUND,
    "don.pdf": "\n\n".join(f"───── Trang {i}/2 ─────\n{page}" for i, page in enumerate(_PAGES[:2], 1)),
    "gcn.pdf": "\n\n".join(f"───── Trang {i}/2 ─────\n{page}" for i, page in enumerate(_PAGES[5:7], 1)),
    "so-dia-chinh.pdf": _PAGES[7],
    "bang-16a.pdf": _PAGES[2],
    "trich-do.pdf": "MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH\nThửa đất số 1, tờ bản đồ số 2",
    "cccd.jpg": _PAGES[3],
    "mau-03a.pdf": _PAGES[8],
    "anh-khac.jpg": "Biên lai thu phí",
}


def _files(names: list[str], same: tuple[str, ...] = ("ho-so-1.pdf", "ho-so-2.pdf")) -> list[dict]:
    # Hai bản file chung giống hệt nhau → cùng dataUrl; các tệp khác mỗi tệp một nội dung.
    return [{"name": name, "type": "application/pdf",
             "dataUrl": "data:application/pdf;base64," + ("SE9TTw==" if name in same else
                                                           base64.b64encode(name.encode()).decode())}
            for name in names]


def _ocr(names: list[str]) -> list[dict]:
    return [{"name": name, "text": _TEXTS[name]} for name in names]


def _rows(attachments: list[dict]) -> list[tuple[str, int]]:
    return [(item["fileName"], item["slotIndex"]) for item in attachments if item["target"] == "fixed-slot"]


def test_bang_3_dong_dung_ten_va_tu_khoa_khong_chong_nhau():
    assert [slot["slotIndex"] for slot in planner.SLOTS] == [0, 1, 2]
    assert planner.SLOTS[0]["slotName"] == "Mẫu số 16. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Bản chính)"
    assert planner.SLOTS[1]["slotName"] == "Giấy chứng nhận đã cấp (bản gốc) (Bản chính)"
    assert planner.SLOTS[2]["slotName"].startswith("Mảnh trích đo bản đồ địa chính thửa đất")
    for slot in planner.SLOTS:
        for keyword in slot["slotKeywords"]:
            owners = [other["slotIndex"] for other in planner.SLOTS if keyword in fold(other["slotName"])]
            assert owners == [slot["slotIndex"]], keyword


def test_nhan_loai_tung_trang_file_chung():
    assert planner.page_kinds(_COMPOUND) == [
        "don_dang_ky_bien_dong", "don_dang_ky_bien_dong", "bang_16a", "identity", "identity", "giay_chung_nhan",
        "giay_chung_nhan", "so_dia_chinh", "mau_03a", "mau_03a", "mau_09", "mau_09",
    ]
    # Trang không tiêu đề nối theo trang trước; ảnh/1 trang không có dòng ngăn → cả chữ là một trang.
    assert planner.page_kinds("───── Trang 1/2 ─────\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI\n───── Trang 2/2 ─────\nchữ ký") == [
        "don_dang_ky_bien_dong", "don_dang_ky_bien_dong"]
    assert planner.page_kinds(_TEXTS["cccd.jpg"]) == ["identity"]


def test_ho_so_mau_hai_ban_giong_nhau_chia_dong_1_va_dong_2():
    names = ["ho-so-1.pdf", "ho-so-2.pdf"]
    attachments, warnings, classified = planner.build_plan_items(_files(names), _ocr(names), {})

    # Bản 1 → dòng Mẫu 16, bản 2 → dòng Giấy chứng nhận đã cấp; trích đo không tích, Giấy tờ khác trống.
    assert _rows(attachments) == [("ho-so-1.pdf", 0), ("ho-so-2.pdf", 1)]
    assert all(item["tickRow"] for item in attachments)
    assert not [item for item in attachments if item["target"] == "new"]
    assert [entry["slotIndex"] for entry in classified] == [[0], [1]]
    note = next(warning for warning in warnings if warning.startswith("Ghi chú đề xuất"))
    assert ("Mẫu số 16 (tr.1-2), Bảng 16a (tr.3), CCCD (tr.4-5), bản sao Giấy chứng nhận (tr.6-7), Sổ địa chính (tr.8), "
            "Mẫu số 03a (tr.9-10), Mẫu số 09 (tr.11-12)") in note
    assert "ho-so-2.pdf trùng nội dung, nộp cho mục Giấy chứng nhận đã cấp" in note
    assert not any("Không xác định" in warning or "Chưa nhận ra" in warning for warning in warnings)


def test_mot_ban_file_chung_dinh_ca_hai_dong():
    attachments, _, _ = planner.build_plan_items(_files(["ho-so-1.pdf"]), _ocr(["ho-so-1.pdf"]), {})
    assert _rows(attachments) == [("ho-so-1.pdf", 0), ("ho-so-1.pdf", 1)]


def test_ban_thu_ba_trung_noi_dung_khong_dinh_them():
    names = ["ho-so-1.pdf", "ho-so-2.pdf", "ho-so-3.pdf"]
    files = _files(names, same=tuple(names))
    attachments, warnings, classified = planner.build_plan_items(files, _ocr(names[:2]) + [
        {"name": "ho-so-3.pdf", "text": _COMPOUND}], {})

    assert _rows(attachments) == [("ho-so-1.pdf", 0), ("ho-so-2.pdf", 1)]
    assert classified[2]["skipped"] is True and classified[2]["reason"] == "duplicate"
    assert any("ho-so-3.pdf" in warning and "trùng nội dung" in warning for warning in warnings)


def test_giay_le_vao_dung_dong_hoac_giay_to_khac():
    names = ["don.pdf", "gcn.pdf", "trich-do.pdf", "cccd.jpg", "mau-03a.pdf", "so-dia-chinh.pdf", "bang-16a.pdf"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    assert _rows(attachments) == [("don.pdf", 0), ("gcn.pdf", 1), ("trich-do.pdf", 2)]
    # Dòng 1 / dòng 2 đã có tệp → Bảng 16a, Sổ địa chính đứng riêng vào "Giấy tờ khác" (ô dòng chỉ 1 tệp).
    others = [item["componentName"] for item in attachments if item["target"] == "new"]
    assert others == [
        "Căn cước công dân - Lê Văn Mẫu",
        "Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a)",
        "Trang sổ địa chính",
        "Bảng 16a - Danh sách người sử dụng đất",
    ]
    assert not any(warning.startswith("Ghi chú đề xuất") for warning in warnings)


def test_so_dia_chinh_le_len_dong_2_khi_khong_co_gcn():
    names = ["don.pdf", "so-dia-chinh.pdf"]
    attachments, _, _ = planner.build_plan_items(_files(names), _ocr(names), {})
    assert _rows(attachments) == [("don.pdf", 0), ("so-dia-chinh.pdf", 1)]


def test_khong_co_don_thi_canh_bao_va_tep_la_vao_giay_to_khac():
    names = ["gcn.pdf", "anh-khac.jpg"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    assert _rows(attachments) == [("gcn.pdf", 1)]
    assert attachments[1]["target"] == "new" and attachments[1]["componentName"] == "anh-khac"
    assert any("Mẫu số 16" in warning for warning in warnings)
    assert any("Giấy tờ khác" in warning for warning in warnings)


def test_llm_chi_cho_tep_luat_khong_nhan_ra():
    names = ["anh-khac.jpg"]
    attachments, _, classified = planner.build_plan_items(_files(names), _ocr(names), {0: "don_dang_ky_bien_dong"})
    assert _rows(attachments) == [("anh-khac.jpg", 0)]
    assert classified[0]["source"] == "llm"


def test_tep_qua_6mb_nen_lot_thi_van_dinh_khong_lot_thi_loai():
    oversized = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    files = [{"name": "don.pdf", "type": "application/pdf", "dataUrl": oversized}]

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(["don.pdf"]), {})
    assert attachments == [] and "6 MB" in warnings[0] and classified[0]["skipped"] is True

    replaced = {"0": {"name": "don.pdf", "bytes": 2_000_000}}
    attachments, warnings, _ = planner.build_plan_items(files, _ocr(["don.pdf"]), {}, replaced)
    assert _rows(attachments) == [("don.pdf", 0)]
    assert not any("6 MB" in warning for warning in warnings)

    replaced = {"0": {"name": "don.pdf", "bytes": 7_000_000}}
    attachments, warnings, _ = planner.build_plan_items(files, _ocr(["don.pdf"]), {}, replaced)
    assert attachments == [] and "nén hết mức vẫn" in warnings[0]


async def test_nen_tep_vuot_6mb_moi_noi_dung_mot_lan(monkeypatch):
    calls: list[int] = []

    def fake_shrink(raw):
        calls.append(len(raw))
        return b"%PDF-nho", "màu 150dpi q75"

    monkeypatch.setattr(planner, "_shrink", fake_shrink)
    big = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    files = [
        {"name": "ho-so-1.pdf", "type": "application/pdf", "dataUrl": big},
        {"name": "ho-so-2.pdf", "type": "application/pdf", "dataUrl": big},
        {"name": "nho.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QQ=="},
    ]
    errors: list[str] = []
    replaced = await planner.shrink_oversized(files, errors)

    assert len(calls) == 1 and errors == []
    assert set(replaced) == {"0", "1"}
    assert replaced["1"]["name"] == "ho-so-2.pdf" and replaced["1"]["bytes"] == len(b"%PDF-nho")
    assert base64.b64decode(replaced["0"]["dataUrl"].split(",", 1)[1]) == b"%PDF-nho"


# ---------------------------------------------------------------- registry + ke_khai_links


def test_registry_va_ke_khai_links_cung_key():
    procedure = get_procedure(KEY)

    assert procedure is not None
    assert procedure["label"] == "[Lai Châu] Cấp lại Giấy chứng nhận do bị mất"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["dichvucong.laichau.gov.vn"]
    assert procedure["detect"]["textPriority"] is True
    assert callable(get_pipeline(KEY))
    assert callable(get_attach_pipeline(KEY))

    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.115557"
    assert link["label"] == "Lai Châu - Cấp lại Giấy chứng nhận do bị mất"
    # Nộp tại Sở, chỉ tài khoản Lai Châu (tiền tố nhãn).
    assert link["needsAgencySelect"] is True and link["selectSo"] is True
    assert link_province_slugs(link, {}) == ["laichau"]
    page = "Thông tin người nộp hồ sơ 1.115557 - Cấp lại Giấy chứng nhận do bị mất Nơi tiếp nhận"
    assert all(fold(phrase) in fold(page) for phrase in procedure["detect"]["textIncludes"])
    assert link["code"] in procedure["detect"]["textIncludes"]


# ---------------------------------------------------------------- trợ lý người dân


def test_tro_ly_cung_key_chon_so_va_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(KEY)
    assert procedure is not None
    assert procedure["provinceOnly"] == ["laichau"]
    # selectSo của ke_khai_links → DVCQG chọn Tỉnh Lai Châu, gạt "Sở", thẻ đầu.
    assert procedure["needsAgencySelect"] is True and procedure["agencyProvince"] == "Lai Châu"
    assert procedure["agencyProvinceOnly"] is True and procedure["agencySoFirst"] is True
    assert procedure["laiChauFeeStep"]
    assert procedure["detect"] == get_procedure(KEY)["detect"]
    assert procedure["keKhaiUrl"] == next(item["url"] for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert get_procedure(KEY)["label"] == "[Lai Châu] " + procedure["label"]
    assert handfree.get_pipeline(KEY) is get_pipeline(KEY)
    assert handfree.get_attach_pipeline(KEY) is get_attach_pipeline(KEY)
    assert handfree.is_allowed_in_province(procedure, "laichau")
    assert not handfree.is_allowed_in_province(procedure, "quangninh")
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don"}
    assert PROCEDURE_HMONG[KEY] and PROCEDURE_HINTS[KEY]


@pytest.mark.parametrize("phrase", ["mất sổ đỏ", "cấp lại sổ đỏ ở lai châu"])
def test_tro_ly_goi_y_chon_thu_tuc(phrase):
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS

    assert phrase in PROCEDURE_HINTS[KEY]
