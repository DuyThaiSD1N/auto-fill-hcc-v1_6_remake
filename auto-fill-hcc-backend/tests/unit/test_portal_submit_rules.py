"""Luật nhận diện nút "Gửi hồ sơ" — đối chiếu với HTML THẬT của màn cuối từng cổng.

Vì sao phải có test này: sai kiểu THIẾU (cổng đổi nhãn → ngừng ghi) chỉ làm hụt số và vá được
bằng một dòng. Sai kiểu THỪA (bắt nhầm nút "Tiếp tục" của bước giữa) thì thổi phồng báo cáo mà
KHÔNG AI phát hiện ra — nên mọi cổng đều phải có ít nhất một ca ÂM chứng minh nút bước giữa
không lọt lưới.

Các chuỗi dưới đây cắt nguyên văn từ snapshot trong 'thongtin/man ket thuc/'. Hàm _matches là
bản Python của đoạn khớp trong content.js (xem auto-fill-hcc-extension/content.js) — đổi bên
nào cũng phải đổi bên kia.
"""
import pathlib
import re
import unicodedata

import pytest

from app.procedures.portal_submit import PORTAL_SUBMIT


def _fold(text: str) -> str:
    """Bản Python của foldSubmitLabel trong content.js."""
    text = text.replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def _matches(host: str, url_path: str, *, element_id: str = "", label: str = "", tag: str = "") -> bool:
    """Khớp = URL đúng VÀ (id trùng HOẶC nhãn trùng HOẶC buttonSelector trùng)."""
    rule = PORTAL_SUBMIT.get(host)
    if not rule:
        return False
    if rule.get("urlPattern") and not re.search(rule["urlPattern"], url_path):
        return False
    if element_id and element_id in (rule.get("buttonIds") or []):
        return True
    if label and _fold(label) in (rule.get("buttonText") or []):
        return True
    selector = rule.get("buttonSelector")
    if selector:
        # Hai dạng đang dùng: button[thuộc-tính="giá-trị"] và button.ten-class.
        attr_form = re.fullmatch(r'button\[([\w-]+)="([^"]+)"\]', selector)
        if attr_form:
            attr, value = attr_form.groups()
            return f'{attr}="{value}"' in tag
        class_form = re.fullmatch(r"button\.([\w-]+)", selector)
        if class_form:
            # So theo TOKEN class, đúng như CSS: `style_btn` không được dính `style_btn_close`.
            found = re.search(r'class="([^"]*)"', tag)
            return bool(found) and class_form.group(1) in found.group(1).split()
        raise AssertionError(f"selector dạng lạ, cập nhật _matches: {selector}")
    return False


# ── Nền Form.io/iGate: sáu cổng, mỏ neo duy nhất là form="captchaForm" ────────────────────
_FORMIO_HOSTS = [
    "dichvucong.danang.gov.vn",
    "dvc.moc.gov.vn",
    "dichvucong.ninhbinh.gov.vn",
    "dichvucong.lamdong.gov.vn",
    "dichvucongnnmt.mae.gov.vn",
    "dichvucongbyt.moh.gov.vn",
    "dichvucong.quangngai.gov.vn",
    "dichvucongbnv.moha.gov.vn",
    "dvc.moet.gov.vn",
    "dichvucong-tthc.moit.gov.vn",
]
_FORMIO_PATH = "/vi/padsvc/apply-online/6861598cacfde3146c41cc08"
# Nguyên văn từ snapshot Ninh Bình / Lâm Đồng (nhãn "Thanh toán") và MAE / Bộ Y tế ("Tiếp tục").
_FORMIO_SUBMIT = (
    '<button _ngcontent-sqo-c375="" mat-flat-button="" form="captchaForm" '
    'class="mat-flat-button mat-button-base mat-focus-indicator btn_next_new ng-star-inserted">'
)
# Nút "Tiếp tục" của các BƯỚC TRƯỚC: cùng class btn_next nhưng KHÔNG có form="captchaForm".
_FORMIO_NEXT_STEP = (
    '<button _ngcontent-nrx-c376="" mat-flat-button="" '
    'class="mat-flat-button mat-button-base mat-focus-indicator btn_next ng-star-inserted">'
)


@pytest.mark.parametrize("host", _FORMIO_HOSTS)
@pytest.mark.parametrize("label", ["Thanh toán", "Tiếp tục", "Nộp hồ sơ"])
def test_formio_bat_dung_nut_cuoi_du_nhan_nao(host, label):
    """Nhãn đổi theo thủ tục (có phí/miễn phí) nên KHÔNG được khớp theo chữ."""
    assert _matches(host, _FORMIO_PATH, label=label, tag=_FORMIO_SUBMIT)


@pytest.mark.parametrize("host", _FORMIO_HOSTS)
def test_formio_bo_qua_nut_tiep_tuc_cua_buoc_giua(host):
    """Snapshot MAE/Bộ Y tế có 4 nút .btn_next, chỉ 1 nút mang form="captchaForm"."""
    assert not _matches(host, _FORMIO_PATH, label="Tiếp tục", tag=_FORMIO_NEXT_STEP)


@pytest.mark.parametrize("host", _FORMIO_HOSTS)
def test_formio_chi_tinh_tren_trang_nop_ho_so(host):
    assert not _matches(host, "/vi/padsvc/home", label="Nộp hồ sơ", tag=_FORMIO_SUBMIT)


# ── Nền eForm /nop-ho-so/<số>: cổng tư pháp + Quảng Ninh ──────────────────────────────────
@pytest.mark.parametrize("host", ["dichvucongnganhtuphap.moj.gov.vn", "dichvucong.quangninh.gov.vn"])
def test_nop_ho_so_bat_dung_nut_gui_ho_so(host):
    assert _matches(host, "/nop-ho-so/145156", element_id="kt_gui-ho-so", label="Gửi hồ sơ")


@pytest.mark.parametrize("host", ["dichvucongnganhtuphap.moj.gov.vn", "dichvucong.quangninh.gov.vn"])
def test_nop_ho_so_bo_qua_nut_buoc_truoc(host):
    """id sinh từ nhãn (kt_ + slug) nên bước 1/2 có id khác — và data-e2e="btn-next" thì
    DÙNG CHUNG mọi bước, kể cả chính nút "Gửi hồ sơ", nên tuyệt đối không khớp theo nó."""
    assert not _matches(host, "/nop-ho-so/145156", element_id="kt_buoc-tiep-theo-cho-ban-than",
                        label="Bước tiếp theo")
    assert not _matches(host, "/nop-ho-so/145156", element_id="xem-truoc-to-khai", label="Xem trước")


@pytest.mark.parametrize("host", ["dichvucongnganhtuphap.moj.gov.vn", "dichvucong.quangninh.gov.vn"])
def test_nop_ho_so_khong_tinh_ngoai_trang_ho_so(host):
    assert not _matches(host, "/tra-cuu-tinh-trang-ho-so", element_id="kt_gui-ho-so", label="Gửi hồ sơ")
    assert not _matches(host, "/nop-ho-so", element_id="kt_gui-ho-so", label="Gửi hồ sơ")


# ── Lai Châu: nền riêng, id và nhãn TRÙNG với bước giữa ───────────────────────────────────
_LC_HOST = "dichvucong.laichau.gov.vn"
_LC_LAST = "/dich-vu-cong/tiep-nhan-online/nhap-le-phi-ho-so"
_LC_MID = "/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so"


def test_lai_chau_bat_dung_buoc_le_phi():
    assert _matches(_LC_HOST, _LC_LAST, element_id="btn-next", label="Đồng ý và tiếp tục")


def test_lai_chau_khong_bat_nham_buoc_nhap_thong_tin():
    """ĐÂY là ca nguy hiểm nhất của cổng này: bước 2 có Y HỆT id="btn-next" và nhãn
    "Đồng ý và tiếp tục". Bỏ urlPattern là mỗi hồ sơ bị đếm thành hai lần nộp."""
    assert not _matches(_LC_HOST, _LC_MID, element_id="btn-next", label="Đồng ý và tiếp tục")


def test_lai_chau_query_sid_khong_lam_truot_luat():
    """URL thật kèm ?sid=88542-... — content.js khớp trên pathname + hash, KHÔNG có query."""
    assert _matches(_LC_HOST, _LC_LAST, element_id="btn-next")


# ── Bất biến chung ───────────────────────────────────────────────────────────────────────
def test_moi_cong_deu_phai_khoa_url():
    """Không khóa URL thì nút cùng tên ở trang chủ/tra cứu cũng bị tính là đã nộp."""
    for host, rule in PORTAL_SUBMIT.items():
        assert rule.get("urlPattern"), f"{host} thiếu urlPattern"


def test_khong_cong_nao_khop_theo_data_e2e():
    """data-e2e="btn-next" có ở MỌI bước của nền eForm — khớp theo nó là đếm nhầm hàng loạt."""
    assert "btn-next" not in str(
        [rule.get("buttonSelector") for rule in PORTAL_SUBMIT.values()]
    )


# ── Đối chiếu snapshot GỐC (chỉ chạy khi có thư mục mẫu bên cạnh repo) ────────────────────
# Fixture phía trên là chuỗi chép tay — chép sai thì test vẫn xanh mà thực tế vẫn hỏng.
# Phần này mở đúng file HTML đã lưu để kiểm lại. Thư mục mẫu nằm NGOÀI repo (không đóng gói
# vào Docker) nên vắng thì bỏ qua, không phải lỗi.
_SNAPSHOT_DIR = pathlib.Path(__file__).resolve().parents[3] / "thongtin" / "man ket thuc"

_SNAPSHOTS = {
    "dichvucong.ninhbinh.gov.vn": ("kt ninh bình/kt ninh bình.html", "formio"),
    "dichvucong.quangngai.gov.vn": ("kt quảng ngãi/kt quảng ngãi.html", "formio"),
    "dichvucongbnv.moha.gov.vn": ("kt bnv/kt bộ nội vụ.html", "formio"),
    "dvc.moet.gov.vn": ("kt bgd/kt bgddt.html", "formio"),
    "dichvucong-tthc.moit.gov.vn": ("kt bộ công thương/kt bộ công thương.html", "formio"),
    "dichvucong.bvhttdl.gov.vn": ("kt vh tt dl/kt bộ vh tt dl .html", "text:Lưu và nộp hồ sơ"),
    "dichvucong.lamdong.gov.vn": ("kt lâm đồng/kt lâm đồng.html", "formio"),
    "dichvucongnnmt.mae.gov.vn": ("kt nnmt/kt nnmt.html", "formio"),
    "dichvucongbyt.moh.gov.vn": ("kt byt/kt byt.html", "formio"),
    "dichvucong.quangninh.gov.vn": ("kt quảng ninh/kt quảng ninh.html", "id:kt_gui-ho-so"),
    "dichvucong.laichau.gov.vn": ("kt lai châu/kt lai châu.html", "id:btn-next"),
}


@pytest.mark.parametrize(("host", "rel", "anchor"), [(h, r, a) for h, (r, a) in _SNAPSHOTS.items()])
def test_mo_neo_ton_tai_dung_mot_lan_trong_snapshot(host, rel, anchor):
    path = _SNAPSHOT_DIR / rel
    if not path.exists():
        pytest.skip(f"không có thư mục mẫu: {path}")
    html = path.read_text(encoding="utf-8", errors="ignore")
    if anchor == "formio":
        # ĐÚNG MỘT nút mang form="captchaForm" — đó là toàn bộ lý do luật dùng thuộc tính này.
        buttons = re.findall(r'<button[^>]*form="captchaForm"[^>]*>', html)
        assert len(buttons) == 1, f"{host}: {len(buttons)} nút captchaForm (kỳ vọng 1)"
    elif anchor.startswith("text:"):
        assert anchor.split(":", 1)[1] in html, f"{host}: không thấy nhãn nút nộp ở màn cuối"
    else:
        element_id = anchor.split(":", 1)[1]
        assert f'id="{element_id}"' in html, f"{host}: không thấy id {element_id} ở màn cuối"


@pytest.mark.parametrize(("host", "rel"), [(h, r) for h, (r, _a) in _SNAPSHOTS.items()])
def test_url_snapshot_khop_urlpattern(host, rel):
    """URL trong dòng 'saved from url' của chính file phải lọt luật — đây mới là bằng chứng
    rằng urlPattern viết đúng, chứ không phải đường dẫn tôi nhớ nhầm."""
    path = _SNAPSHOT_DIR / rel
    if not path.exists():
        pytest.skip(f"không có thư mục mẫu: {path}")
    head = path.open(encoding="utf-8", errors="ignore").read(4000)
    found = re.search(r"saved from url=\(\d+\)(https?://[^\s\"']+)", head)
    assert found, f"{rel}: không đọc được URL nguồn"
    url = found.group(1)
    assert host in url, f"{rel}: URL {url} không thuộc {host}"
    path_only = "/" + url.split("/", 3)[3].split("?")[0] if url.count("/") >= 3 else "/"
    assert re.search(PORTAL_SUBMIT[host]["urlPattern"], path_only), (
        f"{host}: urlPattern không khớp đường dẫn thật {path_only}"
    )


# ── Bộ VHTTDL: URL không tách được bước, mỏ neo là NHÃN ───────────────────────────────────
_VH_HOST = "dichvucong.bvhttdl.gov.vn"


def test_bvhttdl_bat_dung_nut_luu_va_nop():
    assert _matches(_VH_HOST, "/nop-ho-so", label="Lưu và nộp hồ sơ")


def test_bvhttdl_bo_qua_cac_nut_con_lai_cua_trang():
    """Nguyên văn các nút khác trong snapshot — không nút nào được lọt lưới."""
    for label in ["Đóng", "Xác nhận", "×"]:
        assert not _matches(_VH_HOST, "/nop-ho-so", label=label)


def test_bvhttdl_khong_tinh_ngoai_trang_nop_ho_so():
    assert not _matches(_VH_HOST, "/trang-chu", label="Lưu và nộp hồ sơ")


# ── Lưới thứ hai: không được đánh đổi bằng đếm thừa ───────────────────────────────────────
def test_formio_tuyet_doi_khong_lay_nhan_tiep_tuc():
    """Đếm trên toàn bộ snapshot Form.io: "Tiếp tục" xuất hiện 206 lần ở các BƯỚC GIỮA (cùng
    URL apply-online nên urlPattern không đỡ được). Đưa nhãn này vào là mỗi hồ sơ bị đếm
    thành cả chục lần nộp — đúng kiểu sai không ai phát hiện ra."""
    for host in _FORMIO_HOSTS:
        assert "tiep tuc" not in (PORTAL_SUBMIT[host].get("buttonText") or []), host


def test_formio_nhan_du_phong_khong_bat_nut_buoc_giua():
    """Thêm "nop ho so"/"thanh toan" làm lưới hai KHÔNG được kéo theo nút bước giữa."""
    for host in _FORMIO_HOSTS:
        assert not _matches(host, _FORMIO_PATH, label="Tiếp tục", tag=_FORMIO_NEXT_STEP)
        assert not _matches(host, _FORMIO_PATH, label="Quay lại", tag=_FORMIO_NEXT_STEP)
        assert not _matches(host, _FORMIO_PATH, label="Đồng ý", tag=_FORMIO_NEXT_STEP)


def test_formio_van_bat_duoc_khi_mat_thuoc_tinh_form():
    """Cổng nâng cấp Angular bỏ mất form="captchaForm" → mười cổng tắt tiếng cùng lúc nếu
    chỉ có một mỏ neo. Lưới nhãn phải gánh được hai biến thể nhãn đã gặp."""
    for host in _FORMIO_HOSTS:
        for label in ("Nộp hồ sơ", "Thanh toán"):
            assert _matches(host, _FORMIO_PATH, label=label, tag=_FORMIO_NEXT_STEP), f"{host}/{label}"


def test_bvhttdl_luoi_class_khong_dinh_nut_dong():
    """`style_btn` vs `style_btn_close`: so theo TOKEN class nên không được dính nhầm."""
    submit_tag = '<button type="button" class="btn btn-light btn-sm style_btn mr-2">'
    close_tag = '<button type="button" class="btn btn-light btn-sm style_btn_close">'
    assert _matches(_VH_HOST, "/nop-ho-so", label="Đã đổi nhãn", tag=submit_tag)
    assert not _matches(_VH_HOST, "/nop-ho-so", label="Đóng", tag=close_tag)
