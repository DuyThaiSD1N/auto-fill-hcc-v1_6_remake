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
