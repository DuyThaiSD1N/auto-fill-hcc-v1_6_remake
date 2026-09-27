import { useCallback, useEffect, useState } from "react";
import { getFacets, getTrace, MONITOR_AUTH_EXPIRED_EVENT, monitorSession, validateMonitorSession } from "./api";
import Layout from "./components/Layout";
import { ErrorNotice, PageLoading } from "./components/Status";
import { FacetsContext } from "./hooks";
import DashboardPage from "./pages/DashboardPage";
import DossierDetailPage from "./pages/DossierDetailPage";
import DossiersPage from "./pages/DossiersPage";
import LoginPage from "./pages/LoginPage";
import RunDetailPage from "./pages/RunDetailPage";
import RunsPage from "./pages/RunsPage";
import { match, navigate, useLocation } from "./router";
import type { Facets, MonitorUser } from "./types";

export default function App() {
  const [auth, setAuth] = useState<"checking" | "signed-out" | "signed-in">("checking");
  const [user, setUser] = useState<MonitorUser | null>(monitorSession.user);
  const [facets, setFacets] = useState<Facets | null>(null);

  const signOut = useCallback(() => {
    monitorSession.clear();
    setUser(null);
    setAuth("signed-out");
  }, []);

  useEffect(() => {
    let active = true;
    validateMonitorSession().then((u) => {
      if (!active) return;
      setUser(u);
      setAuth(u ? "signed-in" : "signed-out");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    window.addEventListener(MONITOR_AUTH_EXPIRED_EVENT, signOut);
    return () => window.removeEventListener(MONITOR_AUTH_EXPIRED_EVENT, signOut);
  }, [signOut]);

  // Danh sách đơn vị/thủ tục dùng cho bộ lọc + dịch mã → tên ở mọi màn; tải một lần sau đăng nhập.
  useEffect(() => {
    if (auth !== "signed-in") return;
    getFacets().then(setFacets).catch(() => setFacets({ users: [], procedures: [] }));
  }, [auth]);

  if (auth === "checking") return <PageLoading label="Đang kiểm tra phiên…" />;
  if (auth === "signed-out" || !user) {
    return <LoginPage onSuccess={(u) => { setUser(u); setAuth("signed-in"); }} />;
  }
  return (
    <FacetsContext.Provider value={facets}>
      <Layout user={user} onLogout={signOut}><Routes /></Layout>
    </FacetsContext.Provider>
  );
}

function Routes() {
  const { path, query } = useLocation();
  let params: Record<string, string> | null;
  if (path === "/" || path === "") return <DashboardPage />;
  if (path === "/runs") return <RunsPage />;
  if ((params = match("/runs/:id", path))) return <RunDetailPage key={`${params.id}:${query.get("kind")}`} requestId={params.id} kind={query.get("kind")} />;
  if (path === "/dossiers") return <DossiersPage />;
  if ((params = match("/dossiers/:id", path))) return <DossierDetailPage key={params.id} id={params.id} />;
  if ((params = match("/traces/:id", path))) return <LegacyTrace id={params.id} />;
  return <ErrorNotice message="Không có trang này." />;
}

/** Link cũ /traces/<ObjectId> (web quản lý, bookmark) → chuyển sang /runs/<mã hỗ trợ>. */
function LegacyTrace({ id }: { id: string }) {
  const [error, setError] = useState("");
  useEffect(() => {
    getTrace(id)
      .then((t) => navigate(`/runs/${encodeURIComponent(t.request_id)}${t.kind ? `?kind=${t.kind}` : ""}`, { replace: true }))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [id]);
  return error ? <ErrorNotice message={error} /> : <PageLoading label="Đang mở lượt…" />;
}
