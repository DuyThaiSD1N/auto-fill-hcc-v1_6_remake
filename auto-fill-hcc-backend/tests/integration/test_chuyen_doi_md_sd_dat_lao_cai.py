"""[Lào Cai] Chuyển mục đích/chuyển hình thức/gia hạn/điều chỉnh thời hạn sử dụng đất (1.115651).

Dữ liệu theo hồ sơ mẫu trong file mapping: chủ hồ sơ CÔNG TY TNHH SUPER - STAR (nhóm (2) chuyển hình thức, đơn Mẫu
03), người nộp Nhâm Đắc Đạt (VNeID), mảnh đo đạc chỉnh lý số 81-2025 tại xã Phú Thịnh, huyện Yên Bình, tỉnh Yên Bái cũ.
"""

import re
import unicodedata

from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.attach import catalog
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.attach.planner import build_plan_items
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process import mapper
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "chuyen-muc-dich-su-dung-dat-lao-cai"
_VNEID = {"formContext": {"applicantFullname": "NHÂM ĐẮC ĐẠT", "applicantIdentityNumber": "034203010212"}}

_ORG = {
    "ChuHoSo_LoaiDoiTuong": "Tổ chức",
    "ChuHoSo_TenToChuc": "Công ty TNHH Super - Star",
    "ChuHoSo_MaSoThue": "5200123456",
    "ThuaDat_DiaChi": {"tinh": "Yên Bái", "huyen": "Yên Bình", "xa": "Phú Thịnh",
                       "diaChi": "Thôn 3, Khu công nghiệp phía Nam"},
    "Don_DienThoai": "0912345678",
    "Dkdn_Email": "superstar.company@gmail.com",
}


def _run(values: dict, options: dict | None = _VNEID) -> dict:
    out = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    assert all(f["name"] in UI_COMP_BY_NAME for f in out)
    return {f["name"]: f["value"] for f in out}


def test_registry_wires_process_and_attach():
    proc = get_procedure(KEY)
    assert proc["detect"]["urlScope"] == ["laocai.gov.vn"] and proc["hasAttachmentStep"] is True
    assert get_pipeline(KEY) is not None and get_attach_pipeline(KEY) is not None
    assert {f["name"] for f in FIELDS}.isdisjoint(UI_COMP_BY_NAME)


def test_organization_owner_falls_back_to_land_location_from_sample():
    out = _run(_ORG)
    assert out["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert out["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY TNHH SUPER - STAR"
    assert out["ChuHoSo_maSoThueChuHoSo"] == "5200123456"
    assert out["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"  # Yên Bái cũ → Lào Cai
    assert out["ChuHoSo_maPhuongXaCHS"]
    assert out["ChuHoSo_diaChiChuHoSo"].startswith("Thôn 3")
    assert out["ChuHoSo_diDongLienLacCHS"] == "0912345678"
    assert out["ChuHoSo_emailChuHoSo"] == "superstar.company@gmail.com"
    assert out["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH SUPER - STAR"
    assert out["CongDan_maSoThueNguoiNop"] == "5200123456"
    for name in ("CongDan_diDong", "CongDan_email", "ChuHoSo_tenChuHoSo"):
        assert name not in out


def test_business_registration_address_beats_land_location():
    out = _run({**_ORG, "ChuHoSo_DiaChiDkdn": {"tinh": "Hà Nội", "xa": "Khương Đình", "diaChi": "Số 6A"}})
    assert out["ChuHoSo_maTinhThanhCHS"] == "Thành phố Hà Nội"
    assert out["ChuHoSo_diaChiChuHoSo"] == "Số 6A"


def test_individual_owner_uses_own_card():
    values = {
        "ChuHoSo_LoaiDoiTuong": "Cá nhân",
        "ChuHoSo_HoTen": "Trần Văn Bình",
        "ChuHoSo_SoDinhDanh": "015070001234",
        "DanhSachCccd": [{"HoTen": "TRẦN VĂN BÌNH", "SoDinhDanh": "015070001234", "NgaySinh": "02/03/1970",
                          "GioiTinh": "Nam", "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "diaChi": "Tổ 5"}}],
    }
    out = _run(values, {})
    assert out["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert out["ChuHoSo_tenChuHoSo"] == "TRẦN VĂN BÌNH"
    assert out["ChuHoSo_ngaySinhChuHoSo"] == "02/03/1970"
    assert out["ChuHoSo_diaChiChuHoSo"] == "Tổ 5"


def test_applicant_card_fills_applicant_identity():
    card = {"HoTen": "NHÂM ĐẮC ĐẠT", "SoDinhDanh": "034203010212", "NgaySinh": "03/12/2003", "GioiTinh": "Nam",
            "DanToc": "Kinh", "NgayCap": "01/07/2026", "NoiCap": "Bộ Công an"}
    out = _run({**_ORG, "DanhSachCccd": [card]})
    assert out["CongDan_gioiTinhCongDan"] == "Nam" and out["CongDan_ngayCapCmnd"] == "01/07/2026"


# ------------------------------- đính kèm -------------------------------

def _files(n: int) -> list[dict]:
    return [{"name": f"f{i}.pdf", "_index": i} for i in range(n)]


def test_sample_dossier_group_2_plan():
    llm = {
        0: {"label": "don_mau_03", "documentName": "Đơn đề nghị chuyển hình thức sử dụng đất"},
        1: {"label": "gcn", "documentName": "GCN 1"},
        2: {"label": "gcn", "documentName": "GCN 2"},
        3: {"label": "quyet_dinh_giao_dat", "documentName": "Quyết định cho thuê đất"},
        4: {"label": "ban_do", "documentName": "Mảnh đo đạc chỉnh lý số 81-2025"},
        5: {"label": "gcn_dkdn", "documentName": "GCN đăng ký doanh nghiệp"},
        6: {"label": "cccd"},
    }
    attachments, warnings, _, group, source = build_plan_items(_files(7), llm, "1")
    assert (group, source) == ("2", "form")  # đơn thắng nhóm LLM đoán
    by_file = {a["fileName"]: a for a in attachments}
    assert by_file["f0.pdf"]["slotKey"] == "lc_115651_2_1"
    assert by_file["f1.pdf"]["slotKey"] == by_file["f2.pdf"]["slotKey"] == "lc_115651_2_2"
    assert by_file["f3.pdf"]["slotKey"] == "lc_115651_2_3"
    assert by_file["f4.pdf"]["target"] == "new" and by_file["f4.pdf"]["noChooserClick"] is True
    assert by_file["f5.pdf"]["target"] == "new"
    assert "f6.pdf" not in by_file and len(warnings) == 1
    assert all(a["sectionHeader"] == catalog.SECTION_HEADERS["2"] for a in attachments if a["target"] == "fixed-slot")


def test_group_routes_for_other_forms():
    llm = {0: {"label": "don_mau_18"}, 1: {"label": "gcn"}, 2: {"label": "quyet_dinh_giao_dat"},
           3: {"label": "vb_thay_doi_thoi_han_du_an"}}
    attachments, _, _, group, _ = build_plan_items(_files(4), llm)
    assert group == "4"
    assert [a["slotKey"] for a in attachments] == ["lc_115651_4_1", "lc_115651_4_3", "lc_115651_4_4", "lc_115651_4_2"]

    attachments, _, _, group, source = build_plan_items(_files(1), {0: {"label": "gcn"}})
    assert (group, source) == ("1", "default") and attachments[0]["slotKey"] == "lc_115651_1_2"

    # Nhóm (3) không có dòng quyết định giao đất → Giấy tờ khác.
    attachments, _, _, _, _ = build_plan_items(_files(2), {0: {"label": "don_mau_17"}, 1: {"label": "quyet_dinh_giao_dat"}})
    assert attachments[1]["target"] == "new"


# Tên dòng THẬT trên cổng (options.attachmentContext của req_d786792a79d6), theo thứ tự bảng.
_PORTAL_ROWS = [
    "(1) Hồ sơ đề nghị chuyển mục đích sử dụng đất gồm:",
    "Đơn theo Mẫu số 02 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc một trong các loại giấy tờ quy định tại Điều 137 Luật Đất đai hoặc quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật về đất đai qua các thời kỳ; các tài liệu liên quan đến việc đáp ứng tiêu chí, điều kiện chuyển mục đích sử dụng đất trồng lúa, đất rừng phòng hộ, đất rừng đặc dụng, đất rừng sản xuất sang mục đích khác quy định tại khoản 1 Điều 46 Nghị định số 102/2024/NĐ-CP (nếu có)",
    "(2) Hồ sơ đề nghị chuyển hình thức sử dụng đất gồm:",
    "Đơn theo Mẫu số 03 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc một trong các loại giấy tờ quy định tại Điều 137 Luật Đất đai",
    "Quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật đất đai qua các thời kỳ",
    "(3) Hồ sơ đề nghị gia hạn sử dụng đất khi hết thời hạn sử dụng đất gồm:",
    "Đơn theo Mẫu số 17 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai",
    "Văn bản của cơ quan có thẩm quyền cho phép gia hạn thời hạn hoạt động của dự án đầu tư hoặc thể hiện thời hạn hoạt động của dự án đầu tư theo quy định của pháp luật về đầu tư đối với trường hợp sử dụng đất để thực hiện dự án đầu tư",
    "(4) Hồ sơ đề nghị điều chỉnh thời hạn sử dụng đất của dự án đầu tư gồm:",
    "Đơn theo Mẫu số 18 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Văn bản của cơ quan có thẩm quyền cho phép thay đổi thời hạn hoạt động của dự án đầu tư theo quy định của pháp luật về đầu tư",
    "Một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, Giấy chứng nhận quyền sở hữu nhà ở và quyền sử dụng đất ở, Giấy chứng nhận quyền sở hữu nhà ở, Giấy chứng nhận quyền sở hữu công trình xây dựng, Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất đã được cấp theo quy định của pháp luật về đất đai, pháp luật về nhà ở, pháp luật về xây dựng trước ngày Luật Đất đai có hiệu lực thi hành; Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
    "Quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật về đất đai qua các thời kỳ",
]


def _fold(value: str) -> str:
    # Giống foldChoiceText ở extension: bỏ dấu, đ→d, gạch nối → khoảng trắng, chữ thường.
    text = unicodedata.normalize("NFD", value.replace("Đ", "D").replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()
    return re.sub(r"\s+", " ", re.sub(r"\s*[-–—‐‑]+\s*", " ", text)).strip()


def test_row_keywords_pick_exactly_one_row_per_group():
    # Cùng regex tiêu đề nhóm với FIXED_SLOT_SECTION_RE ở extension.
    header = re.compile(r"(^|\s)(?:[a-z]\) doi voi truong hop|\(\d+\) ho so de nghi)")
    rows: dict[tuple[str, int], str] = {}
    group, position = "", 0
    for name in map(_fold, _PORTAL_ROWS):
        if header.search(name):
            group, position = name[1], 0
            assert catalog.SECTION_HEADERS[group] in name
            continue
        assert not header.search(name)
        position += 1
        rows[(group, position)] = name
    assert set(catalog.ROWS) <= set(rows)
    for row, (keywords, _) in catalog.ROWS.items():
        hits = [key for key, text in rows.items() if key[0] == row[0] and any(kw in text for kw in keywords)]
        # FE lấy dòng khớp đầu tiên; chỉ nhóm (3) có 2 dòng GCN trùng hệt nhau trên cổng.
        assert hits and hits[0] == row, (row, hits)
        assert len(hits) == 1 or row == ("3", 2), (row, hits)


def test_response_model_keeps_section_fields_for_lao_cai_planners():
    # Hồi quy: AttachmentPlanResp từng lược mất sectionHeader/slotKeywords/tickRow/noChooserClick → FE không tìm
    # được ô nào ("Không tìm thấy ô đính kèm") và bấm "Chọn tệp tin" mở hộp thoại file.
    from app.attachments.schemas import AttachmentPlanResp
    from app.pipelines.cap_GCN_nhan_chuyen_nhuong.attach.planner import build_plan_items as plan_115667
    from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach.planner import build_plan_items as plan_115668

    items = (
        build_plan_items(_files(2), {0: {"label": "don_mau_03"}, 1: {"label": "ban_do"}})[0]
        + plan_115668(_files(1), {0: {"label": "don_dang_ky"}})[0]
        + plan_115667(_files(1), [], {0: {"label": "don_dang_ky"}}, "b")[0]
    )
    dumped = AttachmentPlanResp(attachments=items).model_dump(exclude_none=True)["attachments"]
    for raw, kept in zip(items, dumped):
        for key in ("sectionHeader", "slotKeywords", "tickRow", "noChooserClick"):
            assert kept.get(key) == raw.get(key), key
