"""[BN] Cấp đổi GCN — nhãn ô thân đơn phải khớp BIỂU MẪU HIỆN TẠI trên cổng.

Cổng đã đổi Đơn Mẫu 18: nhãn cũ "a) Tên" / "c) Địa chỉ" / "2. Nội dung biến động" không còn, nhãn mới
dùng gạch đầu dòng và số La Mã. Ô đơn KHÔNG có class `eform-element-<Key>` ngữ nghĩa (chỉ
`eform-element-text`) nên NHÃN là đường khớp duy nhất — sai một ký tự là trượt cả ô.
"""

import re
import unicodedata
from pathlib import Path

from app.pipelines.cap_doi_gcn_bac_ninh.process import mapper
from app.pipelines.cap_doi_gcn_bac_ninh.process import schema as S

_SNAPSHOT = (
    Path(__file__).resolve().parents[2].parent
    / "thongtin" / "cấp đổi bắc ninh" / "html cấp đổi bắc ninh.html"
)

_HO_SO = [
    {"name": "Cccd_HoTen", "value": "NGUYỄN HỒNG BAN"},
    {"name": "Cccd_SoDinhDanh", "value": "027055006075"},
    {"name": "Cccd_NgayCap", "value": "18/12/2021"},
    {"name": "Cccd_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "Don_KinhGui", "value": "Chi nhánh Văn phòng Đăng ký đất đai liên phường Bắc Ninh"},
    {"name": "Don_DiaChi", "value": "TDP Hòa Long, P. Nam Sơn, Bắc Ninh"},
    {"name": "Don_DienThoai", "value": "0912716347"},
    {"name": "Don_NoiDungBienDong", "value": "Cấp đổi giấy chứng nhận quyền sử dụng đất"},
    {"name": "Don_GiayTo2", "value": "Công văn đính chính số tờ bản đồ"},
    {"name": "Don_ThanhVienHo", "value": "Trần Thị Thuyết"},
    {"name": "Don_TinhTrangTranhChap", "value": "không"},
]


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _snapshot():
    if not _SNAPSHOT.exists():
        return None, None
    html = _SNAPSHOT.read_text(encoding="utf-8", errors="replace")
    labels = []
    for m in re.finditer(r'<(input|textarea)\b[^>]*name="[^"]*element_(\d+)"[^>]*>', html):
        tag = m.group(0)
        if 'type="hidden"' in tag:
            continue
        title = (re.search(r'title="([^"]*)"', tag) or [None, ""])[1]
        labels.append((f"element_{m.group(2)}", title))
    names = set(re.findall(r'name="_org_bn_hoso_noptructuyen_(\w+)"', html))
    return labels, names


def _find_by_label(labels, want):
    """Bản rút gọn findElementByLabel của fill-bacninh.js: exact → startsWith → includes."""
    w = _fold(want)
    starts = inc = None
    starts_len = inc_len = 10**9
    for eid, label in labels:
        folded = _fold(label)
        if not folded:
            continue
        if folded == w:
            return eid
        if folded.startswith(w) and len(folded) < starts_len:
            starts, starts_len = eid, len(folded)
        if w in folded and len(folded) < inc_len:
            inc, inc_len = eid, len(folded)
    return starts or inc


def test_moi_field_mapper_phat_deu_khop_duoc_o_tren_trang():
    labels, names = _snapshot()
    if labels is None:
        return
    fields = mapper.enrich(_HO_SO)
    assert fields, "mapper phải phát được field"
    for f in fields:
        name = f["name"]
        assert name in names or _find_by_label(labels, name), f"không khớp ô nào: {name!r}"


def test_nhan_than_don_la_title_nguyen_van_tren_trang():
    labels, _ = _snapshot()
    if labels is None:
        return
    titles = {_fold(t) for _, t in labels if t}
    for const in (S.L_KINHGUI, S.L_TEN, S.L_GIAYTO, S.L_DIACHI, S.L_MST, S.L_DIENTHOAI,
                  S.L_EMAIL, S.L_NOIDUNG, S.L_GIAYTO2, S.L_GIAYTO3,
                  S.L_THANHVIEN, S.L_TRANHCHAP, S.L_RANHGIOI):
        assert _fold(const) in titles, f"nhãn không có trên trang: {const!r}"


def test_khong_con_nhan_cua_bieu_mau_cu():
    """Nhãn cũ 'a) Tên', 'c) Địa chỉ', '2. Nội dung biến động'… đã bị cổng bỏ."""
    for cu in ("a) Tên", "b) Giấy tờ nhân thân/pháp nhân", "c) Địa chỉ",
               "d) Điện thoại liên hệ", "2. Nội dung biến động", "Kính gửi"):
        assert cu not in S.UI_COMP_BY_NAME, f"vẫn còn nhãn cũ: {cu!r}"


def test_giay_to_muc_iv_khong_dinh_nham_muc_v():
    """'(2)' và '(3)' của mục IV phải khớp EXACT, không rơi vào '(2) Tình trạng tranh chấp…'."""
    labels, _ = _snapshot()
    if labels is None:
        return
    assert _find_by_label(labels, S.L_GIAYTO2) == "element_77397"
    assert _find_by_label(labels, S.L_GIAYTO3) == "element_77398"
    assert _find_by_label(labels, S.L_TRANHCHAP) == "element_77401"
    assert _find_by_label(labels, S.L_RANHGIOI) == "element_77402"


def test_khoi_nguoi_nhan_ket_qua_khop_theo_name():
    _, names = _snapshot()
    if names is None:
        return
    for const in (S.N_HOTEN, S.N_CCCD, S.N_SDT, S.N_DIACHI):
        assert const in names, const


def test_o_moi_duoc_phat_khi_don_co_ghi():
    by_name = {f["name"]: f["value"] for f in mapper.enrich(_HO_SO)}

    assert by_name[S.L_THANHVIEN] == "Trần Thị Thuyết"
    assert by_name[S.L_TRANHCHAP] == "không"
    # Đơn không ghi → không phát, không bịa.
    assert S.L_RANHGIOI not in by_name
    assert S.L_MST not in by_name
    assert S.L_EMAIL not in by_name


def test_giay_to_nhan_than_ghep_du_so_ngay_noi_cap():
    by_name = {f["name"]: f["value"] for f in mapper.enrich(_HO_SO)}
    assert by_name[S.L_GIAYTO] == (
        "CCCD số 027055006075, cấp 18/12/2021, Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    )
