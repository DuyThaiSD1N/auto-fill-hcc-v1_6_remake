"""Unit test attach planner "Đăng ký đất đai lần đầu" (Đà Nẵng).

Trọng tâm: bộ hồ sơ GỘP nhiều giấy tờ trong 1 file mà CÓ Đơn đăng ký Mẫu 15 → LUÔN route vào thành phần
chính "Đơn đăng ký đất đai" (bắt buộc), KHÔNG phân loại nhầm theo tờ khai thuế ở trang đầu."""

from app.pipelines.dang_ky_dat_dai_lan_dau_da_nang.attach import planner as P


def _detect(text: str, llm_type: str) -> tuple[str, str, str]:
    items, _, cls = P.build_plan_items([{"name": "f.pdf"}], [{"name": "f.pdf", "text": text}], {0: llm_type})
    if not items:
        return "", "", cls[0]["source"]
    return items[0]["detectedType"], items[0]["componentName"], cls[0]["source"]


_BUNDLE = (
    "TỜ KHAI THUẾ THU NHẬP CÁ NHÂN\n"
    "... nghĩa vụ tài chính ...\n"
    "ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n"
    "Mẫu số 15\n"
    "MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH thửa đất số 54\n"
)


def test_bundle_co_don_m15_uu_tien_don():
    # Dù LLM lỡ đoán cả bộ là 'nghia_vu_tai_chinh' (vì trang đầu là tờ khai thuế) → override về don_m15.
    dt, comp, source = _detect(_BUNDLE, "nghia_vu_tai_chinh")
    assert dt == "don_m15"
    assert comp == "Đơn đăng ký đất đai"
    assert source == "priority-don-m15"


def test_bundle_llm_khac_van_uu_tien_don():
    dt, _, _ = _detect(_BUNDLE, "ho_so_do_dac")
    assert dt == "don_m15"


def test_chi_to_khai_thue_khong_co_don_van_la_nghia_vu_tai_chinh():
    dt, _, source = _detect("TỜ KHAI THUẾ THU NHẬP CÁ NHÂN\nnghĩa vụ tài chính về đất", "nghia_vu_tai_chinh")
    assert dt == "nghia_vu_tai_chinh"
    assert source == "llm"


def test_chi_trich_do_khong_bi_override():
    dt, _, _ = _detect("MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH thửa đất số 54", "ho_so_do_dac")
    assert dt == "ho_so_do_dac"


def test_don_m15_rieng_le_van_dung():
    dt, comp, _ = _detect("ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\nMẫu số 15", "don_m15")
    assert dt == "don_m15"
    assert comp == "Đơn đăng ký đất đai"
