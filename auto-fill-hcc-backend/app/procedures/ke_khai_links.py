"""Link trang kê khai của từng thủ tục trên Cổng DVC quốc gia.

Nguồn dữ liệu: `data/ke_khai_links.json` (trước đây nằm ở auto-fill-hcc-extension/data/
procedure-links.js — đã dồn về backend để extension không phải đóng gói dữ liệu riêng).
`key` trùng key thủ tục trong registry nên chọn link nào là chọn luôn đúng pipeline điền tự động.

`provinceOnlyAgency`: khối "Chọn cơ quan thực hiện" của thủ tục này CHỈ có ô Tỉnh/Thành phố,
không có ô Phường/Xã (thủ tục do cấp tỉnh tiếp nhận). Thiếu cờ thì popup bắt cán bộ chọn đủ
tỉnh + xã mới cho đi tiếp, còn agency-select.js chờ đủ 2 ô rồi bỏ cuộc vì cổng chỉ render 1 ô.

`submitCardIncludes`: trang kết quả của Cổng QG ra NHIỀU thẻ cùng tên thủ tục, khác nhau ở "Cơ quan
thực hiện" / "Đối tượng". Mặc định trợ lý lấy thẻ ĐẦU; khai chuỗi này thì nó tìm đúng thẻ chứa chuỗi
đó (vd "Cơ quan thực hiện: Văn phòng Đăng ký đất đai") rồi mới bấm "Nộp trực tuyến" — bấm nhầm thẻ là
hồ sơ đi lạc cơ quan tiếp nhận ngay từ bước đầu. Không khớp thì cảnh báo và rơi về quy ước thẻ đầu.

`provincePortalFlow`: thủ tục đặc thù của tỉnh — bấm "Nộp trực tuyến" trên cổng quốc gia xong là
cổng ném sang CỔNG TỈNH, ở đó còn phải bấm "Nộp hồ sơ" đúng dòng, qua đăng nhập riêng của tỉnh rồi
chọn cơ quan tiếp nhận. `{host, rowIncludes, rowIndex, agency}` do content/portal-quangninh.js đọc:
`rowIncludes` chọn dòng theo chữ (một mã TTHC ra nhiều biến thể đồng bằng / miền núi, hải đảo),
`rowIndex` là phương án dự phòng theo vị trí, `agency` là chi nhánh phải chọn trong modal
"Thông tin chung". Đổi địa bàn tiếp nhận thì sửa `agency` ở đây, KHÔNG sửa engine.

Đọc một lần lúc process khởi động, giống app/locations/catalog.py.
"""
import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "data" / "ke_khai_links.json"


def _load() -> list[dict]:
    raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    return list(raw["links"])


KE_KHAI_LINKS: list[dict] = _load()


def with_ke_khai_detect_urls(procedures: list[dict]) -> list[dict]:
    """Bổ sung URL trang chi tiết DVCQG vào cấu hình detect trả cho extension.

    URL kê khai đã có một nguồn chuẩn ở ``ke_khai_links.json``. Ghép lúc trả API giúp
    popup nhận diện được thủ tục ngay tại trang ``/thu-tuc-hanh-chinh/<uuid>`` mà
    không phải chép lại UUID vào từng entry của registry.
    """
    url_by_key = {
        str(item.get("key") or ""): str(item.get("url") or "").strip()
        for item in KE_KHAI_LINKS
        if item.get("key") and item.get("url")
    }
    result: list[dict] = []
    for procedure in procedures:
        public_procedure = dict(procedure)
        entry_url = url_by_key.get(str(procedure.get("key") or ""))
        if entry_url:
            detect = dict(procedure.get("detect") or {})
            url_includes = list(detect.get("urlIncludes") or [])
            if entry_url not in url_includes:
                url_includes.append(entry_url)
            detect["urlIncludes"] = url_includes
            public_procedure["detect"] = detect
        result.append(public_procedure)
    return result
