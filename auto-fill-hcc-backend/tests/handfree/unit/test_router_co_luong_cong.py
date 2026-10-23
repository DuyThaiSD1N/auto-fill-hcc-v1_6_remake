"""Router giữ cờ năng lực của luồng cổng (liên thông, Bộ Xây dựng) và trả cờ cho sidebar — đi qua đúng hàm của router
(test luồng gán capability thẳng vào hội thoại nên không bắt được khi merge làm rơi các dòng này)."""
from app.channels.handfree.chat import flow, router, store


def test_giu_co_lien_thong_va_bo_xay_dung_extension_gui_len():
    caps = router._clean_client_capabilities({"supportsLienThongFlow": True, "supportsBxdFlow": True})
    assert caps["supportsLienThongFlow"] is True
    assert caps["supportsBxdFlow"] is True
    old = router._clean_client_capabilities({})
    assert old["supportsLienThongFlow"] is False and old["supportsBxdFlow"] is False


def _payload(key, caps):
    conv = store.new_conversation()
    conv.update({"procedure_key": key, "client_capabilities": caps})
    return router._serialize(conv, flow.Reply())


def test_tra_co_luong_cong_cho_sidebar_bao_doi_buoc():
    gpxd = _payload("cap-giay-phep-xay-dung-moi-nha-o-rieng-le", {"supportsBxdFlow": True})
    assert gpxd["bxd"] is True and gpxd["lien_thong"] is False
    lt = _payload("khai-sinh-dang-ky", {"supportsLienThongFlow": True})
    assert lt["lien_thong"] is True and lt["bxd"] is False
    old = _payload("cap-giay-phep-xay-dung-moi-nha-o-rieng-le", {})
    assert old["bxd"] is False
