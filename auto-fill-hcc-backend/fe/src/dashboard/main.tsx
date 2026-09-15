import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { adoptAccessToken } from "./api";
import "./dashboard.css";

// Extension Auto Fill mở trang này kèm access token ở FRAGMENT (#hcc=<token>). Fragment không
// được gửi lên server nên không lọt vào log; vẫn xoá khỏi thanh địa chỉ NGAY (trước mọi await)
// để không đọng lại trong lịch sử trình duyệt.
async function consumeHandoffToken(): Promise<void> {
  const m = /^#hcc=(.+)$/.exec(window.location.hash);
  if (!m) return;
  const access = decodeURIComponent(m[1]);
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
  // Token hỏng/hết hạn → không dựng phiên; App tự rơi về màn đăng nhập như thường.
  await adoptAccessToken(access);
}

consumeHandoffToken().finally(() => {
  ReactDOM.createRoot(document.getElementById("dash-root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
});
