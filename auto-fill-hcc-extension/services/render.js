// render.js — markdown → HTML an toàn, tự viết (không phụ thuộc CDN/marked để tránh CSP extension).
// Hỗ trợ: heading, đậm/nghiêng, code inline, link, danh sách (-, *, 1.), xuống dòng, đoạn văn.
// LUÔN escape HTML trước khi xử lý markup → an toàn với nội dung từ server.

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function inlineMd(text) {
  let s = escapeHtml(text);
  // code inline
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  // bold
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  // italic
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  // link [text](url) — chỉ cho http/https
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, t, u) => {
    const url = u.replace(/"/g, "%22");
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${t}</a>`;
  });
  return s;
}

function renderMarkdown(md) {
  const lines = String(md ?? "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let listType = null; // "ul" | "ol"

  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = null;
    }
  };

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) {
      closeList();
      continue;
    }
    // Heading
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      closeList();
      const level = h[1].length + 1; // h1 → h2 (tránh nuốt header panel)
      html.push(`<h${level}>${inlineMd(h[2])}</h${level}>`);
      continue;
    }
    // Unordered list
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    if (ul) {
      if (listType !== "ul") {
        closeList();
        listType = "ul";
        html.push("<ul>");
      }
      html.push(`<li>${inlineMd(ul[1])}</li>`);
      continue;
    }
    // Ordered list
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (ol) {
      if (listType !== "ol") {
        closeList();
        listType = "ol";
        html.push("<ol>");
      }
      html.push(`<li>${inlineMd(ol[1])}</li>`);
      continue;
    }
    // Paragraph
    closeList();
    html.push(`<p>${inlineMd(line)}</p>`);
  }
  closeList();
  return html.join("\n");
}

window.renderMarkdown = renderMarkdown;
window.escapeHtml = escapeHtml;
