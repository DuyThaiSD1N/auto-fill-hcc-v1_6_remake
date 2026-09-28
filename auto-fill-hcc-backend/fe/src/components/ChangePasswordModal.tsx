import { useState } from "react";

import { setUserPassword } from "../api";
import type { ManagedUser } from "../types";
import { PasswordInput, copyText } from "./PasswordFields";

interface Props {
  account: ManagedUser;
  onClose: () => void;
  /** Gọi sau khi đổi xong để trang tải lại danh sách (cờ "đã lưu mật khẩu" thay đổi). */
  onChanged: () => void;
}

const MIN_LENGTH = 8;

export default function ChangePasswordModal({ account, onClose, onChanged }: Props) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [copied, setCopied] = useState<"" | "ok" | "fail">("");

  const tooShort = password.length > 0 && password.length < MIN_LENGTH;
  const mismatch = confirm.length > 0 && confirm !== password;
  const canSubmit = password.length >= MIN_LENGTH && confirm === password && !saving;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    setError("");
    try {
      await setUserPassword(account.id, password);
      setDone(true);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đổi được mật khẩu.");
    } finally {
      setSaving(false);
    }
  }

  const close = () => !saving && onClose();

  return (
    <div className="modal-backdrop" onClick={close}>
      <form className="modal-card" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h2>Đổi mật khẩu: {account.username}</h2>

        {done ? (
          <>
            <p className="muted">
              Đã đổi mật khẩu. Các phiên đang đăng nhập của tài khoản vẫn giữ nguyên; lần đăng
              nhập sau phải dùng mật khẩu mới.
            </p>
            <div className="stored-password">
              <span className="stored-password-label">Mật khẩu mới</span>
              <div className="stored-password-row">
                <input readOnly aria-label="Mật khẩu mới" value={password} />
                <button
                  type="button"
                  className="ghost sm"
                  onClick={async () => setCopied((await copyText(password)) ? "ok" : "fail")}
                >
                  {copied === "ok" ? "Đã sao chép" : "Sao chép"}
                </button>
              </div>
              {copied === "fail" && (
                <span className="field-error">
                  Không sao chép được — hãy chọn chữ và sao chép thủ công.
                </span>
              )}
            </div>
            <div className="modal-actions">
              <button type="button" className="btn-primary" onClick={onClose}>
                Xong
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="muted">
              {account.name || account.username}
              {account.tinh ? ` · ${account.xa ? `${account.xa}, ` : ""}${account.tinh}` : ""}
            </p>
            <PasswordInput
              label="Mật khẩu mới"
              value={password}
              onChange={setPassword}
              autoFocus
              error={tooShort ? `Mật khẩu phải có ít nhất ${MIN_LENGTH} ký tự.` : undefined}
            />
            <PasswordInput
              label="Xác nhận mật khẩu mới"
              value={confirm}
              onChange={setConfirm}
              error={mismatch ? "Mật khẩu xác nhận không khớp." : undefined}
            />
            {error && <div className="error" role="alert">{error}</div>}
            <div className="modal-actions">
              <button type="button" className="ghost" onClick={close} disabled={saving}>
                Hủy
              </button>
              <button type="submit" className="btn-primary" disabled={!canSubmit}>
                {saving ? "Đang đổi…" : "Đổi mật khẩu"}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  );
}
