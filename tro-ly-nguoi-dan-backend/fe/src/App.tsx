import { useEffect, useState } from "react";
import Login from "./pages/Login";
import Traces from "./pages/Traces";
import Stats from "./pages/Stats";
import Accounts from "./pages/Accounts";
import Consents from "./pages/Consents";
import TraceDetailPage from "./components/TraceDetailPage";
import type { View } from "./components/TopBar";
import { AUTH_EXPIRED_EVENT, tokens } from "./api";
import { goToList, parseRoute, type TraceRoute } from "./nav";
import type { User } from "./types";

// Chỉ chấp nhận phiên đã lưu nếu là admin. Loại phiên cũ (lưu trước khi siết quyền) hoặc
// tài khoản đã bị hạ quyền — dọn token luôn để không lơ lửng.
function loadAdminSession(): User | null {
  const u = tokens.getUser() as User | null;
  if (u && u.role === "admin") return u;
  if (u) tokens.clear();
  return null;
}

export default function App() {
  const [user, setUser] = useState<User | null>(loadAdminSession);
  const [view, setView] = useState<View>("traces");
  const [route, setRoute] = useState<TraceRoute | null>(parseRoute);

  useEffect(() => {
    // Token hết hạn giữa chừng (api.ts đã dọn token + phát sự kiện) → đẩy về màn đăng nhập.
    const onExpired = () => setUser(null);
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    // Theo dõi URL hash → chuyển giữa danh sách và trang chi tiết trace (không dùng router).
    const onHash = () => setRoute(parseRoute());
    window.addEventListener("hashchange", onHash);
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
      window.removeEventListener("hashchange", onHash);
    };
  }, []);

  function handleLogout() {
    tokens.clear();
    setUser(null);
  }

  // Bấm tab điều hướng: rời trang chi tiết (xóa hash) rồi đổi view. Ở danh sách thì goToList no-op.
  function navigate(v: View) {
    goToList();
    setView(v);
  }

  if (!user) return <Login onLogin={setUser} />;

  // Trang chi tiết trace (URL #/trace/<id>) ưu tiên hơn view danh sách.
  if (route?.name === "trace") {
    return (
      <TraceDetailPage id={route.id} user={user} onLogout={handleLogout} onNavigate={navigate} />
    );
  }

  // Chỉ admin mới vào được tài khoản + chấp thuận; user thường bị đẩy về Nhật ký.
  const adminOnlyViews: View[] = ["accounts", "consents"];
  const effectiveView: View =
    adminOnlyViews.includes(view) && user.role !== "admin" ? "traces" : view;
  const shared = { user, onLogout: handleLogout, view: effectiveView, onNavigate: navigate };

  if (effectiveView === "accounts") return <Accounts {...shared} />;
  if (effectiveView === "consents") return <Consents {...shared} />;
  if (effectiveView === "stats") return <Stats {...shared} />;
  return <Traces {...shared} />;
}
