"""[Lai Châu] Đăng ký, cấp GCN đối với toàn bộ diện tích đất đang sử dụng (điểm b, c khoản 2 Điều 24 NĐ 101/2024,
mã 1.115590).

Khóa theo file mapping "Mapping_1.115590_LaiChau_Buoc2_NguoiNop" + ảnh ánh xạ đính kèm:
  - process: bộ ô CongDan_* của người nộp (= người sử dụng đất đứng tên Đơn), ghép Đơn + Giấy ủy quyền + GCN khi hồ
    sơ không có thẻ, không lẫn người được ủy quyền;
  - attach: bảng 5 dòng fixed-slot có tick, file chung Đơn + Giấy ủy quyền lên cả dòng 1 và dòng 3, dòng 5 (giấy tờ
    phần diện tích tăng thêm) bỏ trống khi không có, CCCD vào "Giấy tờ khác".

Dữ liệu trong test là PLACEHOLDER, không phải hồ sơ thật của người dân.
"""

import base64

from app.pipelines._shared import fold
from app.pipelines.dang_ky_cap_giay_chung_nhan_doi_voi_toan_bo_dien_tich_dat_lai_chau.attach import planner
from app.pipelines.dang_ky_cap_giay_chung_nhan_doi_voi_toan_bo_dien_tich_dat_lai_chau.process import mapper
from app.pipelines.dang_ky_cap_giay_chung_nhan_doi_voi_toan_bo_dien_tich_dat_lai_chau.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-cap-giay-chung-nhan-doi-voi-toan-bo-dien-tich-dat-lai-chau"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _facts(**extra) -> list[dict]:
    """Bộ hồ sơ như mẫu: KHÔNG có thẻ CCCD, nhân thân ghép từ Đơn + Giấy ủy quyền + GCN."""
    base = {
        "Don_HoTen": "TRẦN THỊ MẪU",
        "Don_SoGiayTo": "CCCD: 012000000001",
        "Don_DiaChi": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Mẫu", "diaChi": "Bản Mẫu Một"},
        "Don_MaSoThue": "012.000.000001",
        "Don_DienThoai": "0900.000.001",
        "UyQuyen_HoTen": "Trần Thị Mẫu",
        "UyQuyen_NgaySinh": "1/2/1970",
        "UyQuyen_SoCccd": "012000000001",
        "UyQuyen_NgayCap": "03/04/2021",
        "UyQuyen_NoiCap": "Cục cảnh sát QLHC về TTXH",
        "UyQuyen_ThuongTru": "Tổ 1, phường Mẫu, thị xã Cũ, tỉnh Lai Châu",
        "Gcn_HoTen": "Trần Thị Mẫu",
        "Gcn_SoCccdMoi": "012000000001",
        "Gcn_NgayCapCccd": "03/04/2021",
        "Gcn_NoiCapCccd": "Cục cảnh sát quản lý hành chính về trật tự xã hội",
        "Gcn_ThuongTruMoi": "Tổ 1, phường Mẫu, thị xã Cũ, tỉnh Lai Châu",
        "NguoiSdd_GioiTinh": "Nữ",
    }
    base.update(extra)
    return [{"name": name, "value": value} for name, value in base.items() if value is not None]


# ---------------------------------------------------------------- process/mapper


def test_mapper_ho_so_khong_the_ghep_don_uy_quyen_gcn():
    values = _values(mapper.enrich(_facts()))

    assert values["CongDan_tenCongDan"] == "TRẦN THỊ MẪU"
    # Đơn/GCN chỉ ghi năm sinh → ngày sinh đầy đủ lấy từ Giấy ủy quyền, chuẩn dd/mm/yyyy.
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1970"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_soCmnd"] == values["CongDan_soCCCD"] == "012000000001"
    assert values["CongDan_ngayCapCmnd"] == "03/04/2021"
    # Giấy ủy quyền viết tắt → cổng nhận tên đầy đủ.
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["CongDan_maSoThueNguoiNop"] == "012000000001"
    assert values["CongDan_diDong"] == "0900000001"
    assert values["CongDan_maDMQuocGia"] == "Việt Nam"
    # Cá nhân + CCCD do Cục Cảnh sát cấp → hai ô này để trống; dân tộc không có nguồn.
    assert "CongDan_tenCoQuanToChuc" not in values
    assert "CongDan_maTinhCapCMND" not in values
    assert "CongDan_danTocCongDan" not in values
    assert "CongDan_email" not in values


def test_mapper_dia_chi_theo_don_thuong_tru_theo_uy_quyen():
    values = _values(mapper.enrich(_facts()))

    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu"
    assert values["CongDan_maPhuongXa"] == "Xã Mẫu"
    assert values["CongDan_diaChi"] == "Bản Mẫu Một"
    assert values["CongDan_noiOHienTai"] == "Bản Mẫu Một, Xã Mẫu, Tỉnh Lai Châu"
    # Ô "Địa chỉ thường trú" theo mapping: thẻ → Giấy ủy quyền (chép nguyên văn) → GCN → Đơn.
    assert values["CongDan_diaChiThuongTru"] == "Tổ 1, phường Mẫu, thị xã Cũ, tỉnh Lai Châu"


def test_mapper_khong_lay_nguoi_duoc_uy_quyen():
    facts = _facts(
        UyQuyen_HoTen="Lê Văn Đại Diện",
        UyQuyen_NgaySinh="05/06/1990",
        UyQuyen_SoCccd="012000000009",
        UyQuyen_ThuongTru="Tổ 9, phường Khác, tỉnh Lai Châu",
        Don_SoGiayTo=None,
        Gcn_SoCccdMoi=None,
    )
    values = _values(mapper.enrich(facts))

    assert values["CongDan_tenCongDan"] == "TRẦN THỊ MẪU"
    assert "CongDan_ngaySinhCongDan" not in values
    assert "CongDan_soCmnd" not in values
    # Thường trú rơi về trang thay đổi của GCN, không lấy địa chỉ người được ủy quyền.
    assert values["CongDan_diaChiThuongTru"] == "Tổ 1, phường Mẫu, thị xã Cũ, tỉnh Lai Châu"


def test_mapper_gcn_bo_cmnd_cu_va_chi_co_nam_sinh():
    facts = _facts(
        UyQuyen_HoTen=None, UyQuyen_NgaySinh=None, UyQuyen_SoCccd=None, UyQuyen_NgayCap=None,
        UyQuyen_NoiCap=None, UyQuyen_ThuongTru=None, Don_SoGiayTo=None, Don_MaSoThue=None,
    )
    values = _values(mapper.enrich(facts))

    assert values["CongDan_soCmnd"] == "012000000001"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert "CongDan_ngaySinhCongDan" not in values
    assert "CongDan_maSoThueNguoiNop" not in values
    assert mapper._date("1970") is None


def test_mapper_co_the_cccd_uu_tien_the_va_bo_the_nguoi_khac():
    own_card = _facts(
        Cccd_HoTen="Trần Thị Mẫu", Cccd_SoDinhDanh="012000000001", Cccd_NgaySinh="01/02/1970",
        Cccd_GioiTinh="Nữ", Cccd_DanToc="Kinh", Cccd_NgayCap="03/04/2021",
        Cccd_NoiCuTru={"tinh": "Tỉnh Lai Châu", "xa": "Xã Mẫu", "diaChi": "Bản Mẫu Hai"},
    )
    values = _values(mapper.enrich(own_card))
    assert values["CongDan_danTocCongDan"] == "Kinh"
    # Địa chỉ 3 ô vẫn theo Đơn; ô thường trú theo thẻ.
    assert values["CongDan_diaChi"] == "Bản Mẫu Một"
    assert values["CongDan_diaChiThuongTru"] == "Bản Mẫu Hai, Xã Mẫu, Tỉnh Lai Châu"

    other_card = _facts(Cccd_HoTen="Lê Văn Đại Diện", Cccd_SoDinhDanh="012000000009", Cccd_GioiTinh="Nam")
    values = _values(mapper.enrich(other_card))
    assert values["CongDan_tenCongDan"] == "TRẦN THỊ MẪU"
    assert values["CongDan_soCmnd"] == "012000000001"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"


def test_mapper_to_chuc_va_email():
    values = _values(mapper.enrich(_facts(ToChuc_Ten="Hợp tác xã Mẫu", Don_Email="mau @example.com")))

    assert values["CongDan_tenCoQuanToChuc"] == "Hợp tác xã Mẫu"
    assert values["CongDan_email"] == "mau@example.com"


def test_schema_moi_o_ui_deu_co_comp_va_khong_phat_o_khong_nguon():
    values = _values(mapper.enrich(_facts()))

    assert set(values) <= set(UI_COMP_BY_NAME)
    for name in ("CongDan_fax", "CongDan_website", "CongDan_soGCNGP", "CongDan_ngayCapGCNGP",
                 "CongDan_noiCapGCNGP", "CongDan_maDMDiaChi", "CongDan_diaChiNuocNgoai"):
        assert name not in UI_COMP_BY_NAME
    assert {"Don_DiaChi", "UyQuyen_NgaySinh", "Gcn_SoCccdMoi", "NguoiSdd_GioiTinh"} <= ALLOWED


# ---------------------------------------------------------------- attach/planner

_TEXTS = {
    "don.pdf": "Mẫu số 16. Đơn đăng ký biến động đất đai\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n"
               "IV. Giấy tờ liên quan: (1) Giấy chứng nhận đã cấp (3) phiếu đo đạc chỉnh lý thửa đất",
    "don-uy-quyen.pdf": "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n...\nGIẤY ỦY QUYỀN\nTôi: Trần Thị Mẫu\n"
                        "Bằng giấy này tôi ủy quyền cho\nLỜI CHỨNG CỦA CÔNG CHỨNG VIÊN",
    "uy-quyen.pdf": "GIẤY ỦY QUYỀN\nTôi: Trần Thị Mẫu Căn cước công dân số 012000000001\nGiấy chứng nhận quyền sử dụng đất",
    "gcn.pdf": "IV. Những thay đổi sau khi cấp giấy chứng nhận\nGIẤY CHỨNG NHẬN\nQUYỀN SỬ DỤNG ĐẤT\nSố vào sổ cấp GCN: CH0",
    "phieu-do-dac.pdf": "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT\n5. Loại giấy tờ: Giấy chứng nhận QSD đất số AA 000000",
    "chuyen-nhuong.pdf": "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT\nphần diện tích tiếp giáp",
    "cccd.pdf": "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name:\nTRẦN THỊ MẪU\nNgày sinh",
    "anh-khac.jpg": "Biên lai thu phí",
}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QQ=="} for name in names]


def _ocr(names: list[str]) -> list[dict]:
    return [{"name": name, "text": _TEXTS[name]} for name in names]


def test_bang_5_dong_dung_ten_va_tu_khoa_khong_chong_nhau():
    assert [slot["slotIndex"] for slot in planner.SLOTS] == [0, 1, 2, 3, 4]
    assert planner.SLOTS[1]["slotName"] == "Giấy chứng nhận đã cấp (bản gốc). (Bản chính)"
    assert len({slot["slotKey"] for slot in planner.SLOTS}) == 5
    for slot in planner.SLOTS:
        for keyword in slot["slotKeywords"]:
            owners = [other["slotIndex"] for other in planner.SLOTS if keyword in fold(other["slotName"])]
            assert owners == [slot["slotIndex"]], keyword


def test_dinh_tuyen_ho_so_mau_theo_rule_khi_khong_co_llm():
    names = ["don-uy-quyen.pdf", "gcn.pdf", "phieu-do-dac.pdf"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    slots = [(item["fileName"], item["slotIndex"]) for item in attachments]
    assert slots == [
        ("don-uy-quyen.pdf", 0),
        ("don-uy-quyen.pdf", 2),
        ("gcn.pdf", 1),
        ("phieu-do-dac.pdf", 3),
    ]
    assert all(item["target"] == "fixed-slot" and item["tickRow"] for item in attachments)
    # Hồ sơ mẫu không có giấy tờ phần diện tích tăng thêm → dòng 5 không tick.
    assert all(item["slotIndex"] != 4 for item in attachments)
    assert warnings == []


def test_don_rieng_uy_quyen_rieng_tang_them_va_cccd():
    names = ["don.pdf", "uy-quyen.pdf", "chuyen-nhuong.pdf", "cccd.pdf"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    slots = [(item["fileName"], item.get("slotIndex")) for item in attachments if item["target"] == "fixed-slot"]
    assert slots == [("don.pdf", 0), ("uy-quyen.pdf", 2), ("chuyen-nhuong.pdf", 4)]
    identity = [item for item in attachments if item["target"] == "new"]
    assert len(identity) == 1
    assert identity[0]["componentName"] == "Căn cước người nộp - Trần Thị Mẫu"
    assert identity[0]["needsAddComponent"] is True
    assert warnings == []


def test_file_chung_don_uy_quyen_thang_nhan_don_cua_llm():
    names = ["don-uy-quyen.pdf"]
    attachments, _, classified = planner.build_plan_items(_files(names), _ocr(names), {0: "don_dang_ky_bien_dong"})

    assert [item["slotIndex"] for item in attachments] == [0, 2]
    assert classified[0]["docType"] == "don_va_uy_quyen"


def test_llm_thang_rule_va_llm_other_thi_ve_rule():
    names = ["phieu-do-dac.pdf", "gcn.pdf"]
    attachments, _, classified = planner.build_plan_items(
        _files(names), _ocr(names), {0: "manh_trich_do", 1: "other"}
    )

    assert [(item["fileName"], item["slotIndex"]) for item in attachments] == [("phieu-do-dac.pdf", 3), ("gcn.pdf", 1)]
    assert [entry["source"] for entry in classified] == ["llm", "rule"]


def test_file_khong_ro_vao_giay_to_khac_kem_canh_bao():
    names = ["anh-khac.jpg"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    assert attachments[0]["target"] == "new"
    assert attachments[0]["componentName"] == "anh-khac"
    assert "Giấy tờ khác" in warnings[0]


def test_file_qua_6mb_bi_loai_kem_canh_bao():
    oversized = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    files = [{"name": "don.pdf", "type": "application/pdf", "dataUrl": oversized}]
    attachments, warnings, classified = planner.build_plan_items(files, _ocr(["don.pdf"]), {0: "don_dang_ky_bien_dong"})

    assert attachments == []
    assert "6 MB" in warnings[0]
    assert classified[0]["skipped"] is True


# ---------------------------------------------------------------- registry


def test_registry_va_ke_khai_links_cung_key():
    procedure = get_procedure(KEY)

    assert procedure is not None
    assert procedure["label"].startswith("[Lai Châu]")
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["dichvucong.laichau.gov.vn"]
    assert procedure["detect"]["textPriority"] is True
    assert "6 MB" in procedure["uploadHint"]
    assert callable(get_pipeline(KEY))
    assert callable(get_attach_pipeline(KEY))

    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.115590"
    assert link["needsAgencySelect"] is True
    # Thủ tục riêng Lai Châu: tỉnh suy từ tiền tố nhãn "Lai Châu - ", tiếp nhận ở cấp xã (không chỉ chọn Tỉnh).
    assert link["label"].startswith("Lai Châu - ")
    assert not link.get("provinceOnlyAgency") and not link.get("selectSo")


# ---------------------------------------------------------------- trợ lý người dân


def test_tro_ly_cung_key_va_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(KEY)
    assert procedure is not None
    assert procedure["provinceOnly"] == ["laichau"]
    assert procedure["needsAgencySelect"] is True and procedure["agencyProvince"] == "Lai Châu"
    assert procedure["detect"] == get_procedure(KEY)["detect"]
    assert procedure["keKhaiUrl"] == next(item["url"] for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert get_procedure(KEY)["label"] == "[Lai Châu] " + procedure["label"]
    assert handfree.get_pipeline(KEY) is get_pipeline(KEY)
    assert handfree.get_attach_pipeline(KEY) is get_attach_pipeline(KEY)
    assert handfree.is_allowed_in_province(procedure, "laichau")
    assert not handfree.is_allowed_in_province(procedure, "bacninh")
    assert "Lai Châu" not in procedure["shortLabel"]
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn", "trich_do"}
    assert PROCEDURE_HMONG[KEY] and PROCEDURE_HINTS[KEY]
