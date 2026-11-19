"""Công nhận và giải quyết chế độ ưu đãi người hoạt động kháng chiến bị nhiễm chất độc hóa học (Bộ Nội vụ, 1.010816).

Dữ liệu trong test là dữ liệu giả."""

import asyncio
import base64
import json

import fitz
import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.attach import planner as dieu_phoi
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.attach.dinh_kem_tach import planner as tach
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.process import mapper, runner
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.process.schema import UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.agency_level import with_agency_level
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.process.schemas import FileItem

KEY = "cong-nhan-che-do-khang-chien-nhiem-chat-doc-hoa-hoc"
_CHU_HO_SO = {"formContext": {"applicantFullname": "Lê Văn Mẫu", "applicantIdentityNumber": "048050000001"}}
_NOP_THAY = {"formContext": {"applicantFullname": "Phạm Thị Nộp", "applicantIdentityNumber": "048190000002"}}


def _values(**overrides):
    values = {
        "ChuHoSo_HoTen": "LÊ VĂN MẪU",
        "ChuHoSo_SoDinhDanh": "048050000001",
        "ChuHoSo_NgaySinh": "3/7/1950",
        "ChuHoSo_GioiTinh": "Nam",
        "ChuHoSo_NgayCap": "1/2/2021",
        "ChuHoSo_NoiCap": "Cục Csát QLý trật tự xã hội Bộ CA",
        "ChuHoSo_QueQuan": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Hòa Hải", "diaChi": ""},
        "ChuHoSo_NoiThuongTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "p. Hải Châu", "diaChi": "K12/3 Lê Lợi"},
        "ChuHoSo_DienThoai": "0905 000 111",
        "HDKC_TinhTrangSucKhoe": "Sức khỏe yếu, tiểu đường, cao huyết áp",
        "HDKC_QuaTrinh": [
            {"thoiGian": "Từ tháng ... năm ... đến tháng ... năm ..."},
            {"thoiGian": "1965 – 1967", "coQuan": "Du kích xã Mẫu", "diaBan": "Xã Mẫu, tỉnh Quảng Nam – Đà Nẵng cũ"},
            {"thoiGian": "Cuối 1970 – 1972", "coQuan": "Đội công tác", "diaBan": "Vùng giải phóng"},
        ],
        "HDKC_ConDe": [{"hoTen": "", "namSinh": ""}],
        "HoSoDinhKem": [
            {"tenGiayTo": "Bản khai Mẫu số 09", "loaiBan": "Bản chính"},
            {"tenGiayTo": "Quyết định phục viên", "loaiBan": "Bản sao chứng thực"},
            {"tenGiayTo": "Bản tóm tắt hồ sơ bệnh án", "loaiBan": "Bản chính"},
        ],
    }
    values.update(overrides)
    return values


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    by_key = {(f["name"], f.get("occurrence")): f["value"] for f in fields}
    return fields, by_key, warnings


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.010816"
    assert link["url"].endswith("019d2bfa-fc29-7229-b30a-9311da45f3ca")
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    assert proc["supportsSplitDocuments"] is True and proc["hasAttachmentStep"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    assert tach.__name__.split(".")[2] == KEY.replace("-", "_")


def test_tu_nop_dien_ca_ba_khoi_dung_occurrence():
    fields, got, warnings = _run(_values(), _CHU_HO_SO)
    assert fields[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": True}
    # Khối Người nộp (occurrence 0): chỉ ô cổng không khoá.
    assert got[("data[identityDate]", 0)] == "01/02/2021"
    assert got[("data[province]", 0)] == "Thành phố Đà Nẵng" and got[("data[district]", 0)] == "Phường Hải Châu"
    assert got[("data[address]", 0)] == "K12/3 Lê Lợi" and got[("data[phoneNumber]", 0)] == "0905000111"
    assert ("data[fullname]", 0) not in got and ("data[identityNumber]", 0) not in got
    # Chủ hồ sơ.
    assert got[("data[ownerFullname]", None)] == "LÊ VĂN MẪU"
    assert got[("data[ownerBirthday]", None)] == "03/07/1950"
    assert got[("data[ownerIdIssuePlace]", None)] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert got[("data[ownerDistrict]", None)] == "Phường Hải Châu"
    # Bản khai (key trùng khối Người nộp → occurrence 1; ô riêng không có occurrence).
    assert got[("data[fullname]", 1)] == "LÊ VĂN MẪU" and got[("data[identityNumber]", 1)] == "048050000001"
    assert got[("data[gender]", 1)] == "Nam" and got[("data[birthday]", 1)] == "03/07/1950"
    assert got[("data[identityAgency]", None)] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Quê quán: xã cũ đã sáp nhập → ô xã theo đơn vị mới, tên xã cũ giữ ở ô số nhà (bắt buộc).
    assert got[("data[province]", 1)] == "Thành phố Đà Nẵng"
    assert got[("data[village]", None)] == "Phường Ngũ Hành Sơn" and got[("data[address]", 1)] == "Hòa Hải"
    assert got[("data[village1]", None)] == "Phường Hải Châu" and got[("data[address1]", None)] == "K12/3 Lê Lợi"
    assert got[("data[tinhTrang]", None)] == "Sức khỏe yếu, tiểu đường, cao huyết áp"
    # Bảng quá trình: bỏ dòng in sẵn, giữ đúng thứ tự.
    assert got[("data[quaTrinh][0][thoiGian]", None)] == "1965 – 1967"
    assert got[("data[quaTrinh][1][thoiGian]", None)] == "Cuối 1970 – 1972"
    assert ("data[quaTrinh][2][thoiGian]", None) not in got
    assert not any(name.startswith("data[conDe]") for name, _ in got)
    # Hồ sơ kèm theo: Bản khai đứng đầu, bản chứng thực → "Bản sao".
    assert got[("data[hoSoDinhKem][0][textField1]", None)].startswith("Bản khai theo Mẫu số 09")
    assert got[("data[hoSoDinhKem][1][textField2]", None)] == "Bản sao"
    assert ("data[hoSoDinhKem][3][textField1]", None) not in got
    assert all(f["name"] in UI_COMP_BY_NAME for f in fields)
    assert warnings == []


def test_nop_thay_co_cccd_nguoi_nop():
    values = _values(NguoiNop_HoTen="Phạm Thị Nộp", NguoiNop_SoDinhDanh="048190000002", NguoiNop_NgayCap="05/06/2022",
                     NguoiNop_NoiCap="Bộ Công an", NguoiNop_NoiCuTru={"tinh": "Đà Nẵng", "xa": "Phường Hải Châu",
                                                                     "diaChi": "Số 5 Trần Phú"})
    fields, got, _ = _run(values, _NOP_THAY)
    assert fields[0]["name"] == "data[isOwnerDossierCheck]" and fields[0]["value"] is False
    assert got[("data[gender]", 0)] == "Nữ" and got[("data[identityDate]", 0)] == "05/06/2022"
    assert got[("data[address]", 0)] == "Số 5 Trần Phú" and got[("data[idIssuePlace]", None)] == "Bộ Công an"
    assert ("data[phoneNumber]", 0) not in got, "số điện thoại Bản khai là của chủ hồ sơ"
    assert got[("data[ownerFullname]", None)] == "LÊ VĂN MẪU" and got[("data[address]", 1)] == "Hòa Hải"


def test_nop_thay_khong_co_giay_to_thi_chi_dien_gioi_tinh_theo_so():
    _, got, warnings = _run(_values(), _NOP_THAY)
    assert got[("data[gender]", 0)] == "Nữ"
    assert not any(occ == 0 and name != "data[gender]" for name, occ in got)
    assert any("Người nộp khác người hoạt động kháng chiến" in w for w in warnings)


_THEO_TO_KHAI = {**_NOP_THAY, "submitterMode": "owner_as_submitter"}


def test_theo_to_khai_nguoi_nop_la_nguoi_khai_mo_khoa_o_tai_khoan():
    values = _values(NguoiNop_HoTen="Phạm Thị Nộp", NguoiNop_SoDinhDanh="048190000002", NguoiNop_NgayCap="05/06/2022")
    fields, got, warnings = _run(values, _THEO_TO_KHAI)
    by_occ = {(f["name"], f.get("occurrence")): f for f in fields}
    assert fields[0]["name"] == "data[isOwnerDossierCheck]" and fields[0]["value"] is True
    for name, value in (("data[fullname]", "LÊ VĂN MẪU"), ("data[identityNumber]", "048050000001"),
                        ("data[birthday]", "03/07/1950")):
        assert by_occ[(name, 0)]["value"] == value and by_occ[(name, 0)]["enableInput"] is True, name
    # Phần còn lại của người nộp theo người khai, không lấy CCCD người nộp thay / giới tính theo số tài khoản.
    assert got[("data[gender]", 0)] == "Nam" and got[("data[identityDate]", 0)] == "01/02/2021"
    assert got[("data[address]", 0)] == "K12/3 Lê Lợi" and got[("data[phoneNumber]", 0)] == "0905000111"
    # Bản khai vẫn occurrence 1.
    assert got[("data[fullname]", 1)] == "LÊ VĂN MẪU"
    assert any("Lấy người nộp theo tờ khai" in w and "Phạm Thị Nộp" in w for w in warnings)
    assert not any("Người nộp khác người hoạt động kháng chiến" in w for w in warnings)


def test_theo_to_khai_khong_co_ngay_sinh_thi_xoa_ngay_sinh_tai_khoan():
    fields, _, _ = _run(_values(ChuHoSo_NgaySinh=""), _THEO_TO_KHAI)
    birthday = next(f for f in fields if f["name"] == "data[birthday]" and f.get("occurrence") == 0)
    assert birthday["clear"] is True and birthday["markEmpty"] is True and birthday["value"] == ""


def test_theo_to_khai_trung_tai_khoan_khong_mo_khoa():
    fields, _, warnings = _run(_values(), {**_CHU_HO_SO, "submitterMode": "owner_as_submitter"})
    assert not any(f.get("enableInput") for f in fields)
    assert not any(f["name"] == "data[fullname]" and f.get("occurrence") == 0 for f in fields)
    assert warnings == []


def test_con_de_di_dang_va_canh_bao_thieu():
    values = _values(HDKC_ConDe=[{"hoTen": "Lê Văn Con", "namSinh": "1980", "giayTo": "GKS số 12",
                                  "tinhTrang": "Dị tật bẩm sinh"}],
                     HDKC_QuaTrinh=[], HDKC_TinhTrangSucKhoe="", ChuHoSo_DienThoai="")
    _, got, warnings = _run(values, _CHU_HO_SO)
    assert got[("data[conDe][0][hoTen]", None)] == "Lê Văn Con"
    assert got[("data[conDe][0][tinhTrang]", None)] == "Dị tật bẩm sinh"
    text = " ".join(warnings)
    assert "bảng quá trình" in text and "Tình trạng bệnh tật" in text and "số điện thoại" in text


_BAN_KHAI_OCR = (
    "BẢN KHAI Để giải quyết chế độ người hoạt động kháng chiến bị nhiễm chất độc hóa học\n"
    "1. Phần khai về người hoạt động kháng chiến bị nhiễm chất độc hóa học\nHọ và tên: LÊ VĂN MẪU\n"
    "CCCD số 048050000001\n2. Phần khai về con đẻ (trường hợp người hoạt động kháng chiến sinh con dị dạng)"
)


def test_context_neo_nguoi_nop():
    docs = [{"text": _BAN_KHAI_OCR},
            {"text": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 048190000002\nHọ và tên / Full name: PHẠM THỊ NỘP"}]
    own = asyncio.run(runner._context(docs, _CHU_HO_SO))
    assert 'result="owner_match"' in own and "<chu_ho_so_ocr" in own and "Phần khai về con" not in own
    other = asyncio.run(runner._context(docs, _NOP_THAY))
    assert 'result="co_giay_to"' in other and "PHẠM THỊ NỘP" in other
    none = asyncio.run(runner._context(docs[:1], _NOP_THAY))
    assert 'result="khong_giay_to"' in none
    # "Lấy người nộp theo tờ khai": có CCCD người nộp thay cũng không neo vào đó.
    theo_to_khai = asyncio.run(runner._context(docs, _THEO_TO_KHAI))
    assert 'result="owner_match"' in theo_to_khai and "cccd_nguoi_nop" not in theo_to_khai


# ---------------- Đính kèm: hai chế độ theo cài đặt "Tách giấy tờ" (gọi qua bộ điều phối) ----------------
# Tệp 0 gộp Bản khai (tr.1) + CCCD (tr.2) + Quyết định phục viên (tr.3) + Bản tóm tắt bệnh án (tr.4–5); tệp 1 ảnh
# giấy xác nhận giải mã phiên hiệu.
_PAGES = [
    _BAN_KHAI_OCR,
    "CĂN CƯỚC CÔNG DÂN Số / No.: 048050000001",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nQUYẾT ĐỊNH phục viên",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBẢN TÓM TẮT HỒ SƠ BỆNH ÁN",
    "Chẩn đoán ra viện: tiểu đường. Bác sĩ điều trị",
]
_TEXTS = {
    "ho-so-gop.pdf": "\n".join(f"───── Trang {p}/5 ─────\n{t}" for p, t in enumerate(_PAGES, start=1)),
    "phien-hieu.png": "GIẤY XÁC NHẬN thông tin giải mã phiên hiệu đơn vị",
}
_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "ban_khai_mau_09"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "cccd"},
    {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "giay_to_khang_chien"},
    {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "giay_to_mac_benh"},
    # Trang 5 LLM bỏ sót → nối tiếp bệnh án (không có quốc hiệu).
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "xac_nhan_phien_hieu"},
]
_TYPES = [
    {"index": 0, "docTypes": ["ban_khai_mau_09", "cccd", "giay_to_khang_chien", "giay_to_mac_benh"]},
    {"index": 1, "docTypes": ["xac_nhan_phien_hieu"]},
]


def _pdf(name, pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    doc.close()
    return FileItem(name=name, type="application/pdf", role="doc", dataUrl=f"data:application/pdf;base64,{data}")


def _plan(monkeypatch, options, *, split_fails=False, texts=None, segments=None, types=None, files=None):
    texts = texts or _TEXTS

    async def fake_ocr(items):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in items]

    async def fake_chat(messages, **_kwargs):
        if "docTypes" in messages[0]["content"]:  # prompt chế độ không tách
            return json.dumps({"documents": types or _TYPES})
        if split_fails:
            raise RuntimeError("LLM hết giờ")
        return json.dumps({"documents": segments or _SEGMENTS})

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr)
    monkeypatch.setattr("app.services.llm.client.chat", fake_chat)
    files = files or [_pdf("ho-so-gop.pdf", 5),
                      FileItem(name="phien-hieu.png", type="image/png", role="doc", dataUrl="data:image/png;base64,AAAA")]
    out = asyncio.run(dieu_phoi.plan(files, options))
    AttachmentPlanResp.model_validate(out)
    return out


def test_bat_tach_cat_dung_dong_khong_sot_trang(monkeypatch):
    out = _plan(monkeypatch, {"splitDocuments": True})
    attachments = out["attachments"]
    gop = [(a["componentIndex"], a["detectedType"], a["sourceSegments"][0]["pageIndexes"], a["loaiBan"])
           for a in attachments if a["fileIndex"] == 0]
    assert gop == [
        (1, "ban_khai_mau_09", [0], "Bản chính"), (1, "cccd", [1], "Bản chính"),
        (2, "giay_to_khang_chien", [2], "Bản sao"), (4, "giay_to_mac_benh", [3, 4], "Bản chính"),
    ]
    assert sorted(p for a in attachments if a["fileIndex"] == 0 for s in a["sourceSegments"] for p in s["pageIndexes"]) \
        == [0, 1, 2, 3, 4]
    phien_hieu = next(a for a in attachments if a["fileIndex"] == 1)
    assert phien_hieu["componentIndex"] == 2 and not phien_hieu.get("sourceSegments")
    assert all(a["target"] == "attp-row" for a in attachments)
    # Không có giấy xác nhận không có con đẻ → bỏ tick dòng 3.
    assert attachments[0]["untickRows"] == ["Giấy xác nhận người hoạt động kháng chiến có vợ hoặc có chồng"]
    assert not any("Chưa có" in e for e in out["errors"])


@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
def test_tat_tach_moi_tep_nguyen_mot_lan(monkeypatch, options):
    out = _plan(monkeypatch, options)
    attachments = out["attachments"]
    assert sorted(a["fileIndex"] for a in attachments) == [0, 1]
    assert not any(a.get("sourceSegments") for a in attachments)
    by_file = {a["fileIndex"]: a for a in attachments}
    # Tệp gộp giữ tên gốc (bỏ đuôi) để cán bộ nhận ra.
    assert by_file[0]["componentIndex"] == 1 and by_file[0]["documentName"] == "ho-so-gop"
    assert by_file[1]["componentIndex"] == 2 and by_file[1]["loaiBan"] == "Bản sao"
    assert any("ho-so-gop.pdf" in e and "gộp nhiều giấy" in e for e in out["errors"])
    assert not any("Chưa có giấy tờ ghi nhận mắc bệnh" in e for e in out["errors"]), "giấy trong tệp gộp không báo thiếu"


def test_bat_tach_ma_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    out = _plan(monkeypatch, {"splitDocuments": True}, split_fails=True)
    assert out["errors"][0].startswith("attachment_agent (tách)")
    assert sorted(a["fileIndex"] for a in out["attachments"]) == [0, 1]
    assert not any(a.get("sourceSegments") for a in out["attachments"])


def test_vo_sinh_bo_tick_dong_benh_va_bao_thieu_giay_khang_chien(monkeypatch):
    texts = {"ban-khai.pdf": _BAN_KHAI_OCR, "xac-nhan.pdf": "GIẤY XÁC NHẬN có vợ nhưng không có con đẻ"}
    segments = [{"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "ban_khai_mau_09"},
                {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "xac_nhan_khong_con_de"}]
    out = _plan(monkeypatch, {"splitDocuments": True}, texts=texts, segments=segments,
                files=[_pdf("ban-khai.pdf", 1), _pdf("xac-nhan.pdf", 1)])
    assert [a["componentIndex"] for a in out["attachments"]] == [1, 3]
    assert out["attachments"][0]["untickRows"] == ["giấy tờ ghi nhận mắc bệnh"]
    assert any("thời gian tham gia kháng chiến" in e for e in out["errors"])


def test_rule_type_ban_khai_thang_ghi_chu_khong_con_de():
    assert tach._rule_type(_BAN_KHAI_OCR + "\nGhi chú: có vợ hoặc có chồng nhưng không có con đẻ") == "ban_khai_mau_09"
    assert tach._rule_type("BẢN TÓM TẮT HỒ SƠ BỆNH ÁN") == "giay_to_mac_benh"
    assert tach._normalize_type("Quyết định phục viên") == "giay_to_khang_chien"


# ---------------- Trợ lý người dân ----------------
@pytest.mark.parametrize(("role", "ward", "so"), [("province", "", True), ("commune", "Phường Hải Châu", False)])
def test_tro_ly_tinh_vao_so_xa_chon_xa(role, ward, so):
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(KEY)
    assert proc["supportsSplitDocuments"] is True and proc["keKhaiUrl"].endswith("9311da45f3ca")
    merged = with_agency_level(proc, role, ward)
    assert bool(merged.get("agencySoFirst")) is so and bool(merged.get("agencyProvinceOnly")) is so
    assert (merged["maeAgencyLevel"] == "ward") is not so
