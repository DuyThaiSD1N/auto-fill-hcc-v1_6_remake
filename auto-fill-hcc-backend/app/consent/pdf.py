"""Sinh PDF bằng chứng chấp thuận xử lý dữ liệu (pymupdf insert_htmlbox).

Dùng insert_htmlbox: render HTML Unicode bằng font bundled của MuPDF → tiếng Việt đủ dấu,
KHÔNG cần nhúng font ngoài. BE tự sinh (không nhận PDF từ client) để bằng chứng không bị sửa.
"""
import html as _html

import fitz


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def build_consent_pdf(*, log_id: str, username: str | None, name: str | None,
                      procedure_label: str | None, version: str, statements: list[str],
                      optimize: bool = False, client_time: str | None, server_time: str,
                      principal_cccd: str | None = None, principal_name: str | None = None) -> bytes:
    items = "".join(f"<li>{_esc(s)}</li>" for s in (statements or [])) or "<li>(không có)</li>"
    optimize_line = (
        f'<tr><td style="color:#64748b">Lưu dữ liệu để tối ưu</td><td>{"Đồng ý" if optimize else "Không đồng ý"}</td></tr>'
    )
    # Chủ thể dữ liệu = tài khoản VNeID đọc từ cổng. Có CCCD thì hiện CCCD (+ tên); không có thì ghi rõ
    # "không xác định được từ cổng" để biên bản trung thực (consent khi đó gắn theo mã phiên).
    if principal_cccd:
        principal_val = _esc(principal_cccd) + (f" — {_esc(principal_name)}" if principal_name else "")
    elif principal_name:
        principal_val = _esc(principal_name) + " (cổng không cung cấp số định danh)"
    else:
        principal_val = "Không xác định được từ cổng (ghi nhận theo mã phiên)"
    principal_line = f'<tr><td style="color:#64748b">Chủ thể dữ liệu (VNeID)</td><td><b>{principal_val}</b></td></tr>'
    body = f"""
    <div style="font-family:sans-serif;color:#1f2d3d">
      <div style="font-size:11px;color:#2456c9;font-weight:bold;letter-spacing:.03em">TRỢ LÝ HỒ SƠ HÀNH CHÍNH CÔNG</div>
      <h2 style="font-size:16px;margin:6px 0 2px">BIÊN BẢN GHI NHẬN CHẤP THUẬN XỬ LÝ DỮ LIỆU CÁ NHÂN</h2>
      <div style="font-size:11px;color:#64748b;margin-bottom:12px">Lập tự động khi chủ thể dữ liệu bấm “Đồng ý và tự động điền” trên Trợ lý.</div>

      <table style="font-size:12.5px;line-height:1.5;width:100%">
        <tr><td style="color:#64748b;width:150px">Mã nhật ký</td><td><b>{_esc(log_id)}</b></td></tr>
        {principal_line}
        <tr><td style="color:#64748b">Nội dung chấp thuận</td><td><b>{_esc(version)}</b></td></tr>
        <tr><td style="color:#64748b">Đơn vị / Phường</td><td>{_esc(name or '')}</td></tr>
        <tr><td style="color:#64748b">Tài khoản</td><td>{_esc(username or '')}</td></tr>
        <tr><td style="color:#64748b">Thủ tục</td><td>{_esc(procedure_label or '(chưa xác định)')}</td></tr>
        <tr><td style="color:#64748b">Thời điểm (người dùng)</td><td>{_esc(client_time or '')}</td></tr>
        <tr><td style="color:#64748b">Thời điểm ghi nhận (máy chủ)</td><td>{_esc(server_time)}</td></tr>
        {optimize_line}
      </table>

      <div style="font-size:12.5px;font-weight:bold;margin:14px 0 4px;color:#193a72">Nội dung chủ thể dữ liệu đã chấp thuận</div>
      <ul style="font-size:12px;line-height:1.5;margin:0;padding-left:18px">{items}</ul>

      <div style="font-size:12.5px;font-weight:bold;margin:14px 0 4px;color:#193a72">Phạm vi và mục đích xử lý</div>
      <div style="font-size:11.5px;line-height:1.5;color:#33445a">
        Trợ lý chỉ đọc những thông tin cần thiết từ giấy tờ do người dùng chủ động cung cấp để thực hiện
        thủ tục hành chính. Mục đích: OCR, chuẩn hoá, hỗ trợ điền biểu mẫu và chuẩn bị tệp đính kèm trên
        Cổng Dịch vụ công. Người dùng có thể kiểm tra, chỉnh sửa dữ liệu trước khi nộp hồ sơ.
      </div>

      <div style="font-size:11px;line-height:1.5;color:#45616d;margin-top:14px;border-top:1px solid #dbe3ec;padding-top:8px">
        Căn cứ Luật số 91/2025/QH15 ngày 26/6/2025 về Bảo vệ dữ liệu cá nhân (Điều 4 — quyền, nghĩa vụ
        của chủ thể dữ liệu cá nhân). Bản ghi này được lưu để đối soát khi cần.
      </div>
    </div>
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_htmlbox(fitz.Rect(40, 40, 555, 802), body)
    return doc.tobytes()
