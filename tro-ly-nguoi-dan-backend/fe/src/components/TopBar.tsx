import type { User } from "../types";
import Logo from "./Logo";

export type View = "traces" | "stats" | "accounts" | "consents";

interface Props {
  user: User;
  view: View;
  onNavigate: (v: View) => void;
  onLogout: () => void;
}

export default function TopBar({ user, view, onNavigate, onLogout }: Props) {
  const isAdmin = user.role === "admin";
  return (
    <header className="topbar">
      <div className="topbar-left">
        <span className="brand">
          <Logo size={26} />
          <strong>Trợ lý người dân</strong>
        </span>
        <nav className="tabs">
          <button
            className={`tab ${view === "traces" ? "active" : ""}`}
            onClick={() => onNavigate("traces")}
          >
            Nhật ký
          </button>
          <button
            className={`tab ${view === "stats" ? "active" : ""}`}
            onClick={() => onNavigate("stats")}
          >
            Thống kê
          </button>
          {isAdmin && (
            <button
              className={`tab ${view === "consents" ? "active" : ""}`}
              onClick={() => onNavigate("consents")}
            >
              Chấp thuận
            </button>
          )}
          {isAdmin && (
            <button
              className={`tab ${view === "accounts" ? "active" : ""}`}
              onClick={() => onNavigate("accounts")}
            >
              Tài khoản
            </button>
          )}
        </nav>
      </div>
      <div className="topbar-right">
        <span className="muted">{user.name || user.username}</span>
        <button className="ghost" onClick={onLogout}>
          Đăng xuất
        </button>
      </div>
    </header>
  );
}
