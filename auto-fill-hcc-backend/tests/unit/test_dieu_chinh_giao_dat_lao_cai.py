"""[Lào Cai] Điều chỉnh quyết định giao đất, cho thuê đất (1.115652).

Khoá theo ánh xạ của BA: 3 dòng thành phần, giấy tờ lạ phải đi đường "Giấy tờ khác" (có TÊN tài liệu),
ô "Về việc" ghi trích yếu thật, và địa danh trước sáp nhập phải được báo cho cán bộ.
"""

from pathlib import Path

from app.pipelines.dieu_chinh_giao_dat_lao_cai.attach import planner
from app.pipelines.dieu_chinh_giao_dat_lao_cai.process import mapper
from app.pipelines.dieu_chinh_giao_dat_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "dieu-chinh-quyet-dinh-giao-dat-lao-cai"
_THONGTIN = Path(__file__).resolve().parents[2].parent / "thongtin" / "lào cai điều chỉnh"


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def test_registry_co_buoc_dinh_kem_va_khoa_dung_cong():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["dichvucong.laocai.gov.vn"]
    assert entry["detect"]["urlIncludes"] == ["1.115652"]
    assert entry["label"].startswith("[Tỉnh Lào Cai]")


def test_ba_dong_thanh_phan_dung_thu_tu_dom():
    assert [r["slotIndex"] for r in planner._ROUTES.values()] == [0, 1, 2]


def test_slot_name_khop_text_that_tren_cong():
    snapshot = _THONGTIN / "lào cài điều chỉnh đính kèm.html"
    if not snapshot.exists():
        return
    html = " ".join(snapshot.read_text(encoding="utf-8", errors="replace").split())
    for doc_type, route in planner._ROUTES.items():
        assert " ".join(route["slotName"].split()) in html, doc_type


def test_ho_so_mau_cua_ba_vao_dung_dong():
    """Ánh xạ BA: đơn → dòng 1; hai tệp quyết định điều chỉnh → CÙNG dòng 3."""
    names = [
        "2026090315141001_1788423288.pdf",          # Đơn Mẫu 04
        "20260414101741011776136690_1788423073.pdf",  # QĐ 894 + QĐ 603
        "20260414165913011776160768_1788423073.pdf",  # QĐ 1132
    ]
    items, warnings, _ = planner.build_plan_items(
        _files(names),
        {0: "don_mau_04", 1: "van_ban_thay_doi_can_cu", 2: "van_ban_thay_doi_can_cu"},
    )

    by_file = {i["fileName"]: i["slotIndex"] for i in items}
    assert by_file[names[0]] == 0
    assert by_file[names[1]] == by_file[names[2]] == 2
    assert all(i["target"] == "fixed-slot" for i in items)
    # Dòng nhận nhiều tệp → nhắc cán bộ ghi danh mục văn bản vào ô Ghi chú.
    assert any("Ghi chú" in w and "2 tệp" in w for w in warnings)


def test_quyet_dinh_bi_dieu_chinh_khac_van_ban_thay_doi_can_cu():
    items, _, _ = planner.build_plan_items(
        _files(["qd857.pdf", "qd1132.pdf"]),
        {0: "quyet_dinh_bi_dieu_chinh", 1: "van_ban_thay_doi_can_cu"},
    )
    assert [i["slotIndex"] for i in items] == [1, 2]


def test_giay_to_la_di_duong_giay_to_khac_co_ten_tai_lieu():
    """Phải là target 'new' để engine otherListFile ĐIỀN TÊN tài liệu, không phải fixed-slot."""
    items, warnings, _ = planner.build_plan_items(
        _files(["GCN_dang_ky_doanh_nghiep.pdf"]), {0: "other"}
    )

    item = items[0]
    assert item["target"] == "new"
    assert item["needsAddComponent"] is True
    assert "slotIndex" not in item
    assert item["componentName"] == "GCN dang ky doanh nghiep"
    assert any("không bỏ sót" in w for w in warnings)


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["target"] == "new" for i in items)
    assert warnings
    assert all(c["source"] == "default" for c in classified)


def test_o_ve_viec_va_ghi_chu_co_that_tren_trang():
    for name in ("HoSoOnline_veViec", "HoSoOnline_ghiChu"):
        assert name in UI_COMP_BY_NAME, name
    snapshot = _THONGTIN / "lào cài điều chỉnh đính kèm.html"
    if not snapshot.exists():
        return
    html = snapshot.read_text(encoding="utf-8", errors="replace")
    for name in ("HoSoOnline_veViec", "HoSoOnline_ghiChu"):
        assert f'name="{name}"' in html, name


def test_ve_viec_la_trich_yeu_that_khong_phai_ten_thu_tuc():
    fields, _ = mapper.enrich([
        {"name": "QuyetDinhGoc_So", "value": "857/QĐ-UBND"},
        {"name": "QuyetDinhGoc_NgayKy", "value": "29/05/2023"},
        {"name": "QuyetDinhGoc_CoQuanBanHanh", "value": "UBND tỉnh Yên Bái"},
        {"name": "DuAn_TenDuAn", "value": "Dự án công viên nghĩa trang X"},
    ])
    ve_viec = _names(fields)["HoSoOnline_veViec"]

    assert ve_viec.startswith("Đề nghị điều chỉnh Quyết định giao đất, cho thuê đất số 857/QĐ-UBND")
    assert "ngày 29/05/2023" in ve_viec and "Dự án công viên nghĩa trang X" in ve_viec


def test_ve_viec_khong_bia_so_quyet_dinh():
    fields, _ = mapper.enrich([{"name": "DuAn_TenDuAn", "value": "Dự án X"}])
    assert "HoSoOnline_veViec" not in _names(fields)


def test_dia_danh_truoc_sap_nhap_duoc_chuan_hoa_va_canh_bao():
    """QĐ cũ ghi 'xã Minh Bảo, tỉnh Yên Bái'; sau sáp nhập xã đó không còn trong danh mục."""
    fields, warnings = mapper.enrich([
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY CỔ PHẦN X"},
        {"name": "ChuHoSo_NoiCuTru",
         "value": {"tinh": "Yên Bái", "xa": "Xã Minh Bảo", "diaChi": "Thôn Thanh Niên"}},
    ])
    by_name = _names(fields)

    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert "ChuHoSo_maPhuongXaCHS" not in by_name
    assert any("trước sáp nhập" in w for w in warnings)


def test_dia_danh_hien_hanh_thi_dien_du_khong_canh_bao():
    fields, warnings = mapper.enrich([
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY CỔ PHẦN X"},
        {"name": "ChuHoSo_NoiCuTru",
         "value": {"tinh": "Yên Bái", "xa": "Phường Nam Cường", "diaChi": "Thôn Thanh Niên"}},
    ])
    by_name = _names(fields)

    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Nam Cường"
    assert not any("trước sáp nhập" in w for w in warnings)


def test_doi_tuong_to_chuc_phat_truoc_o_phu_thuoc():
    """2 ô tenCoQuanToChucCHS/maSoThueChuHoSo chỉ HIỆN khi 'Đối tượng nộp hồ sơ' = DN (sheet2 của BA)."""
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY CỔ PHẦN X"},
        {"name": "ChuHoSo_MaSoThue", "value": "0106761822"},
    ])
    order = [f["name"] for f in fields]

    assert order.index("ChuHoSo_maDoiTuongNopHS") < order.index("ChuHoSo_tenCoQuanToChucCHS")
    assert order.index("ChuHoSo_maDoiTuongNopHS") < order.index("ChuHoSo_maSoThueChuHoSo")
    assert _names(fields)["ChuHoSo_maDoiTuongNopHS"] == "Tổ chức"


def test_nguoi_nop_la_chu_ho_so_van_phat_du_dia_chi():
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NoiCuTru",
         "value": {"tinh": "Lào Cai", "xa": "Phường Nam Cường", "diaChi": "Thôn Thanh Niên"}},
    ])
    by_name = _names(fields)

    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Nam Cường"
    assert by_name["ChuHoSo_diaChiChuHoSo"] == "Thôn Thanh Niên"


def test_prompt_co_bay_phan_biet_hai_loai_quyet_dinh():
    from app.pipelines.dieu_chinh_giao_dat_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "HAI LOẠI QUYẾT ĐỊNH RẤT DỄ LẪN" in SYSTEM_PROMPT
    assert "ĐIỀU CHỈNH CHỦ TRƯƠNG ĐẦU TƯ LẦN 1/2/3/4" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT
    assert "KHÔNG BỊA" in SYSTEM_PROMPT
