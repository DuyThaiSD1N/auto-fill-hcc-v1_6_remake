import re
import unicodedata
from pathlib import Path

import pytest

from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import ROW_CAN_CU, ROW_UY_QUYEN, build_plan_items
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
    # Snapshot chụp trước khi cổng đổi ô ngày sinh "citizenNDKNgaysinh" → "citizenNDK_NgaySinh" (DOM thật);
    # ô "citizenMqhkhac" chỉ render sau khi chọn quan hệ "Khác".
    for name in set(UI_COMP_BY_NAME) - {"citizenNDKNoiCuTru_TrongNuoc", "citizenNDK_NgaySinh", "citizenMqhkhac"}:
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


def test_attach_ten_tep_theo_ten_giay_to_llm_doc():
    items = build_plan_items(["IMG_1.jpg", "IMG_2.jpg", "scan.pdf", "z123.pdf"], {},
                             {0: "Căn cước công dân", 1: "Căn cước công dân", 2: "Giấy khai sinh"})
    # Trùng loại giấy → đánh số; LLM không đọc ra tên → giữ tên tệp gốc.
    assert [i["documentName"] for i in items] == ["Căn cước công dân", "Căn cước công dân 2", "Giấy khai sinh", "z123"]


def test_attach_ten_cccd_theo_chu_the_khong_dau_va_mat_the():
    from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import _llm_document_name
    front = _llm_document_name({"documentName": "CĂN CƯỚC CÔNG DÂN", "matThe": "truoc", "chuThe": "NGUYỄN VĂN AN"})
    back = _llm_document_name({"documentName": "Căn cước công dân", "matThe": "sau", "chuThe": "NGUYEN<<VAN<AN"})
    assert (front, back) == ("CCCD Nguyen Van An mặt trước", "CCCD Nguyen Van An mặt sau")
    assert _llm_document_name({"documentName": "Giấy khai sinh", "matThe": ""}) == "Giấy khai sinh"


def test_attach_ten_cccd_ca_hai_mat_tren_mot_trang_khong_ghi_mat():
    from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import _llm_document_name
    name = _llm_document_name({"documentName": "Căn cước công dân", "matThe": "ca_hai", "chuThe": "NGUYỄN VĂN AN"})
    assert name == "CCCD Nguyen Van An"


def test_quan_he_cai_chinh_ten_theo_ket_luan_phan_vai_khi_thieu_so():
    from app.pipelines.cai_chinh_dvc_moi.process import mapper as cc_mapper
    ctx = ("<nguoi_thay_doi>\nHọ tên: NGUYỄN THỊ AM\nSố định danh:\nTrạng thái: còn sống\n</nguoi_thay_doi>\n"
           "<quan_he>\nKết luận: Bản thân\n</quan_he>")
    opts = {"formContext": {"applicantFullname": "Nguyễn Thị An", "applicantIdentityNumber": "001183000001"}}
    assert cc_mapper._relation({}, ctx, opts)[0] == "Bản thân"
    assert cc_mapper._relation({}, ctx.replace("Bản thân", "Khác"), opts)[0] == "Khác"


def test_noi_dung_bo_muc_cu_moi_giong_nhau():
    from app.pipelines.cai_chinh_dvc_moi.process.mapper import _drop_no_change
    text = "Cải chính tên mẹ từ A thành B; cải chính tên bố từ Trần Văn C thành Trần Văn C; cải chính năm sinh bố từ 1968 thành 1964"
    assert _drop_no_change(text) == "Cải chính tên mẹ từ A thành B; cải chính năm sinh bố từ 1968 thành 1964"


def test_quan_he_cu_the_chi_dien_khi_khac_va_nguoi_yeu_cau_la_tai_khoan():
    def ctx(relation="Khác", requester_id=ACCOUNT["applicantIdentityNumber"], requester="NGUYEN VAN A"):
        return _context(relation=relation).replace(
            f"Kết luận: {relation}",
            f"Kết luận: {relation}\nQuan hệ trên tờ khai: Chồng\nNgười yêu cầu tờ khai: {requester}\n"
            f"Số định danh người yêu cầu tờ khai: {requester_id}")

    out, _ = _enrich(SUBJECT, ctx())
    names = _names(out)
    assert {f["name"]: f["value"] for f in out}["citizenMqhkhac"] == "Chồng"
    assert names.index(RELATION) < names.index("citizenMqhkhac") < names.index("citizenNDKHoTen")
    # Thiếu số → so họ tên, bỏ qua dấu.
    assert "citizenMqhkhac" in _names(_enrich(SUBJECT, ctx(requester_id="", requester="Nguyễn Văn Á"))[0])
    # Người yêu cầu tờ khai không phải chủ tài khoản (bên được ủy quyền nộp thay) → bỏ trống.
    assert "citizenMqhkhac" not in _names(_enrich(SUBJECT, ctx(requester_id="001090000009"))[0])
    assert "citizenMqhkhac" not in _names(_enrich(SUBJECT, _context(relation="Khác"))[0])
    self_out, _ = _enrich({**SUBJECT, "NguoiThayDoi_SoDinhDanh": ACCOUNT["applicantIdentityNumber"]},
                          ctx(relation="Bản thân"))
    assert "citizenMqhkhac" not in _names(self_out)
    # Số người yêu cầu OCR rớt chữ số → so họ tên.
    assert "citizenMqhkhac" in _names(_enrich(SUBJECT, ctx(requester_id="00109000000"))[0])


def test_to_khai_ban_than_cua_chu_tai_khoan_chot_ban_than_khi_thieu_so():
    """Thiếu số người thay đổi, tên trong sổ khác tên tài khoản, nhưng tờ khai do chủ tài khoản khai ghi "Bản thân"."""
    context = _context(relation="Khác").replace(
        "Kết luận: Khác",
        "Kết luận: Khác\nQuan hệ trên tờ khai: Bản Thân\nNgười yêu cầu tờ khai: NGUYEN VAN A\n"
        f"Số định danh người yêu cầu tờ khai: {ACCOUNT['applicantIdentityNumber']}")
    out, _ = _enrich({**SUBJECT, "NguoiThayDoi_SoDinhDanh": ""}, context)
    by = {f["name"]: f for f in out}
    assert by[RELATION]["value"] == "Bản thân" and by[RELATION]["default"] is True
    assert "citizenMqhkhac" not in by
