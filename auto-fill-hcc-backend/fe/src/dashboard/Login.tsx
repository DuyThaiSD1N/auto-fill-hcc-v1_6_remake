import { useState } from "react";
import { loginWard, type WardUser } from "./api";
import Seal from "./Seal";

export default function Login({ onLogin }: { onLogin: (u: WardUser) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await loginWard(username.trim(), password);
      onLogin(res.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-scene">
      <div className="login-panel">
        <Seal size={72} bottom="THỐNG KÊ HỒ SƠ" />
        <p className="login-eyebrow">Trợ lý người dân toàn trình</p>
        <h1 className="login-title">Bảng thống kê phường</h1>
        <p className="login-sub">Đăng nhập bằng tài khoản phường để xem số liệu hồ sơ của phường mình.</p>

        <form onSubmit={submit} className="login-form">
          <label className="field">
            <span>Tài khoản</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
              placeholder="tài khoản phường"
            />
          </label>
          <label className="field">
            <span>Mật khẩu</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
            />
          </label>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="login-btn" disabled={loading || !username || !password}>
            {loading ? "Đang đăng nhập…" : "Đăng nhập"}
          </button>
        </form>
      </div>
      <p className="login-foot">Chỉ hiển thị số liệu tổng hợp của phường bạn quản lý.</p>
    </div>
  );
}
