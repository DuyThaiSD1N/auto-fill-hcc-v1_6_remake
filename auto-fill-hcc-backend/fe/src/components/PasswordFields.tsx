import { useEffect, useId, useState } from "react";

import { revealPassword } from "../api";
import type { ManagedUser } from "../types";

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Clipboard API cần HTTPS + quyền; không có thì để người dùng tự chọn và chép.
    return false;
  }
}

function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
      <circle cx="12" cy="12" r="2.8" />
      {!open && <path d="M4 20 20 4" />}
    </svg>
  );
}

interface PasswordInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoFocus?: boolean;
  error?: string;
}

/** Ô nhập mật khẩu có nút Hiện/Ẩn. Lỗi hiện ngay dưới ô. */
export function PasswordInput({ label, value, onChange, autoFocus, error }: PasswordInputProps) {
  const [shown, setShown] = useState(false);
  const errorId = useId();
  return (
    <label>
      {label}
      <span className="password-input">
        <input
          type={shown ? "text" : "password"}
          value={value}
          autoFocus={autoFocus}
          autoComplete="new-password"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="password-eye"
          aria-label={shown ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          aria-pressed={shown}
          onClick={() => setShown((v) => !v)}
        >
          <EyeIcon open={shown} />
        </button>
      </span>
      {error && <span className="field-error" id={errorId}>{error}</span>}
    </label>
  );
}

interface StoredPasswordProps {
  account: ManagedUser;
  onChangePassword: () => void;
}

/** Mật khẩu hiện tại trong modal Sửa: chỉ gọi BE khi bấm Hiện, đóng modal là quên. */
export function StoredPassword({ account, onChangePassword }: StoredPasswordProps) {
  const [password, setPassword] = useState<string | null>(null);
  const [shown, setShown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<"" | "ok" | "fail">("");
  const stored = account.password_stored === true;

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(""), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  async function toggle() {
    setError("");
    if (shown) {
      setShown(false);
      return;
    }
    if (password !== null) {
      setShown(true);
      return;
    }
    setLoading(true);
    try {
      const res = await revealPassword(account.id);
      if (res.password === null) {
        setError(
          res.vaultEnabled
            ? "Không đọc được mật khẩu đã lưu. Hãy đổi mật khẩu để lưu lại."
            : "Máy chủ chưa cấu hình khoá lưu mật khẩu.",
        );
        return;
      }
      setPassword(res.password);
      setShown(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xem được mật khẩu.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stored-password">
      <span className="stored-password-label">Mật khẩu hiện tại</span>
      <div className="stored-password-row">
        <input
          readOnly
          aria-label="Mật khẩu hiện tại"
          type={shown ? "text" : "password"}
          value={shown && password !== null ? password : stored ? "••••••••" : ""}
          placeholder={stored ? undefined : "Chưa lưu mật khẩu"}
        />
        {stored && (
          <button type="button" className="ghost sm" onClick={toggle} disabled={loading}>
            {loading ? "Đang tải…" : shown ? "Ẩn" : "Hiện"}
          </button>
        )}
        {shown && password !== null && (
          <button
            type="button"
            className="ghost sm"
            onClick={async () => setCopied((await copyText(password)) ? "ok" : "fail")}
          >
            {copied === "ok" ? "Đã sao chép" : "Sao chép"}
          </button>
        )}
      </div>
      {copied === "fail" && (
        <span className="field-error">Không sao chép được — hãy chọn chữ và sao chép thủ công.</span>
      )}
      {error && <span className="field-error">{error}</span>}
      <p className="form-hint">
        {stored
          ? "Bấm Hiện để xem. Lượt xem được ghi vào nhật ký."
          : "Tài khoản tạo trước khi có tính năng lưu mật khẩu nên không xem được."}{" "}
        <button type="button" className="inline-link" onClick={onChangePassword}>
          Đổi mật khẩu
        </button>
      </p>
    </div>
  );
}
