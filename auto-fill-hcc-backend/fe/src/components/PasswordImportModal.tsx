import { useMemo, useRef, useState } from "react";

import {
  downloadPasswordTemplate,
  importPasswords,
  type PasswordImportResult,
  type PasswordImportRow,
  type PasswordImportStatus,
} from "../api";

interface Props {
  onClose: () => void;
  /** Gọi sau khi đã lưu để trang tải lại danh sách. */
  onImported: () => void;
}

const STATUS_META: Record<PasswordImportStatus, { label: string; cls: string }> = {
  store: { label: "Khớp — sẽ lưu", cls: "ok" },
  stored: { label: "Đã lưu", cls: "ok" },
  already: { label: "Đã lưu từ trước", cls: "neutral" },
  mismatch: { label: "Sai mật khẩu", cls: "warn" },
  not_found: { label: "Không có tài khoản", cls: "warn" },
  duplicate_in_file: { label: "Trùng trong file", cls: "neutral" },
  error: { label: "Lỗi", cls: "warn" },
};
const STATUS_ORDER: PasswordImportStatus[] = [
  "store", "stored", "mismatch", "not_found", "error", "already", "duplicate_in_file",
];

type Filter = "all" | PasswordImportStatus;

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function PasswordImportModal({ onClose, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<PasswordImportResult | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [busy, setBusy] = useState<"" | "check" | "apply" | "template">("");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const applied = result?.applied === true;
  const toStore = result?.summary.store ?? 0;
  const rows = useMemo<PasswordImportRow[]>(
    () => (result?.rows ?? []).filter((row) => filter === "all" || row.status === filter),
    [result, filter],
  );

  async function check(picked: File) {
    setFile(picked);
    setResult(null);
    setFilter("all");
    setError("");
    setBusy("check");
    try {
      setResult(await importPasswords(picked, false));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không kiểm tra được file.");
    } finally {
      setBusy("");
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function apply() {
    if (!file) return;
    setBusy("apply");
    setError("");
    try {
      const done = await importPasswords(file, true);
      setResult(done);
      setFilter("all");
      if (done.summary.stored) onImported();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không lưu được mật khẩu.");
    } finally {
      setBusy("");
    }
  }

  async function template() {
    setBusy("template");
    setError("");
    try {
      const { blob, filename } = await downloadPasswordTemplate();
      saveBlob(blob, filename || "mau-nap-mat-khau.xlsx");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được file mẫu.");
    } finally {
      setBusy("");
    }
  }

  const close = () => !busy && onClose();

  return (
    <div className="modal-backdrop" onClick={close}>
      <div className="modal-card import-card" onClick={(e) => e.stopPropagation()}>
        <h2>Nạp mật khẩu đã biết</h2>

        {!result && (
          <p className="muted">
            Dành cho tài khoản tạo trước khi có tính năng lưu mật khẩu. File Excel cần cột{" "}
            <b>Tên đăng nhập</b> và <b>Mật khẩu</b>. Mỗi mật khẩu được so với mật khẩu đang dùng:
            chỉ dòng <b>khớp</b> mới được lưu để xem và xuất về sau.{" "}
            <b>Không đổi mật khẩu của tài khoản nào.</b>
          </p>
        )}

        <div className="import-pick">
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            disabled={Boolean(busy) || applied}
            onChange={(e) => {
              const picked = e.target.files?.[0];
              if (picked) void check(picked);
            }}
          />
          <button type="button" className="ghost sm" onClick={template} disabled={Boolean(busy)}>
            {busy === "template" ? "Đang tải…" : "Tải file mẫu"}
          </button>
        </div>

        {busy === "check" && (
          <div className="muted" aria-live="polite">Đang so mật khẩu trong {file?.name}…</div>
        )}
        {busy === "apply" && (
          <div className="muted" aria-live="polite">
            Đang lưu {toStore} mật khẩu, vui lòng không đóng cửa sổ…
          </div>
        )}
        {error && <div className="error" role="alert">{error}</div>}

        {result && (
          <>
            <div className="import-summary" role="group" aria-label="Lọc theo trạng thái">
              <button
                type="button"
                className={`import-count${filter === "all" ? " active" : ""}`}
                onClick={() => setFilter("all")}
              >
                Tất cả <b>{result.rows.length}</b>
              </button>
              {STATUS_ORDER.filter((s) => result.summary[s]).map((s) => (
                <button
                  type="button"
                  key={s}
                  className={`import-count ${STATUS_META[s].cls}${filter === s ? " active" : ""}`}
                  onClick={() => setFilter(s)}
                >
                  {STATUS_META[s].label} <b>{result.summary[s]}</b>
                </button>
              ))}
            </div>

            <div className="table-wrap import-table">
              <table>
                <thead>
                  <tr>
                    <th>Dòng</th>
                    <th>Tên đăng nhập</th>
                    <th>Kết quả</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.row}>
                      <td className="muted">{row.row}</td>
                      <td className="col-reqid">{row.username || "—"}</td>
                      <td>
                        <span className={`badge ${STATUS_META[row.status].cls}`}>
                          {STATUS_META[row.status].label}
                        </span>
                        {row.message && <div className="import-reason">{row.message}</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        <div className="modal-actions">
          {applied ? (
            <button type="button" className="btn-primary" onClick={onClose}>
              Xong
            </button>
          ) : (
            <>
              <button type="button" className="ghost" onClick={close} disabled={Boolean(busy)}>
                Hủy
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={apply}
                disabled={Boolean(busy) || !toStore}
                title={result && !toStore ? "Không có dòng nào khớp để lưu" : ""}
              >
                {busy === "apply" ? "Đang lưu…" : `Lưu ${toStore} mật khẩu`}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
