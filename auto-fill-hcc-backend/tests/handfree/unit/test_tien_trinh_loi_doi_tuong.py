"""Thanh "Bước X/Y" theo chặng, lỗi kỹ thuật không lộ ra câu thoại, đối tượng thực hiện theo thủ tục."""
from app.channels.handfree.chat import flow
from app.channels.handfree.chat import script_vi as vi


def test_buoc_dem_theo_chang_khong_nhay_coc():
    steps = [flow.build_progress({"state": s})["step"] for s in
             ("greet", "guide_login", "consent", "collecting_docs", "filling", "attaching", "done")]
    assert steps == [1, 2, 3, 3, 4, 5, 5]
    assert flow.build_progress({"state": "filling"})["total"] == len(vi.STEP_PHASES) == 5
    assert {s for phase in vi.STEP_PHASES for s in phase} == set(vi.STEP_ORDER), "mọi trạng thái đều thuộc một chặng"


def test_loi_ky_thuat_doi_thanh_cau_chung_loi_tieng_viet_cat_gon():
    assert flow._short_error("HTTPStatusError: 500 Internal Server Error") == "lỗi kỹ thuật"
    assert flow._short_error("ReadTimeout('timed out')") == "máy chủ xử lý quá lâu"
    assert flow._short_error("Không thấy nút Lưu trên trang") == "Không thấy nút Lưu trên trang"
    long = flow._short_error("Cổng báo " + "lỗi dài " * 30)
    assert len(long) <= 81 and long.endswith("…")
    md, _ = flow._fmt(vi.PIPELINE_ERROR, error="KeyError: 'fields'")
    assert "KeyError" not in md and "lỗi kỹ thuật" in md


def test_ket_hon_khong_hien_doanh_nghiep_va_to_chuc():
    keys = [o["key"] for o in flow._location_card({"procedure_key": "ket-hon"})["executionSubject"]["options"]]
    assert keys == ["self", "authorized_person", "other_person"]
    assert flow._apply_execution_subject({"procedure_key": "ket-hon"}, {"key": "enterprise_authorized"}).display_md == ""
    other = [o["key"] for o in flow._location_card({"procedure_key": "xac-nhan-tinh-trang-hon-nhan"})
             ["executionSubject"]["options"]]
    assert "enterprise_authorized" in other, "thủ tục khác giữ nguyên danh sách"
