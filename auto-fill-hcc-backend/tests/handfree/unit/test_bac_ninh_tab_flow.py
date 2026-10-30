"""Cổng Bắc Ninh — luồng 4 tab cùng trang (chat/bac_ninh, cờ supportsBacNinhTabFlow), thủ tục đầu: Đăng ký biện pháp
bảo đảm bằng quyền sử dụng đất.

Vào trang hỏi cơ quan tiếp nhận (chọn trong chat / nói, hoặc tự chọn trên trang) → hỏi có điền người ủy quyền không → (có) điền khối ủy quyền ở tab Chọn cơ quan tiếp nhận rồi tự điền đơn khi
sang tab Nhập đơn đăng ký / (không) sang thẳng tab đơn → bổ sung ô → sang Thành phần hồ sơ đính kèm → sang Thông tin đăng
ký nhận kết quả, chọn nơi nhận, nút Nộp hồ sơ. Extension cũ (không cờ) giữ nguyên luồng samePageAttach cũ."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import bac_ninh, field_review, flow, pipeline_runner, store, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent
from app.pipelines.dang_ky_bien_phap_bao_dam_bac_ninh.process import mapper

KEY = "dang-ky-bien-phap-bao-dam-bac-ninh"
CAPS = {"supportsFieldReview": True, "supportsFlowV2": True, "supportsBacNinhTabFlow": True,
        "supportsBacNinhAuthorizedPerson": True, "supportsPageBoundDocsComplete": True}
FIELDS = [
    {"name": "loaiDoiTuongKhac", "comp": "bn-doi-tuong-khac", "value": "Doanh nghiệp"},
    {"name": "doiTuongKhachoTen", "comp": "bn-input", "value": "A"},
    {"name": "element_47783", "comp": "bn-input", "value": "B"},
    {"name": "element_47774", "comp": "bn-input", "value": "C"},
]
STATS = {"filled": 10, "optional": 4, "required": 0}
ASK_MD = vi.BN_AUTHORIZED_ASK["md"].format(who=vi.BN_WHO_DEFAULT)
DESCS = [vi.BN_AUTHORIZED_YES_DESC.format(who=vi.BN_WHO_DEFAULT),
         vi.BN_AUTHORIZED_NO_DESC.format(step=vi.BN_TAB_LABELS[2])]
SUFFIX = " - Văn phòng Đăng ký đất đai Bắc Ninh"
AGENCIES = [f"Chi nhánh Văn phòng đăng ký đất đai liên phường A{SUFFIX}",
            f"Chi nhánh Văn phòng đăng ký đất đai liên xã B{SUFFIX}", "Văn phòng đăng ký đất đai Bắc Ninh - SNNMT"]


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    spawned = []
    monkeypatch.setattr(pipeline_runner, "spawn",
                        lambda coro: (spawned.append(coro), getattr(coro, "close", lambda: None)()))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: ("run_attach", a))
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    return spawned


def _conv(state, caps=CAPS, **extra):
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "state": state, "client_capabilities": dict(caps),
                 "location": {"province": "Tỉnh Bắc Ninh", "ward": "Xã B"},
                 "auth_user": {"id": "u1"}, "upload_session_id": "s1", "milestones": [], "agency_done": True,
                 "consent": {"accepted": True}})
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}))


async def _arrive_page(conv, tab=1, agency=AGENCIES[0]):
    return await _turn(conv, "event", "page_status",
                       {"formKind": "bacninh", "attachmentTarget": True, "bnTab": tab, "bnAgency": agency})


def _sends(reply):
    return [c["send"] for c in reply.chips]


def _types(reply):
    return [a.get("type") for a in reply.actions]


def _action(reply, kind):
    return next(a for a in reply.actions if a.get("type") == kind)


def _proc():
    return flow.get_procedure(KEY)


def test_registry_hai_bien_va_chi_bat_khi_extension_khai_co():
    proc = _proc()
    assert proc["bacNinhTabFlow"]["resultMethods"][0]["default"] is True
    assert proc["bacNinhAuthorizedAsk"] is True and proc["bacNinhAgencyAsk"] is True
    assert bac_ninh.enabled(_conv("guide_login"), proc)
    assert not bac_ninh.enabled(_conv("guide_login", caps={"supportsFieldReview": True}), proc)
    assert not bac_ninh.enabled(_conv("guide_login", lang="hmong"), proc)
    # Bộ đọc eForm cũ không đọc được tab Bắc Ninh → không bật vòng bổ sung ô cho extension cũ.
    assert not field_review.active(_conv("guide_login", caps={"supportsFieldReview": True}), proc)
    assert field_review.active(_conv("guide_login"), proc)


async def test_extension_cu_vao_trang_giu_luong_cu():
    conv = _conv("guide_login", caps={"supportsFieldReview": True}, consent={})
    r = await _arrive_page(conv)
    assert conv["state"] == "consent"
    assert "bac_ninh" not in conv and "bn_tab" not in _types(r)


async def test_vao_trang_hoi_co_quan_tiep_nhan_truoc_chon_trong_chat():
    conv = _conv("guide_login")
    r = await _arrive_page(conv, agency="")
    assert r.actions == [{"type": "bn_agency"}] and not r.display_md
    r = await _turn(conv, "action", "bn_agency_report", {"options": AGENCIES, "selected": ""})
    assert r.display_md == vi.BN_AGENCY_ASK["md"]
    # Không liệt kê hết: chỉ gợi ý chi nhánh trùng phường/xã tài khoản + văn phòng cấp tỉnh.
    labels = [o["label"] for o in r.cards[0]["options"]]
    assert labels == ["Chi nhánh Văn phòng đăng ký đất đai liên xã B", "Văn phòng đăng ký đất đai Bắc Ninh - SNNMT"]
    # Nói / bấm một lựa chọn → nhờ extension chọn trên trang; chọn được thì sang câu hỏi ủy quyền.
    r = await _turn(conv, "action", "bn_agency_pick", {"value": AGENCIES[1]})
    assert r.actions == [{"type": "bn_agency", "value": AGENCIES[1]}]
    assert (await _turn(conv, "action", "bn_agency_pick", {"value": "Cơ quan bịa"})).actions == []
    r = await _turn(conv, "action", "bn_agency_report",
                    {"options": AGENCIES, "selected": AGENCIES[1], "changed": {"value": AGENCIES[1], "ok": True}})
    assert r.display_md.startswith("✓ Đã chọn cơ quan tiếp nhận") and ASK_MD in r.display_md
    assert conv["bac_ninh"]["agency"] == AGENCIES[1]
    # Chọn không được trên trang → nhờ chọn tay, vẫn để thẻ.
    conv2 = _conv("guide_login", bac_ninh={"agency_options": AGENCIES})
    r = await _turn(conv2, "action", "bn_agency_report",
                    {"options": AGENCIES, "selected": "", "changed": {"value": AGENCIES[1], "ok": False}})
    assert r.display_md == vi.BN_AGENCY_FAILED["md"] and r.cards


async def test_cong_dan_tu_chon_co_quan_tren_trang_thi_hoi_tiep_uy_quyen():
    conv = _conv("guide_login")
    await _arrive_page(conv, agency="")
    r = await _arrive_page(conv, agency="")
    assert not r.actions and not r.display_md  # đang chờ chọn: không hỏi lại
    r = await _arrive_page(conv, agency=AGENCIES[0])
    assert ASK_MD in r.display_md


async def test_vao_trang_hoi_dien_nguoi_uy_quyen_mot_lan():
    conv = _conv("guide_login")
    r = await _arrive_page(conv)
    assert r.display_md.endswith(ASK_MD)
    assert _sends(r) == ['__action:bn_authorized:{"value":true}', '__action:bn_authorized:{"value":false}']
    assert conv["state"] == "guide_login"
    r = await _arrive_page(conv)
    assert not r.display_md and not r.chips


async def test_chon_dien_uy_quyen_xin_dong_y_tai_tab_dau(monkeypatch):
    conv = _conv("guide_login", consent={})
    await _arrive_page(conv)
    r = await _turn(conv, "action", "bn_authorized", {"value": True})
    assert conv["state"] == "consent" and conv["bac_ninh"]["phase"] == "authorized"
    assert "bn_tab" not in _types(r)  # đang ở đúng tab Chọn cơ quan tiếp nhận
    assert pipeline_runner._bac_ninh_authorized_block(_proc(), conv)["subjectOption"]
    # Bấm lại nút cũ không xin đồng ý lần hai.
    r = await _turn(conv, "action", "bn_authorized", {"value": False})
    assert not r.display_md and conv["bac_ninh"]["authorized"] is True


async def test_chon_khong_dien_sang_tab_don_roi_xin_dong_y():
    conv = _conv("guide_login", consent={}, execution_subject="authorized_person")
    await _arrive_page(conv)
    r = await _turn(conv, "action", "bn_authorized", {"value": False})
    assert _action(r, "bn_tab") == {"type": "bn_tab", "tab": "nhapdondangky", "expect": 2}
    assert conv["state"] == "consent" and conv["bac_ninh"]["phase"] == "declaration"
    # Lựa chọn ở tab đầu thắng "Đối tượng thực hiện" đã chọn ở thẻ thủ tục.
    assert pipeline_runner._bac_ninh_authorized_block(_proc(), conv) is None


def _filling(phase, **extra):
    return _conv("filling", fields=[dict(f) for f in FIELDS], pipeline_status="fields_ready",
                 docs_target="declaration", auto_attach_after_fill=True,
                 bac_ninh={"authorized": phase == "authorized", "phase": phase, "at": 1}, **extra)


async def test_lenh_dien_tab_uy_quyen_chi_mang_khoi_uy_quyen():
    conv = _filling("authorized")
    r = await _turn(conv, "event", "fields_ready")
    action = _action(r, "fill_fields")
    assert action["bnTab"] == "chondonvitiepnhan"
    assert [f["name"] for f in action["fields"]] == ["loaiDoiTuongKhac", "doiTuongKhachoTen"]
    assert action["fieldReview"]["noAsk"] == ["KinhGui", "3BenBaoDam9", "IiiGiayChungNhanDoiVoiQuyenSuDungDat"]
    assert "TenGiayChungNhan=IiiGiayChungNhanDoiVoiQuyenSuDungDat" in action["fieldReview"]["mirror"]


async def test_khong_doc_duoc_nguoi_uy_quyen_van_mo_khoi_voi_loai_mac_dinh():
    conv = _filling("authorized")
    conv["fields"] = [f for f in conv["fields"] if not f["name"].startswith(("doiTuong", "loaiDoiTuong"))]
    r = await _turn(conv, "event", "fields_ready")
    fields = _action(r, "fill_fields")["fields"]
    assert fields == [{"name": "loaiDoiTuongKhac", "comp": "bn-doi-tuong-khac",
                       "value": "Cá nhân khác là Công dân Việt Nam"}]


async def test_dien_xong_tab_uy_quyen_bo_sung_roi_nut_sang_nhap_don(_no_io):
    conv = _filling("authorized")
    r = await _turn(conv, "action", "fill_report", {"filled": 2, "notFound": [], "review": STATS})
    assert conv["state"] == "reviewing" and not _no_io  # chưa đính kèm
    assert "khối thông tin người ủy quyền" in r.display_md
    assert _sends(r)[0] == "__action:bn_next" and r.chips[0]["label"] == vi.BN_NEXT_CHIPS[1]
    assert "__action:field_review_start" in _sends(r)
    # Sang tab đơn: điền đơn luôn từ cùng bộ ô pipeline đã trả.
    r = await _turn(conv, "action", "bn_next")
    assert _action(r, "bn_tab") == {"type": "bn_tab", "tab": "nhapdondangky", "expect": 2}
    r = await _turn(conv, "action", "bn_tab_report", {"ok": True, "expect": 2})
    action = _action(r, "fill_fields")
    assert action["bnTab"] == "nhapdondangky"
    assert [f["name"] for f in action["fields"]] == ["element_47783", "element_47774"]
    assert conv["state"] == "filling" and r.display_md.startswith(vi.BN_FORM_FILLING["md"])
    r = await _turn(conv, "action", "fill_report", {"filled": 2, "notFound": [], "review": STATS})
    assert r.chips[0]["label"] == vi.BN_NEXT_CHIPS[2]
    # Trace gộp hai lượt điền.
    report = tracing.set_report.await_args_list[-1].args[2]
    assert report["filled"] == 4


async def test_sang_thanh_phan_ho_so_dinh_kem_ngay_roi_nut_sang_nhan_ket_qua(_no_io):
    conv = _filling("declaration")
    await _turn(conv, "action", "fill_report", {"filled": 2, "notFound": [], "review": STATS})
    r = await _turn(conv, "action", "bn_next")
    assert _action(r, "bn_tab")["expect"] == 3
    r = await _turn(conv, "action", "bn_tab_report", {"ok": True, "expect": 3})
    assert conv["state"] == "attaching" and conv["attachment_plan_started"] is True and len(_no_io) == 1
    assert r.display_md == vi.BN_ATTACHING["md"]
    conv["attach_plan"] = [{"documentName": "Phiếu yêu cầu", "componentName": "Phiếu"}]
    r = await _turn(conv, "action", "attach_report", {"attached": 3, "errors": []})
    assert conv["state"] == "done"
    assert r.chips[-1]["label"] == vi.BN_NEXT_CHIPS[3]
    assert "tự bấm" not in r.display_md
    # Quay lại tab đính kèm sau khi đã đính: không đính lại.
    conv["bac_ninh"]["at"] = 4
    r = await _turn(conv, "action", "bn_tab_report", {"ok": True, "expect": 3})
    assert r.display_md == vi.BN_ATTACHED_ALREADY["md"] and len(_no_io) == 1


async def test_tab_nhan_ket_qua_chon_noi_nhan_va_nop():
    conv = _conv("done", attach_done=True, bac_ninh={"phase": "declaration", "at": 3, "form_filled": 1,
                                                    "filled_once": True})
    r = await _turn(conv, "action", "bn_next")
    assert _action(r, "bn_tab")["expect"] == 4
    r = await _turn(conv, "action", "bn_tab_report", {"ok": True, "expect": 4})
    assert _types(r) == ["bn_result"]
    r = await _turn(conv, "action", "bn_result_report", {"checked": "1"})
    assert r.cards[0]["kind"] == "result_methods" and r.cards[0]["selected"] == "1"
    assert _sends(r) == [bac_ninh.SUBMIT_SEND]
    r = await _turn(conv, "action", "bn_result_pick", {"value": "3"})
    assert r.actions == [{"type": "bn_result", "value": "3"}]
    r = await _turn(conv, "action", "bn_result_report", {"checked": "3", "changed": {"value": "3", "ok": True}})
    assert "địa chỉ nhận" in r.display_md and r.cards[0]["selected"] == "3"
    r = await _turn(conv, "action", "bn_submit")
    assert r.actions == [{"type": "bn_submit"}]
    r = await _turn(conv, "action", "bn_submit_report", {"clicked": True})
    assert r.display_md == vi.BN_SUBMIT_SENT["md"]
    r = await _turn(conv, "action", "bn_submit_report", {"clicked": True, "message": "Chưa chọn cơ quan"})
    assert "Chưa chọn cơ quan" in r.display_md and _sends(r) == [bac_ninh.SUBMIT_SEND]


async def test_noi_buoc_tiep_theo_la_chuyen_tab():
    conv = _conv("reviewing", bac_ninh={"phase": "declaration", "at": 2, "filled_once": True})
    intent = flow.next_step_by_voice(conv, "sang bước tiếp theo", {"bnTab": 2})
    assert intent.value == "bn_next"
    # "Đúng rồi" sau khi rà đơn: sang tab sau, không đính kèm ngay trên tab đơn.
    r = await _turn(conv, "confirm", "")
    assert _action(r, "bn_tab")["expect"] == 3 and conv["state"] == "reviewing"


def test_vong_bo_sung_di_tiep_la_tab_sau():
    conv = _conv("reviewing", bac_ninh={"phase": "authorized", "at": 1})
    field_review.begin(conv, {"filled": 3, "optional": 0, "required": 0})
    md, _, chips = field_review.conclusion(conv, _proc(), [])
    assert md.startswith("✓ Em đã điền xong phần này") and chips[0]["send"] == "__action:bn_next"
    st = conv["field_review"]
    st.update(running=True, current={"label": "Số điện thoại"})
    r = field_review._proceed(conv, _proc(), st)
    assert _types(r) == ["field_review_stop", "bn_tab"]


def test_mapper_khoi_uy_quyen_la_nguoi_uy_quyen():
    raw = [{"name": "UyQuyen_CoVanBan", "value": True}, {"name": "NguoiUyQuyen_Loai", "value": "doanh nghiệp"},
           {"name": "NguoiUyQuyen_Ten", "value": "CONG TY X"}, {"name": "NguoiUyQuyen_SoDinhDanh", "value": "0100 1124"},
           {"name": "NguoiUyQuyen_GioiTinh", "value": "Nam"}]
    out = mapper.enrich(raw, {"purpose": "authorized_person"})
    assert [f["name"] for f in out] == ["doiTuongKhachoTen", "doiTuongKhacsoDinhDanh"]  # doanh nghiệp: không ô cá nhân
    assert out[1]["value"] == "01001124"
    assert mapper.authorized_subject(raw) == "Doanh nghiệp"
    assert mapper.authorized_subject(raw[1:]) is None  # không có văn bản ủy quyền
    assert mapper.enrich(raw[1:], {"purpose": "authorized_person"}) == []


async def test_tra_loi_bang_loi_cau_hoi_uy_quyen_va_co_quan():
    conv = _conv("guide_login", consent={})
    await _arrive_page(conv)
    # Câu không hiểu / xin nhắc lại: hỏi lại đúng câu ủy quyền, không rơi về câu chờ đăng nhập.
    for intent in (Intent("unknown"), Intent("action", "repeat")):
        r = await flow.handle_turn(conv, intent)
        assert r.display_md == ASK_MD
        assert [c.get("desc") for c in r.chips] == DESCS
    flow.update_voice_options(conv, r)
    assert [i["desc"] for i in conv["voice_options"]["items"]] == DESCS
    # "Không" = không điền.
    r = await flow.handle_turn(conv, Intent("deny"))
    assert conv["bac_ninh"]["authorized"] is False and conv["state"] == "consent"
    # Đang chờ chọn cơ quan: câu không hiểu → hỏi lại kèm thẻ danh sách.
    conv2 = _conv("guide_login")
    await _arrive_page(conv2, agency="")
    await _turn(conv2, "action", "bn_agency_report", {"options": AGENCIES, "selected": ""})
    r = await flow.handle_turn(conv2, Intent("unknown"))
    assert r.display_md == vi.BN_AGENCY_ASK["md"] and r.cards[0]["kind"] == "result_methods"
    # "Có" khi đang hỏi cơ quan không phải chọn ủy quyền.
    await flow.handle_turn(conv2, Intent("confirm"))
    assert "authorized" not in conv2["bac_ninh"]


POINTS = [{"value": "15", "label": "Điểm tiếp nhận tại phường A", "address": "Địa chỉ: Phường A,"},
          {"value": "16", "label": "Điểm tiếp nhận tại phường B", "address": "Địa chỉ: Phường B,"}]
PAGE = [{"value": "1", "label": "Tại nơi nộp hồ sơ (theo giấy hẹn trả)"},
        {"value": "3", "label": "Tại nhà qua bưu chính công ích (VNPOST)"}]


async def test_noi_nhan_tai_noi_nop_hoi_diem_tiep_nhan_trong_mot_the():
    conv = _conv("done", attach_done=True, bac_ninh={"phase": "declaration", "at": 4, "filled_once": True})
    r = await _turn(conv, "action", "bn_result_report", {"checked": "1", "point": "", "options": PAGE, "points": POINTS})
    assert r.display_md == vi.BN_POINT_ASK["md"]
    card = r.cards[0]
    assert [o["label"] for o in card["options"]] == [
        "Tại nơi nộp hồ sơ (theo giấy hẹn trả) — Điểm tiếp nhận tại phường A",
        "Tại nơi nộp hồ sơ (theo giấy hẹn trả) — Điểm tiếp nhận tại phường B",
        "Tại nhà qua bưu chính công ích (VNPOST)"]
    assert card["selected"] == "" and card["options"][0]["desc"] == "Địa chỉ: Phường A,"
    r = await _turn(conv, "action", "bn_result_pick", {"value": "1", "point": "16"})
    assert r.actions == [{"type": "bn_result", "value": "1", "point": "16"}]
    assert (await _turn(conv, "action", "bn_result_pick", {"value": "1", "point": "99"})).actions == []
    r = await _turn(conv, "action", "bn_result_report", {"checked": "1", "point": "16", "options": PAGE,
                                                        "points": POINTS,
                                                        "changed": {"value": "1", "point": "16", "ok": True}})
    assert "Điểm tiếp nhận tại phường B" in r.display_md and r.cards[0]["selected"] == "1:16"
    # Cổng không có danh sách điểm: chỉ cách nhận như cũ.
    conv2 = _conv("done", attach_done=True, bac_ninh={"phase": "declaration", "at": 4})
    r = await _turn(conv2, "action", "bn_result_report", {"checked": "1", "options": PAGE[:1], "points": []})
    assert [o["key"] for o in r.cards[0]["options"]] == ["1"] and r.cards[0]["selected"] == "1"


async def test_nop_khi_chua_chon_diem_tiep_nhan_thi_nhac_chon():
    conv = _conv("done", attach_done=True, bac_ninh={"phase": "declaration", "at": 4})
    r = await _turn(conv, "action", "bn_submit_report",
                    {"clicked": False, "missing": "point", "checked": "1", "options": PAGE, "points": POINTS})
    assert r.display_md == vi.BN_POINT_MISSING["md"] and len(r.cards[0]["options"]) == 3
    assert _sends(r) == [bac_ninh.SUBMIT_SEND]


async def test_dinh_loi_mot_phan_co_nut_dinh_lai_chay_lai_ke_hoach():
    conv = _conv("attaching", bac_ninh={"phase": "declaration", "at": 3, "form_filled": 1, "filled_once": True},
                 attach_plan=[{"documentName": "Phiếu", "componentName": "Phiếu"}])
    r = await _turn(conv, "action", "attach_report", {"attached": 1, "errors": ["Tệp B chưa lên trang"]})
    assert _sends(r)[0] == "__action:bn_attach_retry"
    r = await _turn(conv, "action", "bn_attach_retry")
    assert conv["state"] == "attaching" and _types(r) == ["attach_plan"]


def test_bo_so_muc_khi_hoi_o_cong_bac_ninh():
    field = field_review._field({"key": "k", "label": "3.1. Họ và tên đầy đủ", "section": "3. Bên bảo đảm"},
                                strip_numbers=field_review._bac_ninh_portal(_proc()))
    assert field["label"] == "Họ và tên đầy đủ" and field["where"] == "Bên bảo đảm"
    assert field_review._field({"key": "k", "label": "(ii) Địa chỉ thửa đất"}, strip_numbers=True)["label"] == \
        "Địa chỉ thửa đất"
    # Thủ tục cổng khác giữ nguyên nhãn.
    assert not field_review._bac_ninh_portal(flow.get_procedure("ket-hon"))


POSTAL = [{"name": "guiBuuChinh", "label": "Gửi hồ sơ qua bưu điện", "checked": False},
          {"name": "nhanBuuChinh", "label": "Nhận kết quả qua bưu điện", "checked": False}]


async def test_buu_chinh_hoi_gui_nhan_hay_ca_hai_roi_nhac_dien_thong_tin():
    conv = _conv("done", attach_done=True, bac_ninh={"phase": "declaration", "at": 4})
    r = await _turn(conv, "action", "bn_result_report",
                    {"checked": "3", "options": PAGE, "postal": POSTAL, "changed": {"value": "3", "ok": True}})
    assert vi.BN_POSTAL_ASK["md"] in r.display_md and r.display_md.startswith("✓ Đã chọn nhận kết quả")
    assert [c["label"] for c in r.chips] == ["📤 Gửi hồ sơ qua bưu điện", "📥 Nhận kết quả qua bưu điện",
                                            "📤📥 Cả hai", vi.BN_SUBMIT_CHIP]
    r = await _turn(conv, "action", "bn_postal_pick", {"names": ["guiBuuChinh", "nhanBuuChinh"]})
    assert r.actions == [{"type": "bn_result", "postal": ["guiBuuChinh", "nhanBuuChinh"]}]
    assert (await _turn(conv, "action", "bn_postal_pick", {"names": ["bia"]})).actions == []
    ticked = [{**b, "checked": True} for b in POSTAL]
    r = await _turn(conv, "action", "bn_result_report",
                    {"checked": "3", "options": PAGE, "postal": ticked,
                     "changed": {"postal": ["guiBuuChinh", "nhanBuuChinh"], "ok": True}})
    assert "Gửi hồ sơ qua bưu điện và Nhận kết quả qua bưu điện" in r.display_md
    assert _sends(r) == [bac_ninh.SUBMIT_SEND]
    # Bấm nộp khi chưa tích ô nào: nhắc chọn lại.
    r = await _turn(conv, "action", "bn_submit_report",
                    {"clicked": False, "missing": "postal", "checked": "3", "options": PAGE, "postal": POSTAL})
    assert r.display_md == vi.BN_POSTAL_MISSING["md"] and len(r.chips) == 4


async def test_noi_ten_chi_nhanh_do_tren_ca_danh_sach(monkeypatch):
    conv = _conv("guide_login")
    await _arrive_page(conv, agency="")
    await _turn(conv, "action", "bn_agency_report", {"options": AGENCIES, "selected": ""})
    assert bac_ninh.agency_asking(conv)
    seen = {}

    async def fake_llm(messages, **_):
        seen["prompt"] = messages[0]["content"]
        return '{"index": 1}'

    monkeypatch.setattr(bac_ninh, "llm_chat", fake_llm)
    assert await bac_ninh.match_agency(conv, "liên phường a") == AGENCIES[0]
    assert all(a in seen["prompt"] for a in AGENCIES)  # LLM thấy cả danh sách, không chỉ gợi ý trên thẻ

    async def no_match(messages, **_):
        return '{"index": 0}'

    monkeypatch.setattr(bac_ninh, "llm_chat", no_match)
    assert await bac_ninh.match_agency(conv, "ừ thì") == ""
    # Chọn xong thì thôi dò.
    conv["bac_ninh"]["agency"] = AGENCIES[0]
    assert not bac_ninh.agency_asking(conv)


async def test_da_dinh_xong_noi_ok_la_sang_tab_nhan_ket_qua_khong_mat_nut():
    conv = _conv("done", attach_done=True, bac_ninh={"phase": "declaration", "at": 3, "form_filled": 1,
                                                    "attach_for": 1, "filled_once": True})
    r = await flow.handle_turn(conv, Intent("confirm"))
    assert _action(r, "bn_tab")["expect"] == 4
    # Câu không hiểu: nói lại việc của tab đính kèm, giữ nút đi tiếp (không chỉ còn nút Điều chỉnh giấy tờ).
    r = await flow.handle_turn(conv, Intent("unknown"))
    assert r.display_md == vi.BN_ATTACHED_ALREADY["md"]
    assert r.chips[-1]["send"] == "__action:bn_next" and "qua Thông tin đăng ký nhận kết quả" in r.chips[-1]["desc"]
    flow.update_voice_options(conv, r)
    assert any(i.get("desc") for i in conv["voice_options"]["items"])
    # Tab nhận kết quả: "ok" không tự nộp, nói lại nơi nhận kèm thẻ + nút nộp.
    conv["bac_ninh"].update(at=4, result={"checked": "1", "page": ["1", "3"]})
    r = await flow.handle_turn(conv, Intent("confirm"))
    assert r.cards and _sends(r) == [bac_ninh.SUBMIT_SEND] and not r.actions


# ── Trang hoàn thiện thông tin tài khoản (người làm lần đầu) ──

ACCOUNT_CTX = {"applicantFullname": "NGUOI A", "applicantIdentityNumber": "001"}


async def test_trang_tai_khoan_xin_dong_y_nhan_giay_to_mot_lan_va_neo_chu_the():
    conv = _conv("guide_login", consent={}, form_context=dict(ACCOUNT_CTX))
    r = await _turn(conv, "event", "page_status", {"formKind": "bacninh", "bnAccountForm": True, "bnTab": 0})
    assert r.display_md.startswith(vi.BN_ACCOUNT_INTRO["md"]) and conv["state"] == "consent"
    assert conv["bac_ninh"]["phase"] == "account" and bac_ninh.account_context(conv) == ACCOUNT_CTX
    # Lượt người ủy quyền không chạy ở request tài khoản.
    assert pipeline_runner._bac_ninh_authorized_block(_proc(), conv) is None
    r = await _turn(conv, "event", "page_status", {"formKind": "bacninh", "bnAccountForm": True, "bnTab": 0})
    assert not r.display_md


def _account(state="filling", **extra):
    return _conv(state, fields=[{"name": "ngayCap", "comp": "bn-date", "value": "01/01/2020"}],
                 pipeline_status="fields_ready", docs_target="declaration", auto_attach_after_fill=True,
                 bac_ninh={"phase": "account", "account_ctx": ACCOUNT_CTX}, **extra)


async def test_dien_tai_khoan_chua_du_o_bat_buoc_chua_co_nut_luu():
    conv = _account()
    r = await _turn(conv, "event", "fields_ready")
    action = _action(r, "fill_fields")
    assert action["bnTab"] == "thongtinchung" and action["fields"][0]["name"] == "ngayCap"
    r = await _turn(conv, "action", "fill_report", {"filled": 1, "notFound": [],
                                                   "review": {"filled": 4, "optional": 3, "required": 2}})
    assert conv["state"] == "reviewing" and "thông tin tài khoản" in r.display_md
    assert "__action:bn_next" not in _sends(r) and _sends(r)[0] == "__action:field_review_start"
    # Công dân tự điền đủ ô bắt buộc trên trang → hiện nút Lưu.
    r = await _turn(conv, "event", "field_review_status", {"stats": {"filled": 6, "optional": 3, "required": 0}})
    assert r.chips[0]["label"] == vi.BN_ACCOUNT_SAVE_CHIP


async def test_luu_tai_khoan_loi_thi_moi_bo_sung_luu_duoc_thi_cho_trang_thu_tuc():
    conv = _account(state="reviewing")
    r = await _turn(conv, "action", "bn_next")
    assert r.actions == [{"type": "bn_account_save"}]
    r = await _turn(conv, "action", "bn_account_report", {"clicked": True, "message": "Số điện thoại không được trống"})
    assert "Số điện thoại không được trống" in r.display_md and conv["state"] == "reviewing"
    r = await _turn(conv, "action", "bn_account_report", {"clicked": True, "message": "", "gone": True})
    assert conv["state"] == "guide_login" and conv["bac_ninh"]["account_saved"] is True
    assert r.display_md == vi.BN_ACCOUNT_SAVED["md"]
    # Cổng nạp lại đúng trang tài khoản: chưa lưu được → về vòng bổ sung.
    r = await _turn(conv, "event", "page_status", {"formKind": "bacninh", "bnAccountForm": True, "bnTab": 0})
    assert conv["state"] == "reviewing" and conv["bac_ninh"]["phase"] == "account"


async def test_sang_trang_thu_tuc_sau_tai_khoan_dien_luon_khong_xin_giay_to_lai(_no_io):
    conv = _conv("guide_login", bac_ninh={"account_saved": True}, milestones=["bn_account_intro"])
    await _arrive_page(conv)
    r = await _turn(conv, "action", "bn_authorized", {"value": False})
    assert conv["state"] == "filling" and conv["pipeline_status"] == "running"
    assert r.display_md == vi.BN_FILL_FROM_DOCS["md"] and not r.cards
    assert conv["bac_ninh"]["phase"] == "declaration" and len(_no_io) == 1


class _FakeColl:
    def __init__(self, doc):
        self.doc = doc

    async def find_one(self, _q):
        return self.doc

    async def delete_one(self, _q):
        self.doc = None


async def test_lay_ket_qua_doc_ngam_ghep_khoi_uy_quyen_khi_chon_dien(monkeypatch):
    conv = _conv("filling", bac_ninh={"phase": "authorized", "authorized": True}, upload_session_id="s1")
    store_ = {"c": conv}
    coll = _FakeColl({"status": "done", "fields": [{"name": "element_1", "value": "x"}],
                      "authFields": [{"name": "doiTuongKhachoTen", "value": "y"}], "traceId": "t-1"})

    class _Db:
        bac_ninh_prefill = coll
        pipeline_heartbeats = type("H", (), {"delete_one": AsyncMock(), "update_one": AsyncMock()})()

    sent = []
    monkeypatch.setattr(pipeline_runner, "get_db", lambda: _Db())
    monkeypatch.setattr(pipeline_runner.conv_store, "get", AsyncMock(return_value=conv))
    monkeypatch.setattr(pipeline_runner.conv_store, "save", AsyncMock())
    monkeypatch.setattr(pipeline_runner, "broadcast", AsyncMock(side_effect=lambda sid, msg: sent.append(msg)))
    await pipeline_runner.apply_bac_ninh_prefill.__wrapped__(conv["_id"], "s1", KEY)
    assert [f["name"] for f in store_["c"]["fields"]] == ["element_1", "doiTuongKhachoTen"]
    assert conv["pipeline_status"] == "fields_ready" and conv["trace_request_id"] == "t-1"
    assert sent == [{"type": "fields_ready", "count": 2}] and coll.doc is None
    # Không có kết quả đọc ngầm → đọc lại như thường.
    rerun = AsyncMock()
    monkeypatch.setattr(pipeline_runner.run_process, "__wrapped__", rerun)
    await pipeline_runner.apply_bac_ninh_prefill.__wrapped__(conv["_id"], "s1", KEY)
    rerun.assert_awaited_once()


async def test_request_tai_khoan_neo_chu_the_va_chay_ngam_request_don(monkeypatch, _no_io):
    conv = _conv("filling", bac_ninh={"phase": "account", "account_ctx": ACCOUNT_CTX},
                 form_context={"applicantFullname": "KHAC"})
    calls = {}

    async def account_pipeline(files_by_role, options):
        calls["account"] = options
        return {"fields": [{"name": "ngayCap", "value": "01/01/2020"}]}

    async def main_pipeline(files_by_role, options):
        calls["main"] = options
        return {"fields": []}

    monkeypatch.setattr(pipeline_runner, "get_pipeline",
                        lambda key: account_pipeline if key == bac_ninh.ACCOUNT_PROCEDURE else main_pipeline)
    monkeypatch.setattr(pipeline_runner.up_store, "get", AsyncMock(return_value={"files": [{"fid": "f1"}]}))
    monkeypatch.setattr(pipeline_runner, "_session_files", lambda sess: [{"name": "a.pdf"}])
    monkeypatch.setattr(pipeline_runner.conv_store, "get", AsyncMock(return_value=conv))
    monkeypatch.setattr(pipeline_runner.conv_store, "save", AsyncMock())
    monkeypatch.setattr(pipeline_runner, "broadcast", AsyncMock())
    monkeypatch.setattr(tracing, "record_process", AsyncMock(return_value="t-acc"))
    monkeypatch.setattr(pipeline_runner, "_load_owner_user", AsyncMock(return_value=None))
    await pipeline_runner.run_process.__wrapped__(conv["_id"], "s1", KEY)
    # Neo đúng chủ tài khoản đã lưu lúc vào trang (không lấy form_context của lượt sau).
    assert calls["account"] == {"formContext": ACCOUNT_CTX} and "main" not in calls
    assert conv["fields"] == [{"name": "ngayCap", "value": "01/01/2020"}]
    assert any(getattr(c, "__name__", "") == "run_bac_ninh_prefill" for c in _no_io)


def test_moi_thu_tuc_trang_4_tab_bac_ninh_deu_bat_luong_moi():
    from app.channels.handfree.chat.field_review import registry
    from app.channels.handfree.procedure_registry import public_list

    bn = [p for p in public_list() if "bacninh" in (p.get("provinceOnly") or []) and p.get("samePageAttach")]
    assert len(bn) >= 16
    for p in bn:
        # Cổng chọn sẵn cơ quan tiếp nhận ở các thủ tục này → không hỏi.
        no_agency = {"dinh-chinh-gcn-da-cap-bac-ninh", "dinh-chinh-gcn-da-cap-1115476-bac-ninh",
                     "ho-tro-chi-phi-hoa-tang-bac-ninh", "ho-tro-nguoi-cao-tuoi-bac-ninh"}
        assert p["bacNinhTabFlow"] and p["bacNinhAgencyAsk"] is (p["key"] not in no_agency), p["key"]
        assert p["bacNinhAuthorizedAsk"] is bool(p.get("bacNinhAuthorizedPerson")), p["key"]
        assert registry.get(p["key"]) is not None, p["key"]



# ── Hỗ trợ người cao tuổi: chỉ đính kèm, khối ủy quyền điền người cao tuổi ──

ELDER = "ho-tro-nguoi-cao-tuoi-bac-ninh"


async def test_nguoi_cao_tuoi_hoi_dien_khoi_nguoi_cao_tuoi_roi_sang_thang_thanh_phan(_no_io):
    conv = _conv("guide_login", procedure_key=ELDER, consent={})
    r = await _arrive_page(conv)
    assert "thông tin người cao tuổi" in r.display_md
    assert [c["label"] for c in r.chips] == ["✍️ Điền thông tin người cao tuổi",
                                            "➡️ Không điền, sang Tải thành phần hồ sơ"]
    await _turn(conv, "action", "bn_authorized", {"value": True})
    assert conv["bac_ninh"]["phase"] == "authorized"
    proc = flow.get_procedure(ELDER)
    # Chốt giấy tờ: chạy lượt điền khối người cao tuổi trước, chưa đính kèm.
    assert bac_ninh.docs_target(conv, proc, "attachment") == "declaration"
    assert pipeline_runner._bac_ninh_authorized_block(proc, conv)["subjectOption"] == "Người cao tuổi"
    conv.update(state="filling", fields=[{"name": "loaiDoiTuongKhac", "comp": "bn-doi-tuong-khac",
                                          "value": "Người cao tuổi"},
                                         {"name": "doiTuongKhachoTen", "comp": "bn-input", "value": "A"}],
                auto_attach_after_fill=True, docs_target="declaration")
    r = await _turn(conv, "action", "fill_report", {"filled": 2, "notFound": [], "review": STATS})
    assert r.chips[0]["label"] == vi.BN_NEXT_CHIPS[2]  # sang Thành phần hồ sơ, không qua tab đơn
    r = await _turn(conv, "action", "bn_next")
    assert _action(r, "bn_tab")["expect"] == 3
    r = await _turn(conv, "action", "bn_tab_report", {"ok": True, "expect": 3})
    assert conv["state"] == "attaching" and r.display_md == vi.BN_ATTACHING["md"]


async def test_nguoi_cao_tuoi_khong_dien_thi_dinh_kem_luon():
    conv = _conv("guide_login", procedure_key=ELDER, consent={})
    await _arrive_page(conv)
    r = await _turn(conv, "action", "bn_authorized", {"value": False})
    assert conv["bac_ninh"]["phase"] == "attach" and "bn_tab" not in _types(r)
    assert bac_ninh.docs_target(conv, flow.get_procedure(ELDER), "attachment") == "attachment"



def test_hai_thu_tuc_dinh_chinh_co_hau_to_truong_hop():
    labels = {k: flow.get_procedure(k)["label"] for k in ("dinh-chinh-gcn-da-cap-bac-ninh",
                                                           "dinh-chinh-gcn-da-cap-1115476-bac-ninh")}
    assert labels["dinh-chinh-gcn-da-cap-bac-ninh"].endswith("(Trường hợp Giấy chứng nhận cấp lần đầu có sai sót)")
    assert labels["dinh-chinh-gcn-da-cap-1115476-bac-ninh"].endswith(
        "(Trường hợp Giấy chứng nhận đã đăng ký biến động có sai sót)")


async def test_nguoi_cao_tuoi_trang_2_tab_dinh_xong_quay_lai_chon_buu_chinh_roi_nop():
    conv = _conv("guide_login", procedure_key=ELDER, consent={})
    r = await _arrive_page(conv, agency="")
    assert r.chips and "bn_agency" not in _types(r)  # không hỏi cơ quan tiếp nhận
    conv.update(state="attaching", attach_plan=[{"documentName": "Tờ khai", "componentName": "Tờ khai"}],
                bac_ninh={"phase": "attach", "authorized": False, "at": 3})
    r = await _turn(conv, "action", "attach_report", {"attached": 1, "errors": []})
    assert r.chips[-1]["label"] == vi.BN_POSTAL_STEP_CHIP
    r = await _turn(conv, "action", "bn_next")
    assert _action(r, "bn_tab")["expect"] == 1
    r = await _turn(conv, "action", "bn_tab_report", {"ok": True, "expect": 1})
    assert _types(r) == ["bn_result"]
    ticked = [{**b, "checked": True} for b in POSTAL]
    r = await _turn(conv, "action", "bn_result_report", {"checked": "", "options": [], "postal": ticked})
    assert "Gửi hồ sơ qua bưu điện và Nhận kết quả qua bưu điện" in r.display_md and not r.cards
    assert _sends(r) == [bac_ninh.SUBMIT_SEND]
    # Đi tiếp ở bước này = nộp hồ sơ.
    r = await _turn(conv, "action", "bn_next")
    assert r.actions == [{"type": "bn_submit"}]
