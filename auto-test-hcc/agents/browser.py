"""Kiểm thử trên cổng thật: Chromium + extension Auto Fill, người dùng chỉ làm đúng một việc là đăng nhập VNeID.

Luồng: mở trang chủ Cổng DVC quốc gia → người dùng đăng nhập → bot thấy đã đăng nhập thì vào thủ tục bằng nút "Mở trang
thủ tục" của panel, y như cán bộ dùng Auto Fill: agency-select.js tự chọn cơ quan, bấm Nộp trực tuyến, Xác nhận.
Mỗi lần chạy: tải lại tờ khai → tải giấy tờ lên panel → bấm điền → đọc lại form bằng bộ đọc của extension.

Quy tắc của lớp này:
- Không bao giờ nộp hồ sơ. Bot chỉ bấm trong panel extension; các bước vào tờ khai là extension bấm như khi cán bộ dùng.
  Từ lúc tới tờ khai, lớp chặn bên dưới huỷ mọi nút và request có dáng nộp. Không có cờ tắt.
- Không đụng vào bước đăng nhập. Chromium mở như tiến trình thường, Playwright không nối vào khi đang ở màn SSO.
  Bot không biết mật khẩu VNeID, không lưu gì ngoài profile.
- Playwright bản đồng bộ chỉ xử lý mạng khi đang có lệnh gọi, nên phải rời ra trong lúc chờ agent họp, nếu không
  các request của trang bị treo. Chromium vẫn mở, phiên VNeID vẫn còn.
"""
from __future__ import annotations

import json
import re
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import Error, sync_playwright

import replay
import scoring
from config import CDP_PORT, EXT, PROFILE, REPO, ROOT
from evidence import database
from verify import Stopped

HOME_URL = "https://dichvucong.gov.vn/"
SSO_HOST = "sso.dancuquocgia.gov.vn"
_AUTH_HOST = re.compile(r"xacthuc|vneid|sso|dancuquocgia")
# Id extension unpacked: service worker ngủ thì không đọc được, mà muốn đánh thức lại cần chính id này.
_EXT_ID_FILE = ROOT / "runs" / "_extension_id.txt"
_FILL_TIMEOUT_S = 240
_FORM_BACK_S = 45
_ENTER_FORM_S = 150
HUMAN_TIMEOUT_S = 30 * 60

# Chạy ở mọi frame của cổng từ lúc tài liệu bắt đầu tải. Luật riêng của cổng luôn chặn. Chữ chung chỉ chặn SAU khi
# bot báo đã tới tờ khai: trang chọn cơ quan có nút "Nộp hồ sơ" trên thẻ mà người dùng phải bấm để vào được tờ khai.
GUARD_JS = r"""
(() => {
  if (window.__autotestGuard || location.protocol === "chrome-extension:") return;
  window.__autotestGuard = true;
  const RULES = { "dichvucong.gov.vn": { path: /^\/nop-ho-so\/?$/, text: ["luu va nop ho so"] } };
  const GENERIC = ["nop ho so", "gui ho so", "nop truc tuyen", "luu va nop", "xac nhan nop", "hoan tat nop", "nop don"];
  const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[đĐ]/g, "d").toLowerCase().replace(/\s+/g, " ").trim();
  const label = (el) => fold(el.innerText || el.value || el.getAttribute("aria-label") || el.title || "");
  const isSubmit = (el) => {
    const t = label(el);
    if (!t) return false;
    const rule = RULES[location.hostname];
    if (rule && rule.path.test(location.pathname) && rule.text.some((x) => t.includes(x))) return true;
    return window.__autotestFormReached === true && GENERIC.some((x) => t.includes(x));
  };
  const SEL = "button, a, input[type=submit], input[type=button], [role=button], [class*=btn], [class*=button]";
  const block = (e) => {
    const el = e.type === "submit" ? e.submitter : (e.target && e.target.closest && e.target.closest(SEL));
    if (!el || !isSubmit(el)) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    (window.__autotestBlocked = window.__autotestBlocked || []).push({ type: e.type, text: label(el).slice(0, 80) });
  };
  for (const t of ["pointerdown", "mousedown", "pointerup", "mouseup", "click", "submit"]) {
    window.addEventListener(t, block, true);
  }
})();
"""

# Lớp phụ ở mạng, lớp chính là chặn click. Tải tệp lên thì để qua: tờ khai có thể cần.
_SUBMIT_PATH = re.compile(r"nop|submit|gui-?ho-?so", re.I)
_UPLOAD_PATH = re.compile(r"upload|file|attach|dinh-?kem", re.I)
# Cổng dồn cả lệnh đọc vào nhánh /api/v1/submitting/, ví dụ get-formality-case-fees. Chặn nhầm là form thiếu dữ liệu.
_READ_CALL = re.compile(r"/(get|search|list|find|check|calc|calculate|lookup|tra-?cuu)[-_a-z0-9]*/?$", re.I)

# Giữ bản sao ảnh chụp form: ở local BE không lưu ảnh chụp (thiếu VAULT_URL). Chặn hai request thống kê nộp/đánh giá.
SW_HOOK_JS = r"""() => {
  const g = globalThis;
  if (!g.__autotest) {
    g.__autotest = { snaps: [] };
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg && msg.action === "formSnapshot" && msg.snapshot) g.__autotest.snaps.push(msg.snapshot);
      return undefined;
    });
    const orig = g.fetch.bind(g);
    g.fetch = (url, init) => {
      const u = String((url && url.url) || url);
      if (/\/api\/v1\/dossiers\/(submit-click|rating)/.test(u)) return Promise.resolve(new Response("{}", { status: 409 }));
      return orig(url, init);
    };
  }
  return g.__autotest.snaps.length;
}"""

# Extension không có quyền "tabs" nên tab.url rỗng → hỏi content script từng tab xem nó đang ở đâu.
FIND_TAB_JS = r"""async (target) => {
  const strip = (u) => String(u || "").split("#")[0].replace(/\/$/, "");
  for (const t of await chrome.tabs.query({})) {
    try {
      const r = await chrome.tabs.sendMessage(t.id, { action: "detectProcedure" });
      if (strip(r && r.signals && r.signals.url) === strip(target)) return t.id;
    } catch (_) { /* tab chưa có content script */ }
  }
  const [t] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return t ? t.id : null;
}"""

TOGGLE_PANEL_JS = r"""async (tabId) => {
  try { await chrome.tabs.sendMessage(tabId, { action: "togglePanel" }); return "sent"; }
  catch (e) {
    const files = chrome.runtime.getManifest()?.content_scripts?.[0]?.js || [];
    await chrome.scripting.executeScript({ target: { tabId }, files });
    await chrome.tabs.sendMessage(tabId, { action: "togglePanel" });
    return "injected";
  }
}"""

POPUP_STATE_JS = r"""() => {
  const $ = (id) => document.getElementById(id);
  const shown = (el) => !!el && !el.hidden && getComputedStyle(el).display !== "none";
  const sc = $("supportCode");
  return {
    busy: !!window.__AUTOFILL_HCC_POPUP_BUSY__,
    login: shown($("loginScreen")),
    main: shown($("mainScreen")),
    consent: shown($("view-consent")),
    procedure: ($("procedureSelect") || {}).value || "",
    status: ($("status") || {}).textContent || "",
    statusClass: ($("status") || {}).className || "",
    details: [...document.querySelectorAll("#statusDetails li")].map((li) => li.textContent.trim()),
    supportCode: sc && !sc.hidden ? (($("supportCodeValue") || {}).textContent || "").trim() : "",
    files: document.querySelectorAll("#fileList li").length,
  };
}"""

# Đếm ô để biết tờ khai đã về sau khi tải lại. Gồm mọi kiểu form extension điền được, không riêng cổng nào.
FORM_PROBE_JS = r"""() => document.querySelectorAll(
  '.sd-question[data-name], [formcontrolname], x-input, x-date, x-radio, liz-input, liz-select, liz-datepicker, ' +
  'input[name^="data["], select[name^="data["], form input[name], form select[name], form textarea[name]'
).length"""


# Cùng tiêu chí với content/portal-login.js. Chạy thẳng trên trang để không phải đánh thức service worker của extension:
# đánh thức là mở một tab mới, mà đang lúc người dùng đăng nhập thì không được làm phiền.
LOGGED_IN_JS = r"""() => {
  const shown = (el) => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
  const account = document.querySelector("#account_name") || document.querySelector(".user-dropdown");
  if (shown(account)) return true;
  const fold = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[đĐ]/g, "d").toLowerCase().trim();
  return [...document.querySelectorAll("a, button, span, li")].some((el) => fold(el.textContent) === "dang xuat" && shown(el));
}"""


def preflight() -> str | None:
    """Câu báo lỗi nếu chưa chạy được trên cổng, None nếu ổn."""
    config = (EXT / "api/config.js").read_text(encoding="utf-8")
    if not re.search(r'const BACKEND_URL\s*=\s*"http://localhost:12005"', config):
        return ("Extension đang trỏ backend khác localhost:12005 nên lượt điền sẽ không chạy qua code vừa sửa. "
                "Đổi BACKEND_URL trong auto-fill-hcc-extension/api/config.js về http://localhost:12005.")
    return None


@lru_cache(maxsize=1)
def _extension_name() -> str:
    return json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))["name"]


def _port_open(port: int) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.3).close()
        return True
    except OSError:
        return False


def _is_portal(url: str) -> bool:
    return urlsplit(url).netloc.endswith("gov.vn")


def _is_auth(url: str) -> bool:
    return bool(_AUTH_HOST.search(urlsplit(url).netloc))


def _open_urls() -> list[str]:
    """Danh sách tab đọc từ cổng debug: xem được đang ở đâu mà không cần nối Playwright vào trình duyệt."""
    try:
        pages = httpx.get(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=2).json()
    except (httpx.HTTPError, ValueError):
        return []
    return [p.get("url", "") for p in pages if p.get("type") == "page"]


class PortalBot:
    """Một phiên làm việc với cửa sổ Chromium. ``state`` sống qua nhiều lần nối: url tờ khai, số ô chuẩn, id extension."""

    def __init__(self, state: dict, cancel: threading.Event, log: Callable[[str], None]):
        self.state = state
        self.cancel = cancel
        self.log = log
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.closed = False
        self.armed = False  # lớp chặn mạng: chỉ bật khi đã tới tờ khai, extension còn phải bấm Nộp trực tuyến để vào
        self.requests: list[dict] = []
        self.blocked: list[dict] = []

    # ---- vòng đời ------------------------------------------------------------------------------------------

    def attach(self, guard: bool = True) -> None:
        self.pw = sync_playwright().start()
        if not _port_open(CDP_PORT):
            PROFILE.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(
                [
                    self.pw.chromium.executable_path, f"--user-data-dir={PROFILE}", f"--remote-debugging-port={CDP_PORT}",
                    "--no-first-run", "--no-default-browser-check",
                    f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "about:blank",
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            for _ in range(100):
                if _port_open(CDP_PORT):
                    break
                time.sleep(0.2)
        self.browser = self.pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        self.closed = False
        self.browser.on("disconnected", lambda _: setattr(self, "closed", True))
        self.context = self.browser.contexts[0]
        if guard:
            self.context.add_init_script(GUARD_JS)
            self.context.route(_is_portal, self._route)

    def detach(self) -> None:
        try:
            if self.context and not self.closed:
                self.context.unroute_all(behavior="ignoreErrors")  # kẻo driver dừng khi còn request treo, log đầy rác
            if self.pw:
                self.pw.stop()
        except Exception:  # noqa: BLE001 — tiến trình driver đã chết thì coi như đã rời
            pass
        self.pw = self.browser = self.context = self.page = None

    def sleep(self, ms: int) -> None:
        """Chờ mà vẫn bơm sự kiện Playwright, để route và console còn chạy."""
        if self.cancel.is_set():
            raise Stopped()
        if self.closed:
            raise RuntimeError("Cửa sổ Chromium đã bị đóng.")
        try:
            self.context.wait_for_event("page", timeout=ms)
        except Error:
            pass

    def _route(self, route) -> None:
        request = route.request
        try:
            if self.armed and request.method not in ("GET", "HEAD", "OPTIONS"):
                parts = urlsplit(request.url)
                item = {"method": request.method, "url": f"{parts.netloc}{parts.path}"}
                self.requests.append(item)
                if _SUBMIT_PATH.search(parts.path) and not _UPLOAD_PATH.search(parts.path) and not _READ_CALL.search(parts.path):
                    self.blocked.append(item)
                    self.log(f"Đã chặn request có dáng nộp hồ sơ: {request.method} {item['url']}")
                    route.abort()
                    return
            route.continue_()
        except Error:
            pass

    # ---- service worker + panel ------------------------------------------------------------------------------

    def _own_worker(self):
        """Chromium có sẵn extension nội bộ, cũng có service worker chrome-extension:// nên phải khớp đúng tên."""
        for worker in self.context.service_workers:
            if not worker.url.startswith("chrome-extension://"):
                continue
            try:
                if worker.evaluate("() => chrome.runtime.getManifest().name") == _extension_name():
                    return worker
            except Error:
                continue
        return None

    def _remember(self, worker):
        self.state["extId"] = urlsplit(worker.url).netloc
        _EXT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _EXT_ID_FILE.write_text(self.state["extId"], encoding="utf-8")
        return worker

    def _sw(self):
        worker = self._own_worker()
        if worker:
            return self._remember(worker)
        # Service worker MV3 tự ngủ sau ~30 giây, mở trang của extension để đánh thức.
        known = self.state.get("extId") or (_EXT_ID_FILE.read_text(encoding="utf-8").strip() if _EXT_ID_FILE.is_file() else "")
        if known:
            wake = self.context.new_page()
            try:
                wake.goto(f"chrome-extension://{known}/settings.html", wait_until="domcontentloaded")
            except Error:
                pass
            wake.close()
        end = time.monotonic() + 15
        while time.monotonic() < end:
            worker = self._own_worker()
            if worker:
                return self._remember(worker)
            self.sleep(300)
        raise RuntimeError("Không thấy service worker của extension Auto Fill.")

    def reload_extension(self) -> None:
        """Extension nạp unpacked: sửa file trên đĩa chưa có tác dụng tới khi nạp lại. Tab đang mở phải tải lại sau đó."""
        try:
            self._sw().evaluate("() => { setTimeout(() => chrome.runtime.reload(), 50); }")
        except Error:
            pass  # service worker chết giữa lệnh là đúng ý
        self.sleep(2500)
        self._sw()
        self.state["extensionStale"] = False
        self.log("Đã nạp lại extension trên cửa sổ bot.")

    def sw_eval(self, js: str, arg=None):
        return self._sw().evaluate(js, arg)

    def popup(self):
        prefix = f"chrome-extension://{self.state.get('extId', '')}/popup.html"
        return next((f for f in self.page.frames if f.url.startswith(prefix)), None)

    def popup_state(self) -> dict:
        frame = self.popup()
        if not frame:
            return {}
        try:
            return frame.evaluate(POPUP_STATE_JS)
        except Error:
            return {}

    def popup_click(self, selector: str) -> bool:
        frame = self.popup()
        if not frame:
            return False
        return bool(frame.evaluate("(s) => { const el = document.querySelector(s); if (!el) return false; el.click(); return true; }", selector))

    def ensure_panel(self, timeout_s: float = 25) -> None:
        """togglePanel là công tắc: panel đang thu nhỏ thành bong bóng mà gửi lệnh thì nó ĐÓNG. Điền xong panel tự thu
        nhỏ, tải lại trang thì chỉ khôi phục bong bóng, nên phải xem trang đang có gì rồi mới quyết định."""
        self._sw()
        began = time.monotonic()
        toggled = False
        while time.monotonic() - began < timeout_s:
            if self.popup() and self.popup_state():
                return
            ui = self.page.evaluate(
                "() => { const bubble = document.getElementById('autofill-hcc-bubble');"
                " if (bubble) { bubble.click(); return 'bubble'; }"
                " return document.getElementById('autofill-hcc-panel') ? 'panel' : ''; }"
            )
            # Đợi một nhịp cho extension tự khôi phục, kẻo toggle đè lên bong bóng sắp hiện.
            if not ui and not toggled and time.monotonic() - began > 2:
                tab = self.sw_eval(FIND_TAB_JS, self.page.url)
                if tab is not None:
                    self.sw_eval(TOGGLE_PANEL_JS, tab)
                    toggled = True
            self.sleep(700)
        raise RuntimeError("Không mở được panel extension trên trang.")

    def login_panel(self, credentials: dict) -> None:
        """Mỗi job đăng nhập lại đúng tài khoản chạy lại: panel đang giữ tài khoản của job trước thì sai xã/tỉnh."""
        state = self.popup_state()
        if state.get("main") and self.state.get("panelUser") != credentials["username"]:
            self.popup_click("#logoutBtn")
            self.sleep(1200)
            state = self.popup_state()
        if state.get("login"):
            frame = self.popup()
            frame.fill("#loginUsername", credentials["username"])
            frame.fill("#loginPassword", credentials["password"])
            self.popup_click("#loginBtn")
            end = time.monotonic() + 25
            while time.monotonic() < end and not self.popup_state().get("main"):
                self.sleep(500)
            if not self.popup_state().get("main"):
                raise RuntimeError(f"Panel không đăng nhập được tài khoản {credentials['username']}.")
        self.state["panelUser"] = credentials["username"]

    def flow_state(self) -> dict:
        """Trạng thái luồng của agency-select.js. Cổng khác DVC quốc gia trả về unsupported."""
        try:
            tab = self.sw_eval(FIND_TAB_JS, self.page.url)
            if tab is None:
                return {}
            return self.sw_eval("(t) => chrome.tabs.sendMessage(t, { action: 'getPortalFlowState' }).catch(() => ({}))", tab) or {}
        except (Error, RuntimeError):
            return {}  # trang đang chuyển, nhịp sau hỏi lại

    def confirm_modal(self) -> None:
        """Modal Thông tin chung: agency-select.js tự bấm khi đang chạy luồng vào thủ tục, còn sau khi tải lại trang thì không."""
        tab = self.sw_eval(FIND_TAB_JS, self.page.url)
        if tab is not None:
            self.sw_eval("(t) => chrome.tabs.sendMessage(t, { action: 'confirmInfoModal' }).catch(() => null)", tab)

    def go_to_procedure(self, key: str) -> None:
        """Bấm "Mở trang thủ tục" trong panel: popup tự lên đạn cho agency-select.js theo Tỉnh/Xã của tài khoản rồi chuyển trang."""
        end = time.monotonic() + 30
        ready: dict = {}
        while time.monotonic() < end:
            frame = self.popup()
            if frame:
                ready = frame.evaluate(
                    "(k) => { const s = document.getElementById('keKhaiSelect');"
                    " const box = document.getElementById('destSection');"
                    " return { shown: !!box && !box.hidden, has: !!s && [...s.options].some((o) => o.value === k) }; }", key,
                )
                if ready.get("shown") and ready.get("has"):
                    break
            self.sleep(700)
        else:
            raise RuntimeError(f"Panel chưa có {key} trong danh sách Mở trang thủ tục.")
        self.popup().evaluate(
            "(k) => { const s = document.getElementById('keKhaiSelect'); s.value = k;"
            " s.dispatchEvent(new Event('change', { bubbles: true })); }", key,
        )
        self.sleep(800)
        note = self.popup().evaluate("() => (document.getElementById('keKhaiStatus') || {}).textContent || ''")
        self.log(f"Panel: {note[:120]}")
        self.popup_click("#destGoBtn")

    def wait_form(self, timeout_s: float = _ENTER_FORM_S) -> None:
        """Chờ extension đi hết các bước vào tờ khai, rồi lấy tab đó làm tab làm việc."""
        end = time.monotonic() + timeout_s
        last_confirm = 0.0
        while time.monotonic() < end:
            self.sleep(1000)
            if self.on_login_page():
                raise RuntimeError("Cổng đòi đăng nhập lại.")
            self._follow_busiest_tab()
            flow = self.flow_state()
            if flow.get("ownerInfo"):
                raise RuntimeError("Cổng dừng ở bước Thông tin chủ hồ sơ.")
            if flow.get("infoModal"):
                if time.monotonic() - last_confirm > 6:
                    self.confirm_modal()
                    last_confirm = time.monotonic()
                continue
            count = self._form_count(self.page)
            if count >= 3 and (flow.get("formReady") or flow.get("unsupported")):
                self.sleep(1500)  # để cổng đổ xong dữ liệu theo tài khoản
                self.state.update(formUrl=self.page.url, formFields=self._form_count(self.page))
                self.log(f"Đã vào tờ khai: {urlsplit(self.page.url).netloc}{urlsplit(self.page.url).path}, {self.state['formFields']} ô.")
                self.mark_form_reached()
                return
        raise RuntimeError(f"Quá {int(timeout_s)} giây chưa thấy tờ khai.")

    def enter_form(self, procedure: str, credentials: dict) -> None:
        """Từ trang chủ đi thẳng tới tờ khai. Dùng lúc đầu ca và khi tải lại mà cổng không đưa về tờ khai."""
        self.armed = False
        pages = [p for p in self.context.pages if not p.url.startswith("chrome-extension://")]
        self.page = next((p for p in pages if urlsplit(p.url).netloc == urlsplit(HOME_URL).netloc), pages[0] if pages else self.context.new_page())
        if urlsplit(self.page.url).path not in ("", "/"):
            self.page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
            self.sleep(2500)
        self.ensure_panel()
        self.login_panel(credentials)
        self.go_to_procedure(procedure)
        self.wait_form()

    def select_procedure(self, key: str) -> None:
        state = self.popup_state()
        if state.get("procedure") == key:
            return
        self.log(f"Panel nhận diện '{state.get('procedure') or '(trống)'}', chọn lại đúng thủ tục của req.")
        # Ngay sau đăng nhập danh sách thủ tục chưa nạp xong: đặt value khi chưa có option thì ra rỗng, không báo lỗi.
        end = time.monotonic() + 20
        while time.monotonic() < end:
            done = self.popup().evaluate(
                "(k) => { const s = document.getElementById('procedureSelect');"
                " if (![...s.options].some((o) => o.value === k)) return false;"
                " s.value = k; s.dispatchEvent(new Event('change', { bubbles: true })); return true; }", key,
            )
            if done:
                self.sleep(1200)
                if self.popup_state().get("procedure") == key:
                    return
            self.sleep(700)
        raise RuntimeError(f"Panel không chọn được thủ tục {key}. Tài khoản chạy lại có thể không được cấp thủ tục này.")

    def upload(self, files: list[Path]) -> None:
        if self.popup_state().get("files", 0) == len(files):
            return
        self.popup().set_input_files("#fileInput", [str(p) for p in files])
        end = time.monotonic() + 45
        while time.monotonic() < end and self.popup_state().get("files", 0) < len(files):
            self.sleep(500)

    def fill(self) -> dict:
        self.sw_eval(SW_HOOK_JS)
        self.popup_click("#ocrBtn")
        started = consented = False
        began = time.monotonic()
        state: dict = {}
        while time.monotonic() - began < _FILL_TIMEOUT_S:
            self.sleep(1000)
            state = self.popup_state() or state
            if state.get("consent") and not consented:
                self.popup().evaluate(
                    "() => { const all = document.getElementById('consentSelectAll'); if (all && !all.checked) all.click();"
                    " for (const id of ['consentC0','consentC1']) { const c = document.getElementById(id);"
                    " if (c && !c.checked) c.click(); } }"
                )
                self.popup_click("#consentAcceptBtn")
                consented = True
                continue
            if state.get("busy"):
                started = True
            elif started:
                return state
            elif time.monotonic() - began > 25 and re.search(r"\b(err|warn)\b", state.get("statusClass", "")):
                return state  # dừng trước khi gọi BE: chưa có file, chưa chọn thủ tục…
        raise RuntimeError(f"Quá {_FILL_TIMEOUT_S} giây vẫn chưa điền xong.")

    def snapshot(self, request_id: str) -> dict | None:
        """Ảnh chụp form của đúng lượt này. Tracker tự chụp 1,5 giây sau khi điền; không thấy thì yêu cầu chụp."""
        self.sleep(3000)
        for attempt in range(2):
            snaps = self.sw_eval("() => (globalThis.__autotest && globalThis.__autotest.snaps) || []") or []
            mine = [s for s in snaps if s.get("requestId") == request_id]
            fills = [s for s in mine if s.get("kind") == "fill"]
            if fills or mine:
                return (fills or mine)[-1]
            if attempt == 0:
                tab = self.sw_eval(FIND_TAB_JS, self.page.url)
                if tab is not None:
                    self.sw_eval("(t) => chrome.tabs.sendMessage(t, { action: 'formSnapshotCapture', trigger: 'autotest' }).catch(() => null)", tab)
                self.sleep(2500)
        return None

    # ---- tờ khai ---------------------------------------------------------------------------------------------

    def _form_count(self, page) -> int:
        total = 0
        for frame in page.frames:
            if frame.url.startswith("chrome-extension://"):
                continue
            try:
                total += frame.evaluate(FORM_PROBE_JS)
            except Error:
                continue
        return total

    def _busiest_tab(self):
        """Tab nhiều ô nhất: cổng có thể mở tờ khai ở tab mới."""
        pages = [p for p in self.context.pages if not p.url.startswith("chrome-extension://")]
        return max(((self._form_count(p), p) for p in pages), key=lambda item: item[0], default=(0, None))

    def _follow_busiest_tab(self) -> None:
        count, page = self._busiest_tab()
        if page and count:
            self.page = page

    def pick_form_page(self) -> None:
        count, page = self._busiest_tab()
        if not page or not count:
            raise RuntimeError("Chưa thấy tờ khai trên cửa sổ bot. Hãy mở tới trang có các ô điền rồi bấm lại.")
        self.page = page
        self.state.update(formUrl=page.url, formFields=count)
        self.log(f"Đã nhận tờ khai: {urlsplit(page.url).netloc}{urlsplit(page.url).path}, {count} ô.")
        self.mark_form_reached()

    def mark_form_reached(self) -> None:
        self.armed = True
        for frame in self.page.frames:
            try:
                frame.evaluate(GUARD_JS)
                frame.evaluate("() => { window.__autotestFormReached = true; }")
            except Error:
                pass

    def on_login_page(self) -> bool:
        return any(urlsplit(p.url).netloc == SSO_HOST for p in self.context.pages)

    def reload_form(self) -> bool:
        """Tải lại tờ khai. False khi tờ khai không về: hết phiên, hoặc cổng đẩy về trang trước."""
        self.armed = False  # modal Thông tin chung có thể hiện lại, Xác nhận của nó phải đi qua được
        if self.page is None:
            pages = [p for p in self.context.pages if p.url == self.state.get("formUrl")]
            pages = pages or [p for p in self.context.pages if not p.url.startswith("chrome-extension://")]
            if not pages:
                return False
            self.page = pages[0]
        try:
            self.page.reload(wait_until="domcontentloaded", timeout=60000)
        except Error as reason:
            self.log(f"Tải lại trang lỗi: {reason.message[:160]}")
            return False
        need = max(1, int(self.state.get("formFields", 1) * 0.5))
        end = time.monotonic() + _FORM_BACK_S
        while time.monotonic() < end:
            if self.on_login_page():
                return False
            if self.flow_state().get("infoModal"):
                self.confirm_modal()
                self.sleep(1500)
                continue
            if self._form_count(self.page) >= need:
                self.sleep(1500)  # để cổng đổ xong dữ liệu theo tài khoản, kẻo đè lên giá trị vừa điền
                self.mark_form_reached()
                return True
            self.sleep(800)
        return False

    def blocked_clicks(self) -> list[dict]:
        found: list[dict] = []
        for frame in self.page.frames:
            try:
                found += frame.evaluate("() => window.__autotestBlocked || []")
            except Error:
                continue
        return found

    def screenshot(self, path: Path) -> bool:
        try:
            self.page.screenshot(path=str(path), full_page=True)
            return True
        except Error:
            return False


def prepare_upload_dir(case: dict, job_dir: Path) -> list[Path]:
    """Chép tệp về đúng tên gốc: tên tệp đi vào prompt nên lấy tên đã đổi là khác lượt gốc."""
    files = []
    for item in case["storedFiles"]:
        folder = job_dir / "upload" / str(item["index"])
        folder.mkdir(parents=True, exist_ok=True)
        name = re.sub(r'[<>:"/\\|?*]', "_", str(item.get("name") or "file"))
        target = folder / name
        target.write_bytes((REPO / item["path"]).read_bytes())
        files.append(target)
    return files


def _be_result(request_id: str) -> dict:
    request = database().process_requests.find_one({"request_id": request_id}, {"fields": 1, "procedure": 1}) or {}
    trace = database().traces.find_one({"request_id": request_id}, {"errors": 1}) or {}
    return {"fields": request.get("fields") or [], "errors": trace.get("errors") or [], "requestId": request_id, "procedure": request.get("procedure")}


def run_once(bot: PortalBot, case: dict, number: int, credentials: dict, files: list[Path], out_dir: Path) -> dict:
    began = time.monotonic()
    result: dict = {"n": number, "startedAt": datetime.now(timezone.utc).isoformat(), "mode": "portal"}
    bot.ensure_panel()
    bot.login_panel(credentials)
    bot.select_procedure(case["procedure"])
    bot.upload(files)
    # Xoá ngay trước khi bấm: lần trước vừa ghi cache cho đúng tệp này.
    replay.clear_ocr_cache([f.get("sha256") for f in case["storedFiles"]])
    state = bot.fill()
    request_id = state.get("supportCode") or ""
    result["ms"] = int((time.monotonic() - began) * 1000)
    result["panel"] = {k: state.get(k) for k in ("status", "statusClass", "details")}
    if not request_id or request_id == bot.state.get("lastRequest"):
        result.update(status="error", error=f"Panel không ra lượt mới: {state.get('status') or 'không có thông báo'}")
        if bot.screenshot(out_dir / f"run{number}.png"):
            result["screenshot"] = f"run{number}.png"
        return result
    bot.state["lastRequest"] = request_id

    snapshot = bot.snapshot(request_id)
    be = _be_result(request_id)
    trace = replay.read_trace(request_id)
    (out_dir / f"run{number}_ocr.txt").write_text(trace.pop("ocrText"), encoding="utf-8")
    result.update(trace)
    result.update(requestId=request_id, response=be, status="partial" if be["errors"] else "ok")
    if snapshot:
        result["form"] = {scoring.field_key(f): f.get("value") for f in snapshot.get("fields") or []}
    if be.get("procedure") and be["procedure"] != case["procedure"]:
        result["wrongProcedure"] = be["procedure"]
    if bot.screenshot(out_dir / f"run{number}.png"):
        result["screenshot"] = f"run{number}.png"
    return result


def _back_to_form(bot: PortalBot, wait_human: Callable[[str], None], message: str) -> None:
    """Nhờ người đưa cửa sổ về tờ khai, tới khi thật sự thấy tờ khai. Rời hẳn trình duyệt trong lúc chờ để người dùng
    đăng nhập lại trên Chromium bình thường. Lỡ đóng cửa sổ thì lần nối sau tự mở lại."""
    while True:
        bot.detach()
        wait_human(message)
        bot.attach()
        try:
            bot.pick_form_page()
            return
        except (Error, RuntimeError) as reason:
            message = str(reason)[:200]


def _reload(bot: PortalBot) -> bool:
    try:
        return bot.reload_form()
    except (Error, RuntimeError):
        return False  # cửa sổ vừa bị đóng hoặc trang đang chuyển


def _reenter(bot: PortalBot, case: dict, credentials: dict, log: Callable[[str], None]) -> bool:
    """Tải lại mà cổng không về tờ khai thì tự đi lại từ trang chủ. Hết phiên đăng nhập thì mới phải nhờ người."""
    try:
        if bot.on_login_page():
            return False
        log("Cổng không về tờ khai sau khi tải lại, bot đi lại từ trang chủ…")
        bot.enter_form(case["procedure"], credentials)
        return True
    except (Error, RuntimeError) as reason:
        log(f"Không tự vào lại được: {str(reason)[:160]}")
        return False


def replay_on_portal(
    case: dict,
    count: int,
    phase: str,
    job_dir: Path,
    credentials: dict,
    state: dict,
    cancel: threading.Event,
    wait_human: Callable[[str], None],
    on_run: Callable[[dict], None],
    log: Callable[[str], None],
) -> list[dict]:
    out_dir = job_dir / "replay" / phase
    out_dir.mkdir(parents=True, exist_ok=True)
    files = prepare_upload_dir(case, job_dir)
    runs: list[dict] = []
    bot = PortalBot(state, cancel, log)
    bot.attach()
    try:
        if state.get("extensionStale"):
            bot.reload_extension()
        for number in range(1, count + 1):
            if cancel.is_set():
                break
            if number == 1 and not state.get("formFields"):
                try:
                    bot.pick_form_page()
                except (Error, RuntimeError) as reason:
                    _back_to_form(bot, wait_human, str(reason)[:200])
            while not _reload(bot):
                if not _reenter(bot, case, credentials, log):
                    _back_to_form(bot, wait_human, "Bot không tự vào lại được tờ khai, có thể hết phiên VNeID hoặc cửa sổ đã đóng. Đăng nhập lại và mở tới tờ khai.")
            try:
                run = run_once(bot, case, number, credentials, files, out_dir)
            except Stopped:
                raise
            except (Error, RuntimeError) as reason:
                run = {"n": number, "status": "error", "error": str(reason)[:300], "mode": "portal"}
            run["portalWrites"] = len(bot.requests)
            runs.append(run)
            on_run(run)
        blocked = bot.blocked_clicks() + bot.blocked
        if blocked:
            log(f"Lớp chặn nộp đã chặn {len(blocked)} thao tác: {json.dumps(blocked, ensure_ascii=False)[:300]}")
        # Chỉ đường dẫn, không có nội dung: để biết cổng có lưu nháp dữ liệu khi điền không.
        writes = sorted({f"{r['method']} {r['url']}" for r in bot.requests})
        if writes:
            log("Request ghi lên cổng trong đợt này: " + ", ".join(writes)[:900])
    finally:
        bot.detach()
    (out_dir / "runs.json").write_text(json.dumps(runs, ensure_ascii=False), encoding="utf-8")
    return runs


def reload_if_open(log: Callable[[str], None]) -> None:
    """Sau khi hoàn tác bản sửa extension: cửa sổ bot đang mở thì nạp lại, không có cửa sổ thì ca sau tự nạp từ đĩa."""
    if not _port_open(CDP_PORT):
        return
    bot = PortalBot({}, threading.Event(), log)
    bot.attach(guard=False)
    try:
        bot.reload_extension()
    except (Error, RuntimeError) as reason:
        log(f"Không nạp lại được extension: {str(reason)[:160]}. Ca sau sẽ tự nạp lại.")
    finally:
        bot.detach()


def open_home(state: dict, cancel: threading.Event, log: Callable[[str], None]) -> None:
    """Mở trang chủ cổng rồi rời ra ngay, không để lại route hay script nào trên trang."""
    bot = PortalBot(state, cancel, log)
    was_open = _port_open(CDP_PORT)
    bot.attach(guard=False)
    try:
        if was_open:
            # Cửa sổ của ca trước có thể đang giữ code extension cũ, ví dụ ca đó vừa hoàn tác bản sửa.
            bot.reload_extension()
        pages = [p for p in bot.context.pages if not p.url.startswith("chrome-extension://")]
        page = pages[0] if pages else bot.context.new_page()
        page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
        page.bring_to_front()
    except Error as reason:
        log(f"Không mở được trang chủ cổng: {reason.message[:160]}. Hãy tự mở trên cửa sổ bot.")
    finally:
        bot.detach()


def is_logged_in(state: dict, cancel: threading.Event, log: Callable[[str], None]) -> bool:
    """Đang ở màn đăng nhập thì không nối vào. Chỉ nối thoáng qua khi đã về cổng, để đọc xem có tài khoản chưa."""
    urls = _open_urls()
    if any(_is_auth(url) for url in urls) or not any(_is_portal(url) for url in urls):
        return False
    bot = PortalBot(state, cancel, log)
    bot.attach(guard=False)
    try:
        for page in bot.context.pages:
            if _is_portal(page.url) and not _is_auth(page.url) and page.evaluate(LOGGED_IN_JS):
                return True
        return False
    except Error:
        return False  # trang đang chuyển, nhịp sau hỏi lại
    finally:
        bot.detach()


def enter_form(procedure: str, credentials: dict, state: dict, cancel: threading.Event, log: Callable[[str], None]) -> None:
    bot = PortalBot(state, cancel, log)
    bot.attach()
    try:
        bot.enter_form(procedure, credentials)
    finally:
        bot.detach()


