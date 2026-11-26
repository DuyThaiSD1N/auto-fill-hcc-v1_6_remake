"""Dịch dữ kiện đã trích sang ô eForm khai tử cho thủ tục đăng ký khai tử lưu động (1.000419).

Form lưu động cùng uuid ô với mẫu khai tử 2053 → dùng chung mapper của khai tử có yếu tố nước ngoài (nộp thay ghi đè mục
I theo hồ sơ, nơi cư trú / nơi chết trong nước - nước ngoài, giấy tờ tùy thân, giờ chết, giấy báo tử), chỉ khác:
- Không có ô ngày sinh người yêu cầu (NgaySinhC) và radio Có/Không "Đề nghị cấp bản sao" (CapBanSao) → không phát, kể
  cả lệnh xoá ô đổ theo tài khoản; còn ô số lượng SoLuong.
- Quốc tịch người chết: giấy không ghi thì "Việt Nam" (viền vàng) — khai tử lưu động gần như luôn cho công dân Việt Nam.
- Loại đăng ký: giấy ghi rõ thì theo giấy; không thì quá 15 ngày kể từ ngày chết mà hồ sơ KHÔNG có giấy báo tử / giấy tờ
  thay thế → "Đăng ký khai tử cho người chết đã lâu" (viền vàng, cán bộ xác nhận); có giấy báo tử → "Đăng ký quá hạn".
"""

from datetime import date

from app.pipelines.khai_tu_nuoc_ngoai.process import mapper as khai_tu_2053

from .schema import UI_COMP_BY_NAME

VIET_NAM = khai_tu_2053.VIET_NAM
TRONG_NUOC, KHAC = khai_tu_2053.TRONG_NUOC, khai_tu_2053.KHAC
DUNG_HAN, QUA_HAN, CHET_DA_LAU = khai_tu_2053.DUNG_HAN, khai_tu_2053.QUA_HAN, khai_tu_2053.CHET_DA_LAU

_DEATH_NOTICE_FIELDS = ("DeathNotice_Number", "DeathNotice_IssueDate", "DeathNotice_IssueAgency")


def _has(values: dict, name: str) -> bool:
    return str(values.get(name) or "").strip() != ""


def enrich(fields: list[dict], options: dict | None = None, today: date | None = None) -> list[dict]:
    """Dữ kiện compact → ô eForm khai tử lưu động, theo thứ tự UI_COMP_BY_NAME."""
    values = {f["name"]: f.get("value") for f in fields}
    # Form không có radio Có/Không: tờ khai tích "Có" mà không ghi số lượng thì mapper chung điền 1 bản (viền vàng).
    out = [f for f in khai_tu_2053.enrich(fields, options, today) if f["name"] in UI_COMP_BY_NAME]
    by_name = {f["name"]: f for f in out}

    if "nktQuocTich" not in by_name and (_has(values, "Deceased_FullName") or _has(values, "ToKhai_NguoiChet_HoTen")):
        out.append({"name": "nktQuocTich", "comp": UI_COMP_BY_NAME["nktQuocTich"], "value": VIET_NAM, "default": True})

    registration = by_name.get("loaiDangKy")
    no_death_notice = not any(_has(values, name) for name in _DEATH_NOTICE_FIELDS)
    if (registration and registration["value"] == QUA_HAN and not _has(values, "Registration_Type")
            and no_death_notice):
        registration.update(value=CHET_DA_LAU, default=True)

    order = {name: index for index, name in enumerate(UI_COMP_BY_NAME)}
    out.sort(key=lambda f: order[f["name"]])
    return out
