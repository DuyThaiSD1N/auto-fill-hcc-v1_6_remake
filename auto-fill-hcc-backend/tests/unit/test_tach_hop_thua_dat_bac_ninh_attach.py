"""Đính kèm [BN] Tách/hợp thửa đất (1.011507): khớp thành phần theo MÃ TP-H05 (in trong dòng
tiêu đề mỗi hàng trên cổng), KHÔNG dùng mã KQ (mã kết quả — không hiện ở bảng đính kèm)."""

from app.pipelines.tach_hop_thua_dat_bac_ninh.attach import catalog, planner
from app.pipelines.tach_hop_thua_dat_bac_ninh.attach.planner import _build_item

_FILE = {"name": "x.pdf"}

# Trích OCR thật của giấy ủy quyền trong hồ sơ tách thửa — có nhắc số GCN của thửa đất.
_OCR_UY_QUYEN = (
    "GIẤY ỦY QUYỀN\n1.BÊN ỦY QUYỀN: Ông, bà: P.T.G\n2.BÊN ĐƯỢC ỦY QUYỀN: Ông, bà: P.Q.D\n"
    "Nộp hồ sơ và nhận kết quả tại Chi nhánh Văn phòng đăng ký đất đai đối với thửa đất sau:\n"
    "- Thửa đất số: 156, Tờ bản đồ số: 48\n"
    "Theo giấy chứng nhận quyền sử dụng đất số: AA 0881xxxx"
)


def _item(label: str) -> dict:
    return _build_item(_FILE, 0, label, "Tài liệu")


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _llm(*pairs):
    return {i: {"label": lb, "documentName": dn} for i, (lb, dn) in enumerate(pairs)}


def test_component_names_are_tp_h05_codes_not_kq():
    """FE fill-bacninh khớp componentName = substring text hàng (chứa mã TP-H05), KHÔNG có mã KQ."""
    codes = [code for _, code, _ in catalog.CATALOG if code]
    assert codes, "catalog phải có mã thành phần"
    assert all(code.startswith("TP-H05.") for code in codes), codes
    assert not any(code.startswith("KQ") for code in codes), "KQ là mã kết quả, không khớp bảng đính kèm"


def test_four_slots_map_to_correct_tp_h05_rows():
    assert catalog.resolve("don_tach_thua") == ("existing", "TP-H05.000032")   # Mẫu 22 - Đơn
    assert catalog.resolve("ban_ve_tach_thua") == ("existing", "TP-H05.000033")  # Mẫu 22a - Bản vẽ
    assert catalog.resolve("gcn") == ("existing", "TP-H05.000040")             # Giấy chứng nhận đã cấp
    assert catalog.resolve("van_ban_co_quan") == ("existing", "TP-H05.000047") # Văn bản cơ quan


def test_don_gcn_banve_route_to_existing_slots():
    for label, code in (
        ("don_tach_thua", "TP-H05.000032"),
        ("ban_ve_tach_thua", "TP-H05.000033"),
        ("gcn", "TP-H05.000040"),
    ):
        item = _item(label)
        assert item["target"] == "existing", label
        assert item["componentName"] == code, label
        assert item["slotKey"] == "banChinh", label


def test_cccd_and_other_go_supplementary():
    """CCCD/ủy quyền/giấy phép đo đạc/giấy tờ khác không có ô riêng → ô 'File đính kèm khác'."""
    for label in ("cccd", "uy_quyen", "giay_phep_do_dac", "khac"):
        item = _item(label)
        assert item["target"] == "supplementary", label
        assert item["componentName"] == "", label


def test_ten_hien_thi_dung_so_hieu_mau():
    """documentName trở thành TÊN TỆP trên cổng: Mẫu 22 là ĐƠN, Mẫu 22a là BẢN VẼ."""
    assert catalog.display_name("don_tach_thua") == "Đơn đề nghị tách/hợp thửa (Mẫu 22)"
    assert catalog.display_name("ban_ve_tach_thua") == "Bản vẽ tách/hợp thửa (Mẫu 22a)"
    assert catalog.display_name("uy_quyen") == "Giấy ủy quyền"
    assert catalog.display_name("giay_phep_do_dac") == "Giấy phép hoạt động đo đạc và bản đồ"


def test_uy_quyen_khong_bi_xep_thanh_giay_chung_nhan():
    """Lỗi thật: ủy quyền có trích số GCN của thửa đất → lưới keyword cũ gán thành 'gcn'."""
    items, _, classified = planner.build_plan_items(
        _files(["uy-quyen.pdf"]), _llm(("uy_quyen", "Giấy ủy quyền"))
    )

    assert items[0]["target"] == "supplementary"
    assert items[0]["componentName"] == ""
    assert items[0]["documentName"] == "Giấy ủy quyền"
    assert classified[0]["routeSrc"] == "llm"
    # Chuỗi OCR gây lỗi vẫn nằm đó nhưng không còn lưới nào đọc nó để đoán loại.
    assert "giấy chứng nhận quyền sử dụng đất" in _OCR_UY_QUYEN.lower()


def test_llm_khong_ro_loai_van_vao_o_bo_sung_khong_bi_keo_ve_gcn():
    items, warnings, classified = planner.build_plan_items(
        _files(["la.pdf"]), _llm(("khac", ""))
    )

    assert items[0]["target"] == "supplementary"
    assert items[0]["componentName"] == ""
    # LLM chủ động nói "không rõ" → routeSrc vẫn là llm; "default" dành cho lúc LLM im lặng/lỗi.
    assert classified[0]["routeSrc"] == "llm"
    assert any("không bỏ sót" in w for w in warnings)

    _, _, classified_no_llm = planner.build_plan_items(_files(["la.pdf"]), {})
    assert classified_no_llm[0]["routeSrc"] == "default"


def test_giu_ten_that_cua_tai_lieu_chua_ro_loai():
    """Tên chung chung 'Tài liệu kèm theo.pdf' khiến cán bộ không biết là giấy gì."""
    items, _, _ = planner.build_plan_items(
        _files(["gp.pdf"]), _llm(("khac", "Giấy phép hoạt động đo đạc và bản đồ"))
    )

    assert items[0]["documentName"] == "Giấy phép hoạt động đo đạc và bản đồ"

    # LLM không đọc được tên → mới dùng nhãn mặc định.
    items, _, _ = planner.build_plan_items(_files(["x.pdf"]), _llm(("khac", "")))
    assert items[0]["documentName"] == "Tài liệu kèm theo"


def test_khong_bo_sot_file_nao():
    names = ["gcn.pdf", "don.pdf", "ban-ve.pdf", "uy-quyen.pdf", "cccd.pdf", "gp-do-dac.pdf"]
    items, _, _ = planner.build_plan_items(
        _files(names),
        _llm(
            ("gcn", "Giấy chứng nhận QSDĐ"),
            ("don_tach_thua", "Đơn đề nghị tách thửa"),
            ("ban_ve_tach_thua", "Bản vẽ tách thửa"),
            ("uy_quyen", "Giấy ủy quyền"),
            ("cccd", "Căn cước công dân"),
            ("giay_phep_do_dac", "Giấy phép hoạt động đo đạc và bản đồ"),
        ),
    )

    assert [i["fileIndex"] for i in items] == list(range(len(names)))
    by_file = {i["fileName"]: i["componentName"] for i in items}
    assert by_file["gcn.pdf"] == "TP-H05.000040"
    assert by_file["don.pdf"] == "TP-H05.000032"
    assert by_file["ban-ve.pdf"] == "TP-H05.000033"
    assert by_file["uy-quyen.pdf"] == ""
    assert by_file["gp-do-dac.pdf"] == ""


def test_llm_chet_van_dinh_du_file():
    items, warnings, _ = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert len(items) == 2
    assert all(i["target"] == "supplementary" for i in items)
    assert warnings


def test_khong_con_luoi_keyword_trong_planner():
    """Chốt: phân loại thuần LLM, planner không được tự đọc OCR để đoán loại."""
    for name in ("_label_by_keywords", "_label_by_filename", "_looks_like_identity"):
        assert not hasattr(planner, name), f"{name} phải bị gỡ khỏi planner"


def test_prompt_co_bay_uy_quyen_va_giay_chung_nhan():
    from app.pipelines.tach_hop_thua_dat_bac_ninh.attach.prompt import (
        SYSTEM_PROMPT,
        build_user_prompt,
    )

    assert "NHẮC TỚI GIẤY CHỨNG NHẬN ≠ LÀ GIẤY CHỨNG NHẬN" in SYSTEM_PROMPT
    assert "ỦY QUYỀN ≠ GIẤY CHỨNG NHẬN" in SYSTEM_PROMPT
    assert "MẪU 22 LÀ ĐƠN, MẪU 22a LÀ BẢN VẼ" in SYSTEM_PROMPT
    assert "uy_quyen" in SYSTEM_PROMPT and "giay_phep_do_dac" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT
    assert "KHÔNG BỊA" in SYSTEM_PROMPT
    assert "6 phần tử" in build_user_prompt([{"index": i, "text": ""} for i in range(6)])
