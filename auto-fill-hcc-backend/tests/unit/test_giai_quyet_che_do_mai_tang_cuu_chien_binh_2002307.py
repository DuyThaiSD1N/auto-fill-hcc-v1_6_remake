"""Giải quyết chế độ mai táng phí đối với cựu chiến binh (Bộ Nội vụ, 2.002307).

Dữ liệu trong test là dữ liệu giả."""

import asyncio
import base64
import json

import fitz
import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.giai_quyet_che_do_mai_tang_cuu_chien_binh_2002307.attach import planner as dieu_phoi
from app.pipelines.giai_quyet_che_do_mai_tang_cuu_chien_binh_2002307.attach.dinh_kem_tach import planner as tach
from app.pipelines.giai_quyet_che_do_mai_tang_cuu_chien_binh_2002307.process import mapper, runner
from app.pipelines.giai_quyet_che_do_mai_tang_cuu_chien_binh_2002307.process.schema import UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.process.schemas import FileItem

KEY = "giai-quyet-che-do-mai-tang-cuu-chien-binh-2002307"
_NGUOI_NHAN = {"formContext": {"applicantFullname": "Nguyễn Văn Nhận", "applicantIdentityNumber": "034203000011"}}
_NOP_THAY = {"formContext": {"applicantFullname": "Lê Thị Nộp", "applicantIdentityNumber": "034190000022"}}
_THEO_TO_KHAI = {**_NOP_THAY, "submitterMode": "owner_as_submitter"}


def _values(**overrides):
    values = {
        "ChuHoSo_HoTen": "NGUYỄN VĂN NHẬN",
        "ChuHoSo_SoDinhDanh": "034203000011",
        "ChuHoSo_NgaySinh": "3/12/2003",
        "ChuHoSo_GioiTinh": "Nam",
        "ChuHoSo_NgayCap": "22/4/2021",
        "ChuHoSo_NoiCap": "Cục trưởng Cục Cảnh sát QLHC về TTXH",
        "ChuHoSo_QueQuan": {"quocGia": "Việt Nam", "tinh": "Thái Bình", "huyen": "Vũ Thư", "xa": "Minh Quang",
                            "chiTietDuoiXa": ""},
        "ChuHoSo_NoiThuongTru": {"quocGia": "Việt Nam", "tinh": "Thái Bình", "huyen": "Huyện Vũ Thư",
                                 "xa": "Xã Minh Quang", "chiTietDuoiXa": "Thôn Mẫu"},
        "ChuHoSo_DienThoai": "0900 000 111",
        "ChuHoSo_QuanHe": "cháu nội (con trai của ông A – con trai cả của cựu chiến binh), là người trực tiếp tổ chức "
                          "mai táng",
        "ToChucNhan_Ten": "Không áp dụng",
        "CCB_HoTen": "NGUYỄN VĂN MẪU",
        "CCB_NgaySinh": "15/3/1950",
        "CCB_GioiTinh": "Nam",
        "CCB_QueQuan": {"quocGia": "Việt Nam", "tinh": "Thái Bình", "huyen": "Huyện Vũ Thư", "xa": "Xã Minh Quang",
                        "chiTietDuoiXa": ""},
        "CCB_NoiThuongTru": {"quocGia": "Việt Nam", "tinh": "Hưng Yên", "xa": "Xã Vũ Thư", "chiTietDuoiXa": "Thôn Mẫu"},
        "CCB_DoiTuong": "Cựu chiến binh (kháng chiến chống Mỹ, nhập ngũ 1970, phục viên 1975)",
        "CCB_NgayChet": "07/11/2026",
        "CCB_LoaiGiayChungTu": "Trích lục khai tử",
        "CCB_SoGiayChungTu": "Số: 99/TLKT",
        "CCB_NgayCapGiayChungTu": "10/11/2026",
        "CCB_NoiCapGiayChungTu": "UBND xã Vũ Thư, tỉnh Hưng Yên",
        "HoSoDinhKem": [
            {"tenGiayTo": "Bản khai Mẫu số 01", "loaiBan": "Bản chính"},
            {"tenGiayTo": "Bản sao chứng thực Trích lục khai tử số 99/TLKT", "loaiBan": "Bản sao chứng thực"},
            {"tenGiayTo": "Giấy xác nhận cựu chiến binh số 9/GXN-BCHQS", "loaiBan": "Bản chính"},
            {"tenGiayTo": "Căn cước công dân", "loaiBan": "Bản sao"},
        ],
    }
    values.update(overrides)
    return {k: v for k, v in values.items() if v is not None}


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    by_key = {(f["name"], f.get("occurrence")): f["value"] for f in fields}
    return fields, by_key, warnings


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.002307"
    assert link["url"].endswith("019d2bfb-4a4e-7368-a306-f665291850ca")
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    assert proc["supportsSplitDocuments"] is True and proc["hasAttachmentStep"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    assert tach.__name__.split(".")[2] == KEY.replace("-", "_")


def test_tu_nop_dien_du_cac_khoi_dung_occurrence():
    fields, got, warnings = _run(_values(), _NGUOI_NHAN)
    assert fields[0] == {"name": "data[isOwnerDossierCheck]", "comp": "dom-checkbox", "value": True}
    # Khối Người nộp (occurrence 0): cổng khoá họ tên / CCCD, ngày sinh đổ sẵn → không phát; giới tính sửa "Nữ" mặc định.
    assert ("data[fullname]", 0) not in got and ("data[identityNumber]", 0) not in got and ("data[birthday]", 0) not in got
    assert got[("data[gender]", 0)] == "Nam"
    assert got[("data[identityDate]", None)] == "22/04/2021"
    assert got[("data[idIssuePlace]", None)] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Xã cũ "Minh Quang" có ở hai huyện của Thái Bình → khoá huyện cũ chọn đúng Xã Vũ Thư, Hưng Yên.
    assert got[("data[province]", 0)] == "Tỉnh Hưng Yên" and got[("data[district]", 0)] == "Xã Vũ Thư"
    assert got[("data[address]", 0)] == "Thôn Mẫu" and got[("data[phoneNumber]", None)] == "0900000111"
    # Chủ hồ sơ = người nhận trợ cấp.
    assert got[("data[chonDoiTuong1]", None)] == "Cá nhân"
    assert got[("data[ownerFullname]", None)] == "NGUYỄN VĂN NHẬN" and got[("data[ownerGender]", None)] == "Nam"
    assert got[("data[ownerBirthday]", None)] == "03/12/2003" and got[("data[ownerDistrict]", None)] == "Xã Vũ Thư"
    assert got[("data[ghiChu]", None)] == ("Đề nghị giải quyết chế độ trợ cấp mai táng đối với cựu chiến binh NGUYỄN VĂN "
                                           "MẪU (sinh 15/03/1950, chết ngày 07/11/2026); người nhận trợ cấp: NGUYỄN VĂN "
                                           "NHẬN – cháu nội")
    # Hồ sơ kèm theo: Bản khai đứng đầu, bản chứng thực → "Bản sao", CCCD không phải thành phần hồ sơ.
    assert got[("data[hoSoDinhKem][0][textField1]", None)].startswith("Bản khai đề nghị giải quyết chế độ trợ cấp mai")
    assert got[("data[hoSoDinhKem][1][textField2]", None)] == "Bản sao"
    assert got[("data[hoSoDinhKem][2][textField1]", None)].startswith("Giấy xác nhận cựu chiến binh")
    assert ("data[hoSoDinhKem][3][textField1]", None) not in got
    # Người có công từ trần = cựu chiến binh (key trùng khối Người nộp → occurrence 1).
    assert got[("data[fullname]", 1)] == "NGUYỄN VĂN MẪU" and got[("data[birthday]", 1)] == "15/03/1950"
    assert got[("data[gender]", 1)] == "Nam"
    assert got[("data[province2]", None)] == "Tỉnh Hưng Yên" and got[("data[district2]", None)] == "Xã Vũ Thư"
    assert got[("data[address2]", None)] == "Xã Minh Quang cũ", "ô Số nhà, đường (bắt buộc) giữ tên xã cũ"
    assert got[("data[district3]", None)] == "Xã Vũ Thư" and got[("data[address3]", None)] == "Thôn Mẫu"
    assert got[("data[ttncc_DoiTuong]", None)].startswith("Cựu chiến binh (")
    assert got[("data[ttncc_NgayTuTran]", None)] == "07/11/2026"
    assert got[("data[ttncc_GiayChungTu]", None)] == "Trích lục khai tử số 99/TLKT"
    assert got[("data[ttncc_NgayCap]", None)] == "10/11/2026"
    assert got[("data[ttncc_CoQuanCap]", None)] == "Ủy ban nhân dân xã Vũ Thư, tỉnh Hưng Yên"
    # Người nhận mai táng phí = chủ hồ sơ; trú quán dùng lại key khối Người nộp (occurrence 1).
    assert got[("data[fullname1]", None)] == "NGUYỄN VĂN NHẬN" and got[("data[gender1]", None)] == "Nam"
    assert got[("data[birthday1]", None)] == "03/12/2003"
    assert got[("data[province1]", None)] == "Tỉnh Hưng Yên" and got[("data[district1]", None)] == "Xã Vũ Thư"
    assert got[("data[address1]", None)] == "Minh Quang cũ", "CCCD không ghi loại đơn vị → không tự đoán \"Xã\""
    assert got[("data[province]", 1)] == "Tỉnh Hưng Yên" and got[("data[address]", 1)] == "Thôn Mẫu"
    assert got[("data[ttnn_QuanHe]", None)] == "Cháu nội"
    # Khối trợ cấp một lần / thân nhân người có công không áp dụng.
    assert not any(name.startswith(("data[fullname2]", "data[tnncc_", "data[nntc_")) for name, _ in got)
    assert all(f["name"] in UI_COMP_BY_NAME for f in fields)
    assert warnings == []


def test_nop_thay_co_cccd_nguoi_nop():
    values = _values(NguoiNop_HoTen="Lê Thị Nộp", NguoiNop_SoDinhDanh="034190000022", NguoiNop_NgayCap="05/06/2022",
                     NguoiNop_NoiCap="Bộ Công an",
                     NguoiNop_NoiCuTru={"tinh": "Hưng Yên", "xa": "Xã Vũ Thư", "chiTietDuoiXa": "Số 5 Đường Mẫu"})
    fields, got, _ = _run(values, _NOP_THAY)
    assert fields[0]["name"] == "data[isOwnerDossierCheck]" and fields[0]["value"] is False
    assert got[("data[gender]", 0)] == "Nữ" and got[("data[identityDate]", None)] == "05/06/2022"
    assert got[("data[address]", 0)] == "Số 5 Đường Mẫu" and got[("data[idIssuePlace]", None)] == "Bộ Công an"
    assert ("data[phoneNumber]", None) not in got, "số điện thoại Bản khai là của người nhận trợ cấp"
    assert got[("data[ownerFullname]", None)] == "NGUYỄN VĂN NHẬN" and got[("data[address]", 1)] == "Thôn Mẫu"


def test_nop_thay_khong_co_giay_to_chi_sua_gioi_tinh_theo_so():
    _, got, warnings = _run(_values(), _NOP_THAY)
    assert got[("data[gender]", 0)] == "Nữ"
    assert not any(occ == 0 and name != "data[gender]" for name, occ in got)
    assert ("data[identityDate]", None) not in got
    assert any("Người nộp khác người nhận trợ cấp" in w for w in warnings)


def test_theo_to_khai_mo_khoa_o_tai_khoan_va_xoa_ngay_sinh_khi_thieu():
    fields, got, warnings = _run(_values(), _THEO_TO_KHAI)
    by_occ = {(f["name"], f.get("occurrence")): f for f in fields}
    assert fields[0]["name"] == "data[isOwnerDossierCheck]" and fields[0]["value"] is True
    for name, value in (("data[fullname]", "NGUYỄN VĂN NHẬN"), ("data[identityNumber]", "034203000011"),
                        ("data[birthday]", "03/12/2003")):
        assert by_occ[(name, 0)]["value"] == value and by_occ[(name, 0)]["enableInput"] is True, name
    assert got[("data[gender]", 0)] == "Nam", "không lấy giới tính theo số tài khoản"
    assert got[("data[fullname]", 1)] == "NGUYỄN VĂN MẪU"
    assert any("Lấy người nộp theo tờ khai" in w and "Lê Thị Nộp" in w for w in warnings)

    fields, _, _ = _run(_values(ChuHoSo_NgaySinh=None), _THEO_TO_KHAI)
    birthday = next(f for f in fields if f["name"] == "data[birthday]" and f.get("occurrence") == 0)
    assert birthday["clear"] is True and birthday["markEmpty"] is True and birthday["value"] == ""


def test_khong_co_cccd_nguoi_nhan_thi_canh_bao_dia_chi():
    values = _values(ChuHoSo_QueQuan=None, ChuHoSo_NoiThuongTru=None, ChuHoSo_DienThoai=None)
    _, got, warnings = _run(values, _NGUOI_NHAN)
    assert ("data[province]", 1) not in got and ("data[province1]", None) not in got
    assert ("data[province]", 0) not in got, "không lấy địa chỉ cựu chiến binh cho người nhận"
    text = " ".join(warnings)
    assert "nơi thường trú" in text and "quê quán người nhận" in text and "số điện thoại" in text


def test_to_chuc_nhan_tro_cap_canh_bao_nhap_tay():
    values = _values(ChuHoSo_HoTen=None, ChuHoSo_SoDinhDanh=None, ChuHoSo_NgaySinh=None, ChuHoSo_GioiTinh=None,
                     ChuHoSo_NgayCap=None, ChuHoSo_NoiCap=None, ChuHoSo_QueQuan=None, ChuHoSo_NoiThuongTru=None,
                     ChuHoSo_DienThoai=None, ChuHoSo_QuanHe=None, ToChucNhan_Ten="Hội Cựu chiến binh xã Mẫu")
    _, got, warnings = _run(values, _NGUOI_NHAN)
    assert ("data[ownerFullname]", None) not in got and ("data[fullname1]", None) not in got
    assert got[("data[fullname]", 1)] == "NGUYỄN VĂN MẪU"
    assert any("Hội Cựu chiến binh xã Mẫu" in w and "Tổ chức/Doanh nghiệp" in w for w in warnings)


_BAN_KHAI_OCR = (
    "Mẫu số 01 Thông tư số 21/2026/TT-BNV\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBẢN KHAI CỦA CÁ NHÂN HOẶC TỔ CHỨC ĐỀ "
    "NGHỊ GIẢI QUYẾT CHẾ ĐỘ TRỢ CẤP MAI TÁNG ĐỐI VỚI CỰU CHIẾN BINH ĐÃ CHẾT\n1. Họ và tên cựu chiến binh: NGUYỄN VĂN "
    "MẪU\nGiấy chứng tử số 99/TLKT (Trích lục khai tử) ngày 10 tháng 11 năm 2026\n2. Cá nhân hoặc tổ chức nhận trợ cấp "
    "mai táng:\na) Cá nhân\nHọ và tên: NGUYỄN VĂN NHẬN\nSố định danh cá nhân: 034203000011\nVũ Thư, ngày 26 tháng 11 "
    "năm 2026\nXác nhận của UBND cấp xã"
)
_TRICH_LUC_OCR = (
    "ỦY BAN NHÂN DÂN XÃ VŨ THƯ\nSố: 99/TLKT\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTRÍCH LỤC KHAI TỬ\nHọ, chữ đệm, tên: "
    "NGUYỄN VĂN MẪU\nNơi cư trú cuối cùng: Thôn Mẫu, xã Vũ Thư, tỉnh Hưng Yên\nLỜI CHỨNG CHỨNG THỰC BẢN SAO TỪ BẢN CHÍNH"
)
_GXN_OCR = (
    "ỦY BAN NHÂN DÂN XÃ VŨ THƯ BAN CHỈ HUY QUÂN SỰ\nSố: 9/GXN-BCHQS\nGIẤY XÁC NHẬN CỰU CHIẾN BINH\nHọ và tên: NGUYỄN "
    "VĂN MẪU\nNgày từ trần: 07/11/2026 (Trích lục khai tử số 99/TLKT ngày 10/11/2026 của UBND xã Vũ Thư)"
)
_GXN_KY_OCR = (
    "Giấy xác nhận này cấp cho gia đình ông Nguyễn Văn Mẫu để làm hồ sơ giải quyết chế độ trợ cấp mai táng.\nTM. HỘI "
    "CỰU CHIẾN BINH XÃ CHỦ TỊCH (đã ký)\nCHỈ HUY TRƯỞNG BAN CHỈ HUY QUÂN SỰ XÃ (đã ký)"
)
_CCCD_OCR = "CĂN CƯỚC CÔNG DÂN Số / No.: 034203000011 Họ và tên / Full name: NGUYỄN VĂN NHẬN"


def test_context_khoanh_hai_muc_va_neo_nguoi_nop():
    docs = [{"text": _BAN_KHAI_OCR}, {"text": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 034190000022\nHọ và tên / Full name: LÊ THỊ NỘP"}]
    own = asyncio.run(runner._context(docs, _NGUOI_NHAN))
    assert 'result="owner_match"' in own and "<cuu_chien_binh_ocr" in own and "<nguoi_nhan_tro_cap_ocr" in own
    recipient = own.split("<nguoi_nhan_tro_cap_ocr", 1)[1]
    assert "NGUYỄN VĂN NHẬN" in recipient and "Xác nhận của UBND" not in recipient
    other = asyncio.run(runner._context(docs, _NOP_THAY))
    assert 'result="co_giay_to"' in other and "LÊ THỊ NỘP" in other
    assert 'result="khong_giay_to"' in asyncio.run(runner._context(docs[:1], _NOP_THAY))
    theo_to_khai = asyncio.run(runner._context(docs, _THEO_TO_KHAI))
    assert 'result="owner_match"' in theo_to_khai and "cccd_nguoi_nop" not in theo_to_khai


# ---------------- Đính kèm: hai chế độ theo cài đặt "Tách giấy tờ" (gọi qua bộ điều phối) ----------------
_GOP_PAGES = [_BAN_KHAI_OCR, _TRICH_LUC_OCR, _GXN_OCR, _GXN_KY_OCR]


def _paged(pages):
    return "\n".join(f"───── Trang {p}/{len(pages)} ─────\n{t}" for p, t in enumerate(pages, start=1))


def _pdf(name, pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = base64.b64encode(doc.tobytes()).decode()
    doc.close()
    return FileItem(name=name, type="application/pdf", role="doc", dataUrl=f"data:application/pdf;base64,{data}")


def _image(name):
    return FileItem(name=name, type="image/png", role="doc", dataUrl="data:image/png;base64,AAAA")


def _plan(monkeypatch, options, files, texts, *, segments=None, types=None, split_fails=False):
    async def fake_ocr(items):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in items]

    async def fake_chat(messages, **_kwargs):
        if "docTypes" in messages[0]["content"]:  # prompt chế độ không tách
            return json.dumps({"documents": types or []})
        if split_fails:
            raise RuntimeError("LLM hết giờ")
        return json.dumps({"documents": segments or []})

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr)
    monkeypatch.setattr("app.services.llm.client.chat", fake_chat)
    out = asyncio.run(dieu_phoi.plan(files, options))
    AttachmentPlanResp.model_validate(out)
    return out


# Tệp 0 gộp Bản khai (tr.1) + Trích lục (tr.2) + Giấy xác nhận CCB (tr.3–4); tệp 1 ảnh CCCD.
_GOP_FILES = [_pdf("ho-so-gop.pdf", 4), _image("cccd.png")]
_GOP_TEXTS = {"ho-so-gop.pdf": _paged(_GOP_PAGES), "cccd.png": _CCCD_OCR}
_GOP_SEGMENTS = [
    {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "ban_khai_mau_01"},
    {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "trich_luc_khai_tu"},
    {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "xac_nhan_cuu_chien_binh"},
    # Trang 4 (trang ký của giấy xác nhận) LLM bỏ sót → nối tiếp giấy xác nhận (không có quốc hiệu).
    {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "cccd"},
]


def test_bat_tach_cat_dung_dong_khong_sot_trang(monkeypatch):
    out = _plan(monkeypatch, {"splitDocuments": True}, _GOP_FILES, _GOP_TEXTS, segments=_GOP_SEGMENTS)
    attachments = out["attachments"]
    gop = [(a["componentIndex"], a["detectedType"], a["sourceSegments"][0]["pageIndexes"], a["loaiBan"])
           for a in attachments if a["fileIndex"] == 0]
    assert gop == [(1, "ban_khai_mau_01", [0], "Bản chính"), (2, "trich_luc_khai_tu", [1], "Bản sao"),
                   (3, "xac_nhan_cuu_chien_binh", [2, 3], "Bản chính")]
    cccd = next(a for a in attachments if a["fileIndex"] == 1)
    assert cccd["componentIndex"] == 1 and not cccd.get("sourceSegments")
    assert all(a["target"] == "attp-row" and "untickRows" not in a for a in attachments)
    assert not any("Chưa có" in e for e in out["errors"])
    assert any("cccd.png" in e and "đính chung dòng 1" in e for e in out["errors"])


# Bộ hồ sơ gộp tải lên CÙNG ba tệp lẻ (đúng các trang đó) → tệp gộp không đính thêm.
_LE_FILES = [_pdf("ban-khai.pdf", 1), _pdf("trich-luc.pdf", 1), _pdf("xac-nhan.pdf", 2), _pdf("bo-ho-so.pdf", 4)]
_LE_TEXTS = {"ban-khai.pdf": _BAN_KHAI_OCR, "trich-luc.pdf": _TRICH_LUC_OCR,
             "xac-nhan.pdf": _paged([_GXN_OCR, _GXN_KY_OCR]), "bo-ho-so.pdf": _paged(_GOP_PAGES)}


def test_bat_tach_bo_tep_gop_trung_cac_tep_le(monkeypatch):
    segments = [
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "ban_khai_mau_01"},
        {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "trich_luc_khai_tu"},
        {"fileIndex": 2, "pageFrom": 1, "pageTo": 2, "type": "xac_nhan_cuu_chien_binh"},
        *[{"fileIndex": 3, "pageFrom": p, "pageTo": p, "type": t} for p, t in
          ((1, "ban_khai_mau_01"), (2, "trich_luc_khai_tu"), (3, "xac_nhan_cuu_chien_binh"))],
    ]
    out = _plan(monkeypatch, {"splitDocuments": True}, _LE_FILES, _LE_TEXTS, segments=segments)
    assert [(a["fileIndex"], a["componentIndex"]) for a in out["attachments"]] == [(0, 1), (1, 2), (2, 3)]
    assert not any(a.get("sourceSegments") for a in out["attachments"])
    assert any("bo-ho-so.pdf" in e and "trùng nội dung" in e for e in out["errors"])
    assert all(c.get("duplicateOf") for c in out["extracted"]["classified"] if c["fileIndex"] == 3)


@pytest.mark.parametrize("options", [{}, None, {"splitDocuments": False}])
def test_tat_tach_moi_tep_nguyen_mot_lan_bo_tep_trung(monkeypatch, options):
    types = [{"index": 0, "docTypes": ["ban_khai_mau_01"]}, {"index": 1, "docTypes": ["trich_luc_khai_tu"]},
             {"index": 2, "docTypes": ["xac_nhan_cuu_chien_binh"]},
             {"index": 3, "docTypes": ["ban_khai_mau_01", "trich_luc_khai_tu", "xac_nhan_cuu_chien_binh"]}]
    out = _plan(monkeypatch, options, _LE_FILES, _LE_TEXTS, types=types)
    attachments = out["attachments"]
    assert [(a["fileIndex"], a["componentIndex"], a["loaiBan"]) for a in attachments] == [
        (0, 1, "Bản chính"), (1, 2, "Bản sao"), (2, 3, "Bản chính")]
    assert not any(a.get("sourceSegments") for a in attachments)
    assert any("bo-ho-so.pdf" in e and "trùng nội dung" in e for e in out["errors"])
    assert not any("gộp nhiều giấy" in e for e in out["errors"])


def test_tat_tach_chi_co_tep_gop_thi_dinh_dong_1_va_canh_bao(monkeypatch):
    types = [{"index": 0, "docTypes": ["ban_khai_mau_01", "trich_luc_khai_tu", "xac_nhan_cuu_chien_binh"]},
             {"index": 1, "docTypes": ["cccd"]}]
    out = _plan(monkeypatch, {}, _GOP_FILES, _GOP_TEXTS, types=types)
    by_file = {a["fileIndex"]: a for a in out["attachments"]}
    assert by_file[0]["componentIndex"] == 1 and by_file[0]["documentName"] == "ho-so-gop"
    assert by_file[1]["componentIndex"] == 1
    assert any("ho-so-gop.pdf" in e and "gộp nhiều giấy" in e for e in out["errors"])
    assert not any("Chưa có" in e for e in out["errors"]), "giấy trong tệp gộp không báo thiếu"


def test_bat_tach_ma_chia_giay_loi_thi_dinh_nguyen_tep(monkeypatch):
    types = [{"index": 0, "docTypes": ["ban_khai_mau_01", "trich_luc_khai_tu", "xac_nhan_cuu_chien_binh"]},
             {"index": 1, "docTypes": ["cccd"]}]
    out = _plan(monkeypatch, {"splitDocuments": True}, _GOP_FILES, _GOP_TEXTS, types=types, split_fails=True)
    assert out["errors"][0].startswith("attachment_agent (tách)")
    assert sorted(a["fileIndex"] for a in out["attachments"]) == [0, 1]
    assert not any(a.get("sourceSegments") for a in out["attachments"])


def test_rule_type_khong_nham_trich_luc_nhac_trong_than_giay():
    assert tach._rule_type(_BAN_KHAI_OCR) == "ban_khai_mau_01"
    assert tach._rule_type(_GXN_OCR) == "xac_nhan_cuu_chien_binh"
    assert tach._rule_type(_TRICH_LUC_OCR) == "trich_luc_khai_tu"
    assert tach._rule_type(_CCCD_OCR) == "cccd"
    assert tach._normalize_type("Quyết định phục viên") == "xac_nhan_cuu_chien_binh"
    assert tach._normalize_type("Giấy chứng tử") == "trich_luc_khai_tu"


def test_tep_khac_nhau_khong_bi_coi_la_trung():
    pages = {0: {1: _BAN_KHAI_OCR}, 1: {1: _BAN_KHAI_OCR.replace("NGUYỄN VĂN NHẬN", "TRẦN THỊ KHÁC")
                                         .replace("034203000011", "001190000999").replace("MẪU", "KHÁC")}}
    assert tach.duplicate_files(pages) == {}
    assert tach.duplicate_files({0: {1: _BAN_KHAI_OCR}, 1: {1: _BAN_KHAI_OCR}}) == {1: [0]}


# ---------------- Trợ lý người dân ----------------
def test_tro_ly_chon_co_quan_cap_xa_va_tach_giay():
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(KEY)
    assert proc["supportsSplitDocuments"] is True and proc["keKhaiUrl"].endswith("f665291850ca")
    assert proc["maePortal"] is True and proc["maeAgencyLevel"] == "ward"
    assert "agencySoFirst" not in proc and "agencyProvinceOnly" not in proc and "provinceOnly" not in proc
    assert registry.get_attach_pipeline(KEY) is not None
