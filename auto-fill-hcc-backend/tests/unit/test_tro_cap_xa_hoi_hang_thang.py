"""Quy tắc người khai/người nộp cho thủ tục trợ cấp xã hội hàng tháng."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.tro_cap_xa_hoi_hang_thang.process import mapper
from app.pipelines.tro_cap_xa_hoi_hang_thang.process import runner as process_runner
from app.pipelines.tro_cap_xa_hoi_hang_thang.process.prompt import EXTRA_RULES
from app.pipelines.tro_cap_xa_hoi_hang_thang.process.schema import FIELDS


def _mapped(fields, options=None):
    result, warnings = mapper.enrich(
        [{"name": name, "value": value} for name, value in fields.items()],
        options,
    )
    return {field["name"]: field["value"] for field in result}, warnings


def _subject_fields():
    return {
        "DoiTuong_HoTen": "TRẦN VĂN HÙNG",
        "DoiTuong_NgaySinh": "04/05/1981",
        "DoiTuong_GioiTinh": "Nam",
        "DoiTuong_SoDinhDanh": "038081022531",
        "DoiTuong_NgayCap": "27/02/2022",
        "DoiTuong_NoiCap": "Cục quản lý hành chính về trật tự xã hội",
        "DoiTuong_ThuongTru": {
            "quocGia": "Việt Nam",
            "tinh": "Lai Châu",
            "xa": "phường Đoàn Kết",
            "diaChi": "Tổ 5",
        },
    }


def test_mapper_uses_declarant_and_ignores_frontend_applicant_context():
    fields = {
        **_subject_fields(),
        "NguoiNop_HoTen": "NGUYỄN THÚY VÂN",
        # OCR/tờ khai có 13 số: không được tự sửa thành CCCD hợp lệ.
        "NguoiNop_SoDinhDanh": "0122188005142",
        "NguoiNop_ThuongTru": {
            "quocGia": "Việt Nam",
            "tinh": "",
            "xa": "phường Đoàn Kết",
            "diaChi": "Tổ 5",
        },
    }

    result, warnings = _mapped(fields, {
        "formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }
    })

    assert not warnings
    assert result["data[fullname]"] == "NGUYỄN THÚY VÂN"
    assert "data[identityNumber]" not in result
    assert result["data[province]"] == "Tỉnh Lai Châu"
    assert result["data[district]"] == "phường Đoàn Kết"
    assert result["data[address]"] == "Tổ 5"
    assert result["data[ownerFullname]"] == "TRẦN VĂN HÙNG"
    assert result["data[ownerIdentityNumber]"] == "038081022531"


def test_mapper_uses_subject_for_part_one_when_no_declarant_block():
    result, warnings = _mapped(_subject_fields(), {
        "formContext": {"applicantFullname": "Vũ Đình Thiết"}
    })

    assert not warnings
    assert result["data[fullname]"] == "TRẦN VĂN HÙNG"
    assert result["data[identityNumber]"] == "038081022531"
    assert result["data[ownerFullname]"] == "TRẦN VĂN HÙNG"


def test_mapper_accepts_valid_declarant_identity_only():
    fields = {
        **_subject_fields(),
        "NguoiNop_HoTen": "NGUYỄN THÚY VÂN",
        "NguoiNop_SoDinhDanh": "012188005142",
    }

    result, _ = _mapped(fields)

    assert result["data[fullname]"] == "NGUYỄN THÚY VÂN"
    assert result["data[identityNumber]"] == "012188005142"


def test_address_inference_normalizes_commune_prefix_without_few_shot():
    known = {"tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "diaChi": "Tổ 5"}
    missing = {"tinh": "", "xa": "P.Đoàn Kết", "diaChi": "Tổ 5"}

    mapper._complete_missing_provinces(known, missing)

    assert missing["tinh"] == "Lai Châu"


def test_address_inference_keeps_province_empty_when_commune_is_ambiguous():
    first = {"tinh": "Lai Châu", "xa": "Phường Đoàn Kết"}
    second = {"tinh": "Điện Biên", "xa": "P. Đoàn Kết"}
    missing = {"tinh": "", "xa": "Đoàn Kết"}

    mapper._complete_missing_provinces(first, second, missing)

    assert missing["tinh"] == ""


def test_address_inference_never_overwrites_explicit_province():
    known = {"tinh": "Lai Châu", "xa": "Phường Đoàn Kết"}
    explicit = {"tinh": "Điện Biên", "xa": "Phường Đoàn Kết"}

    mapper._complete_missing_provinces(known, explicit)

    assert explicit["tinh"] == "Điện Biên"


def test_prompt_sources_submitter_from_declarant_block_without_frontend_context():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert 'block "Thông tin người khai thay"' in system_prompt
    assert "BẮT BUỘC trả NguoiNop_HoTen" in system_prompt
    assert "đúng 9 hoặc 12 chữ số" in system_prompt
    assert "tài khoản/người làm" in system_prompt
    assert "<nguoi_nop_context>" not in system_prompt


async def test_runner_does_not_pass_submitter_context_builder(monkeypatch):
    captured = {}

    async def fake_run(files_by_role, **kwargs):
        captured.update(kwargs)
        return {"fields": [], "errors": []}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)

    await process_runner.run({}, {
        "formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }
    })

    assert "context_builder" not in captured
    assert "options" not in captured


# ── Đính kèm (attp-row): form KHÔNG có dòng "Giấy tờ khác" nên file chưa nhận diện được PHẢI
# route về dòng Tờ khai (Mẫu 1a-1d), tuyệt đối KHÔNG trả plan rỗng (FE báo "chưa có kế hoạch"). ──
from app.pipelines.tro_cap_xa_hoi_hang_thang.attach import planner as attach_planner


def test_attach_unknown_file_routes_to_declaration_row_not_empty():
    files = [{"name": "Scan_0029.pdf", "type": "application/pdf", "dataUrl": ""}]
    ocr = [{"name": "Scan_0029.pdf", "text": "noi dung khong ro rang khong khop mau nao"}]
    items, warnings, classified = attach_planner.build_plan_items(files, ocr, {})
    assert len(items) == 1, "file chưa nhận diện vẫn phải sinh 1 item (không rớt → không plan rỗng)"
    assert items[0]["componentName"] == "Mẫu số 1a, 1b, 1c, 1d"
    assert items[0]["target"] == "attp-row"
    assert classified[0]["docType"] == "other" and classified[0]["routedTo"] == "to_khai_doi_tuong"
    assert warnings and "Tờ khai" in warnings[0]


def test_attach_known_file_still_routes_to_its_own_row():
    files = [{"name": "ks.pdf", "type": "application/pdf", "dataUrl": ""}]
    ocr = [{"name": "ks.pdf", "text": "GIẤY KHAI SINH họ tên trẻ em ngày sinh"}]
    items, _warnings, classified = attach_planner.build_plan_items(files, ocr, {})
    assert len(items) == 1
    assert items[0]["componentName"] == "Giấy khai sinh của trẻ em"
    assert classified[0]["docType"] == "khai_sinh"
    # GIỮ NGUYÊN tên file gốc: documentName = tên file (BE-only) → engine attp-row FE đặt tên File =
    # documentName nên file giữ đúng tên tải lên; loại giấy tờ vẫn ở componentName/detectedType.
    assert items[0]["documentName"] == "ks.pdf"
    assert items[0]["fileName"] == "ks.pdf"
    assert items[0]["detectedType"] == "khai_sinh"


async def test_attach_plan_never_empty_even_if_all_files_skip(monkeypatch):
    """1 PDF gộp mà trang đầu là Giấy ủy quyền → cả file bị xếp uy_quyen (skip). Plan KHÔNG được
    rỗng (FE sẽ báo 'chưa có kế hoạch') → lưới cuối đính file đầu vào dòng Tờ khai."""
    from app.pipelines.tro_cap_xa_hoi_hang_thang.attach import planner as ap
    from app.process.schemas import FileItem
    from app.services import ocr as ocr_service

    async def fake_ocr(_files):
        return [{"name": "Scan_0029.pdf", "text": "GIẤY ỦY QUYỀN NỘP HỒ SƠ TRỰC TUYẾN"}]

    async def fake_classify(_docs):
        return {0: ap._UY_QUYEN}  # cả file bị LLM xếp ủy quyền (thuộc _SKIP_DOCS)

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(ap, "_classify_with_llm", fake_classify)

    files = [FileItem(name="Scan_0029.pdf", type="application/pdf",
                      dataUrl="data:application/pdf;base64,QUJD", role="attachment")]
    result = await ap.plan(files, {}, None)
    assert len(result["attachments"]) == 1, "plan không được rỗng dù file bị xếp skip"
    assert result["attachments"][0]["componentName"] == "Mẫu số 1a, 1b, 1c, 1d"
    assert result["attachments"][0]["target"] == "attp-row"
