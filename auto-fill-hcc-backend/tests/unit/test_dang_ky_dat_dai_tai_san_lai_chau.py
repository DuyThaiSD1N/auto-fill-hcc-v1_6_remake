"""[Lai Châu] Đăng ký đất đai, tài sản gắn liền với đất, cấp GCN lần đầu (1.013978).

Khóa hai phần vừa bổ sung:
  - process: 3 ô địa chỉ BẮT BUỘC (*) + các ô liên hệ trước đây bị thiếu, và thứ tự ưu tiên nguồn
    ĐƠN/TỜ KHAI > CCCD;
  - attach: bảng 20 dòng fixed-slot, định tuyến dòng 1/5/8 theo ảnh ánh xạ hồ sơ mẫu.

Dữ liệu trong test là PLACEHOLDER, không phải hồ sơ thật của người dân.
"""

import base64

from app.pipelines.dang_ky_dat_dai_tai_san.attach import planner
from app.pipelines.dang_ky_dat_dai_tai_san.process import mapper
from app.pipelines.dang_ky_dat_dai_tai_san.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_dat_dai_tai_san.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-dat-dai-tai-san-lan-dau-nguoi-o-nuoc-ngoai"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _comps(fields: list[dict]) -> dict:
    return {item["name"]: item["comp"] for item in fields}


def _identity_facts() -> list[dict]:
    return [
        {"name": "Cccd_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Cccd_SoDinhDanh", "value": "012345678901"},
        {"name": "Cccd_NgaySinh", "value": "01/01/1980"},
        {"name": "Cccd_GioiTinh", "value": "Nam"},
        {"name": "Cccd_DanToc", "value": "Kinh"},
        {"name": "Cccd_NgayCap", "value": "02/02/2022"},
        {"name": "Cccd_NoiCap", "value": "Công an tỉnh Lai Châu"},
    ]


# ---------------------------------------------------------------- process/mapper


def test_mapper_emits_three_required_address_fields():
    """3 ô (*) Tỉnh/Thành phố, Phường/Xã, Số nhà/Đường/Tổ/Ấp/Thôn/Xóm trước đây KHÔNG được phát."""
    source = _identity_facts() + [
        {
            "name": "Don_DiaChi",
            "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "diaChi": "Tổ 1"},
        },
    ]

    fields = mapper.enrich(source)
    values = _values(fields)
    comps = _comps(fields)

    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu"
    assert values["CongDan_maPhuongXa"] == "Phường Đoàn Kết"
    assert values["CongDan_diaChi"] == "Tổ 1"
    # Tỉnh/Phường-Xã là <select> trên form, KHÔNG phải input trần.
    assert comps["CongDan_maTinhThanh"] == "dom-select"
    assert comps["CongDan_maPhuongXa"] == "dom-select"
    assert comps["CongDan_diaChi"] == "dom-input"


def test_mapper_emits_newly_added_contact_and_address_text_fields():
    source = _identity_facts() + [
        {
            "name": "Don_DiaChi",
            "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "diaChi": "Tổ 1"},
        },
        {"name": "Don_DienThoai", "value": "0912.345.678"},
        {"name": "Don_Email", "value": "nguoinop@example.com"},
    ]

    fields = mapper.enrich(source)
    values = _values(fields)
    comps = _comps(fields)

    assert values["CongDan_diDong"] == "0912345678"  # bỏ dấu chấm người dân hay viết trên đơn
    assert values["CongDan_email"] == "nguoinop@example.com"
    # Hai ô text địa chỉ đầy đủ ghép từ cùng một nguồn địa chỉ.
    full = "Tổ 1, Phường Đoàn Kết, Tỉnh Lai Châu"
    assert values["CongDan_noiOHienTai"] == full
    assert values["CongDan_diaChiThuongTru"] == full
    # "Nơi cấp CMND (CA Tỉnh)" là danh mục tỉnh -> phải ra nhãn tỉnh, không phải nguyên văn nơi cấp.
    assert values["CongDan_maTinhCapCMND"] == "Tỉnh Lai Châu"
    assert comps["CongDan_maTinhCapCMND"] == "dom-select"


def test_mapper_prefers_don_address_over_cccd_address():
    """CCCD là nguồn CUỐI CÙNG: thẻ cũ hay ghi đơn vị hành chính trước sáp nhập."""
    source = _identity_facts() + [
        {
            "name": "Cccd_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Xã Cũ", "diaChi": "Bản Cũ"},
        },
        {
            "name": "Don_DiaChi",
            "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "diaChi": "Tổ 1"},
        },
    ]

    values = _values(mapper.enrich(source))

    assert values["CongDan_maPhuongXa"] == "Phường Đoàn Kết"
    assert values["CongDan_diaChi"] == "Tổ 1"
    assert "Cũ" not in values["CongDan_diaChiThuongTru"]


def test_mapper_falls_back_to_cccd_address_when_don_missing():
    source = _identity_facts() + [
        {
            "name": "Cccd_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "diaChi": "Tổ 1"},
        },
    ]

    values = _values(mapper.enrich(source))

    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu"
    assert values["CongDan_maPhuongXa"] == "Phường Đoàn Kết"
    assert values["CongDan_diaChi"] == "Tổ 1"


def test_mapper_keeps_existing_identity_and_certificate_fields():
    """Thủ tục ĐANG CHẠY THẬT: các ô cũ phải giữ nguyên hành vi."""
    source = _identity_facts() + [
        {"name": "Gcn_SoPhatHanh", "value": "AA 123456"},
        {"name": "Gcn_NgayCap", "value": "03/03/2020"},
        {"name": "Gcn_CoQuanCap", "value": "TM. ỦY BAN NHÂN DÂN tỉnh Lai Châu CHỦ TỊCH"},
    ]

    values = _values(mapper.enrich(source))

    assert values["CongDan_tenCongDan"] == "NGUYỄN VĂN A"
    assert values["CongDan_soCmnd"] == "012345678901"
    assert values["CongDan_soCCCD"] == "012345678901"
    assert values["CongDan_maDMQuocGia"] == "Việt Nam"
    assert values["CongDan_soGCNGP"] == "AA 123456"
    assert values["CongDan_ngayCapGCNGP"] == "03/03/2020"
    assert values["CongDan_noiCapGCNGP"].startswith("UBND")


def test_mapper_never_emits_unsourced_or_hidden_fields():
    """fax/website không có nguồn trên giấy tờ; maDMDiaChi nằm trong column-24 display:none."""
    source = _identity_facts() + [
        {
            "name": "Don_DiaChi",
            "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "diaChi": "Tổ 1"},
        },
    ]

    names = set(_values(mapper.enrich(source)))

    for hidden in ("CongDan_fax", "CongDan_website", "CongDan_maDMDiaChi"):
        assert hidden in UI_COMP_BY_NAME, "vẫn khai để biết ô có thật trên form"
        assert hidden not in names, "nhưng KHÔNG được phát (không có nguồn / ô ẩn)"


def test_mapper_skips_issuer_province_when_not_a_provincial_police():
    """Thẻ căn cước đời mới ghi Bộ Công an -> select danh mục tỉnh không có option tương ứng."""
    source = [item for item in _identity_facts() if item["name"] != "Cccd_NoiCap"]
    source.append({"name": "Cccd_NoiCap", "value": "Bộ Công an"})

    values = _values(mapper.enrich(source))

    assert "CongDan_maTinhCapCMND" not in values
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"


def test_schema_declares_all_26_form_fields_and_new_source_facts():
    assert len(UI_COMP_BY_NAME) == 26, "bước 2 render đúng 26 ô CongDan_*"
    for name in ("Don_DiaChi", "Don_DienThoai", "Don_Email"):
        assert name in ALLOWED
    # Quy tắc ưu tiên nguồn địa chỉ phải nằm trong prompt, không phải trong mapper.
    assert "Mẫu số 13" in EXTRA_RULES
    assert "CUỐI CÙNG" in EXTRA_RULES


# ---------------------------------------------------------------- attach/planner


def test_slots_cover_20_rows_zero_based():
    assert len(planner.SLOTS) == 20
    assert [slot["slotIndex"] for slot in planner.SLOTS] == list(range(20))
    assert len({slot["slotKey"] for slot in planner.SLOTS}) == 20
    assert planner.SLOTS[0]["slotName"].startswith("Mẫu số 13. Đơn đăng ký đất đai")
    assert planner.SLOTS[4]["slotName"].startswith("Sơ đồ hoặc bản trích lục bản đồ địa chính")
    assert planner.SLOTS[7]["slotName"].startswith("Giấy tờ về việc chuyển quyền sử dụng đất, quyền sở hữu")


def test_attachment_routes_follow_mapping_image():
    """Ảnh ánh xạ: Đơn+13a+CCCD -> dòng 1; trích đo/mô tả ranh giới/GCN liền kề -> dòng 5;
    giấy tờ chuyển quyền + cam kết nguồn gốc đất -> dòng 8; GCN diện tích tăng thêm -> dòng 12."""
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "danh-sach-13a.pdf", "type": "application/pdf"},
        {"name": "cccd.pdf", "type": "application/pdf"},
        {"name": "trich-do.pdf", "type": "application/pdf"},
        {"name": "mo-ta-ranh-gioi.pdf", "type": "application/pdf"},
        {"name": "gcn-lien-ke.pdf", "type": "application/pdf"},
        {"name": "chuyen-quyen.pdf", "type": "application/pdf"},
        {"name": "cam-ket.pdf", "type": "application/pdf"},
        {"name": "gcn-tang-them.pdf", "type": "application/pdf"},
    ]
    llm_types = {
        0: "don_dang_ky",
        1: "danh_sach_su_dung_chung",
        2: "identity",
        3: "so_do_trich_luc_trich_do",
        4: "ban_mo_ta_ranh_gioi",
        5: "gcn_thua_lien_ke",
        6: "giay_to_chuyen_quyen",
        7: "cam_ket_nguon_goc_dat",
        8: "gcn_dien_tich_tang_them",
    }

    attachments, warnings, classified = planner.build_plan_items(files, None, llm_types)

    assert warnings == []
    assert [item["fileIndex"] for item in attachments] == list(range(9))
    assert [item["slotIndex"] for item in attachments] == [0, 0, 0, 4, 4, 4, 7, 7, 11]
    assert [item["docType"] for item in classified] == list(llm_types.values())
    # Engine fixed-slot của eForm Lai Châu, KHÔNG phải attp-row của Form.io.
    assert all(item["target"] == "fixed-slot" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # componentName = tên dòng VERBATIM để FE khớp theo text đã fold dấu.
    assert all(item["componentName"] == item["slotName"] for item in attachments)
    # KHÔNG set Bản chính/Bản sao và không set số bản — cán bộ/cổng tự quyết.
    assert all("loaiBan" not in item and "soBan" not in item for item in attachments)


def test_remaining_rows_route_by_their_own_row_name():
    files = [{"name": f"f{i}.pdf", "type": "application/pdf"} for i in range(11)]
    llm_types = {
        0: "thong_bao_ket_qua_dang_ky",
        1: "thoa_thuan_thua_lien_ke",
        2: "van_ban_thanh_vien_ho_gia_dinh",
        3: "quyet_dinh_xu_phat",
        4: "chung_tu_tai_chinh",
        5: "xac_nhan_xay_dung",
        6: "thua_ke_cong_chung",
        7: "giay_to_dieu_137_khoan1",
        8: "thua_ke_chua_cap_gcn",
        9: "thoa_thuan_cap_chung_gcn",
        10: "van_ban_dai_dien",
    }

    attachments, warnings, _ = planner.build_plan_items(files, None, llm_types)

    assert warnings == []
    assert [item["slotIndex"] for item in attachments] == [1, 2, 3, 5, 6, 8, 9, 10, 12, 16, 17]


def test_other_file_is_not_dropped():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "tai-lieu-la.pdf", "type": "application/pdf"},
    ]

    attachments, warnings, classified = planner.build_plan_items(files, None, {0: "don_dang_ky", 1: "other"})

    assert len(attachments) == 2, "file chưa nhận diện vẫn phải có chỗ đính kèm"
    assert attachments[1]["fileIndex"] == 1
    assert attachments[1]["slotIndex"] == 0
    assert classified[1]["docType"] == "other"
    assert classified[1]["fallback"] is True
    assert len(warnings) == 1 and "tai-lieu-la.pdf" in warnings[0]


def test_missing_or_unknown_llm_type_falls_back_to_other_row_one():
    files = [{"name": "x.pdf", "type": "application/pdf"}]

    attachments, warnings, classified = planner.build_plan_items(files, None, {0: "khong_ton_tai"})

    assert len(attachments) == 1 and attachments[0]["slotIndex"] == 0
    assert classified[0]["docType"] == "other"
    assert len(warnings) == 1


def test_oversized_file_is_reported_with_split_instruction():
    """Cổng chặn cứng 6 MB/tệp; planner không tách file được nên phải báo cho cán bộ."""
    oversized = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "ho-so-gop.pdf", "type": "application/pdf", "dataUrl": oversized},
    ]

    attachments, warnings, classified = planner.build_plan_items(files, None, {0: "don_dang_ky"})

    assert [item["fileIndex"] for item in attachments] == [0], "file quá khổ không vào kế hoạch"
    assert any("6 MB" in text and "ho-so-gop.pdf" in text and "tách" in text for text in warnings)
    assert classified[1]["reason"] == "file_too_large"


def test_planner_is_llm_first_without_keyword_rules():
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_LOAI_BAN")
    # Không có llm_types thì không file nào được đoán sang dòng chuyên biệt.
    files = [{"name": "trich-do.pdf", "type": "application/pdf"}]
    attachments, _, classified = planner.build_plan_items(files, [{"name": "trich-do.pdf", "text": "MẢNH TRÍCH ĐO"}], {})
    assert attachments[0]["slotIndex"] == 0
    assert classified[0]["source"] == "unknown"


# ---------------------------------------------------------------- registry


def test_registry_entry_has_attachment_step_and_both_pipelines():
    procedure = get_procedure(KEY)

    assert procedure is not None
    assert procedure["label"].startswith("[Lai Châu]")
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["laichau.gov.vn"]
    assert callable(get_pipeline(KEY))
    assert callable(get_attach_pipeline(KEY))
    # uploadHint phải nhắc ràng buộc dung lượng của cổng.
    assert "6 MB" in procedure["uploadHint"]
    assert "Mẫu số 13" in procedure["uploadHint"]


# --------------------------------------------------------------------------------------
# Ô "Tên cơ quan/tổ chức" + "MSDN/MST" chỉ dành cho PHÁP NHÂN
# --------------------------------------------------------------------------------------
def test_ca_nhan_khong_dien_ten_to_chuc_va_ma_so_thue():
    """Bug thật: hồ sơ CÁ NHÂN bị điền họ tên vào ô 'Tên cơ quan/tổ chức' và số CCCD vào ô 'MSDN/MST'.
    Hai ô này chỉ dành cho pháp nhân -> cá nhân phải để TRỐNG, KHÔNG fallback."""
    got = _values(mapper.enrich([
        {"name": "Cccd_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Cccd_SoDinhDanh", "value": "012345678901"},
    ]))
    assert got["CongDan_tenCongDan"] == "NGUYỄN VĂN A"
    assert "CongDan_tenCoQuanToChuc" not in got
    assert "CongDan_maSoThueNguoiNop" not in got


def test_to_chuc_dien_ten_va_mst_tu_nguon_rieng():
    """Hồ sơ PHÁP NHÂN: điền từ field nguồn riêng ToChuc_*, không dính gì tới CCCD."""
    got = _values(mapper.enrich([
        {"name": "Cccd_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Cccd_SoDinhDanh", "value": "012345678901"},
        {"name": "ToChuc_Ten", "value": "CÔNG TY TNHH ABC"},
        {"name": "ToChuc_MaSoThue", "value": "0101234567"},
    ]))
    assert got["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH ABC"
    assert got["CongDan_maSoThueNguoiNop"] == "0101234567"
    assert got["CongDan_maSoThueNguoiNop"] != "012345678901"   # không phải CCCD


def test_desc_cam_lay_cccd_lam_mst():
    from app.pipelines.dang_ky_dat_dai_tai_san.process.schema import FIELDS as _F
    mst = next(f["desc"] for f in _F if f["name"] == "ToChuc_MaSoThue")
    ten = next(f["desc"] for f in _F if f["name"] == "ToChuc_Ten")
    assert "KHÔNG lấy số CCCD" in mst and "BỎ FIELD" in mst
    assert "KHÔNG lấy họ tên người dân" in ten
