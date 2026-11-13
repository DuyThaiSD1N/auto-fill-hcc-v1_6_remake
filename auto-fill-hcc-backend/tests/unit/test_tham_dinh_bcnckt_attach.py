"""Dòng thành phần hồ sơ "Thẩm định BCNCKT" (dvc.moc) theo NĐ 217/2026: componentName phải là đoạn con (fold)
của tên dòng trên cổng; giấy không còn dòng riêng (ĐTM, nhà thầu) vẫn có item ở dòng Tờ trình.

Cuối file: địa chỉ/SĐT của nhà thầu (mục "Hồ sơ năng lực của các nhà thầu") không được điền vào chủ đầu tư."""

import pytest

from app.pipelines._shared import fold
from app.pipelines.tham_dinh_bcnckt.attach import planner
from app.pipelines.tham_dinh_bcnckt.process import mapper
from app.pipelines.tham_dinh_bcnckt.process import runner as process_runner

# Tên dòng nguyên văn trên cổng (bảng 15 dòng).
_PORTAL_ROWS = [
    "Tờ trình thẩm định theo quy định tại Mẫu số 01 Phụ lục I ban hành kèm theo Nghị định số 217/2026/NĐ-CP",
    "Văn bản về chủ trương đầu tư xây dựng dự án hoặc văn bản phê duyệt thông tin dự án hoặc quyết định phê duyệt "
    "Đề án du lịch sinh thái, nghỉ dưỡng, giải trí trong rừng",
    "Giấy phép đầu tư, Giấy chứng nhận ưu đãi đầu tư, Giấy chứng nhận đầu tư, Giấy chứng nhận đăng ký đầu tư",
    "Văn bản chấp thuận/quyết định phê duyệt và các bản vẽ quy hoạch có liên quan của quy hoạch sử dụng làm căn cứ "
    "lập dự án theo quy định tại Điều 26 Nghị định số 217/2026/NĐ-CP",
    "Các văn bản thỏa thuận, xác nhận về đấu nối hạ tầng kỹ thuật của dự án; văn bản chấp thuận độ cao công trình",
    "Hồ sơ khảo sát xây dựng được phê duyệt;",
    "Báo cáo nghiên cứu khả thi (gồm thuyết minh và hồ sơ thiết kế xây dựng được lập tại Báo cáo nghiên cứu khả "
    "thi); Báo cáo kết quả thẩm tra thiết kế xây dựng theo Mẫu số 02 Phụ lục I",
]


@pytest.mark.parametrize("doc_type", sorted(planner._ROWS))
def test_component_name_khop_dong_tren_cong(doc_type):
    needle = fold(planner._ROWS[doc_type]["componentName"])
    assert sum(needle in fold(row) for row in _PORTAL_ROWS) == 1


@pytest.mark.parametrize("doc_type", ["moi_truong", "nha_thau"])
def test_giay_khong_con_dong_rieng_dinh_chung_dong_to_trinh(doc_type):
    files = [{"name": "a.pdf", "type": "application/pdf"}]
    items, warnings, classified = planner.build_plan_items(files, [], {0: doc_type})
    assert items[0]["componentName"] == planner._ROWS["to_trinh"]["componentName"]
    assert items[0]["documentName"] == planner._NO_ROW_NAMES[doc_type]
    assert classified[0]["routedTo"] == "to_trinh"
    assert any("a.pdf" in w for w in warnings)


def test_bao_cao_nckt_co_dong_rieng():
    files = [{"name": "tm.pdf", "type": "application/pdf"}]
    items, warnings, _ = planner.build_plan_items(files, [], {0: "bao_cao_nckt"})
    assert items[0]["componentName"] == planner._ROWS["bao_cao_nckt"]["componentName"]
    assert warnings == []


# Tờ trình bịa: chỉ ghi TÊN chủ đầu tư; địa chỉ + SĐT duy nhất là của nhà thầu thiết kế.
_TO_TRINH_KHONG_DIA_CHI_CDT = """CÔNG TY CỔ PHẦN DỆT AN PHÚ
TỜ TRÌNH Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng
6. Tên chủ đầu tư: Công Ty Cổ phần Dệt An Phú.
7. Địa điểm xây dựng:
- Địa chỉ: Km 12, Quốc lộ 9, Phường Ví Dụ, tỉnh Khánh Hòa.
3.Hồ sơ năng lực của các nhà thầu:
a. Thông tin năng lực của nhà thầu lập dự án, thiết kế cơ sở:
Công ty TNHH MTV Kiến trúc Minh Họa:
- Địa chỉ: Số 5, Tầng 2, Tòa nhà Mẫu, đường Thử Nghiệm, Phường Ví Dụ, tỉnh Khánh Hòa;
- Điện thoại: 0912 345 678
"""

_CDT_NHAM_NHA_THAU = {
    "ChuDauTu_Ten": "Công Ty Cổ phần Dệt An Phú",
    "ChuDauTu_DiaChi": {"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Phường Ví Dụ",
                        "chiTietDuoiXa": "Số 5, Tầng 2, Tòa nhà Mẫu, đường Thử Nghiệm"},
    "ChuDauTu_DienThoai": "0912345678",
}


def _enrich(fields: dict):
    return mapper.enrich([{"name": k, "value": v} for k, v in fields.items()], {})


def test_dia_chi_sdt_nha_thau_khong_dien_vao_chu_dau_tu():
    docs = [{"name": "to-trinh.pdf", "text": _TO_TRINH_KHONG_DIA_CHI_CDT}]
    fields = process_runner.drop_contractor_contacts(dict(_CDT_NHAM_NHA_THAU), docs)
    assert "ChuDauTu_DiaChi" not in fields
    assert "ChuDauTu_DienThoai" not in fields
    assert fields["ChuDauTu_Ten"] == "Công Ty Cổ phần Dệt An Phú"

    out, warnings = _enrich(fields)
    names = {f["name"] for f in out}
    assert "data[organization]" in names and "data[chuDauTu]" in names
    for name in ("data[address1]", "data[district1]", "data[province1]", "data[diaChiChuDauTu]",
                 "data[organizationPhoneNumber]", "data[soDienThoaiChuDauTu]"):
        assert name not in names
    assert any("địa chỉ trụ sở chủ đầu tư" in w for w in warnings)


def test_dia_chi_chu_dau_tu_ghi_rieng_van_giu():
    text = _TO_TRINH_KHONG_DIA_CHI_CDT.replace(
        "6. Tên chủ đầu tư: Công Ty Cổ phần Dệt An Phú.",
        "6. Tên chủ đầu tư: Công Ty Cổ phần Dệt An Phú.\n- Địa chỉ: Số 1 đường Hoa Sen, Phường Ví Dụ, tỉnh Khánh Hòa"
        "\n- Điện thoại: 0987 654 321",
    )
    raw = {**_CDT_NHAM_NHA_THAU,
           "ChuDauTu_DiaChi": {"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Phường Ví Dụ",
                               "chiTietDuoiXa": "Số 1 đường Hoa Sen"},
           "ChuDauTu_DienThoai": "0987654321"}
    fields = process_runner.drop_contractor_contacts(raw, [{"name": "to-trinh.pdf", "text": text}])
    assert fields["ChuDauTu_DiaChi"]["chiTietDuoiXa"] == "Số 1 đường Hoa Sen"
    assert fields["ChuDauTu_DienThoai"] == "0987654321"


def test_chu_dau_tu_tu_lap_thiet_ke_giu_dia_chi():
    # Chủ đầu tư cũng là nhà thầu thiết kế: địa chỉ ghi dưới tên chính chủ đầu tư (viết tắt "CP") là của chủ đầu tư.
    text = _TO_TRINH_KHONG_DIA_CHI_CDT.replace("Công ty TNHH MTV Kiến trúc Minh Họa:", "Công ty CP Dệt An Phú:")
    fields = process_runner.drop_contractor_contacts(dict(_CDT_NHAM_NHA_THAU), [{"name": "a.pdf", "text": text}])
    assert fields["ChuDauTu_DiaChi"]["chiTietDuoiXa"] == "Số 5, Tầng 2, Tòa nhà Mẫu, đường Thử Nghiệm"
    assert fields["ChuDauTu_DienThoai"] == "0912345678"


# Tờ trình bịa: MST chủ đầu tư chỉ có ở "Văn bản pháp lý"; nhà thầu cũng ghi số GCN ĐKDN riêng.
_TO_TRINH_GCN = _TO_TRINH_KHONG_DIA_CHI_CDT.replace(
    "3.Hồ sơ năng lực của các nhà thầu:",
    "II-DANH MỤC HỒ SƠ GỬI KÈM BÁO CÁO:\n1.Văn bản pháp lý :\n"
    "- Giấy chứng nhận đăng ký doanh nghiệp số: 0312345678 Phòng đăng ký kinh doanh cấp thay đổi lần thứ 3.\n"
    "3.Hồ sơ năng lực của các nhà thầu:",
) + "- Giấy chứng nhận đăng ký doanh nghiệp số 0398765432 đăng ký lần đầu ngày 01/02/2015\n"


def test_mst_chu_dau_tu_lay_tu_gcn_dkdn_van_ban_phap_ly():
    docs = [{"name": "to-trinh.pdf", "text": _TO_TRINH_GCN}]
    # LLM bỏ MST → bù số GCN ngoài khối nhà thầu.
    fields = process_runner.drop_contractor_contacts({"ChuDauTu_Ten": "Công Ty Cổ phần Dệt An Phú"}, docs)
    assert fields["ChuDauTu_MaSoThue"] == "0312345678"
    # LLM lấy nhầm số GCN của nhà thầu → thay bằng số của chủ đầu tư.
    fields = process_runner.drop_contractor_contacts(
        {"ChuDauTu_Ten": "Công Ty Cổ phần Dệt An Phú", "ChuDauTu_MaSoThue": "0398765432"}, docs)
    assert fields["ChuDauTu_MaSoThue"] == "0312345678"
    # Không có GCN ngoài khối nhà thầu → không nhận số của nhà thầu.
    fields = process_runner.drop_contractor_contacts(
        {"ChuDauTu_Ten": "Công Ty Cổ phần Dệt An Phú", "ChuDauTu_MaSoThue": "0398765432"},
        [{"name": "to-trinh.pdf", "text": _TO_TRINH_GCN.replace("0312345678", "")}])
    assert "ChuDauTu_MaSoThue" not in fields

    out, _ = _enrich(fields | {"ChuDauTu_MaSoThue": "0312345678"})
    by_name = {f["name"]: f["value"] for f in out}
    assert by_name["data[taxCode]"] == "0312345678" and by_name["data[maChuDauTu]"] == "0312345678"


def test_khong_ghi_tru_so_tam_dien_theo_dia_diem_xay_dung():
    fields = {
        "ChuDauTu_Ten": "Công Ty Cổ phần Dệt An Phú",
        "DuAn_DiaDiem": {"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Phường Ví Dụ",
                         "diaChi": "Km 12, Quốc lộ 9, Thừa đất số 6, tờ bản đồ số 9"},
    }
    out, warnings = _enrich(fields)
    items = {(f["name"], f.get("occurrence")): f for f in out}
    assert items[("data[address1]", None)]["value"] == "Km 12, Quốc lộ 9"
    assert items[("data[province1]", None)]["value"] == "Tỉnh Khánh Hòa"
    assert items[("data[district1]", None)]["value"] == "Phường Ví Dụ"
    for key in ("data[address1]", "data[province1]", "data[district1]", "data[diaChiChuDauTu]"):
        assert items[(key, None)].get("default") is True
    assert items[("data[diaChiChuDauTu]", None)]["value"] == "Km 12, Quốc lộ 9, Phường Ví Dụ, Khánh Hòa"
    # Khối địa điểm xây dựng (occ1) vẫn giữ nguyên văn, không gắn cờ.
    assert items[("data[address]", 1)]["value"] == "Km 12, Quốc lộ 9, Thừa đất số 6, tờ bản đồ số 9"
    assert not items[("data[address]", 1)].get("default")
    assert ("data[organizationPhoneNumber]", None) not in items
    assert any("theo địa điểm xây dựng" in w for w in warnings)

    # Tờ trình ghi trụ sở riêng → điền trụ sở, không gắn cờ.
    out, _ = _enrich(fields | {"ChuDauTu_DiaChi": {"tinh": "Khánh Hòa", "xa": "Phường Ví Dụ",
                                                    "diaChi": "Số 1 đường Hoa Sen"}})
    items = {(f["name"], f.get("occurrence")): f for f in out}
    assert items[("data[address1]", None)]["value"] == "Số 1 đường Hoa Sen"
    assert not items[("data[address1]", None)].get("default")
