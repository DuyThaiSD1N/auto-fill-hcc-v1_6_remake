"""Nhật ký hồ sơ trên bảng thống kê: mỗi HỒ SƠ một dòng, không phải mỗi lượt trace.

Trước đây bảng đọc `traces`, nên một hồ sơ làm hai bước (điền + đính kèm) hiện thành HAI dòng
trùng tên thủ tục và con số đầu bảng là số lượt chứ không phải số hồ sơ. Đọc thẳng `dossiers`
còn cho thêm hai thứ tầng trace không có: mốc NỘP và phiếu đánh giá.
"""
from openpyxl import Workbook

from app.dashboard.export import _sheet_logs

_STARTED = "2026-09-12T02:23:00+00:00"
_SUBMITTED = "2026-09-12T03:40:00+00:00"


def _logs_sheet(rows):
    wb = Workbook()
    wb.remove(wb.active)
    _sheet_logs(wb, rows)
    return list(wb["Nhật ký hồ sơ"].iter_rows(values_only=True))


def test_cot_dung_thu_tu_va_bo_cot_buoc():
    header = _logs_sheet([])[0]
    # "Nguồn" xen vào trước "Đánh giá": nhật ký giờ gộp cả Auto Fill lẫn Handfree nên file
    # xuất ra phải nói rõ từng dòng đến từ đâu, y như bảng trên màn hình.
    assert header == (
        "Mã hồ sơ", "Thời gian tiếp nhận", "Thời gian nộp hồ sơ",
        "Đơn vị tiếp nhận", "Thủ tục", "Nguồn", "Đánh giá",
    )
    assert "Bước" not in header, "một dòng là một hồ sơ → không còn khái niệm bước"


def test_ba_trang_thai_danh_gia_phai_phan_biet_duoc():
    # Gộp "chưa hỏi" với "bỏ qua" là mất hẳn thông tin: cái đầu là hệ thống chưa hỏi, cái sau
    # là công dân đã được hỏi và chủ động không trả lời.
    rows = _logs_sheet([
        {"dossierId": "d-1", "receivedAt": _STARTED, "submittedAt": _SUBMITTED,
         "unitName": "Phường Việt Yên", "procedureLabel": "Đăng ký lại khai sinh",
         "rating": {"level": 5, "levelLabel": "Rất hài lòng", "reasons": [], "note": "",
                    "skipped": False, "at": None}},
        {"dossierId": "d-2", "receivedAt": _STARTED, "submittedAt": None,
         "unitName": "Phường Nam Sơn", "procedureLabel": "Chứng thực bản sao", "rating": None},
        {"dossierId": "d-3", "receivedAt": _STARTED, "submittedAt": None,
         "unitName": "X", "procedureLabel": "Y",
         "rating": {"level": None, "levelLabel": "", "reasons": [], "note": "",
                    "skipped": True, "at": None}},
    ])
    assert [r[6] for r in rows[1:]] == ["Rất hài lòng", "—", "Bỏ qua"]


def test_chua_nop_ghi_ro_chu_khong_de_trong():
    rows = _logs_sheet([
        {"dossierId": "d-1", "receivedAt": _STARTED, "submittedAt": _SUBMITTED,
         "unitName": "u", "procedureLabel": "p", "rating": None},
        {"dossierId": "d-2", "receivedAt": _STARTED, "submittedAt": None,
         "unitName": "u", "procedureLabel": "p", "rating": None},
    ])
    assert rows[1][2] == "10:40 12/09/2026", "giờ nộp quy về +07:00"
    assert rows[2][2] == "chưa nộp"


def test_ky_rong_van_gop_du_6_cot():
    rows = _logs_sheet([])
    assert rows[1][0] == "Chưa có hồ sơ nào trong kỳ."


def test_cot_nguon_noi_ro_tung_dong_den_tu_dau():
    """Nhật ký gộp hai trải nghiệm. Thiếu cột này thì hai hồ sơ cùng thủ tục, cùng đơn vị
    nhìn y hệt nhau dù một cái làm bằng extension, một cái bằng Trợ lý người dân."""
    rows = _logs_sheet([
        {"dossierId": "d-1", "receivedAt": _STARTED, "submittedAt": None,
         "unitName": "u", "procedureLabel": "p", "rating": None, "experience": "handfree"},
        {"dossierId": "d-2", "receivedAt": _STARTED, "submittedAt": None,
         "unitName": "u", "procedureLabel": "p", "rating": None, "experience": "autofill"},
        # Hồ sơ cũ chưa có trường experience → không được ghi bừa một nguồn nào.
        {"dossierId": "d-3", "receivedAt": _STARTED, "submittedAt": None,
         "unitName": "u", "procedureLabel": "p", "rating": None},
    ])
    assert [r[5] for r in rows[1:]] == ["Handfree", "No handfree", "—"]
