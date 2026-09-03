import type { MonitorUser } from "../types";
import Brand from "./Brand";
import Icon from "./Icon";

export default function AppHeader({ user, onLogout }: { user: MonitorUser; onLogout: () => void }) {
  return (
    <header className="app-header">
      <div className="app-header__scanline" />
      <div className="app-header__inner">
        <Brand compact />
        <div className="app-header__account">
          <span className="account-chip">
            <span className="account-chip__icon"><Icon name="user" size={16} /></span>
            <span>
              <small>Phiên giám sát</small>
              <strong>{user.name || user.username}</strong>
            </span>
          </span>
          <button className="button button--ghost button--icon-label" type="button" onClick={onLogout}>
            <Icon name="logout" />
            <span>Đăng xuất</span>
          </button>
        </div>
      </div>
    </header>
  );
}
