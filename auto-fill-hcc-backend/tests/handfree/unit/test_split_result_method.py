"""Tách nhiều hồ sơ: lệnh đính kèm gửi kèm cách nhận kết quả mặc định cho các tab tách.

Hồ sơ chính được sidebar gạt công tắc "bản giấy có đóng dấu" theo lệnh select_result_method của
BE. Các tab tách chạy khung hồ sơ phụ CHỈ ĐỌC — không nói chuyện với BE nên không bao giờ nhận
lệnh đó; trước đây từ hồ sơ thứ 2 trở đi không ai gạt. Nay BE gửi sẵn lệnh gạt trong attach_plan
để khung phụ tự gạt trên chính trang của nó.
"""
from app.channels.handfree.chat import flow

KEY = "chung-thuc-ban-sao"
RESULT_CLIENT = {"supportsResultMethod": True, "supportsGuidedSteps": True}


def _conv(mode, caps=RESULT_CLIENT, key=KEY):
    return {
        "_id": "t-split-kq", "procedure_key": key, "attach_mode": mode,
        "client_capabilities": dict(caps), "upload_session_id": "sid",
    }


def test_tach_ho_so_gui_kem_lenh_gat_ban_giay():
    action = flow._attach_plan_action(_conv("split"), [])
    rm = action["resultMethod"]
    assert rm["type"] == "select_result_method"
    assert rm["method"] == "paper" and rm["label"] == "Nhận kết quả bản giấy có đóng dấu"
    assert set(rm["allLabels"]) == {
        "Nhận kết quả bản giấy có đóng dấu", "Nhận kết quả trực tuyến", "Dịch vụ bưu chính công ích",
    }, "phải kèm nhãn cả ba công tắc để FE tắt cái đang bật"
    assert rm["needsInput"] is False


def test_gop_mot_ho_so_khong_gui_kem():
    """Một hồ sơ thì sidebar chính tự gạt ở bước 4 như cũ — không có tab tách nào cần."""
    assert "resultMethod" not in flow._attach_plan_action(_conv("merge"), [])


def test_extension_chua_co_engine_gat_thi_khong_gui():
    action = flow._attach_plan_action(_conv("split", caps={"supportsGuidedSteps": True}), [])
    assert "resultMethod" not in action


def test_thu_tuc_khong_co_cach_nhan_ket_qua_thi_khong_gui():
    action = flow._attach_plan_action(_conv("split", key="chung-thuc-chu-ky"), [])
    assert "resultMethod" not in action


def test_gui_kem_danh_sach_de_khung_phu_ve_card():
    """Khung phụ không hỏi BE nên phải có sẵn cả danh sách để vẽ card 3 lựa chọn."""
    options = flow._attach_plan_action(_conv("split"), [])["resultMethod"]["options"]
    assert [o["key"] for o in options] == ["paper", "online", "postal"]
    assert all(o["label"] and o["icon"] and o["desc"] for o in options)
    assert [o["needsInput"] for o in options] == [False, False, True], "chỉ bưu chính cần điền thêm"
