from app.pipelines.dang_ky_thay_doi_kinh_doanh.attach.planner import _detect_type
from app.pipelines.dang_ky_thay_doi_kinh_doanh.process import mapper
from app.process.schemas import ProcessResp
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _field(name, value):
    return {"name": name, "value": value}


def test_add_text_only_industry_does_not_fake_name_change():
    pages, flow = mapper.build([
        _field("HoKinhDoanh_MaSo", "027200011386"),
        _field("HienTai_Ten", "HỘ KINH DOANH TRƯƠNG HÀN ĐAN"),
        _field("DeNghi_Ten", "TRƯƠNG HÀN ĐAN"),  # mẫu nhắc lại cùng tên, không phải đổi tên
        _field("DeNghi_NganhNgheBoSung", [{"ma": "", "ten": "Tư vấn, tham vấn tâm lý"}]),
    ])

    assert flow["search"]["method"] == "businessNumber"
    assert flow["search"]["value"] == "027200011386"
    assert flow["nameChange"] is False
    assert flow["pageOrder"] == ["nganh-nghe-kinh-doanh", "nguoi-nop-ho-so"]
    assert flow["industryChanges"]["add"] == [
        {"code": "", "name": "Tư vấn, tham vấn tâm lý", "main": False}
    ]
    assert pages["nganh-nghe-kinh-doanh"][0]["name"] == "__businessLineChanges"


def test_remove_industry_keeps_exact_four_digit_code():
    _, flow = mapper.build([
        _field("HoKinhDoanh_MaSo", "001090057964"),
        _field("HienTai_Ten", "HỘ KINH DOANH NGUYỄN PHÚ LUÂN"),
        _field("DeNghi_NganhNgheBaiBo", [{"ma": "47.19", "ten": "Tạp hóa"}]),
    ])

    assert flow["industryChanges"]["remove"] == [
        {"code": "4719", "name": "Tạp hóa", "main": False}
    ]
    assert flow["changeFlags"]["industry"] is True
    assert flow["nameChange"] is False


def test_actual_name_change_sets_wizard_yes_and_name_page():
    pages, flow = mapper.build([
        _field("HienTai_Ten", "HỘ KINH DOANH AN PHÚ"),
        _field("DeNghi_Ten", "HỘ KINH DOANH AN PHÚ MỚI"),
        _field("HienTai_ChuHo", {"hoTen": "Nguyễn Văn A", "soDinhDanh": "012345678901"}),
    ])

    assert flow["nameChange"] is True
    assert flow["pageOrder"] == ["ten-ho-kinh-doanh", "nguoi-nop-ho-so"]
    assert any(field["name"] == "ctl00$C$NAMEFld" and field["value"] == "AN PHÚ MỚI"
               for field in pages["ten-ho-kinh-doanh"])
    assert flow["search"] == {
        "method": "identityNumber",
        "value": "012345678901",
        "expectedName": "HỘ KINH DOANH AN PHÚ",
        "expectedBusinessNumber": "",
    }


def test_identity_candidates_are_deduplicated_for_runtime_account_match():
    _, flow = mapper.build([
        _field("NguoiNop", {"hoTen": "Vũ Đình Thiết", "soDinhDanh": "040203015844", "diaChi": {"tinh": "Nghệ An"}}),
        _field("Cccd_DanhSach", [
            {"hoTen": "Vũ Đình Thiết", "soDinhDanh": "040203015844", "diaChi": {"tinh": "Nghệ An"}},
            {"hoTen": "Nguyễn Văn A", "soDinhDanh": "012345678901", "diaChi": {"tinh": "Đà Nẵng"}},
        ]),
    ])

    assert [(item["hoTen"], item["soDinhDanh"]) for item in flow["identityCandidates"]] == [
        ("Vũ Đình Thiết", "040203015844"),
        ("Nguyễn Văn A", "012345678901"),
    ]


def test_change_remaps_old_address_for_form_and_identity_candidates():
    old_address = {
        "quocGia": "Việt Nam", "tinh": "Bình Thuận", "xa": "Hàm Kiệm", "diaChi": "Tổ 3",
    }
    pages, flow = mapper.build([
        _field("HienTai_TruSo", old_address),
        _field("DeNghi_TruSo", old_address),
        _field("HienTai_ChuHo", {
            "hoTen": "Nguyễn Thị Quỳnh", "soDinhDanh": "033197013790", "diaChi": old_address,
        }),
        _field("Cccd_DanhSach", [{
            "hoTen": "Nguyễn Thị Quỳnh", "soDinhDanh": "033197013790", "diaChi": old_address,
        }]),
    ])

    assert "dia-chi" not in pages
    assert flow["identityCandidates"][0]["diaChi"]["tinh"] == "Lâm Đồng"
    assert flow["identityCandidates"][0]["diaChi"]["xa"] == "Hàm Kiệm"


def test_attachment_detection_routes_notice_and_identity():
    assert _detect_type("THÔNG BÁO THAY ĐỔI NỘI DUNG ĐĂNG KÝ HỘ KINH DOANH") == "change_notice"
    assert _detect_type("CĂN CƯỚC CÔNG DÂN Citizen Identity Card") == "personal_legal"
    assert _detect_type("GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH") == "registration_certificate"
    assert _detect_type("BẢN SAO BIÊN BẢN HỌP THÀNH VIÊN HỘ GIA ĐÌNH") == "family_minutes"


def test_registry_and_response_contract_expose_change_flow():
    key = "dang-ky-thay-doi-noi-dung-ho-kinh-doanh"
    procedure = get_procedure(key)
    assert procedure["businessWorkflow"] == "change"
    assert get_pipeline(key) is not None
    assert get_attach_pipeline(key) is not None

    response = ProcessResp(
        fields=[], extracted={}, stats={}, pages={"nguoi-nop-ho-so": []},
        businessFlow={"workflow": "change", "pageOrder": ["nguoi-nop-ho-so"]},
    )
    assert response.businessFlow["workflow"] == "change"


def test_form_only_dossier_flag_marks_change_without_identity_papers():
    """Hồ sơ chỉ có tờ đơn xin thay đổi → extension chốt vai trò người nộp bằng HỌ TÊN chủ hộ."""
    _, flow = mapper.build([
        _field("HoKinhDoanh_MaSo", "027200011386"),
        _field("HienTai_Ten", "HỘ KINH DOANH TRƯƠNG HÀN ĐAN"),
        _field("HienTai_ChuHo", {"hoTen": "Trương Hàn Đan", "soDinhDanh": "012345678901"}),
        _field("DeNghi_NganhNgheBoSung", [{"ma": "", "ten": "Tư vấn, tham vấn tâm lý"}]),
    ])

    assert flow["formOnly"] is True


def test_form_only_flag_off_when_dossier_has_identity_papers():
    for extra in (
        _field("Cccd_DanhSach", [{"hoTen": "Trần Thị B", "soDinhDanh": "022222222222"}]),
        _field("HasMultipleCCCD", True),
        _field("UyQuyen_CoGiayUyQuyen", True),
        _field("UyQuyen_NguoiDuocUyQuyen_HoTen", "Trần Thị B"),
    ):
        _, flow = mapper.build([
            _field("HoKinhDoanh_MaSo", "027200011386"),
            _field("HienTai_Ten", "HỘ KINH DOANH TRƯƠNG HÀN ĐAN"),
            _field("HienTai_ChuHo", {"hoTen": "Trương Hàn Đan", "soDinhDanh": "012345678901"}),
            _field("DeNghi_NganhNgheBoSung", [{"ma": "", "ten": "Tư vấn, tham vấn tâm lý"}]),
            extra,
        ])
        assert flow["formOnly"] is False, extra["name"]
