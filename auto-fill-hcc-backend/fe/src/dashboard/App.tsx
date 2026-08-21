import { useEffect, useState } from "react";
import Login from "./Login";
import Dashboard from "./Dashboard";
import { AUTH_EXPIRED_EVENT, tokens, type WardUser } from "./api";

export default function App() {
  const [user, setUser] = useState<WardUser | null>(() => tokens.getUser());

  useEffect(() => {
    // Phiên hết hạn không cứu được (api.ts đã dọn token) → về màn đăng nhập.
    const onExpired = () => setUser(null);
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, []);

  function handleLogout() {
    tokens.clear();
    setUser(null);
  }

  if (!user) return <Login onLogin={setUser} />;
  return <Dashboard user={user} onLogout={handleLogout} />;
}
