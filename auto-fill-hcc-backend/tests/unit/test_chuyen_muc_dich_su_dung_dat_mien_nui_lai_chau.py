"""[Lai Châu] Chuyển mục đích sử dụng đất (xã miền núi, biên giới; đảo; vùng khó khăn, mã 1.115578).

Khóa theo file mapping "Mapping_Chuyen_MDSDD_Buoc2" + ảnh ánh xạ đính kèm:
  - process: bộ ô CongDan_* của người đề nghị (Đơn Mẫu 02 mục 1); địa chỉ theo Đơn (thẻ in địa chỉ cũ), ngày cấp theo
    thẻ khi GCN ghi lệch, GCN đứng tên cả vợ chồng không lẫn sang người kia, ô chữ thiếu thì xoá giá trị cổng đổ sẵn;
  - attach: bảng 3 dòng fixed-slot có tick, khớp theo TÊN (thứ tự trên cổng khác ảnh hướng dẫn), CCCD vào "Giấy tờ khác".

Dữ liệu trong test là PLACEHOLDER, không phải hồ sơ thật của người dân.
"""

import base64

import pytest

from app.pipelines._shared import fold
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.attach import planner
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process import mapper
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "chuyen-muc-dich-su-dung-dat-mien-nui-lai-chau"


def _fields(fields: list[dict]) -> dict:
    return {item["name"]: item for item in fields}


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields if not item.get("clear")}


def _facts(**extra) -> list[dict]:
    """Bộ hồ sơ như mẫu: thẻ CCCD (địa chỉ cũ) + Đơn Mẫu 02 (địa chỉ mới) + GCN đứng tên hai vợ chồng."""
    base = {
        "Cccd_HoTen": "LÊ VĂN MẪU",
        "Cccd_SoDinhDanh": "012000000001",
        "Cccd_NgaySinh": "1/2/1990",
        "Cccd_GioiTinh": "Nam",
        "Cccd_NgayCap": "03/12/2022",
        "Cccd_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
        "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Bản Cũ", "chiTietDuoiXa": "Bản Cũ Một"},
        "Don_HoTen": "Lê Văn Mẫu",
        "Don_DiaChi": {"tinh": "tỉnh Lai Châu", "xa": "xã Mẫu", "chiTietDuoiXa": "Thôn Mẫu Hai"},
        "Don_DienThoai": "0900.000.001",
        "Gcn_HoTen": "Lê Văn Mẫu",
        "Gcn_SoCccdMoi": "012000000001",
        "Gcn_NgayCapCccd": "03/11/2022",
        "Gcn_NoiCapCccd": "Cục Cảnh Sát QLHC về TTXH",
        "Gcn_ThuongTruMoi": "Thôn Mẫu Hai, xã Cũ, huyện Cũ, tỉnh Lai Châu",
        "NguoiSdd_GioiTinh": "Nam",
        "TrichLuc_HoTen": "Lê Văn Mẫu (Trần Thị Mẫu)",
    }
    base.update(extra)
    return [{"name": name, "value": value} for name, value in base.items() if value is not None]


def _enrich(facts: list[dict], options: dict | None = None) -> tuple[dict, list[str], dict]:
    fields, warnings = mapper.enrich(facts, options)
    return _values(fields), warnings, _fields(fields)


# ---------------------------------------------------------------- process/mapper


def test_mapper_ho_so_mau_the_va_don():
    values, _, _ = _enrich(_facts())

    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_soCmnd"] == values["CongDan_soCCCD"] == "012000000001"
    # Thẻ và trang thay đổi của GCN lệch ngày cấp → ưu tiên thẻ.
    assert values["CongDan_ngayCapCmnd"] == "03/12/2022"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["CongDan_diDong"] == "0900000001"
    # Cá nhân + thẻ do Cục Cảnh sát cấp → hai ô này để trống; Quốc gia để trống theo mapping.
    assert "CongDan_tenCoQuanToChuc" not in values
    assert "CongDan_maTinhCapCMND" not in values
    assert "CongDan_maDMQuocGia" not in values
    assert "CongDan_danTocCongDan" not in values


def test_mapper_dia_chi_theo_don_khong_theo_the_cu():
    values, _, _ = _enrich(_facts())

    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu"
    assert values["CongDan_maPhuongXa"] == "Xã Mẫu"
    assert values["CongDan_diaChi"] == "Thôn Mẫu Hai"
    assert values["CongDan_noiOHienTai"] == "Thôn Mẫu Hai, Xã Mẫu, Tỉnh Lai Châu"
    # Mapping: thẻ in thường trú cũ → Địa chỉ thường trú theo Đơn.
    assert values["CongDan_diaChiThuongTru"] == "Thôn Mẫu Hai, Xã Mẫu, Tỉnh Lai Châu"


def test_mapper_khong_don_thi_thuong_tru_theo_trang_thay_doi_gcn():
    values, _, _ = _enrich(_facts(Don_DiaChi=None))

    assert values["CongDan_diaChiThuongTru"] == "Thôn Mẫu Hai, xã Cũ, huyện Cũ, tỉnh Lai Châu"
    # 3 ô địa chỉ rơi về thẻ.
    assert values["CongDan_diaChi"] == "Bản Cũ Một"


def test_mapper_khong_the_dung_gcn_va_xoa_o_khong_nguon():
    facts = _facts(
        Cccd_HoTen=None, Cccd_SoDinhDanh=None, Cccd_NgaySinh=None, Cccd_GioiTinh=None, Cccd_NgayCap=None,
        Cccd_NoiCap=None, Cccd_NoiCuTru=None,
    )
    values, warnings, fields = _enrich(facts)

    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"
    assert values["CongDan_soCmnd"] == "012000000001"
    assert values["CongDan_ngayCapCmnd"] == "03/11/2022"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    # GCN chỉ có năm sinh → ô ngày sinh xoá giá trị cổng đổ theo tài khoản và tô đỏ.
    assert fields["CongDan_ngaySinhCongDan"] == {
        "name": "CongDan_ngaySinhCongDan", "comp": "dom-input", "value": "", "clear": True, "markEmpty": True,
    }
    assert fields["CongDan_email"]["clear"] is True and "markEmpty" not in fields["CongDan_email"]
    # Ô chọn không bao giờ phát clear (trợ lý chưa bỏ chọn được).
    assert all(item["comp"] == "dom-input" for item in fields.values() if item.get("clear"))
    assert any("Ngày sinh" in warning for warning in warnings)
    assert any("Dân tộc" in warning for warning in warnings)


def test_mapper_tai_khoan_la_nguoi_nop_thi_giu_o_cong():
    options = {"formContext": {"applicantIdentityNumber": "012 000 000 001"}}
    values, warnings, fields = _enrich(_facts(Cccd_NgaySinh=None), options)

    assert "CongDan_ngaySinhCongDan" not in fields
    assert not any(item.get("clear") for item in fields.values())
    assert warnings == []
    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"


def test_mapper_gcn_cua_vo_chong_khong_lan_sang():
    # LLM lỡ đọc mục I GCN ra người đứng sau "Và bà" → bỏ cả bộ Gcn_*.
    facts = _facts(
        Cccd_HoTen=None, Cccd_SoDinhDanh=None, Cccd_NgayCap=None, Cccd_NoiCap=None, Cccd_GioiTinh=None,
        Gcn_HoTen="Trần Thị Mẫu", Gcn_SoCccdMoi="012000000002", NguoiSdd_GioiTinh="Nữ",
    )
    values, _, _ = _enrich(facts)

    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"
    assert "CongDan_soCmnd" not in values
    assert "CongDan_gioiTinhCongDan" not in values
    assert values["CongDan_diaChiThuongTru"] == "Thôn Mẫu Hai, Xã Mẫu, Tỉnh Lai Châu"


def test_mapper_the_nguoi_khac_bi_bo():
    values, _, _ = _enrich(_facts(Cccd_HoTen="Trần Thị Mẫu", Cccd_SoDinhDanh="012000000002", Cccd_GioiTinh="Nữ"))

    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"
    assert values["CongDan_soCmnd"] == "012000000001"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"


def test_mapper_trich_luc_bo_ten_trong_ngoac_va_to_chuc_email():
    only_trich_luc = _facts(Cccd_HoTen=None, Don_HoTen=None, Gcn_HoTen=None)
    values, _, _ = _enrich(only_trich_luc)
    assert values["CongDan_tenCongDan"] == "LÊ VĂN MẪU"

    values, _, _ = _enrich(_facts(ToChuc_Ten="Hợp tác xã Mẫu", Don_Email="mau @example.com"))
    assert values["CongDan_tenCoQuanToChuc"] == "Hợp tác xã Mẫu"
    assert values["CongDan_email"] == "mau@example.com"


def test_schema_moi_o_ui_deu_co_comp_va_khong_phat_o_khong_nguon():
    _, _, fields = _enrich(_facts())

    assert set(fields) <= set(UI_COMP_BY_NAME)
    for name in ("CongDan_fax", "CongDan_website", "CongDan_soGCNGP", "CongDan_ngayCapGCNGP",
                 "CongDan_noiCapGCNGP", "CongDan_maDMDiaChi", "CongDan_diaChiNuocNgoai", "CongDan_maDMQuocGia"):
        assert name not in UI_COMP_BY_NAME
    assert not any(name.startswith("ChuHoSo_") for name in UI_COMP_BY_NAME)
    assert {"Don_DiaChi", "Gcn_SoCccdMoi", "NguoiSdd_GioiTinh", "TrichLuc_HoTen"} <= ALLOWED


# ---------------------------------------------------------------- attach/planner

_TEXTS = {
    "don.pdf": "Mẫu số 02. Đơn đề nghị chuyển mục đích sử dụng đất\nĐƠN ĐỀ NGHỊ CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT\n"
               "8. Tài liệu gửi kèm: Giấy chứng nhận QSDĐ; Trích lục bản đồ địa chính; CCCD photo",
    "trich-luc.pdf": "TRÍCH LỤC BẢN ĐỒ ĐỊA CHÍNH\n1. Thửa đất số: 1 ;Tờ bản đồ địa chính số: 2\n"
                     "4. Giấy chứng nhận: Giấy chứng nhận số Seri AA 000000",
    "gcn.pdf": "Nội dung thay đổi và cơ sở pháp lý\nthay đổi CMND về CCCD số 012000000001\nGIẤY CHỨNG NHẬN\n"
               "QUYỀN SỬ DỤNG ĐẤT\nSố vào sổ cấp GCN: CH0",
    "quyet-dinh.pdf": "ỦY BAN NHÂN DÂN\nQUYẾT ĐỊNH\nVề việc giao đất cho hộ gia đình",
    "cccd.pdf": "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name:\nLÊ VĂN MẪU\nNgày sinh",
    "uy-quyen.pdf": "GIẤY ỦY QUYỀN\nTôi: Lê Văn Mẫu",
    "anh-khac.jpg": "Biên lai thu phí",
}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,QQ=="} for name in names]


def _ocr(names: list[str]) -> list[dict]:
    return [{"name": name, "text": _TEXTS[name]} for name in names]


def test_bang_3_dong_dung_ten_va_tu_khoa_khong_chong_nhau():
    assert [slot["slotIndex"] for slot in planner.SLOTS] == [0, 1, 2]
    assert planner.SLOTS[0]["slotName"] == "Mẫu số 02. Đơn đề nghị chuyển mục đích sử dụng đất (Bản chính)"
    assert planner.SLOTS[1]["slotName"].startswith("Bản trích lục bản đồ địa chính")
    assert len({slot["slotKey"] for slot in planner.SLOTS}) == 3
    for slot in planner.SLOTS:
        for keyword in slot["slotKeywords"]:
            owners = [other["slotIndex"] for other in planner.SLOTS if keyword in fold(other["slotName"])]
            assert owners == [slot["slotIndex"]], keyword


def test_dinh_tuyen_ho_so_mau_theo_rule_khi_khong_co_llm():
    names = ["don.pdf", "trich-luc.pdf", "gcn.pdf", "cccd.pdf"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    slots = [(item["fileName"], item["slotIndex"]) for item in attachments if item["target"] == "fixed-slot"]
    # Đơn nhắc GCN + trích lục, Trích lục nhắc GCN, GCN nhắc CCCD → vẫn đúng dòng theo tiêu đề.
    assert slots == [("don.pdf", 0), ("trich-luc.pdf", 1), ("gcn.pdf", 2)]
    assert all(item["tickRow"] for item in attachments if item["target"] == "fixed-slot")
    identity = [item for item in attachments if item["target"] == "new"]
    assert [item["componentName"] for item in identity] == ["Căn cước người nộp - Lê Văn Mẫu"]
    assert identity[0]["needsAddComponent"] is True
    assert warnings == []


def test_quyet_dinh_vao_dong_3_uy_quyen_vao_giay_to_khac():
    names = ["quyet-dinh.pdf", "uy-quyen.pdf"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    assert attachments[0]["slotIndex"] == 2 and attachments[0]["detectedType"] == "quyet_dinh_dat"
    assert attachments[1]["target"] == "new" and attachments[1]["componentName"] == "Văn bản ủy quyền"
    assert warnings == []


def test_llm_thang_rule_va_llm_other_thi_ve_rule():
    names = ["trich-luc.pdf", "gcn.pdf"]
    attachments, _, classified = planner.build_plan_items(
        _files(names), _ocr(names), {0: "trich_luc_ban_do", 1: "other"}
    )

    assert [(item["fileName"], item["slotIndex"]) for item in attachments] == [("trich-luc.pdf", 1), ("gcn.pdf", 2)]
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
    attachments, warnings, classified = planner.build_plan_items(files, _ocr(["don.pdf"]), {0: "don_de_nghi"})

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
    assert link["code"] == "1.115578"
    assert link["needsAgencySelect"] is True
    # Thủ tục riêng Lai Châu: tỉnh suy từ tiền tố nhãn "Lai Châu - ", tiếp nhận ở cấp xã (không chỉ chọn Tỉnh).
    assert link["label"].startswith("Lai Châu - ")
    assert not link.get("provinceOnlyAgency") and not link.get("selectSo")
    # Trang nộp in "1.115578 - <tên thủ tục>" KHÔNG kèm đuôi "(Đối với các xã miền núi…)": nhận theo mã + cụm tên,
    # không đòi cụm "miền núi".
    page = (
        "Thông tin người nộp hồ sơ Một phần 1.115578 - Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia "
        "hạn sử dụng đất khi hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư Nơi tiếp nhận"
    )
    assert all(fold(phrase) in fold(page) for phrase in procedure["detect"]["textIncludes"])
    assert link["code"] in procedure["detect"]["textIncludes"]
    assert not any("mien nui" in fold(phrase) for phrase in procedure["detect"]["textIncludes"])


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
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn", "trich_luc"}
    assert PROCEDURE_HMONG[KEY] and PROCEDURE_HINTS[KEY]


# ---------------------------------------------------------------- trợ lý: bước "Lệ phí hồ sơ" (chat/lai_chau.py)
# Trang Lệ phí của cổng (crawl 09/11/2026): ô "Hình thức nhận kết quả" 2 lựa chọn, "Mức lệ phí" 3 mức, nút "Lấy địa chỉ
# của Người nộp". Áp cho cả hai thủ tục Lai Châu cùng cổng (1.115578 và 1.115590).

LC_KEYS = [KEY, "dang-ky-cap-giay-chung-nhan-doi-voi-toan-bo-dien-tich-dat-lai-chau", "giao-dat-cho-thue-dat-lai-chau",
           "cap-lai-giay-chung-nhan-do-bi-mat-lai-chau"]
LC_CAPS = {"supportsFlowV2": True, "supportsLaiChauFeeStep": True}
LC_GROUPS = [
    {"name": "maHinhThucNhanKetQua", "present": True, "value": "Nhận kết quả điện tử và Gửi bản giấy về địa chỉ của tôi",
     "options": ["Nhận kết quả điện tử và Gửi bản giấy về địa chỉ của tôi", "Đến cơ quan giải quyết để nhận kết quả"]},
    {"name": "loaiLePhi", "present": True, "value": "", "options": ["0", "7.000", "14.000"]},
]


@pytest.fixture
def lc_io(monkeypatch):
    from unittest.mock import AsyncMock

    from app.channels.handfree.chat import flow, pipeline_runner, tracing

    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: None)
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())


def _lc_conv(key, state, caps=LC_CAPS, **extra):
    from app.channels.handfree.chat import store

    conv = store.new_conversation()
    conv.update({"procedure_key": key, "state": state, "client_capabilities": dict(caps), "auth_user": {"id": "u1"},
                 "upload_session_id": "s1", "fields": [{"name": "CongDan_tenCongDan", "comp": "dom-input", "value": "A"}]})
    conv.update(extra)
    return conv


async def _lc_turn(conv, kind, value, payload=None):
    from app.channels.handfree.chat import flow
    from app.channels.handfree.chat.intents import Intent

    return await flow.handle_turn(conv, Intent(kind, value, payload or {}))


@pytest.mark.parametrize("key", LC_KEYS)
def test_tro_ly_buoc_le_phi_chi_bat_khi_co_co_va_khong_phai_tieng_mong(key):
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat import lai_chau, router

    proc = handfree.get_procedure(key)
    assert [g["name"] for g in lai_chau._groups(proc)] == ["maHinhThucNhanKetQua", "loaiLePhi"]
    assert lai_chau.enabled(_lc_conv(key, "done"), proc)
    assert not lai_chau.enabled(_lc_conv(key, "done", caps={"supportsFlowV2": True}), proc)
    assert not lai_chau.enabled(_lc_conv(key, "done", lang="hmong"), proc)
    # Cờ phải lọt whitelist của router, không thì luồng không bao giờ bật trên máy thật.
    assert router._clean_client_capabilities({"supportsLaiChauFeeStep": True})["supportsLaiChauFeeStep"] is True
    assert router._clean_client_capabilities({})["supportsLaiChauFeeStep"] is False


@pytest.mark.parametrize("key", LC_KEYS)
async def test_tro_ly_dinh_kem_xong_co_nut_sang_buoc_le_phi(key, lc_io):
    from app.channels.handfree.chat import lai_chau
    from app.channels.handfree.chat import script_vi as vi

    attaching = _lc_conv(key, "attaching", docs_target="attachment", flow2_card="attach",
                         attach_plan=[{"fileName": "don.pdf", "componentIndex": 1}], attach_action_in_progress=True)
    done = await _lc_turn(attaching, "action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})
    assert done.chips[-1] == {"label": vi.LC_CONTINUE_CHIP, "send": lai_chau.NEXT_SEND, "solid": True, "cta": True}
    assert any(a.get("md") == vi.LC_ATTACH_NEXT["md"] for a in done.actions if a.get("type") == "trail_message")
    assert attaching["lai_chau"]["at"] == lai_chau.ATTACHMENT
    assert (await _lc_turn(attaching, "action", "lc_next")).actions == [{"type": "lc_next"}]


@pytest.mark.parametrize("key", LC_KEYS)
async def test_tro_ly_toi_trang_le_phi_doc_va_chon_hinh_thuc_muc_le_phi(key, lc_io):
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat import lai_chau
    from app.channels.handfree.chat import script_vi as vi
    from app.channels.handfree.chat.intents import Intent

    conv = _lc_conv(key, "done", lai_chau={"at": lai_chau.ATTACHMENT})
    arrived = await _lc_turn(conv, "event", "page_status", {"lcStep": 4})
    scan = next(a for a in arrived.actions if a["type"] == "lc_result_scan")
    assert [g["name"] for g in scan["groups"]] == ["maHinhThucNhanKetQua", "loaiLePhi"]
    # Cùng trang báo lại (watcher / tải lại) → luồng Lai Châu im, không đọc lại.
    assert lai_chau.handle(conv, handfree.get_procedure(key), Intent("event", "page_status", {"lcStep": 4})) is None

    report = await _lc_turn(conv, "action", "lc_result_report",
                            {"groups": LC_GROUPS, "missing": [], "prepared": ["address", "quantity"]})
    assert report.cards[0]["kind"] == "lt_result_groups"
    fee_row = report.cards[0]["rows"][1]
    assert [o["label"] for o in fee_row["options"]] == ["0", "7.000", "14.000"]
    assert fee_row["options"][1]["send"].startswith("__action:lc_result_pick:")
    assert vi.LC_ADDRESS_PULLED["md"] in report.display_md
    # Mức lệ phí chưa chọn → câu dặn chọn mức (cổng bắt buộc), nút Đồng ý và tiếp tục.
    assert any(a.get("md") == vi.LC_FEE_ASK["md"] for a in report.actions)
    assert [c["send"] for c in report.chips] == [lai_chau.NEXT_SEND]

    pick = await _lc_turn(conv, "action", "lc_result_pick", {"name": "loaiLePhi", "value": "7.000"})
    assert pick.actions[0]["type"] == "lc_result_set" and pick.actions[0]["value"] == "7.000"
    assert (await _lc_turn(conv, "action", "lc_result_pick", {"name": "loaiLePhi", "value": "99.000"})).actions == []

    chosen = [dict(LC_GROUPS[0]), {**LC_GROUPS[1], "value": "7.000"}]
    changed = await _lc_turn(conv, "action", "lc_result_report", {
        "groups": chosen, "missing": ["Số nhà/Đường/Tổ/Ấp/Thôn/Xóm nhận kết quả"],
        "changed": {"name": "loaiLePhi", "value": "7.000", "ok": True}})
    assert "7.000" in changed.display_md and "Số nhà/Đường/Tổ/Ấp/Thôn/Xóm nhận kết quả" in changed.display_md
    assert any(a.get("md") == vi.LC_CONTINUE_GUIDE["md"] for a in changed.actions)

    # Bị cổng chặn (hộp thoại Nth.Alert) → câu chặn + nút bấm lại; sang trang sau → nhắc tự nộp.
    blocked = await _lc_turn(conv, "action", "lc_step_report", {"clicked": True, "message": "Vui lòng chọn Lệ phí"})
    assert "Vui lòng chọn Lệ phí" in blocked.display_md and blocked.chips[0]["send"] == lai_chau.NEXT_SEND
    after = await _lc_turn(conv, "event", "page_status", {"lcStep": 5})
    assert after.display_md == vi.LC_AFTER_FEE["md"]


LC_CASE_GROUPS = [
    {"name": "maCoQuan", "present": True, "value": "UBND Phường Mẫu", "options": ["UBND Phường Mẫu"]},
    {"name": "maQttt", "present": True, "value": "",
     "options": ["15 ngày làm việc - 15 Ngày - QTC", "25 ngày làm việc - 25 Ngày - QTC"]},
    {"name": "maQuanHuyenNop", "present": False},
    {"name": "maPhuongXaNop", "present": False},
]


@pytest.mark.parametrize("key", LC_KEYS)
async def test_tro_ly_trang_chon_truong_hop_doc_chon_va_nut_dong_y(key, lc_io):
    """Trang "Trường hợp nộp hồ sơ" (chon-truong-hop-ho-so, crawl 09/11): cơ quan giải quyết + trường hợp 15/25 ngày."""
    from app.channels.handfree.chat import lai_chau
    from app.channels.handfree.chat import script_vi as vi

    conv = _lc_conv(key, "guide_login")
    arrived = await _lc_turn(conv, "event", "page_status", {"lcStep": 1})
    assert arrived.display_md == vi.LC_CASE_READING["md"]
    scan = next(a for a in arrived.actions if a["type"] == "lc_result_scan")
    assert [g["name"] for g in scan["groups"]] == ["maCoQuan", "maQttt", "maQuanHuyenNop", "maPhuongXaNop"]

    report = await _lc_turn(conv, "action", "lc_result_report", {"groups": LC_CASE_GROUPS, "missing": [], "prepared": []})
    rows = report.cards[0]["rows"]
    # Ô nơi nộp không có trên trang → không lên thẻ.
    assert [row["name"] for row in rows] == ["maCoQuan", "maQttt"]
    assert [o["label"] for o in rows[1]["options"]] == LC_CASE_GROUPS[1]["options"]
    assert any(a.get("md") == vi.LC_CASE_ASK["md"] for a in report.actions)
    assert report.chips == [lai_chau.next_chip()]

    pick = await _lc_turn(conv, "action", "lc_result_pick", {"name": "maQttt", "value": "25 ngày làm việc - 25 Ngày - QTC"})
    assert pick.actions[0]["type"] == "lc_result_set"
    assert [g["name"] for g in pick.actions[0]["groups"]][:2] == ["maCoQuan", "maQttt"]
    chosen = [LC_CASE_GROUPS[0], {**LC_CASE_GROUPS[1], "value": "25 ngày làm việc - 25 Ngày - QTC"}]
    changed = await _lc_turn(conv, "action", "lc_result_report", {
        "groups": chosen, "changed": {"name": "maQttt", "value": "25 ngày làm việc - 25 Ngày - QTC", "ok": True}})
    assert any(a.get("md") == vi.LC_CASE_GUIDE["md"] for a in changed.actions)
    # Chỉ có một trường hợp → extension chọn sẵn, trợ lý báo.
    single = await _lc_turn(conv, "action", "lc_result_report", {"groups": chosen, "prepared": ["auto:maQttt"]})
    assert vi.LC_CASE_AUTO["md"] in single.display_md

    # Sang Thông tin người nộp (bước 2): để flow cũ nhận giấy tờ / điền.
    assert lai_chau.handle(conv, flow_proc(key), _event_page(2)) is None
    assert conv["lai_chau"]["at"] == lai_chau.DECLARATION


@pytest.mark.parametrize("key", LC_KEYS)
async def test_tro_ly_trang_chon_truong_hop_khong_xin_phep_som(key, lc_io):
    """09/11: trang chọn trường hợp có form → extension báo declarationTarget → luồng cũ xin phép xử lý dữ liệu ngay ở
    đó (state consent không theo dõi trang) → bấm Đồng ý và tiếp tục sang bước 2 là treo. Ở trang 1 phải im lặng."""
    from app.channels.handfree.chat import script_vi as vi

    conv = _lc_conv(key, "guide_login")
    page = {"lcStep": 1, "loggedIn": True, "declarationTarget": True, "formKind": "standard"}
    first = await _lc_turn(conv, "event", "page_status", page)
    assert first.display_md == vi.LC_CASE_READING["md"]
    again = await _lc_turn(conv, "event", "page_status", page)
    assert (again.display_md, again.cards, again.chips) == ("", [], [])
    assert conv["state"] == "guide_login"

    step2 = await _lc_turn(conv, "event", "page_status", {**page, "lcStep": 2})
    assert conv["state"] == "consent"
    assert any(card.get("kind") == "consent_form" for card in step2.cards)


@pytest.mark.parametrize("key", LC_KEYS)
def test_tro_ly_khoi_phuc_phien_sau_khi_sang_trang_mang_co_lai_chau(key):
    """09/11: sang trang Lệ phí (cổng tải trang mới) sidebar dựng lại từ last_reply — thiếu cờ lai_chau thì watcher không
    báo lcStep ở state done, trợ lý đứng im."""
    from app.channels.handfree.chat import router

    last = {"display_md": "Dạ tôi bấm Đồng ý và tiếp tục", "chips": [], "cards": [], "state": "done"}
    assert router._last_reply_for_restore(_lc_conv(key, "done", last_reply=last))["lai_chau"] is True
    old_client = _lc_conv(key, "done", caps={"supportsFlowV2": True}, last_reply=last)
    assert router._last_reply_for_restore(old_client)["lai_chau"] is False


def flow_proc(key):
    from app.channels.handfree import procedure_registry as handfree

    return handfree.get_procedure(key)


def _event_page(step):
    from app.channels.handfree.chat.intents import Intent

    return Intent("event", "page_status", {"lcStep": step})


@pytest.mark.parametrize("key", LC_KEYS)
async def test_tro_ly_dien_xong_buoc_2_co_nut_cam_dong_y_va_tiep_tuc(key, lc_io):
    from app.channels.handfree.chat import lai_chau

    filled = _lc_conv(key, "filling", flow2_card="fill", auto_attach_after_fill=True)
    reply = await _lc_turn(filled, "action", "fill_report", {"filled": 16, "notFound": []})
    assert reply.chips[-1] == lai_chau.next_chip()
    assert sum(1 for c in reply.chips if c.get("cta")) == 1
    # Extension chưa khai cờ → giữ nguyên câu cũ, không nút cam.
    old = await _lc_turn(_lc_conv(key, "filling", caps={"supportsFlowV2": True}, flow2_card="fill",
                                  auto_attach_after_fill=True), "action", "fill_report", {"filled": 16, "notFound": []})
    assert lai_chau.NEXT_SEND not in [c["send"] for c in old.chips]


@pytest.mark.parametrize("key", LC_KEYS)
def test_tro_ly_noi_buoc_tiep_theo_o_trang_le_phi(key):
    from app.channels.handfree.chat import lai_chau

    assert lai_chau.voice_intent(_lc_conv(key, "done"), "bước tiếp theo", {"lcStep": 4}).value == "lc_next"
    assert lai_chau.voice_intent(_lc_conv(key, "guide_login"), "bước tiếp theo", {"lcStep": 1}).value == "lc_next"
    assert lai_chau.voice_intent(_lc_conv(key, "done", lai_chau={"at": 3}), "đồng ý và tiếp tục", {}).value == "lc_next"
    # Bước 2 trước khi điền: "tiếp theo" là chuyện giấy tờ của flow cũ; điền xong (chờ sang trang đính kèm) thì bấm.
    assert lai_chau.voice_intent(_lc_conv(key, "done"), "bước tiếp theo", {"lcStep": 2}) is None
    waiting = _lc_conv(key, "attaching", pipeline_status="waiting_attachment_page")
    assert lai_chau.voice_intent(waiting, "bước tiếp theo", {"lcStep": 2}).value == "lc_next"
