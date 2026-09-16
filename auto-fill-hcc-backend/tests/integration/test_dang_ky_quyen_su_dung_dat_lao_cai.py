"""[Lào Cai] Đăng ký biến động QSDĐ (1.115668) — mapper bước 2 + kế hoạch đính kèm.

Dữ liệu theo hồ sơ mẫu trong file mapping: chủ hồ sơ là Công ty TNHH Thương mại và Dịch vụ La Giang (bên mua
tài sản đấu giá), người nộp Nhâm Đắc Đạt (VNeID), giấy ủy quyền Nguyễn Mạnh Duy → Lê Hồng Thanh.
"""

import re

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach import catalog
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach.planner import build_plan_items
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process import mapper
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-bien-dong-dat-dai-lao-cai"
_VNEID = {"formContext": {"applicantFullname": "NHÂM ĐẮC ĐẠT", "applicantIdentityNumber": "034203010212"}}

_ORG = {
    "ChuHoSo_LoaiDoiTuong": "Tổ chức",
    "ChuHoSo_TenToChuc": "Công ty TNHH Thương mại và Dịch vụ La Giang",
    "ChuHoSo_MaSoThue": "0111428432",
    "ChuHoSo_DiaChiHopDong": {"tinh": "Hà Nội", "xa": "Khương Đình", "diaChi": "Số 6A, hẻm 358/25/5A Bùi Xương Trạch"},
    "Don_DienThoai": "0931391579",
    "HopDong_DienThoai": "0971464078",
    "Dkdn_DienThoai": "0971464078",
    "Dkdn_Email": "lagiangxanh79@gmail.com",
    "NguoiTrongGiayTo": [
        {"HoTen": "Nguyễn Mạnh Duy", "SoDinhDanh": "001096001005", "NgaySinh": "14/02/1996", "NgayCap": "19/04/2021",
         "NoiCap": "Cục cảnh sát quản lý hành chính về trật tự xã hội"},
        {"HoTen": "Lê Hồng Thanh", "SoDinhDanh": "022091001541", "NgaySinh": "13/07/1991", "NgayCap": "26/04/2023",
         "NoiCap": "Cục cảnh sát quản lý hành chính về trật tự xã hội"},
    ],
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


def test_organization_owner_from_sample_dossier():
    out = _run(_ORG)
    assert out["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert out["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY TNHH THƯƠNG MẠI VÀ DỊCH VỤ LA GIANG"
    assert out["ChuHoSo_maSoThueChuHoSo"] == "0111428432"
    assert out["ChuHoSo_maTinhThanhCHS"] == "Thành phố Hà Nội"
    assert out["ChuHoSo_maPhuongXaCHS"] == "Phường Khương Đình"
    assert out["ChuHoSo_diaChiChuHoSo"] == "Số 6A, hẻm 358/25/5A Bùi Xương Trạch"
    assert out["ChuHoSo_diDongLienLacCHS"] == "0931391579"  # Đơn thắng HĐ/GCN ĐKDN
    assert out["ChuHoSo_emailChuHoSo"] == "lagiangxanh79@gmail.com"
    # Người nộp đại diện tổ chức; KHÔNG nhận SĐT/email và không nhận nhân thân của giám đốc/người được ủy quyền.
    assert out["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH THƯƠNG MẠI VÀ DỊCH VỤ LA GIANG"
    assert out["CongDan_maSoThueNguoiNop"] == "0111428432"
    for name in ("ChuHoSo_tenChuHoSo", "ChuHoSo_soCMNDChuHoSo", "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd"):
        assert name not in out
    names = list(out)
    assert names.index("ChuHoSo_maDoiTuongNopHS") < names.index("ChuHoSo_tenCoQuanToChucCHS")
    assert names.index("ChuHoSo_maTinhThanhCHS") < names.index("ChuHoSo_maPhuongXaCHS")


def test_applicant_own_card_fills_applicant_identity():
    card = {"HoTen": "NHÂM ĐẮC ĐẠT", "SoDinhDanh": "034203010212", "NgaySinh": "3/12/2003", "GioiTinh": "Nam",
            "DanToc": "Kinh", "NgayCap": "01/07/2021", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"}
    out = _run({**_ORG, "DanhSachCccd": [card]})
    assert out["CongDan_ngaySinhCongDan"] == "03/12/2003"
    assert out["CongDan_gioiTinhCongDan"] == "Nam"
    assert out["CongDan_danTocCongDan"] == "Kinh"
    assert out["CongDan_ngayCapCmnd"] == "01/07/2021"
    for name in ("CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_diDong", "CongDan_email", "CongDan_maTinhThanh"):
        assert name not in out


def test_authorized_applicant_takes_issue_date_from_power_of_attorney():
    ctx = {"formContext": {"applicantFullname": "LÊ HỒNG THANH", "applicantIdentityNumber": "022091001541"}}
    out = _run(_ORG, ctx)
    assert out["CongDan_ngayCapCmnd"] == "26/04/2023"
    assert out["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert "CongDan_ngaySinhCongDan" not in out  # chỉ thẻ thật mới bổ sung ngày sinh/giới tính


def test_individual_owner_prefers_card_then_documents():
    values = {
        "ChuHoSo_LoaiDoiTuong": "Cá nhân",
        "ChuHoSo_HoTen": "Trần Văn Bình",
        "ChuHoSo_SoDinhDanh": "0150 7000 1234",
        "ChuHoSo_NgaySinh": "1970",
        "ChuHoSo_XungHo": "Ông",
        "ChuHoSo_NgayCap": "05/05/2021",
        "ChuHoSo_DiaChiDon": {"tinh": "Lào Cai", "xa": "Yên Bái", "diaChi": "Tổ 5"},
        "DanhSachCccd": [{"HoTen": "TRẦN VĂN BÌNH", "SoDinhDanh": "015070001234", "NgaySinh": "02/03/1970",
                          "DanToc": "Tày", "NgayCap": "10/10/2022", "NoiCap": "Bộ Công an"}],
    }
    out = _run(values, {})
    assert out["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert out["ChuHoSo_tenChuHoSo"] == "TRẦN VĂN BÌNH"
    assert out["ChuHoSo_soCMNDChuHoSo"] == "015070001234"
    assert out["ChuHoSo_ngaySinhChuHoSo"] == "02/03/1970"
    assert out["ChuHoSo_gioiTinhChuHoSo"] == "Nam"
    assert out["ChuHoSo_danTocChuHoSo"] == "Tày"
    assert out["ChuHoSo_ngayCapCMNDCHS"] == "10/10/2022"  # CCCD thắng giấy tờ
    assert out["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert "CongDan_tenCoQuanToChuc" not in out


def test_individual_without_id_number_is_not_selected():
    out = _run({"ChuHoSo_LoaiDoiTuong": "Cá nhân", "ChuHoSo_HoTen": "Trần Văn Bình"}, {})
    assert "ChuHoSo_maDoiTuongNopHS" not in out


# ------------------------------- đính kèm -------------------------------

_FILES = [{"name": f"f{i}.pdf", "_index": i} for i in range(7)]
_SAMPLE_LLM = {
    0: {"label": "don_dang_ky", "documentName": "Đơn đăng ký biến động đất đai"},
    1: {"label": "hop_dong_chuyen_quyen", "documentName": "Hợp đồng mua bán tài sản đấu giá"},
    2: {"label": "gcn_dkdn", "documentName": "GCN đăng ký doanh nghiệp La Giang"},
    3: {"label": "gcn_dkdn", "documentName": "GCN đăng ký doanh nghiệp PAMC"},
    4: {"label": "vb_dai_dien", "documentName": "Giấy ủy quyền"},
    5: {"label": "hoa_don", "documentName": "Hóa đơn thanh toán"},
    6: {"label": "gcn", "documentName": "Giấy chứng nhận BM 968174"},
}


def test_sample_dossier_attachment_plan():
    attachments, warnings, _, branch = build_plan_items(_FILES, _SAMPLE_LLM)
    assert branch == "a" and not warnings
    by_file = {a["fileName"]: a for a in attachments}
    assert by_file["f0.pdf"]["slotKey"] == "lc_115668_a_1"
    assert by_file["f1.pdf"]["slotKey"] == "lc_115668_a_3"
    assert by_file["f6.pdf"]["slotKey"] == "lc_115668_a_2"
    # Hai GCN ĐKDN + giấy ủy quyền cùng một dòng → cùng slotKey để FE gom một lần chọn tệp.
    assert {by_file[f]["slotKey"] for f in ("f2.pdf", "f3.pdf", "f4.pdf")} == {"lc_115668_a_12"}
    assert by_file["f5.pdf"]["target"] == "new" and by_file["f5.pdf"]["componentName"] == "Hóa đơn thanh toán"
    for item in attachments:
        if item["target"] == "fixed-slot":
            assert item["tickRow"] and item["sectionHeader"] == catalog.SECTION_HEADERS["a"]


def test_identity_cards_are_skipped():
    attachments, warnings, classified, _ = build_plan_items([{"name": "cccd.jpg", "_index": 0}], {0: {"label": "cccd"}})
    assert attachments == [] and len(warnings) == 1 and classified[0]["target"] == "skip"


def test_donation_to_state_switches_to_branch_b_with_certificate_on_same_row():
    files = [{"name": "bb.pdf", "_index": 0}, {"name": "gcn.pdf", "_index": 1}, {"name": "don.pdf", "_index": 2}]
    llm = {0: {"label": "bb_tang_cho_ubnd"}, 1: {"label": "gcn"}, 2: {"label": "don_dang_ky"}}
    attachments, _, _, branch = build_plan_items(files, llm)
    by_file = {a["fileName"]: a for a in attachments}
    assert branch == "b"
    assert by_file["bb.pdf"]["slotKey"] == by_file["gcn.pdf"]["slotKey"] == "lc_115668_b_2"
    assert by_file["don.pdf"]["target"] == "new"


# Tên dòng THẬT trên cổng (options.attachmentContext của req_02f519139998), theo thứ tự bảng.
_PORTAL_ROWS = [
    "a) Đối với trường hợp chuyển đổi, chuyển nhượng, thừa kế, góp vốn bằng quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất; cho thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng; bán hoặc thừa kế hoặc góp vốn bằng tài sản gắn liền với đất thuê của Nhà nước theo hình thức thuê đất trả tiền hàng năm; tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND (Bản chính)",
    "Giấy chứng nhận đã cấp (Bản chính)",
    "Hợp đồng hoặc văn bản về việc chuyển quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đối với trường hợp chuyển đổi, chuyển nhượng, thừa kế, góp vốn bằng quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất (Bản chính)",
    "Hợp đồng hoặc văn bản về việc bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất theo quy định của pháp luật về dân sự đối với trường hợp đất thuê của Nhà nước theo hình thức thuê đất trả tiền hằng năm (Bản chính)",
    "Văn bản của cơ quan có thẩm quyền về việc cho phép chuyển nhượng quyền khai thác khoáng sản đối với trường hợp chuyển nhượng quyền khai thác khoáng sản theo quy định của pháp luật về địa chất và khoáng sản (Bản chính)",
    "Văn bản về việc cho thuê, cho thuê lại quyền sử dụng đất đối với trường hợp cho thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng (Bản chính)",
    "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 28 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND đối với trường hợp đăng ký biến động đất đai mà phải tách thửa đất, hợp thửa đất (Bản chính)",
    "Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc để xác định lại kích thước các cạnh, diện tích của thửa đất (Bản chính)",
    "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đối với trường hợp có nhiều người nhận chuyển quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất (Bản chính)",
    "Văn bản của người sử dụng đất đồng ý cho chủ sở hữu tài sản gắn liền với đất được chuyển nhượng, tặng cho, góp vốn bằng tài sản gắn liền với đất đối với trường hợp chuyển nhượng, tặng cho, góp vốn bằng tài sản gắn liền với đất mà chủ sở hữu tài sản không có quyền sử dụng đất đối với thửa đất đó, trừ trường hợp tổ chức nước ngoài, cá nhân nước ngoài được sở hữu nhà ở theo quy định của pháp luật về nhà ở (Bản chính)",
    "Văn bản của bên nhận thế chấp về việc đồng ý cho bên thế chấp được chuyển nhượng, tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đối với trường hợp chuyển nhượng, tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất mà quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đang được thế chấp và đã đăng ký tại Văn phòng Đăng ký đất đai, Chi nhánh Văn phòng Đăng ký đất đai (Bản chính)",
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện (Bản chính)",
    "b) Đối với trường hợp người sử dụng đất tặng cho quyền sử dụng đất cho Nhà nước hoặc cộng đồng dân cư hoặc mở rộng đường giao thông, người sử dụng đất nộp một trong các loại giấy tờ sau đây:",
    "Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp giữa đại diện thôn, làng, bản, tổ dân phố, điểm dân cư với người sử dụng đất về việc tặng cho quyền sử dụng đất và bản gốc Giấy chứng nhận đã cấp (Bản chính)",
    "Biên bản họp giữa Ủy ban nhân dân cấp xã với người sử dụng đất về việc tặng cho quyền sử dụng đất và bản gốc Giấy chứng nhận đã cấp (Bản chính)",
]


def _fold(value: str) -> str:
    # Giống foldChoiceText ở extension: bỏ dấu, đ→d, gạch nối → khoảng trắng, chữ thường.
    import unicodedata

    text = unicodedata.normalize("NFD", value.replace("Đ", "D").replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()
    return re.sub(r"\s+", " ", re.sub(r"\s*[-–—‐‑]+\s*", " ", text)).strip()


def test_row_keywords_pick_exactly_one_real_portal_row():
    header = re.compile(r"(^|\s)[a-z]\) doi voi truong hop")
    rows: dict[tuple[str, int], str] = {}
    branch, position = "", 0
    for name in map(_fold, _PORTAL_ROWS):
        if header.search(name):
            branch, position = name[0], 0
            assert catalog.SECTION_HEADERS[branch] in name
            continue
        position += 1
        rows[(branch, position)] = name
    assert set(rows) == set(catalog.ROWS)
    for row, (keywords, _) in catalog.ROWS.items():
        hits = [key for key, text in rows.items() if key[0] == row[0] and any(kw in text for kw in keywords)]
        assert hits == [row], (row, hits)
