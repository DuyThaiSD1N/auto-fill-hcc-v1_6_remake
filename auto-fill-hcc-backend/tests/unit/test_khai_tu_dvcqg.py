import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.pipelines.khai_tu_dvcqg.attach.planner import ROW_GIAY_BAO_TU, ROWS, build_plan_items
from app.pipelines.khai_tu_dvcqg.process import mapper, reason
from app.pipelines.khai_tu_dvcqg.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import PROCEDURES

HTML_DIR = Path(__file__).resolve().parents[3] / "html mới"
SNAPSHOTS = {
    "khai-tu": HTML_DIR / "khai tử" / "khai tử html mới.html",
    "khai-sinh-dang-ky-thuong": HTML_DIR / "khai sinh" / "khai sinh html mới.html",
    "trich-luc-ks": HTML_DIR / "trích lụcc" / "trích lục html mới.html",
    "thay-doi-cai-chinh-ho-tich": HTML_DIR / "cải chính" / "cải chính html mới.html",
}
ACCOUNT = {"applicantFullname": "NGUYEN VAN B", "applicantIdentityNumber": "001090000002"}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn")).lower()


def _body(path: Path) -> str:
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", path.read_text(encoding="utf-8"))
    return _fold(re.sub(r"<[^>]+>", " ", html))


def _context(relation="", loai="", gbt="Giấy báo tử"):
    return (
        "<phan_vai_da_xac_dinh>\n<nguoi_mat>\nHọ tên: NGUYEN VAN A\n</nguoi_mat>\n"
        f"<quan_he>\nKết luận: {relation}\n</quan_he>\n"
        f"<loai_dang_ky>\nKết luận: {loai}\nGiấy báo tử: {gbt}\n</loai_dang_ky>\n</phan_vai_da_xac_dinh>"
    )


def _enrich(values: dict, context: str = "", account=ACCOUNT):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    return mapper.enrich(fields, {"formContext": account, "_reasoning_context": context})


def _by(out):
    return {f["name"]: f for f in out}


BASE = {
    "NguoiMat_HoTen": "Nguyen Van A",
    "NguoiMat_SoDinhDanh": "001050000001",
    "NguoiMat_NgaySinh": "1950",
    "NguoiMat_GioiTinh": "Nam",
    "NguoiMat_DanToc": "Kinh",
    "NguoiMat_SoGiayTo": "001050000001",
    "NguoiMat_NgayCap": "02/03/2021",
    "NguoiMat_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Xã Tam Hợp", "diaChi": "Xóm 5"},
    "NguoiMat_NgayMat": (date.today() - timedelta(days=3)).strftime("%d/%m/%Y"),
    "NguoiMat_GioMat": "09:30",
    "NguoiMat_NoiChet": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Xã Tam Hợp", "diaChi": "Tại nhà"},
    "Gbt_Loai": "Giấy báo tử",
    "Gbt_So": "01/UBND-GBT",
    "Gbt_NgayCap": "05/10/2026",
    "Gbt_CoQuanCap": "UBND xã Tam Hợp",
    "NguoiYeuCau_HoTen": "Nguyen Van B",
    "NguoiYeuCau_SoDinhDanh": "001090000002",
    "NguoiYeuCau_QuanHe": "Con",
    "SoLuongBanSao": "2",
}


def test_contract_uses_shared_new_portal_engine():
    assert all(comp.startswith("sjs-") for comp in UI_COMP_BY_NAME.values())
    assert UI_COMP_BY_NAME["citizenNoichet"] == "sjs-radio"
    assert UI_COMP_BY_NAME["citizenNoichet_TrongNuoc"] == "sjs-area"


@pytest.mark.skipif(not all(p.exists() for p in SNAPSHOTS.values()), reason="thiếu snapshot cổng")
def test_detect_text_unique_across_new_portal_forms():
    bodies = {key: _body(path) for key, path in SNAPSHOTS.items()}
    for key in SNAPSHOTS:
        phrases = [_fold(p) for p in next(p for p in PROCEDURES if p["key"] == key)["detect"]["textIncludes"]]
        for page, body in bodies.items():
            assert all(p in body for p in phrases) == (key == page), (key, page)


@pytest.mark.skipif(not SNAPSHOTS["khai-tu"].exists(), reason="thiếu snapshot cổng")
def test_static_ui_keys_exist_in_snapshot():
    data_names = set(re.findall(r'data-name="([A-Za-z0-9_]+?)__\d+"',
                                SNAPSHOTS["khai-tu"].read_text(encoding="utf-8")))
    always = {"citizenmoiquanhe", "citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh",
              "citizenNDKnoicutru", "citizenNoichet", "citizenLoaigiaybaotu", "citizenSoluongbansaonguoiyeucaudenghi",
              "citizenGioitinh_NgdcKT", "citizenField56", "citizenNDKLoaidangky"}
    assert always <= data_names


def test_full_case_order_codes_and_relation():
    out, warnings = _enrich(BASE, _context("Con"))
    names = [f["name"] for f in out]
    by = _by(out)
    assert names[:4] == ["citizenmoiquanhe", "citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh"]
    assert by["citizenmoiquanhe"]["value"] == "Con" and not by["citizenmoiquanhe"].get("default")
    assert all(by[n].get("lookup") for n in names[1:4]) and not by["citizenGioitinh_NgdcKT"].get("lookup")
    assert by["citizenNDK_NgaySinh"]["value"] == "1950"
    assert by["citizenGioitinh_NgdcKT"]["code"] == "1" and by["citizenDantoc_NgdcKT"]["code"] == "01"
    assert by["citizenField19"]["code"] == "2021-03-02"
    assert by["citizenNoicapgiaytotuythan_NgdcKT"]["value"]       # thẻ 12 số → mặc định theo ngày cấp
    assert by["citizenGiomat"]["value"] == "9" and by["citizenPhutmat"]["value"] == "30"
    assert by["citizenNDKLoaidangky"]["code"] == "1"             # chết 3 ngày trước → đúng hạn
    assert names.index("citizenNDKnoicutru") < names.index("citizenNDKTinh_Thtru")
    assert by["citizenNDKXa_Thtru"]["value"] == "Xã Tam Hợp"
    assert by["citizenNoichet_TrongNuoc"]["radio"] == "citizenNoichet"
    assert names.index("citizenNoichet") < names.index("citizenNoichet_TrongNuoc")
    assert by["citizenSogiaybaotu_NgdcKT"]["value"] == "01/UBND-GBT"
    assert by["citizenSoluongbansaonguoiyeucaudenghi"]["value"] == "2"
    assert not warnings


def test_late_and_long_dead_registration():
    late = {**BASE, "NguoiMat_NgayMat": "01/01/2020"}
    assert _by(_enrich(late, _context("Con"))[0])["citizenNDKLoaidangky"]["code"] == "4"
    long_dead = _enrich(late, _context("Con", loai="Đăng ký khai tử cho người chết đã lâu"))[0]
    assert _by(long_dead)["citizenNDKLoaidangky"]["code"] == "5"


def test_relation_from_declaration_only_when_requester_is_account():
    other = {"applicantFullname": "LE THI C", "applicantIdentityNumber": "001190000003"}
    out, warnings = _enrich(BASE, _context(""), account=other)
    assert "citizenmoiquanhe" not in _by(out) and warnings
    out, _ = _enrich(BASE, _context("Cháu nội"), account=other)
    assert _by(out)["citizenmoiquanhe"]["value"] == "Cháu nội" and _by(out)["citizenmoiquanhe"]["default"]


def test_cmnd_issuer_not_defaulted_and_copies_default_zero():
    values = {**BASE, "NguoiMat_SoDinhDanh": "", "NguoiMat_SoGiayTo": "210369831", "NguoiMat_NoiCap": ""}
    values.pop("SoLuongBanSao")
    by = _by(_enrich(values, _context("Con"))[0])
    assert by["citizenLoaiGiaytotuythan_NgdcKT"]["code"] == "2"
    assert "citizenNoicapgiaytotuythan_NgdcKT" not in by
    assert by["citizenSoluongbansaonguoiyeucaudenghi"]["value"] == "0"
    assert by["citizenSoluongbansaonguoiyeucaudenghi"]["default"]


def test_reason_parsing():
    raw = "<nguoi_mat>\nHọ tên: A\n</nguoi_mat>\n<quan_he>\nKết luận: Con\n</quan_he>\n<loai_dang_ky>\nKết luận:"
    ctx = reason._render_context(raw, {"formContext": ACCOUNT})
    assert reason.labeled_value(reason.section(ctx, "quan_he"), "Kết luận") == "Con"
    assert reason._render_context("rỗng", {}) == ""


def test_attach_rows_no_file_dropped():
    items = build_plan_items(["gbt.pdf", "uq.pdf", "bb.pdf", "nc.pdf", "cccd.pdf"],
                             {0: "death_notice", 1: "authorization", 2: "death_event_proof",
                              3: "death_place_proof", 4: "other"})
    assert [i["slotName"] for i in items] == [
        ROW_GIAY_BAO_TU["slotName"], ROWS["authorization"]["slotName"], ROWS["death_event_proof"]["slotName"],
        ROWS["death_place_proof"]["slotName"], ROW_GIAY_BAO_TU["slotName"],
    ]
    assert all(i["target"] == "fixed-slot" for i in items)


def test_attach_plan_shrinks_files_over_2mb(monkeypatch):
    """Cổng chỉ nhận < 2 MB: tệp > 2 MB trả bản nén ở replaceFiles, tệp nhỏ để nguyên."""
    import asyncio
    import base64
    import io

    import pymupdf
    from PIL import Image

    from app.pipelines.khai_tu_dvcqg.attach import planner as attach_planner
    from app.process.schemas import FileItem
    from app.services import ocr

    def data_url(raw: bytes) -> str:
        return "data:application/pdf;base64," + base64.b64encode(raw).decode()

    big = pymupdf.open()
    for seed in range(3):  # nền nhiễu giả lập bản scan màu 200 dpi
        buf = io.BytesIO()
        Image.effect_noise((1650, 2330), 40 + seed).convert("RGB").save(buf, "JPEG", quality=92)
        page = big.new_page(width=595, height=842)
        page.insert_image(page.rect, stream=buf.getvalue())
    small = pymupdf.open()
    small.new_page()

    async def fake_ocr(files):
        return [{"text": ""} for _ in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)

    files = [
        FileItem(name="nho.pdf", type="application/pdf", role="doc", dataUrl=data_url(small.tobytes())),
        FileItem(name="lon.pdf", type="application/pdf", role="doc", dataUrl=data_url(big.tobytes())),
    ]
    result = asyncio.run(attach_planner.plan(files))
    assert list(result["replaceFiles"]) == ["1"]
    shrunk = result["replaceFiles"]["1"]
    assert shrunk["bytes"] <= 1_900_000 < 2_000_000 < shrunk["originalBytes"]
    assert [a["slotName"] for a in result["attachments"]] == [ROW_GIAY_BAO_TU["slotName"]] * 2
    assert result["extracted"]["shrunk"][0]["fileName"] == "lon.pdf"
    assert not result["errors"]
