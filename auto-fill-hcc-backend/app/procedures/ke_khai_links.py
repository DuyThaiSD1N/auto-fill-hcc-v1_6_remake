"""Link trang kê khai của từng thủ tục trên Cổng DVC quốc gia.

Nguồn dữ liệu: `data/ke_khai_links.json` (trước đây nằm ở auto-fill-hcc-extension/data/
procedure-links.js — đã dồn về backend để extension không phải đóng gói dữ liệu riêng).
`key` trùng key thủ tục trong registry nên chọn link nào là chọn luôn đúng pipeline điền tự động.

`provinceOnlyAgency`: khối "Chọn cơ quan thực hiện" của thủ tục này CHỈ có ô Tỉnh/Thành phố,
không có ô Phường/Xã (thủ tục do cấp tỉnh tiếp nhận). Thiếu cờ thì popup bắt cán bộ chọn đủ
tỉnh + xã mới cho đi tiếp, còn agency-select.js chờ đủ 2 ô rồi bỏ cuộc vì cổng chỉ render 1 ô.

`selectSo` / `selectSoProvinces`: thủ tục nộp tại Sở — thay vì chọn Phường/Xã, trợ lý tick radio
"Sở" ở khối "Chọn cơ quan thực hiện" rồi bấm "Nộp trực tuyến" của thẻ ĐẦU TIÊN. `selectSo: true`
áp dụng cho mọi tỉnh; `selectSoProvinces: ["danang", ...]` CHỈ áp dụng ở các tỉnh liệt kê (slug lấy
từ /locations/catalog = `code_name` bỏ dấu gạch dưới) — cùng một mã TTHC nhưng tỉnh khác vẫn nộp ở
cấp xã, bật tràn cả nước là hồ sơ đi lạc cơ quan tiếp nhận. Extension chốt cờ theo tỉnh đang chọn
ở popup.js:selectSoFor.

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


def _code_detect_parts(code: str) -> list[str]:
    """Mảnh URL nhận diện theo mã TTHC quốc gia ở bước chọn của cổng bộ/ngành.

    Bấm "Nộp trực tuyến" trên DVCQG, cổng bộ mở trang chọn quy trình dạng
    ``dvc.moc.gov.vn/vi/nps/apply?MaTTHC=1.013229&MaDVC=1.013229.01&...``. Trang này chưa có
    apply-online/process id nên chỉ mã trên URL là định danh được thủ tục. Mã luôn đủ 6 chữ số
    sau dấu chấm nên ``matthc=<mã>`` không dính mã dài hơn; ``MaDVC`` là mã TTHC + đuôi ``.xx``
    nên chốt thêm dấu chấm. Popup so khớp trên URL đã lower-case.
    """
    return [f"matthc={code}", f"madvc={code}."]


def with_ke_khai_detect_urls(procedures: list[dict]) -> list[dict]:
    """Bổ sung URL trang chi tiết DVCQG và mã TTHC vào cấu hình detect trả cho extension.

    URL kê khai và mã TTHC đã có một nguồn chuẩn ở ``ke_khai_links.json``. Ghép lúc trả API giúp
    popup nhận diện được thủ tục ngay tại trang ``/thu-tuc-hanh-chinh/<uuid>`` và tại trang chọn
    quy trình mang ``MaTTHC=`` của cổng bộ, mà không phải chép lại vào từng entry của registry.
    Entry có ``urlScope`` vẫn bị giới hạn host như cũ, nên các thủ tục tỉnh dùng chung một mã
    không nhận nhầm sang nhau.
    """
    parts_by_key: dict[str, list[str]] = {}
    for item in KE_KHAI_LINKS:
        key = str(item.get("key") or "")
        if not key:
            continue
        parts: list[str] = []
        url = str(item.get("url") or "").strip()
        if url:
            parts.append(url)
        code = str(item.get("code") or "").strip()
        if code:
            parts.extend(_code_detect_parts(code))
        if parts:
            parts_by_key[key] = parts
    result: list[dict] = []
    for procedure in procedures:
        public_procedure = dict(procedure)
        parts = parts_by_key.get(str(procedure.get("key") or ""))
        if parts:
            detect = dict(procedure.get("detect") or {})
            url_includes = list(detect.get("urlIncludes") or [])
            lowered = {str(u).lower() for u in url_includes}
            for part in parts:
                if part.lower() not in lowered:
                    url_includes.append(part)
                    lowered.add(part.lower())
            detect["urlIncludes"] = url_includes
            public_procedure["detect"] = detect
        result.append(public_procedure)
    return result
