"""Đăng ký lại khai sinh: có giấy ủy quyền thì người yêu cầu là bên được ủy quyền, kể cả khi có tờ khai."""
from app.pipelines.khai_sinh_dang_ky_lai.process import mapper

_FIELDS = {
    "Requester_SourceDocumentTitle": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
    "Requester_RelationToSubject": "Bản thân",
    "Requester_FullName": "TRẦN VĂN AN",
    "Requester_IdNumber": "001071000001",
    "Authorized_SourceDocumentTitle": "GIẤY ỦY QUYỀN",
    "Authorized_FullName": "Lê Văn Bình",
    "Authorized_IdNumber": "001056000002",
    "Subject_FullName": "TRẦN VĂN AN",
    "Subject_IdNumber": "001071000001",
}
_CONTEXT = ("<nguoi_duoc_uy_quyen>\nHọ tên: {ten}\nSố CCCD/CMND: {so}\n</nguoi_duoc_uy_quyen>\n"
            "<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: {co}\n</to_khai_dang_ky_lai>")


def _run(fields, has_declaration, authorized=("Lê Văn Bình", "001056000002")):
    context = _CONTEXT.format(ten=authorized[0], so=authorized[1], co="Có" if has_declaration else "Không")
    out = mapper.enrich([{"name": k, "value": v} for k, v in fields.items()], {"_reasoning_context": context})
    return {f["name"]: f["value"] for f in out}


def test_co_to_khai_va_giay_uy_quyen_nguoi_yeu_cau_la_ben_duoc_uy_quyen():
    v = _run(_FIELDS, True)
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("Khac", "LÊ VĂN BÌNH", "001056000002")


def test_co_to_khai_ben_duoc_uy_quyen_la_me_thi_tich_me_de():
    fields = {
        **_FIELDS,
        "Authorized_FullName": "Nguyễn Thị Hoa",
        "Authorized_IdNumber": "001160000003",
        "Mother_FullName": "Nguyễn Thị Hoa",
        "Mother_IdNumber": "001160000003",
    }
    v = _run(fields, True, ("Nguyễn Thị Hoa", "001160000003"))
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("MeDe", "NGUYỄN THỊ HOA", "001160000003")


def test_co_to_khai_khong_co_giay_uy_quyen_nguoi_yeu_cau_theo_to_khai():
    fields = {k: v for k, v in _FIELDS.items() if not k.startswith("Authorized_")}
    out = mapper.enrich(
        [{"name": k, "value": v} for k, v in fields.items()],
        {"_reasoning_context": "<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: Có\n</to_khai_dang_ky_lai>"},
    )
    v = {f["name"]: f["value"] for f in out}
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("BanThan", "TRẦN VĂN AN", "001071000001")


def test_khong_co_to_khai_thi_nguoi_yeu_cau_la_ben_duoc_uy_quyen():
    fields = {k: v for k, v in _FIELDS.items() if not k.startswith("Requester_")}
    v = _run(fields, False)
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("Khac", "LÊ VĂN BÌNH", "001056000002")
