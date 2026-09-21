"""[Bộ VHTTDL] Cấp giấy phép xuất bản tài liệu không kinh doanh (1.003868).

Khoá 3 điều dễ vỡ: mọi (section, mat-label) khai trong schema phải có thật trên trang; ba vai
(người nộp / tổ chức đề nghị / cơ sở in) không được lẫn; bảng đính kèm 4 dòng, mỗi tệp một dòng.
"""

import re
from pathlib import Path

from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.attach import planner
from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.process import mapper
from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.process.schema import (
    S_DN,
    S_DON,
    S_GQ,
    S_NOP,
    UI_FIELDS,
)
from app.procedures.registry import public_list

_KEY = "cap-giay-phep-xuat-ban-tai-lieu-khong-kinh-doanh"
_THONGTIN = Path(__file__).resolve().parents[2].parent / "thongtin"


def _snapshot() -> Path | None:
    for d in _THONGTIN.glob("158-*"):
        for f in d.glob("*.html"):
            return f
    return None


def _fold(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _ui(fields):
    return {(f["section"], f["name"]): f["value"] for f in fields}


def test_registry_khoa_dung_ma_thu_tuc_va_co_buoc_dinh_kem():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlIncludes"] == ["matthc=1.003868"]


def test_moi_o_khai_trong_schema_deu_co_that_tren_trang():
    """Engine fill-liz khớp theo (section, mat-label) — sai một ký tự là ô đó không điền được."""
    html_file = _snapshot()
    if html_file is None:
        return
    html = html_file.read_text(encoding="utf-8", errors="replace")
    labels = {_fold(re.sub(r"(?s)<[^>]+>", " ", m)) for m in re.findall(r"(?s)<mat-label[^>]*>(.*?)</mat-label>", html)}
    headers = {
        _fold(re.sub(r"(?s)<[^>]+>", " ", m))
        for m in re.findall(r'(?s)<[^>]*class="[^"]*group-header[^"]*"[^>]*>(.*?)</div>', html)
    }
    for section, label, _comp in UI_FIELDS:
        assert _fold(label) in labels, label
        assert any(_fold(section) in h or h in _fold(section) for h in headers), section


def test_khong_khai_o_bi_cong_khoa():
    """Tên người nộp / CMND / Địa chỉ hành chính là disabled (cổng tự điền từ tài khoản định danh)."""
    khai = {(s, l) for s, l, _ in UI_FIELDS}
    assert (S_NOP, "Tên người nộp / Tên đơn vị") not in khai
    assert (S_NOP, "CMND/Hộ chiếu/MST Doanh nghiệp") not in khai
    assert (S_NOP, "Địa chỉ hành chính") not in khai
    assert (S_GQ, "Địa chỉ hành chính") not in khai


def test_co_so_in_khong_tran_sang_khoi_to_chuc_de_nghi():
    """BẪY LỚN NHẤT: GCN đăng ký doanh nghiệp trong hồ sơ là của NHÀ IN, không phải tổ chức đứng đơn."""
    fields, _ = mapper.enrich([
        {"name": "ToChucDeNghi_Ten", "value": "Bộ Chỉ huy Bộ đội Biên phòng tỉnh Lào Cai"},
        {"name": "ToChucDeNghi_DiaChi",
         "value": {"tinh": "Lào Cai", "xa": "Phường Lào Cai", "diaChi": "Số 1 Phan Chu Trinh"}},
        {"name": "CoSoIn_TenTiengViet", "value": "CÔNG TY TNHH IN THƯƠNG MẠI ĐỨC ANH"},
        {"name": "CoSoIn_MaSoThue", "value": "5300701326"},
        {"name": "CoSoIn_TruSo",
         "value": {"tinh": "Lào Cai", "xa": "Phường Lào Cai", "diaChi": "Số 074 Phan Chu Trinh"}},
    ])
    ui = _ui(fields)

    assert ui[(S_GQ, "Tên người / Tên đơn vị được giải quyết")].startswith("Bộ Chỉ huy")
    assert ui[(S_DN, "Tên tiếng việt")] == "CÔNG TY TNHH IN THƯƠNG MẠI ĐỨC ANH"
    assert ui[(S_DN, "Mã số thuế")] == "5300701326"
    # Không có ô nào của khối tổ chức đề nghị mang dữ liệu nhà in.
    assert "IN THƯƠNG MẠI" not in ui[(S_GQ, "Tên người / Tên đơn vị được giải quyết")]
    assert (S_DON, "Số GCN đăng ký kinh doanh/ GCN đầu tư/ GCN đăng ký doanh nghiệp (đối với doanh nghiệp)") not in ui


def test_muc_8_cua_don_lay_lai_du_lieu_co_so_in_khi_don_khong_ghi():
    fields, _ = mapper.enrich([
        {"name": "CoSoIn_TenTiengViet", "value": "CÔNG TY TNHH IN THƯƠNG MẠI ĐỨC ANH"},
        {"name": "CoSoIn_TruSo", "value": {"tinh": "Lào Cai", "xa": "Phường Lào Cai", "diaChi": "Số 074"}},
    ])
    ui = _ui(fields)

    assert ui[(S_DON, "Tên cơ sở in")] == "CÔNG TY TNHH IN THƯƠNG MẠI ĐỨC ANH"
    assert "Phường Lào Cai" in ui[(S_DON, "Địa chỉ cơ sở in")]


def test_dia_chi_to_chuc_de_nghi_ghi_day_du_vi_o_hanh_chinh_bi_khoa():
    fields, _ = mapper.enrich([
        {"name": "ToChucDeNghi_Ten", "value": "Trường THPT số 1"},
        {"name": "ToChucDeNghi_DiaChi",
         "value": {"tinh": "Lào Cai", "xa": "Phường Lào Cai", "diaChi": "Tổ 5"}},
    ])
    dia_chi = _ui(fields)[(S_GQ, "Địa chỉ")]

    assert "Tổ 5" in dia_chi and "Phường Lào Cai" in dia_chi and "Tỉnh Lào Cai" in dia_chi


def test_khong_bia_ngay_khi_chi_co_nam_va_canh_bao_khi_thieu_ten_to_chuc():
    fields, warnings = mapper.enrich([
        {"name": "CoSoIn_NgayDangKyLanDau", "value": "2015"},
        {"name": "TaiLieu_Ten", "value": "Tờ gấp tuyên truyền"},
    ])
    ui = _ui(fields)

    assert (S_DN, "Đăng ký lần đầu") not in ui
    assert any("tổ chức ĐỀ NGHỊ" in w for w in warnings)


def test_bon_dong_dinh_kem_dung_thu_tu_dom():
    html_file = _snapshot()
    if html_file is None:
        return
    html = html_file.read_text(encoding="utf-8", errors="replace")
    uploads = re.findall(r"<app-upload-flie-multi", html)
    assert len(uploads) == 4, len(uploads)
    assert set(planner._ROUTES.values()) == {0, 1, 2, 3}


def test_ho_so_mau_cua_ba_len_dung_dong():
    """4 tệp mẫu: đơn → (1), bản thảo → (2), GCN ĐKDN + giấy phép in → (4) vì trang không có 'giấy tờ khác'."""
    items, warnings, _ = planner.build_plan_items(
        _files(["Don_xin_cap_giay_phep.pdf", "Ban_thao.pdf", "1_CNKD.pdf", "2_GP_01_hoat_dong_in.pdf"]),
        {0: ("don_de_nghi", []), 1: ("ban_thao", []), 2: ("other", []), 3: ("other", [])},
    )

    assert len(items) == 4, "mỗi tệp chỉ đính vào MỘT dòng"
    assert [i["slotIndex"] for i in items] == [0, 1, 3, 3]
    assert any("KHÔNG có dòng \"Giấy tờ khác\"" in w for w in warnings)
    assert any("có thể vẫn đang thiếu giấy tờ đúng yêu cầu" in w for w in warnings)


def test_tep_gop_uu_tien_don_de_nghi_va_khong_nhan_ban():
    items, _, classified = planner.build_plan_items(
        _files(["gop.pdf"]), {0: ("ban_thao", ["don_de_nghi", "y_kien_xac_nhan"])}
    )

    assert len(items) == 1
    assert items[0]["slotIndex"] == 0
    assert classified[0]["assignedType"] == "don_de_nghi"


def test_giay_to_la_giu_ten_tep_lam_ten_tai_lieu():
    items, _, _ = planner.build_plan_items(_files(["Hop_dong_in.pdf"]), {0: ("other", [])})

    assert items[0]["documentName"] == "Hop_dong_in.pdf"
    assert items[0]["slotIndex"] == 3


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(c["source"] == "default" for c in classified)
    assert warnings


def test_slot_key_khong_trung_keyword_cua_extension():
    content = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "content.js"
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    assert "gpxb_" not in block


def test_engine_liz_dien_duoc_o_textarea():
    """2 ô dài (tóm tắt nội dung, kèm theo đơn) là <textarea> — inputOf cũ chỉ tìm <input>."""
    fill_liz = (
        Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "content" / "fill-liz.js"
    )
    if not fill_liz.exists():
        return
    block = fill_liz.read_text(encoding="utf-8").split("function inputOf", 1)[1].split("}", 1)[0]
    assert "textarea" in block


def test_prompt_chan_giay_to_nha_in_thanh_y_kien_xac_nhan():
    from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.attach.prompt import SYSTEM_PROMPT

    assert "GIẤY TỜ CỦA NHÀ IN KHÔNG PHẢI THÀNH PHẦN HỒ SƠ" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT


def test_prompt_process_tach_ba_vai():
    from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.process.prompt import EXTRA_RULES

    assert "BẪY LỚN NHẤT" in EXTRA_RULES
    assert "CƠ SỞ IN" in EXTRA_RULES
    assert "thà thiếu còn hơn" in EXTRA_RULES
