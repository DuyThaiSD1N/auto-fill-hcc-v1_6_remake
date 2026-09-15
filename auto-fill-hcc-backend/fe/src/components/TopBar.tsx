import { useEffect, useState } from "react";

import type { User } from "../types";
import Logo from "./Logo";

export type View = "traces" | "dossiers" | "stats" | "reports" | "accounts";

interface Props {
  user: User;
  view: View;
  onNavigate: (v: View) => void;
  onLogout: () => void;
}

interface NavItem {
  key: View;
  label: string;
  description: string;
  icon: "journal" | "folder" | "chart" | "report" | "users";
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { key: "traces", label: "Nhật ký xử lý", description: "Tra cứu từng lượt", icon: "journal" },
  { key: "dossiers", label: "Hồ sơ", description: "Vòng đời từng hồ sơ", icon: "folder", adminOnly: true },
  { key: "stats", label: "Thống kê hồ sơ", description: "Theo dõi số liệu", icon: "chart" },
  { key: "reports", label: "Xuất báo cáo", description: "Kết xuất Excel", icon: "report", adminOnly: true },
  { key: "accounts", label: "Tài khoản", description: "Quản lý truy cập", icon: "users", adminOnly: true },
];

function Icon({ name, size = 19 }: { name: NavItem["icon"] | "menu" | "close" | "logout" | "collapse" | "expand"; size?: number }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (name === "journal") return <svg {...common}><path d="M5 4.5h12.5A1.5 1.5 0 0 1 19 6v13H6.5A2.5 2.5 0 0 1 4 16.5V5.5a1 1 0 0 1 1-1Z" /><path d="M4 16.5A2.5 2.5 0 0 1 6.5 14H19M8 8h7M8 11h5" /></svg>;
  if (name === "folder") return <svg {...common}><path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l2 2.5h7A1.5 1.5 0 0 1 19 10v7.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 3 17.5v-10Z" /><path d="M8 13h7" /></svg>;
  if (name === "chart") return <svg {...common}><path d="M4 19.5V10m6 9.5V4.5m6 15v-6m4 6H2" /></svg>;
  if (name === "report") return <svg {...common}><path d="M6 3.5h8l4 4V20a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" /><path d="M14 3.5v4h4M8 12h7M8 15.5h7" /></svg>;
  if (name === "users") return <svg {...common}><path d="M16 20v-1.5a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4V20M9.5 10.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM17 11a3 3 0 0 0 0-5.8M21 20v-1.5a4 4 0 0 0-3-3.85" /></svg>;
  if (name === "menu") return <svg {...common}><path d="M4 7h16M4 12h16M4 17h16" /></svg>;
  if (name === "close") return <svg {...common}><path d="m6 6 12 12M18 6 6 18" /></svg>;
  if (name === "collapse") return <svg {...common}><path d="m13.5 8-4 4 4 4M19 5v14" /></svg>;
  if (name === "expand") return <svg {...common}><path d="m10.5 8 4 4-4 4M5 5v14" /></svg>;
  return <svg {...common}><path d="M10 17l5-5-5-5M15 12H3M15 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" /></svg>;
}

export default function TopBar({ user, view, onNavigate, onLogout }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => window.localStorage.getItem("hcc_admin_sidebar_collapsed") === "1",
  );
  const isAdmin = user.role === "admin";
  const current = NAV_ITEMS.find((item) => item.key === view) ?? NAV_ITEMS[0];
  const initials = (user.name || user.username)
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "HC";

  useEffect(() => {
    setSidebarOpen(false);
  }, [view]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSidebarOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    document.body.classList.toggle("sidebar-open", sidebarOpen);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("sidebar-open");
    };
  }, [sidebarOpen]);

  useEffect(() => {
    document.body.classList.toggle("sidebar-collapsed", sidebarCollapsed);
    window.localStorage.setItem("hcc_admin_sidebar_collapsed", sidebarCollapsed ? "1" : "0");
    return () => document.body.classList.remove("sidebar-collapsed");
  }, [sidebarCollapsed]);

  function navigate(next: View) {
    setSidebarOpen(false);
    onNavigate(next);
  }

  return (
    <>
      <a className="skip-link" href="#main-content">Chuyển tới nội dung chính</a>
      <button
        type="button"
        className={`sidebar-scrim ${sidebarOpen ? "visible" : ""}`}
        aria-label="Đóng menu điều hướng"
        tabIndex={sidebarOpen ? 0 : -1}
        onClick={() => setSidebarOpen(false)}
      />

      <aside
        className={`app-sidebar ${sidebarOpen ? "open" : ""} ${sidebarCollapsed ? "collapsed" : ""}`}
        id="app-sidebar"
      >
        <div className="sidebar-brand">
          <Logo size={36} />
          <div className="sidebar-brand-copy">
            <strong>Trợ lý nhân dân</strong>
            <span>Quản trị hồ sơ</span>
          </div>
          <button
            type="button"
            className="sidebar-close"
            aria-label="Đóng menu"
            onClick={() => setSidebarOpen(false)}
          >
            <Icon name="close" />
          </button>
        </div>
        <button
          type="button"
          className="sidebar-collapse"
          aria-label={sidebarCollapsed ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"}
          title={sidebarCollapsed ? "Mở rộng" : "Thu gọn"}
          onClick={() => setSidebarCollapsed((value) => !value)}
        >
          <Icon name={sidebarCollapsed ? "expand" : "collapse"} size={17} />
        </button>

        <nav className="sidebar-nav" aria-label="Chức năng quản trị">
          <span className="sidebar-group-label">Vận hành</span>
          {NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin).map((item) => (
            <button
              type="button"
              key={item.key}
              className={`sidebar-nav-item ${view === item.key ? "active" : ""}`}
              aria-current={view === item.key ? "page" : undefined}
              title={sidebarCollapsed ? item.label : undefined}
              onClick={() => navigate(item.key)}
            >
              <span className="nav-icon"><Icon name={item.icon} /></span>
              <span className="nav-copy">
                <strong>{item.label}</strong>
                <small>{item.description}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-account">
          <div className="account-avatar" aria-hidden="true">{initials}</div>
          <div className="sidebar-account-copy">
            <strong title={user.name || user.username}>{user.name || user.username}</strong>
            <span title={user.username}>@{user.username}</span>
          </div>
          <button type="button" className="logout-button" onClick={onLogout} aria-label="Đăng xuất">
            <Icon name="logout" />
          </button>
        </div>
      </aside>

      <header className="topbar">
        <button
          type="button"
          className="menu-button"
          aria-label="Mở menu điều hướng"
          aria-controls="app-sidebar"
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen(true)}
        >
          <Icon name="menu" />
        </button>
        <div className="topbar-context">
          <span>Hệ thống quản trị</span>
          <strong>{current.label}</strong>
        </div>
      </header>
      <span id="main-content" className="main-anchor" tabIndex={-1} />
    </>
  );
}
