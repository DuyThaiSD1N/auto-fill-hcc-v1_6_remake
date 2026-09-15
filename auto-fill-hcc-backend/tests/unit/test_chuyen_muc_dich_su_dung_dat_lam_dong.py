"""Test [Tỉnh Lâm Đồng] "Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng
đất khi hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư" (1.116365).

Khoá 3 nhóm hợp đồng:
1. ĐÍNH KÈM (attp-row, bảng 24 dòng): quy tắc 3 MỤC của ảnh ánh xạ — Đơn+ủy quyền+CCCD vào CÙNG MỘT
   DÒNG của đúng mẫu đơn nhưng vẫn là các TỆP RIÊNG (không gộp PDF), trích lục → dòng 23, GCN → dòng
   22. Kèm test chống-va-chạm componentName chạy ĐÚNG thuật toán khớp dòng của extension trên cả 24
   dòng DOM thật, và test CAM KẾT không bỏ sót file ở mọi kịch bản hỏng.
2. PROCESS: tự nộp → bấm nút data[BUTTON3] và KHÔNG fill Phần III; nộp thay → fill 2 khối, không bấm.
3. Ô "Cơ quan/ tổ chức" chỉ dành cho pháp nhân.

KHÔNG chạy LLM live (môi trường test không có key): mọi test đính kèm inject sẵn llm_types.
"""

import re
import unicodedata

from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.attach import planner
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.attach.prompt import SYSTEM_PROMPT
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process import mapper
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process.prompt import EXTRA_RULES
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "chuyen-muc-dich-su-dung-dat-lam-dong"

# 24 dòng DOM thật, lấy VERBATIM từ cột "Tên giấy tờ" của 'chuyển mục đích đính kèm.html'.
_ROWS = [
    "Đơn, Mẫu số 4b Phụ lục VI ban hành kèm theo Quyết định số 40/2026/QĐ-UBND",
    "Văn bản của cơ quan có thẩm quyền cho phép thay đổi thời hạn hoạt động của dự án đầu tư theo quy "
    "định của pháp luật về đầu tư",
    "Một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, Giấy chứng nhận quyền sở hữu "
    "nhà ở và quyền sử dụng đất ở, Giấy chứng nhận quyền sở hữu nhà ở, Giấy chứng nhận quyền sở hữu "
    "công trình xây dựng, Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn "
    "liền với đất đã được cấp theo quy định của pháp luật về đất đai, pháp luật về nhà ở, pháp luật "
    "về xây dựng trước ngày Luật Đất đai có hiệu lực thi hành; Giấy chứng nhận quyền sử dụng đất, "
    "quyền sở hữu tài sản gắn liền với đất",
    "Đơn, Mẫu số 03 Phụ lục VI ban hành kèm theo Quyết định số 40/2026/QĐ-UBND",
    "Đơn theo Mẫu số 4a Phụ lục VI ban hành kèm theo Quyết định số 40/2026/QĐ-UBND",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai",
    "Quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất "
    "của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật đất đai qua các thời kỳ",
    "Văn bản của cơ quan có thẩm quyền cho phép gia hạn thời hạn hoạt động của dự án đầu tư hoặc thể "
    "hiện thời hạn hoạt động của dự án đầu tư theo quy định của pháp luật về đầu tư đối với trường "
    "hợp sử dụng đất để thực hiện dự án đầu tư",
    "Tờ khai lệ phí trước bạ",
    "Tờ khai thuế sử dụng đất phi nông nghiệp tương ứng với từng trường hợp theo quy định của pháp "
    "luật về quản lý thuế",
    "Giấy tờ có liên quan chứng minh thuộc diện được miễn, giảm tiền sử dụng đất theo quy định của "
    "pháp luật về người có công với cách mạng",
    "Quyết định hoặc văn bản theo quy định của pháp luật về miễn, giảm tiền sử dụng đất của Ủy ban "
    "nhân dân cấp tỉnh hoặc của cơ quan được Ủy ban nhân dân cấp tỉnh ủy quyền, phân cấp",
    "Giấy chứng nhận đầu tư hoặc Giấy phép đầu tư hoặc Giấy chứng nhận đăng ký đầu tư",
    "Xác nhận thông tin về cư trú hoặc Thông báo số định danh cá nhân và thông tin công dân trong Cơ "
    "sở dữ liệu quốc gia về dân cư",
    "Xác nhận của cơ quan có thẩm quyền về hộ nghèo",
    "Quyết định giao đất của cơ quan nhà nước có thẩm quyền",
    "Văn bản của cơ quan nhà nước có thẩm quyền về thực hiện dự án",
    "Văn bản đề nghị theo mẫu số 01/MGTH tại Phụ lục I ban hành kèm theo Thông tư số 80/2021/TT-BTC "
    "ngày 29/9/2021 của Bộ Tài chính",
    "Quyết định giao đất ở để bố trí tái định cư của cơ quan nhà nước có thẩm quyền",
    "Văn bản của cơ quan nhà nước có thẩm quyền phê duyệt về thực hiện dự án",
    "Đơn, Mẫu số 02 Phụ lục VI ban hành kèm theo Quyết định số 40/2026/QĐ-UBND; - TP-H36.000013",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc "
    "một trong các loại giấy tờ quy định tại Điều 137 Luật Đất đai hoặc quyết định giao đất, quyết "
    "định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm "
    "quyền theo quy định của pháp luật về đất đai qua các thời kỳ",
    "Bản trích lục bản đồ địa chính hoặc trích đo bản đồ địa chính",
    "Các giấy tờ đề nghị miễn, giảm tiền sử dụng đất, tiền thuê đất tại Phụ lục V ban hành kèm theo "
    "Quyết định số 40/2026/QĐ-UBND (nếu có)",
]

_ROW_DON_MAU_4B = 1
_ROW_THAY_DOI_THOI_HAN_DU_AN = 2
_ROW_DON_MAU_03 = 4
_ROW_DON_MAU_4A = 5
_ROW_QUYET_DINH_DAT = 7
_ROW_GIA_HAN_DU_AN = 8
_ROW_LE_PHI_TRUOC_BA = 9
_ROW_THUE_PHI_NONG_NGHIEP = 10
_ROW_GCN_DAU_TU = 13
_ROW_CU_TRU = 14
_ROW_DON_MAU_02 = 21
_ROW_GCN = 22
_ROW_TRICH_LUC = 23
_ROW_MIEN_GIAM = 24


def _fold(value: str) -> str:
    """Bản rút gọn của foldChoiceText trong content.js: bỏ dấu, đ→d, gộp khoảng trắng, lowercase."""
    text = unicodedata.normalize("NFD", value)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    text = re.sub(r"[–—]", "-", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _row_matches(row_text: str, component_name: str) -> bool:
    """componentTextMatches() của content.js — khớp HAI CHIỀU (dòng chứa tên, hoặc tên chứa dòng)."""
    row = _fold(row_text)
    want = _fold(component_name)
    if not row or not want:
        return False
    return row == want or want in row or row in want


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _ocr(files: list[dict]) -> list[dict]:
    return [{"name": item["name"], "text": "ocr"} for item in files]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — quy tắc 3 MỤC của ảnh ánh xạ
# --------------------------------------------------------------------------------------
def test_muc_1_don_uy_quyen_cccd_cung_mot_dong_nhung_van_la_tep_rieng():
    """MỤC 1: Đơn + Giấy ủy quyền + CCCD vào CÙNG dòng 21 — KHÔNG gộp PDF (ô upload là multiple)."""
    files = _files(["cccd.pdf", "uy-quyen.pdf", "don-cmd.pdf"])
    llm_types = {0: "cccd", 1: "uy_quyen", 2: "don_chuyen_muc_dich"}

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    # 3 item riêng = 3 TỆP riêng, cùng một dòng.
    assert len(attachments) == 3
    assert all(item["componentIndex"] == _ROW_DON_MAU_02 for item in attachments)
    assert all(item["target"] == "attp-row" for item in attachments)
    # TUYỆT ĐỐI không gộp PDF: sourceFileIndexes sẽ khiến popup merge 3 tệp thành 1.
    assert all("sourceFileIndexes" not in item for item in attachments)
    # Thứ tự đính giữ đúng thứ tự đọc của ảnh ánh xạ, KHÔNG theo thứ tự người dùng tải lên.
    assert [item["fileIndex"] for item in attachments] == [2, 1, 0]
    assert [item["documentName"] for item in attachments] == [
        "Đơn đề nghị chuyển mục đích sử dụng đất",
        "Giấy ủy quyền",
        "Căn cước công dân",
    ]


def test_hai_tep_cccd_duoc_danh_so_de_khong_trung_ten():
    """documentName trở thành TÊN TỆP ở FE → 2 tệp CCCD cùng ô phải khác tên, nếu không bộ chống-trùng
    của extension sẽ bỏ qua tệp thứ hai."""
    files = _files(["don-cmd.pdf", "cccd-1.pdf", "cccd-2.pdf"])
    llm_types = {0: "don_chuyen_muc_dich", 1: "cccd", 2: "cccd"}

    attachments, _, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    names = [item["documentName"] for item in attachments]
    assert names == ["Đơn đề nghị chuyển mục đích sử dụng đất", "Căn cước công dân (1)", "Căn cước công dân (2)"]
    assert len(set(names)) == len(names)


def test_muc_2_va_muc_3_di_dong_rieng():
    """MỤC 2 (trích lục) → dòng 23; MỤC 3 (GCN) → dòng 22; KHÔNG gộp vào PDF của đơn."""
    files = _files(["don-cmd.pdf", "gcn.pdf", "trich-luc.pdf"])
    llm_types = {0: "don_chuyen_muc_dich", 1: "giay_chung_nhan", 2: "trich_luc_ban_do"}

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    by_index = {item["componentIndex"]: item for item in attachments}
    assert set(by_index) == {_ROW_DON_MAU_02, _ROW_GCN, _ROW_TRICH_LUC}
    assert by_index[_ROW_GCN]["fileIndex"] == 1
    assert by_index[_ROW_TRICH_LUC]["fileIndex"] == 2
    assert by_index[_ROW_DON_MAU_02]["fileIndex"] == 0
    # Không gộp PDF ở bất kỳ mục nào.
    assert all("sourceFileIndexes" not in item for item in attachments)


def test_bon_mau_don_route_dung_dong_cua_no():
    """Bốn biến thể của thủ tục: Mẫu 02→21, Mẫu 03→4, Mẫu 4a→5, Mẫu 4b→1."""
    expected = {
        "don_chuyen_muc_dich": _ROW_DON_MAU_02,
        "don_chuyen_hinh_thuc": _ROW_DON_MAU_03,
        "don_gia_han": _ROW_DON_MAU_4A,
        "don_dieu_chinh_thoi_han": _ROW_DON_MAU_4B,
    }
    for doc_type, row_index in expected.items():
        files = _files([f"{doc_type}.pdf"])
        attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), {0: doc_type})
        assert warnings == []
        assert len(attachments) == 1
        assert attachments[0]["componentIndex"] == row_index, doc_type


def test_moi_docType_phu_tro_co_dong_rieng():
    """Các giấy tờ 'nếu có' đều trỏ đúng dòng STT 1-based của bảng 24 dòng."""
    expected = {
        "xac_nhan_cu_tru": _ROW_CU_TRU,
        "to_khai_le_phi_truoc_ba": _ROW_LE_PHI_TRUOC_BA,
        "to_khai_thue_phi_nong_nghiep": _ROW_THUE_PHI_NONG_NGHIEP,
        "van_ban_thay_doi_thoi_han_du_an": _ROW_THAY_DOI_THOI_HAN_DU_AN,
        "van_ban_gia_han_du_an": _ROW_GIA_HAN_DU_AN,
        "quyet_dinh_dat_qua_cac_thoi_ky": _ROW_QUYET_DINH_DAT,
        "giay_chung_nhan_dau_tu": _ROW_GCN_DAU_TU,
        "giay_to_mien_giam": _ROW_MIEN_GIAM,
    }
    files = _files([f"{name}.pdf" for name in expected])
    llm_types = dict(enumerate(expected))

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    assert {item["detectedType"]: item["componentIndex"] for item in attachments} == expected
    assert len(attachments) == len(expected)
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # Mỗi dòng của cổng đã ghi cứng "1 Bản chính"/"1 Bản sao" (không có radio) → không set loaiBan.
    assert all("loaiBan" not in item for item in attachments)


def test_moi_componentName_chi_khop_dung_mot_dong():
    """CHỐNG VA CHẠM: chạy đúng thuật toán khớp dòng của extension trên cả 24 dòng DOM thật.

    Bẫy có thật trên bảng này: dòng 6 là TIỀN TỐ của dòng 22, dòng 7 gần trùng đuôi dòng 22 — mà FE
    khớp HAI CHIỀU nên một chuỗi hớ hênh sẽ trỏ nhầm dòng.
    """
    routes = {route["index"]: route["name"] for route in planner._DON_ROUTES.values()}
    routes.update({route["index"]: route["name"] for route in planner._ROUTES.values()})

    for row_index, component_name in sorted(routes.items()):
        hits = [i + 1 for i, row in enumerate(_ROWS) if _row_matches(row, component_name)]
        assert hits == [row_index], f"componentName của dòng {row_index} khớp {hits}"


def test_file_la_duoc_xep_tai_lieu_khac_va_dinh_vao_dong_don():
    """File không nhận ra loại: xếp 'Tài liệu khác', đính vào dòng Đơn, giữ tên gốc + cảnh báo."""
    files = _files(["don-cmd.pdf", "giay-la.pdf"])
    llm_types = {0: "don_chuyen_muc_dich", 1: "other"}

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), llm_types)

    assert len(attachments) == 2
    other = attachments[-1]
    assert other["fileIndex"] == 1
    assert other["componentIndex"] == _ROW_DON_MAU_02
    assert other["detectedType"] == "other"
    assert other["documentName"] == "Tài liệu khác - giay-la.pdf"
    assert "sourceFileIndexes" not in other
    assert any("giay-la.pdf" in w for w in warnings)
    assert classified[-1]["docType"] == "other"


def test_tuyet_doi_khong_miss_file_o_moi_kich_ban_hong():
    """CAM KẾT: mọi file tải lên LUÔN có ít nhất một plan item, kể cả khi LLM im lặng/trả loại lạ/
    OCR rỗng (file .docx, ảnh mờ...). Không bao giờ được rơi file."""
    files = _files([
        "don-cmd.pdf", "gcn.pdf", "khong-ocr-duoc.docx", "anh-mo.png", "loai-la.pdf", "trong-rong.pdf",
    ])
    scenarios = {
        "LLM im lặng hoàn toàn (lỗi/hết quota)": {},
        "LLM chỉ trả một phần": {0: "don_chuyen_muc_dich", 1: "giay_chung_nhan"},
        "LLM trả loại KHÔNG có trong allowed_types": {
            0: "don_chuyen_muc_dich", 1: "giay_chung_nhan", 2: "so_ho_khau", 3: "", 4: "khong_biet", 5: "other",
        },
        "LLM lệch index (trả thừa index không tồn tại)": {0: "don_chuyen_muc_dich", 99: "giay_chung_nhan"},
    }

    for label, llm_types in scenarios.items():
        attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)
        planned = {item["fileIndex"] for item in attachments}
        assert planned == set(range(len(files))), f"{label}: rơi file {set(range(len(files))) - planned}"
        # File không rõ loại phải nằm ở dòng Đơn và được cảnh báo cho cán bộ.
        for item in attachments:
            if item["detectedType"] == "other":
                assert item["componentIndex"] == _ROW_DON_MAU_02, label
                assert item["documentName"].startswith("Tài liệu khác - "), label
                assert any(item["fileName"] in w for w in warnings), label


def test_plan_end_to_end_khong_bo_sot_file_kieu_la_va_khi_llm_loi():
    """Chạy cả hàm plan(): file KHÔNG thuộc loại OCR được (.docx/.zip) không bao giờ tới LLM, và LLM
    thì ném lỗi — vẫn phải ra kế hoạch đủ 3/3 file."""
    import asyncio

    from app.process.schemas import FileItem
    from app.services import ocr as ocr_service

    files = [
        FileItem(name="don-cmd.pdf", role="other", type="application/pdf", dataUrl="data:application/pdf;base64,AA=="),
        FileItem(name="phu-luc.docx", role="other", type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 dataUrl="data:application/octet-stream;base64,AA=="),
        FileItem(name="ho-so.zip", role="other", type="application/zip", dataUrl="data:application/zip;base64,AA=="),
    ]

    async def fake_ocr(items):
        return [{"name": item["name"], "text": "ocr"} for item in items]

    async def fake_chat(*args, **kwargs):
        raise RuntimeError("LLM down")

    original_ocr, original_chat = ocr_service.ocr_per_file, planner.client.chat
    ocr_service.ocr_per_file, planner.client.chat = fake_ocr, fake_chat
    try:
        result = asyncio.run(planner.plan(files))
    finally:
        ocr_service.ocr_per_file, planner.client.chat = original_ocr, original_chat

    assert {item["fileIndex"] for item in result["attachments"]} == {0, 1, 2}
    assert all(item["componentIndex"] == _ROW_DON_MAU_02 for item in result["attachments"])
    assert any("LLM down" in err for err in result["errors"])


def test_khong_co_giay_to_nao_nhan_dien_duoc_van_dinh_du_vao_dong_don_chinh():
    """Cực đoan: KHÔNG file nào nhận ra loại → tất cả về dòng Đơn Mẫu 02, không file nào bị bỏ."""
    files = _files(["a.pdf", "b.pdf", "c.pdf"])

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), {})

    assert len(attachments) == 3
    assert all(item["componentIndex"] == _ROW_DON_MAU_02 for item in attachments)
    assert len(warnings) == 3


def test_khong_co_don_van_dinh_uy_quyen_cccd_vao_dong_don_chinh():
    """Thiếu Đơn → ủy quyền/CCCD vẫn vào dòng Đơn Mẫu 02 (dòng chính của thủ tục) + cảnh báo."""
    files = _files(["uy-quyen.pdf", "cccd.pdf"])
    llm_types = {0: "uy_quyen", 1: "cccd"}

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert len(attachments) == 2
    assert all(item["componentIndex"] == _ROW_DON_MAU_02 for item in attachments)
    assert any("Không nhận ra Đơn đề nghị" in w for w in warnings)


def test_don_thu_hai_di_dong_rieng_uy_quyen_cccd_neo_theo_don_dau():
    """Hồ sơ xin nhiều nội dung: mỗi đơn về dòng của chính nó; ủy quyền/CCCD neo theo đơn ĐẦU TIÊN."""
    files = _files(["don-cmd.pdf", "don-gia-han.pdf", "cccd.pdf"])
    llm_types = {0: "don_chuyen_muc_dich", 1: "don_gia_han", 2: "cccd"}

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    rows = {item["fileIndex"]: item["componentIndex"] for item in attachments}
    assert rows == {0: _ROW_DON_MAU_02, 1: _ROW_DON_MAU_4A, 2: _ROW_DON_MAU_02}
    # Mỗi file chỉ sinh ĐÚNG một item — không đính trùng file sang hai dòng.
    assert len(attachments) == 3


# --------------------------------------------------------------------------------------
# PROCESS — hai vai trò và nút "Người nộp là chủ hồ sơ"
# --------------------------------------------------------------------------------------
def _owner_facts() -> list[dict]:
    return [
        {"name": "Nguoi_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Nguoi_NgaySinh", "value": "24/10/1975"},
        {"name": "Nguoi_GioiTinh", "value": "Nam"},
        {"name": "Nguoi_SoDinhDanh", "value": "000000000001"},
        {"name": "Nguoi_NgayCapCccd", "value": "01/02/2021"},
        {"name": "Nguoi_NoiCapCccd", "value": "Bộ Công an"},
        {"name": "Nguoi_DienThoai", "value": "0900000001"},
        {"name": "Nguoi_ThuongTru", "value": {"tinh": "Lâm Đồng", "xa": "Phường Lâm Viên - Đà Lạt", "diaChi": "16 Số Nhà"}},
    ]


def test_tu_nop_bam_nut_nguoi_nop_la_chu_ho_so():
    """Người nộp = chủ hồ sơ → điền Phần I + phát data[BUTTON3]; KHÔNG fill tay Phần III."""
    fields, warnings = mapper.enrich(_owner_facts())
    values = _values(fields)

    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "000000000001"
    assert values["data[BUTTON3]"] is True
    # Nút sẽ tự chép xuống Phần III → không được phát thêm ô nào của khối chủ hồ sơ (kể cả dom-expect).
    owner_fields = [name for name in values if name.startswith("data[owner")] + [
        name for name in values if name in {"data[gender1]", "data[nation1]", "data[province1]", "data[district1]"}
    ]
    assert owner_fields == []
    # Fixture không có Giấy chứng nhận → chỉ còn đúng cảnh báo thiếu Phần IV, không cảnh báo về người.
    assert warnings == ["Chưa đọc được số phát hành/ngày cấp Giấy chứng nhận đã cấp (Phần IV)."]


def test_nop_thay_dien_ca_hai_khoi_va_khong_bam_nut():
    """Có ủy quyền → Phần I là người được ủy quyền, Phần III là chủ hồ sơ, KHÔNG phát data[BUTTON3]."""
    fields = _owner_facts() + [
        {"name": "NguoiDuocUyQuyen", "value": {
            "hoTen": "TRẦN VĂN B",
            "ngaySinh": "13/09/1995",
            "gioiTinh": "Nam",
            "soDinhDanh": "000000000002",
            "ngayCapCccd": "05/06/2022",
            "noiCapCccd": "Bộ Công an",
            "thuongTru": {"tinh": "Lâm Đồng", "xa": "Xã D'Ran", "diaChi": "Tổ dân phố X"},
        }},
    ]

    values = _values(mapper.enrich(fields)[0])

    assert "data[BUTTON3]" not in values
    assert values["data[fullname]"] == "TRẦN VĂN B"
    assert values["data[identityNumber]"] == "000000000002"
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[ownerIdentityNumber]"] == "000000000001"
    # SĐT ghi trong Đơn là của CHỦ HỒ SƠ — không được mượn sang ô của người nộp.
    assert values["data[ownerPhoneNumber]"] == "0900000001"
    assert values["data[phoneNumber]"] == ""
    # Hai khối địa chỉ không lẫn nhau.
    assert values["data[district]"] != values["data[district1]"]


def test_ghi_chu_ghi_noi_dung_de_nghi_va_thua_dat():
    fields = _owner_facts() + [
        {"name": "Don_NoiDungDeNghi", "value": "Đề nghị chuyển mục đích sử dụng đất sang đất ở đô thị"},
        {"name": "ThuaDat_So", "value": "82"},
        {"name": "ThuaDat_ToBanDo", "value": "51"},
    ]

    ghi_chu = _values(mapper.enrich(fields)[0])["data[ghiChu]"]

    assert "chuyển mục đích sử dụng đất" in ghi_chu
    assert "Thửa đất số 82, tờ bản đồ số 51." in ghi_chu


def test_ca_nhan_khong_dien_o_co_quan_to_chuc():
    """Hồ sơ cá nhân: 'Cơ quan/ tổ chức' để TRỐNG — không lấy họ tên người dân làm tên tổ chức."""
    values = _values(mapper.enrich(_owner_facts())[0])

    assert "data[organization]" not in values


def test_phap_nhan_dien_o_co_quan_to_chuc_tu_nguon_rieng():
    fields = _owner_facts() + [{"name": "ToChuc_Ten", "value": "Công ty TNHH Mẫu"}]

    values = _values(mapper.enrich(fields)[0])

    assert values["data[organization]"] == "Công ty TNHH Mẫu"


def test_phan_iv_gcn_dung_dinh_dang_flatpickr_va_lau_dai_de_trong():
    fields = _owner_facts() + [
        {"name": "Gcn_SoPhatHanh", "value": "AA 07874787 (số vào sổ CN001884)"},
        {"name": "Gcn_NgayCap", "value": "27/05/2026"},
        {"name": "Gcn_DonViCap", "value": "KT. GIÁM ĐỐC Chi nhánh Văn phòng đăng ký đất đai khu vực X"},
        {"name": "Gcn_NoiCap", "value": "Phường Lâm Viên - Đà Lạt"},
        {"name": "Gcn_ThoiHan", "value": "Lâu dài"},
    ]

    values = _values(mapper.enrich(fields)[0])

    assert values["data[licenseCode]"] == "AA 07874787"
    # Ô ngày Phần IV dùng flatpickr yyyy/mm/dd, KHÁC các ô người dd/MM/yyyy.
    assert values["data[licenseDate]"] == "2026/05/27"
    assert values["data[effectiveDate]"] == "2026/05/27"
    # "Lâu dài" → không có ngày hết hạn.
    assert "data[expirationDate]" not in values
    assert values["data[licensingPlace]"].startswith("Chi nhánh Văn phòng đăng ký đất đai")


def test_nhan_tinh_thanh_dung_loai_don_vi_ke_ca_khi_in_dinh_tien_to():
    """Bẫy thật trên CCCD/GCN: 'TP.Hồ Chí Minh' in DÍNH tiền tố → nhãn phải là 'Thành phố Hồ Chí
    Minh', không phải 'Tỉnh TP.Hồ Chí Minh' (select Choices.js khớp theo đúng chuỗi nhãn)."""
    assert mapper._province("TP.Hồ Chí Minh") == "Thành phố Hồ Chí Minh"
    assert mapper._province("tp.Đà Nẵng") == "Thành phố Đà Nẵng"
    assert mapper._province("Lâm Đồng") == "Tỉnh Lâm Đồng"
    assert mapper._province("Tỉnh Lâm Đồng") == "Tỉnh Lâm Đồng"
    assert mapper._province("Tây Ninh") == "Tỉnh Tây Ninh"


def test_thua_dat_va_noi_o_khong_lan_nhau():
    fields = _owner_facts() + [
        {"name": "ThuaDat_DiaChi", "value": {"tinh": "Lâm Đồng", "xa": "Xã D'Ran"}},
    ]

    values = _values(mapper.enrich(fields)[0])

    assert values["data[village2]"] == "Xã D'Ran"
    assert values["data[district]"] == "Phường Lâm Viên - Đà Lạt"


# --------------------------------------------------------------------------------------
# HỢP ĐỒNG SCHEMA / REGISTRY
# --------------------------------------------------------------------------------------
def test_ui_field_set_khop_form_35_o():
    """35 ô data[...] đọc từ 'chuyển mục đichs fill.html' — không thiếu, không thừa."""
    assert len(UI_COMP_BY_NAME) == 35
    assert UI_COMP_BY_NAME["data[BUTTON3]"] == "dom-owner-copy"
    assert UI_COMP_BY_NAME["data[organization]"] == "dom-input"
    for name in ("data[licenseDate]", "data[effectiveDate]", "data[expirationDate]"):
        assert UI_COMP_BY_NAME[name] == "dom-date"


def test_mapper_khong_phat_o_ngoai_form():
    fields = _owner_facts() + [{"name": "ToChuc_Ten", "value": "Công ty TNHH Mẫu"}]
    for item in mapper.enrich(fields)[0]:
        assert item["name"] in UI_COMP_BY_NAME


def test_prompt_cam_lay_ten_nguoi_dan_lam_ten_to_chuc():
    to_chuc = next(f for f in FIELDS if f["name"] == "ToChuc_Ten")
    assert "PHÁP NHÂN" in to_chuc["desc"]
    assert "KHÔNG lấy họ tên người dân" in to_chuc["desc"]
    assert "PHÁP NHÂN" in EXTRA_RULES
    assert "Không bịa thông tin còn thiếu" in EXTRA_RULES


def test_prompt_dinh_kem_khai_du_bon_mau_don():
    for doc_type in ("don_chuyen_muc_dich", "don_chuyen_hinh_thuc", "don_gia_han", "don_dieu_chinh_thoi_han"):
        assert doc_type in SYSTEM_PROMPT


def test_prompt_bat_llm_tra_du_moi_index_va_uu_tien_other_khi_khong_chac():
    assert "không bỏ sót index nào" in SYSTEM_PROMPT
    assert 'Thà trả "other" còn hơn đoán bừa' in SYSTEM_PROMPT


def test_registry_wiring():
    procedure = get_procedure(_KEY)
    assert procedure is not None
    assert procedure["hasAttachmentStep"] is True
    assert procedure["mode"] == "agent"
    assert procedure["detect"]["urlScope"] == ["lamdong.gov.vn"]
    assert "1.116365" in procedure["detect"]["textIncludes"]
    assert get_pipeline(_KEY) is not None
    assert get_attach_pipeline(_KEY) is not None
