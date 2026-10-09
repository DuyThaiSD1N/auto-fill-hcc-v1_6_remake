"""Đăng ký lại khai sinh: có tờ khai thì người yêu cầu theo tờ khai; giấy ủy quyền chỉ dùng khi không có tờ khai."""
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
_CONTEXT = ("<nguoi_duoc_uy_quyen>\nHọ tên: Lê Văn Bình\nSố CCCD/CMND: 001056000002\n</nguoi_duoc_uy_quyen>\n"
            "<to_khai_dang_ky_lai>\nCó tờ khai đăng ký lại khai sinh: {co}\n</to_khai_dang_ky_lai>")


def _run(fields, has_declaration):
    out = mapper.enrich([{"name": k, "value": v} for k, v in fields.items()],
                        {"_reasoning_context": _CONTEXT.format(co="Có" if has_declaration else "Không")})
    return {f["name"]: f["value"] for f in out}


def test_co_to_khai_va_giay_uy_quyen_nguoi_yeu_cau_theo_to_khai():
    v = _run(_FIELDS, True)
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("BanThan", "TRẦN VĂN AN", "001071000001")


def test_khong_co_to_khai_thi_nguoi_yeu_cau_la_ben_duoc_uy_quyen():
    fields = {k: v for k, v in _FIELDS.items() if not k.startswith("Requester_")}
    v = _run(fields, False)
    assert (v["QuanHe"], v["HoVaTenC"], v["SoDinhDanhC"]) == ("Khac", "LÊ VĂN BÌNH", "001056000002")
