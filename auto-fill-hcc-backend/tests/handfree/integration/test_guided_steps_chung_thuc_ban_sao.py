"""Luồng dẫn từng bước (guidedSteps) — thử nghiệm trên chứng thực bản sao.

Trợ lý đặt nút chuyển bước ngay trong khung chat và bấm hộ nút của cổng, thay vì để công dân
tự dò nút "Bước tiếp theo" ở cuối trang.

RÀNG BUỘC SỐNG CÒN: backend này còn phải phục vụ bản extension đang chạy ngoài chợ. Bản cũ
không khai `supportsGuidedSteps` → phải nhận ĐÚNG NGUYÊN VĂN câu thoại cũ, không chip, không
action lạ. Mọi test "client cũ" dưới đây là hàng rào cho điều đó.
"""
import pytest

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import flow
from app.channels.handfree.chat.flow import Intent

KEY = "chung-thuc-ban-sao"
NEW_CLIENT = {"supportsGuidedSteps": True}
OLD_CLIENT = {"supportsRating": True}  # bản trên chợ: có rating, chưa có guided steps


def _conv(caps=NEW_CLIENT, **kw):
    base = {
        "_id": "t-guided", "state": "guide_login", "history": [], "milestones": [],
        "procedure_key": KEY, "upload_session_id": "sid",
        "location": {"province": "Thành phố Hà Nội", "ward": "Phường Thanh Xuân"},
        "client_capabilities": dict(caps),
    }
    base.update(kw)
    return base


async def _owner_page(conv):
    """Cổng đang ở bước 1 Thông tin chủ hồ sơ."""
    return await flow.handle_turn(conv, Intent("event", "page_status", {
        "loggedIn": True, "wizardStep": 1,
    }))


# ── Bước Thông tin chủ hồ sơ ──────────────────────────────────────────────────────────────

async def test_client_cu_van_nhan_nguyen_van_cau_thoai_cu():
    conv = _conv(OLD_CLIENT)
    r = await _owner_page(conv)
    assert r.display_md == vi.OWNER_INFO_ATTACH_GUIDE["md"]
    assert not r.chips and not r.actions, "bản cũ không được nhận nút/lệnh của luồng mới"


async def test_client_moi_nhan_cau_moi_va_nut_chuyen_buoc():
    conv = _conv()
    r = await _owner_page(conv)
    assert "Thông tin chủ hồ sơ" in r.display_md
    assert "Thành phần hồ sơ" in r.display_md, "phải gọi đúng tên bước kế tiếp trên cổng"
    chip = r.chips[0]
    assert chip["send"] == "__action:guided_next" and chip["phase"] == "owner"
    assert chip["cta"] is True
    # Nút tự mang theo hợp đồng các ô cần đọc → FE không tự đoán selector. Bốn ô của khối
    # ủy quyền khai kèm luôn: trang tự làm không có ô nào khớp nên FE/BE tự bỏ qua.
    keys = [f["key"] for f in chip["fields"]]
    assert keys[:4] == ["issueDate", "issuePlace", "phoneNumber", "detailedAddress"]
    assert "relationship" in keys and "grantorFullName" in keys
    grantor = next(f for f in chip["fields"] if f["key"] == "grantorFullName")
    assert grantor["sectionLabel"] == "Thông tin ủy quyền cá nhân", "FE cần mốc để dò đúng khối"


async def test_thieu_o_bat_buoc_thi_goi_ten_o_va_khong_bam_nut_trang():
    conv = _conv(state="guide_login")
    r = await flow.handle_turn(conv, Intent("action", "guided_next", {
        "phase": "owner",
        "ownerFields": {"issueDate": "", "issuePlace": "Cục Cảnh sát",
                        "phoneNumber": "", "detailedAddress": "Thôn Trưng Trắc B"},
    }))
    assert "ngày cấp" in r.display_md and "số điện thoại" in r.display_md
    assert "nơi cấp" not in r.display_md, "ô đã điền thì không được kể là thiếu"
    assert "địa chỉ" not in r.display_md
    assert not r.actions, "còn thiếu thì KHÔNG được bấm nút chuyển bước của cổng"
    assert r.chips[0]["send"] == "__action:guided_next", "phải mời bấm lại sau khi điền nốt"


async def test_o_khong_tim_thay_tren_trang_thi_khong_ke_la_thieu():
    """Bộ dò không thấy ô → để chính cổng chặn, không chặn oan công dân."""
    conv = _conv()
    r = await flow.handle_turn(conv, Intent("action", "guided_next", {
        "phase": "owner", "ownerFields": {"phoneNumber": "0348929851"},
    }))
    assert r.actions and r.actions[0]["type"] == "guided_click_next"


async def test_dien_du_thi_bam_nut_buoc_tiep_theo_va_cho_dung_buoc_dinh_kem():
    conv = _conv()
    r = await flow.handle_turn(conv, Intent("action", "guided_next", {
        "phase": "owner",
        "ownerFields": {"issueDate": "30/07/2026", "issuePlace": "Cục Cảnh sát",
                        "phoneNumber": "0348929851", "detailedAddress": "Thôn Trưng Trắc B"},
    }))
    action = r.actions[0]
    assert action["type"] == "guided_click_next" and action["phase"] == "owner"
    assert action["expectStep"] == 3, "chứng thực bản sao bỏ qua kê khai, sang thẳng bước 3"


# ── Cổng chặn ─────────────────────────────────────────────────────────────────────────────

async def test_cong_bao_thieu_thi_doc_lai_nguyen_van_cho_cong_dan():
    conv = _conv(state="done", attach_done=True)
    r = await flow.handle_turn(conv, Intent("action", "guided_step_report", {
        "phase": "attachment", "ok": False,
        "message": "Vui lòng đính kèm đủ Hồ sơ bắt buộc",
    }))
    assert "Vui lòng đính kèm đủ Hồ sơ bắt buộc" in r.display_md
    assert r.chips[0]["send"] == "__action:guided_next"


async def test_bam_ma_trang_khong_chuyen_va_cung_khong_bao_gi():
    conv = _conv()
    r = await flow.handle_turn(conv, Intent("action", "guided_step_report", {
        "phase": "owner", "ok": False, "message": "",
    }))
    assert "chưa chuyển" in r.display_md
    assert r.chips[0]["phase"] == "owner"


# ── Bước Thành phần hồ sơ ─────────────────────────────────────────────────────────────────

async def _attach_ok(conv):
    return await flow.handle_turn(
        conv, Intent("action", "attach_report", {"attached": 2, "errors": []}),
    )


def _attaching(caps):
    return _conv(caps, state="attaching", attach_plan=[{"fileName": "a.pdf"}],
                 attach_mode="merge", attach_done=False)


async def test_dinh_kem_xong_client_cu_van_duoc_dan_tu_bam_nop():
    conv = _attaching(OLD_CLIENT)
    r = await _attach_ok(conv)
    assert r.display_md == vi.ATTACH_DONE["md"].format(attached=2)
    assert [c["send"] for c in r.chips] == ["__action:add_documents"]


async def test_dinh_kem_xong_client_moi_duoc_nut_sang_buoc_nhan_ket_qua():
    conv = _attaching(NEW_CLIENT)
    r = await _attach_ok(conv)
    assert "Thông tin nhận kết quả" in r.display_md
    assert "tự bấm" not in r.display_md, "không còn đẩy việc bấm nút cho công dân"
    cta = r.chips[-1]
    assert cta["send"] == "__action:guided_next" and cta["phase"] == "attachment"


async def test_van_con_nut_dieu_chinh_giay_to_o_buoc_dinh_kem():
    """Sự cố 22/09/2026: dựng Reply mới cho câu thoại guided là thay cả danh sách chip → nút
    'Điều chỉnh giấy tờ' bị nuốt, công dân đính sai không có đường sửa."""
    conv = _attaching(NEW_CLIENT)
    r = await _attach_ok(conv)
    assert [chip["send"] for chip in r.chips] == [
        "__action:add_documents", "__action:guided_next",
    ], "sửa giấy tờ đứng trước, nút chuyển bước tràn ngang xuống cuối"
    assert not r.chips[0].get("cta"), "nút sửa giấy tờ không được nổi bật như nút chuyển bước"


async def test_dinh_kem_co_loi_van_du_ca_hai_nut():
    conv = _attaching(NEW_CLIENT)
    r = await flow.handle_turn(conv, Intent("action", "attach_report", {
        "attached": 1, "errors": ["Trang báo lỗi tải lên"],
    }))
    assert [chip["send"] for chip in r.chips] == [
        "__action:add_documents", "__action:guided_next",
    ]


async def test_che_do_tach_ho_so_van_co_nut_chuyen_buoc_cho_ho_so_o_tab_goc():
    """Sự cố 22/09/2026: chế độ tách hồ sơ mất hẳn nút sang bước nhận kết quả.

    Nút bấm qua sendToContent gắn chặt tab của sidebar nên không thể bấm nhầm hồ sơ khác —
    nó luôn chuyển hồ sơ ở TAB GỐC. Các tab tách không có khung lái nên công dân tự bấm, và
    câu thoại phải nói rõ hai phần đó, nếu không công dân tưởng một nút lo hết mọi hồ sơ.
    """
    conv = _attaching(NEW_CLIENT)
    conv["attach_mode"] = "split"
    r = await _attach_ok(conv)
    cta = r.chips[-1]
    assert cta["send"] == "__action:guided_next" and cta["phase"] == "attachment"
    assert "hồ sơ ở tab này" in r.display_md
    assert "từng tab" in r.display_md, "phải dặn công dân tự bấm nộp ở các tab còn lại"
    assert "Thông tin nhận kết quả" in r.display_md


async def test_che_do_tach_ho_so_co_ban_mong():
    from app.channels.handfree.chat import script_mong as mong

    assert mong.GUIDED_ATTACH_SPLIT_DONE.get("md"), "thiếu bản Mông là giọng Mông đọc chữ Việt"


# ── Bước Thông tin nhận kết quả ───────────────────────────────────────────────────────────

def _after_attach(caps=NEW_CLIENT):
    return _conv(caps, state="done", attach_done=True)


async def test_qua_buoc_nhan_ket_qua_thi_huong_dan_ba_phuong_thuc():
    conv = _after_attach()
    r = await flow.handle_turn(conv, Intent("action", "guided_step_report", {
        "phase": "attachment", "ok": True, "wizardStep": 4,
    }))
    for phrase in ("bản giấy có đóng dấu", "trực tuyến", "bưu chính"):
        assert phrase in r.display_md
    assert "đơn vị bưu chính" in r.display_md, "chọn bưu chính là phải điền thêm cả khối địa chỉ"
    assert r.chips[0]["send"] == "__action:guided_submit"
    assert not r.actions, "bot KHÔNG tự chọn phương thức nhận kết quả hộ công dân"


async def test_cong_dan_tu_bam_sang_buoc_4_cung_duoc_huong_dan():
    """Không bấm nút của trợ lý mà tự bấm nút cuối trang cổng thì vẫn phải đổi hướng dẫn."""
    conv = _after_attach()
    r = await flow.handle_turn(conv, Intent("event", "page_status", {"wizardStep": 4}))
    assert "Thông tin nhận kết quả" in r.display_md
    assert r.chips[0]["send"] == "__action:guided_submit"


async def test_khong_lap_lai_huong_dan_nhan_ket_qua():
    conv = _after_attach()
    await flow.handle_turn(conv, Intent("event", "page_status", {"wizardStep": 4}))
    r = await flow.handle_turn(conv, Intent("event", "page_status", {"wizardStep": 4}))
    assert not r.display_md and not r.chips


async def test_client_cu_o_buoc_4_van_im_nhu_cu():
    conv = _after_attach(OLD_CLIENT)
    r = await flow.handle_turn(conv, Intent("event", "page_status", {"wizardStep": 4}))
    assert not r.display_md and not r.chips and not r.actions


async def test_bam_gui_ho_so_thi_phat_lenh_bam_nut_cua_cong():
    conv = _after_attach()
    r = await flow.handle_turn(conv, Intent("action", "guided_submit", {}))
    assert r.actions[0] == {"type": "guided_submit", "label": "Gửi hồ sơ"}
    assert "Gửi hồ sơ" in r.display_md


async def test_gui_thanh_cong_thi_im_de_luong_nop_cu_lo_tiep():
    conv = _after_attach()
    r = await flow.handle_turn(conv, Intent("action", "guided_submit_report", {"ok": True}))
    assert not r.display_md and not r.chips, "card đánh giá của luồng cũ mới là lời chốt"


# ── Thủ tục chưa bật ──────────────────────────────────────────────────────────────────────

async def test_thu_tuc_khac_du_client_moi_van_chay_luong_cu():
    conv = _conv(NEW_CLIENT, procedure_key="chung-thuc-giao-dich-tai-san")
    r = await _owner_page(conv)
    assert r.display_md == vi.OWNER_INFO_ATTACH_GUIDE["md"]
    assert not r.chips


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
