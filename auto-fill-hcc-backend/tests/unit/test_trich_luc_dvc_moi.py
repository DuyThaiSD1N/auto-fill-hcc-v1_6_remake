import asyncio
import re
import unicodedata
from pathlib import Path

import pytest

from app.pipelines.trich_luc_dvc_moi.attach.dinh_kem_khong_tach.planner import build_plan_items
from app.pipelines.trich_luc_dvc_moi.process import mapper, reason
from app.pipelines.trich_luc_dvc_moi.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import PROCEDURES

KEY = "trich-luc-ks"
SNAPSHOT = (Path(__file__).resolve().parents[3] / "html mới" / "trích lụcc" / "trích lục html mới.html")
ACCOUNT = {"applicantFullname": "NGUYEN VAN A", "applicantIdentityNumber": "001090000001"}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn")).lower()


def _context(relation="", other="", subject_id="", status="còn sống", event="khai sinh"):
    return (
        "<phan_vai_da_xac_dinh>\n"
        f"<nguoi_duoc_cap>\nHọ tên: TRAN THI B\nSố định danh: {subject_id}\nTrạng thái: {status}\n</nguoi_duoc_cap>\n"
        f"<giay_to_ho_tich>\nLoại trích lục cần cấp: {event}\n</giay_to_ho_tich>\n"
        f"<quan_he>\nKết luận: {relation}\nQuan hệ khác: {other}\nCăn cứ: x\n</quan_he>\n"
        "</phan_vai_da_xac_dinh>"
    )


def _enrich(values: dict, context: str, account=ACCOUNT):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    return mapper.enrich(fields, {"formContext": account, "_reasoning_context": context})


SUBJECT = {
    "NguoiDuocCap_HoTen": "Tran Thi B",
    "NguoiDuocCap_SoDinhDanh": "001190000002",
    "NguoiDuocCap_NgaySinh": "01/02/1990",
    "NguoiDuocCap_GioiTinh": "Nữ",
    "NguoiDuocCap_SoGiayTo": "001190000002",
    "NguoiDuocCap_NgayCap": "02/03/2021",
    "NguoiDuocCap_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường Xuân Hương", "diaChi": "Số 1"},
    "GiayTo_LoaiSuKien": "birth",
    "GiayTo_CoQuanDangKy": "Ủy ban nhân dân phường X",
    "GiayTo_So": "12/1990",
    "GiayTo_NgayDangKy": "05/02/1990",
    "SoLuongBanSao": "02",
}


def _names(out):
    return [f["name"] for f in out]


def test_registry_entry_wires_new_package():
    entry = next(p for p in PROCEDURES if p["key"] == KEY)
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["textPriority"] and entry["detect"]["headingDisabled"]
    assert entry["detect"]["urlScope"] == ["://dichvucong.gov.vn/nop-ho-so"]


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="thiếu snapshot cổng")
def test_detect_phrases_and_ui_keys_exist_in_snapshot():
    html = SNAPSHOT.read_text(encoding="utf-8")
    body = _fold(re.sub(r"<[^>]+>", " ", html))
    entry = next(p for p in PROCEDURES if p["key"] == KEY)
    for phrase in entry["detect"]["textIncludes"]:
        assert _fold(phrase) in body
    data_names = set(re.findall(r'data-name="([A-Za-z0-9_]+?)__\d+"', html))
    # Ô "Quan hệ khác" và bốn ô địa chỉ người được cấp chỉ render theo điều kiện → không có trong snapshot.
    conditional = {"citizenField8", "citizenField21", "citizenNDK_TinhThanh", "citizenNDK_PhuongXa", "citizenField38"}
    for name in set(UI_COMP_BY_NAME) - conditional:
        assert name in data_names, name


def test_self_by_identity_skips_subject_block():
    out, warnings = _enrich({**SUBJECT, "NguoiDuocCap_SoDinhDanh": ACCOUNT["applicantIdentityNumber"]},
                            _context("Mẹ đẻ"))
    names = _names(out)
    assert names[0] == "citizenQuanhe"
    assert out[0]["value"] == "Bản thân"
    assert not [n for n in names if n.startswith("citizenNDK_") or n in ("citizenField13", "citizenField32")]
    assert "citizenLoaiViecYeuCau" in names and "citizencauhoi3" in names
    assert not warnings


def test_kinh_gui_and_tai_left_to_extension_tool_account():
    out, _ = _enrich(SUBJECT, _context("Mẹ đẻ"))
    assert not {"citizenField27", "citizenField37"} & set(_names(out))


def test_cmnd_issuer_never_defaulted():
    values = {**SUBJECT, "NguoiDuocCap_SoGiayTo": "060145645", "NguoiDuocCap_NgayCap": "07/03/1979"}
    out, _ = _enrich(values, _context("Mẹ đẻ"))
    by = {f["name"]: f for f in out}
    assert by["citizenNDK_LoaiGiayToTuyThan"]["value"] == "Chứng minh nhân dân"
    assert "citizenNDK_NoiCap" not in by


def test_no_extract_type_when_not_stated():
    values = {k: v for k, v in SUBJECT.items() if k != "GiayTo_LoaiSuKien"}
    out, _ = _enrich(values, _context("Mẹ đẻ", event="không xác định"))
    names = _names(out)
    assert "citizenLoaiViecYeuCau" not in names and "citizenTenGiayToHoTich" not in names


def test_relation_other_person_fills_subject_block_in_order():
    out, warnings = _enrich(SUBJECT, _context("Mẹ đẻ", subject_id="001190000002"))
    names = _names(out)
    by = {f["name"]: f for f in out}
    assert by["citizenQuanhe"]["value"] == "Mẹ đẻ"
    assert names.index("citizenQuanhe") < names.index("citizenNDK_HoVaTen")
    assert by["citizenNDK_HoVaTen"]["value"] == "TRAN THI B"
    assert by["citizenNDK_NoiCap"]["value"]  # mặc định theo ngày cấp
    address = ["citizenNDK_Noicutru", "citizenField21", "citizenNDK_TinhThanh", "citizenNDK_PhuongXa", "citizenField38"]
    assert [n for n in names if n in address] == address
    assert by["citizenField21"]["value"] == "Việt Nam"
    assert by["citizenNDK_PhuongXa"]["value"] == "Phường Xuân Hương" and by["citizenField38"]["value"] == "Số 1"
    assert by["citizenSoLuongBanSao"]["value"] == "2"
    assert by["citizenLoaiViecYeuCau"]["value"].startswith("Giấy khai sinh")
    assert not warnings


@pytest.mark.parametrize("reason_event,code", [
    ("chấm dứt giám sát giám hộ", "supervision_end"), ("nuôi con nuôi", "adoption"),
    ("thay đổi cải chính", "civil_change"), ("khai tử", "death"),
])
def test_all_extract_types_map_to_portal_option(reason_event, code):
    values = {k: v for k, v in SUBJECT.items() if k != "GiayTo_LoaiSuKien"}
    out, _ = _enrich(values, _context("Mẹ đẻ", event=reason_event))
    by = {f["name"]: f for f in out}
    assert by["citizenLoaiViecYeuCau"]["value"] == mapper._EVENT_TO_OPTION[code]


def test_llm_self_rejected_when_identity_differs():
    out, warnings = _enrich(SUBJECT, _context("Bản thân"))
    assert "citizenQuanhe" not in _names(out)
    assert "citizenNDK_HoVaTen" in _names(out)
    assert warnings


def test_self_never_for_deceased():
    values = {**SUBJECT, "NguoiDuocCap_SoDinhDanh": ACCOUNT["applicantIdentityNumber"], "GiayTo_LoaiSuKien": "death"}
    out, warnings = _enrich(values, _context("Bản thân", status="đã chết", event="khai tử"))
    assert "citizenQuanhe" not in _names(out)
    assert warnings


def test_other_relation_needs_text():
    out, _ = _enrich(SUBJECT, _context("Khác", other="Em ruột"))
    by = {f["name"]: f for f in out}
    assert by["citizenQuanhe"]["value"] == "Khác" and by["citizenField8"]["value"] == "Em ruột"
    out, warnings = _enrich(SUBJECT, _context("Khác"))
    assert "citizenQuanhe" not in _names(out) and warnings


def test_unknown_relation_left_blank_with_warning():
    out, warnings = _enrich(SUBJECT, _context("Không xác định"))
    assert "citizenQuanhe" not in _names(out)
    assert warnings


def test_child_under_14_without_card_has_no_id_cluster():
    values = {k: v for k, v in SUBJECT.items() if k not in ("NguoiDuocCap_NgayCap", "NguoiDuocCap_SoGiayTo")}
    values["NguoiDuocCap_NgaySinh"] = "01/02/2020"
    out, _ = _enrich(values, _context("Mẹ đẻ"))
    names = _names(out)
    assert "citizenNDK_SoDinhDanh" in names
    assert "citizenNDK_SoGiayToTuyThan" not in names and "citizenNDK_LoaiGiayToTuyThan" not in names


def test_reason_render_and_truncated_block():
    raw = ("<nguoi_nop>\nHọ tên: A\n</nguoi_nop>\n<nguoi_duoc_cap>\nHọ tên: B\nSố định danh: 1\n</nguoi_duoc_cap>\n"
           "<giay_to_ho_tich>\nLoại trích lục cần cấp: khai sinh\n</giay_to_ho_tich>\n<quan_he>\nKết luận: Mẹ đẻ")
    ctx = reason._render_context(raw, {"formContext": ACCOUNT})
    assert "<phan_vai_da_xac_dinh>" in ctx
    assert reason.labeled_value(reason.section(ctx, "quan_he"), "Kết luận") == "Mẹ đẻ"
    assert reason._render_context("không có khối nào", {}) == ""


def test_reason_hint_marks_documents_with_account_id():
    docs = [{"name": "a", "text": "Số 001 090 000 001"}, {"name": "b", "text": "khác"}]
    content = reason._build_user_content(docs, {"formContext": ACCOUNT})
    assert "Tài liệu chứa đúng số định danh này: 1." in content


def test_attach_plan_puts_every_file_on_the_single_row():
    items = build_plan_items(["gks.pdf", "cccd.jpg", "uy-quyen.pdf"])
    assert [i["fileIndex"] for i in items] == [0, 1, 2]
    assert {i["slotIndex"] for i in items} == {0}
    assert all(i["target"] == "fixed-slot" and i["noChooserClick"] for i in items)


def test_attach_plan_async_contract(monkeypatch):
    from app.pipelines.trich_luc_dvc_moi.attach import plan
    from app.pipelines.trich_luc_dvc_moi.attach.dinh_kem_khong_tach import planner
    from app.process.schemas import FileItem
    from app.services import ocr

    async def fake_ocr(files):
        return [{"text": "VĂN BẢN ỦY QUYỀN ..."} for _ in files]

    async def fake_chat(*_args, **_kwargs):
        return '{"documents":[{"index":0,"documentName":"Văn bản ủy quyền"}]}'

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [FileItem(name="IMG_9.jpg", type="image/jpeg", dataUrl="data:,", role=""),
             FileItem(name="ghi-chu.docx", type="application/msword", dataUrl="data:,", role="")]
    res = asyncio.run(plan(files, {}))
    assert res["errors"] == []
    # Tệp OCR được → tên theo giấy tờ; tệp không OCR → giữ tên gốc. Mọi tệp vẫn vào dòng duy nhất.
    assert [i["documentName"] for i in res["attachments"]] == ["Văn bản ủy quyền", "ghi-chu"]
    assert {i["slotIndex"] for i in res["attachments"]} == {0}


def test_attach_ten_trung_duoc_danh_so():
    items = build_plan_items(["a.jpg", "b.jpg"], {0: "Căn cước công dân", 1: "Căn cước công dân"})
    assert [i["documentName"] for i in items] == ["Căn cước công dân", "Căn cước công dân 2"]
