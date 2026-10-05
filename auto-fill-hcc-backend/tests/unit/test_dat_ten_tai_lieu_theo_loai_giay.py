"""Tên tài liệu theo loại giấy cho các planner trước đây giữ tên tệp gốc (engine FE đặt tên tệp tải lên
theo documentName; cài đặt tài khoản tắt "đổi tên tệp" thì FE tự giữ tên gốc).

Chung cho mọi planner: loại đã nhận diện → tên theo loại; cùng loại trong một dòng → đánh số; giấy chưa biết
loại → giữ tên gốc (không bịa tên chung); tên không chứa "/" (trình duyệt/cổng coi là đường dẫn).
"""
from app.pipelines.cap_lai_CCHN_thu_y.attach import planner as cchn_cap_lai
from app.pipelines.cap_van_ban_chap_thuan_tau_ca.attach import planner as tau_ca
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.attach import planner as gia_han
from app.pipelines.tro_cap_xa_hoi_hang_thang.attach import planner as tro_cap


def _files(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def test_cap_lai_cchn_thu_y_dat_ten_cchn_cu_va_anh_the():
    llm = {0: "don_cap_lai", 1: "cchn_cu", 2: "anh_the", 3: "anh_the", 4: "other"}
    items, _, _ = cchn_cap_lai.build_plan_items(_files("a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"), [], llm)
    names = [item["documentName"] for item in items]
    assert names[1:] == ["Chứng chỉ hành nghề thú y đã cấp", "Ảnh chân dung 4x6", "Ảnh chân dung 4x6 2", "e.pdf"]


def test_tau_ca_dat_ten_cccd():
    llm = {0: "to_khai", 1: "cccd", 2: "cccd", 3: "other"}
    items, _, _ = tau_ca.build_plan_items(_files("a.pdf", "b.pdf", "c.pdf", "d.pdf"), [], llm)
    assert [item["documentName"] for item in items][1:] == ["Căn cước công dân", "Căn cước công dân 2", "d.pdf"]


def test_gia_han_cchn_thu_y_dat_ten_moi_loai_ke_ca_van_bang():
    llm = {0: "don_gia_han", 1: "gksk", 2: "van_bang", 3: "cchn_cu", 4: "other"}
    items, _, _ = gia_han.build_plan_items(_files("a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"), [], llm)
    by_index = {item["fileIndex"]: item for item in items}
    assert by_index[0]["documentName"] == "Đơn đăng ký gia hạn Chứng chỉ hành nghề thú y"
    assert by_index[1]["documentName"] == "Giấy chứng nhận sức khỏe"
    assert by_index[2]["documentName"] == "Văn bằng chuyên môn"
    assert by_index[2]["target"] == "add-document-dialog"
    assert by_index[3]["documentName"] == "Chứng chỉ hành nghề thú y đã cấp"
    assert by_index[4]["documentName"] == "e.pdf"
    assert all(len(item["documentName"]) <= 50 for item in items)


def test_tro_cap_xa_hoi_ten_khong_co_dau_gach_cheo_va_danh_so():
    llm = {0: tro_cap._TK_DOITUONG, 1: tro_cap._CU_TRU_CCCD, 2: tro_cap._CU_TRU_CCCD}
    items, _, _ = tro_cap.build_plan_items(_files("a.pdf", "b.pdf", "c.pdf"), [], llm)
    names = [item["documentName"] for item in items]
    assert all("/" not in name for name in names)
    assert names[2] == f"{names[1]} 2"
