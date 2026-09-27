// Ngôn ngữ chung của Monitor: nhóm công đoạn (màu), tên từng bước, loại lượt, kết quả.
// Mã bước đến từ BE (app/monitor/recorder.py) — thêm bước mới ở BE thì thêm nhãn ở đây.

export type Group = "pre" | "ocr" | "llm" | "post" | "persist" | "other";

export const GROUPS: { key: Group; label: string }[] = [
  { key: "pre", label: "Tiền xử lý" },
  { key: "ocr", label: "OCR" },
  { key: "llm", label: "LLM" },
  { key: "post", label: "Hậu xử lý" },
  { key: "other", label: "Chưa đo" },
  { key: "persist", label: "Ghi DB" },
];

export function groupOf(name: string): Group | null {
  const head = name.split(".", 1)[0];
  return head === "pre" || head === "ocr" || head === "llm" || head === "post" || head === "persist" ? head : null;
}

const STEP_LABELS: Record<string, string> = {
  "pre.request": "Nhận request",
  "pre.receive": "Đọc tệp tải lên",
  "pre.prepare": "Chuẩn bị",
  "pre.load": "Nạp tệp của phiên",
  "pre.hash": "Băm tệp",
  "pre.decode": "Giải mã tệp",
  "pre.docx": "Tách DOCX",
  "pre.docx_images": "Ảnh trong DOCX",
  "ocr.call": "OCR",
  "ocr.cache": "Tra cache OCR",
  "ocr.remote": "Gọi OCR",
  "ocr.server": "Máy chủ OCR",
  "ocr.split": "Tách kết quả OCR",
  "llm.extract": "LLM trích xuất",
  "llm.reason": "LLM suy luận",
  "llm.plan": "LLM lập kế hoạch",
  "llm.classify": "LLM phân loại",
  "llm.intent": "LLM hiểu ý",
  "llm.call": "LLM",
  "post.parse": "Đọc JSON",
  "post.reason": "Suy luận vai trò",
  "post.fallback": "Vá kết quả",
  "post.validate": "Lọc field",
  "post.mapper": "Mapper thủ tục",
  "post.dates": "Chuẩn hoá ngày",
  "post.plan": "Luật đính kèm",
  "post.stt1": "STT1 ảo",
  "post.route": "Gán ô giấy tờ",
  "post.response": "Dựng response",
  "persist.files": "Lưu tệp",
  "persist.db": "Ghi DB",
  "persist.review": "Lưu rà soát",
  pipeline: "Pipeline thủ tục",
};

export function stepLabel(name: string): string {
  return STEP_LABELS[name] ?? name;
}

export const KIND_LABELS: Record<string, string> = {
  autofill: "Điền",
  attach: "Đính kèm",
  classify: "Phân loại",
  owner_info: "Chủ hồ sơ",
};

export const SOURCE_LABELS: Record<string, string> = { autofill: "Auto Fill", handfree: "Handfree" };

export const OUTCOME_LABELS: Record<string, string> = { ok: "OK", partial: "Có lỗi", error: "Hỏng" };

export const CACHE_REASONS: Record<string, string> = {
  not_found: "chưa có / hết hạn",
  thin: "text mỏng (OCR cho phân loại)",
  empty: "text rỗng",
  provider: "khác provider",
  no_key: "không băm được",
};

export const DROP_REASONS: Record<string, string> = {
  not_allowed: "tên field không có trong schema",
  duplicate: "trùng field",
  empty: "giá trị rỗng",
};
