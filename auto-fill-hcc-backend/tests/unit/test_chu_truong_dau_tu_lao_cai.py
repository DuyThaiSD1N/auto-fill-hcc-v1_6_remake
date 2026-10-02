"""[Lào Cai] 3 thủ tục chủ trương đầu tư (1.009759, 1.009646, 1.009645) — process chung + dòng đính kèm riêng.

Dữ liệu giả; chủ hồ sơ là NHÀ ĐẦU TƯ, người nộp chọn theo mốc tài khoản (chế độ mặc định) hoặc theo tờ khai.
"""

import re
import unicodedata
from pathlib import Path

from app.pipelines.chu_truong_dau_tu_lao_cai.attach import planner
from app.pipelines.chu_truong_dau_tu_lao_cai.process import mapper
from app.pipelines.chu_truong_dau_tu_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEYS = {
    "193": ("chap-thuan-dieu-chinh-chu-truong-dau-tu-bql-lao-cai", "1.009759", planner.CONFIG_DIEU_CHINH_BQL),
    "194": ("dieu-chinh-du-an-dau-tu-ubnd-tinh-lao-cai", "1.009646", planner.CONFIG_DIEU_CHINH_UBND),
    "195": ("chap-thuan-chu-truong-dau-tu-ubnd-tinh-lao-cai", "1.009645", planner.CONFIG_CHAP_THUAN_UBND),
}
_ANCHOR = {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "001068000001"}

_DOANH_NGHIEP = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Mẫu"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300 000 001"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Tỉnh Lào Cai", "xa": "Xã Gia Phú", "diaChi": "Lô CN2"}},
    {"name": "ChuHoSo_DienThoai", "value": "0214.3000.001"},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Ông Nguyễn Văn A", "SoDinhDanh": "001068000001", "NgaySinh": "15/08/1968", "GioiTinh": "Nam",
         "DanToc": "Kinh", "NgayCap": "09/08/2021",
         "NoiCap": "Cục cảnh sát quản lý hành chính về trật tự xã hội",
         "NoiCuTru": {"tinh": "Thành phố Hà Nội", "xa": "Phường Ba Đình", "diaChi": "Số nhà 1, phố Mẫu"}},
    ]},
    {"name": "NguoiNop_HoTen", "value": "Nguyễn Văn A"},
    {"name": "NguoiNop_SoDinhDanh", "value": "001068000001"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _snapshot_pages(code: str) -> list[str]:
    folder = next(p for p in (_root() / "thongtin").iterdir() if p.name.startswith(code))
    return [p.read_text(encoding="utf-8", errors="ignore") for p in folder.iterdir() if p.suffix == ".html"]


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", unicodedata.normalize("NFC", text))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("đ", "d").replace("Đ", "D")).lower()


def test_registry_ba_thu_tuc_dung_chung_process_rieng_dong_dinh_kem():
    for key, code, _row in _KEYS.values():
        proc = get_procedure(key)
        assert proc["detect"]["urlScope"] == ["dichvucong.laocai.gov.vn"]
        assert proc["detect"]["textIncludes"][0] == code
        assert proc["hasAttachmentStep"] is True
        assert get_pipeline(key) is get_pipeline(_KEYS["193"][0])
    assert len({get_attach_pipeline(key) for key, _, _ in _KEYS.values()}) == 3


def test_detect_khop_dung_trang_cua_minh_khong_lan_sang_thu_tuc_kia():
    for code, (key, _, _) in _KEYS.items():
        phrases = get_procedure(key)["detect"]["textIncludes"]
        for other, (other_key, _, _) in _KEYS.items():
            for html in _snapshot_pages(other):
                text = _fold(re.sub(r"<[^>]+>", " ", html))
                hit = all(_fold(p) in text for p in phrases)
                assert hit == (other == code), (key, other)


def test_ui_key_co_that_tren_trang_dien_ca_3_thu_tuc():
    for code in _KEYS:
        html = next(h for h in _snapshot_pages(code) if "CongDan_tenCongDan" in h)
        for name in UI_COMP_BY_NAME:
            assert f'name="{name}"' in html, (code, name)


def test_slot_index_tro_dung_dong_tren_snapshot():
    """slotIndex = thứ tự input[type=file] trên trang đính kèm; dòng ở vị trí đó phải chứa slotName."""
    for code, (_key, _, config) in _KEYS.items():
        html = next(h for h in _snapshot_pages(code) if "GiayToCuaHoSoOnline_" in h and "fileGiayTo" in h)
        inputs = [m.start() for m in re.finditer(r'<input[^>]*type="file"[^>]*>', html)]
        for row in config["rows"]:
            pos = inputs[row["slotIndex"]]
            row_html = html[html.rfind("<tr", 0, pos):pos]
            assert _fold(row["slotName"]) in _fold(re.sub(r"<[^>]+>", " ", row_html)), (code, row["slotName"])
        # Trang có/không có "Giấy tờ khác" khớp cấu hình tràn.
        assert ('name="HoSoOnline_giayToKhac[]"' in html) == config["otherList"], code


def _files(n, big=()):
    small = "data:application/pdf;base64,QUJD"
    large = "data:application/pdf;base64," + "A" * (9 * 1024 * 1024)
    return [{"name": f"tep_{i}_1787560359.pdf", "dataUrl": large if i in big else small} for i in range(n)]


def test_planner_toi_da_5_tep_moi_dong_va_canh_bao_tep_qua_6mb():
    items, warnings = planner.build_plan_items(_files(4, big={1}), planner.CONFIG_DIEU_CHINH_UBND)
    assert [i["fileIndex"] for i in items] == [0, 1, 2, 3]
    assert all(i["target"] == "fixed-slot" and i["slotIndex"] == 5 and i["tickRow"] for i in items)
    assert all(i["documentName"] == i["fileName"] for i in items)
    assert len(warnings) == 1 and "tep_1_" in warnings[0] and "tep_0_" not in warnings[0]


def test_qua_5_tep_van_ban_de_nghi_vao_dong_chinh_phan_con_lai_sang_giay_to_khac():
    llm = {i: ("other", f"Tài liệu số {i}") for i in range(8)}
    llm[7] = ("van_ban_de_nghi", "Văn bản đề nghị điều chỉnh dự án")
    llm[6] = ("other", "")
    items, warnings = planner.build_plan_items(_files(8), planner.CONFIG_DIEU_CHINH_BQL, llm)
    assert sorted(i["fileIndex"] for i in items) == list(range(8)), "không tệp nào bị bỏ"
    fixed = [i for i in items if i["target"] == "fixed-slot"]
    other = [i for i in items if i["target"] == "new"]
    assert len(fixed) == 5 and fixed[0]["fileIndex"] == 7
    assert [i["fileIndex"] for i in other] == [4, 5, 6]
    assert other[0]["componentName"] == "Tài liệu số 4" and other[0]["needsAddComponent"]
    # LLM không đặt được tên → tên tệp đã bỏ dãy số upload.
    assert other[2]["componentName"] == "tep 6"
    assert warnings and "Giấy tờ khác" in warnings[0]


def test_trang_khong_co_giay_to_khac_tran_sang_dong_cung_ho_so():
    items, warnings = planner.build_plan_items(_files(23), planner.CONFIG_CHAP_THUAN_UBND)
    slots = [i["slotIndex"] for i in items]
    assert slots.count(0) == slots.count(1) == slots.count(3) == slots.count(5) == 5
    assert all(i["target"] == "fixed-slot" for i in items) and len(items) == 20
    assert any("đính tay" in w and "tep_22_" in w for w in warnings)


def test_doanh_nghiep_chon_doi_tuong_truoc_va_khong_phat_o_ca_nhan_bi_an():
    fields, _ = mapper.enrich(_DOANH_NGHIEP, {"formContext": _ANCHOR})
    names = [f["name"] for f in fields]
    values = _values(fields)
    chs = [n for n in names if n.startswith("ChuHoSo_")]
    assert chs[0] == "ChuHoSo_maDoiTuongNopHS"
    assert values["ChuHoSo_maDoiTuongNopHS"] == "Doanh nghiệp/ Tổ chức"
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Công ty TNHH Mẫu"
    assert values["ChuHoSo_maSoThueChuHoSo"] == "5300000001"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Lô CN2"
    assert values["ChuHoSo_diDongLienLacCHS"] == "02143000001"
    for hidden in ("ChuHoSo_tenChuHoSo", "ChuHoSo_ngaySinhChuHoSo", "ChuHoSo_soCMNDChuHoSo",
                   "ChuHoSo_gioiTinhChuHoSo", "ChuHoSo_ngayCapCMNDCHS"):
        assert hidden not in values, hidden


def test_che_do_tai_khoan_lay_nhan_than_nguoi_dai_dien_khi_la_chinh_tai_khoan():
    fields, warnings = mapper.enrich(_DOANH_NGHIEP, {"formContext": _ANCHOR})
    values = _values(fields)
    assert "CongDan_tenCongDan" not in values and "CongDan_soCmnd" not in values
    assert values["CongDan_ngaySinhCongDan"] == "15/08/1968"
    assert values["CongDan_ngayCapCmnd"] == "09/08/2021"
    assert values["CongDan_maTinhThanh"] == "Thành phố Hà Nội"
    assert values["CongDan_diaChi"] == "Số nhà 1, phố Mẫu"
    # Người nộp đại diện doanh nghiệp → tên cơ quan/MST khối người nộp là của doanh nghiệp.
    assert values["CongDan_tenCoQuanToChuc"] == "Công ty TNHH Mẫu"
    assert not any("NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_che_do_tai_khoan_khong_phai_nguoi_trong_ho_so_thi_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_DOANH_NGHIEP, {"formContext": {
        "applicantFullname": "Trần Thị B", "applicantIdentityNumber": "001199000002",
    }})
    values = _values(fields)
    assert "CongDan_ngaySinhCongDan" not in values and "CongDan_diaChi" not in values
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)
    # Khối chủ hồ sơ (nhà đầu tư) độc lập với người đi nộp.
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Công ty TNHH Mẫu"


def test_che_do_to_khai_ghi_ho_ten_can_cuoc_nguoi_ky_van_ban_de_nghi():
    fields, _ = mapper.enrich(_DOANH_NGHIEP, {"submitterMode": "owner_as_submitter", "formContext": _ANCHOR})
    names = [f["name"] for f in fields]
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "Nguyễn Văn A"
    assert values["CongDan_soCmnd"] == "001068000001"
    assert values["CongDan_ngaySinhCongDan"] == "15/08/1968"
    cong_dan = [n for n in names if n.startswith("CongDan_")]
    assert cong_dan[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]


def test_doanh_nghiep_khong_muon_dia_chi_nguoi_nop_lam_tru_so():
    facts = [f for f in _DOANH_NGHIEP if f["name"] != "ChuHoSo_NoiCuTru"]
    fields, warnings = mapper.enrich(facts, {"formContext": _ANCHOR})
    values = _values(fields)
    assert "ChuHoSo_diaChiChuHoSo" not in values
    assert any("địa chỉ nhà đầu tư" in w for w in warnings)


def test_nha_dau_tu_ca_nhan_dien_nhan_than_chu_ho_so():
    facts = [
        {"name": "ChuHoSo_LaToChuc", "value": False},
        {"name": "ChuHoSo_HoTen", "value": "LÊ VĂN C"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "001090000003"},
        {"name": "ChuHoSo_NgaySinh", "value": "01/02/1990"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Tỉnh Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Tổ 1"}},
    ]
    fields, _ = mapper.enrich(facts, {"formContext": _ANCHOR})
    values = _values(fields)
    assert values["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    assert values["ChuHoSo_tenChuHoSo"] == "LÊ VĂN C"
    assert values["ChuHoSo_soCMNDChuHoSo"] == "001090000003"
    assert "ChuHoSo_tenCoQuanToChucCHS" not in values


def test_popup_gui_form_context_cho_ca_3_thu_tuc():
    popup = _root() / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    for key, _, _ in _KEYS.values():
        assert f'cfg.key === "{key}"' in block, key


def test_khong_doc_duoc_nha_dau_tu_thi_khong_chon_doi_tuong():
    fields, warnings = mapper.enrich([], {"formContext": _ANCHOR})
    assert "ChuHoSo_maDoiTuongNopHS" not in _values(fields)
    assert any("Đối tượng nộp hồ sơ" in w for w in warnings)


def test_nguoi_dai_dien_khong_co_so_rieng_thi_di_dong_lay_so_doanh_nghiep():
    fields, _ = mapper.enrich(_DOANH_NGHIEP, {"formContext": _ANCHOR})
    assert _values(fields)["CongDan_diDong"] == "02143000001"


def test_chi_co_so_dinh_danh_khong_ngay_cap_thi_khong_suy_noi_cap():
    facts = [f for f in _DOANH_NGHIEP if f["name"] != "NguoiTrongGiayTo"] + [{"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Nguyễn Văn A", "SoDinhDanh": "001068000001", "NgaySinh": "15/08/1968"},
    ]}]
    fields, _ = mapper.enrich(facts, {"formContext": _ANCHOR})
    assert "CongDan_noiCapCmnd" not in _values(fields)
