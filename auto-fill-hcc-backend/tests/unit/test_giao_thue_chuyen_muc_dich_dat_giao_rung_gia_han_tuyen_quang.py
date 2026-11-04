import asyncio
import base64
import re
from types import SimpleNamespace

import fitz

from app.pipelines._shared import fold
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang import attach
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.attach import planner as dispatcher
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.attach.dinh_kem_khong_tach import planner
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.attach.dinh_kem_khong_tach.prompt import (
    SYSTEM_PROMPT,
)
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.attach.dinh_kem_tach import planner as tach
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as TACH_PROMPT,
)
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.process import mapper
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.process_vbdlis import (
    mapper as vbdlis_mapper,
)
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.process_vbdlis.schema import (
    UI_COMP_BY_NAME as VBDLIS_UI,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "giao-thue-chuyen-muc-dich-dat-giao-rung-gia-han-tuyen-quang"
_VBDLIS_KEY = "giao-thue-chuyen-muc-dich-dat-giao-rung-gia-han-tuyen-quang-vbdlis"

# Cột "Tên giấy tờ" của 14 dòng thành phần hồ sơ trên cổng Tuyên Quang, đúng thứ tự DOM (file mapping).
_ROWS = [
    "Bản sao văn bản phê duyệt kết quả lựa chọn nhà đầu tư của cơ quan nhà nước có thẩm quyền đối với trường "
    "hợp quy định tại khoản 2 Điều 116 Luật Đất đai.",
    "Đơn theo Mẫu số 01",
    "Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư, quyết định chấp thuận "
    "chủ trương đầu tư đồng thời chấp thuận nhà đầu tư theo quy định của pháp luật về đầu tư công, pháp luật "
    "về đầu tư; văn bản phê duyệt kết quả lựa chọn nhà đầu tư đối với dự án đầu tư theo phương thức đối tác "
    "công tư (nếu có).",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc một trong "
    "các loại giấy tờ quy định tại Điều 137 Luật Đất đai hoặc quyết định giao đất, quyết định cho thuê đất, "
    "quyết định cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của "
    "pháp luật về đất đai qua các thời kỳ.",
    "Phương án sử dụng tầng đất mặt theo Mẫu số 26 ban hành kèm theo Nghị định số 151/2025/NĐ-CP (đối với "
    "trường hợp chuyển mục đích sử dụng đất chuyên trồng lúa).",
    "Dự án đầu tư đối với khu rừng đề nghị giao; báo cáo điều tra, đánh giá hiện trạng rừng và bản đồ hiện "
    "trạng rừng theo quy định của pháp luật về lâm nghiệp (đối với trường hợp đề nghị giao đất và giao rừng);",
    "Kết quả đấu giá thuê rừng; biên bản đấu giá cho thuê rừng; danh sách người trúng đấu giá thuê rừng; "
    "thông báo hoàn thành nghĩa vụ tài chính đối với người trúng đấu giá thuê rừng (đối với trường hợp cho "
    "thuê đất và cho thuê rừng).",
    "Một trong các loại giấy tờ sau: + Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ "
    "trương đầu tư, quyết định chấp thuận chủ trương đầu tư đồng thời chấp thuận nhà đầu tư theo quy định của "
    "pháp luật về đầu tư công, pháp luật về đầu tư; văn bản phê duyệt kết quả lựa chọn nhà đầu tư đối với dự "
    "án đầu tư theo phương thức đối tác công tư (nếu có); + Bản sao văn bản của cơ quan nhà nước có thẩm "
    "quyền chấp thuận nhà đầu tư theo quy định của pháp luật về đầu tư đối với trường hợp quy định tại khoản "
    "5 Điều 124 Luật Đất đai; + Bản sao văn bản của đơn vị được giao tổ chức thực hiện việc đấu giá quyền sử "
    "dụng đất về kết quả đấu giá quyền sử dụng đất không thành quy định tại điểm b khoản 6 Điều 125 Luật Đất "
    "đai; + Bản sao văn bản về kết quả thực hiện việc nhận chuyển nhượng dự án bất động sản theo quy định của "
    "pháp luật về kinh doanh bất động sản đối với trường hợp quy định tại khoản 7 Điều 124 Luật Đất đai; + "
    "Bản sao các văn bản theo quy định của pháp luật đối với trường hợp quy định tại điểm i khoản 1 Điều 133 "
    "Luật Đất đai mà phải thu hồi đất.",
    "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương đã được cơ quan, tổ chức có "
    "thẩm quyền phê duyệt",
    "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích đất thu "
    "hồi của công ty nông, lâm nghiệp quản lý, sử dụng để giao đất, cho thuê đất quy định tại các điểm c, d "
    "và đ khoản 2 Điều 181 Luật Đất đai;",
    "Một trong các loại giấy tờ sau: + Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ "
    "trương đầu tư, quyết định chấp thuận chủ trương đầu tư đồng thời chấp thuận nhà đầu tư theo quy định của "
    "pháp luật về đầu tư công, pháp luật về đầu tư; văn bản phê duyệt kết quả lựa chọn nhà đầu tư đối với dự "
    "án đầu tư theo phương thức đối tác công tư (nếu có); + Bản sao văn bản của cơ quan nhà nước có thẩm "
    "quyền chấp thuận nhà đầu tư theo quy định của pháp luật về đầu tư đối với trường hợp quy định tại khoản "
    "5 Điều 124 Luật Đất đai; + Bản sao văn bản của đơn vị được giao tổ chức thực hiện việc đấu giá quyền sử "
    "dụng đất về kết quả đấu giá quyền sử dụng đất không thành quy định tại điểm b khoản 6 Điều 125 Luật Đất "
    "đai; + Bản sao văn bản về kết quả thực hiện việc nhận chuyển nhượng dự án bất động sản theo quy định của "
    "pháp luật về kinh doanh bất động sản đối với trường hợp quy định tại khoản 7 Điều 124 Luật Đất đai; + "
    "Bản sao các văn bản theo quy định của pháp luật đối với trường hợp quy định tại điểm i khoản 1 Điều 133 "
    "Luật Đất đai mà phải thu hồi đất.",
    "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh tế, "
    "đơn vị sự nghiệp công lập đã được Nhà nước giao đất, cho thuê đất trước ngày Luật Đất đai có hiệu lực "
    "thi hành;",
    "Một trong các giấy tờ sau: + Bản sao một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, "
    "quyền sở hữu tài sản gắn liền với đất, Giấy chứng nhận quyền sử dụng đất, Giấy chứng nhận quyền sở hữu "
    "nhà ở và quyền sử dụng đất ở, Giấy chứng nhận quyền sở hữu nhà ở, Giấy chứng nhận quyền sở hữu công "
    "trình xây dựng, Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất "
    "đã được cấp theo quy định của pháp luật về đất đai, pháp luật về nhà ở, pháp luật về xây dựng trước ngày "
    "Luật này có hiệu lực thi hành vẫn có giá trị pháp lý và không phải cấp đổi sang Giấy chứng nhận quyền sử "
    "dụng đất, quyền sở hữu tài sản gắn liền với đất. + Quyết định giao đất, quyết định cho thuê đất, quyết "
    "định cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật "
    "về đất đai qua các thời kỳ. + Văn bản của cơ quan có thẩm quyền cho phép gia hạn thời hạn hoạt động của "
    "dự án đầu tư hoặc thể hiện thời hạn hoạt động của dự án đầu tư theo quy định của pháp luật về đầu tư đối "
    "với trường hợp sử dụng đất để thực hiện dự án đầu tư.",
    "Đơn theo Mẫu số 04",
]


def _fe_fold(value: str) -> str:
    """Như foldChoiceText của FE: bỏ dấu, gộp mọi dấu gạch cùng khoảng trắng quanh nó thành một khoảng trắng."""
    return re.sub(r"\s+", " ", re.sub(r"\s*[-–—]+\s*", " ", fold(value))).strip()


def _fe_matches(row_text: str, name: str) -> bool:
    row, want = _fe_fold(row_text), _fe_fold(name)
    return row == want or want in row or row in want


def _fe_find_row(name: str, index: int) -> int | None:
    """Như findAttachmentRowByComponent của FE: dòng theo STT trước, không khớp tên mới dò dòng khớp đầu tiên."""
    if 1 <= index <= len(_ROWS) and _fe_matches(_ROWS[index - 1], name):
        return index
    return next((stt for stt, row in enumerate(_ROWS, start=1) if _fe_matches(row, name)), None)


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _facts(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields if not item.get("clear")}


def _cleared(fields: list[dict]) -> set[str]:
    """Ô gửi cờ clear: extension xoá trắng giá trị cổng điền sẵn và tô đỏ cho cán bộ nhập tay."""
    cleared = {item["name"] for item in fields if item.get("clear")}
    assert all(item["value"] == "" and item.get("markEmpty") for item in fields if item.get("clear"))
    return cleared


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — KHÔNG TÁCH
# --------------------------------------------------------------------------------------
def test_sample_three_files_follow_attachment_mapping():
    """Ánh xạ hồ sơ: Đơn -> dòng 2, giấy ủy quyền -> dòng 2 chung với Đơn, Giấy chứng nhận -> dòng 4, Bản chính."""
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf", "uq.pdf"]), None,
        {0: ["don_de_nghi"], 1: ["gcn"], 2: ["authorization"]},
    )
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [(0, 2), (1, 4), (2, 2)]
    assert {item["loaiBan"] for item in attachments} == {"Bản chính"}
    assert [item["documentName"] for item in attachments] == [
        "Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 01)",
        "Giấy chứng nhận quyền sử dụng đất", "Giấy ủy quyền"]
    assert warnings == []


def test_bundle_goes_whole_once_to_don_row():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["ho-so.pdf"]), None, {0: ["authorization", "gcn", "don_de_nghi", "identity"]},
    )
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [(2, "ho-so.pdf")]
    assert len(warnings) == 1 and "dòng 2" in warnings[0] and "dòng 4" in warnings[0]


def test_gia_han_dossier_uses_rows_13_and_14():
    attachments, _warnings, _classified = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf", "uq.pdf", "la.pdf"]), None,
        {0: ["don_gia_han"], 1: ["gcn"], 2: ["authorization"], 3: ["other"]},
    )
    assert [item["componentIndex"] for item in attachments] == [14, 13, 14, 14]


def test_project_documents_go_to_their_own_rows():
    types = ["ket_qua_lua_chon_nha_dau_tu", "van_ban_phe_duyet_du_an", "phuong_an_tang_dat_mat", "du_an_giao_rung",
             "dau_gia_thue_rung", "giay_to_dau_tu_tong_hop", "phuong_an_cong_ty_nong_lam", "phuong_an_dat_thu_hoi",
             "phuong_an_to_chuc_kinh_te"]
    attachments, warnings, _classified = planner.build_plan_items(
        _files([f"{index}.pdf" for index in range(len(types))]), None, dict(enumerate([[t] for t in types])),
    )
    assert [item["componentIndex"] for item in attachments] == [1, 3, 5, 6, 7, 8, 9, 10, 12]
    assert warnings == []


def test_unknown_goes_to_don_row_with_original_name():
    attachments, warnings, classified = planner.build_plan_items(_files(["la.pdf", "trong.pdf"]), None, {0: "abc"})
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [(2, "la.pdf"), (2, "trong.pdf")]
    assert len(warnings) == 2
    assert [item["source"] for item in classified] == ["llm", "unknown"]


def test_component_names_resolve_to_their_own_row_on_fe():
    for row, name in planner._ROWS.items():
        assert _fe_find_row(name, row) == row, row
    assert 11 not in planner._ROWS  # dòng 11 trùng dòng 8
    assert len({_fe_fold(name) for name in planner._ROWS.values()}) == len(planner._ROWS)
    # Dòng 8 chứa nguyên câu của dòng 3: chỉ STT giữ giấy phê duyệt dự án ở dòng 3.
    assert _fe_matches(_ROWS[7], planner._ROWS[3])


def test_attach_prompts_list_every_type():
    for doc_type in list(planner._ROUTES) + ["other"]:
        assert doc_type in SYSTEM_PROMPT and doc_type in TACH_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT and '"trangDau"' in TACH_PROMPT


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — TÁCH
# --------------------------------------------------------------------------------------
_PAGE = "Nội dung trang đủ dài để không bị coi là trang trắng của bản scan hồ sơ giao đất, chuyển mục đích. " * 2


def _pdf_data_url(pages: int) -> str:
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def test_dispatcher_picks_mode_from_split_setting(monkeypatch):
    calls = []

    async def fake_tach(files, options, session):
        calls.append("tach")
        return {}

    async def fake_khong_tach(files, options, session):
        calls.append("khong_tach")
        return {}

    monkeypatch.setattr(dispatcher, "plan_with_split", fake_tach)
    monkeypatch.setattr(dispatcher, "plan_without_split", fake_khong_tach)
    for options in ({"splitDocuments": True}, {}, None, {"splitDocuments": True, "supportsSourceSegments": False}):
        asyncio.run(attach.plan([], options))
    assert calls == ["tach", "khong_tach", "khong_tach", "khong_tach"]


def test_split_bundle_one_item_per_document():
    """File gộp Đơn + giấy ủy quyền (2 trang kèm lời chứng thực) + Giấy chứng nhận (2 trang)."""
    documents = {0: [(0, "don_de_nghi", "Đơn đề nghị chuyển mục đích sử dụng đất"),
                     (1, "authorization", "Giấy ủy quyền"),
                     (3, "gcn", "Giấy chứng nhận quyền sử dụng đất")]}
    attachments, warnings, segments = tach.build_plan_items(_files(["ho-so.pdf"]), {0: [_PAGE] * 5}, documents)

    assert [(item["componentIndex"], item["sourceSegments"][0]["pageIndexes"]) for item in attachments] == [
        (2, [0]), (2, [1, 2]), (4, [3, 4])]
    assert [item["documentName"] for item in attachments] == [
        "Đơn đề nghị chuyển mục đích sử dụng đất", "Giấy ủy quyền", "Giấy chứng nhận quyền sử dụng đất"]
    assert {item["loaiBan"] for item in attachments} == {"Bản chính"}
    assert warnings == [] and segments[2]["pages"] == [4, 5]


def test_split_drops_blank_pages_and_routes_gia_han():
    pages = [_PAGE, "Qwen", _PAGE]
    documents = {0: [(0, "don_gia_han", ""), (2, "gcn", "")]}
    attachments, _warnings, _segments = tach.build_plan_items(_files(["gia-han.pdf"]), {0: pages}, documents)
    assert [(item["componentIndex"], item["sourceSegments"][0]["pageIndexes"]) for item in attachments] == [
        (14, [0]), (13, [2])]
    assert attachments[0]["documentName"] == "Đơn đề nghị gia hạn sử dụng đất (Mẫu số 04)"


def test_split_unsplittable_bundle_goes_whole_once():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["gop.pdf"]), {0: ["trích đoạn"]}, {0: [(0, "gcn", ""), (0, "don_de_nghi", ""), (0, "identity", "")]},
    )
    assert [(item["componentIndex"], item["documentName"], "sourceSegments" in item) for item in attachments] == [
        (2, "gop.pdf", False)]
    assert len(warnings) == 1 and "dòng 4" in warnings[0]


def test_split_plan_cuts_real_pdf_pages(monkeypatch):
    from app.services import ocr

    text = "\n".join(f"───── Trang {n}/3 ─────\n{_PAGE}" for n in range(1, 4))

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        return ('{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"docType":"don_de_nghi","ten":"Đơn"},'
                '{"trangDau":2,"docType":"gcn","ten":"Giấy chứng nhận"}]}]}')

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(3))]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [(item["componentIndex"], item["sourceSegments"]) for item in result["attachments"]] == [
        (2, [{"fileIndex": 0, "pageIndexes": [0]}]), (4, [{"fileIndex": 0, "pageIndexes": [1, 2]}])]


def test_split_falls_back_to_no_split_mode(monkeypatch):
    from app.services import ocr

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def broken_segment(units):
        raise ValueError("JSON hỏng")

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn","don_de_nghi"]}]}'

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(tach, "_segment", broken_segment)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl="x")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [item["componentIndex"] for item in result["attachments"]] == [2]
    assert result["errors"][0].startswith("Tách giấy tờ: JSON hỏng")


# --------------------------------------------------------------------------------------
# ĐIỀN — chung dữ liệu cho hai form
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="Lê Văn An",
    ChuHoSo_NgaySinh="02/06/1967",
    ChuHoSo_GioiTinh="Nam",
    ChuHoSo_SoDinhDanh="0360 6700 0001",
    ChuHoSo_NgayCap="25/08/2021",
    ChuHoSo_NoiCap="Cục cảnh sát QLHC về TTXH",
    ChuHoSo_NoiCuTru={"tinh": "Ninh Bình", "xa": "Nghĩa Hưng", "chiTietDuoiXa": "Thôn Đông"},
    ChuHoSo_DienThoai="0912.000.111",
    DongSuDung_HoTen="Phạm Thị Cúc",
    DongSuDung_GioiTinh="Nữ",
    DongSuDung_NgaySinh="05/07/1971",
    DongSuDung_SoDinhDanh="036171000003",
    DongSuDung_NgayCap="27/08/2021",
    DongSuDung_NoiCap="Cục cảnh sát QLHC về TTXH",
    Don_TieuDe="ĐƠN ĐỀ NGHỊ CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT",
    Don_NoiDungDeNghi="Chuyển 50 m2 từ đất trồng cây lâu năm (CLN) sang đất ở tại nông thôn ONT – lâu dài",
    Don_HinhThucSuDung="Sử dụng chung của vợ và chồng",
    ThuaDat_SoThua="82",
    ThuaDat_SoTo="21",
    ThuaDat_DiaChi={"tinh": "Ninh Bình", "xa": "Nghĩa Hưng", "chiTietDuoiXa": "Thôn Đông"},
    GCN_So="AA 01234567",
    GCN_SoVaoSo="VP00001",
    GCN_NgayCap="23/06/2026",
    GCN_CoQuanCap="Văn phòng đăng ký đất đai Nam Định",
)
_AGENT = dict(
    NguoiNop_HoTen="Trần Thị Bình",
    NguoiNop_NgaySinh="1985",
    NguoiNop_GioiTinh="Nữ",
    NguoiNop_SoDinhDanh="036185000002",
    NguoiNop_NgayCap="31/03/2025",
    NguoiNop_NoiCap="Bộ Công An",
    NguoiNop_NoiCuTru={"tinh": "Ninh Bình", "xa": "Nghĩa Hưng", "chiTietDuoiXa": "Thôn Tây"},
)
_CO_USER = ("Người đồng sử dụng: bà Phạm Thị Cúc, sinh ngày 05/07/1971, CCCD 036171000003, do Cục Cảnh sát quản lý "
            "hành chính về trật tự xã hội cấp ngày 27/08/2021.")


def test_form1_authorized_submitter_in_part_one_and_owner_in_part_two():
    fields, warnings = mapper.enrich(_facts(**_OWNER, **_AGENT))
    values = _values(fields)

    assert values["data[fullname]"] == "Trần Thị Bình"
    assert values["data[identityNumber]"] == "036185000002"
    assert values["data[gender]"] == "Nữ"
    assert (values["data[identityDate]"], values["data[identityAgency]"]) == ("31/03/2025", "Bộ Công an")
    assert (values["data[province]"], values["data[district]"], values["data[address]"]) == (
        "Tỉnh Ninh Bình", "Xã Nghĩa Hưng", "Thôn Tây")
    # Bên được ủy quyền không ghi số: dùng số liên hệ trên Đơn (file mapping).
    assert values["data[phoneNumber]"] == "0912000111"
    assert "data[birthday]" not in values  # chỉ có năm sinh → xoá trắng ngày sinh tài khoản cổng điền sẵn
    assert _cleared(fields) == {"data[birthday]", "data[email]"}
    assert values["data[tenHoSo]"] == "ĐƠN ĐỀ NGHỊ CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT"
    assert values["data[textField]"] == (
        "Chuyển 50 m2 từ đất trồng cây lâu năm (CLN) sang đất ở tại nông thôn ONT – lâu dài; thửa đất số 82, tờ bản "
        "đồ số 21, địa điểm Thôn Đông, xã Nghĩa Hưng, tỉnh Ninh Bình; Giấy chứng nhận số AA 01234567, số vào sổ cấp "
        "VP00001, cấp ngày 23/06/2026; hình thức sử dụng đất: Sử dụng chung của vợ và chồng. " + _CO_USER)
    assert values["data[Hovaten]"] == "Lê Văn An"
    assert values["data[Sogiaytotuythan]"] == "036067000001"
    assert values["data[sodienthoai]"] == "0912000111"
    assert values["data[diachi]"] == "Thôn Đông, xã Nghĩa Hưng, tỉnh Ninh Bình"
    assert {item["name"] for item in fields if item.get("default")} == {"data[nation]", "data[hinhThucNop]"}
    assert len(warnings) == 1 and "Ngày sinh" in warnings[0] and "Giới tính" not in warnings[0]


def test_form1_self_submit_fills_part_one_from_owner_only():
    fields, warnings = mapper.enrich(_facts(**_OWNER))
    values = _values(fields)
    assert values["data[fullname]"] == "Lê Văn An"
    assert values["data[birthday]"] == "02/06/1967"
    assert values["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[address]"] == "Thôn Đông"
    assert not {"data[Hovaten]", "data[Sogiaytotuythan]", "data[sodienthoai]", "data[diachi]"} & set(values)
    assert warnings == []


def test_form2_vbdlis_owner_name_and_applicant_fields():
    fields, warnings = vbdlis_mapper.enrich(_facts(**_OWNER, **_AGENT))
    values = _values(fields)

    assert values["data[ownerFullname]"] == "Lê Văn An"
    assert values["data[fullname]"] == "Trần Thị Bình"
    assert values["data[gender]"] == "Nữ"
    assert values["data[phoneNumber]"] == "0912000111"
    assert values["data[identityNumber]"] == "036185000002"
    assert (values["data[province]"], values["data[district]"], values["data[address]"]) == (
        "Tỉnh Ninh Bình", "Xã Nghĩa Hưng", "Thôn Tây")
    assert values["data[note]"] == _CO_USER + " Hình thức sử dụng đất: Sử dụng chung của vợ và chồng."
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Đề nghị cho phép chuyển mục đích sử dụng đất: Chuyển 50 m2 từ đất trồng cây lâu năm (CLN) sang đất ở tại "
        "nông thôn ONT – lâu dài; Giấy chứng nhận số AA 01234567, số vào sổ cấp VP00001, do Văn phòng đăng ký đất đai "
        "Nam Định cấp ngày 23/06/2026.")
    assert values["data[tenHoSo]"] == "ĐƠN ĐỀ NGHỊ CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT"
    assert (values["data[SoThuTuThua]"], values["data[SoHieuToBanDo]"]) == ("82", "21")
    assert values["data[diaChiThuaDat1]"] == "Thôn Đông, xã Nghĩa Hưng, tỉnh Ninh Bình"
    assert (values["data[province2]"], values["data[district2]"]) == ("Tỉnh Ninh Bình", "Xã Nghĩa Hưng")
    assert {item["name"] for item in fields if item.get("default")} == {
        "data[chonDoiTuong]", "data[hinhThucNop]", "data[nation]", "data[nation2]"}
    assert len(warnings) == 1 and "Ngày sinh" in warnings[0] and "thửa đất" not in warnings[0]


def test_form2_warns_when_parcel_province_has_no_source():
    owner = {key: value for key, value in _OWNER.items() if key != "ThuaDat_DiaChi"}
    _fields, warnings = vbdlis_mapper.enrich(_facts(**owner))
    assert len(warnings) == 1 and "Tỉnh/TP thửa đất" in warnings[0]
    assert {"data[province2]", "data[district2]"} <= _cleared(_fields)


def test_schemas_skip_organisation_fields():
    assert "data[fullname1]" not in UI_COMP_BY_NAME and "data[agency1]" not in UI_COMP_BY_NAME
    assert not {"data[fullname1]", "data[ProcedureDossierQuantity]"} & set(VBDLIS_UI)
    assert {"DongSuDung_HoTen", "GCN_SoVaoSo", "ThuaDat_SoThua", "Don_TieuDe"} <= ALLOWED


# --------------------------------------------------------------------------------------
# REGISTRY + NHẬN DIỆN + LINK KÊ KHAI
# --------------------------------------------------------------------------------------
def _detect(url: str, body: str) -> str:
    """Như bước 0 của detectProcedureKeyFromSignals (popup.js): entry textPriority đúng cổng, đủ mọi cụm, tổng dài nhất."""
    text = fold(body)
    best, best_score = "", 0
    for procedure in PROCEDURES:
        detect = procedure.get("detect") or {}
        if not detect.get("textPriority"):
            continue
        if detect.get("urlScope") and not any(scope.lower() in url for scope in detect["urlScope"]):
            continue
        phrases = [fold(phrase) for phrase in detect.get("textIncludes") or []]
        if phrases and all(phrase in text for phrase in phrases) and sum(map(len, phrases)) > best_score:
            best, best_score = procedure["key"], sum(map(len, phrases))
    return best


def test_vbdlis_page_detected_as_form_2_and_normal_page_as_form_1():
    url = "https://dichvucong.tuyenquang.gov.vn/vi/padsvc/apply-online/abc"
    title = get_procedure(_KEY)["label"].removeprefix("Tuyên Quang - ")
    assert _detect(url, f"{title} 1.013949_VBDLIS_25 Ngày Thông tin chủ hồ sơ") == _VBDLIS_KEY
    assert _detect(url, f"{title} Quy trình giải quyết TTHC Họ và tên:") == _KEY


def test_registry_wires_both_forms_and_shared_attach():
    for key, module in ((_KEY, "process."), (_VBDLIS_KEY, "process_vbdlis.")):
        procedure = get_procedure(key)
        assert procedure["detect"]["urlScope"] == ["tuyenquang.gov.vn"]
        assert procedure["supportsSplitDocuments"] is True
        assert procedure_province_slugs(procedure) == ["tuyenquang"]
        assert get_pipeline(key).__module__.startswith(
            f"app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.{module}")
    assert get_attach_pipeline(_VBDLIS_KEY) is get_attach_pipeline(_KEY)
    # Cùng thủ tục: popup đổi từ form gốc (link kê khai) sang form VBDLIS mà không xoá giấy tờ.
    assert get_procedure(_VBDLIS_KEY)["formVariantOf"] == _KEY and "formVariantOf" not in get_procedure(_KEY)


def test_ke_khai_link_shares_registry_key():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.013949"
    assert links[0]["label"] == get_procedure(_KEY)["label"]


def test_quy_trinh_vbdlis_option_runs_form_2(monkeypatch):
    """Trợ lý: công dân chọn quy trình VBDLIS ở hộp thoại "Chọn trường hợp giải quyết" → options.quyTrinh → key gốc
    điền form 2; không có khóa này (Auto Fill) thì vẫn form 1."""
    from app.pipelines._shared.compact_agent import runner

    async def fake_run(files_by_role, **kwargs):
        return {"fields": _facts(ChuHoSo_HoTen="Trần Thị Bình", ThuaDat_SoThua="45"), "errors": []}

    monkeypatch.setattr(runner, "run", fake_run)
    form1 = asyncio.run(get_pipeline(_KEY)({"": []}, {}))
    form2 = asyncio.run(get_pipeline(_KEY)({"": []}, {"quyTrinh": "vbdlis"}))
    assert "data[SoThuTuThua]" not in _values(form1["fields"])
    assert _values(form2["fields"])["data[SoThuTuThua]"] == "45"
    assert _values(form2["fields"])["data[ownerFullname]"] == "Trần Thị Bình"
    assert _values(form2["fields"]) == _values(asyncio.run(get_pipeline(_VBDLIS_KEY)({"": []}, {}))["fields"])
    assert _values(asyncio.run(get_pipeline(_KEY)({"": []}, {"quyTrinh": "ilis"}))["fields"]) == _values(form1["fields"])


def test_tro_ly_chi_tai_khoan_tuyen_quang_va_hop_thoai_chon_quy_trinh():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Tuyên Quang - " + procedure["label"] == core["label"]
    assert procedure["detect"] == core["detect"] and procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.013949"
    assert handfree.is_allowed_in_province(procedure, "tuyenquang")
    assert not handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY]
    for label, options in (("Quy trình 20 ngày", {}), ("1.013949_VBDLIS_25 Ngày", {"quyTrinh": "vbdlis"})):
        conv = {"mae_dialog_options": {"process": {"options": [label], "current": label}}}
        assert handfree.case_pipeline_options(procedure, conv) == options, label
