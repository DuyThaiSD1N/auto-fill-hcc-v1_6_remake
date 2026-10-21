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

`agencyWard`: Phường/Xã CỐ ĐỊNH phải chọn ở khối "Chọn cơ quan thực hiện", thay cho xã đang lưu
ở popup (vd "Đặc khu Cô Tô" cho các thủ tục Quảng Ninh chỉ nộp qua đặc khu). Chỉ dùng cùng thủ tục
đặc thù của một tỉnh (nhãn "Tỉnh - …"), vì tỉnh được ép theo tiền tố nhãn ở popup.js:agencyLocationFor.

`submitCardIncludes`: trang kết quả của Cổng QG ra NHIỀU thẻ cùng tên thủ tục, khác nhau ở "Cơ quan
thực hiện" / "Đối tượng". Mặc định trợ lý lấy thẻ ĐẦU; khai chuỗi này thì nó tìm đúng thẻ chứa chuỗi
đó (vd "Cơ quan thực hiện: Văn phòng Đăng ký đất đai") rồi mới bấm "Nộp trực tuyến" — bấm nhầm thẻ là
hồ sơ đi lạc cơ quan tiếp nhận ngay từ bước đầu. Không khớp thì cảnh báo và rơi về quy ước thẻ đầu.

`submitCardIncludesByWard`: như `submitCardIncludes` nhưng CHỈ áp cho Phường/Xã liệt kê, dạng
`{"Phường Liên Chiểu": "Khu vực 5 (Hòa Khánh, Liên Chiểu, Hải Vân)"}` (tên xã theo /locations/catalog).
Xã có trong bảng thì đè `submitCardIncludes`; xã khác giữ nguyên cách chọn thẻ cũ. Extension chốt
chuỗi theo xã đang chọn ở popup.js:submitCardIncludesFor.

`provincePortalFlow`: thủ tục đặc thù của tỉnh — bấm "Nộp trực tuyến" trên cổng quốc gia xong là
cổng ném sang CỔNG TỈNH, ở đó còn phải bấm "Nộp hồ sơ" đúng dòng, qua đăng nhập riêng của tỉnh rồi
chọn cơ quan tiếp nhận. `{host, rowIncludes, rowIndex, agency}` do content/portal-quangninh.js đọc:
`rowIncludes` chọn dòng theo chữ (một mã TTHC ra nhiều biến thể đồng bằng / miền núi, hải đảo),
`rowIndex` là phương án dự phòng theo vị trí, `agency` là chi nhánh phải chọn trong modal
"Thông tin chung". Đổi địa bàn tiếp nhận thì sửa `agency` ở đây, KHÔNG sửa engine.

Đọc một lần lúc process khởi động, giống app/locations/catalog.py.

`provinceOnly` (tính lúc trả API, không khai tay): thủ tục ĐẶC THÙ của tỉnh chỉ hiện cho tài khoản
đúng tỉnh đó. Tỉnh suy từ tiền tố nhãn ("[Tỉnh Bắc Ninh] …", "Quảng Ninh - …", "(Lào Cai - Cấp
phường/xã) …") và host `urlScope` của registry lõi (dichvucong.quangninh.gov.vn…). Cùng ý với
`provinceOnly` khai tay bên registry trợ lý (app/channels/handfree/procedure_registry.py).
"""
import json
import re
from pathlib import Path

from app.locations.catalog import PROVINCES, find_province

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


# "[Tỉnh Bắc Ninh] …", "[Tỉnh Lào Cai - Cấp Sở] …", "(Lào Cai - Cấp phường/xã) …", "Quảng Ninh - …".
# Phần bắt được chỉ tính là tỉnh khi khớp danh mục: "… do ngành Lao động - Thương binh …" không phải tỉnh.
_PROVINCE_PREFIX = re.compile(r"^\s*(?:[\[(]\s*([^\])]+?)\s*(?:[\])]|\s-\s)|(.+?)\s+-\s+)")
_PROVINCE_SLUGS = frozenset(province["slug"] for province in PROVINCES)


def _label_province_slug(label: str | None) -> str:
    match = _PROVINCE_PREFIX.match(str(label or ""))
    if not match:
        return ""
    province = find_province(match.group(1) or match.group(2) or "")
    return province["slug"] if province else ""


def _url_scope_province_slugs(detect: dict | None) -> set[str]:
    """Tỉnh theo host urlScope: dichvucong.<slug>.gov.vn, <slug>.gov.vn. Cổng bộ ngành không ra tỉnh."""
    slugs: set[str] = set()
    for scope in (detect or {}).get("urlScope") or []:
        host = re.sub(r"^[a-z]*:?//", "", str(scope).strip().lower()).split("/", 1)[0]
        slugs.update(part for part in host.split(".") if part in _PROVINCE_SLUGS)
    return slugs


def procedure_province_slugs(procedure: dict) -> list[str]:
    """Tỉnh mà thủ tục lõi chỉ dành riêng — rỗng là thủ tục dùng chung cả nước.

    Entry khai tay `provinceOnly` (như registry trợ lý) thì lấy đúng danh sách đó, không suy nữa.
    """
    if procedure.get("provinceOnly"):
        return sorted(procedure["provinceOnly"])
    slugs = _url_scope_province_slugs(procedure.get("detect"))
    label_slug = _label_province_slug(procedure.get("label"))
    if label_slug:
        slugs.add(label_slug)
    return sorted(slugs)


def link_province_slugs(link: dict, procedures_by_key: dict[str, dict]) -> list[str]:
    """Tỉnh của link kê khai: tiền tố nhãn link + tỉnh của thủ tục lõi cùng key.

    Nhãn link nhiều khi không ghi tỉnh dù thủ tục lõi đã khoá tỉnh (vd `dinh-chinh-sai-sot` Lai Châu),
    nên phải gộp cả hai. Chiều ngược lại thì KHÔNG: `tham-dinh-bcnckt` nhãn link ghi Ninh Bình (link
    ép chọn cơ quan Ninh Bình) nhưng pipeline lõi là cổng Bộ Xây dựng, tỉnh nào mở form cũng điền được.
    """
    if link.get("provinceOnly"):
        return sorted(link["provinceOnly"])
    slugs = set()
    label_slug = _label_province_slug(link.get("label"))
    if label_slug:
        slugs.add(label_slug)
    core = procedures_by_key.get(str(link.get("key") or ""))
    if core:
        slugs.update(procedure_province_slugs(core))
    return sorted(slugs)


def account_province_slug(user: dict | None) -> str:
    province = find_province(str((user or {}).get("tinh") or ""))
    return province["slug"] if province else ""


def visible_in_province(items: list[dict], province_slug: str) -> list[dict]:
    """Giữ thủ tục dùng chung + thủ tục riêng của `province_slug`, kèm `provinceOnly` cho extension.

    `province_slug` rỗng (tài khoản chưa gán tỉnh / tỉnh ngoài danh mục) → KHÔNG lọc, giống
    is_allowed_in_province bên trợ lý: thà hiện thừa còn hơn ẩn sạch thủ tục riêng của mọi tỉnh.
    """
    result: list[dict] = []
    for item in items:
        only = item.get("provinceOnly") or []
        if only and province_slug and province_slug not in only:
            continue
        result.append(item)
    return result


def with_province_only(items: list[dict], slugs_for) -> list[dict]:
    result: list[dict] = []
    for item in items:
        slugs = slugs_for(item)
        result.append({**item, "provinceOnly": slugs} if slugs else item)
    return result
