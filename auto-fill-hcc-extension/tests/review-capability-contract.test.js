const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const endpoints = fs.readFileSync(path.join(root, "api", "endpoints.js"), "utf8");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const review = fs.readFileSync(path.join(root, "content", "review.js"), "utf8");

test("review chỉ mở khi process trả capability đúng request", () => {
  assert.match(endpoints, /getReviewSources\(requestId, reviewToken\)/);
  assert.match(endpoints, /if \(!requestId \|\| !reviewToken\) return null/);
  assert.match(endpoints, /sources\?token=\$\{encodeURIComponent\(reviewToken\)\}/);
  assert.match(popup, /maybeShowReview\(res\.requestId \|\| res\.sessionId, res\.reviewToken\)/);
  assert.match(popup, /reviewToken,/);
});

test("ảnh bbox mang capability và không còn URL public chỉ theo requestId", () => {
  assert.match(review, /let SRC_TOKEN = ""/);
  assert.match(review, /token=\$\{encodeURIComponent\(SRC_TOKEN\)\}/);
  assert.match(review, /SRC_TOKEN = msg\.reviewToken \|\| ""/);
  assert.doesNotMatch(
    review,
    /image\?index=\$\{src\.imageIndex \|\| 0\}`/,
  );
});
