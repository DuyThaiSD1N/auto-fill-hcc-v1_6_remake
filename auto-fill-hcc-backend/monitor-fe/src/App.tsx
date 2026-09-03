import { useCallback, useEffect, useState } from "react";
import {
  MONITOR_AUTH_EXPIRED_EVENT,
  monitorSession,
  validateMonitorSession,
} from "./api";
import type { MonitorUser } from "./types";
import { PageLoading } from "./components/Status";
import LoginPage from "./pages/LoginPage";
import SearchPage from "./pages/SearchPage";
import TraceDetailPage from "./pages/TraceDetailPage";

const RETURN_PATH_KEY = "hcc_monitor_return_path";

interface Route {
  kind: "search" | "trace";
  traceId?: string;
}

function currentRoute(): Route {
  const match = window.location.pathname.match(/^\/traces\/([^/]+)\/?$/);
  if (match) return { kind: "trace", traceId: decodeURIComponent(match[1]) };
  return { kind: "search" };
}

function navigate(path: string, replace = false) {
  if (replace) window.history.replaceState({}, "", path);
  else window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export default function App() {
  const [route, setRoute] = useState<Route>(currentRoute);
  const [auth, setAuth] = useState<"checking" | "signed-out" | "signed-in">("checking");
  const [user, setUser] = useState<MonitorUser | null>(monitorSession.user);

  const signOut = useCallback(() => {
    monitorSession.clear();
    setUser(null);
    setAuth("signed-out");
    document.title = "Đăng nhập — Trợ lý hồ sơ Monitor";
  }, []);

  useEffect(() => {
    const onRoute = () => setRoute(currentRoute());
    window.addEventListener("popstate", onRoute);
    return () => window.removeEventListener("popstate", onRoute);
  }, []);

  useEffect(() => {
    let active = true;
    validateMonitorSession().then((sessionUser) => {
      if (!active) return;
      if (sessionUser) {
        setUser(sessionUser);
        setAuth("signed-in");
      } else {
        setUser(null);
        setAuth("signed-out");
      }
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    window.addEventListener(MONITOR_AUTH_EXPIRED_EVENT, signOut);
    return () => window.removeEventListener(MONITOR_AUTH_EXPIRED_EVENT, signOut);
  }, [signOut]);

  if (auth === "checking") return <PageLoading label="Đang kiểm tra phiên Monitor…" />;

  if (auth === "signed-out" || !user) {
    return (
      <LoginPage
        onSuccess={(nextUser) => {
          setUser(nextUser);
          setAuth("signed-in");
          document.title = "Trợ lý hồ sơ — Monitor";
        }}
      />
    );
  }

  if (route.kind === "trace" && route.traceId) {
    return (
      <TraceDetailPage
        onBack={() => navigate(sessionStorage.getItem(RETURN_PATH_KEY) || "/")}
        onLogout={signOut}
        traceId={route.traceId}
        user={user}
      />
    );
  }

  return (
    <SearchPage
      onLogout={signOut}
      onOpenTrace={(traceId, returnPath) => {
        sessionStorage.setItem(RETURN_PATH_KEY, returnPath);
        navigate(`/traces/${encodeURIComponent(traceId)}`);
      }}
      user={user}
    />
  );
}
