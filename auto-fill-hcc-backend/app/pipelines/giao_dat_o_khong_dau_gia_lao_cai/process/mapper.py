"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115684 (Lào Cai, cổng iGate mới, cấp phường/xã).

Chọn người + phát ô dùng NGUYÊN mapper chung của form "FORM NGUOI NOP" (chuyen_doi_md_sd_dat_igate_lao_cai): theo tài
khoản / theo tờ khai (mở khoá Họ tên/CCCD/Ngày sinh bằng enableInput), chủ hồ sơ cá nhân điền thẳng từ giấy tờ, KHÔNG
tích "Người nộp hồ sơ là chủ hồ sơ" (tích là cổng calculateValue chép đè khối chủ hồ sơ), ô (*) thiếu → dom-expect.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (`options.submitterMode`, cài đặt "Lấy người nộp theo tờ khai" của extension):
  - theo tài khoản (mặc định): khối người nộp = người trong hồ sơ KHỚP tài khoản đăng nhập; không khớp ai → để trống
    nhân thân khối người nộp + cảnh báo, chỉ điền khối chủ hồ sơ.
  - theo tờ khai (`owner_as_submitter`): người nộp = NGƯỜI ĐỀ NGHỊ mục 1 Đơn. Khác tài khoản (hoặc không có mốc) →
    Họ tên/CCCD/Ngày sinh phát kèm enableInput (extension bỏ khoá rồi ghi đè) + cảnh báo; trùng tài khoản → để ô khoá
    như cổng đổ. Địa chỉ/SĐT/Email người nộp = của người đề nghị (Đơn mục 2–3).
  Đơn không đọc được người đề nghị mà hồ sơ có đúng MỘT thẻ căn cước → lấy thẻ đó làm người đề nghị (thủ tục chỉ có
  một cá nhân) + cảnh báo.

Ba điểm riêng theo mapping 1.115684:
1. Địa chỉ: Đơn Mẫu 01 mục 2 là NƠI THƯỜNG TRÚ HIỆN TẠI (thủ tục xét "thường trú tại xã"); thẻ căn cước thường còn in
   địa chỉ cũ trước khi chuyển đến → Đơn thắng địa chỉ trên thẻ của CHÍNH người đề nghị (cả khối người nộp khi người
   đề nghị tự nộp, cả khối chủ hồ sơ) + cảnh báo khi hai nơi khác nhau.
2. Nơi cấp "Cục Cảnh sát đăng ký, quản lý cư trú và dữ liệu quốc gia về dân cư – Bộ Công an" (cơ quan cấp thẻ Căn cước
   từ 01/7/2024) không có trong 2 option của cổng → "Bộ Công An". Bộ chuẩn hoá chung đọc cụm "cục cảnh sát" thành Cục
   CS QLHC về TTXH nên phải đổi trước khi gọi mapper chung.
3. "Ghi chú" (data[tenHoSo]) = tóm tắt Đơn: diện tích, mục đích, thửa, tờ bản đồ, vị trí.
"""

import re

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process import mapper as _goc
from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.process.schema import UI_COMP_BY_NAME

_BO_CONG_AN = "Bộ Công an"


def _noi_cap_c06(value):
    """Tên Cục C06 (đăng ký, quản lý cư trú và dữ liệu quốc gia về dân cư) → "Bộ Công an"; còn lại giữ nguyên."""
    folded = _goc._fold(value)
    return _BO_CONG_AN if "cu tru" in folded and "dan cu" in folded else value


def _person_noi_cap(person: dict) -> dict:
    return {**person, "NoiCap": _noi_cap_c06(person["NoiCap"])} if person.get("NoiCap") else person


def _cung_noi(left: dict | None, right: dict | None) -> bool:
    return bool(left and right) and all(_goc._fold(left.get(k)) == _goc._fold(right.get(k)) for k in ("tinh", "xa"))


def _o_dia_chi(area: dict) -> str:
    return ", ".join(p for p in (_goc._plain(area.get("diaChi")), _goc._plain(area.get("xa")),
                                 _goc._plain(area.get("tinh"))) if p)


def _chuan_hoa(fields: list[dict]) -> tuple[list[dict], list[str]]:
    """Đổi dữ kiện trước khi vào mapper chung: nơi cấp C06, bỏ địa chỉ trên thẻ của người đề nghị khi Đơn có nơi
    thường trú hiện tại (mapper chung xếp thẻ TRƯỚC Đơn)."""
    values = _goc._by_name(fields)
    warnings: list[str] = []
    don_area = _igate._area(values.get("ChuHoSo_DiaChiDon"))
    cards = _goc._people(values, "DanhSachCccd")
    out: list[dict] = []
    if not (values.get("ChuHoSo_HoTen") or values.get("ChuHoSo_SoDinhDanh")):
        # Đơn không đọc được người đề nghị: thủ tục chỉ có MỘT cá nhân → một thẻ duy nhất là người đề nghị (cả hai chế
        # độ người nộp cần mốc này; thiếu thì chế độ theo tờ khai bỏ trống khối người nộp).
        so_the = {_goc._digits(c.get("SoDinhDanh")) or _goc._fold(c.get("HoTen")) for c in cards} - {""}
        if len(so_the) == 1 and _goc._plain(cards[0].get("HoTen")):
            out += [{"name": "ChuHoSo_HoTen", "value": cards[0]["HoTen"]},
                    {"name": "ChuHoSo_SoDinhDanh", "value": cards[0].get("SoDinhDanh")}]
            values.update(ChuHoSo_HoTen=cards[0]["HoTen"], ChuHoSo_SoDinhDanh=cards[0].get("SoDinhDanh"))
            warnings.append(
                f"Không đọc được người đề nghị ở mục 1 của Đơn — trợ lý lấy theo thẻ căn cước duy nhất trong hồ sơ "
                f"({_goc._plain(cards[0]['HoTen'])}); cán bộ kiểm tra lại."
            )
    owner_card = _goc._find_person(cards, values.get("ChuHoSo_SoDinhDanh"), values.get("ChuHoSo_HoTen"))

    for field in fields:
        name, value = field.get("name"), field.get("value")
        if name == "ChuHoSo_NoiCap" and value:
            field = {**field, "value": _noi_cap_c06(value)}
        elif name in ("DanhSachCccd", "NguoiTrongGiayTo") and isinstance(value, list):
            items = []
            for person in value:
                if not isinstance(person, dict):
                    items.append(person)
                    continue
                fixed = _person_noi_cap(person)
                if name == "DanhSachCccd" and don_area and person is owner_card and fixed.get("NoiCuTru"):
                    card_area = _igate._area(fixed.get("NoiCuTru"))
                    if card_area and not _cung_noi(card_area, don_area):
                        warnings.append(
                            f"Địa chỉ in trên thẻ căn cước ({_o_dia_chi(card_area)}) khác nơi thường trú hiện tại ghi ở "
                            f"mục 2 của Đơn ({_o_dia_chi(don_area)}) — trợ lý điền theo Đơn; cán bộ đối chiếu xác "
                            "nhận cư trú nếu cần."
                        )
                    fixed = {k: v for k, v in fixed.items() if k != "NoiCuTru"}
                items.append(fixed)
            field = {**field, "value": items}
        out.append(field)
    return out, warnings


def _so(value) -> str | None:
    text = _goc._plain(value)
    if not text:
        return None
    text = re.sub(r"(?i)\s*(m2|m²|mét vuông)\s*$", "", text).strip()
    return text or None


def _ghi_chu(values: dict) -> str | None:
    dien_tich = _so(values.get("ThuaDat_DienTich"))
    so_thua = _goc._plain(values.get("ThuaDat_SoThua"))
    so_to = _goc._plain(values.get("ThuaDat_SoTo"))
    vi_tri = _goc._plain(values.get("ThuaDat_ViTri"))
    if not vi_tri:
        area = values.get("ThuaDat_DiaChi")
        if isinstance(area, dict):
            vi_tri = ", ".join(p for p in (_goc._plain(area.get(k)) for k in ("chiTietDuoiXa", "diaChi", "xa", "tinh"))
                               if p) or None
    if not (dien_tich or so_thua or vi_tri):
        return None
    muc_dich = _goc._plain(values.get("Don_MucDich")) or "đất ở"
    if muc_dich[:1].isupper() and _goc._fold(muc_dich).startswith("dat "):
        muc_dich = muc_dich[:1].lower() + muc_dich[1:]
    parts = ["Đề nghị giao" + (f" {dien_tich} m²" if dien_tich else "") + f" {muc_dich}"]
    if so_thua:
        parts.append(f"thửa đất số {so_thua}")
    if so_to:
        parts.append(f"tờ bản đồ địa chính số {so_to}")
    if vi_tri:
        parts.append(vi_tri)
    return ", ".join(parts)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    fields, warnings = _chuan_hoa(fields)
    out, chung = _igate.enrich_with_warnings(fields, options)
    ghi_chu = _ghi_chu(_goc._by_name(fields))
    if ghi_chu:
        out.append({"name": "data[tenHoSo]", "comp": UI_COMP_BY_NAME["data[tenHoSo]"], "value": ghi_chu})
    return out, [*warnings, *chung]
