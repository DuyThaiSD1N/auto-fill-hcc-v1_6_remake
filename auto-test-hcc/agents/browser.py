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
import mimetypes
import os
import re
import socket
import subprocess
import sys
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
import runner_hub
import scoring
from config import CDP_PORT, EXTENSION_BACKEND, EXT, PROFILE, REPO, ROOT
from evidence import test_database as database
from verify import Stopped

HOME_URL = "https://dichvucong.gov.vn/"
SSO_HOST = "sso.dancuquocgia.gov.vn"
_AUTH_HOST = re.compile(r"xacthuc|vneid|sso|dancuquocgia")
# Id extension unpacked: service worker ngủ thì không đọc được, mà muốn đánh thức lại cần chính id này.
_EXT_ID_FILE = ROOT / "runs" / "_extension_id.txt"
# Thư mục extension cửa sổ bot đã nạp: khu làm việc và repo người phát triển là 2 extension khác nhau (id khác, backend khác).
_EXT_PATH_FILE = ROOT / "runs" / "_extension_path.txt"
_FILL_TIMEOUT_S = 240
_FORM_BACK_S = 45
_ENTER_FORM_S = 150
# Trang trắng / form không lên quá chừng này giây thì tự tải lại, tối đa _BLANK_RELOADS lần rồi mới nhờ người.
_BLANK_RELOAD_S = 8
_BLANK_RELOADS = 3
# Cùng một nút không bấm lại trong khoảng này: cổng chưa kịp chuyển thì bấm dồn dễ mở trùng bước.
_ADVANCE_GAP_S = 5
# Nút phải đứng yên chừng này giây mới bấm (để extension tự xử lý trước).
_ADVANCE_SETTLE_S = 4

# Bot tự bấm nút xác nhận / chuyển bước khi đang vào tờ khai, không đợi người. Ưu tiên nút trong hộp thoại; nút ngoài trang
# chỉ bấm khi được phép (bước Thông tin chủ hồ sơ). KHÔNG BAO GIỜ bấm nút có chữ nộp / gửi / lưu / huỷ…: lớp chặn nộp
# (GUARD_JS + route) vẫn chặn thêm ở dưới.
ADVANCE_JS = r"""
({ allowPage, click }) => {
  const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[đĐ]/g, "d").toLowerCase().replace(/\s+/g, " ").trim();
  const OK = ["xac nhan", "dong y", "tiep tuc", "tiep theo", "buoc tiep theo", "buoc tiep", "da hieu", "toi da hieu", "chap nhan"];
  const NEVER = ["nop", "gui", "luu", "huy", "xoa", "dang xuat", "quay lai", "tro lai", "tu choi", "khong", "thanh toan",
                 "ky so", "in ", "tai ve", "tai len", "chon tep"];
  const shown = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none"
      && !el.disabled && el.getAttribute("aria-disabled") !== "true";
  };
  const text = (el) => fold(el.innerText || el.value || el.getAttribute("aria-label") || "");
  const dialogs = [...document.querySelectorAll(
    '[role="dialog"], [role="alertdialog"], .modal.show, .modal.in, .ant-modal-wrap, .swal2-popup, .mat-dialog-container, .p-dialog'
  )].filter(shown);
  const scopes = dialogs.length ? dialogs : (allowPage ? [document] : []);
  for (const scope of scopes) {
    const buttons = [...scope.querySelectorAll('button, a.btn, a[role="button"], [role="button"], input[type="button"], input[type="submit"]')]
      .filter(shown);
    for (const el of buttons) {
      const t = text(el);
      if (!t || t.length > 40 || NEVER.some((w) => t.includes(w))) continue;
      if (t === "ok" || OK.some((w) => t.startsWith(w))) {
        const label = (el.innerText || el.value || "").trim().slice(0, 40);
        if (click && click === label) el.click();
        return { label, inDialog: scope !== document, clicked: !!click && click === label };
      }
    }
  }
  return null;
}
"""

# Trang trắng: gần như không có chữ, không có ô nhập, không có iframe (form nằm trong iframe thì không tính là trắng).
BLANK_JS = r"""() => {
  const body = document.body;
  if (!body) return true;
  const text = (body.innerText || "").trim().length;
  const inputs = document.querySelectorAll("input:not([type=hidden]), select, textarea").length;
  const frames = document.querySelectorAll("iframe").length;
  return text < 40 && inputs === 0 && frames === 0;
}"""
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


# Đọc bảng đính kèm trên trang: mỗi dòng có ô / nút tải tệp → {label, files}. Dùng chung cho mọi cổng nên đoán theo DOM:
# nhãn là ô nhiều chữ nhất không phải tên tệp / nút, tệp là phần tử có chữ kết thúc bằng đuôi tệp (hoặc title/download).
ATTACH_ROWS_JS = r"""() => {
  const EXT = /\.(pdf|jpe?g|png|gif|bmp|tiff?|heic|docx?|xlsx?|xml|zip|rar|mp3|mp4|wav)$/i;
  const FILE = /[^\\/:*?"<>|\r\n\t]{1,160}?\.(pdf|jpe?g|png|gif|bmp|tiff?|heic|docx?|xlsx?|xml|zip|rar|mp3|mp4|wav)(?![a-z0-9])/gi;
  const UPLOAD = /chon tep|chon file|tai len|tai tep|dinh kem|upload|them tep|them file|browse/;
  const fold = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[đĐ]/g, "d").toLowerCase().trim();
  const shown = (el) => el.getClientRects().length > 0;
  const marks = new Set(document.querySelectorAll("input[type=file]"));
  for (const el of document.querySelectorAll("button, a, label, [role=button]")) {
    const t = fold(el.innerText || el.title || el.getAttribute("aria-label"));
    if (t && t.length <= 40 && UPLOAD.test(t)) marks.add(el);
  }
  const rows = new Set();
  for (const el of marks) {
    const row = el.closest("tr, .sd-question, .sd-row, li, [class*=row], [class*=item]");
    if (row && row !== document.body && row !== document.documentElement) rows.add(row);
  }
  // Bảng lồng bảng: hàng ngoài chứa cả bảng con, chỉ giữ hàng trong cùng.
  const inner = [...rows].filter((r) => ![...rows].some((o) => o !== r && r.contains(o)));
  return inner.filter(shown).slice(0, 80).map((row) => {
    const names = new Set();
    for (const el of row.querySelectorAll("a, span, div, li, p, td, label")) {
      const own = (el.innerText || "").trim();
      if (own && own.length <= 200 && !own.includes("\n") && EXT.test(own)) names.add(own);
      for (const attr of ["title", "download"]) {
        const v = (el.getAttribute(attr) || "").trim();
        if (v && v.length <= 200 && EXT.test(v)) names.add(v);
      }
    }
    if (!names.size) for (const m of (row.innerText || "").matchAll(FILE)) names.add(m[0].trim());
    // Ô chứa nhiều tệp liền nhau cho ra một chuỗi dính ("a.pdfb.jpg"): bỏ chuỗi chứa trọn một tên tệp khác.
    const files = [...names].filter((n) => ![...names].some((o) => o !== n && n.includes(o)));
    let label = "";
    const parts = row.matches("tr") ? [...row.cells].map((c) => c.innerText || "") : (row.innerText || "").split("\n");
    for (const part of parts) {
      const t = part.replace(FILE, " ").replace(/\s+/g, " ").trim();
      if (!t || (t.length < 40 && UPLOAD.test(fold(t)))) continue;
      if (row.matches("tr") ? t.length > label.length : !label) label = t;
    }
    return { label: label.slice(0, 240), files: files.slice(0, 40) };
  });
}"""

# Nút đính kèm của panel + danh sách tệp extension báo chưa đính được (mục "Chưa đính kèm được" trong Xem chi tiết).
POPUP_ATTACH_JS = r"""() => {
  const $ = (id) => document.getElementById(id);
  const shown = (el) => !!el && !el.hidden && getComputedStyle(el).display !== "none";
  const failed = [];
  for (const h of document.querySelectorAll("#attachResultList h3.err")) {
    const list = h.nextElementSibling;
    if (list) for (const li of list.querySelectorAll("li")) failed.push(li.textContent.trim());
  }
  return {
    attachStep: shown($("attachStepBtn")) && !$("attachStepBtn").disabled,
    fillAttach: shown($("fillAttachBtn")),
    failed,
  };
}"""

_ATTACH_TIMEOUT_S = 420
_ATTACH_STEP_S = 90
_SPLIT_DOCUMENTS_KEY = "autofill_attach_split_documents"


# Cùng tiêu chí với content/portal-login.js. Chạy thẳng trên trang để không phải đánh thức service worker của extension:
# đánh thức là mở một tab mới, mà đang lúc người dùng đăng nhập thì không được làm phiền.
LOGGED_IN_JS = r"""() => {
  const shown = (el) => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
  const account = document.querySelector("#account_name") || document.querySelector(".user-dropdown");
  if (shown(account)) return true;
  const fold = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[đĐ]/g, "d").toLowerCase().trim();
  return [...document.querySelectorAll("a, button, span, li")].some((el) => fold(el.textContent) === "dang xuat" && shown(el));
}"""


def preflight(remote: bool = False) -> str | None:
    """Câu báo lỗi nếu chưa chạy được trên cổng, None nếu ổn. ``remote``: Chromium chạy trên máy người dùng (runner_hub)."""
    config = (EXT / "api/config.js").read_text(encoding="utf-8")
    if not re.search(rf'const BACKEND_URL\s*=\s*"{re.escape(EXTENSION_BACKEND)}"', config):
        return (f"Extension đang trỏ backend khác {EXTENSION_BACKEND} nên lượt điền sẽ không chạy qua code vừa sửa. "
                f"Đổi BACKEND_URL trong auto-fill-hcc-extension/api/config.js về {EXTENSION_BACKEND}.")
    if not remote and sys.platform != "win32" and not os.environ.get("DISPLAY"):
        return "Máy chưa có màn hình cho cửa sổ bot (thiếu DISPLAY). Trên server hãy bật dịch vụ màn hình ảo autotest-vnc."
    return None


@lru_cache(maxsize=1)
def _extension_name() -> str:
    return json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))["name"]


def _loaded_extension() -> str | None:
    """Thư mục extension mà cửa sổ bot đang chạy đã nạp lúc mở (ghi khi bot tự mở cửa sổ). None = không rõ."""
    try:
        return _EXT_PATH_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _close_browser(pw) -> None:
    try:
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        session = browser.new_browser_cdp_session()
        session.send("Browser.close")
    except Error:
        pass
    for _ in range(50):
        if not _port_open(CDP_PORT):
            return
        time.sleep(0.2)


def _platform_flags() -> list[str]:
    """Linux chạy bằng root thì Chromium đòi --no-sandbox. Nên chạy dịch vụ bằng user thường để còn sandbox."""
    if sys.platform != "win32" and hasattr(os, "geteuid") and os.geteuid() == 0:
        return ["--no-sandbox"]
    return []


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


def _cdp_port(state: dict) -> int:
    """Cổng debug Chromium của bot: trên máy dịch vụ, hoặc cổng giả runner_hub mở dẫn tới Chromium trên máy người dùng."""
    runner = state.get("runner")
    return runner_hub.cdp_port(runner) if runner else CDP_PORT


def _ws_endpoint(port: int) -> str:
    """Địa chỉ WebSocket của Chromium qua cổng giả: Chromium trả địa chỉ theo cổng debug THẬT trên máy người dùng, phải thay cổng."""
    data = httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=20).json()
    return f"ws://127.0.0.1:{port}{urlsplit(data['webSocketDebuggerUrl']).path}"


def _open_urls(port: int = CDP_PORT) -> list[str]:
    """Danh sách tab đọc từ cổng debug: xem được đang ở đâu mà không cần nối Playwright vào trình duyệt."""
    try:
        pages = httpx.get(f"http://127.0.0.1:{port}/json/list", timeout=5).json()
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
        # Chromium trên máy người dùng (trình chạy bot): không tự mở trình duyệt, id extension giải nén ở máy đó khác máy này.
        self.runner = state.get("runner")
        self.ext_id_file = ROOT / "runs" / f"_extension_id_{self.runner}.txt" if self.runner else _EXT_ID_FILE

    # ---- vòng đời ------------------------------------------------------------------------------------------

    def attach(self, guard: bool = True) -> None:
        if self.runner:
            endpoint = _ws_endpoint(_cdp_port(self.state))  # trình chạy đã ngắt thì báo ngay, chưa khởi động Playwright
            self.pw = sync_playwright().start()
            self.browser = self.pw.chromium.connect_over_cdp(endpoint)
        else:
            self._attach_local()
        self.closed = False
        self.browser.on("disconnected", lambda _: setattr(self, "closed", True))
        self.context = self.browser.contexts[0]
        if guard:
            self.context.add_init_script(GUARD_JS)
            self.context.route(_is_portal, self._route)

    def _attach_local(self) -> None:
        self.pw = sync_playwright().start()
        if _port_open(CDP_PORT) and _loaded_extension() != str(EXT):
            # Cửa sổ cũ nạp extension ở chỗ khác (vd repo người phát triển, trỏ 12005): điền qua nó là gọi nhầm backend.
            self.log("Cửa sổ bot đang nạp extension khác thư mục hiện tại: đóng để mở lại đúng extension (phiên VNeID giữ trong profile).")
            _close_browser(self.pw)
        if not _port_open(CDP_PORT):
            PROFILE.mkdir(parents=True, exist_ok=True)
            _EXT_PATH_FILE.parent.mkdir(parents=True, exist_ok=True)
            if _loaded_extension() != str(EXT):
                _EXT_ID_FILE.unlink(missing_ok=True)  # id unpacked tính theo đường dẫn: đổi thư mục là đổi id
            _EXT_PATH_FILE.write_text(str(EXT), encoding="utf-8")
            subprocess.Popen(
                [
                    self.pw.chromium.executable_path, f"--user-data-dir={PROFILE}", f"--remote-debugging-port={CDP_PORT}",
                    "--no-first-run", "--no-default-browser-check", *_platform_flags(),
                    f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "about:blank",
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            for _ in range(100):
                if _port_open(CDP_PORT):
                    break
                time.sleep(0.2)
        self.browser = self.pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")

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
        self.ext_id_file.parent.mkdir(parents=True, exist_ok=True)
        self.ext_id_file.write_text(self.state["extId"], encoding="utf-8")
        return worker

    def _sw(self):
        worker = self._own_worker()
        if worker:
            return self._remember(worker)
        # Service worker MV3 tự ngủ sau ~30 giây, mở trang của extension để đánh thức.
        known = self.state.get("extId") or (self.ext_id_file.read_text(encoding="utf-8").strip() if self.ext_id_file.is_file() else "")
        if not known and self.runner:
            remote_runner = runner_hub.get(self.runner)
            known = remote_runner.info.get("extId", "") if remote_runner else ""  # trình chạy báo id lúc nối
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

    def sync_extension(self) -> bool:
        """Chromium trên máy người dùng: chép bản extension khu làm việc sang máy đó nếu khác (sau khi agent sửa / hoàn tác).
        True = vừa đổi, phải nạp lại extension. Chromium trên máy này đọc thẳng thư mục khu làm việc nên không cần."""
        if not self.runner:
            return False
        changed = runner_hub.sync_extension(self.runner)
        if changed:
            self.log(f"Đã chép bản extension mới sang {runner_hub.describe(self.runner)}.")
        return changed

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

    def auto_advance(self, allow_page: bool = False, settle_s: float = _ADVANCE_SETTLE_S) -> str | None:
        """Tự bấm một nút xác nhận / chuyển bước (xem ADVANCE_JS) ở mọi frame của tab làm việc. Trả chữ trên nút đã bấm.

        Chỉ bấm khi nút đã hiện liên tục ``settle_s`` giây: hộp thoại chọn cơ quan do agency-select.js của extension tự chọn
        rồi tự xác nhận trong 1–2 giây, bot bấm sớm hơn là xác nhận khi extension chưa chọn xong. Bot là lớp dự phòng."""
        if self.page is None:
            return None
        seen = self.state.setdefault("advanceSeen", {})
        clicks = self.state.setdefault("advanceAt", {})
        now = time.monotonic()
        for frame in self.page.frames:
            try:
                found = frame.evaluate(ADVANCE_JS, {"allowPage": allow_page, "click": None})
            except Error:
                continue  # frame đang chuyển trang
            if not found:
                continue
            label = found.get("label") or "?"
            for other in [k for k in seen if k != label]:
                seen.pop(other)
            first = seen.setdefault(label, now)
            if now - first < settle_s or now - clicks.get(label, -1e9) < _ADVANCE_GAP_S:
                return None
            try:
                done = frame.evaluate(ADVANCE_JS, {"allowPage": allow_page, "click": label})
            except Error:
                return None
            if not (done or {}).get("clicked"):
                return None
            clicks[label] = now
            seen.pop(label, None)
            self.log(f"Bot tự bấm \"{label}\"" + (" trong hộp thoại" if found.get("inDialog") else "") + ".")
            return label
        seen.clear()
        return None

    def is_blank(self) -> bool:
        if self.page is None:
            return False
        try:
            return bool(self.page.evaluate(BLANK_JS))
        except Error:
            return False  # đang chuyển trang: chưa kết luận

    def _reload_if_stuck(self, stuck_since: float | None, stuck: bool, reason: str) -> float | None:
        """Theo dõi trang trắng / form không lên: quá _BLANK_RELOAD_S giây thì tự tải lại (tối đa _BLANK_RELOADS lần mỗi lượt).
        Trả mốc bắt đầu kẹt mới (None = không kẹt)."""
        now = time.monotonic()
        if not stuck:
            return None
        if stuck_since is None:
            return now
        if now - stuck_since < _BLANK_RELOAD_S:
            return stuck_since
        done = self.state.get("blankReloads", 0)
        if done >= _BLANK_RELOADS:
            return stuck_since
        self.state["blankReloads"] = done + 1
        self.log(f"{reason} quá {_BLANK_RELOAD_S} giây, bot tự tải lại trang (lần {done + 1}/{_BLANK_RELOADS}).")
        try:
            self.page.reload(wait_until="domcontentloaded", timeout=60000)
        except Error as error:
            self.log(f"Tải lại trang lỗi: {error.message[:160]}")
        return None

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
        owner_since: float | None = None
        blank_since: float | None = None
        self.state["blankReloads"] = 0
        while time.monotonic() < end:
            self.sleep(1000)
            if self.on_login_page():
                raise RuntimeError("Cổng đòi đăng nhập lại.")
            self._follow_busiest_tab()
            flow = self.flow_state()
            if flow.get("ownerInfo"):
                # Bước Thông tin chủ hồ sơ: bot tự bấm Tiếp tục. Bấm mãi không qua (thiếu dữ liệu bắt buộc) mới nhờ người.
                owner_since = owner_since or time.monotonic()
                if not self.auto_advance(allow_page=True, settle_s=2) and time.monotonic() - owner_since > 30:
                    raise RuntimeError("Cổng dừng ở bước Thông tin chủ hồ sơ, bot bấm Tiếp tục không qua được.")
                continue
            owner_since = None
            if flow.get("infoModal"):
                if time.monotonic() - last_confirm > 6:
                    self.confirm_modal()
                    if time.monotonic() - last_confirm < 20:  # extension xác nhận không ăn: bot tự bấm nút trong hộp thoại
                        self.auto_advance()
                    last_confirm = time.monotonic()
                continue
            self.auto_advance()  # hộp thoại thông báo / xác nhận bất kỳ trên đường vào tờ khai
            blank_since = self._reload_if_stuck(blank_since, self.is_blank(), "Trang trắng")
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
        if self.runner:
            # Trình duyệt ở máy khác: đường dẫn trên máy này vô nghĩa với nó, gửi nội dung tệp (Playwright giới hạn 50 MB / lần).
            payload = [{"name": p.name, "mimeType": mimetypes.guess_type(p.name)[0] or "application/octet-stream", "buffer": p.read_bytes()}
                       for p in files]
            self.popup().set_input_files("#fileInput", payload)
        else:
            self.popup().set_input_files("#fileInput", [str(p) for p in files])
        end = time.monotonic() + 45
        while time.monotonic() < end and self.popup_state().get("files", 0) < len(files):
            self.sleep(500)

    def fill(self) -> dict:
        return self.press("#ocrBtn", _FILL_TIMEOUT_S)

    def press(self, selector: str, timeout_s: float) -> dict:
        """Bấm một nút chạy việc của panel (điền / đính kèm), tự đồng ý xử lý dữ liệu nếu panel hỏi, chờ tới khi panel rảnh."""
        self.sw_eval(SW_HOOK_JS)
        self.popup_click(selector)
        started = consented = False
        began = time.monotonic()
        state: dict = {}
        while time.monotonic() - began < timeout_s:
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
        raise RuntimeError(f"Quá {int(timeout_s)} giây panel vẫn chưa chạy xong.")

    # ---- đính kèm --------------------------------------------------------------------------------------------

    def read_attach_rows(self) -> list[dict]:
        """Các dòng đính kèm trên tab làm việc (mọi frame của cổng) cùng tên tệp đang hiện ở mỗi dòng."""
        rows: list[dict] = []
        if self.page is None:
            return rows
        for frame in self.page.frames:
            if frame.url.startswith("chrome-extension://"):
                continue
            try:
                rows += frame.evaluate(ATTACH_ROWS_JS) or []
            except Error:
                continue  # frame đang chuyển trang
        return rows

    def on_attach_step(self, expected: list[str]) -> bool:
        """Đang ở bước đính kèm: có dòng tải tệp trùng tên dòng lượt gốc đọc được. Ô ảnh trên tờ khai không tính."""
        rows = self.read_attach_rows()
        if not expected:
            return len(rows) >= 2
        return any(scoring.same_row(row.get("label"), name) for row in rows for name in expected)

    def attach_controls(self) -> dict:
        frame = self.popup()
        if not frame:
            return {}
        try:
            return frame.evaluate(POPUP_ATTACH_JS) or {}
        except Error:
            return {}

    def set_split_documents(self, on: bool) -> None:
        """Cài đặt "Tách giấy tờ" của extension, đặt đúng như lượt gốc. Panel nghe storage.onChanged nên nhận ngay."""
        self.sw_eval(f"(v) => chrome.storage.local.set({{ {_SPLIT_DOCUMENTS_KEY}: v }})", bool(on))

    def advance_to_attach(self, expected: list[str], timeout_s: float = _ATTACH_STEP_S) -> bool:
        """Cổng nhiều bước: tự bấm Tiếp tục / Bước tiếp theo tới khi thấy bảng đính kèm. Không bao giờ bấm nút có chữ lưu / nộp
        (ADVANCE_JS), nên cổng chỉ có nút "Lưu và tiếp tục" thì trả False để nhờ người."""
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            self._follow_busiest_attach_tab(expected)
            if self.on_attach_step(expected):
                self.sleep(1500)
                return True
            self.auto_advance(allow_page=True, settle_s=2)
            self.sleep(1500)
        return self.on_attach_step(expected)

    def _follow_busiest_attach_tab(self, expected: list[str]) -> None:
        """Cổng có thể mở bước đính kèm ở tab mới: chuyển sang tab có bảng đính kèm."""
        current = self.page
        for page in [p for p in self.context.pages if not p.url.startswith("chrome-extension://")]:
            self.page = page
            if self.on_attach_step(expected):
                return
        self.page = current

    def pick_attach_page(self, expected: list[str]) -> bool:
        pages = [p for p in self.context.pages if not p.url.startswith("chrome-extension://")]
        for page in pages:
            self.page = page
            if self.on_attach_step(expected):
                self.mark_form_reached()
                return True
        self.page = pages[0] if pages else None
        return False

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
        # Mỗi lần tự tải lại vì trang trắng / form không lên được cộng thêm thời gian chờ, kẻo vừa tải lại đã hết giờ.
        end = time.monotonic() + _FORM_BACK_S + _BLANK_RELOADS * _BLANK_RELOAD_S
        stuck_since: float | None = None
        self.state["blankReloads"] = 0
        while time.monotonic() < end:
            if self.on_login_page():
                return False
            if self.flow_state().get("infoModal"):
                self.confirm_modal()
                self.sleep(1500)
                self.auto_advance()
                continue
            self.auto_advance()
            count = self._form_count(self.page)
            if count >= need:
                self.sleep(1500)  # để cổng đổ xong dữ liệu theo tài khoản, kẻo đè lên giá trị vừa điền
                self.mark_form_reached()
                return True
            # Đúng trang tờ khai mà form không lên (trắng, hoặc chưa có ô nào) quá 8 giây: tải lại.
            stuck_since = self._reload_if_stuck(stuck_since, count == 0 or self.is_blank(), "Form không lên")
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


def expected_attach_rows(case: dict) -> list[str]:
    """Tên các dòng đính kèm extension đọc được ở lượt gốc: để nhận ra đã tới bước đính kèm, không nhầm ô ảnh trên tờ khai."""
    components = ((case.get("options") or {}).get("attachmentContext") or {}).get("components") or []
    names = [str(c.get("componentName") or "") for c in components if isinstance(c, dict)]
    names += [scoring.attach_row_name(item) for item in case.get("plan") or [] if isinstance(item, dict)]
    return [name for name in dict.fromkeys(names) if name and name != "?"]


def _attach_trace(username: str, since: datetime) -> dict | None:
    """Lượt đính kèm vừa chạy trên backend thử: trace kind=attach mới nhất của tài khoản chạy lại kể từ lúc bấm.

    Không dựa vào mã hỗ trợ trên panel: thủ tục điền kèm đính kèm hiện mã của lượt điền."""
    end = time.monotonic() + 10
    while True:
        trace = database().traces.find_one(
            {"kind": "attach", "username": username, "created_at": {"$gte": since}},
            {"request_id": 1, "llm_output.attachments": 1, "errors": 1},
            sort=[("created_at", -1)],
        )
        if trace or time.monotonic() > end:
            return trace
        time.sleep(1)


def _wait_attach_step(bot: PortalBot, wait_human: Callable[..., None], expected: list[str], message: str) -> None:
    """Nhờ người bấm sang bước đính kèm. Rời trình duyệt trong lúc chờ (Playwright đồng bộ giữ request của trang)."""
    while True:
        bot.detach()
        wait_human(message, "Đã tới bước đính kèm, chạy tiếp")
        bot.attach()
        if bot.pick_attach_page(expected):
            bot.ensure_panel()
            return
        message = "Bot chưa thấy bảng đính kèm trên cửa sổ bot. Hãy mở tới bước Thành phần hồ sơ (bảng có nút chọn tệp)."


def run_attach_once(
    bot: PortalBot, case: dict, number: int, credentials: dict, files: list[Path], out_dir: Path, wait_human: Callable[..., None],
) -> dict:
    """Một lần đính kèm trên cổng thật bằng giấy tờ thật của req: panel đính như cán bộ dùng, bot đọc lại tên tệp trên từng dòng.

    Cổng điền và đính cùng trang (nút "Điền biểu mẫu và đính kèm" hoặc thủ tục tự đính sau khi điền) thì bấm một nút. Cổng nhiều
    bước thì điền tờ khai, tự bấm sang bước đính kèm (không bấm nút có chữ lưu / nộp), rồi bấm "Đính kèm" của panel.
    Tệp tải lên nằm trong hồ sơ nháp của tài khoản VNeID đang đăng nhập; không bao giờ nộp.
    """
    began = time.monotonic()
    result: dict = {"n": number, "startedAt": datetime.now(timezone.utc).isoformat(), "mode": "portal", "kind": "attach"}
    expected = expected_attach_rows(case)
    bot.ensure_panel()
    bot.login_panel(credentials)
    bot.select_procedure(case["procedure"])
    bot.set_split_documents((case.get("options") or {}).get("splitDocuments") is True)
    bot.upload(files)
    controls = bot.attach_controls()
    if not controls.get("fillAttach") and controls.get("attachStep") and not bot.on_attach_step(expected):
        state = bot.fill()
        result["fill"] = {k: state.get(k) for k in ("status", "statusClass")}
        if not bot.advance_to_attach(expected):
            _wait_attach_step(
                bot, wait_human, expected,
                "Bot không tự sang được bước đính kèm (nút chuyển bước có chữ Lưu bot không bấm, hoặc tờ khai còn ô bắt buộc). "
                "Hãy bấm sang bước Thành phần hồ sơ trên cửa sổ bot.",
            )
        controls = bot.attach_controls()
    button = "#fillAttachBtn" if controls.get("fillAttach") else "#attachStepBtn" if controls.get("attachStep") else "#ocrBtn"
    rows_before = bot.read_attach_rows()
    replay.clear_ocr_cache([f.get("sha256") for f in case["storedFiles"]])
    since = datetime.now(timezone.utc)
    state = bot.press(button, _ATTACH_TIMEOUT_S)
    result["ms"] = int((time.monotonic() - began) * 1000)
    result["panel"] = {k: state.get(k) for k in ("status", "statusClass", "details")}
    result["button"] = button
    bot.sleep(2500)  # cổng hiện tên tệp sau khi tải xong
    rows_after = bot.read_attach_rows()
    failed = bot.attach_controls().get("failed") or []
    trace = _attach_trace(credentials["username"], since)
    shot = bot.screenshot(out_dir / f"run{number}.png")
    if shot:
        result["screenshot"] = f"run{number}.png"
    (out_dir / f"run{number}_portal.json").write_text(
        json.dumps({"button": button, "rowsBefore": rows_before, "rowsAfter": rows_after, "failed": failed}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not trace:
        result.update(status="error", error=f"Panel không gọi backend đính kèm: {state.get('status') or 'không có thông báo'}")
        return result
    request_id = trace["request_id"]
    plan = [item for item in (trace.get("llm_output") or {}).get("attachments") or [] if isinstance(item, dict)]
    errors = trace.get("errors") or []
    (out_dir / f"run{number}_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    names = [f.get("name") or "" for f in case["storedFiles"]]
    counts = case.get("pageCounts")
    details = replay.read_trace(request_id, "attach")
    (out_dir / f"run{number}_ocr.txt").write_text(details.pop("ocrText"), encoding="utf-8")
    result.update(details)
    result.update(
        requestId=request_id,
        status="partial" if errors else "ok",
        response={"fields": scoring.attach_fields(plan, counts, errors), "attachments": plan, "errors": errors, "requestId": request_id},
        form=scoring.attach_portal_values(plan, counts, names, rows_after, rows_before, failed, errors),
        portalRows=len(rows_after),
    )
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
        if bot.sync_extension() or state.get("extensionStale"):
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
                if replay.is_attach(case):
                    run = run_attach_once(bot, case, number, credentials, files, out_dir, wait_human)
                else:
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
    was_open = bool(bot.runner) or _port_open(CDP_PORT)
    bot.attach(guard=False)
    try:
        bot.sync_extension()
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
    try:
        urls = _open_urls(_cdp_port(state))
    except RuntimeError:
        return False  # trình chạy bot trên máy người dùng vừa ngắt: chờ nó nối lại
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


