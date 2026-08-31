"""Phân loại tài liệu đính kèm cho thủ tục thành lập công ty TNHH hai thành viên trở lên.

Route theo OCR là TẤT ĐỊNH (LLM chỉ là lưới đỡ), nên phần dễ sai nhất là THỨ TỰ xét marker: nhiều
loại giấy trong hồ sơ này chứa lẫn dấu hiệu của nhau — nặng nhất là cặp "Danh sách thành viên" và
"Danh sách chủ sở hữu hưởng lợi" (gần như trùng cột).
"""

from app.pipelines.thanh_lap_ctythnn_2_nguoi.attach import planner


def test_giay_de_nghi_thang_moi_loai_khac():
    """Giấy đề nghị cũng có bảng nguồn vốn + số định danh cá nhân -> phải xét TRƯỚC các loại kia."""
    text = (
        "GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP CÔNG TY TNHH HAI THÀNH VIÊN TRỞ LÊN "
        "Danh sách thành viên kèm theo. Số định danh cá nhân: 049197013201. "
        "Căn cước công dân của người đại diện theo pháp luật."
    )
    assert planner._detect_category(text) == planner._CAT_BUSREG


def test_dieu_le_khong_bi_nham_thanh_danh_sach_thanh_vien():
    """Điều lệ cũng liệt kê thành viên; dấu hiệu chắc chắn là cấu trúc "Chương"/"Điều"."""
    text = "ĐIỀU LỆ CÔNG TY TNHH DỊCH VỤ VẬN TẢI. Chương I. Điều 1. Danh sách thành viên gồm..."
    assert planner._detect_category(text) == planner._CAT_CHARTER


def test_danh_sach_thanh_vien():
    text = "DANH SÁCH THÀNH VIÊN CÔNG TY TNHH HAI THÀNH VIÊN TRỞ LÊN. Phần vốn góp. Tỷ lệ (%)."
    assert planner._detect_category(text) == planner._CAT_MEMBERS


def test_chu_so_huu_huong_loi_khong_bi_nham_sang_danh_sach_thanh_vien():
    """Hai bảng gần trùng cột; giấy CSH hưởng lợi cũng nhắc chữ 'thành viên' ở phần chú thích."""
    text = (
        "DANH SÁCH CHỦ SỞ HỮU HƯỞNG LỢI CỦA DOANH NGHIỆP. "
        "Tỷ lệ sở hữu vốn điều lệ: 50%. Ghi chú: Trực tiếp. Là thành viên góp vốn của công ty."
    )
    assert planner._detect_category(text) == planner._CAT_BENEFICIAL


def test_uy_quyen_thang_giay_to_ca_nhan():
    """Giấy ủy quyền luôn kèm số CCCD hai bên -> phải xét ủy quyền TRƯỚC giấy tờ cá nhân."""
    text = "GIẤY ỦY QUYỀN. Bên ủy quyền: ... Căn cước công dân số 049197013201. Bên được ủy quyền: ..."
    assert planner._detect_category(text) == planner._CAT_AUTH


def test_can_cuoc_cong_dan():
    assert planner._detect_category("CỘNG HÒA... CĂN CƯỚC CÔNG DÂN. Số: 052176015320") == planner._CAT_CPID


def test_ocr_rong_hoac_khong_ro_thi_nhuong_llm():
    assert planner._detect_category("") is None
    assert planner._detect_category("hóa đơn tiền điện tháng 8") is None


def test_nhan_hien_thi_phu_kin_moi_category():
    """Extension khớp option trên cổng theo NHÃN, nên mọi category đều phải có nhãn."""
    for category in (planner._CAT_BUSREG, planner._CAT_CHARTER, planner._CAT_MEMBERS,
                     planner._CAT_BENEFICIAL, planner._CAT_CPID, planner._CAT_AUTH,
                     planner._CAT_OTHERS):
        assert planner._LABEL_BY_CAT[category].strip()


def test_moi_type_cua_llm_deu_map_duoc_sang_category_co_nhan():
    for kind, category in planner._LLM_TO_CAT.items():
        assert category in planner._LABEL_BY_CAT, kind


def test_ten_tai_lieu_trung_thi_phai_tach_ra():
    """Cùng loại giấy tờ (vd 2 CCCD) không được trùng documentName — cổng dùng tên để phân biệt dòng."""
    used: set[str] = set()
    first = planner._unique_document_name("Căn cước công dân", used, "Khác")
    second = planner._unique_document_name("Căn cước công dân", used, "Khác")
    assert first != second
