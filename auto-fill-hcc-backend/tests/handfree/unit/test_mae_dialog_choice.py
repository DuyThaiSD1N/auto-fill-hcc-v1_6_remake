"""Hộp thoại "Chọn trường hợp giải quyết" (cổng Bộ Xây dựng): câu hỏi liệt kê tên GỌN các lựa chọn (nhãn cổng rất dài,
thẻ vẫn hiện nguyên văn), và công dân nói TÊN lựa chọn ("nhà ở riêng lẻ") là chọn được như bấm thẻ."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, store
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.procedure_registry import case_pipeline_options

KEY = "cap-giay-phep-xay-dung-moi-nha-o-rieng-le"
CONG_TRINH = ("(10 ngày làm việc) Cấp giấy phép xây dựng mới đối với công trình cấp III, cấp IV (Công trình không "
              "theo tuyến/Theo tuyến trong đô thị/Tín ngưỡng, tôn giáo/Tượng đài, tranh hoành tráng/Dự án)")
NHA_O = "(7 ngày làm việc) Cấp giấy phép xây dựng mới đối với nhà ở riêng lẻ"


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())


def _conv():
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "state": "guide_login", "client_capabilities": {"supportsMaeDialogChoice": True},
                 "auth_user": {"id": "u1"},
                 "mae_dialog_options": {"agency": {"options": ["UBND Phường A"], "current": "UBND Phường A"},
                                        "process": {"options": [CONG_TRINH, NHA_O], "current": CONG_TRINH}}})
    return conv


def test_ten_gon_bo_phan_trong_ngoac_va_phan_mo_dau_giong_nhau():
    assert flow._mae_dialog_short_labels([CONG_TRINH, NHA_O]) == ["công trình cấp III, cấp IV", "nhà ở riêng lẻ"]
    assert flow._mae_dialog_short_labels(["UBND Phường A"]) == ["UBND Phường A"]


def test_ten_gon_bo_ca_phan_duoi_giong_nhau():
    tail = " - Cấp điều chỉnh giấy phép xây dựng đối với công trình cấp III, cấp IV"
    labels = ["Đối với nhà ở riêng lẻ" + tail, "Đối với công trình" + tail + " (Dự án)"]
    assert flow._mae_dialog_short_labels(labels) == ["nhà ở riêng lẻ", "công trình"]


def test_cau_hoi_chi_liet_ke_ten_gon_the_van_nguyen_van():
    conv = _conv()
    reply = flow._to_choose_mae_dialog(conv)
    assert "**công trình cấp III, cấp IV** · **nhà ở riêng lẻ**" in reply.display_md
    assert "Tượng đài" not in reply.display_md and "Tượng đài" not in reply.tts_text
    assert "công trình cấp III, cấp IV, hoặc nhà ở riêng lẻ" in reply.tts_text
    (card,) = reply.cards
    assert [o["label"] for o in card["groups"][0]["options"]] == [CONG_TRINH, NHA_O]


async def test_noi_ten_lua_chon_la_chon_dung_lua_chon_do():
    conv = _conv()
    reply = flow._to_choose_mae_dialog(conv)
    flow.update_voice_options(conv, reply)
    items = conv["voice_options"]["items"]
    nha_o = next(i for i in items if i["label"] == "nhà ở riêng lẻ")
    assert nha_o["send"] == '__action:set_mae_dialog:{"process": 1}' and nha_o["desc"] == NHA_O
    # Lời nói chọn nút → cùng lệnh như bấm thẻ (payload mang chỉ số lựa chọn).
    picked = await flow.handle_turn(conv, Intent("action", "set_mae_dialog",
                                                 {"process": 1, "_voice_button": nha_o["send"]}))
    action = next(a for a in picked.actions if a["type"] == "fill_mae_agency")
    assert action["processExact"] == NHA_O
    assert "trường hợp **nhà ở riêng lẻ**" in picked.display_md
    assert conv["mae_dialog_choice_labels"]["process"] == NHA_O


def test_hoi_hai_o_cung_luc_thi_chi_chon_tren_the():
    conv = _conv()
    conv["mae_dialog_options"]["agency"] = {"options": ["UBND Phường A", "UBND Phường B"], "current": ""}
    card = flow._mae_dialog_card(conv)
    assert flow._card_voice_items(card) == []


async def test_dang_bam_dong_y_ma_trang_chua_doc_duoc_lua_chon_thi_khong_hoi_lai_truong_hop():
    conv = _conv()
    conv["state"] = "choose_mae_dialog"
    await flow.handle_turn(conv, Intent("action", "set_mae_dialog", {"process": 1}))
    # FE đang mở ô chọn để điền → lần đọc trang này không lấy được lựa chọn của hộp thoại.
    reply = await flow.handle_turn(conv, Intent("event", "page_status", {"maeAgencyBlock": True}))
    assert conv["state"] != "choose_variant"
    assert not reply.chips and not reply.actions and not reply.display_md


SC_CONG_TRINH = ("(10 ngày làm việc) Cấp giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV")
SC_NHA_O = "(15 ngày làm việc) Cấp giấy phép xây dựng sửa chữa, cải tạo đối với nhà ở riêng lẻ"


def _sua_chua_conv(key):
    conv = store.new_conversation()
    conv.update({"procedure_key": key, "state": "guide_login", "client_capabilities": {"supportsMaeDialogChoice": True},
                 "auth_user": {"id": "u1"}})
    return conv


def _dialog_ctx(*process):
    return {"maeDialogOptions": {"agency": {"options": ["UBND Phường A"], "current": "UBND Phường A"},
                                 "process": {"options": list(process), "current": process[0]}}}


@pytest.mark.parametrize("key, label, variant", [
    ("sua-chua-cai-tao-gpxd-cong-trinh", SC_CONG_TRINH, "cong_trinh"),
    ("sua-chua-cai-tao-gpxd-nha-o-rieng-le", SC_NHA_O, "nha_o_rieng_le"),
])
def test_sua_chua_card_nhanh_nao_thi_hop_thoai_tu_chon_truong_hop_nhanh_do(key, label, variant):
    conv = _sua_chua_conv(key)
    proc = flow.get_procedure(key)
    reply = flow._mae_dialog_on_page(conv, _dialog_ctx(SC_NHA_O, SC_CONG_TRINH), proc)
    # Chỉ còn một trường hợp → không hỏi công dân, chọn luôn đúng nhãn nguyên văn.
    assert conv["state"] != "choose_mae_dialog"
    action = next(a for a in reply.actions if a["type"] == "fill_mae_agency")
    assert action["processExact"] == label
    assert case_pipeline_options(proc, conv) == {"constructionVariant": variant}


def test_sua_chua_cong_trinh_cong_doi_nhan_khong_loc_duoc_thi_van_hoi():
    key = "sua-chua-cai-tao-gpxd-cong-trinh"
    conv = _sua_chua_conv(key)
    odd = ["Quy trình A đối với nhà ở riêng lẻ", "Quy trình B đối với nhà ở riêng lẻ"]
    reply = flow._mae_dialog_on_page(conv, _dialog_ctx(*odd), flow.get_procedure(key))
    assert conv["state"] == "choose_mae_dialog"
    assert [o["label"] for o in reply.cards[0]["groups"][0]["options"]] == odd


# ── Cổng iGate Tuyên Quang: mỗi trường hợp giải quyết (quy trình) là một FORM khác → chọn xong phải điền đúng form ──
TQ_DAT_DAI = "dang-ky-dat-dai-lan-dau-tuyen-quang"
TQ_DINH_CHINH = "dinh-chinh-gcn-cap-lan-dau-sai-sot-tuyen-quang"
TQ_GIAO_DAT = "giao-thue-chuyen-muc-dich-dat-giao-rung-gia-han-tuyen-quang"
TQ_KEYS = (TQ_DAT_DAI, TQ_DINH_CHINH, TQ_GIAO_DAT)
TQ_5_BUOC = "5 bước 20 ngày"
TQ_ILIS = "iLis cấp xã - 30 ngày"
TQ_VBDLIS = "1.013978_VBDLIS_20"


def _tq_conv(key):
    conv = _sua_chua_conv(key)
    conv["auth_user"] = {"id": "u1", "province_slug": "tuyenquang"}
    conv["location"] = {"province": "Tỉnh Tuyên Quang", "province_slug": "tuyenquang", "ward": "Xã Thượng Lâm"}
    return conv


@pytest.mark.parametrize("slug, visible", [("tuyenquang", True), ("khanhhoa", False)])
def test_tuyen_quang_hien_tren_man_chao_o_tim_kiem_va_bo_chon_loi_noi_dung_tinh(slug, visible):
    """Tài khoản Tuyên Quang thấy 3 thẻ (tìm được theo tên đầy đủ / mã TTHC) và bộ chọn theo lời nói có 3 thủ tục; tài
    khoản tỉnh khác không thấy."""
    from app.channels.handfree.chat.procedure_picker.agent import procedures_for

    conv = store.new_conversation()
    conv["auth_user"] = {"id": "u1", "province_slug": slug}
    items = {item["key"]: item for item in flow._service_list_card(conv)["items"]}
    picker = {p["key"] for p in procedures_for(slug)}
    for key, code in zip(TQ_KEYS, ("1.013978", "1.012796", "1.013949")):
        assert (key in items) is visible and (key in picker) is visible, key
        if visible:
            assert items[key]["code"] == code
            assert "Tuyên Quang" not in items[key]["title"]
    if visible:
        assert items[TQ_DAT_DAI]["label"].startswith("Đăng ký đất đai, tài sản gắn liền với đất")


@pytest.mark.parametrize("slug, code, expect", [
    ("tuyenquang", "1.013978", TQ_DAT_DAI),
    ("khanhhoa", "1.013978", "dang-ky-dat-dai-lan-dau-khanh-hoa"),
    ("tuyenquang", "mã 1.013949", TQ_GIAO_DAT),
    ("khanhhoa", "1.013949", "giao-thue-chuyen-muc-dich-dat-khanh-hoa"),
])
async def test_go_ma_tthc_co_ban_nhieu_tinh_thi_chon_ban_cua_tinh_tai_khoan(slug, code, expect):
    """1.013978 / 1.013949 có cả bản Khánh Hòa lẫn Tuyên Quang (mỗi bản khóa tỉnh riêng): tài khoản Tuyên Quang gõ mã phải
    vào bản Tuyên Quang, không dính bản Khánh Hòa đứng trước rồi bị báo "chỉ làm được ở Tỉnh Khánh Hòa"."""
    from app.channels.handfree.chat import intents

    conv = store.new_conversation()
    conv["auth_user"] = {"id": "u1", "province_slug": slug}
    intent = await intents.resolve(code, "greet", conv)
    assert (intent.kind, intent.value) == ("pick_procedure", expect)


async def test_go_ma_tthc_tinh_khong_co_ban_nao_van_bao_khoa_tinh():
    from app.channels.handfree.chat import intents

    conv = store.new_conversation()
    conv["auth_user"] = {"id": "u1", "province_slug": "laichau"}
    intent = await intents.resolve("1.013978", "greet", conv)
    assert intent.kind == "pick_procedure" and flow.get_procedure(intent.value)["provinceOnly"] != ["laichau"]


async def test_tuyen_quang_doc_hop_thoai_hoi_cong_dan_roi_chon_dung_quy_trinh_va_form():
    conv = _tq_conv(TQ_DAT_DAI)
    reply = await flow.handle_turn(conv, Intent("event", "page_status",
                                                {"maeAgencyBlock": True, **_dialog_ctx(TQ_5_BUOC, TQ_ILIS, TQ_VBDLIS)}))
    # Ba quy trình → hỏi công dân trên thẻ, chưa bấm Đồng ý hộ.
    assert conv["state"] == "choose_mae_dialog"
    assert not [a for a in reply.actions if a["type"] == "fill_mae_agency"]
    (group,) = reply.cards[0]["groups"]
    assert [o["label"] for o in group["options"]] == [TQ_5_BUOC, TQ_ILIS, TQ_VBDLIS]
    # Chưa chọn: form theo lựa chọn cổng đang để (quy trình đầu = form gốc).
    assert case_pipeline_options(flow.get_procedure(TQ_DAT_DAI), conv) == {}

    picked = await flow.handle_turn(conv, Intent("action", "set_mae_dialog", {"process": 2}))
    action = next(a for a in picked.actions if a["type"] == "fill_mae_agency")
    assert action["processExact"] == TQ_VBDLIS
    assert conv["state"] == "guide_login"
    assert case_pipeline_options(flow.get_procedure(TQ_DAT_DAI), conv) == {"quyTrinh": "vbdlis"}


@pytest.mark.parametrize("key, labels, pick, options", [
    (TQ_DAT_DAI, (TQ_5_BUOC, TQ_ILIS, TQ_VBDLIS), 0, {}),
    (TQ_DAT_DAI, (TQ_5_BUOC, TQ_ILIS, TQ_VBDLIS), 1, {"quyTrinh": "ilis"}),
    (TQ_DINH_CHINH, ("Quy trình 5 bước - 10 ngày", "iLis cấp xã"), 0, {}),
    (TQ_DINH_CHINH, ("Quy trình 5 bước - 10 ngày", "iLis cấp xã"), 1, {"quyTrinh": "ilis"}),
    (TQ_GIAO_DAT, ("Quy trình 20 ngày", "1.013949_VBDLIS_25 Ngày"), 0, {}),
    (TQ_GIAO_DAT, ("Quy trình 20 ngày", "1.013949_VBDLIS_25 Ngày"), 1, {"quyTrinh": "vbdlis"}),
])
async def test_tuyen_quang_lua_chon_nao_thi_pipeline_dien_form_cua_quy_trinh_do(key, labels, pick, options):
    conv = _tq_conv(key)
    proc = flow.get_procedure(key)
    flow._mae_dialog_on_page(conv, _dialog_ctx(*labels), proc)
    assert conv["state"] == "choose_mae_dialog"
    picked = await flow.handle_turn(conv, Intent("action", "set_mae_dialog", {"process": pick}))
    assert next(a for a in picked.actions if a["type"] == "fill_mae_agency")["processExact"] == labels[pick]
    assert case_pipeline_options(proc, conv) == options


async def test_tuyen_quang_khong_doc_duoc_hop_thoai_thi_hoi_ba_quy_trinh_khai_san():
    """Extension không đọc được lựa chọn (page_status chỉ báo hộp thoại đang mở) → hỏi 3 quy trình khai sẵn; quy trình 5
    bước chọn trên cổng bằng cách TRÁNH cả iLis lẫn VBDLIS."""
    conv = _tq_conv(TQ_DAT_DAI)
    reply = await flow.handle_turn(conv, Intent("event", "page_status", {"maeAgencyBlock": True}))
    assert conv["state"] == "choose_variant"
    assert len(reply.chips) >= 3 and "ba" in reply.tts_text

    picked = await flow.handle_turn(conv, Intent("action", "set_variant", {"value": "nam_buoc"}))
    action = next(a for a in picked.actions if a["type"] == "fill_mae_agency")
    assert (action["variantMatch"], action["variantAvoid"]) == ("", "ilis|vbdlis")
    assert case_pipeline_options(flow.get_procedure(TQ_DAT_DAI), conv) == {}

    conv = _tq_conv(TQ_DAT_DAI)
    await flow.handle_turn(conv, Intent("event", "page_status", {"maeAgencyBlock": True}))
    picked = await flow.handle_turn(conv, Intent("action", "set_variant", {"value": "ilis"}))
    action = next(a for a in picked.actions if a["type"] == "fill_mae_agency")
    assert (action["variantMatch"], action["variantAvoid"]) == ("ilis", "")
    assert case_pipeline_options(flow.get_procedure(TQ_DAT_DAI), conv) == {"quyTrinh": "ilis"}


@pytest.mark.parametrize("key, label, expect, absent", [
    (TQ_DAT_DAI, TQ_ILIS, {"data[ownerFullname]", "data[village2]"}, "data[district]"),
    (TQ_DAT_DAI, TQ_VBDLIS, {"data[SoThuTuThua]", "data[noidungyeucaugiaiquyet]"}, "data[village2]"),
    (TQ_DAT_DAI, TQ_5_BUOC, {"data[district]", "data[hinhThucNop]"}, "data[ownerFullname]"),
    (TQ_DINH_CHINH, "iLis cấp xã", {"data[ownerFullname]", "data[province2]"}, "data[district]"),
    (TQ_GIAO_DAT, "1.013949_VBDLIS_25 Ngày", {"data[SoThuTuThua]", "data[ownerFullname]"}, "data[textField]"),
])
async def test_tuyen_quang_run_process_dien_dung_form_cua_quy_trinh_da_chon(monkeypatch, key, label, expect, absent):
    """Lượt điền thật của trợ lý (chỉ giả OCR + LLM): quy trình công dân chốt ở hộp thoại → đúng bộ ô của form đó."""
    from app.channels.handfree.chat import pipeline_runner, tracing
    from app.pipelines._shared.compact_agent import runner

    conv = _tq_conv(key)
    conv.update({"_id": "c-tq", "state": "filling", "mae_dialog_options": _dialog_ctx(label)["maeDialogOptions"],
                 "mae_dialog_choice_labels": {"process": label}})
    facts = {"ChuHoSo_HoTen": "Trần Thị Bình", "ChuHoSo_NgaySinh": "05/03/1985", "ChuHoSo_SoDinhDanh": "008185012345",
             "ChuHoSo_NoiCuTru": {"tinh": "Tuyên Quang", "xa": "Xã Thượng Lâm", "chiTietDuoiXa": "Thôn Bản Bó"},
             "ThuaDat_DiaChi": {"tinh": "Tuyên Quang", "xa": "Xã Thượng Lâm"}, "ThuaDat_SoThua": "45",
             "Don_NoiDungDeNghi": "Đề nghị cấp Giấy chứng nhận"}

    async def fake_run(files_by_role, **kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in facts.items()], "errors": []}

    monkeypatch.setattr(runner, "run", fake_run)
    monkeypatch.setattr(pipeline_runner.up_store, "get", AsyncMock(return_value={"_id": "s1", "files": []}))
    monkeypatch.setattr(pipeline_runner, "_session_files", lambda sess: [{"name": "don.pdf", "type": "application/pdf",
                                                                           "dataUrl": "x"}])
    monkeypatch.setattr(pipeline_runner.conv_store, "get", AsyncMock(return_value=conv))
    monkeypatch.setattr(pipeline_runner.conv_store, "save", AsyncMock())
    monkeypatch.setattr(pipeline_runner, "_load_owner_user", AsyncMock(return_value=None))
    monkeypatch.setattr(pipeline_runner, "_start_recorder", lambda *a, **k: None)
    monkeypatch.setattr(pipeline_runner, "_finish_recorder", lambda *a, **k: None)
    monkeypatch.setattr(pipeline_runner, "broadcast", AsyncMock())
    monkeypatch.setattr(tracing, "record_process", AsyncMock(return_value="req-tq"))

    await pipeline_runner.run_process.__wrapped__("c-tq", "s1", key)

    assert conv["pipeline_status"] == "fields_ready", conv.get("pipeline_error")
    names = {item["name"] for item in conv["fields"] if not item.get("clear")}
    assert expect <= names and absent not in names


# ── Cổng iGate Khánh Hòa 1.013995: trang nps/apply "Chọn trường hợp giải quyết" (Đơn vị thực hiện + 4 quy trình) ──
KH_TAI_SAN = "dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn-khanh-hoa"
KH_NHA_TRANG = "Chi nhánh Văn phòng Đăng ký đất đai Nha Trang"
KH_CAM_RANH = "Chi nhánh Văn phòng Đăng ký đất đai Cam Ranh"
KH_CASES = (
    "1.013995-1.1 Đối với trường hợp đăng ký quyền sở hữu tài sản gắn liền với thửa đất đã cấp Giấy chứng nhận - Đối "
    "với trường hợp còn lại",
    "1.013995-1.2 Đối với trường hợp đăng ký quyền sở hữu tài sản gắn liền với thửa đất đã cấp Giấy chứng nhận - Đối "
    "với xã miền núi, hải đảo",
    "1.013995-2.1 Đối với trường hợp đăng ký thay đổi về tài sản gắn liền với đất so với nội dung đã đăng ký - Đối với "
    "trường hợp còn lại",
    "1.013995-2.2 Đối với trường hợp đăng ký thay đổi về tài sản gắn liền với đất so với nội dung đã đăng ký - Đối với "
    "xã miền núi, hải đảo",
)


def _kh_conv(ward="Phường Nam Nha Trang"):
    conv = _sua_chua_conv(KH_TAI_SAN)
    conv["auth_user"] = {"id": "u1", "province_slug": "khanhhoa"}
    conv["location"] = {"province": "Tỉnh Khánh Hòa", "province_slug": "khanhhoa", "ward": ward}
    return conv


def _kh_ctx(agencies, current):
    return {"maeAgencyBlock": True,
            "maeDialogOptions": {"agency": {"options": list(agencies), "current": current},
                                 "process": {"options": list(KH_CASES), "current": KH_CASES[0]}}}


async def test_khanh_hoa_hoi_truong_hop_giu_chi_nhanh_cua_xa_roi_chon_ho():
    """Ô Đơn vị thực hiện liệt kê nhiều chi nhánh VPĐK: giữ chi nhánh của xã tài khoản (đã chọn ở DVCQG), chỉ hỏi 4
    trường hợp giải quyết; chọn quy trình 2.x thì pipeline biết là đăng ký thay đổi về tài sản."""
    conv = _kh_conv()
    reply = await flow.handle_turn(conv, Intent("event", "page_status", _kh_ctx((KH_CAM_RANH, KH_NHA_TRANG), KH_CAM_RANH)))
    assert conv["state"] == "choose_mae_dialog"
    (group,) = reply.cards[0]["groups"]
    assert group["key"] == "process" and [o["label"] for o in group["options"]] == list(KH_CASES)
    proc = flow.get_procedure(KH_TAI_SAN)
    assert case_pipeline_options(proc, conv) == {}

    picked = await flow.handle_turn(conv, Intent("action", "set_mae_dialog", {"process": 2}))
    action = next(a for a in picked.actions if a["type"] == "fill_mae_agency")
    assert (action["agencyExact"], action["processExact"]) == (KH_NHA_TRANG, KH_CASES[2])
    assert case_pipeline_options(proc, conv) == {"truongHop": "thay_doi"}


def test_khanh_hoa_don_vi_khong_khop_chi_nhanh_cua_xa_thi_van_hoi():
    conv = _kh_conv()
    odd = ("Văn phòng Đăng ký đất đai tỉnh Khánh Hòa", "Trung tâm phục vụ hành chính công")
    flow._mae_dialog_on_page(conv, _kh_ctx(odd, odd[0]), flow.get_procedure(KH_TAI_SAN))
    assert conv["state"] == "choose_mae_dialog"
    assert conv["mae_dialog_options"]["agency"]["options"] == list(odd)


@pytest.mark.parametrize("key, code", [
    ("dang-ky-dat-dai-lan-dau-khanh-hoa", "1.013978"),
    ("giao-thue-chuyen-muc-dich-dat-khanh-hoa", "1.013949"),
    ("cap-doi-gcn-khanh-hoa", "1.012783"),
    ("dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-khanh-hoa", "1.013831"),
])
async def test_khanh_hoa_4_thu_tuc_dau_cung_hoi_truong_hop_giai_quyet_roi_chon_ho(key, code):
    """4 thủ tục Khánh Hòa đầu từng khai wizard thường (không maePortal) → trợ lý bỏ qua trang "Chọn trường hợp giải
    quyết". Nay đọc trang, hỏi công dân khi có nhiều quy trình, chọn hộ đúng nhãn và bấm Đồng ý; một form mọi quy trình
    nên pipeline không nhận options ép form."""
    conv = _kh_conv()
    conv["procedure_key"] = key
    cases = (f"{code}-1.1 Đối với trường hợp còn lại", f"{code}-1.2 Đối với xã miền núi, hải đảo")
    ctx = {"maeAgencyBlock": True,
           "maeDialogOptions": {"agency": {"options": [KH_NHA_TRANG], "current": KH_NHA_TRANG},
                                "process": {"options": list(cases), "current": cases[0]}}}
    reply = await flow.handle_turn(conv, Intent("event", "page_status", ctx))
    assert conv["state"] == "choose_mae_dialog"
    (group,) = reply.cards[0]["groups"]
    assert group["key"] == "process" and [o["label"] for o in group["options"]] == list(cases)

    picked = await flow.handle_turn(conv, Intent("action", "set_mae_dialog", {"process": 1}))
    action = next(a for a in picked.actions if a["type"] == "fill_mae_agency")
    assert (action["agencyExact"], action["processExact"]) == (KH_NHA_TRANG, cases[1])
    assert case_pipeline_options(flow.get_procedure(key), conv) == {}
