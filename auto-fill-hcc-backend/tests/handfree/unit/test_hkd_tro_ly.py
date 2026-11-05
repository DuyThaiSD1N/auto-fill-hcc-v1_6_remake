"""Trợ lý hộ kinh doanh (chat/hkd_tro_ly): đi từng khối trên HkdOnline, hỏi tới ô nào điền ngay ô đó, LLM được mock."""
import time

import pytest

from app.channels.handfree.chat import hkd_tro_ly as hkd
from app.channels.handfree.chat import pipeline_runner, router
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.hkd_tro_ly import hoi_dap, nganh_nghe
from app.channels.handfree.chat.intents import Intent

PROC = {"key": "dang-ky-kinh-doanh", "businessWorkflow": "create"}
ORDER = ["hinh-thuc-dang-ky", "dia-chi", "nganh-nghe-kinh-doanh", "ten-ho-kinh-doanh", "chu-ho-kinh-doanh",
         "thong-tin-ve-von", "thong-tin-ve-thue", "nguoi-nop-ho-so", "thong-tin-uy-quyen"]


def _conv(**extra):
    conv = {"_id": "c1", "client_capabilities": {hkd.CAPABILITY: True}, "lang": "vi",
            "consent": {"accepted": True}, "location": {"province": "Tỉnh Bắc Ninh", "ward": "Phường Kinh Bắc"}}
    conv.update(extra)
    return conv


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    async def no_user(conv, sess):
        return None
    monkeypatch.setattr(pipeline_runner, "_load_owner_user", no_user)


def _fake_lookup(monkeypatch, rows, chinh="", hoi_lai=""):
    async def fake(text, current=None):
        return nganh_nghe.KetQua(nganh=[nganh_nghe.Nganh(*r) for r in rows], chinh=chinh, hoi_lai=hoi_lai)
    monkeypatch.setattr(nganh_nghe, "tra_cuu", fake)


def _fake_answers(monkeypatch, answers: dict):
    """Mục đang hỏi → giá trị trả lời (LLM giả). Bảng xác nhận khối → đồng ý."""
    async def fake(text, asking, question, slots, values, location):
        if asking == "tom_tat":
            return hoi_dap.Parsed("dong_y")
        value = answers.get(asking, "__unclear__")
        if value == "__unclear__":
            return hoi_dap.Parsed("khong_ro")
        if value == "__skip__":
            return hoi_dap.Parsed("bo_qua")
        return hoi_dap.Parsed("tra_loi", {asking: value})
    monkeypatch.setattr(hoi_dap, "interpret", fake)


async def _drive(conv, first, limit=80):
    """Giả extension: mở khối → báo đã tới; lưu khối → báo lưu xong; còn lại trả lời / xác nhận. Ghi lại mọi lệnh."""
    log = {"saves": [], "fills": [], "focus": [], "confirms": []}
    r = first
    for _ in range(limit):
        st = conv.get("hkd") or {}
        if st.get("phase") == "done":
            return r, log
        types = [a["type"] for a in r.actions]
        for a in r.actions:
            if a["type"] == "hkd_fill":
                log["fills"].append(a)
            if a["type"] == "hkd_focus" and a["names"]:
                log["focus"].append(a)
        if "start_business_registration" in types:
            log["saves"].append(next(a for a in r.actions if a["type"] == "start_business_registration"))
            r = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))
        elif "hkd_open_block" in types:
            page = next(a for a in r.actions if a["type"] == "hkd_open_block")["page"]
            r = await hkd.handle(conv, PROC, Intent("event", "hkd_arrived", {"page": page}))
        elif st.get("phase") == "confirm":
            log["confirms"].append(hkd._page(st))
            r = await hkd.handle(conv, PROC, Intent("action", "hkd_save"))
        else:
            r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "trả lời"}))
    raise AssertionError(f"kẹt: khối {hkd._page(conv['hkd'])} mục {conv['hkd'].get('field')}")


_ANSWERS = {
    "dia_chi_kd": {"tinh": "Bắc Ninh", "xa": "Kinh Bắc", "diaChi": "Số 5 Ngô Gia Tự", "quocGia": "Việt Nam"},
    "dien_thoai": "0912345678", "email": "__skip__", "fax": "__skip__", "website": "__skip__",
    "khong_kd_tru_so": True, "ten_ho": "Phở Hùng", "ten_nuoc_ngoai": "__skip__", "ten_viet_tat": "__skip__",
    "chu_ho_la_ban": True, "chu_the": "ca_nhan", "noi_o": "giong", "von": 50000000,
    "dia_chi_thue": True, "ngay_bat_dau": "01/12/2026", "so_lao_dong": 2,
}


def test_chi_bat_khi_co_capability_tieng_viet_va_thanh_lap_moi():
    assert hkd.active(_conv(), PROC)
    assert not hkd.active(_conv(client_capabilities={}), PROC), "bản extension cũ trên chợ"
    assert not hkd.active(_conv(lang="hmong"), PROC)
    assert not hkd.active(_conv(), {**PROC, "businessWorkflow": "change"})
    assert hkd.consent_card_extra(_conv(), PROC) == {"no_docs_label": vi.HKD_NO_DOCS_LABEL}
    assert hkd.consent_card_extra(_conv(client_capabilities={}), PROC) == {}


def test_router_whitelist_capability():
    assert router._clean_client_capabilities({hkd.CAPABILITY: True}).get(hkd.CAPABILITY) is True


async def test_khong_giay_to_di_tung_khoi_hoi_toi_dau_dien_toi_do(monkeypatch):
    _fake_lookup(monkeypatch, [("Mở quán phở bò", ["5610"], True, "Bán phở bò")], chinh="5610")
    _fake_answers(monkeypatch, _ANSWERS)
    conv = _conv()
    first = await hkd.start_no_docs(conv)
    assert first.actions == [{"type": "hkd_open_block", "page": "hinh-thuc-dang-ky", "label": "Hình thức đăng ký"}]
    r, log = await _drive(conv, first)
    assert [s["businessFlow"]["pageOrder"][0] for s in log["saves"]] == ORDER
    assert all(len(s["pages"]) == 1 for s in log["saves"]), "mỗi lần lưu đúng một khối"
    assert "hinh-thuc-dang-ky" not in log["confirms"] and "nguoi-nop-ho-so" not in log["confirms"], \
        "khối không phải hỏi gì thì tự lưu"
    assert "dia-chi" in log["confirms"] and "thong-tin-ve-von" in log["confirms"]
    # Trả lời địa chỉ → điền NGAY khối địa chỉ (tỉnh → xã → số nhà) trên trang Địa chỉ.
    addr = next(f for f in log["fills"] if f["page"] == "dia-chi" and
                any(x["name"].endswith("ADDRCtl$WARD_IDFld") for x in f["fields"]))
    assert {x["name"].split("$")[-1]: x["value"] for x in addr["fields"]}["WARD_IDFld"] == "Kinh Bắc"
    assert any(f["names"] == hkd._DOM["von"] for f in log["focus"]), "trỏ vào ô vốn khi hỏi"
    # Kinh doanh tại địa chỉ → KHÔNG tích ô "Không kinh doanh tại trụ sở".
    dia_chi = next(s for s in log["saves"] if "dia-chi" in s["pages"])["pages"]["dia-chi"]
    assert not any(f["name"].endswith("NO_BUSINESS_HEADOFFICEld") for f in dia_chi)
    nganh = next(s for s in log["saves"] if "nganh-nghe-kinh-doanh" in s["pages"])["pages"]["nganh-nghe-kinh-doanh"]
    lines = next(f for f in nganh if f["name"] == "__businessLines")["value"]
    assert lines["codes"] == ["5610"] and lines["main"] == "5610"
    assert lines["items"][0]["name"] == "Bán phở bò", "ô chi tiết ghi lời công dân, không phải tên chuẩn"
    owner = next(s for s in log["saves"] if "chu-ho-kinh-doanh" in s["pages"])["pages"]["chu-ho-kinh-doanh"]
    assert owner[0] == {"name": "__copyAccount", "comp": "raw", "value": True}
    assert not any(f["name"].endswith("FULL_NAMEFld") for f in owner), "không hỏi/bịa nhân thân"
    assert set(conv["hkd"]["skipped"]) == {"email", "fax", "website", "ten_nuoc_ngoai", "ten_viet_tat"}
    assert conv["state"] == "done" and vi.HKD_DONE["md"].split("{")[0] in r.display_md


async def test_ho_gia_dinh_co_khoi_thanh_vien(monkeypatch):
    _fake_lookup(monkeypatch, [("Bán tạp hoá", ["4711"], True, "Bán tạp hoá")], chinh="4711")
    answers = {**_ANSWERS, "chu_the": "ho_gia_dinh", "tv_ho_ten": "Nguyễn Văn A", "tv_gioi_tinh": "Nam",
               "tv_ngay_sinh": "01/02/1990", "tv_so_dinh_danh": "099090000001", "tv_noi_o": "giong", "tv_them": False}
    _fake_answers(monkeypatch, answers)
    conv = _conv()
    r, log = await _drive(conv, await hkd.start_no_docs(conv))
    order = [s["businessFlow"]["pageOrder"][0] for s in log["saves"]]
    assert order.index(hkd.MEMBERS_PAGE) == order.index("chu-ho-kinh-doanh") + 1
    owner = next(s for s in log["saves"] if "chu-ho-kinh-doanh" in s["pages"])["pages"]["chu-ho-kinh-doanh"]
    assert next(f for f in owner if f["name"] == "ctl00$C$OWNER_TYPE_RbBox")["value"] == "M"
    members = next(s for s in log["saves"] if hkd.MEMBERS_PAGE in s["pages"])["pages"][hkd.MEMBERS_PAGE][0]["value"]
    assert len(members) == 1
    assert {f["name"].split("$")[-1]: f["value"] for f in members[0]}["PERS_DOC_NOFld"] == "099090000001"


async def test_khoi_uy_quyen_khong_co_thi_bo_qua(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"]["block"] = len(hkd._blocks(conv["hkd"])) - 1
    conv["hkd"]["phase"] = "open"
    await hkd.handle(conv, PROC, Intent("event", "hkd_arrived", {"page": hkd.AUTH_PAGE, "missing": True}))
    assert conv["hkd"]["phase"] == "done" and conv["state"] == "done"


async def test_ket_qua_luu_cu_khong_lam_nhay_khoi(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=1, phase="saving", saving_at=time.time())
    stale = {"ok": True, "createdAt": (time.time() - 60) * 1000}
    await hkd.handle(conv, PROC, Intent("event", "page_status", {"businessResult": stale}))
    assert conv["hkd"]["phase"] == "saving" and conv["hkd"]["block"] == 1
    fresh = {"ok": True, "createdAt": (time.time() + 1) * 1000}
    await hkd.handle(conv, PROC, Intent("event", "page_status", {"businessResult": fresh}))
    assert conv["hkd"]["block"] == 2 and conv["hkd"]["phase"] == "open"


async def test_mo_khoi_sai_trang_thi_mo_lai_co_tran(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=1, phase="open", open_tries=1, opened_at=time.time() - 30)
    for _ in range(2):
        r = await hkd.handle(conv, PROC, Intent("event", "page_status", {"businessPageKey": "hinh-thuc-dang-ky"}))
        assert r.actions and r.actions[0]["type"] == "hkd_open_block"
        conv["hkd"]["opened_at"] = time.time() - 30
    r = await hkd.handle(conv, PROC, Intent("event", "page_status", {"businessPageKey": "hinh-thuc-dang-ky"}))
    assert not r.actions and "menu bên trái" in r.display_md


async def test_so_dinh_danh_sai_do_dai_thi_hoi_lai(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=4, phase="ask", field="chu_ho_so_dinh_danh", values={"chu_ho_la_ban": False})

    async def fake(text, asking, question, slots, values, location):
        return hoi_dap.Parsed("tra_loi", bad_digits={"chu_ho_so_dinh_danh": "00109000"})
    monkeypatch.setattr(hoi_dap, "interpret", fake)
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "không không một ..."}))
    assert "8 số" in r.display_md and "chu_ho_so_dinh_danh" not in conv["hkd"]["values"]


async def test_muc_bat_buoc_khong_bo_qua_duoc(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=5, phase="ask", field="von")
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_skip"))
    assert vi.HKD_REQUIRED["md"] in r.display_md and conv["hkd"]["field"] == "von"


async def test_nganh_phan_van_bam_chon_ma_roi_ghi_chi_tiet(monkeypatch):
    _fake_lookup(monkeypatch, [("bán bia rượu", ["4723", "4633"], False, "Bán bia, rượu")])
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=2, phase="ask", field="nganh")
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "bán bia rượu"}))
    assert conv["hkd"]["field"] == "nganh_chon"
    assert [c["send"] for c in r.chips] == ['__action:hkd_pick:{"row":0,"ma":"4723"}',
                                            '__action:hkd_pick:{"row":0,"ma":"4633"}']
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_pick", {"row": 0, "ma": "4723"}))
    assert conv["hkd"]["phase"] == "confirm" and conv["hkd"]["chinh"] == "4723"
    assert "chi tiết: Bán bia, rượu" in r.display_md


async def test_dong_khong_ma_ben_dong_co_ma_phai_ro_hoac_bo(monkeypatch):
    _fake_lookup(monkeypatch, [("quán bún", ["5610"], True, "Bán bún"), ("việc vặt", [], False, "")], chinh="5610")
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=2, phase="ask", field="nganh")
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "quán bún, làm việc vặt"}))
    assert conv["hkd"]["field"] == "nganh_ro"
    await hkd.handle(conv, PROC, Intent("action", "hkd_pick", {"row": 1, "drop": True}))
    assert len(conv["hkd"]["nganh"]) == 1 and conv["hkd"]["phase"] == "confirm"


_DOCS_FULL = [
    {"name": "HoKinhDoanh_Ten", "value": "A"}, {"name": "TruSo_DiaChi", "value": {"tinh": "X", "xa": "Y"}},
    {"name": "TruSo_DienThoai", "value": "0912345678"}, {"name": "ChuHo_Email", "value": "a@example.com"},
    {"name": "Von_SoTien", "value": "100000000"}, {"name": "Thue_NgayBatDau", "value": "01/12/2026"},
    {"name": "Thue_SoLaoDong", "value": "1"}, {"name": "ChuHo_HoTen", "value": "B"},
    {"name": "ChuHo_SoDinhDanh", "value": "099090000001"}, {"name": "ChuHo_DiaChi", "value": {"tinh": "X", "xa": "Y"}},
    {"name": "NganhNghe_DanhSach", "value": [{"ma": "4722", "ten": "Bán lẻ thực phẩm", "chinh": True}]},
]


async def test_co_giay_du_thi_tu_luu_tung_khoi_khong_hoi_dinh_kem_khoi_cuoi(monkeypatch):
    conv = _conv(business_facts=_DOCS_FULL, pipeline_status="business_ready", upload_session_id="s1",
                 attach_plan=[{"fileIndex": 0}])
    assert hkd.needs_review(conv, PROC)
    r, log = await _drive(conv, await hkd.start_review(conv))
    assert not log["confirms"], "đủ thông tin thì không hỏi, không bắt xác nhận"
    assert [s["businessFlow"]["pageOrder"][0] for s in log["saves"]] == ORDER
    assert log["saves"][-1]["attachments"] == [{"fileIndex": 0}] and log["saves"][-1]["session_id"] == "s1"
    assert all(not s["attachments"] for s in log["saves"][:-1])
    owner = next(s for s in log["saves"] if "chu-ho-kinh-doanh" in s["pages"])["pages"]["chu-ho-kinh-doanh"]
    assert not any(f["name"] == "__copyAccount" for f in owner), "chủ hộ lấy từ tờ khai"


async def test_co_giay_thieu_von_chi_hoi_von(monkeypatch):
    docs = [f for f in _DOCS_FULL if f["name"] != "Von_SoTien"]
    _fake_answers(monkeypatch, {"von": 30000000})
    conv = _conv(business_facts=docs, pipeline_status="business_ready")
    r, log = await _drive(conv, await hkd.start_review(conv))
    assert log["confirms"] == ["thong-tin-ve-von"]
    von = next(s for s in log["saves"] if "thong-tin-ve-von" in s["pages"])["pages"]["thong-tin-ve-von"]
    assert von[0]["value"]


def test_kiem_dang_gia_tri():
    assert hoi_dap.check("phone", "0912 345 678", "", False) == ("0912345678", "")
    assert hoi_dap.check("phone", "912345678", "", False) == (None, "912345678")
    assert hoi_dap.check("id12", "", "không không một không chín không không không không không không một", True) \
        == ("001090000001", "")
    assert hoi_dap.check("date", "31/02/2026", "", False) == (None, "")
    assert hoi_dap.check("address", {"tinh": "X", "xa": ""}, "", False) == (None, "")
    assert hoi_dap.check("address", "giong", "", False, allow_same=True) == ("giong", "")
    addr, _ = hoi_dap.check("address", {"tinh": "X", "xa": "Y", "diaChi": "Thôn Đông"}, "", False)
    assert addr["diaChi"] == "Thôn Đông", "client LLM đổi chiTietDuoiXa → diaChi"


def test_agent_nganh_chot_chan_tat_dinh():
    data = {"nganh": [{"hoatDong": "a", "ma": ["9999", "5610"], "chac": True, "chiTiet": "Bán phở"},
                      {"hoatDong": "b", "ma": ["4722"], "chac": True},
                      {"hoatDong": "c", "ma": ["4711", "4719", "4722", "4723"], "chac": False}], "chinh": "4722"}
    out = nganh_nghe._clean(data, viewed={"5610"})
    assert out.nganh[0].ma == ["5610"] and out.nganh[0].chac and out.nganh[0].chi_tiet == "Bán phở"
    assert out.nganh[1].ma == ["4722"] and not out.nganh[1].chac, "chưa đọc nội dung → không được chắc"
    assert len(out.nganh[2].ma) == 3
    assert out.chinh == "", "ngành chính phải là mã đã chắc"


def test_runner_chi_tra_facts_khi_handfree_yeu_cau():
    import inspect
    from app.pipelines.dang_ky_kinh_doanh.process import runner
    assert 'if opts.get("returnFacts"):' in inspect.getsource(runner.run)
    src = inspect.getsource(pipeline_runner.run_business_registration)
    assert 'process_result.pop("facts", None)' in src.split("_note_result(rec, process_result)")[0]


async def test_khoi_khac_vang_trong_menu_thi_nho_bam_tay_khong_bo_qua(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=1, phase="open")
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_arrived", {"page": "dia-chi", "missing": True}))
    assert conv["hkd"]["block"] == 1 and "menu bên trái" in r.display_md


def test_cau_co_khong_nhan_chu_model_hay_ghi():
    assert hoi_dap.check("yesno", "giong", "", True) == (True, "")
    assert hoi_dap.check("yesno", "không", "", True) == (False, "")
    assert hoi_dap.check("yesno", "abc", "", True) == (None, "")
