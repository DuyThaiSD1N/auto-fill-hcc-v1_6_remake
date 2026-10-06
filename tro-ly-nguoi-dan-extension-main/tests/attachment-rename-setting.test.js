// Cài đặt theo tài khoản "đổi tên tệp theo loại giấy tờ khi đính kèm" (BE /api/v1/account/settings).
// Khoá: mặc định (chưa có bản sao) vẫn đổi tên như cũ; tắt thì giữ tên gốc đã làm sạch, tệp khác nội
// dung trùng tên được đánh số (không bị coi là "đã có trong hồ sơ"); tệp ảo virtualCopy luôn đổi tên.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const core = fs.readFileSync(path.join(root, "content/attach-core.js"), "utf8");
const stripComments = (src) => src.replace(/\/\/[^\n]*/g, "");

function slice(src, startMarker, endMarker) {
  const start = src.indexOf(startMarker);
  const end = src.indexOf(endMarker, start + startMarker.length);
  assert.ok(start >= 0 && end > start, `Không tìm thấy khối ${startMarker}`);
  return src.slice(start, end);
}

function loadNaming(stored) {
  let changeListener = null;
  const context = {
    chrome: {
      runtime: { lastError: null },
      storage: {
        local: { get: (_keys, cb) => cb(stored === undefined ? {} : { tlnd_account_settings: stored }) },
        onChanged: { addListener: (fn) => { changeListener = fn; } },
      },
    },
    foldChoiceText: (v) => String(v || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase(),
  };
  // dataUrlFilesForBatch gọi dataUrlToFile: thay bằng bản rút gọn chỉ trả tên tệp.
  context.dataUrlToFile = (payload, documentName) => ({ name: context.safeAttachmentFileName(payload, documentName) });
  vm.createContext(context);
  vm.runInContext(
    slice(core, "function fileExtension", "\nfunction dataUrlToFile") +
      slice(core, "function attachmentDocumentName(file)", "\nfunction setFilesOnInput") +
      "\nthis.safeAttachmentFileName = safeAttachmentFileName; this.ready = accountSettingsReady;" +
      " this.dataUrlFilesForBatch = dataUrlFilesForBatch; this.walletSafeDocumentName = walletSafeDocumentName;",
    context,
  );
  context.change = (value) => changeListener({ tlnd_account_settings: { newValue: value } }, "local");
  return context;
}

const photo = (tail) => ({ name: "image.jpg", dataUrl: `data:image/jpeg;base64,${"A".repeat(200)}${tail}` });

(async () => {
  // 1. Chưa có bản sao cài đặt (máy cũ, chưa đăng nhập, BE cũ) → đổi tên y như trước.
  const byDefault = loadNaming(undefined);
  await byDefault.ready;
  assert.equal(byDefault.safeAttachmentFileName({ name: "IMG_01.jpg" }, "Giấy khai sinh"), "Giấy khai sinh.jpg");
  assert.equal(byDefault.safeAttachmentFileName({ name: "a.pdf" }, "Tờ khai.pdf"), "Tờ khai.pdf", "không nhân đôi đuôi");

  // 2. Tắt → tên gốc (làm sạch ký tự cổng không nhận), bỏ qua documentName.
  const off = loadNaming({ renameAttachmentFiles: false });
  await off.ready;
  assert.equal(off.safeAttachmentFileName({ name: "Scan (1).pdf", dataUrl: "data:x;base64,AAA" }, "Giấy khai sinh"), "Scan 1.pdf");

  // 3. Hai tệp KHÁC nội dung cùng tên gốc → tệp sau được đánh số; cùng tệp gọi lại vẫn ra đúng tên cũ.
  const first = photo("BBBB");
  const second = photo("CCCC");
  assert.equal(off.safeAttachmentFileName(first, "CCCD"), "image.jpg");
  assert.equal(off.safeAttachmentFileName(second, "Hộ khẩu"), "image 2.jpg");
  assert.equal(off.safeAttachmentFileName({ ...first }, "CCCD"), "image.jpg", "cùng nội dung phải ra cùng tên");

  // 4. Tệp ẢO (virtualCopy) cùng byte tệp thật → vẫn đổi tên theo loại giấy dù đang tắt.
  assert.equal(off.safeAttachmentFileName(first, "Bản sao", { forceRename: true }), "Bản sao.jpg");

  // 5. Đổi cài đặt ở trang Cài đặt → content nhận ngay qua storage.onChanged.
  off.change({ renameAttachmentFiles: true });
  assert.equal(off.safeAttachmentFileName({ name: "x.pdf" }, "Giấy khai sinh"), "Giấy khai sinh.pdf");
  off.change(undefined);
  assert.equal(off.safeAttachmentFileName({ name: "x.pdf" }, "Giấy khai sinh"), "Giấy khai sinh.pdf", "xoá bản sao = mặc định bật");

  // 5b. Tên tệp tạo trên macOS (NFD) không được vỡ dấu thành "uy quye n thie t".
  const nfd = "uỷ quyền thiết.pdf".normalize("NFD");
  const offNfd = loadNaming({ renameAttachmentFiles: false });
  await offNfd.ready;
  assert.equal(offNfd.safeAttachmentFileName({ name: nfd, dataUrl: "data:x;base64,QQ" }, "Giấy ủy quyền"), "uỷ quyền thiết.pdf");
  assert.equal(offNfd.walletSafeDocumentName(nfd), "uỷ quyền thiết", "ô Tên tài liệu cũng phải giữ dấu");

  // 5c. Nhiều tệp cùng loại giấy vào MỘT ô (fixed-slot/HkdOnline): bật đổi tên thì đánh số, tắt thì tên gốc.
  const batchOn = loadNaming(undefined);
  await batchOn.ready;
  assert.deepEqual(
    batchOn.dataUrlFilesForBatch([
      { payload: { name: "scan-1.pdf" }, documentName: "Văn bản đề nghị" },
      { payload: { name: "scan-2.pdf" }, documentName: "Văn bản đề nghị.pdf" },
      { payload: { name: "scan-3.pdf" }, documentName: "" },
    ]).map((f) => f.name),
    ["Văn bản đề nghị.pdf", "Văn bản đề nghị 2.pdf", "scan-3.pdf"],
  );
  assert.deepEqual(
    offNfd.dataUrlFilesForBatch([{ payload: photo("DDDD"), documentName: "Văn bản đề nghị" }]).map((f) => f.name),
    ["image.jpg"],
  );

  // 6. Hợp đồng nối dây — các chỗ dễ bị merge nuốt / chép đè từ bản no handfree.
  const code = stripComments(core);
  assert.match(code, /async function attachFilesByPlan\([^)]*\) \{\s*await accountSettingsReady;/,
    "attachFilesByPlan (cả luồng split-attach gọi thẳng) phải chờ đọc xong cài đặt");
  assert.match(code, /dataUrlToFile\(payloadFile, intendedDocumentName, \{ forceRename: planItem\.virtualCopy === true \}\)/,
    "ví tài liệu phải giữ tên riêng cho tệp ảo");
  assert.match(code, /attpRowHasDoc\(row, item, payloadForPlanItem\(payloadFiles, item\)\)/,
    "chống trùng attp phải biết tên sẽ tải lên");
  assert.match(slice(code, "function attachmentPlanLabels", "\nfunction findExistingAttachedRowForPlanItem"),
    /renameAttachmentFiles[\s\S]*safeAttachmentFileName\(payloadFile, planItem\.documentName\)/,
    "nhãn 'đã có trong hồ sơ' phải dùng tên sẽ tải lên khi tắt đổi tên");

  assert.match(code, /dataUrlFilesForBatch\(indices[\s\S]{0,200}documentName: attachments\[i\]\.documentName/,
    "fixed-slot phải đặt tên theo loại giấy (trước đây luôn giữ tên gốc)");
  assert.match(code, /walletDocumentName = renameAttachmentFiles \|\| planItem\.virtualCopy === true \? intendedDocumentName : file\.name/,
    "tắt đổi tên thì ô Tên tài liệu của ví mang tên tệp tải lên");
  const br = stripComments(fs.readFileSync(path.join(root, "content/procedures/business-registration.js"), "utf8"));
  assert.match(br, /H\.dataUrlFilesForBatch\(/, "HkdOnline phải đặt tên theo cài đặt");
  assert.match(br, /p\.uploadName = files\[i\]\.name/, "HkdOnline phải nhớ tên đã tải lên cho pha gán loại");
  assert.match(br, /\[x\.fileName, x\.uploadName\]/, "gán loại theo tên phải khớp cả tên đã tải lên");

  const sidebar = stripComments(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
  assert.match(sidebar, /ACCOUNT_SETTINGS_KEY = "tlnd_account_settings"/, "khoá storage phải trùng với attach-core.js");
  assert.match(slice(sidebar, "function showLogin()", "\n  function renderAccount"), /forgetAccountSettings\(\)/,
    "đăng xuất / hết phiên phải bỏ bản sao cài đặt của tài khoản trước");
  assert.match(sidebar, /await window\.tlndAuth\.login\(u, p\);[\s\S]*?refreshAccountSettings\(\)[\s\S]*?bootChat\(\)/,
    "đăng nhập phải nạp cài đặt của tài khoản");
  assert.match(sidebar, /if \(st\?\.access\) \{[^}]*refreshAccountSettings\(\)/, "mở lại sidebar còn phiên cũng phải nạp");
  const client = fs.readFileSync(path.join(root, "api/client.js"), "utf8");
  assert.match(client, /\/api\/v1\/account\/settings/);
  const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
  assert.match(html, /id="rename-files-switch"[^>]*disabled/, "công tắc khoá tới khi đọc được giá trị từ BE");

  console.log("attachment rename setting (handfree) passed");
})().catch((e) => { console.error(e); process.exit(1); });
