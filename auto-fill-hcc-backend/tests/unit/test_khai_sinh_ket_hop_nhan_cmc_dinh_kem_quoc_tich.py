"""Khai sinh kết hợp nhận cha, mẹ, con: thỏa thuận quốc tịch và hộ chiếu người nước ngoài vào đúng dòng có sẵn của cổng."""
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.attach import planner

# Nguyên văn hai dòng thành phần trên cổng (extension khớp dòng bằng chuỗi con đã bỏ dấu).
_ROW_QUOC_TICH = ("- Trường hợp cha hoặc mẹ hoặc cả cha, mẹ là người nước ngoài thì phải nộp văn bản thỏa thuận của cha, "
                  "mẹ về việc lựa chọn quốc tịch cho con.")
_ROW_HO_CHIEU = ("- Trường hợp đăng ký nhận cha, mẹ, con giữa công dân Việt Nam với người nước ngoài hoặc giữa người "
                 "nước ngoài với nhau thì người nước ngoài phải nộp bản sao hộ chiếu hoặc giấy tờ có giá trị thay hộ "
                 "chiếu để chứng minh về nhân thân.")


def _plan(llm_types):
    files = [{"name": "a.pdf"}, {"name": "b.pdf"}]
    ocr_results = [{"name": "a.pdf", "text": "PASSPORT"}, {"name": "b.pdf", "text": "VĂN BẢN THỎA THUẬN"}]
    attachments, _ = planner.build_plan_items(files, ocr_results, llm_types)
    return attachments


def test_thoa_thuan_quoc_tich_va_ho_chieu_nguoi_nuoc_ngoai_vao_dong_co_san():
    hc, tt = _plan({0: {"type": "foreign_passport", "documentName": "Hộ chiếu"},
                    1: {"type": "nationality_agreement", "documentName": "Văn bản thỏa thuận quốc tịch cho con"}})
    assert hc["target"] == tt["target"] == "existing"
    assert planner.fold(hc["componentName"]) in planner.fold(_ROW_HO_CHIEU)
    assert planner.fold(tt["componentName"]) in planner.fold(_ROW_QUOC_TICH)
    assert (hc["documentName"], tt["documentName"]) == ("Hộ chiếu", "Văn bản thỏa thuận quốc tịch cho con")


def test_giay_tuy_than_dat_ten_theo_llm_khong_goi_ho_chieu_la_can_cuoc():
    hc, _ = _plan({0: {"type": "identity", "documentName": "Hộ chiếu"}, 1: {"type": "other", "documentName": "Đơn"}})
    assert hc["documentName"] == "Hộ chiếu"
