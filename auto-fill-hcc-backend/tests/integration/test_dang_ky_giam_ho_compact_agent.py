"""Compact agent đăng ký giám hộ: OCR text -> source facts -> iframe UI fields."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.dang_ky_giam_ho import process as agent
from app.pipelines.dang_ky_giam_ho.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_giam_ho.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


@respx.mock
async def test_dang_ky_giam_ho_derives_iframe_fields(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "type": f["type"], "text": "OCR text", "provider": "raw"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Requester_FullName": "Nguyễn Thị Phương Thảo",
            "Requester_IdNumber": "011192002254",
            "Requester_IdIssueDate": "25/04/2021",
            "Requester_IdIssuePlace": "Cục Cảnh sát QLHC về TTXH",
            "Requester_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Tân Phong",
                "diaChi": "Tổ 1",
            },
            "Guardian_FullName": "Hà Thị Kiều",
            "Guardian_BirthDate": "05/01/1970",
            "Guardian_Gender": "Nữ",
            "Guardian_Ethnicity": "Kinh",
            "Guardian_Nationality": "Việt Nam",
            "Guardian_IdNumber": "011170001926",
            "Guardian_IdIssueDate": "10/05/2021",
            "Guardian_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Guardian_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Đông Phong",
                "diaChi": "Tổ 22",
            },
            "Ward_FullName": "Bùi Gia Hoàng Thịnh",
            "Ward_BirthDate": "04/08/2018",
            "Ward_Gender": "Nam",
            "Ward_Ethnicity": "Mường",
            "Ward_Nationality": "Việt Nam",
            "Ward_IdNumber": "012218001675",
            "Ward_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Tân Phong",
                "diaChi": "Tổ 1",
            },
            "Ward_BirthCertificateNumber": "234",
            "Ward_BirthCertificateIssueDate": "08/10/2018",
            "Ward_BirthCertificateIssuePlace": "UBND phường Tân Phong",
            "Ward_BirthCertificateInfo": "Giấy khai sinh số 234, UBND phường Tân Phong cấp ngày 08/10/2018",
            "Registration_Agency": "UBND phường Tân Phong",
            "Registration_RelationshipType": "Bà ngoại giám hộ cho cháu",
            "Registration_Reason": "Mẹ đi công tác xa, ủy quyền giám hộ cho bà ngoại chăm sóc",
            "CopyRequest_WantsCopy": "Có",
            "CopyRequest_Quantity": "05",
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run(
        {
            "doc": [
                _file("tờ khai đăng ký giám hộ.pdf"),
                _file("cccd người yêu cầu.pdf"),
                _file("cccd người giám hộ.pdf"),
                _file("giấy khai sinh.pdf"),
            ]
        },
        {},
    )
    by_name = {f["name"]: f for f in res["fields"]}
    d = {name: f["value"] for name, f in by_name.items()}

    assert d["HoVaTenC"] == "NGUYỄN THỊ PHƯƠNG THẢO"
    assert d["SoDinhDanhC"] == "011192002254"
    assert d["LoaiGiayToDinhDanhC"] == "Thẻ căn cước công dân"
    assert d["NgayCapDDC"] == "25/04/2021"
    assert d["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["TT_SoNhaToDanPhoC"] == "Tổ 1"
    assert d["TT_TinhThanhC"] == "Tỉnh Lai Châu"
    assert d["TT_PhuongXaC"] == "Phường Tân Phong"

    assert d["hotenA"] == "HÀ THỊ KIỀU"
    assert d["ngaysinhA"] == "05/01/1970"
    assert d["gioitinhA"] == "Nữ"
    assert d["dantocA"] == "Kinh"
    assert d["quoctichA"] == "Việt Nam"
    assert d["sodinhdanhA"] == "011170001926"
    assert d["loaigiaytoA"] == "Thẻ căn cước công dân"
    assert d["sodinhdanhA1"] == "011170001926"
    assert d["ngaycapA"] == "10/05/2021"
    assert d["noicapA"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["cutru1"] == "Thường trú"
    assert d["noicutruA"] == "Tổ 22"
    assert d["tinhA"] == "Tỉnh Lai Châu"
    assert d["xaA"] == "Phường Đông Phong"

    assert d["hotenB"] == "BÙI GIA HOÀNG THỊNH"
    assert d["ngaysinhB"] == "04/08/2018"
    assert d["gioitinhB"] == "Nam"
    assert d["dantocB"] == "Mường"
    assert d["quoctichB"] == "Việt Nam"
    assert d["sodinhdanhB"] == "012218001675"
    assert d["loaigiaytoB"] == "Giấy tờ khác bao gồm các giấy tờ có dán"
    assert d["sodinhdanhB1"] == "234"
    assert d["ngaycapB"] == "08/10/2018"
    assert d["noicapB"] == "UBND phường Tân Phong"
    assert d["cutru2"] == "Thường trú"
    assert d["noicutruB"] == "Tổ 1"
    assert d["TinhB"] == "Tỉnh Lai Châu"
    assert d["XaB"] == "Phường Tân Phong"

    assert d["lydo"] == "Mẹ đi công tác xa, ủy quyền giám hộ cho bà ngoại chăm sóc"
    assert d["CapBanSao"] == "Có"
    assert by_name["CapBanSao"]["comp"] == "x-radio"
    assert d["soluong"] == "05"
    assert by_name["soluong"]["comp"] == "raw"
    # DOM hiện tại không có field điện thoại/email người yêu cầu.
    assert "SoLuong" not in d
    assert "phoneNumber" not in d
    assert not res["errors"]


@respx.mock
async def test_dang_ky_giam_ho_falls_back_ward_residence_and_birth_certificate(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    ocr_text = """
TỜ KHAI ĐĂNG KÝ GIÁM HỘ
Họ, chữ đệm, tên người yêu cầu: Nguyễn Thị Phương Thảo
Nơi cư trú: Tổ 1 phường Tân Phong, Thành phố Lai Châu, Tỉnh Lai Châu
Giấy tờ tùy thân: 011192002254 cấp 25/4/2021 do Cục cảnh sát QLHC và TTXH cấp

Người giám hộ:
Họ, chữ đệm, tên: Hà Thị Kiều
Ngày, tháng, năm sinh: 05/01/1970
Giới tính: Nữ Dân tộc: Kinh Quốc tịch: Việt Nam
Nơi cư trú: Tổ 22 phường Tân Phong, Tp Lai Châu, Tỉnh Lai Châu
Giấy tờ tùy thân: 011170001926 cấp ngày 10/5/2021 do Cục cảnh sát QLHC và TTXH cấp

Người được giám hộ:
Họ, chữ đệm, tên: Bùi Gia Hoàng Thịnh
Ngày, tháng, năm sinh: 04/8/2018
Giới tính: Nam Dân tộc: Mường Quốc tịch: Việt Nam
Nơi cư trú: Tổ 1 phường Tân Phong, Tp Lai Châu, tỉnh Lai Châu
Giấy khai sinh/Giấy tờ tùy thân: 012218001675 Giấy khai sinh số 234 do UBND phường Tân Phong cấp ngày 08/10/2018
Lý do đăng ký giám hộ: Mẹ đi công tác xa ủy quyền giám hộ cho bà ngoại cháu
Đề nghị cấp bản sao: Có, Không
Số lượng: 05 bản
"""

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "type": f["type"], "text": ocr_text, "provider": "gemini"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Requester_FullName": "Nguyễn Thị Phương Thảo",
            "Requester_IdNumber": "011192002254",
            "Requester_IdIssueDate": "25/04/2021",
            "Requester_IdIssuePlace": "Cục cảnh sát QLHC và TTXH",
            "Requester_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Tân Phong",
                "diaChi": "Tổ 1",
            },
            "Guardian_FullName": "Hà Thị Kiều",
            "Guardian_BirthDate": "05/01/1970",
            "Guardian_Gender": "Nữ",
            "Guardian_Ethnicity": "Kinh",
            "Guardian_Nationality": "Việt Nam",
            "Guardian_IdNumber": "011170001926",
            "Guardian_IdIssueDate": "10/05/2021",
            "Guardian_IdIssuePlace": "Cục cảnh sát QLHC và TTXH",
            "Guardian_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Tân Phong",
                "diaChi": "Tổ 22",
            },
            "Ward_FullName": "Bùi Gia Hoàng Thịnh",
            "Ward_BirthDate": "04/08/2018",
            "Ward_Gender": "Nam",
            "Ward_Ethnicity": "Mường",
            "Ward_Nationality": "Việt Nam",
            "Ward_IdNumber": "012218001675",
            "Ward_BirthCertificateInfo": "Số 234; Nơi đăng ký khai sinh: Uỷ ban nhân dân Phường Tân Phong, thành phố Lai Châu, tỉnh Lai Châu; Ngày đăng ký: 08/10/2018",
            "Registration_Reason": "Mẹ đi công tác xa ủy quyền giám hộ cho bà ngoại cháu",
            "CopyRequest_WantsCopy": "Có",
            "CopyRequest_Quantity": "5",
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run({"doc": [_file("tờ khai đăng ký giám hộ.pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["cutru2"] == "Thường trú"
    assert d["noicutruB"] == "Tổ 1"
    assert d["TinhB"] == "Tỉnh Lai Châu"
    assert d["XaB"] == "Phường Tân Phong"
    assert d["loaigiaytoB"] == "Giấy tờ khác bao gồm các giấy tờ có dán"
    assert d["sodinhdanhB1"] == "234"
    assert d["ngaycapB"] == "08/10/2018"
    assert d["noicapB"] == "UBND phường Tân Phong"
    assert d["soluong"] == "5"
    assert not res["errors"]


@respx.mock
async def test_dang_ky_giam_ho_prefers_ward_identity_doc_over_birth_certificate(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    ocr_text = """
TỜ KHAI ĐĂNG KÝ GIÁM HỘ
Họ, chữ đệm, tên người yêu cầu: CHẺO TON SƠN
Ngày, tháng, năm sinh: 12/09/1999
Nơi cư trú: Tổ dân phố Sùng Phải, phường Đoàn Kết, tỉnh Lai Châu
Giấy tờ tùy thân: CCCD số: 012099002088, Cục Cảnh sát QLHC về TTXH cấp ngày 17/05/2023.

Người giám hộ:
Họ, chữ đệm, tên: HOÀNG A TOAN
Ngày, tháng, năm sinh: 25/09/1981
Giới tính: Nam Dân tộc: Dao Quốc tịch: Việt Nam
Nơi cư trú: Tổ dân phố Căn Câu, phường Đoàn Kết, tỉnh Lai Châu
Giấy tờ tùy thân: Thẻ CCCD số: 012081000601, Cục Cảnh sát QLHC về TTXH cấp ngày 22/04/2021

Người được giám hộ:
Họ, chữ đệm, tên: CHẺO YẾN NHI
Ngày, tháng, năm sinh: 05/12/2020
Giới tính: Nữ Dân tộc: Dao Quốc tịch: Việt Nam
Nơi cư trú: Tổ dân phố Căn Câu, phường Đoàn Kết, tỉnh Lai Châu
Giấy khai sinh/Giấy tờ tùy thân: Thẻ CC số: 012320003527, Bộ Công an cấp ngày
16/08/2024.
Lý do đăng ký giám hộ: Bố mẹ đi làm ăn xa, không có khả năng chăm sóc, giáo dục con.
"""

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "type": f["type"], "text": ocr_text, "provider": "gemini"} for f in files]

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    out = {
        "fields": {
            "Requester_FullName": "CHẺO TON SƠN",
            "Requester_IdNumber": "012099002088",
            "Requester_IdIssueDate": "17/05/2023",
            "Requester_IdIssuePlace": "Cục Cảnh sát QLHC về TTXH",
            "Requester_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Đoàn Kết",
                "diaChi": "Tổ dân phố Sùng Phải",
            },
            "Guardian_FullName": "HOÀNG A TOAN",
            "Guardian_BirthDate": "25/09/1981",
            "Guardian_Gender": "Nam",
            "Guardian_Ethnicity": "Dao",
            "Guardian_Nationality": "Việt Nam",
            "Guardian_IdNumber": "012081000601",
            "Guardian_IdIssueDate": "22/04/2021",
            "Guardian_IdIssuePlace": "Cục CS QLHC về TTXH",
            "Guardian_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Đoàn Kết",
                "diaChi": "Tổ dân phố Căn Câu",
            },
            "Ward_FullName": "CHẺO YẾN NHI",
            "Ward_BirthDate": "05/12/2020",
            "Ward_Gender": "Nữ",
            "Ward_Ethnicity": "Dao",
            "Ward_Nationality": "Việt Nam",
            "Ward_IdNumber": "012320003527",
            "Ward_ResidenceDomestic": {
                "quocGia": "Việt Nam",
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Đoàn Kết",
                "diaChi": "BẢN CĂN CÂU",
            },
            "Ward_BirthCertificateNumber": "35",
            "Ward_BirthCertificateIssueDate": "03/02/2021",
            "Ward_BirthCertificateIssuePlace": "Ủy ban nhân dân Xã Sùng Phài, thành phố Lai Châu, tỉnh Lai Châu",
            "Registration_Reason": "Bố mẹ đi làm ăn xa, không có khả năng chăm sóc, giáo dục con.",
            "CopyRequest_WantsCopy": "Có",
        }
    }
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )

    res = await agent.run({"doc": [_file("tờ khai đăng ký giám hộ.pdf"), _file("giấy khai sinh.pdf")]}, {})
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["loaigiaytoA"] == "Thẻ căn cước công dân"
    assert d["sodinhdanhB"] == "012320003527"
    assert d["loaigiaytoB"] == "Thẻ Căn cước"
    assert d["sodinhdanhB1"] == "012320003527"
    assert d["ngaycapB"] == "16/08/2024"
    assert d["noicapB"] == "Bộ Công an"
    assert not res["errors"]


def test_dang_ky_giam_ho_prompt_locks_roles_and_ui_contract():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Đăng ký giám hộ" in system_prompt
    assert "người yêu cầu đăng ký giám hộ -> Requester_*" in system_prompt
    assert "người giám hộ -> Guardian_*" in system_prompt
    assert "người được giám hộ -> Ward_*" in system_prompt
    assert "Không trả field UI như HoVaTenC, hotenA, hotenB" in system_prompt
    assert "CSDL dân cư chỉ là nguồn fallback" in system_prompt
    assert "Số định danh cá nhân" in system_prompt
    assert "Ward_BirthCertificateNumber" in system_prompt
    assert "BẮT BUỘC trả Ward_ResidenceDomestic" in system_prompt
    assert "Thẻ CC số: 012320003527, Bộ Công an cấp ngày 16/08/2024" in system_prompt


def test_dang_ky_giam_ho_registered_with_process_and_attachment_step():
    proc = get_procedure("dang-ky-giam-ho")

    assert proc
    assert proc["label"] == "Thủ tục đăng ký giám hộ"
    assert proc["mode"] == "agent"
    assert proc["roles"] == []
    assert proc["hasAttachmentStep"] is True
    assert get_pipeline("dang-ky-giam-ho") is agent.run
    assert get_attach_pipeline("dang-ky-giam-ho") is not None
