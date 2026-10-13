"""Đăng ký nội quy lao động của doanh nghiệp (Bộ Nội vụ, 2.001955)."""

from app.pipelines.dang_ky_noi_quy_lao_dong.attach import planner
from app.pipelines.dang_ky_noi_quy_lao_dong.process import mapper
from app.pipelines.dang_ky_noi_quy_lao_dong.process.runner import find_submitter_mention, trim_rule_pages
from app.pipelines.dang_ky_noi_quy_lao_dong.process.schema import UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "dang-ky-noi-quy-lao-dong"
_NGUOI_NOP = {"formContext": {"applicantFullname": "Trần Văn Bình", "applicantIdentityNumber": "001090000002"}}
_DAI_DIEN = {"formContext": {"applicantFullname": "Lê Thị Mẫu", "applicantIdentityNumber": "001175000003"}}


def _values(**overrides):
    values = {
        "DoanhNghiep_Ten": "Công ty TNHH Mẫu Xanh",
        "DoanhNghiep_MaSo": "0100000001",
        "DoanhNghiep_DiaChi": {"tinh": "Thành phố Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 1 phố Mẫu"},
        "DoanhNghiep_DienThoai": "024.3000.0001",
        "DaiDien_HoTen": "Bà Lê Thị Mẫu",
        "DaiDien_SoDinhDanh": "001175000003",
        "DaiDien_NgayCap": "01/02/2022",
        "DaiDien_NoiCap": "Cục Cảnh sát QLHC về TTXH",
        "NguoiNop_HoTen": "Trần Văn Bình",
        "NguoiNop_SoDinhDanh": "001090000002",
        "NguoiNop_NgayCap": "ngày 03 tháng 4 năm 2021",
        "NguoiNop_NoiCap": "Cục Cảnh sát QLHC về TTXH",
        "QuyetDinh_So": "12/QĐ-MX",
        "QuyetDinh_Ngay": "05/08/2026",
        "DanhMucHoSo": [
            "Văn bản đề nghị đăng ký nội quy lao động – Số: 34/MX-TCNS",
            "1. Quyết định ban hành Nội quy lao động – Số: 12/QĐ-MX",
            "Nội quy lao động",
            "CCCD của người được ủy quyền",
        ],
    }
    values.update(overrides)
    return values


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return fields, {f["name"]: f for f in fields}, warnings


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.001955"
    assert link["url"].endswith("019d2bfb-42a2-76ce-9565-812f8b562c71")
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    assert proc["hasAttachmentStep"] is True and proc["detect"]["textPriority"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    # Tên package trùng key để tra.
    assert planner.__name__.split(".")[2] == KEY.replace("-", "_")


def test_nop_thay_chu_ho_so_la_doanh_nghiep():
    ordered, fields, warnings = _run(_values(), _NGUOI_NOP)
    # Ô cổng khoá theo tài khoản không bao giờ phát.
    for locked in ("data[fullname]", "data[birthday]", "data[identityNumber]", "data[chonDoiTuong]"):
        assert locked not in fields
    assert fields["data[identityDate]"]["value"] == "03/04/2021"
    assert fields["data[idIssuePlace]"]["value"]
    assert fields["data[gender]"]["value"] == "Nam", "suy từ số định danh tài khoản khi giấy tờ không ghi"
    # Chủ hồ sơ = doanh nghiệp, khác người nộp.
    assert fields["data[isOwnerDossierCheck]"]["value"] is False
    assert fields["data[chonDoiTuong1]"]["value"] == "Tổ chức/Doanh nghiệp"
    assert fields["data[ownerOrganizationFullname]"]["value"] == "CÔNG TY TNHH MẪU XANH"
    assert fields["data[ownerTaxCode]"]["value"] == "0100000001"
    assert fields["data[ownerFullname]"]["value"] == "LÊ THỊ MẪU"
    assert fields["data[ownerIdentityNumber]"]["value"] == "001175000003"
    assert fields["data[ownerGender]"]["value"] == "Nữ"
    assert fields["data[ownerIdentityDate]"]["value"] == "01/02/2022"
    assert fields["data[ownerProvince]"]["value"] == "Thành phố Hà Nội"
    assert fields["data[ownerDistrict]"]["value"] == "Phường Hoàn Kiếm"
    assert fields["data[ownerAddress]"]["value"] == "Số 1 phố Mẫu"
    assert fields["data[ownerNation]"]["value"] == "Việt Nam"
    assert fields["data[ghiChu]"]["value"] == (
        "Đăng ký Nội quy lao động ban hành theo Quyết định số 12/QĐ-MX ngày 05/08/2026")
    # Datagrid: bỏ số thứ tự đầu dòng và CCCD.
    assert fields["data[hoSoDinhKem][1][textField1]"]["value"].startswith("Quyết định ban hành")
    assert fields["data[hoSoDinhKem][2][textField2]"]["value"] == "Bản chính"
    assert "data[hoSoDinhKem][3][textField1]" not in fields
    # Loại chủ hồ sơ phải chọn TRƯỚC thì ô tên tổ chức mới hiện.
    names = [f["name"] for f in ordered]
    assert names.index("data[chonDoiTuong1]") < names.index("data[ownerOrganizationFullname]")
    assert all(f["comp"] == UI_COMP_BY_NAME[f["name"]] for f in ordered)
    assert any("số cố định" in w for w in warnings)
    assert any("ngày sinh" in w for w in warnings)


def test_nguoi_dai_dien_tu_nop_lay_nhan_than_dai_dien_cho_phan_i():
    _, fields, _ = _run(_values(NguoiNop_HoTen=None, NguoiNop_SoDinhDanh=None, NguoiNop_NgayCap=None,
                                NguoiNop_NoiCap=None), _DAI_DIEN)
    assert fields["data[identityDate]"]["value"] == "01/02/2022"
    assert fields["data[gender]"]["value"] == "Nữ"
    # Địa chỉ trụ sở KHÔNG phải nơi cư trú của người nộp.
    assert "data[province]" not in fields
    assert fields["data[isOwnerDossierCheck]"]["value"] is False
    assert fields["data[ownerFullname]"]["value"] == "LÊ THỊ MẪU"


def test_khong_co_tai_khoan_thi_khong_dien_phan_i():
    _, fields, warnings = _run(_values())
    assert not any(name in fields for name in ("data[identityDate]", "data[idIssuePlace]", "data[gender]"))
    assert fields["data[ownerOrganizationFullname]"]["value"] == "CÔNG TY TNHH MẪU XANH"
    assert any("tài khoản đang đăng nhập" in w for w in warnings)


def test_giay_to_khong_khop_tai_khoan_khong_dien_phan_i():
    other = {"formContext": {"applicantFullname": "Phạm Văn Khác", "applicantIdentityNumber": "001090000009"}}
    _, fields, warnings = _run(_values(), other)
    assert "data[identityDate]" not in fields
    assert any("khớp người nộp" in w for w in warnings)


def _paged(*pages):
    return "\n".join(f"Trang {i}/{len(pages)}\n{text}" for i, text in enumerate(pages, start=1))


def test_trim_bo_toan_van_noi_quy_giu_giay_to_khac():
    text = _paged(
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nQUYẾT ĐỊNH Về việc ban hành Nội quy lao động\nCăn cứ Bộ luật Lao động",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nSố: 34/MX-TCNS V/v đăng ký Nội quy lao động\nKính gửi: Sở Nội vụ",
        "CÔNG TY TNHH MẪU XANH\nNỘI QUY LAO ĐỘNG\n(Ban hành kèm theo Quyết định số 12/QĐ-MX)\nChương I NHỮNG QUY ĐỊNH CHUNG",
        "Điều 30. Người vi phạm bị lập biên bản; quyết định xử lý kỷ luật do Giám đốc ban hành.",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY ỦY QUYỀN\nBên ủy quyền (Bên A)",
    )
    out = trim_rule_pages([{"text": text}])[0]["text"]
    assert "Về việc ban hành Nội quy" in out
    assert "V/v đăng ký" in out
    assert "NỘI QUY LAO ĐỘNG" in out, "giữ trang tiêu đề để LLM biết hồ sơ có Nội quy"
    assert "Điều 30" not in out
    assert "GIẤY ỦY QUYỀN" in out


def _segment(page_from, page_to, doc_type, name=""):
    return {"fileIndex": 0, "pageFrom": page_from, "pageTo": page_to, "type": doc_type, "documentName": name}


def test_plan_ghep_quyet_dinh_va_noi_quy_vao_dong_1_uy_quyen_qua_modal():
    raw_files = [{"name": "ho-so.pdf", "type": "application/pdf", "dataUrl": ""}]
    segments = [
        _segment(1, 4, "gop_y_dai_dien", "Biên bản hội nghị đối thoại"),
        _segment(5, 6, "giay_uy_quyen", "Giấy ủy quyền"),
        _segment(7, 7, "quyet_dinh_ban_hanh", "Quyết định ban hành NQLĐ"),
        _segment(8, 9, "van_ban_de_nghi", "Văn bản đề nghị đăng ký"),
        _segment(10, 39, "noi_quy_lao_dong", "Nội quy lao động"),
        _segment(40, 40, "cccd"),
    ]
    file_meta = {0: {"pageCount": 40, "pageBoundariesAvailable": True}}
    attachments, classified, warnings = planner.build_plan_items(raw_files, segments, file_meta, {0: {}})
    by_row = {a.get("componentIndex"): a for a in attachments if a["target"] == "attp-row"}
    assert sorted(by_row) == [1, 2, 4]
    row1 = by_row[1]
    assert row1["includedTypes"] == ["quyet_dinh_ban_hanh", "noi_quy_lao_dong"], "Quyết định đứng trước Nội quy"
    assert [s["pageIndexes"][0] for s in row1["sourceSegments"]] == [6, 9]
    assert row1["loaiBan"] == "Bản chính"
    dialog = next(a for a in attachments if a["target"] == "add-document-dialog")
    assert dialog["componentName"] == "Giấy ủy quyền"
    assert dialog["fallbackComponentName"] == by_row[4]["componentName"]
    assert dialog["quantity"] == 1 and dialog["needsAddComponent"] is True
    assert any(c["type"] == "cccd" and c["target"] == "skip" for c in classified)
    assert not warnings, "dòng 3 (nếu có) để trống không phải lỗi"


def test_plan_thieu_giay_bat_buoc_thi_canh_bao():
    raw_files = [{"name": "noi-quy.pdf", "type": "application/pdf", "dataUrl": ""}]
    file_meta = {0: {"pageCount": 5, "pageBoundariesAvailable": True}}
    attachments, _, warnings = planner.build_plan_items(
        raw_files, [_segment(1, 5, "noi_quy_lao_dong")], file_meta, {0: {}})
    assert [a["componentIndex"] for a in attachments] == [1]
    text = " ".join(warnings)
    assert "dòng 4" in text and "dòng 2" in text and "Quyết định ban hành" in text


def test_rule_type_va_normalize():
    assert planner._rule_type("CỘNG HÒA XÃ HỘI\nGIẤY ỦY QUYỀN\nBên ủy quyền") == "giay_uy_quyen"
    assert planner._rule_type("QUYẾT ĐỊNH Về việc ban hành Nội quy lao động") == "quyet_dinh_ban_hanh"
    assert planner._rule_type("NỘI QUY LAO ĐỘNG (Ban hành kèm theo Quyết định số 1/QĐ)") == "noi_quy_lao_dong"
    assert planner._rule_type("V/v đăng ký nội quy lao động. Kính gửi: Sở Nội vụ") == "van_ban_de_nghi"
    assert planner._rule_type("BIÊN BẢN HỘI NGHỊ ĐỐI THOẠI tại nơi làm việc") == "gop_y_dai_dien"
    assert planner._normalize_type("Quyết định ban hành") == "quyet_dinh_ban_hanh"
    assert planner._normalize_type("van ban de nghi dang ky noi quy") == "van_ban_de_nghi"


def test_neo_nguoi_nop_vao_doan_ben_b_giay_uy_quyen():
    text = (
        "GIẤY ỦY QUYỀN\nNgười ủy quyền (Bên A):\nHọ và tên: Bà LÊ THỊ MẪU\nCCCD số: 001175000003\n"
        "Người được ủy quyền (Bên B):\nHọ và tên: Ông TRẦN VĂN BÌNH\nCCCD số: 001 090 000 002 - Ngày cấp: 03/04/2021"
    )
    docs = [{"text": "Công văn đề nghị"}, {"text": text}]
    idx, scope = find_submitter_mention(docs, "Trần Văn Bình", "001090000002")
    assert idx == 2 and "TRẦN VĂN BÌNH" in scope and "03/04/2021" in scope
    idx, scope = find_submitter_mention(docs, "trần văn bình", "")
    assert idx == 2 and "Bên B" in scope
    assert find_submitter_mention(docs, "Phạm Văn Khác", "001090000009") is None
