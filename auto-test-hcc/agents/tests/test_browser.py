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
    config.write_text('const BACKEND_URL = "https://may-chu-that.example";\n', encoding="utf-8")
    assert "localhost:12005" in browser.preflight()
    config.write_text('const BACKEND_URL = "http://localhost:12005";     // ghi chú\n', encoding="utf-8")
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
    monkeypatch.setattr(browser, "_open_urls", lambda: ["https://sso.dancuquocgia.gov.vn/auth"])

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
