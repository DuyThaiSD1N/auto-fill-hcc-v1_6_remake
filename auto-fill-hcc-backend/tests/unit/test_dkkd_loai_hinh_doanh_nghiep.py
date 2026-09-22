"""[ĐKKD qua mạng] Nhận diện LOẠI HÌNH doanh nghiệp: công ty cổ phần vs TNHH hai thành viên trở lên.

Cổng dangkyquamang.dkkd.gov.vn dùng CHUNG domain và chung Registration.aspx/DW_DOCUMENTEdit.aspx cho
mọi loại hình, nên rule "detect" của hai thủ tục này trùng hệt nhau — không thể nhận diện bằng URL.
Thứ duy nhất phân biệt là dòng "Loại hình doanh nghiệp" in trên chính hồ sơ; extension quy nhãn đó về
MÃ loại hình (value radio $CtlEntType) rồi mới so với registry.

Khoá ba điều dễ vỡ:
  1. Cả hai thủ tục đều phải TỰ NHẬN DIỆN được (trước đây TNHH hai thành viên bị tắt detectDisabled
     nên hồ sơ TNHH luôn bị nhận thành công ty cổ phần — entry đứng trước trên cùng domain).
  2. Mỗi thủ tục phải khai enterpriseEntityValue, và hai mã phải KHÁC nhau.
  3. Mã khai tay phải khớp mã suy ra từ nhãn — nếu ai đó sửa nhãn cho "gọn" mà quên mã thì test đỏ.
"""

import re
import unicodedata

from app.procedures.registry import public_list

_KEY_CTCP = "thanh-lap-cong-ty-co-phan"
_KEY_TNHH2 = "thanh-lap-cong-ty-tnhh-hai-thanh-vien"


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def _entity_code(label: str) -> str:
    """Bản Python của enterpriseEntityCode() trong popup.js — giữ hai bên nói cùng một thứ tiếng."""
    text = _norm(label)
    if not text:
        return ""
    if "hop danh" in text:
        return "PARTNER"
    if "tu nhan" in text:
        return "PRI"
    if "trach nhiem huu han" in text or re.search(r"\btnhh\b", text):
        if re.search(r"\bmtv\b", text) or re.search(r"\b(mot|1) thanh vien\b", text):
            return "LLC1"
        if re.search(r"\b(hai|2) thanh vien\b", text):
            return "LLC2"
        return ""
    if "co phan" in text:
        return "SC"
    return ""


def _proc(key: str) -> dict:
    found = next((p for p in public_list() if p["key"] == key), None)
    assert found, f"Thiếu thủ tục {key} trong registry"
    return found


def test_hai_thu_tuc_deu_thuoc_cong_dkkd_qua_mang():
    for key in (_KEY_CTCP, _KEY_TNHH2):
        proc = _proc(key)
        assert proc.get("enterprisePortal") is True
        assert proc["detect"]["urlIncludes"] == ["dangkyquamang.dkkd.gov.vn"]


def test_tnhh_hai_thanh_vien_khong_con_bi_tat_nhan_dien():
    # Bật lại được là nhờ extension chốt loại hình theo dòng "Loại hình doanh nghiệp" của hồ sơ và
    # KHÔNG đoán theo domain nữa; tắt lại cờ này = hồ sơ TNHH lại bị kéo sang công ty cổ phần.
    assert not _proc(_KEY_TNHH2).get("detectDisabled")
    assert not _proc(_KEY_CTCP).get("detectDisabled")


def test_moi_thu_tuc_khai_ma_loai_hinh_rieng():
    ctcp = _proc(_KEY_CTCP).get("enterpriseEntityValue")
    tnhh2 = _proc(_KEY_TNHH2).get("enterpriseEntityValue")
    assert ctcp == "SC"
    assert tnhh2 == "LLC2"
    assert ctcp != tnhh2


def test_ma_khai_tay_khop_ma_suy_tu_nhan():
    for key in (_KEY_CTCP, _KEY_TNHH2):
        proc = _proc(key)
        assert _entity_code(proc["enterpriseEntityLabel"]) == proc["enterpriseEntityValue"], key


def test_nhan_bien_the_cua_cong_van_ra_dung_ma():
    # Cổng in nhãn mỗi chỗ một kiểu — tất cả phải quy về cùng một mã.
    assert _entity_code("Công ty cổ phần") == "SC"
    for label in (
        "Công ty trách nhiệm hữu hạn hai thành viên trở lên",
        "Công ty TNHH hai thành viên trở lên",
        "Công ty TNHH 2 thành viên trở lên",
    ):
        assert _entity_code(label) == "LLC2", label
    # Loại hình chưa có thủ tục: phải ra mã KHÁC để extension bỏ qua, không nhận bừa sang CTCP/TNHH2.
    assert _entity_code("Công ty trách nhiệm hữu hạn một thành viên") == "LLC1"
    assert _entity_code("Doanh nghiệp tư nhân") == "PRI"
    assert _entity_code("Công ty hợp danh") == "PARTNER"
    # Không rõ một hay hai thành viên thì KHÔNG đoán.
    assert _entity_code("Công ty trách nhiệm hữu hạn") == ""


def test_khong_thu_tuc_nao_khac_tranh_ma_loai_hinh():
    seen: dict[str, str] = {}
    for proc in public_list():
        code = proc.get("enterpriseEntityValue")
        if not code:
            continue
        assert code not in seen, f"{proc['key']} trùng mã loại hình với {seen[code]}"
        seen[code] = proc["key"]
