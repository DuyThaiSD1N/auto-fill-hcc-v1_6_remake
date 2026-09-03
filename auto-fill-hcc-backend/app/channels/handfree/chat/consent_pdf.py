"""Sinh PDF biên bản chấp thuận xử lý dữ liệu cá nhân (kênh sidebar).

Port từ auto-fill app/consent/pdf.py — pymupdf insert_htmlbox: render HTML Unicode
bằng font bundled của MuPDF → tiếng Việt đủ dấu, KHÔNG cần nhúng font ngoài. BE tự
sinh từ entry (không nhận file từ client) để bằng chứng không bị sửa.

Khác auto-fill (chủ thể = tài khoản VNeID trên cổng): kênh sidebar người dân nặc danh
→ biên bản định danh theo MÃ PHIÊN hội thoại + nơi làm thủ tục + tài khoản quầy đang
đăng nhập; chỉ sinh cho lượt ĐỒNG Ý (user chốt — lượt từ chối chỉ nằm trong Mongo).
"""
import html as _html

import fitz


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def build_consent_pdf(entry: dict) -> bytes:
    """entry = bản ghi consent_logs (app/chat/consent.py build_entry)."""
    statements = entry.get("statements") or []
    checks = entry.get("checks") or []
    items = "".join(
        f"<li>{_esc(s)}{'' if (i < len(checks) and checks[i]) else ' <i>(không tích)</i>'}</li>"
        for i, s in enumerate(statements)
    ) or "<li>(không có)</li>"
    docs = "".join(f"<li>{_esc(d)}</li>" for d in (entry.get("documents") or [])) or "<li>(không có)</li>"

    loc = entry.get("location") or {}
    place = ", ".join(x for x in (loc.get("ward"), loc.get("province")) if x) or "(chưa chọn)"
    method_label = "Nói/gõ đồng ý (verbal)" if entry.get("method") == "verbal" else "Bấm nút trên thẻ xác nhận"

    # Chủ thể dữ liệu = tài khoản VNeID đọc từ cổng (wording theo auto-fill): có CCCD thì hiện
    # CCCD (+ tên); chỉ tên thì ghi rõ cổng không cung cấp số; không có → gắn theo mã phiên.
    p_cccd, p_name = entry.get("principal_cccd"), entry.get("principal_name")
    if p_cccd:
        principal_val = f"<b>{_esc(p_cccd)}</b>" + (f" — {_esc(p_name)}" if p_name else "")
    elif p_name:
        principal_val = f"<b>{_esc(p_name)}</b> (cổng không cung cấp số định danh)"
    else:
        principal_val = "Không xác định được từ cổng (ghi nhận theo mã phiên)"

    body = f"""
    <div style="font-family:sans-serif;color:#1f2d3d">
      <div style="font-size:11px;color:#0d7d52;font-weight:bold;letter-spacing:.03em">TRỢ LÝ NGƯỜI DÂN TOÀN TRÌNH</div>
      <h2 style="font-size:16px;margin:6px 0 2px">BIÊN BẢN GHI NHẬN CHẤP THUẬN XỬ LÝ DỮ LIỆU CÁ NHÂN</h2>
      <div style="font-size:11px;color:#64748b;margin-bottom:12px">Lập tự động khi người dân xác nhận đồng ý trên Trợ lý (thẻ xin phép hiển thị trước khi nhận giấy tờ).</div>

      <table style="font-size:12.5px;line-height:1.5;width:100%">
        <tr><td style="color:#64748b;width:170px">Mã nhật ký</td><td><b>{_esc(entry.get('_id'))}</b></td></tr>
        <tr><td style="color:#64748b">Chủ thể dữ liệu (VNeID)</td><td>{principal_val}</td></tr>
        <tr><td style="color:#64748b">Mã phiên hội thoại</td><td>{_esc(entry.get('conversation_id'))}</td></tr>
        <tr><td style="color:#64748b">Kết quả</td><td><b>{"ĐỒNG Ý" if entry.get("accepted") else "KHÔNG ĐỒNG Ý"}</b></td></tr>
        <tr><td style="color:#64748b">Phương thức xác nhận</td><td>{method_label}</td></tr>
        <tr><td style="color:#64748b">Nội dung chấp thuận</td><td>phiên bản <b>{_esc(entry.get('version'))}</b></td></tr>
        <tr><td style="color:#64748b">Thủ tục</td><td>{_esc(entry.get('procedure_label') or '(chưa xác định)')}</td></tr>
        <tr><td style="color:#64748b">Nơi làm thủ tục</td><td>{_esc(place)}</td></tr>
        <tr><td style="color:#64748b">Tài khoản quầy</td><td>{_esc(entry.get('auth_username') or '(không đăng nhập)')}</td></tr>
        <tr><td style="color:#64748b">Thời điểm ghi nhận</td><td>{_esc(entry.get('at_display'))} (giờ Việt Nam, máy chủ)</td></tr>
      </table>

      <div style="font-size:12.5px;font-weight:bold;margin:14px 0 4px;color:#0d5c46">Nội dung chủ thể dữ liệu đã xác nhận</div>
      <ul style="font-size:12px;line-height:1.5;margin:0;padding-left:18px">{items}</ul>

      <div style="font-size:12.5px;font-weight:bold;margin:14px 0 4px;color:#0d5c46">Giấy tờ được phép đọc trong thủ tục này</div>
      <ul style="font-size:12px;line-height:1.5;margin:0;padding-left:18px">{docs}</ul>

      <div style="font-size:12.5px;font-weight:bold;margin:14px 0 4px;color:#0d5c46">Phạm vi, mục đích chia sẻ và xử lý dữ liệu</div>
      <div style="font-size:11.5px;line-height:1.5;color:#33445a">{_esc(entry.get('scope'))}.</div>

      <div style="font-size:11px;line-height:1.5;color:#45616d;margin-top:14px;border-top:1px solid #dbe3ec;padding-top:8px">
        Căn cứ Luật số 91/2025/QH15 ngày 26/6/2025 về Bảo vệ dữ liệu cá nhân (Điều 4 — quyền, nghĩa vụ
        của chủ thể dữ liệu cá nhân). Bản ghi này do hệ thống tự sinh và lưu để đối soát khi cần;
        người dân có quyền yêu cầu xem, chỉnh sửa, xóa dữ liệu theo quy định.
      </div>
    </div>
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_htmlbox(fitz.Rect(40, 40, 555, 802), body)
    return doc.tobytes()
