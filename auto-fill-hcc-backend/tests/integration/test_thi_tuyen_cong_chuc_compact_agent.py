"""Compact agent Thi tuyển công chức: Phiếu đăng ký -> Form.io actions."""

import json

import httpx
import respx

from app.config import settings
from app.pipelines.thi_tuyen_cong_chuc import process as agent


def _file(name, typ="application/pdf"):
    return {"name": name, "type": typ, "dataUrl": "data:x;base64,AAA"}


def _disable_external_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")


def _mock_services(out):
    respx.post(settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw").mock(
        return_value=httpx.Response(200, json={"fullText": "OCR TEXT"})
    )
    respx.post(settings.llm_base_url.rstrip("/") + "/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {
                "content": "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
            }}]},
        )
    )


@respx.mock
async def test_thi_tuyen_cong_chuc_agent_maps_detailed_form(monkeypatch):
    _disable_external_fallbacks(monkeypatch)
    _mock_services({
        "fields": {
            "Phieu_ViTriViecLam": "Chuyên viên lĩnh vực tài chính: Quản lý tài chính – ngân sách nhà nước",
            "Phieu_CoQuanDuTuyen": "Phòng kinh tế xã Nậm Cuổi",
            "Phieu_HoTen": "Vàng Thị Thu",
            "Phieu_NgaySinh": "23/07/1994",
            "Phieu_GioiTinh": "Nữ",
            "Phieu_SoDinhDanh": "012194003716",
            "Phieu_NgayCap": "17/06/2021",
            "Phieu_NoiCap": "Công an tỉnh Hưng Yên",
            "Phieu_NoiThuongTru": {"tinh": "Tỉnh Hưng Yên", "xa": "Xã Hưng Hà", "diaChi": "Thôn Đồng Hàn"},
            "Phieu_DienThoai": "0963831658",
            "Phieu_VanBangChungChi": [
                {
                    "tenTruong": "ĐH Kinh tế Quốc dân",
                    "ngayCap": "29/03/2018",
                    "trinhDo": "Cử nhân",
                    "soHieu": "0700-MT56",
                    "chuyenNganh": "Kinh tế - Quản lý tài nguyên và môi trường",
                    "nganh": "Kinh tế",
                    "hinhThuc": "Chính quy",
                    "xepLoai": "Khá",
                }
            ],
            "Phieu_CoDoiTuongUuTien": "Có",
            "Phieu_DoiTuongUuTien": "Là người dân tộc thiểu số, sinh viên cử tuyển",
            "Phieu_DiemUuTien": "5",
            "Phieu_ThuTuUuTien": [{"tenCoQuan": "Phòng kinh tế xã Nậm Cuổi", "nguyenVong": "Nguyện vọng 1"}],
        }
    })

    res = await agent.run(
        {"doc": [_file("mau cong chuc.pdf")]},
        {"formContext": {"applicantFullname": "Vàng Thị Thu", "applicantIdentityNumber": "012194003716"}},
    )
    d = {f["name"]: f["value"] for f in res["fields"]}

    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "Vàng Thị Thu"
    assert d["data[VtVlDt]"].startswith("Chuyên viên lĩnh vực tài chính")
    assert d["data[DataGrid][0][TenTruong]"] == "ĐH Kinh tế Quốc dân"
    assert d["data[DataGrid2][0][txtNguyenVong]"] == "Nguyện vọng 1"
    assert not res["errors"]
