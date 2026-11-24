import { createContext, useContext, type ReactNode } from "react";
import Icon from "../components/Icon";
import { navigate, onLinkClick } from "../router";
import type { CaseStatus } from "./api";

// ---- che số giấy tờ ---------------------------------------------------------------------------------------------------

const LONG_DIGITS = /\d(?:[ .]?\d){8,15}/g;

/** Số ≥ 9 chữ số (CCCD, SĐT, số giấy tờ) hiện dạng 024199•••147. Năm / ngày tháng (≤ 8 chữ số) giữ nguyên. */
export function maskDigits(text: string): string {
  return text.replace(LONG_DIGITS, (run) => {
    const digits = run.replace(/\D/g, "");
    const head = digits.length >= 12 ? 6 : 3;
    return `${digits.slice(0, head)}•••${digits.slice(-3)}`;
  });
}

export const RevealContext = createContext(false);

/** Giá trị có thể chứa số giấy tờ: che theo cài đặt "Hiện đủ số" của trang. */
export function Masked({ value, empty = "—" }: { value: unknown; empty?: string }) {
  const reveal = useContext(RevealContext);
  const text = valueText(value);
  if (!text) return <span className="faint">{empty}</span>;
  return <>{reveal ? text : maskDigits(text)}</>;
}

export function useMask() {
  const reveal = useContext(RevealContext);
  return (value: unknown) => {
    const text = valueText(value);
    return reveal ? text : maskDigits(text);
  };
}

export function valueText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  try { return JSON.stringify(value); } catch { return String(value); }
}

// ---- thời gian ----------------------------------------------------------------------------------------------------------

/** ms tính từ đầu lượt → "03:34". */
export function offset(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "—";
  const total = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** Giờ thật của một mốc trong lượt. */
export function clockAt(startAt: string | null, t: number): string {
  if (!startAt) return "—";
  const d = new Date(new Date(startAt).getTime() + t);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function humanDuration(ms: number | null | undefined): string {
  if (!ms && ms !== 0) return "—";
  const total = Math.round(ms / 1000);
  if (total < 60) return `${total} giây`;
  const m = Math.floor(total / 60);
  const s = total % 60;
  return s ? `${m} phút ${s} giây` : `${m} phút`;
}

// ---- nhãn ------------------------------------------------------------------------------------------------------------

export const VERDICTS: Record<string, { label: string; tone: "ok" | "bad" | "warn" | "muted"; cause?: string; fix?: string }> = {
  same: { label: "Giữ nguyên", tone: "ok" },
  llm: {
    label: "Người dân sửa", tone: "bad", cause: "Trích sai từ giấy tờ",
    fix: "Giấy tờ có giá trị đúng nhưng trợ lý trích sai: xem lại prompt / mapper của trường này.",
  },
  ocr: {
    label: "Người dân sửa", tone: "bad", cause: "OCR đọc nhầm",
    fix: "Chữ / số trên ảnh bị đọc nhầm: hỏi lại người dân khi giá trị quan trọng, hoặc đối chiếu chéo giữa các giấy tờ.",
  },
  other: {
    label: "Người dân sửa", tone: "bad", cause: "Giá trị không có trên giấy tờ",
    fix: "Người dân điền giá trị không có trên giấy tờ (mặc định / suy ra sai): ô không có trên giấy thì hỏi, không đặt sẵn.",
  },
  cleared: {
    label: "Người dân xoá", tone: "bad", cause: "Điền thừa",
    fix: "Trợ lý điền ô người dân không muốn khai: xem điều kiện điền của ô.",
  },
  missing: {
    label: "Trợ lý bỏ trống", tone: "warn", cause: "Trợ lý bỏ trống",
    fix: "Người dân tự điền. Nếu giá trị có trên giấy tờ thì là ô trợ lý bỏ sót.",
  },
  nodata: {
    label: "Form không nhận", tone: "warn", cause: "Form không nhận giá trị",
    fix: "Backend có giá trị nhưng ô trên cổng vẫn trống: lỗi phía extension (tên ô / định dạng / option).",
  },
  recorded: { label: "Theo lúc ghi", tone: "muted" },
  "": { label: "Chưa có ảnh chụp", tone: "muted" },
};

export function VerdictBadge({ verdict }: { verdict: string }) {
  const v = VERDICTS[verdict] ?? { label: verdict, tone: "muted" as const };
  return <span className={`lab-badge lab-badge--${v.tone}`}>{v.label}</span>;
}

export const SOURCE_TEXT: Record<string, string> = { llm: "đọc từ giấy tờ", rule: "luật / mapper suy ra", be: "backend trả", none: "" };

export const STATUS: Record<CaseStatus, { label: string; tone: "ok" | "bad" | "warn" | "muted" }> = {
  pass: { label: "Đạt", tone: "ok" },
  fail: { label: "Lỗi", tone: "bad" },
  review: { label: "Cần duyệt", tone: "warn" },
  error: { label: "Không chạy được", tone: "bad" },
};

export function StatusBadge({ status, failed }: { status?: CaseStatus | null; failed?: number }) {
  if (!status) return <span className="faint">—</span>;
  const s = STATUS[status];
  return <span className={`lab-badge lab-badge--${s.tone}`}>{s.label}{status === "fail" && failed ? ` ${failed} ô` : ""}</span>;
}

export const SOURCE_LABEL: Record<string, string> = { backend: "Backend", form: "Form", chat: "Hội thoại", extension: "Extension" };

export const DATA_SOURCE: Record<string, string> = {
  archive: "Kho lưu trữ",
  mongo: "Mongo nguồn",
  local: "Mongo local",
};

// ---- khung trang ------------------------------------------------------------------------------------------------------

export function LabNotice() {
  return (
    <div className="lab-notice" role="note">
      <Icon name="shield" size={16} />
      <div><strong>Lưu ý</strong> Đây là giấy tờ thật của người dân. Mọi lượt mở, tái hiện, xem và tải gói đều được ghi lại.</div>
    </div>
  );
}

// Tab chung của mục menu "Ca test": Bộ ca / Lần chạy / Cấu hình ghi (mỗi tab vẫn là một đường dẫn riêng).
const CA_TEST_TABS = [
  { key: "suites", label: "Bộ ca", href: "/autotest/suites" },
  { key: "runs", label: "Lần chạy", href: "/autotest/runs" },
  { key: "config", label: "Cấu hình ghi", href: "/autotest/config" },
] as const;

export function CaTestTabs({ active }: { active: (typeof CA_TEST_TABS)[number]["key"] }) {
  return (
    <div className="tabs" role="tablist" aria-label="Phần của Ca test">
      {CA_TEST_TABS.map((t) => (
        <button key={t.key} role="tab" type="button" aria-selected={active === t.key} onClick={() => navigate(t.href)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function LabCrumbs({ items }: { items: { label: string; href?: string; mono?: boolean }[] }) {
  return (
    <nav className="crumbs" aria-label="Vị trí">
      <span>Auto test</span>
      {items.map((item, i) => (
        <span key={i} style={{ display: "contents" }}>
          <span>/</span>
          {item.href ? (
            <a href={item.href} className={item.mono ? "mono" : undefined} onClick={(e) => onLinkClick(e, item.href!)}>{item.label}</a>
          ) : <span className={item.mono ? "mono" : undefined}>{item.label}</span>}
        </span>
      ))}
    </nav>
  );
}

export function Unavailable() {
  return (
    <div className="state">
      <strong>Dịch vụ Auto test chưa chạy trên máy này</strong>
      <span>Phần này đọc lượt qua dịch vụ agent (auto-test-hcc, cổng 12009). Bật bằng: <code>python auto-test-hcc/agents/server.py</code></span>
    </div>
  );
}

export function Section({ title, sub, actions, children }: { title: string; sub?: ReactNode; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="panel lab-section">
      <div className="panel__head">
        <div className="lab-section__title"><h2>{title}</h2>{sub ? <span>{sub}</span> : null}</div>
        {actions ? <div className="lab-section__actions">{actions}</div> : null}
      </div>
      <div className="lab-section__body">{children}</div>
    </section>
  );
}

export function downloadJson(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
