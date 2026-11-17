"""Xác định mức độ khuyết tật — lớp soát thứ hai (thanh tra định danh + địa chỉ) và bản vá điền đợt 2 trên form Form.io.
Dữ liệu giả."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Case, Result
from app.pipelines.khuyet_tat import thanh_tra
from app.pipelines.khuyet_tat.process import runner
from app.pipelines.khuyet_tat.thanh_tra import dinh_danh, dot_hai, trang
from app.procedures.registry import PROCEDURES
from app.second_pass.service import capability

_DON = ("ĐƠN ĐỀ NGHỊ XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT\n"
        "I. Thông tin người được xác định mức độ khuyết tật\nHọ và tên: Nguyễn Văn Con\n"
        "II. Thông tin người đại diện hợp pháp\nHọ và tên: Nguyễn Văn Cha\n"
        "- Mối quan hệ với người được xác định khuyết tật: con\n")
_THE = ("CĂN CƯỚC CÔNG DÂN\nSố / No.: 001080000002\n"
        "IDVNM0800000020001080000002<<1\n8004031M2504035VNM<<<<<<<<<<<0\nNGUYEN<<VAN<CHA")


def test_dang_ky_dot_hai_form_formio():
    entry = next(p for p in PROCEDURES if p["key"] == "xac-dinh-muc-do-khuyet-tat")
    assert entry["secondPass"] == "formio"
    assert capability(entry) == "secondPassFormio"


def test_quan_he_theo_chu_tren_don_khi_luot_trich_dao_chieu():
    pages = trang.pages([{"name": "don.pdf", "text": _DON}])
    finding = dinh_danh.relation_finding({"Ndd_QuanHe": "Cha"}, pages)
    assert finding and finding.values == {"Ndd_QuanHe": "con"}
    assert dinh_danh.relation_finding({"Ndd_QuanHe": "Con trai"}, pages) is None
    # Sau nhãn chỉ có dấu chấm → không có căn cứ.
    blank = trang.pages([{"name": "don.pdf", "text": _DON.replace(": con", ": ....")}])
    assert dinh_danh.relation_finding({"Ndd_QuanHe": "Mẹ"}, blank) is None


def test_so_ngay_sinh_nguoi_dai_dien_theo_mrz_the_cua_chinh_nguoi_do():
    values = {"Ndd_HoTen": "Nguyễn Văn Cha", "Ndd_SoDinhDanh": "001080000092", "Ndd_NgaySinh": "03/04/1981"}
    docs = [{"name": "the.jpg", "text": _THE + "\nNgày sinh: 03/04/1980"}]
    found = {f.unit.key: f.values for f in dinh_danh.card_findings(dinh_danh.NDD, values, docs)}
    assert found["ndd.so_dinh_danh"] == {"Ndd_SoDinhDanh": "001080000002"}
    assert found["ndd.ngay_sinh"] == {"Ndd_NgaySinh": "03/04/1980"}
    # Thẻ trùng họ tên mà số lệch xa VÀ năm sinh khác → thẻ của người khác (mẹ / con trùng tên), không lấy.
    other = {**values, "Ndd_SoDinhDanh": "001224003781", "Ndd_NgaySinh": "26/02/2024"}
    assert dinh_danh.card_findings(dinh_danh.NDD, other, docs) == []


def test_chep_gia_tri_da_sua_sang_khoi_chu_ho_so_va_nguoi_nop_cung_nguoi():
    before = {"Nkt_HoTen": "Nguyễn Văn Côn", "ChuHoSo_HoTen": "Nguyễn Văn Côn",
              "Ndd_SoDinhDanh": "001080000092", "NguoiNop_SoDinhDanh": "001080000092"}
    after = {**before, "Nkt_HoTen": "NGUYỄN VĂN CON", "Ndd_SoDinhDanh": "001080000002"}
    out = thanh_tra.sync(before, after)
    assert out["ChuHoSo_HoTen"] == "NGUYỄN VĂN CON"
    assert out["NguoiNop_SoDinhDanh"] == "001080000002"
    # Khối chủ hồ sơ đọc từ nguồn riêng, khác giá trị người khuyết tật → không đè.
    out = thanh_tra.sync({**before, "ChuHoSo_HoTen": "Nguyễn Văn Khác"}, {**after, "ChuHoSo_HoTen": "Nguyễn Văn Khác"})
    assert out["ChuHoSo_HoTen"] == "Nguyễn Văn Khác"


def _patch(monkeypatch, before: dict, after: dict, options: dict) -> list[dict]:
    async def fake_review(documents, values, opts=None):
        return Result(dict(after), [], {})

    monkeypatch.setattr(dot_hai, "review", fake_review)
    raw = [{"name": k, "value": v} for k, v in before.items()]
    base = dot_hai._ui(before, options)
    return asyncio.run(dot_hai.patch([{"name": "d", "text": ""}], raw, base, options))["fields"]


_MUC_I = {"Nkt_HoTen": "Nguyễn Văn Com", "Nkt_SoDinhDanh": "001220000001", "Nkt_NgaySinh": "01/02/2020",
          "Nkt_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Hải Châu", "diaChi": "Tổ 1"}}
_MUC_II = {"Ndd_HoTen": "Nguyễn Văn Cha", "Ndd_SoDinhDanh": "001080000002", "Ndd_QuanHe": "Cha"}
_TK_CHA = {"formContext": {"applicantFullname": "NGUYỄN VĂN CHA", "applicantIdentityNumber": "001080000002"}}


def test_ban_va_chi_ghi_o_phan_quyet_lam_doi_va_khong_doi_o_chu_ho_so(monkeypatch):
    before = {**_MUC_I, **_MUC_II}
    after = thanh_tra.sync(before, {**before, "Nkt_HoTen": "Nguyễn Văn Con", "Ndd_QuanHe": "con"})
    fields = {f["name"]: f for f in _patch(monkeypatch, before, after, _TK_CHA)}
    assert fields["data[NktHoTen]"]["value"] == "NGUYỄN VĂN CON" and fields["data[NktHoTen]"]["by"] == "dinh_danh"
    assert fields["data[ownerFullname]"]["value"] == "NGUYỄN VĂN CON"
    assert fields["data[NddQuanheNkt]"]["value"] == "Con"
    assert "data[isOwnerDossierCheck]" not in fields and "data[NktSoDinhdanh]" not in fields


def test_phan_quyet_lam_doi_o_nguoi_nop_la_chu_ho_so_thi_khong_va_khoi_chu_ho_so(monkeypatch):
    """Tài khoản là người khuyết tật: lượt đầu không nhận ra (lệch cả tên lẫn số) nên bỏ tích; phán quyết sửa đúng tên + số
    thì ô tích sẽ đổi — đợt 2 không đổi ô tích, nên không vá khối chủ hồ sơ / người nộp đang theo trạng thái cũ."""
    tk_con = {"formContext": {"applicantFullname": "NGUYỄN VĂN CON", "applicantIdentityNumber": "001220000001"}}
    before = {**_MUC_I, "Nkt_SoDinhDanh": "001220000081"}
    after = thanh_tra.sync(before, {**before, "Nkt_HoTen": "Nguyễn Văn Con", "Nkt_SoDinhDanh": "001220000001"})
    fields = {f["name"] for f in _patch(monkeypatch, before, after, tk_con)}
    assert "data[NktHoTen]" in fields
    assert not fields & {"data[ownerFullname]", "data[ownerIdentityNumber]", "data[isOwnerDossierCheck]"}


def test_runner_chi_tra_dot_hai_khi_extension_khai_biet(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        await kwargs["context_builder"]([{"name": "don.pdf", "text": _DON}], {})
        return {"fields": [{"name": k, "comp": "raw", "value": v} for k, v in {**_MUC_I, **_MUC_II}.items()],
                "ocr_text": _DON}

    async def no_vision(files):
        return None

    async def no_levels(documents):
        return None

    monkeypatch.setattr(runner.runner, "run", fake_run)
    monkeypatch.setattr(runner.vision, "read_section_iii", no_vision)
    monkeypatch.setattr(runner.muc_do, "read_activity_levels", no_levels)
    res = asyncio.run(runner.run({"doc": []}, {"_secondPass": True}))
    assert callable(res.get("_second_pass"))
    res = asyncio.run(runner.run({"doc": []}, {}))
    assert "_second_pass" not in res


def test_ho_so_khong_co_the_chi_soat_quan_he():
    found = dinh_danh.findings_from(Case([{"name": "don.pdf", "text": _DON}], "", {**_MUC_I, **_MUC_II}, {}))
    assert [f.unit.key for f in found] == ["ndd.quan_he"]


_DON_DIA_CHI = (
    "ĐƠN ĐỀ NGHỊ XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT\n"
    "I. Thông tin người được xác định mức độ khuyết tật\n- Họ và tên: Nguyễn Văn Con\n"
    "- Nơi ở hiện nay: Tổ 1 - Phường Đông Hà - Quận 1\n"
    "II. Thông tin người đại diện hợp pháp\n- Họ và tên: Nguyễn Văn Cha\n"
    "- Hộ khẩu thường trú: Tổ 2\n"
    "III. Thông tin về tình trạng khuyết tật\n"
)


def test_dia_chi_cat_dung_dong_cua_tung_o_tren_don():
    from app.pipelines.khuyet_tat.thanh_tra import dia_chi

    lines = dia_chi.lines_of([{"name": "don.pdf", "text": _DON_DIA_CHI}])
    assert lines["Nkt_NoiOHienNay"][0].endswith("Quận 1") and lines["Ndd_NoiCuTru"][0].endswith("Tổ 2")
    assert "Nkt_ThuongTru" not in lines


def test_dia_chi_khong_bia_tinh_va_loi_cua_luot_trich_do_ma_chi_ra():
    """Dòng không ghi tỉnh: tỉnh model ghi bị bỏ, lấy tỉnh duy nhất có xã đó. Lượt trích bị đem ra toà khi tỉnh / xã của nó
    không có trên giấy nào (tỉnh tự suy từ "Quận 1", xã khớp gần sang tên khác)."""
    from app.pipelines.khuyet_tat.thanh_tra import dia_chi

    line = "- Nơi ở hiện nay: Tổ 1 - Phường Đông Hà - Quận 1"
    got = dia_chi.check("Nkt_NoiOHienNay", {"tinh": "TP Hồ Chí Minh", "xa": "Phường Đông Hà", "chiTietDuoiXa": "Tổ 1"},
                        line, None)
    assert (got["tinh"], got["xa"], got["diaChi"]) == ("Quảng Trị", "Phường Đông Hà", "Tổ 1")
    # Chi tiết không có trên dòng → không nhận.
    assert dia_chi.check("Nkt_NoiOHienNay", {"xa": "Phường Đông Hà", "chiTietDuoiXa": "Tổ 9"}, line, None) is None
    ours = {"quocGia": "Việt Nam", "tinh": "TP Hồ Chí Minh", "xa": "Phường Đông Hà", "diaChi": "Tổ 1"}
    reasons = dia_chi.faults(ours, got, _DON_DIA_CHI)
    assert any("tỉnh" in r for r in reasons) and any("xã" in r for r in reasons)
    # Lượt trích đã đúng tỉnh / xã có trên giấy → không có lỗi để đem ra toà.
    assert dia_chi.faults(got, got, _DON_DIA_CHI) == []
