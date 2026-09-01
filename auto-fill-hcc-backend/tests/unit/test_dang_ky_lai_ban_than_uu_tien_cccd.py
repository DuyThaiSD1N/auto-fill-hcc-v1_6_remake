"""Người yêu cầu tự đi làm cho mình ("Bản thân") → giấy tờ tùy thân mục I lấy theo CCCD.

Hồ sơ thật của ông Ngô Văn Tiến: tờ khai viết tay ghi "CCCD số 0240806368" (OCR rụng mất hai chữ
số), còn tấm căn cước trong hồ sơ ghi 024068006368. Mapper cũ ưu tiên tờ khai nên mục I ra số 10
chữ số — cổng bắt lỗi đỏ cả ô "Số định danh cá nhân" lẫn ô "Giấy tờ tùy thân". Số/ngày cấp/nơi cấp
là thuộc tính CỦA TẤM THẺ nên thẻ là nguồn đúng; tờ khai chỉ bù khi hồ sơ không có thẻ.
"""

from app.pipelines.khai_sinh_dang_ky_lai.process.mapper import enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


# Nguyên văn output agent của hồ sơ Scan_0001.pdf (đã lược field không liên quan).
_HO_SO = [
    {"name": "Requester_SourceDocumentTitle", "value": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH"},
    {"name": "Requester_RelationToSubject", "value": "Bản thân"},
    {"name": "Requester_FullName", "value": "Ngô Văn Tiến"},
    {"name": "Requester_IdNumber", "value": "0240806368"},          # OCR tờ khai rụng chữ số
    {"name": "Requester_IdIssueDate", "value": "16/12/2024"},
    {"name": "Requester_IdIssuePlace", "value": "Bộ Công an"},
    {"name": "Requester_ResidenceDomestic",
     "value": {"quocGia": "Việt Nam", "tinh": "Bà Rịa - Vũng Tàu", "xa": "Bắc Giang",
               "diaChi": "Số 03, đường Lê Lợi, TDPDK"}},
    {"name": "Subject_FullName", "value": "Ngô Văn Tiến"},
    {"name": "Subject_BirthDate", "value": "03/10/1968"},
    {"name": "Subject_Gender", "value": "Nam"},
    {"name": "Subject_Ethnicity", "value": "Kinh"},
    {"name": "Subject_IdNumber", "value": "024068006368"},          # đọc từ thẻ căn cước
    {"name": "Subject_IdIssueDate", "value": "16/12/2024"},
    {"name": "Subject_IdIssuePlace", "value": "Bộ Công an"},
    {"name": "Subject_ResidenceDomestic",
     "value": {"quocGia": "Việt Nam", "tinh": "Bắc Giang", "xa": "Bắc Giang", "diaChi": "Dinh Kế"}},
    {"name": "Mother_FullName", "value": "Nguyễn Thị Tín"},
    {"name": "Mother_IdNumber", "value": "024139002897"},
    {"name": "Father_FullName", "value": "Ngô Thanh Chi"},
]


def test_so_dinh_danh_muc_i_lay_theo_the_can_cuoc():
    result = _by_name(enrich(list(_HO_SO), None))

    assert result["QuanHe"]["value"] == "BanThan"
    assert result["SoDinhDanhC"]["value"] == "024068006368", "Số 10 chữ số của tờ khai là OCR hỏng"
    assert result["SoGiayToDinhDanhC"]["value"] == "024068006368"
    assert result["LoaiGiayToDinhDanhC"]["value"] == "Căn cước công dân"


def test_noi_cu_tru_van_uu_tien_to_khai():
    """Tờ khai viết hôm nay; thẻ có thể cấp từ nhiều năm trước, địa giới đã đổi."""
    result = _by_name(enrich(list(_HO_SO), None))

    assert result["nycNoiCuTru_TrongNuoc"]["value"]["diaChi"] == "Số 03, đường Lê Lợi, TDPDK"
    assert result["HoVaTenC"]["value"] == "Ngô Văn Tiến"


def test_khong_co_the_trong_ho_so_thi_van_dung_so_cua_to_khai():
    """Không có Subject_IdNumber (hồ sơ chỉ có tờ khai) → tờ khai vẫn là nguồn, không rỗng ô."""
    fields = [f for f in _HO_SO if not f["name"].startswith("Subject_Id")]
    fields = [f for f in fields if f["name"] != "Requester_IdNumber"]
    fields.append({"name": "Requester_IdNumber", "value": "024068006368"})
    result = _by_name(enrich(fields, None))

    assert result["SoDinhDanhC"]["value"] == "024068006368"


def test_so_sai_do_dai_khong_duoc_dien_khi_khong_co_the_de_doi_chieu():
    """Agent bỏ Subject_IdNumber → không còn gì để đảo ưu tiên; số 10 chữ số vẫn không được lọt.

    Số định danh chỉ có 9 (CMND) hoặc 12 chữ số. Ô đỏ để người dùng gõ lại còn hơn một con số
    sai độ dài trông y như số thật — cổng cũng chặn, nhưng người soát hồ sơ thì không.
    """
    fields = [f for f in _HO_SO if not f["name"].startswith("Subject_Id")]
    result = _by_name(enrich(fields, None))

    assert "SoDinhDanhC" not in result
    assert "SoGiayToDinhDanhC" not in result
    assert "LoaiGiayToDinhDanhC" not in result
    assert result["HoVaTenC"]["value"] == "Ngô Văn Tiến", "Các ô còn lại vẫn phải điền"


def test_so_ho_chieu_co_chu_khong_bi_luat_do_dai_chan():
    """Giấy tờ nước ngoài không có luật độ dài nào để áp → cho qua nguyên văn."""
    fields = [f for f in _HO_SO if not f["name"].startswith("Subject_Id")]
    fields = [f for f in fields if f["name"] != "Requester_IdNumber"]
    fields.append({"name": "Requester_IdNumber", "value": "EN7660049"})
    result = _by_name(enrich(fields, None))

    assert result["SoDinhDanhC"]["value"] == "EN7660049"


def test_quan_he_cha_me_giu_nguyen_uu_tien_to_khai():
    """Chỉ ca "Bản thân" mới đảo ưu tiên: thẻ trong hồ sơ lúc đó chắc chắn của chính người yêu cầu."""
    fields = [f for f in _HO_SO if f["name"] not in ("Requester_RelationToSubject", "Requester_FullName", "Requester_IdNumber")]
    fields += [
        {"name": "Requester_RelationToSubject", "value": "Mẹ"},
        {"name": "Requester_FullName", "value": "Nguyễn Thị Tín"},
        {"name": "Requester_IdNumber", "value": "024199009999"},   # khác số trên CCCD của mẹ
    ]
    result = _by_name(enrich(fields, None))

    assert result["QuanHe"]["value"] == "MeDe"
    assert result["SoDinhDanhC"]["value"] == "024199009999", "Ca cha/mẹ giữ nguyên hành vi cũ"


def test_quan_he_cha_me_so_hong_thi_lay_bu_tu_the_cua_chinh_vai_do():
    """Tờ khai ghi số mẹ bị OCR rụng chữ số → lấy bù từ CCCD của CHÍNH mẹ, không để trống."""
    fields = [f for f in _HO_SO if f["name"] not in ("Requester_RelationToSubject", "Requester_FullName", "Requester_IdNumber")]
    fields += [
        {"name": "Requester_RelationToSubject", "value": "Mẹ"},
        {"name": "Requester_FullName", "value": "Nguyễn Thị Tín"},
        {"name": "Requester_IdNumber", "value": "0241390028"},     # 10 chữ số — OCR hỏng
    ]
    result = _by_name(enrich(fields, None))

    assert result["SoDinhDanhC"]["value"] == "024139002897"


def test_tick_ban_than_nhung_ten_khac_han_thi_khong_muon_the():
    """Ô quan hệ tick nhầm: không được ghép số định danh của người khác vào mục I."""
    fields = [f for f in _HO_SO if f["name"] not in ("Requester_FullName", "Requester_IdNumber")]
    fields += [
        {"name": "Requester_FullName", "value": "Lương Thị Chính"},
        {"name": "Requester_IdNumber", "value": "024169007777"},
    ]
    result = _by_name(enrich(fields, None))

    assert result["SoDinhDanhC"]["value"] == "024169007777"


def test_tick_ban_than_sai_nguoi_va_so_hong_thi_de_trong_chu_khong_muon():
    """Vừa tick nhầm vừa OCR hỏng số: để trống, TUYỆT ĐỐI không mượn số của người được cấp."""
    fields = [f for f in _HO_SO if f["name"] != "Requester_FullName"]
    fields.append({"name": "Requester_FullName", "value": "Lương Thị Chính"})
    result = _by_name(enrich(fields, None))

    assert "SoDinhDanhC" not in result
    assert result["HoVaTenC"]["value"] == "Lương Thị Chính"
