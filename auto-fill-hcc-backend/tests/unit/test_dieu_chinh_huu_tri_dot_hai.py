"""Thực hiện trợ cấp hưu trí xã hội — lớp soát thứ hai (thanh tra định danh + địa chỉ) và bản vá điền đợt 2 Form.io.
Dữ liệu giả."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Case, Result
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.process import runner
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.thanh_tra import dia_chi, dot_hai
from app.procedures.registry import PROCEDURES
from app.second_pass.service import capability

_DON = (
    "VĂN BẢN ĐỀ NGHỊ\nI. Thông tin chung\n1. Đối tượng hưởng trợ cấp xã hội, trợ cấp hưu trí xã hội\n"
    "1.1. Họ và tên: Nguyễn Văn Ông\n1.2. Nơi cư trú:\n1.3. Nơi ở hiện nay (Ghi cụ thể): Tổ 1 - Phường Đông Hà - Quận 1\n"
    "2. Thông tin người giám hộ\n2.1. Họ và tên: Nguyễn Văn Con\n2.3. Nơi ở hiện nay (Ghi cụ thể): Tổ 2\n"
    "II. Thông tin đề nghị hưởng trợ cấp xã hội\n"
)


def test_dang_ky_dot_hai_form_formio():
    entry = next(p for p in PROCEDURES if p["key"] == "dieu-chinh-huu-tri-xa-hoi")
    assert capability(entry) == "secondPassFormio"


def test_dia_chi_cat_dong_cua_nguoi_huong_va_nguoi_giam_ho_khi_la_nguoi_nop():
    docs = [{"name": "don.pdf", "text": _DON}]
    lines = dia_chi.lines_of(docs, {"NguoiNop_HoTen": "Nguyễn Văn Con"})
    assert lines["ChuHoSo_NoiCuTru"][0].endswith("Quận 1") and lines["NguoiNop_NoiCuTru"][0].endswith("Tổ 2")
    # Người nộp không phải người ở mục 2 (CCCD riêng) → không soát theo dòng mục 2.
    assert "NguoiNop_NoiCuTru" not in dia_chi.lines_of(docs, {"NguoiNop_HoTen": "Người Khác"})
    # Bên được ủy quyền chính là người ghi ở mục 2 → soát theo dòng mục 2; người khác thì không.
    assert dia_chi.lines_of(docs, {"UyQuyen_HoTen": "Nguyễn Văn Con"})["UyQuyen_NoiCuTru"][0].endswith("Tổ 2")
    assert "UyQuyen_NoiCuTru" not in dia_chi.lines_of(docs, {"UyQuyen_HoTen": "Người Khác"})


def test_dia_chi_chi_tiet_trong_va_xa_ngoai_danh_muc_la_loi_cua_a():
    ours = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Tiên Du", "diaChi": ""}
    reasons = dia_chi.faults(ours, {**ours, "diaChi": "Thôn 1"}, "")
    assert any("chi tiết của A TRỐNG" in reason for reason in reasons)
    # B giữ nguyên xã ngoài danh mục của A → không được nói "ô xã của A sẽ trống" như lỗi B sửa được.
    bad = {**ours, "xa": "Xã Không Có Thật"}
    assert not any("TRỐNG trên cổng" in reason for reason in dia_chi.faults(bad, {**bad, "diaChi": "Thôn 1"}, ""))


def _trang(*pages):
    return dia_chi.trang.pages([{"text": "\n───── Trang 2/9 ─────\n".join(pages)}])


def test_chi_tiet_doc_lech_tren_don_sua_theo_giay_khac():
    don = "VĂN BẢN ĐỀ NGHỊ trợ cấp hưu trí xã hội\n1.2. Nơi cư trú: Thôn Đông Ngạc, phường Tân An"
    giay = "Giấy xác nhận khuyết tật\nNơi ở hiện nay: Tổ dân phố Đông Ngọc, phường Tiên An"
    the = "CĂN CƯỚC\nNơi thường trú / Place of residence: Đông Ngọc, Tiên An"
    fix = dia_chi.detail_fix("Thôn Đông Ngạc", _trang(don, giay, the))
    assert fix["diaChi"] == "Thôn Đông Ngọc"
    # Cách viết của A có trên giấy in → không đoán; chỉ một trang ghi cách khác → không đủ căn cứ.
    assert dia_chi.detail_fix("Thôn Đông Ngạc", _trang(don, giay, the.replace("Ngọc", "Ngạc"))) is None
    assert dia_chi.detail_fix("Thôn Đông Ngạc", _trang(don, giay)) is None
    # Số nhà / tên một chữ không đoán.
    assert dia_chi.detail_fix("Số 12 Đông Ngạc", _trang(don, giay, the)) is None


def test_dia_chi_loi_tinh_tu_suy_do_ma_chi_ra():
    proposed = {"quocGia": "Việt Nam", "tinh": "Quảng Trị", "xa": "Phường Đông Hà", "diaChi": "Tổ 1"}
    ours = {"quocGia": "Việt Nam", "tinh": "TP Hồ Chí Minh", "xa": "Phường Đông Hà", "diaChi": "Tổ 1"}
    assert any("tỉnh" in reason for reason in dia_chi.faults(ours, proposed, _DON))
    assert dia_chi.faults(proposed, proposed, _DON) == []


def _patch(monkeypatch, before: dict, after: dict, options: dict) -> list[dict]:
    async def fake_review(documents, values, opts=None):
        return Result(dict(after), [], {})

    monkeypatch.setattr(dot_hai, "review", fake_review)
    base = dot_hai._ui(before, options)
    return asyncio.run(dot_hai.patch([{"name": "d", "text": ""}], [{"name": k, "value": v} for k, v in before.items()],
                                     base, options))["fields"]


def test_ban_va_chi_ghi_o_phan_quyet_lam_doi(monkeypatch):
    before = {"ChuHoSo_HoTen": "Nguyễn Văn Ông", "ChuHoSo_SoDinhDanh": "001150000111",
              "ChuHoSo_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "TP Hồ Chí Minh", "xa": "Đông Hà", "diaChi": "Tổ 1"}}
    after = {**before, "ChuHoSo_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Quảng Trị", "xa": "Phường Đông Hà",
                                            "diaChi": "Tổ 1"}}
    fields = {f["name"]: f for f in _patch(monkeypatch, before, after, {"submitterMode": "owner_as_submitter"})}
    assert fields["data[province]"]["by"] == "dia_chi" and "Quảng Trị" in fields["data[province]"]["value"]
    assert "data[isOwnerDossierCheck]" not in fields and "data[fullname]" not in fields


def test_phan_quyet_lam_doi_o_tich_thi_khong_va(monkeypatch):
    """Đổi vai người nộp (ô "người nộp là chủ hồ sơ" đổi) → form đang theo trạng thái cũ, không vá gì."""
    before = {"ChuHoSo_HoTen": "Nguyễn Văn Ông", "ChuHoSo_SoDinhDanh": "001150000111"}
    after = {**before, "UyQuyen_HoTen": "Nguyễn Văn Con", "UyQuyen_SoDinhDanh": "001190000222"}
    assert _patch(monkeypatch, before, after, {"submitterMode": "owner_as_submitter"}) == []


def test_runner_bo_khoa_o_nguoi_nop_xa_quay_va_dot_hai(monkeypatch):
    seen = {}

    async def fake_run(files_by_role, **kwargs):
        seen["context"] = await kwargs["context_builder"]([{"name": "don.pdf", "text": _DON}],
                                                          {"counterWard": "HCC Phường Đông Hà"})
        return {"fields": [{"name": "ChuHoSo_HoTen", "comp": "raw", "value": "Nguyễn Văn Ông"}], "ocr_text": _DON}

    monkeypatch.setattr(runner.runner, "run", fake_run)
    res = asyncio.run(runner.run({"doc": []}, {"_secondPass": True, "counterWard": "HCC Phường Đông Hà"}))
    by = {f["name"]: f for f in res["fields"]}
    assert by["data[identityNumber]"] == {"name": "data[identityNumber]", "comp": "dom-expect", "value": "",
                                          "enableInput": True}
    assert "<xa_quay>" in seen["context"] and callable(res.get("_second_pass"))


def test_chi_tiet_bi_cat_bot_lay_ban_day_du_tren_dong():
    assert dia_chi._cut_detail("Tổ dân phố Thị trấn", "Tổ dân phố Thị trấn Hòa", "Phường An")
    # A trọn tên, phần sau là xã / huyện cũ → không nối.
    assert not dia_chi._cut_detail("Tổ dân phố Hòa", "Tổ dân phố Hòa Bình", "Phường An")
    # Phần bị cắt là tên xã → không phải chi tiết.
    assert not dia_chi._cut_detail("Tổ dân phố Thị trấn", "Tổ dân phố Thị trấn Phường An", "Phường An")
    assert not dia_chi._cut_detail("Tổ 1", "Tổ 2 Hòa", "")


_THE = """CĂN CƯỚC CÔNG DÂN
Số / No.: 012050000123
Họ và tên / Full name: NGUYỄN VĂN ANH
Giới tính / Sex: Nam
IDVNM0500001233012050000123<<3
5003150M9912315VNM<<<<<<<<<<<<<<4
NGUYEN<<VAN<ANH<<<<<<<<<<<<<<<<<
"""


def test_ten_doc_sai_han_nhan_the_theo_ngay_sinh_va_so_gan():
    from app.pipelines.dieu_chinh_huu_tri_xa_hoi.thanh_tra import dinh_danh

    docs = [{"text": "VĂN BẢN ĐỀ NGHỊ trợ cấp hưu trí xã hội\n1.1. Họ và tên: Nguyễn Văn Bình"}, {"text": _THE},
            {"text": "Tên chủ tài khoản: Nguyễn Văn Anh"}]
    values = {"ChuHoSo_HoTen": "Nguyễn Văn Bình", "ChuHoSo_SoDinhDanh": "012050000987", "ChuHoSo_NgaySinh": "15/03/1950"}
    out = {f.unit.key: f.values for f in dinh_danh.findings_from(Case(docs, "", values))}
    assert out["chu_ho_so.ho_ten"] == {"ChuHoSo_HoTen": "NGUYỄN VĂN ANH"}
    assert out["chu_ho_so.so_dinh_danh"] == {"ChuHoSo_SoDinhDanh": "012050000123"}
    # Ngày sinh khác → không phải thẻ của người này.
    other = {**values, "ChuHoSo_NgaySinh": "16/03/1950"}
    assert not dinh_danh.findings_from(Case(docs, "", other))
