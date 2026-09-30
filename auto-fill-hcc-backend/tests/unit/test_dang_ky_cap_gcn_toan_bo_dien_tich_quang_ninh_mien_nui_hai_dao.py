"""Unit test planner "[Quảng Ninh] Đăng ký, cấp GCN toàn bộ diện tích đất đang sử dụng (khoản 2 Điều 24
NĐ 101/2024) - Miền núi, hải đảo" (attach-only, 1.115841). Dữ liệu trong test là dữ liệu bịa."""

from app.pipelines.dang_ky_cap_gcn_toan_bo_dien_tich_quang_ninh_mien_nui_hai_dao.attach import planner
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_procedure

_KEY = "dang-ky-cap-gcn-toan-bo-dien-tich-dang-su-dung-quang-ninh"

_DON = (
    "Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất. Kính gửi: Chủ tịch UBND đặc khu "
    "Cô Tô. Tên: Ông NGUYỄN VĂN AN; Bà TRẦN THỊ BÌNH. II. Nội dung biến động: Đăng ký, cấp giấy chứng "
    "nhận QSD đất đối với thửa đất có phần diện tích đất tăng thêm do thay đổi ranh giới so với Giấy chứng "
    "nhận đã cấp có số seri X 123456; - Đăng ký bổ sung tài sản gắn liền với đất đã được cấp giấy chứng "
    "nhận QSD đất. IV. (1) Bản gốc Giấy chứng nhận đã cấp; (2) Phiếu đo đạc chỉnh lý thửa đất; Phiếu xác "
    "nhận kết quả đo đạc hiện trạng thửa đất; Bản mô tả ranh giới, mốc giới thửa đất"
)
_GCN = (
    "NHỮNG THAY ĐỔI SAU KHI CẤP GIẤY CHỨNG NHẬN. GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT Số X 123456. "
    "CHỨNG NHẬN Ông: Nguyễn Văn An. Được quyền sử dụng 500,00 m2 đất. SƠ ĐỒ ĐẤT CẤP"
)
_PHIEU = (
    "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT 1. Thửa đất số: 12 ; Tờ bản đồ số: 7 ; Diện tích: 612.5 m2 ; "
    "5. Giấy tờ pháp lý về quyền sử dụng đất: Giấy chứng nhận QSD đất số seri X 123456, số vào sổ 9; "
    "- Diện tích trên giấy tờ: 500.0 m2; 7. Diện tích sau đo đạc, chỉnh lý: 612.5 m2. "
    "PHIẾU XÁC NHẬN KẾT QUẢ ĐO ĐẠC HIỆN TRẠNG THỬA ĐẤT. BẢN MÔ TẢ RANH GIỚI, MỐC GIỚI THỬA ĐẤT. "
    "NHỮNG THAY ĐỔI SAU KHI CẤP GIẤY CHỨNG NHẬN. ĐƠN XIN ĐĂNG KÝ QUYỀN SỬ DỤNG ĐẤT. "
    "V/v xác nhận thông tin về nhà ở của bà Trần Thị Bình"
)


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def test_bo_ho_so_mau_ba_file_vao_dung_ba_dong():
    """Tên file 'đơn cấp đổi' nhưng nội dung Mẫu 18 → dòng 1; phiếu đo đạc gộp nhiều giấy tờ → dòng 3."""
    names = ["DON CAP DOI.pdf", "GCN.pdf", "PHIEU DO DAC CHINH LY.pdf"]
    ocr = [{"name": n, "text": t} for n, t in zip(names, [_DON, _GCN, _PHIEU])]

    attachments, warnings, _ = planner.build_plan_items(_files(names), ocr)

    assert [(a["detectedType"], a["componentIndex"], a["target"]) for a in attachments] == [
        ("don_mau_18", 1, "existing"),
        ("gcn_da_cap", 2, "existing"),
        ("giay_to_dien_tich_tang_them", 3, "existing"),
    ]
    assert attachments[2]["componentName"] == "Giấy tờ chứng minh phần diện tích tăng thêm"
    assert len(warnings) == 1
    note = warnings[0]
    assert note.startswith("Ghi chú (Trích yếu nội dung hồ sơ) đề xuất:")
    assert "thửa đất số 12, tờ bản đồ số 7" in note
    assert "500,0 m² → 612,5 m², tăng 112,5 m²" in note
    assert "số seri X 123456" in note
    assert "đăng ký bổ sung tài sản gắn liền với đất" in note
    for bundled in ("bản photo Giấy chứng nhận", "đơn đăng ký quyền sử dụng đất cũ", "xác nhận về nhà ở"):
        assert bundled in note


def test_llm_uu_tien_hon_rule():
    names = ["a.pdf"]
    ocr = [{"name": "a.pdf", "text": _PHIEU}]
    attachments, _, classified = planner.build_plan_items(_files(names), ocr, {0: "gcn_da_cap"})
    assert attachments[0]["componentIndex"] == 2
    assert classified[0]["source"] == "llm"


def test_to_khai_vao_dong_4_5_6():
    names = ["lptb.pdf", "pnn.pdf", "tncn.pdf"]
    ocr = [
        {"name": "lptb.pdf", "text": "TỜ KHAI LỆ PHÍ TRƯỚC BẠ Mẫu số 01/LPTB"},
        {"name": "pnn.pdf", "text": "TỜ KHAI THUẾ SỬ DỤNG ĐẤT PHI NÔNG NGHIỆP 04/TK-SDDPNN"},
        {"name": "tncn.pdf", "text": "TỜ KHAI THUẾ THU NHẬP CÁ NHÂN 03/BĐS-TNCN"},
    ]
    attachments, warnings, _ = planner.build_plan_items(_files(names), ocr)
    assert [a["componentIndex"] for a in attachments] == [4, 5, 6]
    # Thiếu Đơn và GCN (hai dòng bắt buộc) → nhắc bổ sung.
    assert sum("mời bổ sung" in w for w in warnings) == 2


def test_uy_quyen_tai_san_va_giay_la_them_thanh_phan_moi():
    names = ["uy quyen.pdf", "nha o.pdf", "CONG VAN LA.pdf"]
    ocr = [
        {"name": "uy quyen.pdf", "text": "GIẤY ỦY QUYỀN"},
        {"name": "nha o.pdf", "text": "V/v xác nhận thông tin về nhà ở của hộ gia đình"},
        {"name": "CONG VAN LA.pdf", "text": "MỘT VĂN BẢN KHÔNG LIÊN QUAN"},
    ]
    attachments, _, _ = planner.build_plan_items(_files(names), ocr)
    assert [a["detectedType"] for a in attachments] == ["van_ban_dai_dien", "giay_to_tai_san", "other"]
    assert all(a["target"] == "new" and a["needsAddComponent"] for a in attachments)
    assert attachments[2]["componentName"] == "CONG VAN LA"


def test_khong_bo_sot_file_khi_khong_co_ocr():
    attachments, _, _ = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), [])
    assert [a["fileIndex"] for a in attachments] == [0, 1]


def test_registry_wires_attach_only():
    proc = get_procedure(_KEY)
    assert proc is not None
    assert proc["mode"] == "attach"
    assert get_attach_pipeline(_KEY) is not None


def _matches(entry: dict, text: str) -> int:
    """Mô phỏng nhánh textPriority của popup.js: khớp đủ mọi cụm → điểm = tổng độ dài cụm."""
    detect = entry.get("detect") or {}
    phrases = [p.lower() for p in detect.get("textIncludes") or []]
    if not phrases or not all(p in text for p in phrases):
        return 0
    return sum(len(p) for p in phrases)


def test_nhan_dien_khong_tranh_trang_quang_ninh_khac():
    page = (
        "[đặc thù] thủ tục đăng ký, cấp giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với "
        "đất đối với toàn bộ diện tích đất đang sử dụng quy định tại khoản 2 điều 24 nghị định số "
        "101/2024/nđ-cp - miền núi, hải đảo"
    )
    scoped = [p for p in PROCEDURES if "dichvucong.quangninh.gov.vn" in (p.get("detect") or {}).get("urlScope", [])]
    scores = {p["key"]: _matches(p, page) for p in scoped}
    assert max(scores, key=scores.get) == _KEY
    assert [k for k, v in scores.items() if v] == [_KEY]
