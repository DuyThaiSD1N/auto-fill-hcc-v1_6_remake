const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const popupSource = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const contentSource = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

const resetStart = popupSource.indexOf("function shouldResetProcedureWork(nextKey)");
const resetEnd = popupSource.indexOf("\nfunction resetProcedureWorkState", resetStart);
assert.ok(resetStart >= 0 && resetEnd > resetStart, "Không tách được rule đổi phiên thủ tục");

const sandbox = { workProcedureKey: "", selectedProcedureKey: "" };
vm.runInNewContext(`
  let workProcedureKey = "";
  let selectedProcedureKey = "";
  ${popupSource.slice(resetStart, resetEnd)}
  globalThis.check = (workKey, selectedKey, nextKey) => {
    workProcedureKey = workKey;
    selectedProcedureKey = selectedKey;
    return shouldResetProcedureWork(nextKey);
  };
`, sandbox);

// Reload/chuyển bước cùng thủ tục phải giữ file.
assert.equal(sandbox.check("procedure-a", "procedure-a", "procedure-a"), false);
// Detect tạm rỗng không phải là một thủ tục mới.
assert.equal(sandbox.check("procedure-a", "procedure-a", ""), false);
// Lần chọn đầu tiên không có hồ sơ cũ để xóa.
assert.equal(sandbox.check("", "", "procedure-a"), false);
// Chuyển A → B phải tạo phiên làm việc mới.
assert.equal(sandbox.check("procedure-a", "procedure-a", "procedure-b"), true);
// Màn chọn chung làm selection rỗng vẫn phải nhớ file thuộc A.
assert.equal(sandbox.check("procedure-a", "", "procedure-b"), true);

assert.match(
  popupSource,
  /if \(revision !== sessionWriteRevision\) return;[\s\S]*?enqueueSessionWrite\(async \(\) => \{[\s\S]*?if \(revision !== sessionWriteRevision\) return;/,
  "Save session phải chặn cả trước và trong hàng đợi để file cũ không ghi đè trở lại",
);
assert.match(
  popupSource,
  /procedureKey:\s*selectedProcedureKey,\s*\n\s*workProcedureKey,/,
  "Session phải lưu thủ tục sở hữu file qua reload",
);
assert.match(
  popupSource,
  /if \(selectionChanged \|\| workOwnerChanged\) await saveSession\(\);/,
  "Detect lại cùng thủ tục không được ghi lại khối file base64",
);
assert.match(
  popupSource,
  /async function selectProcedure\(key, \{ source = "manual" \} = \{\}\)[\s\S]*?manualProcedureOverride = true;[\s\S]*?procedureAutoDetected = false;/,
  "Chọn từ dropdown phải chuyển sang chế độ thủ công",
);
assert.match(
  popupSource,
  /function openProcedureDropdown\(\) \{\s*if \(!procedureDropdown\) return;/,
  "Ô thủ tục phải mở được kể cả khi vừa tự nhận diện",
);
assert.match(
  popupSource,
  /const isUrlNavigation =[\s\S]*?manualProcedureOverride = false;[\s\S]*?else if \(manualProcedureOverride\) \{\s*return;/,
  "Lựa chọn tay phải sống qua DOM update và chỉ reset khi URL đổi/reload",
);
assert.ok(
  (popupSource.match(/selectProcedure\(key, \{ source: "auto" \}\)/g) || []).length >= 2,
  "Nhận diện ban đầu và SPA phải đánh dấu rõ nguồn tự động",
);

assert.match(contentSource, /new MutationObserver\(/, "Phải detect lại khi SPA đổi DOM mà URL đứng yên");
assert.match(
  contentSource,
  /\[0, 350, 1000, 2500\]/,
  "URL SPA phải retry để chờ tên thủ tục render xong",
);
assert.match(
  contentSource,
  /signature === lastSignalSignature/,
  "DOM watcher phải bỏ qua tín hiệu không đổi",
);

console.log("procedure session + SPA detection lifecycle passed");
