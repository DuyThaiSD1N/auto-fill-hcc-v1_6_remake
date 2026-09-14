/**
 * PROBE ĐÍNH KÈM — bấm nút "Chọn tệp tin" của một dòng thành phần hồ sơ rồi ghi lại CHÍNH XÁC cổng
 * mở ra cái gì. Dùng khi trợ lý báo "Không mở được modal Danh sách tài liệu điện tử": engine đang
 * chờ một hộp thoại [role=dialog] có đúng tên đó, còn eForm mới có thể dùng hộp thoại kiểu khác,
 * một menu thả xuống, hay bung thẳng hộp chọn tệp của máy.
 *
 * DÙNG:
 *   1. Mở Bước 2 (Thành phần hồ sơ) của hồ sơ đang làm dở.
 *   2. F12 → tab Console. Lần đầu Chrome chặn dán, gõ  allow pasting  rồi Enter.
 *   3. Dán NGUYÊN file này, Enter. Mặc định thử dòng 1; muốn dòng khác thì chạy
 *      __probeAttach(3)  (số là STT dòng trên bảng).
 *   4. Nếu máy bung hộp chọn tệp của Windows thì cứ bấm Cancel, kết quả vẫn ghi đủ.
 *   5. Chép JSON trong clipboard gửi lại. Không copy được thì lấy ở  window.__probeAttach_result.
 *
 * GHI LẠI: các dòng hồ sơ đọc được, nút đã bấm, và SO SÁNH DOM trước/sau khi bấm — hộp thoại mới,
 * lớp phủ mới, thẻ mới gắn vào <body>, ô input[type=file] mới xuất hiện.
 *
 * An toàn: chỉ bấm đúng nút chọn tệp của dòng được chỉ định, không tải file nào lên, không gửi dữ
 * liệu đi đâu.
 */
(() => {
  // Panel của trợ lý là một khung riêng nằm trong trang. Console mặc định có thể đang trỏ vào khung
  // đó thay vì trang cổng — chạy ở đấy thì không thấy dòng hồ sơ nào, báo ngay cho đỡ mất công.
  if (location.protocol === "chrome-extension:" || location.protocol === "moz-extension:") {
    const message =
      "[probe-attach] Đang chạy trong khung của extension, không phải trang cổng. " +
      "Ở góc trái thanh Console có ô chọn ngữ cảnh (đang là popup.html) — đổi sang top / dichvucong.gov.vn rồi dán lại.";
    console.error(message);
    return { error: message, url: location.href };
  }

  const clean = (value) => String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  const text = (node) => clean(node && (node.innerText || node.textContent)).slice(0, 200);
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const fold = (value) =>
    String(value || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();

  function describe(node) {
    if (!node) return null;
    const rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;
    return {
      tag: String(node.tagName || "").toLowerCase(),
      id: clean(node.id),
      cls: clean(node.getAttribute && node.getAttribute("class")),
      role: clean(node.getAttribute && node.getAttribute("role")),
      ariaModal: clean(node.getAttribute && node.getAttribute("aria-modal")),
      name: clean(node.getAttribute && node.getAttribute("name")),
      type: clean(node.getAttribute && node.getAttribute("type")),
      text: text(node),
      visible: !!(rect && (rect.width || rect.height)),
    };
  }

  // Mọi thứ trông giống hộp thoại/lớp phủ, KHÔNG chỉ [role=dialog] như engine đang dò.
  const OVERLAY_SELECTOR = [
    "[role='dialog']",
    "[role='alertdialog']",
    "[aria-modal='true']",
    "dialog",
    ".modal",
    ".ant-modal",
    ".MuiDialog-root",
    ".cdk-overlay-container > *",
    ".mat-menu-panel",
    ".mat-mdc-menu-panel",
    "[role='menu']",
    "[data-radix-popper-content-wrapper]",
  ].join(",");

  function snapshot() {
    return {
      overlays: Array.from(document.querySelectorAll(OVERLAY_SELECTOR)).map(describe),
      fileInputs: Array.from(document.querySelectorAll("input[type='file']")).map(describe),
      bodyChildren: Array.from(document.body.children).map((node) => describe(node)),
      hasWalletTitle: fold(document.body.innerText || "").includes("danh sach tai lieu dien tu"),
    };
  }

  function attachmentRows() {
    return Array.from(document.querySelectorAll("tr")).filter((row) =>
      Array.from(row.querySelectorAll("button")).some((button) => fold(text(button)).includes("chon tep"))
    );
  }

  function chooseButton(row) {
    return Array.from(row.querySelectorAll("button")).find((button) =>
      fold(text(button)).includes("chon tep")
    ) || null;
  }

  async function probe(stt = 1) {
    const rows = attachmentRows();
    const report = {
      url: location.href,
      probedAt: new Date().toISOString(),
      rowCount: rows.length,
      rows: rows.map((row, index) => ({
        stt: index + 1,
        cells: Array.from(row.cells || []).map((cell) => ({
          text: text(cell),
          controls: Array.from(cell.querySelectorAll("input, button, a")).map(describe),
        })),
      })),
    };

    const row = rows[stt - 1];
    const button = row ? chooseButton(row) : null;
    report.picked = { stt, found: !!button, button: describe(button) };

    if (!button) {
      report.note = "Không tìm thấy nút chọn tệp ở dòng này.";
    } else {
      report.before = snapshot();
      button.scrollIntoView({ block: "center" });
      button.focus && button.focus();
      button.click();
      await sleep(1500);
      report.after = snapshot();
      // Thứ MỚI xuất hiện sau khi bấm mới là câu trả lời; danh sách đầy đủ chỉ để đối chiếu.
      const beforeKeys = new Set(report.before.overlays.map((item) => JSON.stringify(item)));
      report.newOverlays = report.after.overlays.filter((item) => !beforeKeys.has(JSON.stringify(item)));
      const beforeFiles = new Set(report.before.fileInputs.map((item) => JSON.stringify(item)));
      report.newFileInputs = report.after.fileInputs.filter((item) => !beforeFiles.has(JSON.stringify(item)));
    }

    report.json = JSON.stringify(report, null, 2);
    window.__probeAttach_result = report;

    console.log("%c[probe-attach] dòng hồ sơ đọc được:", "font-weight:bold", report.rowCount);
    console.table(report.rows.map((item) => ({ stt: item.stt, ten: item.cells[1]?.text || item.cells[0]?.text })));
    console.log("[probe-attach] nút đã bấm:", report.picked);
    console.log("[probe-attach] hộp thoại/menu MỚI sau khi bấm:", report.newOverlays);
    console.log("[probe-attach] ô input file MỚI sau khi bấm:", report.newFileInputs);
    console.log("[probe-attach] trang có chữ 'Danh sách tài liệu điện tử':", report.after?.hasWalletTitle);

    try {
      if (typeof copy === "function") copy(report.json);
      else if (navigator.clipboard) navigator.clipboard.writeText(report.json);
      console.log("[probe-attach] Đã copy JSON vào clipboard — Ctrl+V để dán gửi đi.");
    } catch (error) {
      console.warn("[probe-attach] Không copy được, dùng: copy(window.__probeAttach_result.json)", error);
    }
    return report;
  }

  window.__probeAttach = probe;
  return probe(1);
})();
