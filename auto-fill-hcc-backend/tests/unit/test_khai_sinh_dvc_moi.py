import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.pipelines.khai_sinh_dvc_moi.attach.planner import ROW_CHUNG_SINH, ROWS, build_plan_items
from app.pipelines.khai_sinh_dvc_moi.process import mapper, reason
from app.pipelines.khai_sinh_dvc_moi.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import PROCEDURES

KEY = "khai-sinh-dang-ky-thuong"
HTML_DIR = Path(__file__).resolve().parents[3] / "html mới"
SNAPSHOTS = {
    KEY: HTML_DIR / "khai sinh" / "khai sinh html mới.html",
    "trich-luc-ks": HTML_DIR / "trích lụcc" / "trích lục html mới.html",
    "thay-doi-cai-chinh-ho-tich": HTML_DIR / "cải chính" / "cải chính html mới.html",
}
MOTHER = {"applicantFullname": "NGUYEN THI A", "applicantIdentityNumber": "001190000001"}
RELATION = "citizenQuanhevoinguoiduockhaisinh"


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn")).lower()


def _body(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html)
    return _fold(re.sub(r"<[^>]+>", " ", html))


def _phrases(key: str) -> list[str]:
    return [_fold(p) for p in next(p for p in PROCEDURES if p["key"] == key)["detect"]["textIncludes"]]


def _context(relation="", detail="", loai="Đã xác định được cả cha lẫn mẹ", co_ho_so="Không"):
    return (
        "<phan_vai_da_xac_dinh>\n<con>\nHọ tên: TRAN VAN C\n</con>\n"
        f"<quan_he>\nKết luận: {relation}\nQuan hệ cụ thể: {detail}\n</quan_he>\n"
        f"<loai_khai_sinh>\nKết luận: {loai}\nĐã có hồ sơ, giấy tờ cá nhân: {co_ho_so}\n</loai_khai_sinh>\n"
        "</phan_vai_da_xac_dinh>"
    )


def _enrich(values: dict, context: str, account=MOTHER):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    return mapper.enrich(fields, {"formContext": account, "_reasoning_context": context})


def _today_minus(days: int) -> str:
    return (date.today() - timedelta(days=days)).strftime("%d/%m/%Y")


BASE = {
    "Con_HoTen": "Tran Van C",
    "Con_NgaySinh": _today_minus(10),
    "Con_GioiTinh": "Nam",
    "Con_NoiSinh": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường Xuân Hương", "diaChi": "Bệnh viện X"},
    "Me_HoTen": "Nguyen Thi A",
    "Me_SoDinhDanh": "001190000001",
    "Me_SoGiayTo": "001190000001",
    "Me_NgayCap": "02/03/2021",
    "Me_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường Xuân Hương", "diaChi": "Số 1"},
    "Cha_HoTen": "Zhang Tao",
    "Cha_QuocTich": "Trung Quốc",
    "Cha_LoaiGiayTo": "Hộ chiếu",
    "Cha_SoGiayTo": "EA1234567",
    "Cha_NgaySinh": "1998",
    "SoLuongBanSao": "10",
}


def _by(out):
    return {f["name"]: f for f in out}


def test_registry_entry():
    entry = next(p for p in PROCEDURES if p["key"] == KEY)
    assert entry["hasAttachmentStep"] and entry["detect"]["urlScope"] == ["://dichvucong.gov.vn/nop-ho-so"]


@pytest.mark.skipif(not all(p.exists() for p in SNAPSHOTS.values()), reason="thiếu snapshot cổng")
def test_detect_three_new_portal_forms_do_not_collide():
    bodies = {key: _body(path) for key, path in SNAPSHOTS.items()}
    for key in SNAPSHOTS:
        for page, body in bodies.items():
            assert all(p in body for p in _phrases(key)) == (key == page), (key, page)


@pytest.mark.skipif(not SNAPSHOTS[KEY].exists(), reason="thiếu snapshot cổng")
def test_ui_keys_exist_in_snapshot():
    data_names = set(re.findall(r'data-name="([A-Za-z0-9_]+?)__\d+"', SNAPSHOTS[KEY].read_text(encoding="utf-8")))
    for name in UI_COMP_BY_NAME:
        if name.endswith("_TrongNuoc") or name == "citizenField62":  # chỉ hiện theo điều kiện
            continue
        assert name in data_names, name


def test_mother_submits_order_and_blocks():
    out, warnings = _enrich(BASE, _context("Mẹ"))
    names = [f["name"] for f in out]
    by = _by(out)
    assert names[:3] == [RELATION, "citizenLoaiDangKy", "citizenLoaikhaisinh_NgdcKS"]
    assert by[RELATION]["value"] == "Mẹ" and not by[RELATION].get("default")
    assert "citizenField62" not in by
    assert by["citizenLoaiDangKy"]["value"] == "Đăng ký đúng hạn"
    assert by["citizenQuoctich_NgdcKS"]["value"] == "Việt Nam" and by["citizenQuoctich_NgdcKS"]["default"]
    assert by["citizenNoisinhnks_TrongNuoc"]["radio"] == "citizenNoisinhnks"
    assert names.index("citizenMeNoicutru") < names.index("citizenMeNoicutru_TrongNuoc")
    assert by["citizenField24"]["value"] == "Hộ chiếu" and by["citizenSoGiayToTuyThan_cha"]["value"] == "EA1234567"
    assert "citizenNDK_NgaySinhCha" not in by          # chỉ có năm sinh
    assert "citizenCoquancap_cha" not in by            # hộ chiếu không mặc định cơ quan cấp
    assert by["citizenSoluongbansao"]["value"] == "10"
    assert not warnings


def test_late_registration_and_existing_documents():
    out, _ = _enrich({**BASE, "Con_NgaySinh": _today_minus(90)}, _context("Mẹ"))
    assert _by(out)["citizenLoaiDangKy"]["value"] == "Đăng ký quá hạn"
    out, _ = _enrich(BASE, _context("Mẹ", co_ho_so="Có"))
    assert _by(out)["citizenLoaiDangKy"]["value"] == "Đăng ký cho người đã có hồ sơ, giấy tờ cá nhân"


def test_self_registration_maps_to_other_with_text():
    account = {"applicantFullname": "TRAN VAN C", "applicantIdentityNumber": ""}
    out, _ = _enrich(BASE, _context("Bản thân"), account=account)
    by = _by(out)
    assert by[RELATION]["value"] == "Khác" and by["citizenField62"]["value"] == "Bản thân"


def test_other_requester_uses_declaration_relation_only_when_requester_is_account():
    account = {"applicantFullname": "LE THI D", "applicantIdentityNumber": "001160000009"}
    values = {**BASE, "NguoiYeuCau_HoTen": "Le Thi D", "NguoiYeuCau_SoDinhDanh": "001160000009",
              "NguoiYeuCau_QuanHe": "Bà nội"}
    by = _by(_enrich(values, _context("Khác"), account=account)[0])
    assert by[RELATION]["value"] == "Khác" and by["citizenField62"]["value"] == "Bà nội"
    out, warnings = _enrich({**values, "NguoiYeuCau_SoDinhDanh": "001160000000"}, _context("Khác"), account=account)
    assert "citizenField62" not in _by(out) and warnings


def test_dead_parent_skips_residence_with_warning():
    out, warnings = _enrich({**BASE, "Me_DaChet": True}, _context("Khác"), account={})
    assert "citizenMeNoicutru" not in _by(out) and any("mẹ đã chết" in w for w in warnings)


def test_loai_khai_sinh_fallback_when_reason_missing():
    values = {k: v for k, v in BASE.items() if not k.startswith("Cha_")}
    out, _ = _enrich(values, "")
    assert _by(out)["citizenLoaikhaisinh_NgdcKS"]["value"] == "Chưa xác định được cha"


def test_reason_parsing():
    raw = "<con>\nHọ tên: B\n</con>\n<quan_he>\nKết luận: Mẹ\n</quan_he>\n<loai_khai_sinh>\nKết luận: Trẻ bị bỏ rơi"
    ctx = reason._render_context(raw, {"formContext": MOTHER})
    assert reason.labeled_value(reason.section(ctx, "loai_khai_sinh"), "Kết luận") == "Trẻ bị bỏ rơi"
    assert reason._render_context("rỗng", {}) == ""


def test_attach_rows():
    items = build_plan_items(["gcs.pdf", "uq.pdf", "mth.pdf", "br.pdf", "cccd.pdf"],
                             {1: "authorization", 2: "surrogacy_doc", 3: "abandoned_record", 4: "lạ"})
    assert [i["slotName"] for i in items] == [
        ROW_CHUNG_SINH["slotName"], ROWS["authorization"]["slotName"], ROWS["surrogacy_doc"]["slotName"],
        ROWS["abandoned_record"]["slotName"], ROW_CHUNG_SINH["slotName"],
    ]
