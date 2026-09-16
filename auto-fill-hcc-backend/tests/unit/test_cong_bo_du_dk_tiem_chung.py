from app.pipelines.cong_bo_du_dk_tiem_chung.attach.planner import build_plan_items
from app.pipelines.cong_bo_du_dk_tiem_chung.process.mapper import enrich
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "cong-bo-co-so-du-dieu-kien-tiem-chung"

_THONG_BAO = [
    {"name": "CoSo_Ten", "value": "Khoa Nhi, bệnh viện đa khoa Sìn Hồ"},
    {"name": "CoSo_DiaChi", "value": {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Sìn Hồ",
                                      "diaChi": "Thôn 3"}},
    {"name": "CoSo_NguoiDungDau", "value": "BS CK1 Hoàng Việt Bắc"},
    {"name": "CoSo_DienThoai", "value": "0988 440 349"},
    {"name": "CoSo_Email", "value": "vietbacsh@gmail.com"},
]

_CCCD_BAC = {
    "HoTen": "HOÀNG VIỆT BẮC",
    "NgaySinh": "12/03/1978",
    "GioiTinh": "Nam",
    "SoDinhDanh": "012078000123",
    "NgayCap": "01/05/2022",
    "NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "ThuongTru": {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Sìn Hồ", "diaChi": "Thôn 3"},
}


def _person(prefix: str, person: dict) -> list[dict]:
    return [{"name": f"{prefix}{k}", "value": v} for k, v in person.items()]


def _values(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_registry_wires_pipeline():
    assert get_procedure(_KEY)
    assert get_pipeline(_KEY)
    assert get_attach_pipeline(_KEY)


def test_owner_follows_thong_bao_without_cccd():
    out, warnings = enrich(_THONG_BAO, {"formContext": {"applicantFullname": "Lò Văn A",
                                                        "applicantIdentityNumber": "012000000001"}})
    v = _values(out)
    assert v["data[isOwnerDossierCheck]"] is False
    assert v["data[ownerFullname]"] == "Hoàng Việt Bắc"
    assert v["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert v["data[ownerAddress]"] == "Thôn 3"
    assert v["data[ownerPhoneNumber]"] == "0988440349"
    assert v["data[ownerEmail]"] == "vietbacsh@gmail.com"
    assert v["data[ownerNation]"] == "Việt Nam"
    assert "data[ownerIdentityNumber]" not in v
    # Không có CCCD người nộp → không chạm Phần I.
    assert not any(name in v for name in ("data[birthday]", "data[gender]", "data[phoneNumber]"))
    assert any("không có CCCD của người nộp" in w for w in warnings)


def test_submitter_is_head_fills_both_parts_from_same_cccd():
    fields = _THONG_BAO + _person("NguoiNop_", _CCCD_BAC)
    ctx = {"formContext": {"applicantFullname": "Hoàng Việt Bắc", "applicantIdentityNumber": "012078000123"}}
    v = _values(enrich(fields, ctx)[0])
    assert v["data[birthday]"] == "12/03/1978"
    assert v["data[gender]"] == "Nam"
    assert v["data[identityDate]"] == "01/05/2022"
    assert v["data[phoneNumber]"] == "0988440349"
    assert "data[fullname]" not in v  # cổng đã đổ sẵn tên tài khoản
    assert v["data[ownerIdentityNumber]"] == "012078000123"
    assert v["data[ownerBirthday]"] == "12/03/1978"
    assert v["data[ownerGender]"] == "Nam"


def test_cccd_not_matching_account_is_ignored_for_part_one():
    fields = _THONG_BAO + _person("NguoiNop_", _CCCD_BAC)
    ctx = {"formContext": {"applicantFullname": "Lò Văn A", "applicantIdentityNumber": "012000000001"}}
    v = _values(enrich(fields, ctx)[0])
    assert "data[birthday]" not in v
    assert "data[identityDate]" not in v


def test_head_cccd_with_other_name_is_rejected():
    fields = _THONG_BAO + _person("DauCoSo_", {**_CCCD_BAC, "HoTen": "Nguyễn Thị Hạnh"})
    out, warnings = enrich(fields, {})
    v = _values(out)
    assert "data[ownerIdentityNumber]" not in v
    assert any("KHÔNG phải người đứng đầu" in w for w in warnings)


def test_attach_combined_pdf_and_skip_cccd():
    files = [{"name": "to-trinh-thong-bao.pdf"}, {"name": "cccd.jpg"}]
    ocr = [
        {"name": "to-trinh-thong-bao.pdf", "text": "TỜ TRÌNH Về việc đăng tải cơ sở đủ điều kiện tiêm chủng ... "
                                                    "THÔNG BÁO Cơ sở đủ điều kiện tiêm chủng Tên cơ sở thông báo: "
                                                    "Khoa Nhi Người đứng đầu cơ sở: BS CK1 Hoàng Việt Bắc"},
        {"name": "cccd.jpg", "text": "CĂN CƯỚC CÔNG DÂN Số 012078000123"},
    ]
    items, warnings, classified = build_plan_items(files, ocr)
    assert len(items) == 1
    assert items[0]["componentIndex"] == 1
    assert items[0]["detectedType"] == "thong_bao"
    assert items[0]["target"] == "attp-row"
    assert classified[1]["skipped"] is True
    assert warnings == []


def test_attach_multiple_files_keep_original_names():
    files = [{"name": "tb-nhi.pdf"}, {"name": "to-trinh.pdf"}]
    ocr = [
        {"name": "tb-nhi.pdf", "text": "THÔNG BÁO Tên cơ sở thông báo: Khoa Nhi"},
        {"name": "to-trinh.pdf", "text": "TỜ TRÌNH về việc đăng tải cơ sở đủ điều kiện tiêm chủng"},
    ]
    items, _, _ = build_plan_items(files, ocr)
    assert [i["documentName"] for i in items] == ["tb-nhi.pdf", "to-trinh.pdf"]


def test_attach_warns_when_no_thong_bao():
    items, warnings, _ = build_plan_items([{"name": "x.pdf"}], [{"name": "x.pdf", "text": "hoá đơn"}])
    assert items == []
    assert any("Không tìm thấy tờ Thông báo" in w for w in warnings)
