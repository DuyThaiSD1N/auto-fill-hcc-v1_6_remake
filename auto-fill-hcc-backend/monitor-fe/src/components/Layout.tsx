import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { navigate, onLinkClick, useLocation } from "../router";
import { GROUPS } from "../stages";
import type { MonitorUser } from "../types";
import Icon from "./Icon";

const NAV = [
  { to: "/", label: "Tổng quan", icon: "gauge" as const, match: (p: string) => p === "/" },
  { to: "/runs", label: "Lượt xử lý", icon: "list" as const, match: (p: string) => p.startsWith("/runs") || p.startsWith("/traces") },
  { to: "/dossiers", label: "Hồ sơ", icon: "folder" as const, match: (p: string) => p.startsWith("/dossiers") },
];

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
    } catch { /* trình duyệt chặn storage → chỉ áp dụng trong phiên */ }
  }, [theme]);
  const dark = theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  return { dark, toggle: () => setTheme(dark ? "light" : "dark") };
}

/** Tìm nhanh: mã hỗ trợ → mở thẳng lượt; còn lại → danh sách (lượt hoặc hồ sơ) đã lọc theo chữ. */
function QuickSearch() {
  const loc = useLocation();
  const [text, setText] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    const q = text.trim();
    if (!q) return;
    if (/^req_[a-z0-9]+$/i.test(q)) navigate(`/runs/${encodeURIComponent(q)}`);
    else if (loc.path.startsWith("/dossiers")) navigate(`/dossiers?q=${encodeURIComponent(q)}&range=all`);
    else navigate(`/runs?q=${encodeURIComponent(q)}&range=all`);
    setText("");
  }
  return (
    <form className="quick-search" role="search" onSubmit={submit}>
      <Icon name="search" size={16} />
      <input
        aria-label="Tìm nhanh"
        placeholder="Mã hỗ trợ req_…, mã hồ sơ, tên người làm thủ tục, đơn vị"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
    </form>
  );
}

export default function Layout({ user, onLogout, children }: { user: MonitorUser; onLogout: () => void; children: ReactNode }) {
  const loc = useLocation();
  const { dark, toggle } = useTheme();
  const [navOpen, setNavOpen] = useState(false);
  useEffect(() => setNavOpen(false), [loc.path]);

  return (
    <div className="shell" data-nav={navOpen ? "open" : "closed"}>
      <aside className="sidebar" aria-label="Điều hướng">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true"><span /><span /><span /><span /></span>
          <span className="brand__words"><strong>Monitor</strong><span>Trợ lý nhân dân</span></span>
        </div>
        <nav className="nav">
          {NAV.map((item) => (
            <a key={item.to} href={item.to} aria-current={item.match(loc.path) ? "page" : undefined}
               onClick={(e) => onLinkClick(e, item.to)}>
              <Icon name={item.icon} size={16} /> {item.label}
            </a>
          ))}
        </nav>
        <div className="legend" aria-label="Chú giải màu công đoạn">
          <h3>Công đoạn</h3>
          {GROUPS.map((g) => (
            <span key={g.key} className="legend__item"><i className={`swatch st-${g.key}`} />{g.label}</span>
          ))}
        </div>
      </aside>

      <header className="topbar">
        <button className="btn btn--icon btn--ghost topbar__menu" type="button" aria-label="Mở menu"
                onClick={() => setNavOpen((v) => !v)}>
          <Icon name="menu" />
        </button>
        <QuickSearch />
        <div className="topbar__right">
          <button className="btn btn--icon btn--ghost" type="button" onClick={toggle}
                  aria-label={dark ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}>
            <Icon name={dark ? "sun" : "moon"} size={16} />
          </button>
          <span className="account" title={user.username}>{user.name || user.username}</span>
          <button className="btn btn--icon btn--ghost" type="button" onClick={onLogout} aria-label="Đăng xuất">
            <Icon name="logout" size={16} />
          </button>
        </div>
      </header>

      <main id="main-content" className="main" tabIndex={-1}>{children}</main>
    </div>
  );
}
