"""Regression hai vai trò cho trợ cấp thờ cúng liệt sĩ."""

from app.pipelines.tro_cap_tho_cung_liet_si.process import mapper
from app.pipelines.tro_cap_tho_cung_liet_si.process.runner import (
    _authorization_sections,
    _proposal_section,
    _requester_context,
)
from app.pipelines.tro_cap_tho_cung_liet_si.process.schema import ALLOWED


def _run(values: dict, form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    fields, warnings = mapper.enrich(compact, {"formContext": form_context or {}})
    mapped = {
        (field["name"], field.get("occurrence")): field["value"]
        for field in fields
    }
    return fields, mapped, warnings


_OWNER = {
    "ChuHoSo_HoTen": "Vũ Đình Tuyến",
    "ChuHoSo_NgaySinh": "08/03/1962",
    "ChuHoSo_SoDinhDanh": "034062017797",
    "ChuHoSo_NgayCap": "09/05/2021",
    "ChuHoSo_NoiCap": "Cục CSQLHC về TTXH",
    "ChuHoSo_QueQuan": {
        "quocGia": "Việt Nam",
        "tinh": "Hưng Yên",
        "xa": "Long Hưng",
        "diaChi": "",
    },
    "ChuHoSo_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Lâm Viên",
        "diaChi": "2 Trương Văn Hoàn",
    },
    "ChuHoSo_DienThoai": "0982577867",
    "ToKhai_MoiQuanHeVoiLietSi": "Con trai",
    "ToKhai_LietSiThoCung": "Vũ Đình Soang",
    "ToKhai_ThanNhan": [
        {
            "hoTen": "Vũ Thị Duyên",
            "namSinh": "1965",
            "noiThuongTru": "8/5 Xô Viết Nghệ Tĩnh, Phường Lâm Viên",
            "moiQuanHe": "Con",
        }
    ],
}


def _run_owner_mode(values: dict, form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    opts = {"submitterMode": "owner_as_submitter"}
    if form_context is not None:
        opts["formContext"] = form_context
    fields, warnings = mapper.enrich(compact, opts)
    return {(f["name"], f.get("occurrence")): f["value"] for f in fields}, warnings


def test_owner_mode_submitter_is_owner_and_ticks():
    """Toggle owner_as_submitter, không mỏ neo UI → occ0 (người nộp) = chủ hồ sơ + tick; phần còn lại giữ nguyên."""
    mapped, _ = _run_owner_mode(_OWNER)
    assert mapped[("data[isOwnerDossierCheck]", None)] is True
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Tuyến"          # người nộp = chủ hồ sơ
    assert mapped[("data[fullname]", 1)] == "Vũ Đình Tuyến"          # Mẫu 18 chi tiết (luôn owner)
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"  # khối chủ hồ sơ (luôn owner)
    assert mapped[("data[MqhVls1]", None)] == "Con trai"             # nghiệp vụ liệt sĩ vẫn điền
    assert mapped[("data[UqTcLs]", None)] == "Vũ Đình Soang"


def test_owner_mode_ignores_ui_anchor_no_warning():
    """Owner mode bỏ mỏ neo UI: dù form có người KHÁC vẫn owner=submitter, KHÔNG cảnh báo lệch người nộp."""
    mapped, warnings = _run_owner_mode(
        _OWNER, {"applicantFullname": "Người Khác", "applicantIdentityNumber": "999999999999"}
    )
    assert mapped[("data[isOwnerDossierCheck]", None)] is True
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Tuyến"
    assert not any("người nộp" in w for w in warnings)


def test_schema_has_two_identity_roles_and_keeps_business_fields():
    assert "ChuHoSo_HoTen" in ALLOWED
    assert "NguoiNop_HoTen" in ALLOWED
    assert "ToKhai_MoiQuanHeVoiLietSi" in ALLOWED
    assert "ToKhai_ThanNhan" in ALLOWED
    assert not any(name.startswith("Person") for name in ALLOWED)
    assert "ToKhai_HoTen" not in ALLOWED


def test_mismatching_ui_fills_owner_and_detail_but_not_requester():
    fields, mapped, warnings = _run(
        _OWNER,
        {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        },
    )

    assert fields[0]["name"] == "data[isOwnerDossierCheck]"
    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert mapped[("data[ownerBirthday]", None)] == "08/03/1962"
    assert mapped[("data[ownerIdentityNumber]", None)] == "034062017797"
    assert mapped[("data[ownerIdentityDate]", None)] == "09/05/2021"
    assert mapped[("data[ownerProvince]", None)] == "Tỉnh Lâm Đồng"
    assert mapped[("data[ownerDistrict]", None)] == "Phường Lâm Viên"
    assert mapped[("data[fullname]", 1)] == "Vũ Đình Tuyến"
    assert mapped[("data[birthday]", 1)] == "08/03/1962"
    assert mapped[("data[MqhVls1]", None)] == "Con trai"
    assert mapped[("data[UqTcLs]", None)] == "Vũ Đình Soang"
    assert ("data[ownerGender]", None) not in mapped
    assert ("data[gender]", 1) not in mapped
    assert "không điền phần người nộp" in warnings[0]


def test_owner_matching_ui_ticks_and_explicitly_fills_both_blocks():
    _, mapped, warnings = _run(
        _OWNER,
        {
            "applicantFullname": "Vũ Đình Tuyến",
            "applicantIdentityNumber": "034062017797",
        },
    )

    assert mapped[("data[isOwnerDossierCheck]", None)] is True
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Tuyến"
    assert mapped[("data[birthday]", 0)] == "08/03/1962"
    assert mapped[("data[identityDate]", 0)] == "09/05/2021"
    assert mapped[("data[ownerBirthday]", None)] == "08/03/1962"
    assert mapped[("data[ownerIdentityDate]", None)] == "09/05/2021"
    assert not warnings


def test_distinct_verified_requester_fills_both_roles():
    values = {
        **_OWNER,
        "NguoiNop_HoTen": "Vũ Đình Thiết",
        "NguoiNop_NgaySinh": "26/04/2003",
        "NguoiNop_SoDinhDanh": "040203015844",
    }
    _, mapped, warnings = _run(
        values,
        {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        },
    )

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert mapped[("data[fullname]", 0)] == "Vũ Đình Thiết"
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert mapped[("data[fullname]", 1)] == "Vũ Đình Tuyến"
    assert not warnings


def test_name_match_but_identity_mismatch_is_not_accepted():
    _, mapped, warnings = _run(
        _OWNER,
        {
            "applicantFullname": "Vũ Đình Tuyến",
            "applicantIdentityNumber": "999999999999",
        },
    )

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert warnings


def test_missing_ui_anchor_still_fills_owner_and_business_details():
    _, mapped, warnings = _run(_OWNER)

    assert mapped[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in mapped
    assert mapped[("data[ownerFullname]", None)] == "Vũ Đình Tuyến"
    assert mapped[("data[DataGrid][0][Ht]", None)] == "Vũ Thị Duyên"
    assert not warnings


def test_martyr_name_list_is_joined_and_duplicate_relatives_are_merged():
    values = {
        **_OWNER,
        "ToKhai_LietSiThoCung": ["Vũ Đình Soang", "Vũ Đình Hải"],
        "ToKhai_ThanNhan": [
            {
                "hoTen": "Vũ Đình Tuyên",
                "namSinh": "1962",
                "noiThuongTru": "Số 2 Trường Sơn Vân Hoàn",
                "moiQuanHe": "em trai",
            },
            {
                "hoTen": "VŨ ĐÌNH TUYÊN",
                "namSinh": "",
                "noiThuongTru": "phường Lâm Viên Đà Lạt",
                "moiQuanHe": "em trai",
            },
            {
                "hoTen": "Vũ Thị Duyên",
                "namSinh": "1965",
                "noiThuongTru": "8/5 Hồ Xuân Hương P. Lâm Viên Đà Lạt",
                "moiQuanHe": "em trai",
            },
            {"hoTen": "Vũ Thị Duyên", "namSinh": "1965"},
        ],
    }

    _, mapped, warnings = _run(values)

    assert mapped[("data[UqTcLs]", None)] == "Vũ Đình Soang và Vũ Đình Hải"
    assert mapped[("data[DataGrid][0][Ht]", None)] == "Vũ Đình Tuyên"
    assert mapped[("data[DataGrid][0][Ns]", None)] == "1962"
    assert mapped[("data[DataGrid][1][Ht]", None)] == "Vũ Thị Duyên"
    assert mapped[("data[DataGrid][1][Ns]", None)] == "1965"
    assert ("data[DataGrid][2][Ht]", None) not in mapped
    assert not warnings


async def test_runner_scopes_owner_and_rejects_unrelated_people_as_requester():
    ocr = """Mẫu số 18
1. Thông tin người đề nghị
Họ và tên: Vũ Đình Tuyên
Ngày tháng năm sinh: 1962
CCCD/CMND số 034062011797
Mối quan hệ với liệt sĩ: Con trai
2. Thông tin về thân nhân liệt sĩ
1 | Vũ Thị Duyên | 1965

BÊN ỦY QUYỀN:
Họ và tên: Vũ Thị Duyên
CC số: 034165017965
BÊN ĐƯỢC ỦY QUYỀN:
Họ và tên: Vũ Đình Tuyến Sinh năm: 08/03/1962
CCCD số: 034062017797 cấp ngày 09/05/2021
Địa chỉ: 2 Trương Văn Hoàn, Phường Lâm Viên, Lâm Đồng
NỘI DUNG ỦY QUYỀN:
Thờ cúng liệt sĩ Vũ Đình Soang
"""

    proposal = _proposal_section(ocr)
    assert "Vũ Đình Tuyên" in proposal
    assert "Vũ Thị Duyên" not in proposal
    authorization = _authorization_sections(ocr)[0]
    assert "Vũ Đình Tuyến" in authorization
    assert "Vũ Thị Duyên" not in authorization

    owner_context = await _requester_context(
        [{"name": "ho-so.pdf", "text": ocr}],
        {"formContext": {
            "applicantFullname": "Vũ Đình Tuyến",
            "applicantIdentityNumber": "034062017797",
        }},
    )
    assert 'result="owner_match"' in owner_context

    mismatch_context = await _requester_context(
        [{"name": "ho-so.pdf", "text": ocr}],
        {"formContext": {
            "applicantFullname": "Vũ Đình Thiết",
            "applicantIdentityNumber": "040203015844",
        }},
    )
    assert 'result="no_document_match"' in mismatch_context


# ---- Đính kèm: cài đặt "Có tách hồ sơ khi đính kèm" (PDF gộp → mỗi giấy một tệp) ----

_TRANG = (
    "Mẫu số 18 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐỀ NGHỊ Giải quyết chế độ trợ cấp thờ cúng liệt sĩ",
    "",
    "Mẫu số 80A BIÊN BẢN HỌP ĐỒNG THUẬN Giải quyết chế độ trợ cấp thờ cúng liệt sĩ Nguyễn Văn B, ủy quyền cho",
    "CÁC THÀNH VIÊN (Ký và ghi rõ họ tên) Nguyễn Văn A, Nguyễn Văn C, Nguyễn Thị D, chức vụ người ký",
    "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐỀ NGHỊ Về việc thay đổi người thờ cúng liệt sĩ Nguyễn Văn B",
    "XÁC NHẬN CỦA TỔ TRƯỞNG TỔ DÂN PHỐ Xác nhận lời khai của ông Nguyễn Văn A trong đơn nêu trên là đúng",
    "CĂN CƯỚC CÔNG DÂN Citizen Identity Card số định danh 001070000001 họ và tên Nguyễn Văn A",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM TỔ QUỐC GHI CÔNG LIỆT SĨ Nguyễn Văn B Bằng số GX 100",
    "UBND PHƯỜNG",
    "UBND XÃ AN BÌNH TRÍCH LỤC KHAI TỬ Họ, chữ đệm, tên: NGUYỄN VĂN E, ngày chết 01/01/2023",
)
_TEXT_10 = "\n".join(f"───── Trang {n + 1}/10 ─────\n{t}" for n, t in enumerate(_TRANG))
_LOAI_10 = ["don_de_nghi", "don_de_nghi", "van_ban_uy_quyen", "van_ban_uy_quyen", "don_thay_doi_nguoi_tho_cung",
            "don_thay_doi_nguoi_tho_cung", "cccd", "bang_tqgc", "bang_tqgc", "trich_luc_khai_tu"]


def _plan_split(page_types, text=_TEXT_10):
    from app.pipelines.tro_cap_tho_cung_liet_si.attach import planner

    return planner.build_plan_items([{"name": "goc.pdf"}], [{"name": "goc.pdf", "text": text}], {}, {0: page_types})


def test_tach_moi_giay_mot_tep_vao_dung_o():
    items, warnings, classified = _plan_split(_LOAI_10)
    assert [(i["slotIndex"], i["documentName"], i["sourceSegments"][0]["pageIndexes"]) for i in items] == [
        (0, "Văn bản ủy quyền thờ cúng liệt sĩ", [2, 3]),
        (1, "Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt sĩ (Mẫu số 18)", [0]),
        (2, 'Bằng "Tổ quốc ghi công"', [7]),
        (1, "Đơn đề nghị thay đổi người thờ cúng liệt sĩ", [4, 5]),
        (1, "Căn cước công dân người nộp", [6]),
        (1, "Trích lục khai tử thân nhân liệt sĩ", [9]),
    ]
    assert {(i["target"], i["fileIndex"]) for i in items} == {("fixed-slot", 0)}
    assert not warnings
    assert classified[0]["source"] == "llm-pages"
    assert classified[0]["tachGiayTo"][0] == {"docType": "don_de_nghi", "pages": [1]}


def test_tach_ca_tep_mot_giay_khong_trang_trang_thi_khong_cat():
    text = "\n".join(f"───── Trang {n + 1}/2 ─────\n{_TRANG[n * 2]}" for n in range(2))
    items, _, _ = _plan_split(["don_de_nghi", "don_de_nghi"], text)
    assert len(items) == 1 and items[0]["slotKey"] == "don_de_nghi" and "sourceSegments" not in items[0]


def test_tach_trang_chua_ro_loai_van_dinh_o_don_va_canh_bao():
    trang = list(_TRANG)
    trang[9] = "HỢP ĐỒNG MUA BÁN " + "nội dung điều khoản thỏa thuận giữa các bên " * 8
    text = "\n".join(f"───── Trang {n + 1}/10 ─────\n{t}" for n, t in enumerate(trang))
    loai = list(_LOAI_10)
    loai[9] = "other"
    items, warnings, _ = _plan_split(loai, text)
    assert (items[-1]["slotKey"], items[-1]["documentName"]) == ("don_de_nghi", "Giấy tờ kèm theo")
    assert len(warnings) == 1


def test_tach_trang_other_it_chu_la_trang_noi_tiep_giay_truoc():
    # Mặt sau in xuyên: OCR ra một dòng tên cơ quan → không thành tệp "Giấy tờ kèm theo" riêng.
    loai = list(_LOAI_10)
    loai[9] = "other"
    items, warnings, classified = _plan_split(loai)
    assert [i["documentName"] for i in items if i["documentName"] == "Giấy tờ kèm theo"] == []
    assert next(i for i in items if i["slotKey"] == "bang_tqgc")["sourceSegments"][0]["pageIndexes"] == [7, 9]
    assert not warnings
    assert classified[0]["tachGiayTo"][-1] == {"docType": "bang_tqgc", "pages": [10]}


def test_don_thay_doi_nguoi_tho_cung_khong_lan_voi_mau_18():
    from app.pipelines.tro_cap_tho_cung_liet_si.attach import planner

    assert planner._rule_doc_type(_TRANG[4]) == "don_thay_doi_nguoi_tho_cung"
    assert planner._rule_doc_type(_TEXT_10) == "don_de_nghi"  # PDF gộp mở đầu Mẫu 18 (chế độ thường)
    assert planner._normalize_doc_type("Biên bản họp đồng thuận") == "van_ban_uy_quyen"
    assert planner._normalize_doc_type("don_thay_doi_nguoi_tho_cung") == "don_thay_doi_nguoi_tho_cung"


def _plan_e2e(monkeypatch, options):
    import asyncio

    from app.pipelines.tro_cap_tho_cung_liet_si.attach import planner
    from app.process.schemas import FileItem
    from app.services import ocr

    async def _ocr(files, **_k):
        return [{"name": f["name"], "text": _TEXT_10} for f in files]

    calls = []

    async def _chat(messages, **_k):
        calls.append(messages[0]["content"])
        return '{"tep":[{"fileIndex":0,"trang":%s}]}' % str(_LOAI_10).replace("'", '"')

    monkeypatch.setattr(ocr, "ocr_per_file", _ocr)
    monkeypatch.setattr(planner.client, "chat", _chat)
    monkeypatch.setattr(planner, "splittable_pages", lambda _f, text: planner.split_pages(text))
    files = [FileItem(name="goc.pdf", type="application/pdf", role="", dataUrl="data:application/pdf;base64,AA==")]
    return asyncio.run(planner.plan(files, options)), calls


def test_bat_cai_dat_thi_xep_trang_ca_tep_khop_luat_don(monkeypatch):
    result, calls = _plan_e2e(monkeypatch, {"splitDocuments": True, "supportsSourceSegments": True})
    assert len(calls) == 1 and "TỪNG TRANG" in calls[0]
    assert len(result["attachments"]) == 6 and result["extracted"]["splitDocuments"] is True


def test_tat_cai_dat_thi_dinh_nguyen_tep_khong_goi_llm(monkeypatch):
    result, calls = _plan_e2e(monkeypatch, {"splitDocuments": False})
    assert calls == []
    assert len(result["attachments"]) == 1 and "sourceSegments" not in result["attachments"][0]
    assert result["attachments"][0]["slotKey"] == "don_de_nghi"
    assert result["extracted"]["splitDocuments"] is False


def test_registry_cong_bo_ho_tro_tach():
    from app.channels.handfree.procedure_registry import get_procedure as hf_get
    from app.procedures.registry import get_procedure

    assert get_procedure("tro-cap-tho-cung-liet-si")["supportsSplitDocuments"] is True
    assert hf_get("tro-cap-tho-cung-liet-si")["supportsSplitDocuments"] is True
