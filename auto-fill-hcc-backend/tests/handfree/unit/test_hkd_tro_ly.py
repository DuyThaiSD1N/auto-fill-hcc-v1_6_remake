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
         "thong-tin-ve-von", "thong-tin-ve-thue", "nguoi-nop-ho-so"]


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


async def _drive(conv, first, limit=80, same=None):
    """Giả extension: mở khối → báo đã tới; sao chép tài khoản (người nộp) → báo kết quả so với chủ hộ; lưu khối → báo
    lưu xong; còn lại trả lời / xác nhận. Ghi lại mọi lệnh."""
    log = {"saves": [], "fills": [], "focus": [], "confirms": [], "opens": [], "copies": []}
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
        copy = next((a for a in r.actions if a["type"] == "hkd_fill"
                     and any(f["name"] in ("__copySubmitter", "__copyAccount") for f in a["fields"])), None)
        if copy:
            if copy["fields"][0]["name"] == "__copySubmitter":
                log["copies"].append(copy["fields"][0]["value"])
            else:
                log.setdefault("owner_copies", []).append(copy["page"])
            r = await hkd.handle(conv, PROC, Intent("event", "hkd_copied",
                                                    {"page": copy["page"], "copied": True, "same": same}))
        elif "start_business_registration" in types:
            log["saves"].append(next(a for a in r.actions if a["type"] == "start_business_registration"))
            r = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))
        elif "hkd_open_block" in types:
            page = next(a for a in r.actions if a["type"] == "hkd_open_block")["page"]
            log["opens"].append({"page": page})
            r = await hkd.handle(conv, PROC, Intent("event", "hkd_arrived", {"page": page}))
        elif st.get("phase") == "offer":
            log.setdefault("offers", []).append(r.display_md)
            r = await hkd.handle(conv, PROC, Intent("action", "hkd_fill_missing"))
        elif st.get("phase") == "confirm_list":
            log.setdefault("lists", []).append(hkd._page(st))
            r = await hkd.handle(conv, PROC, Intent("action", "hkd_fill_block"))
        elif st.get("phase") == "confirm":
            log["confirms"].append(hkd._page(st))
            r = await hkd.handle(conv, PROC, Intent("action", "hkd_save"))
        else:
            r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "trả lời"}))
    raise AssertionError(f"kẹt: khối {hkd._page(conv['hkd'])} mục {conv['hkd'].get('field')}")


_ANSWERS = {
    "dia_chi_kd": {"tinh": "Bắc Ninh", "xa": "Kinh Bắc", "diaChi": "Số 5 Ngô Gia Tự", "quocGia": "Việt Nam"},
    "dien_thoai": "0912345678", "email": "__skip__", "fax": "__skip__", "website": "__skip__", "nganh_them": False,
    "khong_kd_tru_so": True, "ten_ho": "Phở Hùng", "ten_nuoc_ngoai": "__skip__", "ten_viet_tat": "__skip__",
    "chu_ho_la_ban": True, "chu_the": "ca_nhan", "noi_o": "giong", "von": 50000000,
    "dia_chi_thue": True, "ngay_bat_dau": "01/12/2026", "so_lao_dong": 2,
}


def test_chi_bat_khi_co_capability_tieng_viet_va_thanh_lap_moi(monkeypatch):
    monkeypatch.setattr(hkd, "NO_DOCS_ENABLED", True)
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
    assert first.actions[0]["businessFlow"]["pageOrder"] == ["hinh-thuc-dang-ky"], "hình thức: nói rồi tự lưu"
    assert "Thành lập mới" in first.display_md
    r, log = await _drive(conv, first)
    assert [s["businessFlow"]["pageOrder"][0] for s in log["saves"]] == ORDER
    assert all(len(s["pages"]) == 1 for s in log["saves"]), "mỗi lần lưu đúng một khối"
    assert "nguoi-nop-ho-so" in log["confirms"], "người nộp: điền nơi ở chủ hộ ngay rồi chờ xác nhận Lưu"
    assert not any(a["page"] in ("hinh-thuc-dang-ky", hkd.AUTH_PAGE) for a in log["opens"]), \
        "khối không hỏi thì lưu thẳng, không mở + chờ báo tới"
    assert log["copies"] == [{"owner": None}], "khối người nộp: sao chép tài khoản; chủ hộ là người đăng nhập"
    nop = next(s for s in log["saves"] if "nguoi-nop-ho-so" in s["pages"])["pages"]["nguoi-nop-ho-so"]
    assert next(f for f in nop if f["name"].endswith("PERS_SUBGroup"))["value"].startswith("Người có thẩm quyền")
    assert "dia-chi" in log["confirms"] and "thong-tin-ve-von" in log["confirms"]
    # Trả lời địa chỉ → điền NGAY khối địa chỉ (tỉnh → xã → số nhà) trên trang Địa chỉ.
    addr = next(f for f in log["fills"] if f["page"] == "dia-chi" and
                any(x["name"].endswith("ADDRCtl$WARD_IDFld") for x in f["fields"]))
    assert {x["name"].split("$")[-1]: x["value"] for x in addr["fields"]}["WARD_IDFld"] == "Kinh Bắc"
    assert any(f["names"] == hkd._DOM["von"] for f in log["focus"]), "trỏ vào ô vốn khi hỏi"
    # Kinh doanh tại địa chỉ → KHÔNG tích ô "Không kinh doanh tại trụ sở" (gửi false để bỏ tích nếu vừa sửa lại).
    dia_chi = next(s for s in log["saves"] if "dia-chi" in s["pages"])["pages"]["dia-chi"]
    assert next(f for f in dia_chi if f["name"].endswith("NO_BUSINESS_HEADOFFICEld"))["value"] is False
    nganh = next(s for s in log["saves"] if "nganh-nghe-kinh-doanh" in s["pages"])["pages"]["nganh-nghe-kinh-doanh"]
    lines = next(f for f in nganh if f["name"] == "__businessLines")["value"]
    assert lines["codes"] == ["5610"] and lines["main"] == "5610"
    assert lines["items"][0]["name"] == "Bán phở bò", "ô chi tiết ghi lời công dân, không phải tên chuẩn"
    assert log["owner_copies"] == ["chu-ho-kinh-doanh"], "chủ hộ là người đăng nhập → sao chép, chờ trang reload"
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
    conv["hkd"]["submitter_owner"] = False
    conv["hkd"]["block"] = hkd._blocks(conv["hkd"]).index(hkd.AUTH_PAGE)
    conv["hkd"]["phase"] = "open"
    await hkd.handle(conv, PROC, Intent("event", "hkd_arrived", {"page": hkd.AUTH_PAGE, "missing": True}))
    assert conv["hkd"]["phase"] == "done" and conv["state"] == "done"


async def test_ket_qua_luu_cu_khong_lam_nhay_khoi(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=0, phase="saving", saving_at=time.time())
    stale = {"ok": True, "createdAt": (time.time() - 60) * 1000}
    await hkd.handle(conv, PROC, Intent("event", "page_status", {"businessResult": stale}))
    assert conv["hkd"]["phase"] == "saving" and conv["hkd"]["block"] == 0
    fresh = {"ok": True, "createdAt": (time.time() + 1) * 1000}
    await hkd.handle(conv, PROC, Intent("event", "page_status", {"businessResult": fresh}))
    assert conv["hkd"]["block"] == 1 and conv["hkd"]["phase"] == "open"


async def test_mo_khoi_sai_trang_thi_mo_lai_co_tran(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=1, phase="open", open_tries=1, opened_at=time.time() - 30)
    for _ in range(2):
        r = await hkd.handle(conv, PROC, Intent("event", "page_status", {"businessPageKey": "nganh-nghe-kinh-doanh"}))
        assert r.actions and r.actions[0]["type"] == "hkd_open_block"
        conv["hkd"]["opened_at"] = time.time() - 30
    r = await hkd.handle(conv, PROC, Intent("event", "page_status", {"businessPageKey": "nganh-nghe-kinh-doanh"}))
    assert not any(a["type"] == "hkd_open_block" for a in r.actions) and "menu bên trái" in r.display_md


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
    assert conv["hkd"]["field"] == "nganh_them" and "chi tiết: Bán bia, rượu" in r.display_md
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_value", {"v": False}))
    assert conv["hkd"]["phase"] == "confirm_list", "một ngành → không hỏi ngành chính, sang xác nhận danh sách"
    assert "(ngành chính)" in r.display_md and r.chips[0]["send"] == "__action:hkd_fill_block"


async def test_dong_khong_ma_ben_dong_co_ma_phai_ro_hoac_bo(monkeypatch):
    _fake_lookup(monkeypatch, [("quán bún", ["5610"], True, "Bán bún"), ("việc vặt", [], False, "")], chinh="5610")
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=2, phase="ask", field="nganh")
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "quán bún, làm việc vặt"}))
    assert conv["hkd"]["field"] == "nganh_ro"
    await hkd.handle(conv, PROC, Intent("action", "hkd_pick", {"row": 1, "drop": True}))
    assert len(conv["hkd"]["nganh"]) == 1 and conv["hkd"]["field"] == "nganh_them"


_DOCS_FULL = [
    {"name": "HoKinhDoanh_Ten", "value": "A"}, {"name": "TruSo_DiaChi", "value": {"tinh": "X", "xa": "Y", "diaChi": "Số 1"}},
    {"name": "TruSo_DienThoai", "value": "0912345678"}, {"name": "ChuHo_Email", "value": "a@example.com"},
    {"name": "Von_SoTien", "value": "100000000"}, {"name": "Thue_NgayBatDau", "value": "01/12/2026"},
    {"name": "Thue_SoLaoDong", "value": "1"}, {"name": "ChuHo_HoTen", "value": "B"},
    {"name": "ChuHo_SoDinhDanh", "value": "099090000001"}, {"name": "ChuHo_DiaChi", "value": {"tinh": "X", "xa": "Y", "diaChi": "Số 2"}},
    {"name": "NganhNghe_DanhSach", "value": [{"ma": "4722", "ten": "Bán lẻ thực phẩm", "chinh": True}]},
]


async def test_co_giay_dien_luon_moi_khoi_roi_bao_o_thieu_va_bo_sung(monkeypatch):
    _fake_answers(monkeypatch, _ANSWERS)
    conv = _conv(business_facts=_DOCS_FULL, pipeline_status="business_ready", upload_session_id="s1",
                 attach_plan=[{"fileIndex": 0}])
    assert hkd.needs_review(conv, PROC)
    first = await hkd.start_review(conv)
    fill = first.actions[0]
    assert fill["type"] == "start_business_registration" and "pageOrder" not in (fill["businessFlow"] or {}), \
        "điền luôn mọi khối một lượt như luồng tờ khai"
    assert {"dia-chi", "thong-tin-ve-von", "chu-ho-kinh-doanh"} <= set(fill["pages"])
    assert fill["attachments"] == [{"fileIndex": 0}] and fill["session_id"] == "s1"
    r, log = await _drive(conv, first)
    offer = log["offers"][0]
    assert "Còn thiếu" in offer and "số fax" in offer and "vốn" not in offer, "đọc danh sách ô còn thiếu theo khối"
    assert "bổ sung thông tin" in offer
    opened = [o["page"] for o in log["opens"]]
    assert opened == ["dia-chi", "ten-ho-kinh-doanh", "nguoi-nop-ho-so"], \
        "chỉ mở khối còn thiếu (ô không bắt buộc cũng hỏi) + khối người nộp"
    assert log["copies"] == [{"owner": {"hoTen": "B", "soDinhDanh": "099090000001"}}], "so tài khoản với chủ hộ trên giấy"
    assert all(not s["attachments"] for s in log["saves"][1:]), "tệp đã đính ở lượt điền luôn"
    owner = log["saves"][0]["pages"]["chu-ho-kinh-doanh"]
    assert not any(f["name"] == "__copyAccount" for f in owner), "chủ hộ lấy từ giấy tờ"


async def test_co_giay_thieu_von_bao_thieu_roi_chi_hoi_von(monkeypatch):
    docs = [f for f in _DOCS_FULL if f["name"] != "Von_SoTien"] + [
        {"name": "TruSo_Fax", "value": "0241"}, {"name": "TruSo_Website", "value": "a.vn"},
        {"name": "HoKinhDoanh_TenNuocNgoai", "value": "A"}, {"name": "HoKinhDoanh_TenVietTat", "value": "A"}]
    _fake_answers(monkeypatch, {**_ANSWERS, "von": 30000000})
    conv = _conv(business_facts=docs, pipeline_status="business_ready")
    r, log = await _drive(conv, await hkd.start_review(conv))
    assert "vốn kinh doanh" in log["offers"][0]
    assert [o["page"] for o in log["opens"]] == ["dia-chi", "thong-tin-ve-von", "nguoi-nop-ho-so"]
    von = next(s for s in log["saves"] if list(s["pages"]) == ["thong-tin-ve-von"])["pages"]["thong-tin-ve-von"]
    assert von[0]["value"]
    assert conv["hkd"]["phase"] == "done"


async def test_co_giay_du_het_van_qua_buoc_nguoi_nop(monkeypatch):
    _fake_answers(monkeypatch, {**_ANSWERS, "nguoi_nop_noi_o": {"tinh": "X", "xa": "Z", "diaChi": "Số 1",
                                                               "quocGia": "Việt Nam"}})
    docs = _DOCS_FULL + [{"name": "TruSo_Fax", "value": "0241"}, {"name": "TruSo_Website", "value": "a.vn"},
                         {"name": "HoKinhDoanh_TenNuocNgoai", "value": "A"}, {"name": "HoKinhDoanh_TenVietTat", "value": "A"}]
    conv = _conv(business_facts=docs, pipeline_status="business_ready")
    await hkd.start_review(conv)
    conv["hkd"]["values"]["khong_kd_tru_so"] = True
    r = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))
    assert "Người nộp hồ sơ" in r.display_md and "Địa chỉ" not in r.display_md, "chỉ còn bước người nộp"
    r, log = await _drive(conv, r, same=False)
    assert [s["businessFlow"]["pageOrder"][0] for s in log["saves"]][-2:] == ["nguoi-nop-ho-so", hkd.AUTH_PAGE], \
        "người đăng nhập khác chủ hộ trên giấy → ủy quyền, lưu thêm khối Thông tin Ủy quyền"
    assert conv["hkd"]["phase"] == "done"


def test_kiem_dang_gia_tri():
    assert hoi_dap.check("phone", "0912 345 678", "", False) == ("0912345678", "")
    assert hoi_dap.check("phone", "912345678", "", False) == (None, "912345678")
    assert hoi_dap.check("id12", "", "không không một không chín không không không không không không một", True) \
        == ("001090000001", "")
    assert hoi_dap.check("date", "31/02/2026", "", False) == (None, "")
    assert hoi_dap.check("address", {"tinh": "", "xa": ""}, "", False) == (None, "")
    assert hoi_dap.check("address", {"tinh": "X", "xa": ""}, "", False)[0]["tinh"] == "X", "hỏi từng phần: chỉ tỉnh"
    assert hoi_dap.check("address", "giong", "", False, allow_same=True) == ("giong", "")
    addr, _ = hoi_dap.check("address", {"tinh": "X", "xa": "Y", "diaChi": "Thôn Đông"}, "", False)
    assert addr["diaChi"] == "Thôn Đông", "client LLM đổi chiTietDuoiXa → diaChi"
    addr, _ = hoi_dap.check("address", {"tinh": "", "xa": "lien chieu", "diaChi": "so 10 duong mau"},
                            "không, gửi về số 10 đường Mẫu phường Liên Chiểu", False)
    assert (addr["xa"], addr["diaChi"]) == ("Liên Chiểu", "số 10 đường Mẫu"), "model bỏ dấu → lấy lại từ lời công dân"
    addr, _ = hoi_dap.check("address", {"xa": "liên chiểu"}, "phường Liên Chiểu", True)
    assert addr["xa"] == "Liên Chiểu", "model viết thường → lấy lại chữ hoa theo lời công dân"
    addr, _ = hoi_dap.check("address", {"xa": "Liên Chiểu"}, "phuong lien chieu", True)
    assert addr["xa"] == "Liên Chiểu", "công dân gõ không dấu → giữ bản có dấu của model"


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


def test_y_dinh_khong_co_to_khai_chi_mo_khi_luong_ho_kinh_doanh_bat(monkeypatch):
    from app.channels.handfree.chat import intents
    monkeypatch.setattr(hkd, "NO_DOCS_ENABLED", True)
    hkd_conv = _conv(procedure_key="dang-ky-kinh-doanh")
    values = [e["value"] for e in intents._state_entries("consent", hkd_conv)]
    assert "consent_no_docs" in values
    assert "hkd_no_docs" in [e["value"] for e in intents._state_entries("ask_doc_method", hkd_conv)]
    assert "consent_no_docs" not in [e["value"] for e in intents._state_entries(
        "consent", _conv(procedure_key="dang-ky-kinh-doanh", client_capabilities={}))], "bản extension trên chợ"
    assert "consent_no_docs" not in [e["value"] for e in intents._state_entries(
        "consent", _conv(procedure_key="ket-hon"))], "thủ tục khác"


async def test_noi_khong_co_to_khai_o_buoc_dong_y_la_dong_y_va_vao_hoi_dap(monkeypatch):
    monkeypatch.setattr(hkd, "NO_DOCS_ENABLED", True)
    from app.channels.handfree.chat import consent as consent_log
    from app.channels.handfree.chat import flow

    async def persist(entry):
        return None
    monkeypatch.setattr(consent_log, "persist", persist)
    conv = _conv(consent={}, procedure_key="dang-ky-kinh-doanh", state="consent")
    r = await flow._handle_consent(conv, Intent("action", "consent_no_docs"))
    assert conv["consent"]["accepted"] is True and conv["hkd"]["mode"] == "khong_giay"
    assert [a["type"] for a in r.actions][:2] == ["consent_verbal", "start_business_registration"]


async def test_them_nganh_thu_hai_roi_bat_buoc_hoi_nganh_chinh(monkeypatch):
    calls = []

    async def fake_lookup(text, current=None):
        calls.append([r["ma"] for r in current or []])
        rows = [nganh_nghe.Nganh(**{"hoat_dong": r["hoatDong"], "ma": r["ma"], "chac": r["chac"],
                                     "chi_tiet": r.get("chiTiet", "")}) for r in current or []]
        rows.append(nganh_nghe.Nganh("bán rau", ["4722"], True, "Bán rau"))
        return nganh_nghe.KetQua(nganh=rows)
    monkeypatch.setattr(nganh_nghe, "tra_cuu", fake_lookup)

    async def fake_interpret(text, asking, question, slots, values, location):
        return hoi_dap.Parsed("tra_loi", nganh_text="bán rau")
    monkeypatch.setattr(hoi_dap, "interpret", fake_interpret)
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=2, phase="ask", field="nganh_them", asked=True,
                       nganh=[{"hoatDong": "cafe", "ma": ["5630"], "chac": True, "chiTiet": "Bán cafe"}])
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "còn bán rau nữa"}))
    assert [r["ma"][0] for r in conv["hkd"]["nganh"]] == ["5630", "4722"], "ngành cũ được giữ"
    assert calls[-1] == [["5630"]], "agent nhận danh sách đang có"
    assert conv["hkd"]["field"] == "nganh_them"
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_value", {"v": False}))
    assert conv["hkd"]["field"] == "nganh_chinh", "nhiều ngành → phải hỏi ngành chính, không tự chọn"
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_pick", {"chinh": "4722"}))
    assert conv["hkd"]["phase"] == "confirm_list"
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_fill_block"))
    save = next(a for a in r.actions if a["type"] == "start_business_registration")
    lines = next(f for f in save["pages"]["nganh-nghe-kinh-doanh"] if f["name"] == "__businessLines")["value"]
    assert lines["codes"] == ["5630", "4722"] and lines["main"] == "4722"
    r = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))
    assert conv["hkd"]["phase"] == "confirm" and conv["hkd"]["block"] == 2, "điền xong → chờ xác nhận lưu"
    assert vi.HKD_LIST_FILLED["md"].split("{")[0] in r.display_md
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_save"))
    assert conv["hkd"]["block"] == 3, "xác nhận → sang khối kế (dòng đã lưu khi điền)"


async def test_llm_khong_quyet_duoc_cau_khong_co_o_o_bo_qua_duoc_thi_bo_qua(monkeypatch):
    async def fake(text, asking, question, slots, values, location):
        return hoi_dap.Parsed("khong_ro")
    monkeypatch.setattr(hoi_dap, "interpret", fake)
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=1, phase="ask", field="website", asked=True)
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "Không có."}))
    assert "website" in conv["hkd"]["skipped"]
    conv["hkd"].update(field="von")
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "không có"}))
    assert "von" not in conv["hkd"]["skipped"], "mục bắt buộc không bị bỏ qua"


async def test_dia_chi_hoi_lan_luot_tinh_xa_so_nha_dien_ngay_tung_phan(monkeypatch):
    parts = iter([{"tinh": "Cần Thơ", "xa": "", "diaChi": ""}, {"tinh": "", "xa": "Ninh Kiều", "diaChi": ""},
                  {"tinh": "", "xa": "", "diaChi": "Số 12 đường 3/2"}])
    questions = []

    async def fake(text, asking, question, slots, values, location):
        questions.append(question)
        return hoi_dap.Parsed("tra_loi", {asking: hoi_dap.check("address", next(parts), "", True)[0]})
    monkeypatch.setattr(hoi_dap, "interpret", fake)
    conv = _conv(location={"province": "Thành phố Cần Thơ", "ward": "Phường Ninh Kiều"})
    await hkd.start_no_docs(conv)
    first = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))  # lưu xong hình thức
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_arrived", {"page": first.actions[0]["page"]}))
    assert "Đã vào khối **Địa chỉ**" in r.display_md and "địa chỉ kinh doanh và các thông tin liên quan" in r.display_md
    assert "tỉnh, thành phố" in r.display_md, "tỉnh luôn hỏi dù cổng để sẵn tỉnh của tài khoản"
    assert any(c["label"] == "Thành phố Cần Thơ" for c in r.chips)
    assert next(a for a in r.actions if a["type"] == "hkd_focus")["names"] == [hkd._DOM["dia_chi_kd"][0]]
    seen = []
    for _ in range(3):
        r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "trả lời"}))
        fill = next(a for a in r.actions if a["type"] == "hkd_fill")
        seen.append({f["name"].split("$")[-1] for f in fill["fields"]})
        if conv["hkd"]["field"] == "dia_chi_kd":
            focus = next(a for a in r.actions if a["type"] == "hkd_focus")["names"]
            assert focus == [hkd._DOM["dia_chi_kd"][len(seen)]], "trỏ đúng ô xã rồi ô số nhà"
    assert "CITY_IDFld" in seen[0] and "WARD_IDFld" not in seen[0], "trả lời tỉnh → điền ngay ô tỉnh"
    assert "WARD_IDFld" in seen[1] and "STREET_NUMBERFld" in seen[2]
    assert conv["hkd"]["values"]["dia_chi_kd"]["tinh"] == "Cần Thơ"
    assert conv["hkd"]["values"]["dia_chi_kd"]["xa"] == "Ninh Kiều"
    assert conv["hkd"]["field"] == "dien_thoai"
    assert "xã, phường" in r.display_md or "Số điện thoại" in r.display_md


async def test_dia_chi_noi_ca_cau_thi_khong_hoi_tung_phan(monkeypatch):
    _fake_answers(monkeypatch, _ANSWERS)
    conv = _conv()
    await hkd.start_no_docs(conv)
    first = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))
    await hkd.handle(conv, PROC, Intent("event", "hkd_arrived", {"page": first.actions[0]["page"]}))
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "số 5 Ngô Gia Tự, Kinh Bắc, Bắc Ninh"}))
    assert conv["hkd"]["field"] == "dien_thoai"


def test_doi_tinh_thi_bo_xa_cu():
    st = {"values": {"dia_chi_kd": {"tinh": "Bắc Ninh", "xa": "Kinh Bắc", "diaChi": "Số 5"}}, "member": {}}
    hkd._apply(st, "dia_chi_kd", {"tinh": "Cần Thơ", "xa": "", "diaChi": ""})
    assert hkd._addr_part(st["values"]["dia_chi_kd"]) == "xa"
    hkd._apply(st, "dia_chi_kd", {"tinh": "", "xa": "Ninh Kiều", "diaChi": ""})
    assert st["values"]["dia_chi_kd"]["tinh"] == "Cần Thơ"


async def test_nguoi_nop_khac_chu_ho_thi_uy_quyen_hoi_noi_o_va_luu_khoi_uy_quyen(monkeypatch):
    answers = {**_ANSWERS, "chu_ho_la_ban": False, "chu_ho_ho_ten": "Nguyễn Văn Mẫu", "chu_ho_gioi_tinh": "Nam",
               "chu_ho_ngay_sinh": "01/02/1980", "chu_ho_so_dinh_danh": "099080000001",
               "noi_o": {"tinh": "Bắc Ninh", "xa": "Kinh Bắc", "diaChi": "Số 9", "quocGia": "Việt Nam"},
               "nguoi_nop_noi_o": {"tinh": "Bắc Ninh", "xa": "Vũ Ninh", "diaChi": "Số 7 Lý Thái Tổ", "quocGia": "Việt Nam"}}
    _fake_lookup(monkeypatch, [("Mở quán phở bò", ["5610"], True, "Bán phở bò")], chinh="5610")
    _fake_answers(monkeypatch, answers)
    conv = _conv()
    r, log = await _drive(conv, await hkd.start_no_docs(conv), same=False)
    assert log["copies"] == [{"owner": {"hoTen": "Nguyễn Văn Mẫu", "soDinhDanh": "099080000001"}}], \
        "so tài khoản vừa sao chép với chủ hộ đã khai"
    assert [s["businessFlow"]["pageOrder"][0] for s in log["saves"]][-2:] == ["nguoi-nop-ho-so", hkd.AUTH_PAGE]
    role = next(f for f in log["fills"] if any(x["name"].endswith("PERS_SUBGroup") for x in f["fields"]))
    assert role["fields"][0]["value"] == "Người được ủy quyền", "tick ngay vai trò trên trang"
    save = next(s for s in log["saves"] if "nguoi-nop-ho-so" in s["pages"])
    nop = {f["name"]: f["value"] for f in save["pages"]["nguoi-nop-ho-so"]}
    assert nop["ctl00$C$PERS_SUBGroup"] == "Người được ủy quyền"
    assert nop["ctl00$C$PERSCtl$ADDRCCtl$WARD_IDFld"] == "Vũ Ninh", "nơi ở người nộp = câu trả lời, không phải chủ hộ"
    assert nop["__applicantAddress"]["other"]["xa"] == "Vũ Ninh"
    assert save["businessFlow"]["owner"]["soDinhDanh"] == "099080000001"
    assert "nguoi-nop-ho-so" in log["confirms"]


async def test_dia_ban_ep_nguoi_co_tham_quyen_van_hoi_noi_o_nguoi_nop(monkeypatch):
    answers = {**_ANSWERS, "chu_ho_la_ban": False, "chu_ho_ho_ten": "Nguyễn Văn Mẫu", "chu_ho_gioi_tinh": "Nam",
               "chu_ho_ngay_sinh": "01/02/1980", "chu_ho_so_dinh_danh": "099080000001", "noi_o": "giong",
               "nguoi_nop_noi_o": {"tinh": "Đà Nẵng", "xa": "Liên Chiểu", "diaChi": "Số 7", "quocGia": "Việt Nam"}}
    _fake_lookup(monkeypatch, [("Mở quán phở bò", ["5610"], True, "Bán phở bò")], chinh="5610")
    _fake_answers(monkeypatch, answers)
    conv = _conv(location={"province": "Thành phố Đà Nẵng", "ward": "Phường Liên Chiểu"})
    r, log = await _drive(conv, await hkd.start_no_docs(conv), same=False)
    assert log["saves"][-1]["businessFlow"]["pageOrder"] == ["nguoi-nop-ho-so"], "không có khối ủy quyền"
    nop = {f["name"]: f["value"] for f in log["saves"][-1]["pages"]["nguoi-nop-ho-so"]}
    assert nop["ctl00$C$PERS_SUBGroup"].startswith("Người có thẩm quyền")
    assert nop["__applicantAddress"]["other"]["xa"] == "Liên Chiểu"


async def test_phan_dia_chi_model_ghi_ngoai_ma_muc_van_nhan(monkeypatch):
    async def fake_chat(messages, **kw):
        return '{"hanhDong": "tra_loi", "giaTri": {"xa": "Tân An"}}'
    monkeypatch.setattr(hoi_dap, "llm_chat", fake_chat)
    slots = [{"key": "dia_chi_kd", "label": "Địa chỉ kinh doanh", "kind": "address"}]
    parsed = await hoi_dap.interpret("Tân An", "dia_chi_kd", "", slots, {}, "")
    assert parsed.values["dia_chi_kd"]["xa"] == "Tân An"


async def test_hoi_chu_ho_co_phai_nguoi_dang_nhap_kem_ten_roi_sao_chep_chi_hoi_noi_o(monkeypatch):
    _fake_answers(monkeypatch, _ANSWERS)
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=hkd._blocks(conv["hkd"]).index("chu-ho-kinh-doanh"), phase="open")
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_arrived",
                                            {"page": "chu-ho-kinh-doanh", "accountName": "NGUYỄN VĂN MẪU"}))
    assert conv["hkd"]["field"] == "chu_the", "hỏi cá nhân / hộ gia đình trước"
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "một mình"}))
    assert conv["hkd"]["field"] == "chu_ho_la_ban" and "NGUYỄN VĂN MẪU" in r.display_md
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "đúng rồi"}))
    assert conv["hkd"]["phase"] == "copy" and vi.HKD_OWNER_COPY["md"][:20] in r.display_md
    assert r.actions[0]["fields"][0]["name"] == "__copyAccount" and not r.chips, "chưa hỏi gì khi trang sắp reload"
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_copied", {"page": "chu-ho-kinh-doanh", "copied": True}))
    assert conv["hkd"]["field"] == "noi_o", "sao chép xong chỉ hỏi nơi ở"


async def test_moi_cau_hoi_kem_lenh_tro_o_de_mic_ranh_tay_mo_lai(monkeypatch):
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=hkd._blocks(conv["hkd"]).index("nganh-nghe-kinh-doanh"), phase="open")
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_arrived", {"page": "nganh-nghe-kinh-doanh"}))
    assert conv["hkd"]["field"] == "nganh" and not r.chips
    assert any(a["type"] == "hkd_focus" for a in r.actions), "câu hỏi không có nút vẫn phải mở lại mic"


async def test_chon_nganh_chinh_trong_danh_sach_khong_tra_ma_lai(monkeypatch):
    async def fake_pick(text, question, options):
        return (1, False) if "năm sáu" in text else (None, "thêm" in text)
    looked = []

    async def fake_lookup(text, current=None):
        looked.append(text)
        return nganh_nghe.KetQua(nganh=[nganh_nghe.Nganh(r["hoatDong"], r["ma"], r["chac"], r.get("chiTiet", ""))
                                        for r in current or []])
    monkeypatch.setattr(hoi_dap, "pick", fake_pick)
    monkeypatch.setattr(nganh_nghe, "tra_cuu", fake_lookup)
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    rows = [{"hoatDong": "a", "ma": ["4773"], "chac": True, "chiTiet": "Bán hoa"},
            {"hoatDong": "b", "ma": ["5610"], "chac": True, "chiTiet": "Bán phở"}]
    conv["hkd"].update(block=hkd._blocks(conv["hkd"]).index("nganh-nghe-kinh-doanh"), phase="ask", field="nganh_chinh",
                       nganh=rows, nganh_done=True, asked=True)
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "ờ"}))
    assert conv["hkd"]["field"] == "nganh_chinh" and not looked, "không rõ → hỏi lại, không đưa agent tra mã"
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "cái năm sáu một không"}))
    assert conv["hkd"]["chinh"] == "5610" and not looked
    conv["hkd"].update(field="nganh_chinh", chinh="", phase="ask")
    await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "thêm bán bánh mì"}))
    assert looked == ["thêm bán bánh mì"], "muốn đổi danh sách → agent tra mã"


async def test_khong_kinh_doanh_tai_tru_so_tich_va_sua_lai_thi_bo_tich():
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=hkd._blocks(conv["hkd"]).index("dia-chi"), phase="ask", field="khong_kd_tru_so")
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_value", {"v": False}))
    fill = next(a for a in r.actions if a["type"] == "hkd_fill")["fields"]
    assert fill == [{"name": "ctl00$C$NO_BUSINESS_HEADOFFICEld", "comp": "dom-checkbox", "value": True}]
    assert "tích ô" in r.display_md
    conv["hkd"].update(phase="ask", field="khong_kd_tru_so")
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_value", {"v": True}))
    fill = next(a for a in r.actions if a["type"] == "hkd_fill")["fields"]
    assert fill[0]["value"] is False, "sửa lại thành có kinh doanh tại địa chỉ → bỏ tích"


async def test_ten_ho_kiem_trung_tren_cong_trung_thi_hoi_giu_hay_doi(monkeypatch):
    _fake_answers(monkeypatch, {**_ANSWERS, "ten_ho": "Phở Hùng"})
    conv = _conv(client_capabilities={hkd.CAPABILITY: True, hkd.NAME_CHECK_CAPABILITY: True})
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=hkd._blocks(conv["hkd"]).index("ten-ho-kinh-doanh"), phase="ask", field="ten_ho")
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "phở hùng"}))
    check = next(a for a in r.actions if a["type"] == "hkd_check_name")
    assert check["name"] == "PHỞ HÙNG" and check["kind"] == "vi" and conv["hkd"]["phase"] == "check_name"
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_name_checked", {
        "slot": "ten_ho", "name": "PHỞ HÙNG", "ok": True, "names": ["PHỞ HÙNG CƯỜNG", "PHỞ HÙNG", "PHỞ HÙNG"],
        "text": "Có 7 Hộ kinh doanh (đơn vị trực thuộc) có tên trùng, tương tự như : PHỞ HÙNG"}))
    assert conv["hkd"]["field"] == "ten_ho_giu" and "7 hộ kinh doanh" in r.display_md and "2 hộ trùng hẳn" in r.display_md
    assert [c["label"] for c in r.chips] == [vi.HKD_NAME_KEEP_LABEL, vi.HKD_NAME_CHANGE_LABEL]
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_value", {"v": False}))
    assert conv["hkd"]["field"] == "ten_ho", "đổi tên → hỏi lại tên"
    _fake_answers(monkeypatch, {**_ANSWERS, "ten_ho": "Phở Hùng Mẫu"})
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "phở hùng mẫu"}))
    assert next(a for a in r.actions if a["type"] == "hkd_check_name")["name"] == "PHỞ HÙNG MẪU", "tên mới kiểm lại"
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_name_checked", {
        "slot": "ten_ho", "name": "PHỞ HÙNG MẪU", "ok": True, "names": [],
        "text": "Không có Hộ kinh doanh (đơn vị trực thuộc) nào có tên trùng, tương tự như : PHỞ HÙNG MẪU"}))
    assert "không có hộ kinh doanh nào trùng" in r.display_md and conv["hkd"]["field"] == "ten_nuoc_ngoai"


async def test_extension_cu_khong_khai_kiem_ten_thi_khong_cho_ket_qua(monkeypatch):
    _fake_answers(monkeypatch, {**_ANSWERS, "ten_ho": "Phở Hùng"})
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    conv["hkd"].update(block=hkd._blocks(conv["hkd"]).index("ten-ho-kinh-doanh"), phase="ask", field="ten_ho")
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_answer", {"text": "phở hùng"}))
    assert not any(a["type"] == "hkd_check_name" for a in r.actions) and conv["hkd"]["field"] == "ten_nuoc_ngoai"


async def test_co_giay_chu_ho_tu_nop_ma_giay_khong_co_noi_o_thi_hoi_noi_o_nguoi_nop(monkeypatch):
    answers = {**_ANSWERS, "nguoi_nop_noi_o": {"tinh": "Bắc Ninh", "xa": "Bắc Giang", "diaChi": "Tổ Mão Trì",
                                                "quocGia": "Việt Nam"}, "noi_o": "__skip__"}
    _fake_answers(monkeypatch, answers)
    docs = [f for f in _DOCS_FULL if f["name"] != "ChuHo_DiaChi"]
    conv = _conv(business_facts=docs, pipeline_status="business_ready")
    await hkd.start_review(conv)
    await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))  # xong lượt điền luôn
    st = conv["hkd"]
    st.update(block=hkd._blocks(st).index("nguoi-nop-ho-so"), phase="copy", only_missing=True)
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_copied", {"page": "nguoi-nop-ho-so", "copied": True,
                                                                   "same": True}))
    assert st["field"] == "nguoi_nop_noi_o" and "Chưa có nơi ở" in r.display_md
    r, log = await _drive(conv, r)
    nop = {f["name"]: f["value"] for f in log["saves"][0]["pages"]["nguoi-nop-ho-so"]}
    assert nop["ctl00$C$PERSCtl$ADDRCCtl$WARD_IDFld"] == "Bắc Giang"
    assert nop["__applicantAddress"]["self"]["xa"] == "Bắc Giang" and nop["ctl00$C$PERS_SUBGroup"].startswith("Người có")


async def test_dia_chi_tren_giay_thieu_xa_thi_hoi_lai_tu_tinh():
    docs = [f for f in _DOCS_FULL if f["name"] != "TruSo_DiaChi"] + [
        {"name": "TruSo_DiaChi", "value": {"tinh": "Cần Thơ", "xa": "", "diaChi": ""}}]
    conv = _conv(business_facts=docs, pipeline_status="business_ready")
    await hkd.start_review(conv)
    assert hkd._addr_part(conv["hkd"]["values"].get("dia_chi_kd")) == "tinh", "có sẵn tỉnh vẫn hỏi từ tỉnh"
    assert "dia_chi_kd" in hkd._missing_items(conv["hkd"], "dia-chi")


async def test_nguoi_nop_la_chu_ho_dien_ngay_noi_o_chu_ho_roi_cho_xac_nhan_luu(monkeypatch):
    _fake_answers(monkeypatch, _ANSWERS)
    conv = _conv(business_facts=_DOCS_FULL, pipeline_status="business_ready")
    await hkd.start_review(conv)
    await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True}))
    st = conv["hkd"]
    st.update(block=hkd._blocks(st).index("nguoi-nop-ho-so"), phase="copy", only_missing=True)
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_copied", {"page": "nguoi-nop-ho-so", "copied": True,
                                                                   "same": True}))
    fill = next(a for a in r.actions if a["type"] == "hkd_fill")["fields"]
    assert {f["name"].split("$")[-1]: f["value"] for f in fill}["STREET_NUMBERFld"] == "Số 2", "điền ngay nơi ở chủ hộ"
    assert st["phase"] == "confirm" and "nơi ở của chủ hộ" in r.display_md, "đọc lại rồi chờ bấm Lưu, không tự lưu"
    assert not any(a["type"] == "start_business_registration" for a in r.actions)


async def test_luu_du_khoi_moi_chuan_bi_loi_thi_doc_loi_xong_thi_nut_nop():
    conv = _conv(client_capabilities={hkd.CAPABILITY: True, hkd.PREPARE_CAPABILITY: True, hkd.SUBMIT_CAPABILITY: True})
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    r = hkd._finish(conv, ("", ""))
    assert not r.actions and r.chips[0]["send"] == "__action:hkd_prepare", "không tự bấm Chuẩn bị — mời công dân"
    assert "sửa nốt" in r.display_md and conv["hkd"]["phase"] == "ready_prepare"
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_prepare"))
    assert r.actions == [{"type": "hkd_prepare"}] and conv["hkd"]["phase"] == "prepare"
    errors = ["(Người nộp hồ sơ) Phường/Xã trong địa chỉ liên hệ của người nộp hồ sơ là bắt buộc"]
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_prepared", {"ok": False, "errors": errors}))
    assert "1 lỗi" in r.display_md and errors[0] in r.display_md and r.chips[0]["send"] == "__action:hkd_prepare"
    await hkd.handle(conv, PROC, Intent("action", "hkd_prepare"))
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_prepared", {"ok": True}))
    assert conv["state"] == "done" and r.chips == [hkd._submit_chip()] and not r.actions, "chuẩn bị xong → nút Nộp"
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_submit"))
    assert r.actions == [{"type": "hkd_submit"}] and "OK" in r.display_md
    r = await hkd.handle(conv, PROC, Intent("event", "hkd_submit_failed", {}))
    assert r.chips == [hkd._submit_chip()], "không bấm được → nút Nộp lại"


def test_noi_nop_ho_so_bang_loi_phai_hoi_xac_nhan():
    from app.channels.handfree.chat import flow
    assert hkd.SUBMIT_SEND in flow._VOICE_CONFIRM_SENDS


async def test_extension_chua_khai_chuan_bi_thi_ket_thuc_nhu_cu():
    conv = _conv()
    conv["hkd"] = await hkd._base_state(conv, "khong_giay")
    r = hkd._finish(conv, ("", ""))
    assert not r.actions and conv["state"] == "done"


async def test_tam_tat_loi_vao_khong_giay_to_luon_phai_dua_giay(monkeypatch):
    from app.channels.handfree.chat import consent as consent_log
    from app.channels.handfree.chat import flow, intents

    async def persist(entry):
        return None
    monkeypatch.setattr(consent_log, "persist", persist)
    assert hkd.NO_DOCS_ENABLED is False
    conv = _conv(procedure_key="dang-ky-kinh-doanh")
    assert hkd.consent_card_extra(conv, PROC) == {} and hkd.no_docs_chip(conv, PROC) is None, "không còn nút"
    assert "consent_no_docs" not in [e["value"] for e in intents._state_entries("consent", conv)], "không còn ý định"
    assert "hkd_no_docs" not in [e["value"] for e in intents._state_entries("ask_doc_method", conv)]
    assert await hkd.handle(conv, PROC, Intent("action", "hkd_no_docs")) is None
    conv = _conv(consent={}, procedure_key="dang-ky-kinh-doanh", state="consent")
    await flow._handle_consent(conv, Intent("action", "consent", {"accepted": True, "checks": [True, True],
                                                                  "noDocs": True}))
    assert "hkd" not in conv and conv["consent"]["accepted"] is True, "thẻ cũ gửi noDocs → đồng ý bình thường, đi tải giấy"
