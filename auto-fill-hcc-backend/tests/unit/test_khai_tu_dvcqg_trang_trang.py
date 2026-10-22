"""Khai tử (Cổng DVC quốc gia mới), tách giấy: trang LLM gọi "trắng" mà OCR có chữ (ảnh bia mộ) không bị bỏ."""
from app.pipelines.khai_tu_dvcqg.attach.dinh_kem_tach.planner import _segments

_PAGES = ["TỜ KHAI ĐĂNG KÝ KHAI TỬ", "BIÊN BẢN XÁC MINH", "MỘ THỊ\nBÀ NGUYỄN THỊ A", "  .  \n- 3 -  "]


def test_trang_co_chu_bi_goi_trang_van_giu_lai():
    docs = [{"fileIndex": 0, "pages": [1], "docType": "other"},
            {"fileIndex": 0, "pages": [2], "docType": "death_event_proof"},
            {"fileIndex": 0, "pages": [3], "docType": "blank_page"},
            {"fileIndex": 0, "pages": [4], "docType": "blank_page"}]
    segs = _segments({0: _PAGES}, docs)
    assert [(s["pages"], s["doc"].get("docType")) for s in segs] == [([0], "other"), ([1], "death_event_proof"),
                                                                    ([2], "other")]
