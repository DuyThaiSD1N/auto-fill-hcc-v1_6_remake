const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const contentSource = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const angularSource = fs.readFileSync(path.join(__dirname, "..", "content", "fill-angular.js"), "utf8");

// Cổng liên thông render ô "Dân tộc khác" bằng input[name], không có formcontrolname.
assert.match(contentSource, /input\[name="\$\{escaped\}"\], textarea\[name="\$\{escaped\}"\], select\[name="\$\{escaped\}"\]/);
assert.match(contentSource, /named\.closest\("app-input, mat-form-field"\) \|\| named/);

const helperStart = contentSource.indexOf("function findFormControl(names)");
const helperEnd = contentSource.indexOf("\n  // Tô VIỀN VÀNG", helperStart);
assert.ok(helperStart >= 0 && helperEnd > helperStart, "Không tách được findFormControl");

const appInput = { kind: "app-input" };
const namedInput = {
  getAttribute: (name) => name === "name" ? "ChaDantocKhac" : "",
  closest: (selector) => selector === "app-input, mat-form-field" ? appInput : null,
};
const sandbox = {
  CSS: { escape: (value) => String(value) },
  document: {
    querySelector: (selector) => selector.includes('input[name="ChaDantocKhac"]') ? namedInput : null,
    querySelectorAll: () => [],
  },
};
vm.runInNewContext(`
  ${contentSource.slice(helperStart, helperEnd)}
  globalThis.find = findFormControl;
`, sandbox);
assert.equal(sandbox.find(["ChaDantocKhac"]), appInput);

// Ô động phải được chờ sau khi dropdown dân tộc vừa chọn "Khác".
assert.match(angularSource, /\["DantocKhac", "MeDantocKhac", "ChaDantocKhac"\]\.includes\(f\.name\)/);
assert.match(angularSource, /await waitFor\(\(\) => findFormControl\(candidates\), 4000, 50\)/);

// Không được coi click option là thành công giả: phải verify nhãn ng-select đã commit đúng giá trị.
assert.match(angularSource, /function ngSelectedMatches\(ng, want\)/);
assert.match(angularSource, /await waitFor\(\(\) => ngSelectedMatches\(ng, want\), 1500, 50\)/);
assert.match(angularSource, /ng-select \[\$\{fcn\}\] không commit/);

console.log("angular dynamic ethnicity: name fallback + render wait passed");
