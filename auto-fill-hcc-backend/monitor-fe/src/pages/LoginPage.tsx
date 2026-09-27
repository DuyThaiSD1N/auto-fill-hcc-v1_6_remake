import { useState, type FormEvent } from "react";
import { loginMonitor } from "../api";
import Icon from "../components/Icon";
import { Spinner } from "../components/Status";
import type { MonitorUser } from "../types";

export default function LoginPage({ onSuccess }: { onSuccess: (user: MonitorUser) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    setError("");
    try {
      onSuccess(await loginMonitor(username.trim(), password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không đăng nhập được. Thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main id="main-content" className="login">
      <form className="login-card" onSubmit={submit}>
        <div className="brand">
          <span className="brand__mark" aria-hidden="true"><span /><span /><span /><span /></span>
          <span className="brand__words"><strong>Monitor</strong><span>Trợ lý nhân dân</span></span>
        </div>
        <span className="ribbon" aria-hidden="true">
          <span className="ribbon__seg st-pre" style={{ width: "8%" }} />
          <span className="ribbon__seg st-ocr" style={{ width: "34%" }} />
          <span className="ribbon__seg st-llm" style={{ width: "46%" }} />
          <span className="ribbon__seg st-post" style={{ width: "12%" }} />
        </span>

        <label className="field">
          <span>Tên đăng nhập</span>
          <input className="input" autoComplete="username" autoFocus disabled={loading}
                 value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="field">
          <span>Mật khẩu</span>
          <span className="field__pw">
            <input className="input" autoComplete="current-password" disabled={loading}
                   type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} />
            <button className="btn btn--icon btn--ghost" type="button" onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>
              <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
            </button>
          </span>
        </label>
        {error ? <div className="form-error" role="alert">{error}</div> : null}
        <button className="btn btn--primary" style={{ height: 38 }} type="submit" disabled={loading || !username.trim() || !password}>
          {loading ? <Spinner label="Đang đăng nhập" /> : "Đăng nhập"}
        </button>
      </form>
    </main>
  );
}
