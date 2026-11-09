"""Pipeline "Tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn vào cơ sở trợ giúp xã hội" (1.116907,
NĐ 335/2026/NĐ-CP): gọi lại pipeline 1.116908 (cùng form, cùng Tờ khai Mẫu số 04). Test chốt phần KHÁC: Ghi chú không
mặc định nhóm khẩn cấp, bảng đính kèm chỉ một dòng tờ khai. Dữ liệu trong test là ví dụ bịa."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.tiep_nhan_doi_tuong_bao_tro_xa_hoi_co_hoan_canh_dac_biet_kho_khan_vao_co_so_tro_giup_xa_hoi.attach import (
    planner as ap,
)
from app.pipelines.tiep_nhan_doi_tuong_bao_tro_xa_hoi_co_hoan_canh_dac_biet_kho_khan_vao_co_so_tro_giup_xa_hoi.process import (
    runner as process_runner,
)
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.attach import planner as base_ap
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process import runner as base_runner
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process.schema import FIELDS
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "tiep-nhan-doi-tuong-bao-tro-xa-hoi-co-hoan-canh-dac-biet-kho-khan-vao-co-so-tro-giup-xa-hoi"
_EMERGENCY_KEY = "tiep-nhan-doi-tuong-can-bao-ve-khan-cap-vao-co-so-tro-giup-xa-hoi"
_DECLARATION_MODE = {"submitterMode": "owner_as_submitter"}


def _facts(**extra):
    # Người cao tuổi neo đơn khuyết tật nặng, cháu ruột là người giám hộ.
    facts = {
        "DoiTuong_HoTen": "LÒ VĂN PHÚC",
        "DoiTuong_NgaySinh": "12/12/1950",
        "DoiTuong_GioiTinh": "Nam",
        "DoiTuong_SoDinhDanh": "012050004455",
        "DoiTuong_NgayCap": "20/08/2024",
        "DoiTuong_NoiCap": "Bộ Công an",
        "DoiTuong_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Than Uyên",
                              "diaChi": "Bản Mường Cang"},
        "DoiTuong_NhomDoiTuong": "Người khuyết tật nặng, đặc biệt nặng; Người cao tuổi không có điều kiện sống tại "
                                 "cộng đồng",
        "DoiTuong_MucDoKhuyetTat": "Đặc biệt nặng",
        "NguoiNop_HoTen": "LÒ THỊ MAI",
        "NguoiNop_SoDinhDanh": "012190006677",
        "NguoiNop_NgaySinh": "01/03/1990",
        "NguoiNop_GioiTinh": "Nữ",
        "NguoiNop_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Than Uyên",
                              "diaChi": "Bản Mường Cang"},
        "NguoiNop_DienThoai": "0977111222",
    }
    facts.update(extra)
    return [{"name": k, "value": v} for k, v in facts.items()]


async def _run(monkeypatch, facts, options):
    seen = {}

    async def fake_run(files_by_role, **kwargs):
        seen.update(kwargs)
        return {"fields": facts, "errors": []}

    monkeypatch.setattr(base_runner.runner, "run", fake_run)
    res = await process_runner.run({}, options)
    return {f["name"]: f for f in res["fields"]}, res, seen


async def test_dung_pipeline_1116908_nguoi_giam_ho_nop_doi_tuong_la_chu_ho_so(monkeypatch):
    fields, res, seen = await _run(monkeypatch, _facts(), _DECLARATION_MODE)

    assert seen["fields"] is FIELDS
    assert "bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn" in seen["extra_rules"]
    assert "cần bảo vệ khẩn cấp" not in seen["extra_rules"]
    assert fields["data[fullname]"]["value"] == "LÒ THỊ MAI" and fields["data[fullname]"].get("enableInput")
    assert fields["data[ownerFullname]"]["value"] == "LÒ VĂN PHÚC"
    assert fields["data[ownerProvince]"]["value"] == "Tỉnh Lai Châu"
    assert fields["data[ownerPhoneNumber]"]["value"] == "0977111222"
    assert fields["data[isOwnerDossierCheck]"]["value"] is False
    assert not res.get("errors")


async def test_ghi_chu_chi_ghi_nhom_doc_duoc_khong_them_nhom_khan_cap(monkeypatch):
    fields, _, _ = await _run(monkeypatch, _facts(), _DECLARATION_MODE)
    assert fields["data[ghiChu]"]["value"] == (
        "Người khuyết tật đặc biệt nặng; người cao tuổi không có điều kiện sống tại cộng đồng "
        "(Tờ khai Mẫu số 04 mục I.7)."
    )


async def test_khong_doc_duoc_nhom_va_noi_o_trung_thi_khong_ghi_chu(monkeypatch):
    facts = [f for f in _facts(DoiTuong_NoiOHienNay="Như trên") if f["name"] not in (
        "DoiTuong_NhomDoiTuong", "DoiTuong_MucDoKhuyetTat")]
    fields, _, _ = await _run(monkeypatch, facts, _DECLARATION_MODE)
    assert "data[ghiChu]" not in fields


async def test_chi_co_noi_o_hien_nay_khac_thi_ghi_chu_noi_o(monkeypatch):
    facts = [f for f in _facts(DoiTuong_NoiOHienNay="Nhà văn hóa bản Nà Cang, xã Than Uyên")
             if f["name"] not in ("DoiTuong_NhomDoiTuong", "DoiTuong_MucDoKhuyetTat")]
    fields, _, _ = await _run(monkeypatch, facts, _DECLARATION_MODE)
    assert fields["data[ghiChu]"]["value"] == "Nơi ở hiện nay: Nhà văn hóa bản Nà Cang, xã Than Uyên."


async def test_tai_khoan_khop_nguoi_giam_ho_khi_tat_cai_dat(monkeypatch):
    options = {"formContext": {"applicantFullname": "Lò Thị Mai", "applicantIdentityNumber": "012190006677"}}
    fields, res, _ = await _run(monkeypatch, _facts(), options)
    assert fields["data[fullname]"]["value"] == "Lò Thị Mai"
    assert not fields["data[fullname]"].get("enableInput")
    assert not res.get("errors")


def test_prompt_mau_04_dung_chung():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, process_runner.EXTRA_RULES)
    assert "Thông tin người giám hộ" in system_prompt
    assert "NGƯỜI TIẾP NHẬN TỜ KHAI" in system_prompt


# ── Đính kèm: bảng CHỈ một dòng Tờ khai Mẫu số 04 ──

_TK04_TEXT = (
    "Mẫu số 04 TỜ KHAI ĐỀ NGHỊ CHĂM SÓC, NUÔI DƯỠNG TẠI CƠ SỞ TRỢ GIÚP XÃ HỘI I. Thông tin của người đề nghị "
    "được chăm sóc, nuôi dưỡng"
)
_BB_TEXT = "BIÊN BẢN TIẾP NHẬN ĐỐI TƯỢNG Đại diện UBND xã, đại diện cơ sở trợ giúp xã hội"
_CCCD_TEXT = "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân"


def _files(*names):
    return [{"name": n, "type": "application/pdf", "dataUrl": ""} for n in names]


def _plan_items(files, ocr, llm=None):
    return base_ap.build_plan_items(files, ocr, llm or {}, bien_ban_row=False)


def test_mot_dong_to_khai_bien_ban_va_cccd_khong_dinh():
    files = _files("cccd.pdf", "bien_ban.pdf", "tk_1.pdf", "tk_2.pdf")
    ocr = [{"name": "cccd.pdf", "text": _CCCD_TEXT}, {"name": "bien_ban.pdf", "text": _BB_TEXT},
           {"name": "tk_1.pdf", "text": _TK04_TEXT}, {"name": "tk_2.pdf", "text": _TK04_TEXT}]
    items, warnings, _ = _plan_items(files, ocr)

    assert not warnings
    assert [(i["fileName"], i["componentName"], i["documentName"]) for i in items] == [
        ("tk_1.pdf", "Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội",
         "Tờ khai đề nghị chăm sóc, nuôi dưỡng (Mẫu số 04)"),
        ("tk_2.pdf", "Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội",
         "Tờ khai đề nghị chăm sóc, nuôi dưỡng (Mẫu số 04) 2"),
    ]


def test_tep_chung_voi_bien_ban_chi_dinh_dong_to_khai():
    items, warnings, _ = _plan_items(_files("ho_so.pdf"), [{"name": "ho_so.pdf", "text": "x"}],
                                     {0: "to_khai_kem_bien_ban"})
    assert [i["componentName"] for i in items] == ["Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội"]
    assert not warnings


def test_thieu_to_khai_va_tep_la_thi_canh_bao():
    files = _files("cccd.pdf", "mo.pdf")
    items, warnings, _ = _plan_items(files, [{"name": "cccd.pdf", "text": _CCCD_TEXT}], {1: "other"})

    assert not items
    assert any("mo.pdf" in w and "Tờ khai Mẫu số 04 —" in w for w in warnings)
    assert any("Không thấy Tờ khai Mẫu số 04" in w for w in warnings)
    assert not any("Biên bản" in w for w in warnings)


async def test_plan_dung_prompt_rieng_va_mot_dong(monkeypatch):
    from app.process.schemas import FileItem
    from app.services import ocr as ocr_service

    prompts = []

    async def fake_ocr(_files):
        return [{"name": "a.pdf", "text": _TK04_TEXT}, {"name": "b.pdf", "text": _BB_TEXT}]

    async def fake_classify(_docs, system_prompt=None):
        prompts.append(system_prompt)
        return {0: "to_khai_mau_04", 1: "bien_ban_tiep_nhan"}

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(base_ap, "_classify_with_llm", fake_classify)
    files = [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,QUJD", role="attachment")
             for n in ("a.pdf", "b.pdf")]
    result = await ap.plan(files, {}, None)

    assert [a["fileName"] for a in result["attachments"]] == ["a.pdf"]
    assert result["extracted"]["notAttached"] == ["b.pdf"]
    assert result["extracted"]["rows"] == ["Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội"]
    assert not result["errors"]
    assert "bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn" in prompts[0]


# ── Registry lõi, link kê khai và trợ lý người dân ──

def test_registry_va_nhan_dien_khong_trung_thu_tuc_anh_em():
    from app.procedures import registry

    assert get_pipeline(_KEY) is process_runner.run
    assert get_attach_pipeline(_KEY) is ap.plan
    phrase = registry._BY_KEY[_KEY]["detect"]["textIncludes"][0].lower()
    assert phrase in get_procedure(_KEY)["label"].lower()
    for code in ("1.116908", "1.116909", "1.116910"):
        other = next(link for link in KE_KHAI_LINKS if link.get("code") == code)
        assert phrase not in other["label"].lower()
    emergency_phrase = registry._BY_KEY[_EMERGENCY_KEY]["detect"]["textIncludes"][0].lower()
    assert emergency_phrase not in get_procedure(_KEY)["label"].lower()


def test_ke_khai_link_trung_key_va_chon_phuong_xa():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    link = links[0]
    assert link["code"] == "1.116907"
    assert link["needsAgencySelect"] is True
    assert not link.get("provinceOnlyAgency") and not link.get("selectSo")


def test_tro_ly_dung_pipeline_loi_va_link_ke_khai():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert procedure["label"] == get_procedure(_KEY)["label"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.116907"
    assert not procedure.get("provinceOnly")
    assert procedure["detect"]["urlScope"] == ["dichvucongbyt.moh.gov.vn"]
    assert procedure["bxdFlow"] == handfree.get_procedure(_EMERGENCY_KEY)["bxdFlow"]
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert field_review.get(_KEY)["noAsk"] == ("ghiChu",)
    assert PROCEDURE_HINTS[_KEY] and PROCEDURE_HMONG[_KEY]
    assert not set(PROCEDURE_HINTS[_KEY]) & set(PROCEDURE_HINTS[_EMERGENCY_KEY])
