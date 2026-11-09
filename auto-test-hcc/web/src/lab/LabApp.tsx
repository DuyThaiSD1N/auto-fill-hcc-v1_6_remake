import { useCallback, useEffect, useState, type FormEvent } from "react";
import Icon from "../components/Icon";
import { PageLoading, Spinner } from "../components/Status";
import { LAB_AUTH_EXPIRED_EVENT, labSession, loginLab, validateLabSession, type LabUser } from "./api";
import AutoTest from "./auto/AutoTest";

const THEME_KEY = "hcc_monitor_theme";

function useTheme() {
  const [theme, setTheme] = useState<string>(() => {
    try { return localStorage.getItem(THEME_KEY) || ""; } catch { return ""; }
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme) root.dataset.theme = theme; else delete root.dataset.theme;
    try {
      if (theme) localStorage.setItem(THEME_KEY, theme); else localStorage.removeItem(THEME_KEY);
    } catch { /* storage bị chặn → chỉ áp dụng trong phiên */ }
  }, [theme]);
  const dark = theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  return { dark, toggle: () => setTheme(dark ? "light" : "dark") };
}

function Brand() {
  return (
    <div className="brand">
      <span className="brand__mark" aria-hidden="true"><span /><span /><span /><span /></span>
      <span className="brand__words"><strong>Tự động kiểm thử</strong><span>Trợ lý nhân dân</span></span>
    </div>
  );
}

function LoginPage({ onSuccess }: { onSuccess: (user: LabUser) => void }) {
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
      onSuccess(await loginLab(username.trim(), password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không đăng nhập được. Thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main id="main-content" className="login">
      <form className="login-card" onSubmit={submit}>
        <Brand />
        <p className="muted lab-login-hint">Đăng nhập bằng tài khoản Monitor (super_admin).</p>
        <label className="field">
          <span>Tên đăng nhập</span>
          <input className="input" autoComplete="username" autoFocus disabled={loading} value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="field">
          <span>Mật khẩu</span>
          <span className="field__pw">
            <input className="input" autoComplete="current-password" disabled={loading} type={showPassword ? "text" : "password"}
                   value={password} onChange={(e) => setPassword(e.target.value)} />
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

export default function LabApp() {
  const [auth, setAuth] = useState<"checking" | "signed-out" | "signed-in">("checking");
  const [user, setUser] = useState<LabUser | null>(labSession.user);

  const signOut = useCallback(() => {
    labSession.clear();
    setUser(null);
    setAuth("signed-out");
  }, []);

  useEffect(() => {
    let active = true;
    validateLabSession().then((u) => {
      if (!active) return;
      setUser(u);
      setAuth(u ? "signed-in" : "signed-out");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    window.addEventListener(LAB_AUTH_EXPIRED_EVENT, signOut);
    return () => window.removeEventListener(LAB_AUTH_EXPIRED_EVENT, signOut);
  }, [signOut]);

  if (auth === "checking") return <PageLoading label="Đang kiểm tra phiên…" />;
  if (auth === "signed-out" || !user) return <LoginPage onSuccess={(u) => { setUser(u); setAuth("signed-in"); }} />;
  return <Shell user={user} onLogout={signOut} />;
}

function Shell({ user, onLogout }: { user: LabUser; onLogout: () => void }) {
  const { dark, toggle } = useTheme();
  return (
    <div className="lab-shell">
      <header className="lab-top">
        <Brand />
        <span className="lab-top__title">Agent sửa ca lỗi và làm thủ tục mới, hệ thống tự test, build và kiểm tra lại</span>
        <div className="topbar__right">
          <button className="btn btn--icon btn--ghost" type="button" onClick={toggle} aria-label={dark ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}>
            <Icon name={dark ? "sun" : "moon"} size={16} />
          </button>
          <span className="account" title={user.username}>{user.name || user.username}</span>
          <button className="btn btn--icon btn--ghost" type="button" onClick={onLogout} aria-label="Đăng xuất">
            <Icon name="logout" size={16} />
          </button>
        </div>
      </header>
      <main id="main-content" className="lab-main" tabIndex={-1}>
        <AutoTest />
      </main>
    </div>
  );
}
