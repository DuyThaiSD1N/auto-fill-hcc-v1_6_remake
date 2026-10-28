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
        _CHU_HO_SO_TO_CHUC + [{"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"}],
        # Khối chủ hồ sơ không phụ thuộc người đi nộp, nhưng vẫn truyền mốc tài khoản để không lẫn với
        # cảnh báo "chưa xác định được người đang đi nộp" (xem test_giao_thue_dat_lao_cai_nguoi_nop).
        {"formContext": {"applicantFullname": "NGUYỄN VĂN A", "applicantIdentityNumber": "012345678901"}},
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
    # 3 ô "giấy tờ khác" (10-12) + ô tổng hợp (13) KHÔNG đi bằng slotIndex nữa: chúng cần engine
    # otherListFile của FE để gõ tên tài liệu, nên planner không giữ hằng số slot cho chúng.
    assert not hasattr(planner, "_OTHER_SLOT_INDEX")


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

    by_file = {i["fileName"]: i for i in items}
    assert by_file["don.pdf"]["slotIndex"] == 0
    # Quyết định gốc + 2 bản điều chỉnh CÙNG một dòng (ô upload multiple).
    assert (by_file["qd_goc.pdf"]["slotIndex"] == by_file["qd_dc_1.pdf"]["slotIndex"]
            == by_file["qd_dc_2.pdf"]["slotIndex"] == 1)
    # ĐKKD không có dòng riêng → dòng "Giấy tờ khác" (target new để FE gõ được tên tài liệu).
    assert by_file["dkkd.pdf"]["target"] == "new"
    assert "slotIndex" not in by_file["dkkd.pdf"]
    assert any("không bỏ sót" in w for w in warnings)


def test_nhieu_tai_lieu_la_deu_thanh_dong_giay_to_khac_rieng():
    """FE tự bấm nút '+' thêm dòng nên không giới hạn 3 ô như bảng in sẵn."""
    items, _, _ = planner.build_plan_items(
        _files([f"la{i}.pdf" for i in range(6)]),
        {i: ("other", f"Văn bản số {i}") for i in range(6)},
    )

    assert all(i["target"] == "new" and i["needsAddComponent"] for i in items)
    assert len({i["documentName"] for i in items}) == 6


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


def test_giay_to_khac_phai_di_target_new_de_fe_dien_ten():
    """Chỉ engine otherListFile mới THÊM DÒNG + GÕ TÊN; fixed-slot thì tệp lên mà ô tên để trống."""
    items, _, _ = planner.build_plan_items(
        _files(["scan.pdf"]), {0: ("other", "QĐ 1678/QĐ-UBND điều chỉnh chủ trương đầu tư lần 2")}
    )

    item = items[0]
    assert item["target"] == "new"
    assert item["needsAddComponent"] is True
    assert "slotIndex" not in item
    # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại của hệ điều hành → cấm FE bấm.
    assert item["noChooserClick"] is True


def test_ten_tai_lieu_lay_tu_llm_va_giu_so_hieu_van_ban():
    """normalize_document_name của _shared cắt mất phần trước '/' — số hiệu là thứ phân biệt các QĐ."""
    items, _, _ = planner.build_plan_items(
        _files(["25528_QD_1678_dieu_chinh_chu_truong_dau_tu_lan_2_1787304693.pdf"]),
        {0: ("other", "QĐ 1678/QĐ-UBND điều chỉnh chủ trương đầu tư lần 2")},
    )
    name = items[0]["documentName"]

    assert "1678" in name
    assert name == items[0]["componentName"]  # FE gõ componentName vào ô tên
    # Không được lấy tên tệp (mất dấu + dính số của hệ thống upload).
    assert "1787304693" not in name
    assert "dieu_chinh" not in name


def test_hai_tai_lieu_trung_ten_thi_tach_ra():
    items, _, _ = planner.build_plan_items(
        _files(["a.pdf", "b.pdf"]),
        {0: ("other", "Quyết định chấp thuận điều chỉnh chủ trương đầu tư"),
         1: ("other", "Quyết định chấp thuận điều chỉnh chủ trương đầu tư")},
    )

    assert items[0]["documentName"] != items[1]["documentName"]
    assert items[1]["documentName"].endswith(" 2")


def test_llm_khong_dat_duoc_ten_thi_dung_ten_mac_dinh():
    items, _, _ = planner.build_plan_items(_files(["a.pdf"]), {0: ("other", "")})
    assert items[0]["documentName"] == "Tài liệu khác"


def test_tai_lieu_nhan_ra_loai_van_di_fixed_slot():
    items, _, _ = planner.build_plan_items(
        _files(["don.pdf"]), {0: ("don_mau_01", "Đơn đề nghị cho thuê đất")}
    )

    assert items[0]["target"] == "fixed-slot"
    assert items[0]["slotIndex"] == 0
    # Dòng có sẵn không có ô tên → giữ tên hiển thị cố định của dòng.
    assert items[0]["documentName"] == "Đơn đề nghị giao đất, cho thuê đất (Mẫu số 01)"


def test_canh_bao_tep_vuot_6mb():
    import base64

    big = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    _, warnings, _ = planner.build_plan_items(
        [{"name": "scan.pdf", "type": "application/pdf", "dataUrl": big}], {0: ("other", "Bản vẽ")}
    )

    assert any("6 MB" in w and "scan.pdf" in w for w in warnings)


def test_prompt_cam_chep_ten_tep():
    from app.pipelines.giao_thue_dat_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "documentName" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG chép tên tệp" in SYSTEM_PROMPT


# ── Phường Cam Đường: thủ tục đất đai Lào Cai luôn tách giấy tờ ─────────────────────────────────────────

import base64
import json

import fitz

from app.pipelines._shared import lao_cai_tach_giay_to as tach
from app.process.schemas import FileItem

_CAM_DUONG = {"tinh": "Tỉnh Lào Cai", "xa": "Phường Cam Đường"}


def _pdf_item(name: str, pages: int) -> FileItem:
    doc = fitz.open()
    for n in range(pages):
        doc.new_page().insert_text((72, 72), f"page {n + 1}")
    data = base64.b64encode(doc.tobytes()).decode("ascii")
    doc.close()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}", role="")


def _ocr_text(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {n + 1}/{len(pages)} ─────\n{p}" for n, p in enumerate(pages))


def _fake_stack(monkeypatch, texts: dict[str, str], starts: dict | None):
    """OCR theo tên tệp gốc (đếm số lượt) + LLM: lượt chia giấy trả `starts`, lượt phân loại đọc từ khoá."""
    from app.services import ocr
    from app.services.llm import client

    calls = {"ocr": []}

    async def fake_ocr(files, *, classify):
        calls["ocr"].append([f["name"] for f in files])
        return [{"name": f["name"], "type": f["type"], "text": texts.get(f["name"], ""), "provider": "tiengnoi"}
                for f in files]

    async def fake_chat(messages, max_tokens=None, enable_thinking=False, **_):
        if messages[0]["content"] == tach.SYSTEM_PROMPT:
            if starts is None:
                raise RuntimeError("LLM chết")
            return json.dumps(starts, ensure_ascii=False)
        text = messages[1]["content"]
        doc_type = ("don_mau_01" if "ĐƠN ĐỀ NGHỊ" in text
                    else "giay_to_mien_giam" if "MIỄN TIỀN" in text else "other")
        return json.dumps({"documents": [{"index": 0, "docType": doc_type, "documentName": "GCN đăng ký doanh nghiệp"}]},
                          ensure_ascii=False)

    monkeypatch.setattr(ocr, "_ocr_per_file", fake_ocr)
    monkeypatch.setattr(client, "chat", fake_chat)
    return calls


def test_cam_duong_dat_co_luon_tach_cho_thu_tuc_dat_dai():
    opts = tach.with_account_attach_options({}, _CAM_DUONG, _KEY)
    assert opts[tach.ALWAYS_SPLIT_OPTION] is True
    assert tach.always_split(opts)
    # Không có engine cắt trang (trợ lý bản cũ) → không tách.
    assert not tach.always_split({**opts, "supportsSourceSegments": False})


def test_cam_duong_khong_ap_cho_xa_khac_thu_tuc_khac_va_client_khong_tu_bat_duoc():
    assert tach.ALWAYS_SPLIT_OPTION not in tach.with_account_attach_options(
        {}, {"tinh": "Tỉnh Lào Cai", "xa": "Phường Yên Bái"}, _KEY)
    assert tach.ALWAYS_SPLIT_OPTION not in tach.with_account_attach_options(
        {tach.ALWAYS_SPLIT_OPTION: True}, {"tinh": "Tỉnh Lào Cai", "xa": "Xã Đơn Dương"}, _KEY)
    # Chủ trương đầu tư không phải thủ tục đất đai.
    assert tach.ALWAYS_SPLIT_OPTION not in tach.with_account_attach_options(
        {}, _CAM_DUONG, "chap-thuan-chu-truong-dau-tu-ubnd-tinh-lao-cai")


def test_moi_thu_tuc_dat_dai_cam_duong_deu_co_trong_registry_va_planner():
    from app.procedures.registry import get_attach_pipeline

    keys = {p["key"] for p in public_list()}
    assert tach.PROCEDURE_KEYS <= keys
    assert all(get_attach_pipeline(k) for k in tach.PROCEDURE_KEYS)


async def test_tep_gop_tach_tung_giay_vao_dung_dong_con_lai_vao_giay_to_khac(monkeypatch):
    texts = {"ho_so.pdf": _ocr_text([
        "ĐƠN ĐỀ NGHỊ GIAO ĐẤT, CHO THUÊ ĐẤT", "tiếp theo đơn, chữ ký",
        "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP", "QUYẾT ĐỊNH MIỄN TIỀN SỬ DỤNG ĐẤT",
    ])}
    starts = {"tep": [{"fileIndex": 0, "giayTo": [
        {"trangDau": 1, "ten": "Đơn đề nghị"}, {"trangDau": 3, "ten": "GCN đăng ký doanh nghiệp"},
        {"trangDau": 4, "ten": "Quyết định miễn tiền"}]}]}
    calls = _fake_stack(monkeypatch, texts, starts)

    result = await tach.plan_with_split(planner.plan, [_pdf_item("ho_so.pdf", 4)], {})

    # OCR tệp gốc đúng một lượt; planner dùng lại chữ của từng đoạn.
    assert calls["ocr"] == [["ho_so.pdf"]]
    items = result["attachments"]
    assert [(i.get("slotIndex"), i["target"]) for i in items] == [(0, "fixed-slot"), (None, "new"), (8, "fixed-slot")]
    assert [i["sourceSegments"] for i in items] == [
        [{"fileIndex": 0, "pageIndexes": [0, 1]}],
        [{"fileIndex": 0, "pageIndexes": [2]}],
        [{"fileIndex": 0, "pageIndexes": [3]}],
    ]
    assert all(i["fileIndex"] == 0 for i in items)
    assert items[1]["componentName"] == "GCN đăng ký doanh nghiệp"


async def test_giay_planner_bo_qua_van_vao_giay_to_khac(monkeypatch):
    texts = {"a.pdf": _ocr_text(["HỢP ĐỒNG CHUYỂN NHƯỢNG", "CĂN CƯỚC CÔNG DÂN"])}
    starts = {"tep": [{"fileIndex": 0, "giayTo": [{"trangDau": 1, "ten": "Hợp đồng chuyển nhượng"},
                                                  {"trangDau": 2, "ten": "CCCD Trần Thị B"}]}]}
    _fake_stack(monkeypatch, texts, starts)

    async def plan_chi_dinh_hop_dong(files, options=None, session=None):
        return {"attachments": [{"fileIndex": 0, "fileName": files[0].name, "target": "fixed-slot", "slotIndex": 2}],
                "errors": []}

    result = await tach.plan_with_split(plan_chi_dinh_hop_dong, [_pdf_item("a.pdf", 2)], {})

    extra = result["attachments"][1]
    assert extra["target"] == "new" and extra["needsAddComponent"] and extra["noChooserClick"]
    assert extra["componentName"] == "CCCD Trần Thị B"
    assert extra["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    assert any("Giấy tờ khác" in e for e in result["errors"])


async def test_mot_giay_hoac_llm_chia_loi_thi_dinh_nguyen_tep(monkeypatch):
    texts = {"don.pdf": _ocr_text(["ĐƠN ĐỀ NGHỊ GIAO ĐẤT", "trang 2"]), "anh.jpg": "QUYẾT ĐỊNH MIỄN TIỀN"}
    _fake_stack(monkeypatch, texts, None)
    files = [_pdf_item("don.pdf", 2), FileItem(name="anh.jpg", type="image/jpeg", dataUrl="data:image/jpeg;base64,AA", role="")]

    result = await tach.plan_with_split(planner.plan, files, {})

    items = result["attachments"]
    assert [(i["fileIndex"], i.get("slotIndex")) for i in items] == [(0, 0), (1, 8)]
    assert not any("sourceSegments" in i for i in items)
    assert any("đính nguyên tệp" in e for e in result["errors"])
