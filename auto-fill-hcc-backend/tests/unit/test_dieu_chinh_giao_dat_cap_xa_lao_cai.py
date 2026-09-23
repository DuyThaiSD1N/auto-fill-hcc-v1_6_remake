"""[Lào Cai — cấp xã] Điều chỉnh quyết định giao đất, cho thuê đất (1.115680).

Cùng nghiệp vụ với bản nộp ở Sở (1.115652) và bước 2 giống hệt, nhưng cơ quan tiếp nhận cấp xã yêu
cầu đính kèm KHÁC HẲN: hai dòng thành phần tương ứng để TRỐNG, quyết định + thông báo gộp một tệp vào
một dòng "Giấy tờ khác"; ô "Về việc" thì giữ nguyên chuỗi cổng điền sẵn.
"""

from pathlib import Path

from app.pipelines.dieu_chinh_giao_dat_cap_xa_lao_cai.attach import planner
from app.pipelines.dieu_chinh_giao_dat_cap_xa_lao_cai.process import mapper
from app.pipelines.dieu_chinh_giao_dat_cap_xa_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "dieu-chinh-quyet-dinh-giao-dat-cap-xa-lao-cai"
_SO_KEY = "dieu-chinh-quyet-dinh-giao-dat-lao-cai"
_SNAPSHOT = (
    Path(__file__).resolve().parents[2].parent / "thongtin"
    / "167- Lào Cai-Thủ tục điều chỉnh quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất."
    / "167 đính kèm.html"
)


def _entry(key=_KEY):
    return next(p for p in public_list() if p["key"] == key)


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_registry_khoa_bang_ma_va_thang_rule_theo_ten():
    """Tên 1.115652 là CHUỖI CON của tên trang này → chỉ mã mới tách được hai thủ tục."""
    entry = _entry()
    detect = entry["detect"]

    assert detect["urlScope"] == ["dichvucong.laocai.gov.vn"]
    assert "1.115680" in detect["textIncludes"]
    assert detect["textPriority"] is True
    assert entry["label"].startswith("[Tỉnh Lào Cai(cấp xã)]")
    assert entry["hasAttachmentStep"] is True

    so = _entry(_SO_KEY)
    assert sum(map(len, detect["textIncludes"])) > sum(map(len, so["detect"]["textIncludes"]))
    # Trang của Sở không chứa mã 1.115680 nên entry cấp xã không cướp được nó.
    assert not any("1.115680" in t for t in so["detect"]["textIncludes"])


def test_slot_name_khop_text_that_tren_cong():
    if not _SNAPSHOT.exists():
        return
    html = " ".join(_SNAPSHOT.read_text(encoding="utf-8", errors="replace").split())
    for doc_type, route in planner._ROUTES.items():
        assert " ".join(route["slotName"].split()) in html, doc_type


def test_ho_so_mau_cua_ba_don_vao_dong_1_con_qd_va_tb_xuong_giay_to_khac():
    """Ánh xạ BA: Đơn → dòng 1; QĐ và văn bản thay đổi căn cứ xuống "Giấy tờ khác", mỗi tệp một dòng."""
    names = [
        "Don_dusigned_1787126956.pdf",       # Đơn đề nghị điều chỉnh (Mẫu 04)
        "QD_DUsigned_1787126974.pdf",        # QĐ 2153/QĐ-UBND giao đất
        "TB_SO_140signed_1787126978.pdf",    # TB 140/TB-NNMT kết quả kiểm tra
    ]
    items, _, classified = planner.build_plan_items(
        _files(names),
        {0: ("don_mau_04", ""), 1: ("quyet_dinh_bi_dieu_chinh", ""),
         2: ("van_ban_thay_doi_can_cu", "")},
    )

    assert len(items) == 3, "mỗi tệp một dòng, không gộp"
    don, qd, tb = items
    assert don["slotIndex"] == 0 and don["target"] == "fixed-slot"

    for item in (qd, tb):
        assert item["target"] == "new" and item["needsAddComponent"] is True
        assert item["noChooserClick"] is True
        assert "sourceFileIndexes" not in item, "không gộp tệp — cán bộ còn xem/xoá được từng tệp"
    # Tên dòng cố định theo LOẠI để đọc là biết giấy gì.
    assert qd["componentName"] == "bản chính quyết định"
    assert tb["componentName"] == "bản chính văn bản thay đổi căn cứ"
    assert qd["documentName"] == qd["componentName"]
    # Dòng 2 và 3 phải TRỐNG — không item nào trỏ vào chúng.
    assert all(i.get("slotIndex") not in (1, 2) for i in items)
    assert [c["fileName"] for c in classified] == names


def test_khac_ban_nop_o_so_o_hai_dong_tuong_ung():
    """_ROUTES vẫn giữ đủ ba dòng để đổi lại hành vi bằng cách rút khỏi _TEN_DONG_GIAY_TO_KHAC."""
    assert [r["slotIndex"] for r in planner._ROUTES.values()] == [0, 1, 2]
    assert set(planner._TEN_DONG_GIAY_TO_KHAC) == {
        "quyet_dinh_bi_dieu_chinh", "van_ban_thay_doi_can_cu",
    }


def test_giay_to_la_van_co_ten_rieng_do_llm_dat():
    """Giấy tờ ngoài danh mục KHÔNG đội tên cố định của quyết định — nó có tên riêng."""
    items, warnings, _ = planner.build_plan_items(
        _files(["uy_quyen.pdf", "qd.pdf"]),
        {0: ("other", "Giấy uỷ quyền nộp hồ sơ"), 1: ("quyet_dinh_bi_dieu_chinh", "")},
    )
    by_name = {i["componentName"]: i for i in items}

    assert "Giấy uỷ quyền nộp hồ sơ" in by_name
    assert "bản chính quyết định" in by_name


def test_hai_quyet_dinh_cung_loai_khong_de_ra_hai_dong_trung_ten():
    """Hai dòng trùng tên là cán bộ không phân biệt được văn bản nào."""
    items, _, _ = planner.build_plan_items(
        _files(["qd1.pdf", "qd2.pdf"]),
        {0: ("quyet_dinh_bi_dieu_chinh", ""), 1: ("quyet_dinh_bi_dieu_chinh", "")},
    )
    names = [i["componentName"] for i in items]

    assert names == ["bản chính quyết định", "bản chính quyết định 2"]


def test_canh_bao_tep_vuot_6mb():
    import base64

    big = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    files = [{"name": "qd.pdf", "type": "application/pdf", "dataUrl": big}]
    _, warnings, _ = planner.build_plan_items(files, {0: ("quyet_dinh_bi_dieu_chinh", "")})

    assert any("6 MB" in w and "qd.pdf" in w for w in warnings)


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["target"] == "new" for i in items)
    assert warnings and all(c["source"] == "default" for c in classified)


def test_o_ve_viec_giu_nguyen_khong_ghi_de():
    """Cơ quan cấp xã yêu cầu giữ chuỗi cổng điền sẵn — NGƯỢC với 1.115652."""
    fields, _ = mapper.enrich([
        {"name": "Don_TrichYeu", "value": "Đề nghị điều chỉnh Quyết định số 2153/QĐ-UBND"},
        {"name": "QuyetDinhGoc_So", "value": "2153/QĐ-UBND"},
    ], {})

    assert "HoSoOnline_veViec" not in _values(fields)
    # Ô vẫn khai trong UI_COMP_BY_NAME để bật lại chỉ bằng một dòng add(...).
    assert "HoSoOnline_veViec" in UI_COMP_BY_NAME


def test_doi_tuong_nop_ho_so_phat_option_value():
    """Nhãn tổ chức của cổng là "Doanh nghiệp/ Tổ chức" và còn có "Tổ chức khác" → phát value."""
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH ABC"},
    ], {})
    assert _values(fields)["ChuHoSo_maDoiTuongNopHS"] == "DN"

    fields, _ = mapper.enrich([{"name": "ChuHoSo_HoTen", "value": "Trần Như Dư"}], {})
    assert _values(fields)["ChuHoSo_maDoiTuongNopHS"] == "CN"


def test_hai_che_do_nguoi_nop_van_chay():
    facts = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN NHƯ DƯ"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "010060001234"},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "TRẦN NHƯ DƯ", "SoDinhDanh": "010060001234", "NgaySinh": "05/05/1960",
             "NgayCap": "21/11/2025", "NoiCap": "Bộ Công an",
             "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 5"}},
        ]},
    ]
    anchor = {"applicantFullname": "TRẦN NHƯ DƯ", "applicantIdentityNumber": "010060001234"}

    values = _values(mapper.enrich(facts, {"formContext": anchor})[0])
    assert values["CongDan_ngaySinhCongDan"] == "05/05/1960"
    assert values["CongDan_tenCongDan"] == "TRẦN NHƯ DƯ"

    values = _values(mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})[0])
    assert values["CongDan_tenCongDan"] == "TRẦN NHƯ DƯ"

    fields, warnings = mapper.enrich(facts, {})
    assert "CongDan_ngaySinhCongDan" not in _values(fields)
    assert any("NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_popup_gui_form_context_cho_thu_tuc_nay():
    popup = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "popup.js"
    if not popup.exists():
        return
    block = popup.read_text(encoding="utf-8").split("collectFormContext", 1)[0]
    assert f'cfg.key === "{_KEY}"' in block
