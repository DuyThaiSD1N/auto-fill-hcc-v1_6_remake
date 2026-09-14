const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");

// Queue chỉ mở một tab ACTIVE; pending + activeTabId phải được lưu trước khi điều hướng để content
// không đọc hụt bundle. activeTabId chặn tuyệt đối việc mở tab tiếp theo khi tab trước chưa terminal.
const openNextStart = background.indexOf("async function openNextSplitQueueItemUnlocked");
const openNextEnd = background.indexOf("async function finishSplitQueueTabUnlocked", openNextStart);
const openNext = background.slice(openNextStart, openNextEnd);
const activeGuardAt = openNext.indexOf("if (state.activeTabId)");
const createBlankAt = openNext.indexOf('chrome.tabs.create({ url: "about:blank", active: true })');
const persistPendingAt = openNext.indexOf("await setPendingMap(pendingMap)");
const persistQueueAt = openNext.indexOf("await setSplitAttachQueue(state)");
const navigateAt = openNext.indexOf("await chrome.tabs.update(tab.id, { url: item.url, active: true })");
assert.ok(activeGuardAt >= 0 && activeGuardAt < createBlankAt, "Không được mở tab mới khi queue còn tab active");
assert.ok(createBlankAt < persistPendingAt && persistPendingAt < persistQueueAt && persistQueueAt < navigateAt,
  "Phải lưu pending + queue trước khi điều hướng tab active");
assert.doesNotMatch(openNext, /active: false/);

const finishQueueStart = background.indexOf("async function finishSplitQueueTabUnlocked");
const finishQueueEnd = background.indexOf("chrome.tabs.onRemoved", finishQueueStart);
const finishQueue = background.slice(finishQueueStart, finishQueueEnd);
assert.match(finishQueue, /state\.activeTabId = null/);
assert.match(finishQueue, /await openNextSplitQueueItemUnlocked\(\)/);

// Tab đầu tiên cũng phải được đưa vào pending khi thao tác trực tiếp gặp modal treo.
const stageActionStart = background.indexOf('msg?.action === "stageDossierTabAttach"');
const stageActionEnd = background.indexOf('msg?.action === "reloadDossierTabAttach"', stageActionStart);
const stageAction = background.slice(stageActionStart, stageActionEnd);
assert.match(stageAction, /map\[tabId\] = \{/);
assert.match(stageAction, /recoveryCode: msg\.recoveryCode \|\| null/);
assert.match(stageAction, /recoveryCount: msg\.recoveryCode \? 1 : 0/);

const firstAttachAt = popup.indexOf('const firstRes = await sendToContent({');
const stageCurrentAt = popup.indexOf('action: "stageDossierTabAttach"', firstAttachAt);
const startQueueAt = popup.indexOf('action: "startSplitAttachQueue"', stageCurrentAt);
const reloadCurrentAt = popup.indexOf('action: "reloadDossierTabAttach"', startQueueAt);
assert.ok(firstAttachAt < stageCurrentAt, "Chỉ stage tab hiện tại sau khi thao tác trực tiếp đã lỗi");
assert.ok(stageCurrentAt < startQueueAt && startQueueAt < reloadCurrentAt,
  "Phải lưu queue chờ tab hiện tại trước khi reload phục hồi");
assert.match(popup, /SPLIT_RELOADABLE_WALLET_CODES\.has\(String\(firstRes\.code \|\| ""\)\)/);
const splitAttachStart = popup.indexOf("async function attachSplitAcrossTabs");
const splitAttachEnd = popup.indexOf("\n// ===== BƯỚC CHẤP THUẬN", splitAttachStart);
const splitAttach = popup.slice(splitAttachStart, splitAttachEnd);
assert.match(splitAttach, /procedure === "chung-thuc-chu-ky"/);
assert.match(splitAttach, /buildDefaultSplitBundles/);
assert.match(splitAttach, /action: "startSplitAttachQueue"/);
assert.match(splitAttach, /chrome\.storage\.local\.set/);
assert.match(splitAttach, /itemsStorageKey: SPLIT_ATTACH_QUEUE_STAGE_KEY/);
assert.doesNotMatch(splitAttach, /action: "startSplitAttachQueue",[\s\S]{0,200}items: rest\.map/);
assert.doesNotMatch(splitAttach, /openDossierTabAndAttach/);

const startQueueActionStart = background.indexOf('msg?.action === "startSplitAttachQueue"');
const startQueueActionEnd = background.indexOf('msg?.action === "getPendingAttach"', startQueueActionStart);
const startQueueAction = background.slice(startQueueActionStart, startQueueActionEnd);
assert.match(startQueueAction, /chrome\.storage\.local\.get\(itemsStorageKey\)/);
assert.match(startQueueAction, /chrome\.storage\.local\.remove\(itemsStorageKey\)/);

const pollerStart = content.indexOf("// ===== Tách hồ sơ (split)");
const pollerEnd = content.indexOf("\n  function detectFormKind", pollerStart);
const poller = content.slice(pollerStart, pollerEnd);
const openWalletStart = content.indexOf("async function openDocumentWalletForRow");
const openWalletEnd = content.indexOf("\n  function findWalletUploadDoneButton", openWalletStart);
const openWallet = content.slice(openWalletStart, openWalletEnd);

// Không coi gọi click là đã chuyển bước; phải đợi URL/DOM hoặc bảng đính kèm thực sự thay đổi.
assert.match(poller, /includes\("thong tin chu ho so"\)/);
assert.match(poller, /const maxNextFailures = 5;/);
assert.match(poller, /location\.href !== beforeUrl/);
assert.match(poller, /!ownerStepPresent\(\)/);
assert.match(poller, /hasAttachmentTarget\(\)/);
assert.doesNotMatch(poller, /nextClicks/);
assert.match(poller, /const pendingFiles = Array\.isArray\(pending\?\.files\)/);
assert.match(poller, /const pendingAttachments = Array\.isArray\(pending\?\.attachments\)/);
assert.match(poller, /attachFilesByPlan\(pendingFiles, pendingAttachments/);
assert.match(poller, /if \(r\?\.ok && !r\?\.error\)/);
assert.match(poller, /if \(document\.hidden\)/);
assert.match(poller, /finishPendingAttach\(true\)/);
assert.match(poller, /action: ok \? "clearPendingAttach" : "failPendingAttach"/);

// Mỗi trạng thái ví tài liệu bị treo được reload tối đa 3 lần và guard phải sống qua reload cùng tab.
assert.match(content, /code: "wallet-stale-modal"/);
assert.match(content, /code: "wallet-modal-not-opened"/);
assert.match(content, /code: "wallet-device-upload-not-opened"/);
assert.match(content, /function isSplitReloadableWalletError\(code\)/);
assert.match(content, /const SPLIT_MAX_RELOADS_PER_WALLET_CODE = 3;/);
assert.match(poller, /const recoveryKeyForCode = \(code\)/);
assert.match(poller, /sessionStorage\.setItem\(recoveryKeyForCode\(code\)/);
assert.match(poller, /const seedInitialSplitReload = \(\) =>/);
assert.match(poller, /pending\?\.recoveryCount/);
assert.match(poller, /seedInitialSplitReload\(\);/);
assert.match(poller, /splitReloadCount\(r\.code\) < SPLIT_MAX_RELOADS_PER_WALLET_CODE/);
assert.match(poller, /SPLIT_RELOADABLE_WALLET_CODES\.size \* SPLIT_MAX_RELOADS_PER_WALLET_CODE/);
assert.match(poller, /splitReloadTotal\(\) < maxReloadTotal/);
assert.match(poller, /location\.reload\(\)/);
assert.match(poller, /vẫn lỗi sau reload; dừng để tránh vòng lặp/);
assert.match(content, /splitMode && isSplitReloadableWalletError\(result\.code\)/);
assert.match(content, /if \(Number\(item\?\.componentIndex\) === 2\) return true;/);

// Chứng thực chữ ký: mỗi bundle có đúng một tài liệu STT1 và dùng lại cùng giấy tùy thân ở STT2.
assert.match(popup, /async function buildSignatureSplitBundles\(payloadFiles, attachments\)/);
assert.match(popup, /const identityEntries = entries\.filter/);
assert.match(popup, /const documentEntries = entries\.filter/);
assert.match(popup, /if \(!documentEntries\.length\)/);
assert.match(popup, /files\.push\(sharedIdentityFile\)/);
assert.match(popup, /componentIndex: 2/);
assert.match(popup, /return \{ files, planItems \}/);
assert.match(popup, /procedure === "chung-thuc-chu-ky"/);
assert.match(popup, /files: bundle\.files,\s*attachments: bundle\.planItems/);

// Nút mở Radix wallet chỉ được nhận một logical click; phát click kép có thể mở rồi đóng modal ngay.
assert.match(openWallet, /button\.focus\?\.\(\);\s*button\.click\(\);/);
assert.doesNotMatch(openWallet, /clickLikeUser\(button\)/);

// Nút "Tải lên từ thiết bị" phải được bấm lại có kiểm chứng và theo dõi node dialog mới do React render.
assert.match(content, /function walletDeviceUploadState\(previousDialog\)/);
assert.match(content, /function openWalletDeviceUpload\(previousDialog\)/);
assert.match(content, /for \(let attempt = 0; attempt < 2; attempt\+\+\)/);
assert.match(content, /const deviceUpload = await openWalletDeviceUpload\(dialog\)/);
assert.match(content, /dialog = deviceUpload\.dialog \|\| dialog/);

// Không được coi modal đóng là đã đính file: phải thấy tên file thật trên dòng hồ sơ.
assert.match(content, /async function waitForPersistedAttachment\(row, planItem = \{\}, previousName = ""\)/);
assert.match(content, /const attachedName = rowAttachedFileName\(liveRow\)/);
assert.match(content, /code: "wallet-file-not-persisted"/);
assert.match(content, /markAttachmentResult\(persisted\.row, true\)/);
// Số lần thử lại của MỘT tệp giờ do vòng round-robin khống chế (tối đa MAX_ROUNDS lượt), thay
// cho cặp cờ persistedRetryUsed cũ. Vẫn đúng cam kết gốc: không để tệp này bị thử ba lượt liên
// tiếp rồi vẫn tô xanh — nhưng lần thử sau được giãn ra sau khi đã đính các tệp khác, và hỏng
// một tệp không còn chặn phần còn lại.
assert.match(content, /const MAX_ROUNDS = 2/);
assert.match(content, /for \(let round = 1; round <= MAX_ROUNDS && queue\.length && !splitAbort/);
assert.match(content, /action: "pausePendingAttach"/);
assert.match(background, /msg\?\.action === "pausePendingAttach"/);

// Popup tab đầu phải bám tiến độ background và đổi sang trạng thái hoàn tất, không giữ câu tĩnh.
assert.match(popup, /const SPLIT_ATTACH_PROGRESS_KEY = "autofill_split_attach_progress"/);
assert.match(popup, /function splitProgressPresentation\(progress\)/);
assert.match(popup, /chrome\.storage\?\.onChanged\?\.addListener/);
assert.match(popup, /Đã đính kèm thành công \$\{succeeded\}\/\$\{total\} hồ sơ/);
const splitAttachProgressStart = popup.indexOf("async function attachSplitAcrossTabs");
const splitAttachProgressEnd = popup.indexOf("\n// ===== BƯỚC CHẤP THUẬN", splitAttachProgressStart);
assert.doesNotMatch(popup.slice(splitAttachProgressStart, splitAttachProgressEnd), /hồ sơ đang chờ/);

console.log("split attachment recovery: sequential active queue, visibility pause and bounded reload passed");
