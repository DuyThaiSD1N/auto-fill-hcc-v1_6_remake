const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const css = fs.readFileSync(path.join(__dirname, "..", "popup.css"), "utf8");

function luminance(hex) {
  const rgb = hex.match(/[0-9a-f]{2}/gi).map((part) => parseInt(part, 16) / 255);
  const linear = rgb.map((value) => value <= 0.04045
    ? value / 12.92
    : ((value + 0.055) / 1.055) ** 2.4);
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrast(foreground, background) {
  const lighter = Math.max(luminance(foreground), luminance(background));
  const darker = Math.min(luminance(foreground), luminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

assert.match(
  css,
  /\.procedure-trigger:hover:not\(:disabled\)\s*\{[\s\S]*?background:\s*#f4f8fe;[\s\S]*?border-color:\s*#1565c0;/,
  "Hover của ô thủ tục phải dùng nền sáng riêng, không nhận nền xanh đậm của button chung",
);
assert.match(
  css,
  /\.procedure-trigger:focus-visible\s*\{[\s\S]*?outline:\s*3px solid rgba\(21, 101, 192, 0\.24\);/,
  "Ô thủ tục phải có focus ring rõ cho bàn phím",
);
assert.match(
  css,
  /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.procedure-trigger-caret[\s\S]*?transition:\s*none;/,
  "Chuyển động của picker phải tôn trọng reduced motion",
);

assert.ok(contrast("#555555", "#f4f8fe") >= 4.5, "Nhãn thường phải đạt WCAG AA trên nền hover");
assert.ok(contrast("#1565c0", "#f4f8fe") >= 4.5, "Tên thủ tục phải đạt WCAG AA trên nền hover");

console.log("procedure picker UI: light hover, focus ring and AA contrast passed");
