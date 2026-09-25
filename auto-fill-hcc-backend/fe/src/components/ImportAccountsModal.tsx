import { useMemo, useRef, useState } from "react";
import {
  downloadImportTemplate,
  importUsers,
  type ImportResult,
  type ImportRow,
  type ImportRowStatus,
} from "../api";

interface Props {
  onClose: () => void;
  /** Gọi sau khi đã tạo xong để trang tải lại danh sách. */
  onImported: () => void;
}

const STATUS_META: Record<ImportRowStatus, { label: string; cls: string }> = {
  create: { label: "Sẽ tạo", cls: "ok" },
  created: { label: "Đã tạo", cls: "ok" },
  exists: { label: "Đã tồn tại", cls: "neutral" },
  exists_deleted: { label: "Đã tồn tại (đã xóa)", cls: "neutral" },
  duplicate_in_file: { label: "Trùng trong file", cls: "neutral" },
  error: { label: "Lỗi", cls: "warn" },
};
// Thứ tự hiện ô đếm: việc cần làm trước, lỗi cần sửa ngay sau.
const STATUS_ORDER: ImportRowStatus[] = [
  "create", "created", "error", "exists", "exists_deleted", "duplicate_in_file",
];
const ROLE_LABEL = { province: "HCC tỉnh", commune: "HCC xã", "": "—" } as const;

type Filter = "all" | ImportRowStatus;

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ImportAccountsModal({ onClose, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [busy, setBusy] = useState<"" | "check" | "apply" | "template">("");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const applied = result?.applied === true;
  const toCreate = result?.summary.create ?? 0;
  const rows = useMemo<ImportRow[]>(
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
      setResult(await importUsers(picked, false));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không kiểm tra được file.");
    } finally {
      setBusy("");
      // Cho phép chọn lại ĐÚNG file vừa chọn (đã sửa trong Excel) — cùng tên thì onChange không bắn.
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function apply() {
    if (!file) return;
    setBusy("apply");
    setError("");
    try {
      const done = await importUsers(file, true);
      setResult(done);
      setFilter("all");
      if (done.summary.created) onImported();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tạo được tài khoản.");
    } finally {
      setBusy("");
    }
  }

  async function template() {
    setBusy("template");
    setError("");
    try {
      const { blob, filename } = await downloadImportTemplate();
      saveBlob(blob, filename || "mau-tao-tai-khoan.xlsx");
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
        <h2>Nhập tài khoản từ Excel</h2>

        {!result && (
          <p className="muted">
            Mỗi dòng một tài khoản, gồm Tên, Tên tỉnh, Tên xã/phường, Tên đăng nhập, Mật khẩu và
            Role. Tên đăng nhập đã có sẽ được <b>bỏ qua</b>, tài khoản cũ giữ nguyên. File được
            kiểm tra trước — chưa tạo tài khoản nào cho tới khi bấm xác nhận.
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

        {busy === "check" && <div className="muted">Đang kiểm tra {file?.name}…</div>}
        {busy === "apply" && (
          <div className="muted">Đang tạo {toCreate} tài khoản, vui lòng không đóng cửa sổ…</div>
        )}
        {error && <div className="error">{error}</div>}

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
                    <th>Tên</th>
                    <th>Địa bàn</th>
                    <th>Vai trò</th>
                    <th>Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.row}>
                      <td className="muted">{row.row}</td>
                      <td className="col-reqid">{row.username || "—"}</td>
                      <td>{row.name || <span className="muted">—</span>}</td>
                      <td>
                        {row.xa ? `${row.xa}, ` : ""}
                        {row.tinh || <span className="muted">—</span>}
                      </td>
                      <td>{ROLE_LABEL[row.role]}</td>
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
                disabled={Boolean(busy) || !toCreate}
                title={result && !toCreate ? "Không còn dòng nào để tạo" : ""}
              >
                {busy === "apply" ? "Đang tạo…" : `Tạo ${toCreate} tài khoản`}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
