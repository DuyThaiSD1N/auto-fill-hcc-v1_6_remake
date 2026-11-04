"""Dòng thành phần hồ sơ "Thẩm định BCNCKT" (dvc.moc) theo NĐ 217/2026: componentName phải là đoạn con (fold)
của tên dòng trên cổng; giấy không còn dòng riêng (ĐTM, nhà thầu) vẫn có item ở dòng Tờ trình."""

import pytest

from app.pipelines._shared import fold
from app.pipelines.tham_dinh_bcnckt.attach import planner

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
