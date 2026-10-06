import re
import unicodedata
from pathlib import Path

import pytest

from app.pipelines.cai_chinh_dvc_moi.attach.planner import ROW_CAN_CU, ROW_UY_QUYEN, build_plan_items
from app.pipelines.cai_chinh_dvc_moi.process import mapper, reason
from app.pipelines.cai_chinh_dvc_moi.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import PROCEDURES

KEY = "thay-doi-cai-chinh-ho-tich"
SNAPSHOT = Path(__file__).resolve().parents[3] / "html mới" / "cải chính" / "cải chính html mới.html"
TRICH_LUC_SNAPSHOT = Path(__file__).resolve().parents[3] / "html mới" / "trích lụcc" / "trích lục html mới.html"
ACCOUNT = {"applicantFullname": "NGUYEN VAN A", "applicantIdentityNumber": "001090000001"}
RELATION = "citizenQuanhevsngcaichinhhotich1"


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn")).lower()


def _body(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html)
    html = re.sub(r'<div[^>]*style="display: none;"[\s\S]*?</ul>', " ", html)  # popup option ẩn
    return _fold(re.sub(r"<[^>]+>", " ", html))


def _context(relation="", subject_id="", viec="Cải chính", giay_to="khai sinh", status="còn sống"):
    return (
        "<phan_vai_da_xac_dinh>\n"
        f"<nguoi_thay_doi>\nHọ tên: TRAN THI B\nSố định danh: {subject_id}\nTrạng thái: {status}\n</nguoi_thay_doi>\n"
        f"<viec_dang_ky>\nGiấy tờ hộ tịch đã đăng ký: {giay_to}\nLoại việc: {viec}\n</viec_dang_ky>\n"
        f"<quan_he>\nKết luận: {relation}\n</quan_he>\n"
        "</phan_vai_da_xac_dinh>"
    )


def _enrich(values: dict, context: str, account=ACCOUNT):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    return mapper.enrich(fields, {"formContext": account, "_reasoning_context": context})


SUBJECT = {
    "NguoiThayDoi_HoTen": "Tran Thi B",
    "NguoiThayDoi_SoDinhDanh": "001190000002",
    "NguoiThayDoi_NgaySinh": "01/02/1990",
    "NguoiThayDoi_GioiTinh": "Nữ",
    "NguoiThayDoi_QuocTich": "Trung Quốc",
    "NguoiThayDoi_SoGiayTo": "001190000002",
    "NguoiThayDoi_NgayCap": "16/10/2023",
    "NguoiThayDoi_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường Xuân Hương", "diaChi": "Số 1"},
    "HoSo_So": "143/TLKS-BS",
    "HoSo_NgayDangKy": "07/06/1978",
    "HoSo_NoiDangKy": "UBND phường X",
    "NoiDung": "Thay đổi lại quốc tịch từ A thành B",
    "LyDo": "Sai sót khi đăng ký",
    "SoLuongBanSao": "03",
}


def _names(out):
    return [f["name"] for f in out]


def test_registry_entry():
    entry = next(p for p in PROCEDURES if p["key"] == KEY)
    assert entry["hasAttachmentStep"] and entry["detect"]["textPriority"]
    assert entry["detect"]["urlScope"] == ["://dichvucong.gov.vn/nop-ho-so"]


@pytest.mark.skipif(not (SNAPSHOT.exists() and TRICH_LUC_SNAPSHOT.exists()), reason="thiếu snapshot cổng")
def test_detect_matches_own_page_only():
    phrases = [_fold(p) for p in next(p for p in PROCEDURES if p["key"] == KEY)["detect"]["textIncludes"]]
    assert all(p in _body(SNAPSHOT) for p in phrases)
    assert not all(p in _body(TRICH_LUC_SNAPSHOT) for p in phrases)
    trich_luc = [_fold(p) for p in next(p for p in PROCEDURES if p["key"] == "trich-luc-ks")
                 ["detect"]["textIncludes"]]
    assert not all(p in _body(SNAPSHOT) for p in trich_luc)


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="thiếu snapshot cổng")
def test_ui_keys_exist_in_snapshot():
    data_names = set(re.findall(r'data-name="([A-Za-z0-9_]+?)__\d+"', SNAPSHOT.read_text(encoding="utf-8")))
    # Snapshot chụp trước khi cổng đổi ô ngày sinh "citizenNDKNgaysinh" → "citizenNDK_NgaySinh" (DOM thật).
    for name in set(UI_COMP_BY_NAME) - {"citizenNDKNoiCuTru_TrongNuoc", "citizenNDK_NgaySinh"}:
        assert name in data_names, name


def test_self_by_identity_skips_subject_block():
    out, warnings = _enrich({**SUBJECT, "NguoiThayDoi_SoDinhDanh": ACCOUNT["applicantIdentityNumber"]}, _context())
    assert out[0] == {"name": "citizenNycNoicutru", "comp": "sjs-radio", "value": "Trong Nước",
                      "default": True, "onlyIfEmpty": True}
    assert out[1] == {"name": RELATION, "comp": "sjs-radio", "value": "Bản thân"}
    assert not [n for n in _names(out) if n.startswith("citizenNDK")]
    assert {"citizenViecDangKy", "citizenTTNoidungdk", "citizenLydothaydoi"} <= set(_names(out))
    assert not warnings


def test_only_account_documents_means_self_marked_default():
    """Không tờ khai / ủy quyền / giấy hộ tịch, chỉ có giấy tờ của chủ tài khoản → Bản thân, tô vàng."""
    context = _context(subject_id=ACCOUNT["applicantIdentityNumber"], viec="không xác định",
                       giay_to="không xác định").replace(
        "Trạng thái: còn sống", "Trạng thái: còn sống\nNguồn: giấy tờ chủ tài khoản")
    out, warnings = _enrich({}, context)
    relation = next(f for f in out if f["name"] == RELATION)
    assert relation["value"] == "Bản thân" and relation["default"] is True
    assert not [n for n in _names(out) if n.startswith("citizenNDK")]
    assert not warnings


def test_other_person_fills_subject_block_in_order():
    out, _ = _enrich(SUBJECT, _context())
    by = {f["name"]: f for f in out}
    names = _names(out)
    assert by[RELATION]["value"] == "Khác" and not by[RELATION].get("default")
    assert names.index(RELATION) < names.index("citizenNDKHoTen")
    assert by["citizenNDKQuocTich"]["value"] == "Trung Quốc" and not by["citizenNDKQuocTich"].get("default")
    assert names.index("citizenNDKNoiCuTru") < names.index("citizenNDKNoiCuTru_TrongNuoc")
    assert by["citizenNDKNoiCuTru_TrongNuoc"]["radio"] == "citizenNDKNoiCuTru"
    assert by["citizenViecDangKy"]["value"] == "Cải chính thông tin hộ tịch"
    assert by["citizenLoainghiepvu"]["value"] == "Giấy khai sinh"
    assert by["citizenSoluongbansao"]["value"] == "3"


def test_birth_date_uses_current_portal_key_as_text():
    out, _ = _enrich(SUBJECT, _context())
    birth = next(f for f in out if f["name"] == "citizenNDK_NgaySinh")
    assert birth == {"name": "citizenNDK_NgaySinh", "comp": "sjs-text", "value": SUBJECT["NguoiThayDoi_NgaySinh"]}
    assert "citizenNDKNgaysinh" not in _names(out)


def test_relation_by_name_when_no_identity_is_marked_default():
    values = {k: v for k, v in SUBJECT.items() if k not in ("NguoiThayDoi_SoDinhDanh", "NguoiThayDoi_SoGiayTo")}
    values["NguoiThayDoi_HoTen"] = ACCOUNT["applicantFullname"]
    out, _ = _enrich(values, _context(), account={"applicantFullname": ACCOUNT["applicantFullname"]})
    assert out[1]["value"] == "Bản thân" and out[1]["default"]


def test_relation_unknown_without_anchor_warns():
    values = {k: v for k, v in SUBJECT.items() if not k.startswith("NguoiThayDoi_")}
    out, warnings = _enrich(values, _context("Không xác định"), account={})
    assert RELATION not in _names(out) and warnings


def test_deceased_never_self():
    out, _ = _enrich({**SUBJECT, "NguoiThayDoi_SoDinhDanh": ACCOUNT["applicantIdentityNumber"]},
                     _context(status="đã chết"))
    assert out[1]["value"] == "Khác"


def test_zero_copies_kept_and_cmnd_issuer_not_defaulted():
    values = {**SUBJECT, "SoLuongBanSao": "0", "NguoiThayDoi_SoGiayTo": "060145645"}
    values.pop("NguoiThayDoi_SoDinhDanh")
    out, _ = _enrich(values, _context())
    by = {f["name"]: f for f in out}
    assert by["citizenSoluongbansao"]["value"] == "0"
    assert by["citizenNDKLoaiGiaytotuythan"]["value"] == "Chứng minh nhân dân"
    assert "citizenNDKCoquancap" not in by


def test_unknown_viec_and_document_left_blank():
    values = {k: v for k, v in SUBJECT.items()}
    out, _ = _enrich(values, _context(viec="không xác định", giay_to="không xác định"))
    assert "citizenViecDangKy" not in _names(out) and "citizenLoainghiepvu" not in _names(out)


@pytest.mark.parametrize("viec,option", [("Bổ sung", "Bổ sung thông tin hộ tịch"),
                                         ("Thay đổi", "Thay đổi thông tin hộ tịch"),
                                         ("Xác định lại dân tộc", "Xác định lại dân tộc")])
def test_viec_options(viec, option):
    out, _ = _enrich(SUBJECT, _context(viec=viec))
    assert {f["name"]: f for f in out}["citizenViecDangKy"]["value"] == option


@pytest.mark.parametrize("giay_to,option", [
    ("giám sát giám hộ", "Trích lục đăng ký đăng ký giám sát việc giám hộ"),
    ("giám hộ", "Trích lục đăng ký giám hộ"), ("nhận cha mẹ con", "Trích lục đăng ký nhận cha, mẹ, con"),
    ("khai tử", "Trích lục khai tử"), ("kết hôn", "Giấy chứng nhận kết hôn"),
])
def test_document_options(giay_to, option):
    out, _ = _enrich(SUBJECT, _context(giay_to=giay_to))
    assert {f["name"]: f for f in out}["citizenLoainghiepvu"]["value"] == option


def test_reason_context_parsing():
    raw = ("<nguoi_thay_doi>\nHọ tên: B\n</nguoi_thay_doi>\n<viec_dang_ky>\nLoại việc: Cải chính\n</viec_dang_ky>\n"
           "<quan_he>\nKết luận: Khác")
    ctx = reason._render_context(raw, {"formContext": ACCOUNT})
    assert reason.labeled_value(reason.section(ctx, "quan_he"), "Kết luận") == "Khác"
    assert reason._render_context("rỗng", {}) == ""


def test_attach_routes_authorization_and_everything_else():
    items = build_plan_items(["cccd.pdf", "trich-luc.pdf", "to-khai.pdf", "uy-quyen.pdf"], {3: "uy_quyen", 0: "other"})
    rows = [i["slotName"] for i in items]
    assert rows == [ROW_CAN_CU["slotName"]] * 3 + [ROW_UY_QUYEN["slotName"]]
    assert [i["fileIndex"] for i in items] == [0, 1, 2, 3]
    assert all(i["target"] == "fixed-slot" for i in items)
