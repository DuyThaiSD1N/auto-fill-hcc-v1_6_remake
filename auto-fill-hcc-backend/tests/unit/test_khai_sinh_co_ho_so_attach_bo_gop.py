"""Đăng ký khai sinh cho người đã có hồ sơ: file gộp nhiều giấy tờ không bị đặt tên như một tấm CCCD."""
import asyncio
import json

from app.pipelines.khai_sinh_co_ho_so import attach
from app.pipelines.khai_sinh_co_ho_so.attach import planner, prompt
from app.process.schemas import FileItem
from app.services import ocr

_BUNDLE = "\n".join(
    f"───── Trang {i}/8 ─────\n{body}" for i, body in enumerate(
        ["CĂN CƯỚC Họ, chữ đệm và tên khai sinh / Full name: PHẠM THỊ AN Ngày, tháng, năm sinh: 01/01/1960 " + "x" * 600,
         "CHỨNG NHẬN KẾT HÔN", "CĂN CƯỚC CÔNG DÂN VÕ VĂN B", "CĂN CƯỚC CÔNG DÂN PHẠM C",
         "CĂN CƯỚC CÔNG DÂN NGUYỄN THỊ D", "CHỨNG NHẬN KẾT HÔN", "CĂN CƯỚC", "MRZ"], start=1))


def test_rut_gon_giu_dau_moi_trang():
    short = prompt._truncate_text(_BUNDLE, limit=1600)
    assert all(f"Trang {i}/8" in short for i in range(1, 9))
    assert "NGUYỄN THỊ D" in short


def test_bo_gop_khong_gan_ten_nguoi(monkeypatch):
    async def fake_ocr(files, *_a, **_k):
        return [{"name": f["name"], "text": _BUNDLE} for f in files]

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [{"index": 0, "type": "personal_document", "title": "Hồ sơ giấy tờ cá nhân"}]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    res = asyncio.run(attach.plan([FileItem(name="ho-so.pdf", type="application/pdf", dataUrl="data:,", role="")], {}))
    assert res["attachments"][0]["documentName"] == "Hồ sơ giấy tờ cá nhân"


# ---- Bước điền (process/mapper): người nộp hộ kèm CCCD của tài khoản, loại khai sinh, xoá ô cha/mẹ trống ----

from app.pipelines.khai_sinh_co_ho_so.process import mapper  # noqa: E402
from app.pipelines.khai_sinh_co_ho_so.process import reason as co_ho_so_reason  # noqa: E402

_ACCOUNT = {"formContext": {"applicantFullname": "LÊ VĂN NỘP", "applicantIdentityNumber": "001204000003"}}
_HO_SO = {
    "Subject_FullName": "TRẦN VĂN CON", "Subject_BirthDate": "15/10/2026", "Subject_Gender": "Nam",
    "Father_FullName": "TRẦN VĂN CHA", "Father_IdNumber": "024091000002", "Father_IdIssueDate": "20/12/2024",
    "Father_BirthDateOrYear": "29/11/1991", "Father_Ethnicity": "Kinh",
    "Mother_FullName": "HOÀNG THỊ MẸ", "Mother_BirthDateOrYear": "21/09/2000", "Mother_Ethnicity": "Kinh",
}
_THE_TAI_KHOAN = {
    "AccountCard_IdNumber": "001204000003", "AccountCard_FullName": "LÊ VĂN NỘP",
    "AccountCard_IdIssueDate": "10/04/2021",
    "AccountCard_ResidenceDomestic": {"quocGia": "Việt Nam", "tinh": "Lào Cai", "xa": "Phường Yên Bái",
                                      "diaChi": "Tổ 1"},
}


def _enrich(values, options=None):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    return {f["name"]: f for f in mapper.enrich(fields, options)}


def test_loai_khai_sinh_la_x_select_va_theo_cha_me():
    out = _enrich(_HO_SO)
    assert out["nksLoaiKhaiSinh"]["comp"] == "x-select"
    assert out["nksLoaiKhaiSinh"]["value"] == "Đã xác định được cả cha lẫn mẹ"
    khong_cha = {k: v for k, v in _HO_SO.items() if not k.startswith("Father_")}
    assert _enrich(khong_cha)["nksLoaiKhaiSinh"]["value"] == "Chưa xác định được cha"


def test_cccd_tai_khoan_dien_noi_cu_tru_muc_i_giu_nhan_than_vneid():
    out = _enrich({**_HO_SO, **_THE_TAI_KHOAN}, _ACCOUNT)
    assert out["QuanHe"]["value"] == "Khac" and not out["QuanHe"].get("default")
    assert out["nycLoaiCuTru"]["value"] == "Thường trú"
    assert out["nycNoiCuTru"]["value"] == "1"
    assert out["nycNoiCuTru_TrongNuoc"]["value"]["diaChi"] == "Tổ 1"
    # Họ tên/số/ngày cấp/nơi cấp: cổng đã đổ từ VNeID của chính người này → không ghi đè bằng OCR.
    assert not {"HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC"} & set(out)


def test_cccd_khong_trung_so_tai_khoan_khong_dien_muc_i():
    lech = {**_THE_TAI_KHOAN, "AccountCard_IdNumber": "001204999999"}
    out = _enrich({**_HO_SO, **lech}, _ACCOUNT)
    assert out["QuanHe"]["value"] == "Khac" and out["QuanHe"].get("default")
    assert "nycNoiCuTru_TrongNuoc" not in out
    assert "nycNoiCuTru_TrongNuoc" not in _enrich({**_HO_SO, **_THE_TAI_KHOAN})


def test_cccd_tai_khoan_trung_cha_tich_cha():
    the_cha = {**_THE_TAI_KHOAN, "AccountCard_IdNumber": "024091000002"}
    account = {"formContext": {"applicantFullname": "TRẦN VĂN CHA", "applicantIdentityNumber": "024091000002"}}
    assert _enrich({**_HO_SO, **the_cha}, account)["QuanHe"]["value"] == "ChaDe"


def test_cha_me_thieu_truong_thi_xoa_trang():
    out = _enrich(_HO_SO)
    for name in ("SoDinhDanhMe", "SoGiayToDinhDanhMe", "NgayCapDDMe", "NoiCapDDMe"):
        assert out[name]["clear"] is True and out[name]["value"] == ""
    assert out["HoTenMeKS"]["value"] == "HOÀNG THỊ MẸ" and not out["HoTenMeKS"].get("clear")
    # Cha có thẻ: ô nào có dữ liệu thì điền, nơi cấp suy mặc định theo ngày cấp → không bị xoá.
    assert out["SoDinhDanhCha"]["value"] == "024091000002"
    assert not out["NoiCapDDCha"].get("clear")
    assert not any(f.get("clear") for n, f in out.items() if n.endswith("Cha") or n.endswith("ChaKS"))


def test_context_ghim_so_dinh_danh_tai_khoan():
    raw = "<con>\nHọ tên: TRẦN VĂN CON\nNgày sinh: 15/10/2026\nGiới tính: Nam\n</con>"
    docs = [{"name": "ks.pdf", "text": "GIẤY KHAI SINH\nHọ, chữ đệm, tên: TRẦN VĂN CON"}]
    context = co_ho_so_reason._render_context(raw, _ACCOUNT, docs)
    assert "<tai_khoan_dang_nhap>" in context and "001204000003" in context
    assert "<tai_khoan_dang_nhap>" not in co_ho_so_reason._render_context(raw, {}, docs)
