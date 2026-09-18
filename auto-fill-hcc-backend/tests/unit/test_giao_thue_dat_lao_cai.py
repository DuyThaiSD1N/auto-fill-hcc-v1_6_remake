"""[Lào Cai] Giao đất, cho thuê đất — eForm iGate (CongDan_*/ChuHoSo_*) + đính kèm fixed-slot.

Khoá hai điều dễ vỡ: khối CHỦ HỒ SƠ phải có đủ 3 ô địa chỉ (nút "Người nộp là chủ hồ sơ" của cổng
KHÔNG copy địa chỉ), và slotIndex phải đúng thứ tự DOM của 14 ô upload.
"""

from pathlib import Path

from app.pipelines.giao_thue_dat_lao_cai.attach import planner
from app.pipelines.giao_thue_dat_lao_cai.process import mapper
from app.pipelines.giao_thue_dat_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "giao-thue-dat-lao-cai"

_CHU_HO_SO_TO_CHUC = [
    {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
    {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH MỘT THÀNH VIÊN X"},
    {"name": "ChuHoSo_MaSoThue", "value": "5300123456-001"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "012345678901"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Số 1 đường A"}},
]


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def test_co_trong_registry_va_khoa_dung_cong_lao_cai():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["dichvucong.laocai.gov.vn"]
    # Cổng SPA, sid đổi mỗi phiên → không được khóa bằng urlIncludes.
    assert "urlIncludes" not in entry["detect"]


def test_nguoi_nop_la_chu_ho_so_van_phat_du_dia_chi_chu_ho_so():
    """Nút 'Người nộp là chủ hồ sơ' của cổng chỉ copy tới nơi cấp/ngày cấp căn cước, KHÔNG copy địa chỉ."""
    fields, warnings = mapper.enrich(
        _CHU_HO_SO_TO_CHUC + [{"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"}]
    )
    by_name = _names(fields)

    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Cam Đường"
    assert by_name["ChuHoSo_diaChiChuHoSo"] == "Số 1 đường A"
    assert not warnings


def test_khong_phat_checkbox_nguoi_nop_la_chu_ho_so():
    """Không tự bấm checkbox: cổng có thể xoá dữ liệu đã điền khi trạng thái đổi."""
    assert "chkbox_nguoinoplachuhs" not in UI_COMP_BY_NAME
    fields, _ = mapper.enrich(_CHU_HO_SO_TO_CHUC)
    assert "chkbox_nguoinoplachuhs" not in _names(fields)


def test_khong_doc_duoc_dia_chi_thi_canh_bao_thay_vi_im_lang():
    fields, warnings = mapper.enrich([{"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"}])

    assert "ChuHoSo_maTinhThanhCHS" not in _names(fields)
    assert any("KHÔNG sao chép" in w for w in warnings)


def test_ho_so_to_chuc_phat_ten_cong_ty_va_mst_cho_ca_hai_khoi():
    fields, _ = mapper.enrich(_CHU_HO_SO_TO_CHUC)
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Tổ chức"
    assert by_name["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY TNHH MỘT THÀNH VIÊN X"
    assert by_name["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH MỘT THÀNH VIÊN X"
    # Mã số thuế giữ đuôi đơn vị phụ thuộc.
    assert by_name["ChuHoSo_maSoThueChuHoSo"] == "5300123456-001"


def test_ho_so_ca_nhan_khong_bia_to_chuc():
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Xã Y", "diaChi": "Thôn Z"}},
    ])
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    assert "ChuHoSo_tenCoQuanToChucCHS" not in by_name
    assert "CongDan_maSoThueNguoiNop" not in by_name


def test_khong_bia_ngay_thang_khi_chi_co_nam():
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_NgaySinh", "value": "1980"},
    ])
    assert "ChuHoSo_ngaySinhChuHoSo" not in _names(fields)


def test_ui_comp_chi_khai_o_co_that_tren_snapshot():
    """Mọi tên ô khai trong schema phải xuất hiện thật trong 'Lào Cai Giao đất fill.html'."""
    snapshot = (
        Path(__file__).resolve().parents[2].parent
        / "thongtin" / "lào cài giao đất" / "Lào Cai Giao đất fill.html"
    )
    if not snapshot.exists():
        return
    html = snapshot.read_text(encoding="utf-8", errors="replace")
    for name in UI_COMP_BY_NAME:
        assert f'name="{name}"' in html, name


def test_slot_index_dung_thu_tu_dom_cua_14_o_upload():
    assert [r["slotIndex"] for r in planner._ROUTES.values()] == list(range(10))
    assert planner._OTHER_SLOT_INDEX == 10
    assert planner._OTHER_SLOT_INDEX + planner._OTHER_SLOT_COUNT == 14


def test_slot_name_khop_text_that_cua_dong():
    """componentName/slotName chỉ dùng để hiển thị & đối chiếu — phải là text có thật trên trang."""
    snapshot = (
        Path(__file__).resolve().parents[2].parent
        / "thongtin" / "lào cài giao đất" / "Lào Cai Giao đất đính kèm.html"
    )
    if not snapshot.exists():
        return
    html = " ".join(snapshot.read_text(encoding="utf-8", errors="replace").split())
    for doc_type, route in planner._ROUTES.items():
        assert " ".join(route["slotName"].split()) in html, doc_type


def test_slot_key_khong_trung_keyword_cua_extension():
    """slotKey cố ý KHÔNG có trong FIXED_SLOT_KEYWORDS → FE dùng thẳng slotIndex."""
    content = (
        Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "content.js"
    )
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    for doc_type in planner._ROUTES:
        assert f"laocai_gtd_{doc_type}:" not in block, doc_type


def test_mot_bo_ho_so_that_vao_dung_dong():
    names = ["don.pdf", "qd_goc.pdf", "qd_dc_1.pdf", "qd_dc_2.pdf", "dkkd.pdf"]
    items, warnings, _ = planner.build_plan_items(
        _files(names),
        {
            0: "don_mau_01",
            1: "van_ban_chu_truong_dau_tu",
            2: "van_ban_chu_truong_dau_tu",
            3: "van_ban_chu_truong_dau_tu",
            4: "other",  # ĐKKD không phải văn bản phê duyệt dự án
        },
    )

    by_file = {i["fileName"]: i["slotIndex"] for i in items}
    assert by_file["don.pdf"] == 0
    # Quyết định gốc + 2 bản điều chỉnh CÙNG một dòng (ô upload multiple).
    assert by_file["qd_goc.pdf"] == by_file["qd_dc_1.pdf"] == by_file["qd_dc_2.pdf"] == 1
    assert by_file["dkkd.pdf"] == 10
    assert all(i["target"] == "fixed-slot" for i in items)
    assert any("không bỏ sót" in w for w in warnings)


def test_nhieu_tai_lieu_la_trai_deu_qua_cac_o_giay_to_khac():
    items, _, _ = planner.build_plan_items(_files([f"la{i}.pdf" for i in range(6)]), {})

    # 4 ô "giấy tờ khác" (10..13), file thứ 5 trở đi dồn vào ô cuối.
    assert [i["slotIndex"] for i in items] == [10, 11, 12, 13, 13, 13]
    # Giữ TÊN THẬT theo tệp để cán bộ biết là giấy gì.
    assert items[0]["documentName"].startswith("la0")


def test_khong_bo_sot_file_nao_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert warnings
    assert all(c["source"] == "default" for c in classified)


def test_prompt_co_bay_quyet_dinh_dieu_chinh_va_dkkd():
    from app.pipelines.giao_thue_dat_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "QUYẾT ĐỊNH ĐIỀU CHỈNH CHỦ TRƯƠNG ĐẦU TƯ VẪN LÀ van_ban_chu_truong_dau_tu" in SYSTEM_PROMPT
    assert "ĐKKD/ĐKDN) KHÔNG PHẢI văn bản phê duyệt dự án" in SYSTEM_PROMPT
    assert "BA LOẠI PHƯƠNG ÁN SỬ DỤNG ĐẤT GẦN GIỐNG NHAU" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT


def _detect(url: str, body: str) -> str:
    """Bản rút gọn nhánh textPriority + textIncludes của popup.js detectProcedureKeyFromSignals."""
    import re
    import unicodedata

    def norm(value):
        text = unicodedata.normalize("NFD", str(value or ""))
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()

    url, body = url.lower(), norm(body)
    items = [p for p in public_list() if p.get("detect") and not p.get("detectDisabled")]

    def scope_ok(detect):
        scope = detect.get("urlScope")
        return True if not scope else any(u and u.lower() in url for u in scope)

    for only_priority in (True, False):
        best, best_score = "", 0
        for p in items:
            detect = p["detect"]
            if only_priority and not detect.get("textPriority"):
                continue
            if not scope_ok(detect):
                continue
            phrases = [norm(x) for x in (detect.get("textIncludes") or []) if x]
            if not phrases or not all(x in body for x in phrases):
                continue
            score = sum(len(x) for x in phrases)
            if score > best_score:
                best, best_score = p["key"], score
        if best:
            return best
    return ""


_URL_LAO_CAI = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"


def test_trang_giao_dat_lao_cai_nhan_dung_thu_tuc():
    body = (
        "Giao đất, cho thuê đất đối với trường hợp giao đất, cho thuê đất không đấu giá quyền sử dụng "
        "đất, không đấu thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất. "
        "Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư"
    )
    assert _detect(_URL_LAO_CAI, body) == _KEY


def test_trang_dieu_chinh_lao_cai_khong_cuop_trang_giao_dat():
    body = "Điều chỉnh quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất"
    assert _detect(_URL_LAO_CAI, body) == "dieu-chinh-quyet-dinh-giao-dat-lao-cai"


def test_entry_dieu_chinh_cu_khong_con_tu_nhan_dien():
    """Rule cũ chỉ có 2 cụm ["điều chỉnh", "giao đất"] và không khóa cổng → đã tắt tự nhận diện."""
    old = next(p for p in public_list() if p["key"] == "dieu-chinh-dat-dai")
    assert old.get("detectDisabled") is True
    # Trang đất đai tỉnh khác có đủ 2 chữ đó không được rơi vào thủ tục nào.
    assert _detect(
        "https://dichvucong.bacninh.gov.vn/x",
        "Đơn đề nghị điều chỉnh quyết định giao đất cho hộ gia đình",
    ) == ""


def test_moi_entry_lao_cai_deu_khoa_dung_host():
    for key in (_KEY, "dieu-chinh-quyet-dinh-giao-dat-lao-cai"):
        entry = next(p for p in public_list() if p["key"] == key)
        assert entry["detect"]["urlScope"] == ["dichvucong.laocai.gov.vn"], key
        assert entry["label"].startswith("[Tỉnh Lào Cai]"), key
