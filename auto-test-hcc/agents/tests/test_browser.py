"""Lớp chặn nộp hồ sơ chạy trong Chromium thật. Đây là chốt chặn quan trọng nhất của chế độ cổng thật nên phải
kiểm bằng cú click thật, không kiểm bằng cách đọc code."""
import pytest
from playwright.sync_api import sync_playwright

import browser
import scoring
from browser import GUARD_JS

PAGE = """
<form onsubmit="window.__sent = 'form'; return false;">
  <input name="data[hoTen]">
  <button id="luu" type="button" onclick="window.__sent = 'luu'">Lưu nháp</button>
  <button id="nop" type="button" onclick="window.__sent = 'nop'">Lưu và nộp hồ sơ</button>
  <button id="gui" type="submit">Gửi hồ sơ</button>
  <a id="the" href="#" onclick="window.__sent = 'the'; return false;">Nộp hồ sơ</a>
  <div id="div" class="ant-btn" onclick="window.__sent = 'div'"><span id="chu">Nộp trực tuyến</span></div>
</form>
"""


@pytest.fixture(scope="module")
def chromium():
    with sync_playwright() as pw:
        instance = pw.chromium.launch()
        yield instance
        instance.close()


def tab_at(chromium, host):
    tab = chromium.new_page()
    tab.add_init_script(GUARD_JS)
    tab.route(f"https://{host}/**", lambda route: route.fulfill(content_type="text/html; charset=utf-8", body=PAGE))
    return tab


@pytest.fixture(scope="module")
def page(chromium):
    return tab_at(chromium, "cong-gia.gov.vn")


def fresh(page, reached):
    page.goto("https://cong-gia.gov.vn/nop-ho-so")
    page.evaluate("(v) => { window.__autotestFormReached = v; window.__sent = null; }", reached)


@pytest.mark.parametrize("target", ["#nop", "#gui", "#the", "#div", "#chu"])
def test_toi_to_khai_roi_thi_moi_nut_nop_bi_chan(page, target):
    fresh(page, True)
    page.click(target)
    assert page.evaluate("() => window.__sent") is None
    assert page.evaluate("() => window.__autotestBlocked.length") >= 1


def test_nut_khac_van_bam_duoc(page):
    fresh(page, True)
    page.click("#luu")
    assert page.evaluate("() => window.__sent") == "luu"


def test_chua_toi_to_khai_thi_khong_chan_nut_tren_the_co_quan(page):
    # Người dùng phải bấm được "Nộp hồ sơ" trên thẻ cơ quan thì mới vào được tờ khai.
    fresh(page, False)
    page.click("#the")
    assert page.evaluate("() => window.__sent") == "the"


def test_chan_ca_click_do_script_goi(page):
    fresh(page, True)
    page.evaluate("() => document.getElementById('nop').click()")
    assert page.evaluate("() => window.__sent") is None


def test_dvcqg_luon_chan_nut_nop_that_ke_ca_khi_chua_bao_toi_to_khai(chromium):
    tab = tab_at(chromium, "dichvucong.gov.vn")
    tab.goto("https://dichvucong.gov.vn/nop-ho-so")
    tab.evaluate("() => { window.__sent = null; }")
    tab.click("#nop")
    assert tab.evaluate("() => window.__sent") is None


def test_preflight_bat_extension_tro_nham_server(tmp_path, monkeypatch):
    (tmp_path / "api").mkdir()
    config = tmp_path / "api/config.js"
    monkeypatch.setattr(browser, "EXT", tmp_path)
    monkeypatch.setenv("DISPLAY", ":99")
    config.write_text('const BACKEND_URL = "https://may-chu-that.example";\n', encoding="utf-8")
    assert "localhost:12005" in browser.preflight()
    config.write_text('const BACKEND_URL = "http://localhost:12005";     // ghi chú\n', encoding="utf-8")
    assert browser.preflight() is None


def test_preflight_theo_backend_thu_cua_server(tmp_path, monkeypatch):
    """Trên server extension của bot trỏ backend thử (12015), không phải 12005."""
    (tmp_path / "api").mkdir()
    config = tmp_path / "api/config.js"
    monkeypatch.setattr(browser, "EXT", tmp_path)
    monkeypatch.setattr(browser, "EXTENSION_BACKEND", "http://localhost:12015")
    monkeypatch.setenv("DISPLAY", ":99")
    config.write_text('const BACKEND_URL = "http://localhost:12005";\n', encoding="utf-8")
    assert "localhost:12015" in browser.preflight()
    config.write_text('const BACKEND_URL = "http://localhost:12015";\n', encoding="utf-8")
    assert browser.preflight() is None


class FakeBot:
    def __init__(self, fails):
        self.fails = list(fails)
        self.calls = []

    def detach(self):
        self.calls.append("detach")

    def attach(self):
        self.calls.append("attach")

    def pick_form_page(self):
        self.calls.append("pick")
        if self.fails:
            raise RuntimeError(self.fails.pop(0))


@pytest.mark.parametrize("html, expected", [
    ('<a href="/dang-nhap">Đăng nhập</a>', False),
    ('<div id="account_name">Nguyễn Văn Bịa</div>', True),
    ('<div class="user-dropdown">Tài khoản</div>', True),
    ('<a href="#">Đăng xuất</a>', True),
    ('<a href="#" style="display:none">Đăng xuất</a>', False),
    ('<div id="account_name" style="display:none">x</div><a href="/dang-nhap">Đăng nhập</a>', False),
])
def test_nhan_biet_da_dang_nhap(chromium, html, expected):
    tab = chromium.new_page()
    tab.set_content(f"<!doctype html><meta charset=utf-8>{html}")
    assert tab.evaluate(browser.LOGGED_IN_JS) is expected
    tab.close()


@pytest.mark.parametrize("url, expected", [
    ("https://sso.dancuquocgia.gov.vn/auth", True),
    ("https://xacthuc.dichvucong.gov.vn/", True),
    ("https://dichvucong.gov.vn/", False),
    ("https://dichvucong.gov.vn/nop-ho-so?formalityId=1", False),
])
def test_nhan_biet_man_dang_nhap(url, expected):
    assert browser._is_auth(url) is expected


def test_dang_o_man_sso_thi_khong_noi_vao_trinh_duyet(monkeypatch):
    monkeypatch.setattr(browser, "_open_urls", lambda port=None: ["https://sso.dancuquocgia.gov.vn/auth"])

    def forbidden(*_args, **_kwargs):
        raise AssertionError("không được nối Playwright khi đang ở màn đăng nhập")

    monkeypatch.setattr(browser, "PortalBot", forbidden)
    assert browser.is_logged_in({}, None, print) is False


class Route:
    def __init__(self, url, method="POST"):
        self.request = type("R", (), {"url": url, "method": method})()
        self.done = None

    def abort(self):
        self.done = "abort"

    def continue_(self):
        self.done = "continue"


def bot_with_guard(armed):
    bot = browser.PortalBot({}, None, lambda _text: None)
    bot.armed = armed
    return bot


def test_lop_chan_mang_chua_bat_khi_dang_vao_to_khai():
    # Extension phải bấm Nộp trực tuyến để vào hồ sơ: bật sớm là chặn chính đường vào.
    route = Route("https://dichvucong.gov.vn/api/nop-ho-so/tao-moi")
    bot_with_guard(False)._route(route)
    assert route.done == "continue"


def test_toi_to_khai_thi_huy_request_co_dang_nop():
    route = Route("https://dichvucong.gov.vn/api/nop-ho-so")
    bot = bot_with_guard(True)
    bot._route(route)
    assert route.done == "abort" and bot.blocked


@pytest.mark.parametrize("path", [
    "/api/v1/submitting/get-formality-case-fees",
    "/api/v1/submitting/search-agencies",
    "/api/v1/submitting/calculate-fee/",
])
def test_lenh_doc_nam_trong_nhanh_submitting_khong_bi_chan(path):
    route = Route(f"https://dichvucong.gov.vn{path}")
    bot = bot_with_guard(True)
    bot._route(route)
    assert route.done == "continue" and not bot.blocked


@pytest.mark.parametrize("path", [
    "/api/v1/submitting/submit",
    "/api/v1/submitting/create-dossier",
    "/api/v1/submitting",
    "/nop-ho-so/gui",
])
def test_lenh_ghi_trong_nhanh_nop_van_bi_chan(path):
    route = Route(f"https://dichvucong.gov.vn{path}")
    bot = bot_with_guard(True)
    bot._route(route)
    assert route.done == "abort" and bot.blocked


def test_toi_to_khai_van_cho_request_tai_tep_va_doc_du_lieu():
    upload = Route("https://dichvucong.gov.vn/api/upload-file-nop-ho-so")
    read = Route("https://dichvucong.gov.vn/api/danh-muc", method="GET")
    bot = bot_with_guard(True)
    bot._route(upload)
    bot._route(read)
    assert upload.done == "continue" and read.done == "continue"


def test_chua_toi_to_khai_thi_nhac_lai_den_khi_thay():
    bot = FakeBot(["Chưa thấy tờ khai"])
    asked = []
    browser._back_to_form(bot, asked.append, "Đăng nhập lại")
    assert asked == ["Đăng nhập lại", "Chưa thấy tờ khai"]
    assert bot.calls == ["detach", "attach", "pick", "detach", "attach", "pick"]


def portal_run(be, form):
    return {"status": "ok", "form": form, "response": {"fields": [{"name": k, "value": v} for k, v in be.items()]}}


def test_cham_tren_gia_tri_that_tren_form_khong_phai_be():
    check = {"field": "a", "op": "equals", "expected": "1"}
    # Backend trả đúng nhưng form không nhận: phải trượt, đó chính là lý do kiểm trên cổng thật.
    assert not scoring.evaluate([check], [portal_run({"a": "1"}, {"a": None})])["allPass"]
    assert scoring.evaluate([check], [portal_run({"a": "1"}, {"a": "1"})])["allPass"]


def test_khong_doc_duoc_form_thi_cham_tren_be():
    check = {"field": "a", "op": "equals", "expected": "1"}
    assert scoring.evaluate([check], [{"status": "ok", "response": {"fields": [{"name": "a", "value": "1"}]}}])["allPass"]


def test_form_gaps_tach_khong_thay_o_va_o_trong():
    runs = [portal_run({"a": "1", "b": "2", "c": "3", "d": False}, {"a": None, "b": "", "c": "3", "d": ""})]
    gaps = {g["field"]: g for g in scoring.form_gaps(runs)}
    assert gaps["a"]["notFound"] == 1 and gaps["b"]["empty"] == 1
    assert "c" not in gaps and "d" not in gaps


def test_bang_cho_agent_co_ca_form_lan_be():
    table = scoring.field_table([], [portal_run({"a": "1"}, {"a": ""})])
    assert table[0]["runs"] == [""] and table[0]["beRuns"] == ["1"]


DIALOG = """
<div id="trang"><button id="tieptuc" onclick="window.__clicked='trang'">Tiếp tục</button></div>
<div role="dialog" class="modal show" style="display:block">
  <button onclick="window.__clicked='nop'">Xác nhận nộp hồ sơ</button>
  <button onclick="window.__clicked='luu'">Lưu và tiếp tục</button>
  <button onclick="window.__clicked='huy'">Không đồng ý</button>
  <button onclick="window.__clicked='xacnhan'">Xác nhận</button>
</div>
"""


def test_tu_bam_xac_nhan_trong_hop_thoai_khong_bao_gio_bam_nop(chromium):
    tab = chromium.new_page()
    tab.set_content(DIALOG)
    found = tab.evaluate(browser.ADVANCE_JS, {"allowPage": False, "click": None})
    assert found == {"label": "Xác nhận", "inDialog": True, "clicked": False}
    assert tab.evaluate("() => window.__clicked") is None  # chỉ dò, chưa bấm
    tab.evaluate(browser.ADVANCE_JS, {"allowPage": False, "click": "Xác nhận"})
    assert tab.evaluate("() => window.__clicked") == "xacnhan"
    tab.close()


def test_nut_ngoai_trang_chi_bam_khi_duoc_phep(chromium):
    tab = chromium.new_page()
    tab.set_content('<button onclick="window.__clicked=1">Tiếp tục</button><button onclick="window.__clicked=2">Nộp hồ sơ</button>')
    assert tab.evaluate(browser.ADVANCE_JS, {"allowPage": False, "click": None}) is None
    assert tab.evaluate(browser.ADVANCE_JS, {"allowPage": True, "click": None})["label"] == "Tiếp tục"
    tab.close()


def test_nhan_biet_trang_trang(chromium):
    tab = chromium.new_page()
    tab.set_content("<html><body></body></html>")
    assert tab.evaluate(browser.BLANK_JS) is True
    tab.set_content("<body><iframe></iframe></body>")
    assert tab.evaluate(browser.BLANK_JS) is False  # form nằm trong iframe không phải trang trắng
    tab.set_content("<body><h1>Cổng dịch vụ công quốc gia</h1><p>Đang tải tờ khai, vui lòng chờ trong giây lát…</p></body>")
    assert tab.evaluate(browser.BLANK_JS) is False
    tab.close()


class _Frame:
    def __init__(self, label):
        self.label = label
        self.clicks = 0

    def evaluate(self, js, arg):
        if not self.label:
            return None
        if arg["click"] == self.label:
            self.clicks += 1
        return {"label": self.label, "inDialog": True, "clicked": arg["click"] == self.label}


def _bot(frames):
    bot = browser.PortalBot({}, __import__("threading").Event(), lambda text: None)
    bot.page = type("P", (), {"frames": frames})()
    return bot


def test_chi_bam_khi_nut_dung_yen_du_lau(monkeypatch):
    """Extension tự xác nhận hộp thoại chọn cơ quan trong 1–2 giây: bot chỉ bấm khi nút đứng yên đủ lâu."""
    clock = {"t": 100.0}
    monkeypatch.setattr(browser.time, "monotonic", lambda: clock["t"])
    frame = _Frame("Xác nhận")
    bot = _bot([frame])
    assert bot.auto_advance() is None and frame.clicks == 0
    clock["t"] += 2
    assert bot.auto_advance() is None and frame.clicks == 0
    clock["t"] += 2.5
    assert bot.auto_advance() == "Xác nhận" and frame.clicks == 1
    clock["t"] += 1
    assert bot.auto_advance() is None and frame.clicks == 1  # không bấm dồn


def test_trang_trang_qua_8_giay_thi_tai_lai_toi_da_3_lan(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(browser.time, "monotonic", lambda: clock["t"])
    reloads = []
    bot = _bot([])
    bot.page = type("P", (), {"reload": lambda self, **k: reloads.append(k)})()
    since = None
    for _ in range(60):  # 60 giây trắng liên tục
        since = bot._reload_if_stuck(since, True, "Trang trắng")
        clock["t"] += 1
    assert len(reloads) == 3
    assert bot._reload_if_stuck(None, False, "Trang trắng") is None  # hết trắng thì thôi đếm


import threading  # noqa: E402

# ---- Đính kèm trên cổng thật -------------------------------------------------------------------------------------

ATTACH_TABLE = """
<h3>Thành phần hồ sơ</h3>
<table>
  <tr><th>STT</th><th>Tên giấy tờ</th><th>Tệp</th><th></th></tr>
  <tr><td>1</td><td>Tờ khai đăng ký (bắt buộc)</td><td><a title="Tờ khai.pdf">Tờ khai.pdf</a></td>
      <td><button>Chọn tệp</button><input type="file" style="display:none"></td></tr>
  <tr><td>2</td><td>Giấy tờ tùy thân</td><td></td><td><button>Chọn tệp</button></td></tr>
  <tr><td>3</td><td>Giấy tờ khác</td><td><span>Căn cước.pdf</span><span>anh 2.jpg</span></td><td><label>Tải lên</label></td></tr>
</table>
<form><input name="data[hoTen]"><button>Tiếp tục</button></form>
"""


def test_doc_bang_dinh_kem_tren_cong(chromium):
    tab = chromium.new_page()
    tab.set_content(ATTACH_TABLE)
    rows = tab.evaluate(browser.ATTACH_ROWS_JS)
    tab.close()
    assert [r["label"] for r in rows] == ["Tờ khai đăng ký (bắt buộc)", "Giấy tờ tùy thân", "Giấy tờ khác"]
    assert rows[0]["files"] == ["Tờ khai.pdf"]
    assert rows[1]["files"] == []
    assert sorted(rows[2]["files"]) == ["Căn cước.pdf", "anh 2.jpg"]


def test_to_khai_co_o_anh_khong_tinh_la_buoc_dinh_kem(monkeypatch):
    bot = browser.PortalBot({}, threading.Event(), lambda _: None)
    monkeypatch.setattr(bot, "read_attach_rows", lambda: [{"label": "Ảnh chân dung", "files": []}])
    assert not bot.on_attach_step(["Tờ khai đăng ký", "Giấy tờ tùy thân"])
    monkeypatch.setattr(bot, "read_attach_rows", lambda: [{"label": "2 Giấy tờ tùy thân", "files": []}])
    assert bot.on_attach_step(["Tờ khai đăng ký", "Giấy tờ tùy thân"])


def test_dong_mong_doi_lay_tu_cong_va_ke_hoach_luot_goc():
    case = {
        "options": {"attachmentContext": {"components": [{"componentName": "Tờ khai"}, {"componentName": "Giấy tờ tùy thân"}]}},
        "plan": [{"componentName": "Tờ khai", "target": "existing"}, {"slotName": "Ô cố định", "target": "fixed-slot"}],
    }
    assert browser.expected_attach_rows(case) == ["Tờ khai", "Giấy tờ tùy thân", "Ô cố định"]


class _AttachBot:
    """Bot giả cho run_attach_once: cổng nhiều bước, phải điền rồi sang bước đính kèm."""

    def __init__(self, rows_after):
        self.clicked = []
        self.split = None
        self.step = False
        self.rows_after = rows_after
        self.pressed = None

    def ensure_panel(self): pass
    def login_panel(self, credentials): pass
    def select_procedure(self, key): pass
    def upload(self, files): pass
    def sleep(self, ms): pass
    def set_split_documents(self, on): self.split = on
    def attach_controls(self): return {"attachStep": True, "fillAttach": False, "failed": []}
    def on_attach_step(self, expected): return self.step
    def fill(self):
        self.clicked.append("#ocrBtn")
        return {"status": "Đã điền", "statusClass": "ok"}
    def advance_to_attach(self, expected):
        self.step = True
        return True
    def read_attach_rows(self): return self.rows_after if self.pressed else []
    def press(self, selector, timeout_s):
        self.pressed = selector
        return {"status": "Đã đính kèm 2/2", "statusClass": "ok", "details": []}
    def screenshot(self, path): return False


def test_mot_lan_dinh_kem_tren_cong(monkeypatch, tmp_path):
    import replay

    plan = [{"fileIndex": 0, "documentName": "Tờ khai", "componentName": "Tờ khai đăng ký", "target": "existing"}]
    monkeypatch.setattr(browser, "_attach_trace", lambda username, since: {"request_id": "req_moi", "llm_output": {"attachments": plan}})
    monkeypatch.setattr(replay, "clear_ocr_cache", lambda shas: None)
    monkeypatch.setattr(replay, "read_trace", lambda rid, kind="autofill": {"ocrText": "", "ocrFresh": True, "llmReused": False})
    bot = _AttachBot([{"label": "1 Tờ khai đăng ký", "files": ["Tờ khai.pdf"]}])
    case = {"procedure": "thu-tuc-mau", "kind": "attach", "options": {"splitDocuments": True}, "plan": plan, "pageCounts": [1],
            "storedFiles": [{"name": "scan.pdf", "sha256": "x"}]}
    run = browser.run_attach_once(bot, case, 1, {"username": "autotest-x"}, [], tmp_path, lambda *a: None)
    assert bot.split is True and bot.clicked == ["#ocrBtn"] and bot.pressed == "#attachStepBtn"
    assert run["status"] == "ok" and run["requestId"] == "req_moi" and run["portalRows"] == 1
    assert run["form"]["dòng: Tờ khai đăng ký"] == "Tờ khai [#1]"
    assert run["response"]["fields"][0] == {"name": "dòng: Tờ khai đăng ký", "value": "Tờ khai [#1]"}
    assert (tmp_path / "run1_portal.json").is_file() and (tmp_path / "run1_plan.json").is_file()


def test_panel_khong_goi_backend_dinh_kem_thi_bao_loi(monkeypatch, tmp_path):
    import replay

    monkeypatch.setattr(browser, "_attach_trace", lambda username, since: None)
    monkeypatch.setattr(replay, "clear_ocr_cache", lambda shas: None)
    bot = _AttachBot([])
    bot.step = True
    case = {"procedure": "p", "kind": "attach", "options": {}, "plan": [], "storedFiles": []}
    run = browser.run_attach_once(bot, case, 2, {"username": "u"}, [], tmp_path, lambda *a: None)
    assert run["status"] == "error" and "không gọi backend đính kèm" in run["error"]
    assert bot.clicked == []  # đã ở bước đính kèm thì không điền lại
