import { useState, type FormEvent } from "react";
import { loginMonitor } from "../api";
import type { MonitorUser } from "../types";
import Brand from "../components/Brand";
import Icon from "../components/Icon";
import { Spinner } from "../components/Status";

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
      setError(reason instanceof Error ? reason.message : "Không đăng nhập được. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main id="main-content" className="login-page">
      <section className="login-context" aria-label="Giới thiệu Monitor">
        <div className="login-context__grid" />
        <div className="login-context__content">
          <Brand />
          <div className="login-context__copy">
            <span className="eyebrow eyebrow--light">Không gian kiểm tra độc lập</span>
            <h1>Đọc lại từng dấu vết của một hồ sơ.</h1>
            <p>
              Đối chiếu giấy tờ đầu vào, nội dung OCR, kết quả LLM và báo cáo thực thi trong
              cùng một màn hình.
            </p>
          </div>
          <div className="access-rule">
            <Icon name="shield" size={20} />
            <span>
              <strong>Vùng dữ liệu hạn chế</strong>
              Chỉ tài khoản giám sát được ủy quyền mới có thể truy cập.
            </span>
          </div>
        </div>
        <div className="scan-index" aria-hidden="true">
          <span>INPUT</span><span>OCR</span><span>LLM</span><span>REPORT</span>
        </div>
      </section>

      <section className="login-form-panel">
        <form className="login-card" onSubmit={submit}>
          <header>
            <span className="eyebrow">Xác thực Monitor</span>
            <h2>Đăng nhập</h2>
            <p>Dùng tài khoản super admin dành riêng cho hệ thống giám sát.</p>
          </header>

          <label className="field">
            <span>Tên đăng nhập</span>
            <span className="field__control">
              <Icon name="user" />
              <input
                autoComplete="username"
                autoFocus
                disabled={loading}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Nhập tên đăng nhập"
                value={username}
              />
            </span>
          </label>

          <label className="field">
            <span>Mật khẩu</span>
            <span className="field__control">
              <Icon name="shield" />
              <input
                autoComplete="current-password"
                disabled={loading}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Nhập mật khẩu"
                type={showPassword ? "text" : "password"}
                value={password}
              />
              <button
                aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                className="field__reveal"
                onClick={() => setShowPassword((current) => !current)}
                tabIndex={0}
                type="button"
              >
                <Icon name={showPassword ? "eye-off" : "eye"} />
              </button>
            </span>
          </label>

          {error ? <div className="form-error" role="alert">{error}</div> : null}

          <button
            className="button button--primary button--large"
            disabled={loading || !username.trim() || !password}
            type="submit"
          >
            {loading ? <Spinner label="Đang xác thực" /> : <><Icon name="shield" /> Vào Monitor</>}
          </button>

          <p className="login-card__footnote">
            Phiên đăng nhập được tách hoàn toàn khỏi web quản lý hồ sơ hiện tại.
          </p>
        </form>
      </section>
    </main>
  );
}
