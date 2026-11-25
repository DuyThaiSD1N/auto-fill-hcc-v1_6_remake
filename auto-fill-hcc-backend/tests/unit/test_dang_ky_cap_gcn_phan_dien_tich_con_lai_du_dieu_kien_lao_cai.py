"""[Lào Cai - cổng iGate mới] 1.115692 đăng ký, cấp GCN phần diện tích còn lại nay đủ điều kiện (cấp xã) — nhận diện 2
cổng, mapper Form.io data[...] (form người nộp + Ghi chú, hai chế độ người nộp, Bộ A nộp thay qua người đại diện), đính
kèm bảng 5 dòng hai bộ (A dòng 1–3 / B dòng 4–5) có tách giấy.

Dữ liệu trong file đều là ví dụ bịa.
"""

import asyncio
import base64

import fitz
import pytest

from app.pipelines._shared import lao_cai_tach_giay_to
from app.pipelines.dang_ky_cap_gcn_phan_dien_tich_con_lai_du_dieu_kien_lao_cai.attach import planner as dispatcher
from app.pipelines.dang_ky_cap_gcn_phan_dien_tich_con_lai_du_dieu_kien_lao_cai.attach.dinh_kem_khong_tach import (
    planner,
)
from app.pipelines.dang_ky_cap_gcn_phan_dien_tich_con_lai_du_dieu_kien_lao_cai.attach.dinh_kem_tach import (
    planner as planner_tach,
)
from app.pipelines.dang_ky_cap_gcn_phan_dien_tich_con_lai_du_dieu_kien_lao_cai.process import mapper
from app.process.schemas import FileItem
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES
from app.services import ocr

_KEY = "dang-ky-cap-gcn-phan-dien-tich-con-lai-du-dieu-kien-lao-cai"
_CHU = "001200000777"
_DAI_DIEN = "001178000555"
_KHAC = "001190000888"
_NOI_DUNG = (
    "Đề nghị đăng ký, cấp Giấy chứng nhận đối với phần diện tích 90,0 m² (đất trồng cây lâu năm) còn lại của thửa\n"
    "đất số 41, tờ bản đồ số 9, địa chỉ: Tổ dân phố 3, phường Cam Đường, tỉnh Lào Cai. Thông tin Giấy chứng nhận đã\n"
    "cấp: số vào sổ CH 00001; số phát hành AA 000001. Có nhu cầu cấp mới Giấy chứng nhận."
)

# Bộ B: người sử dụng đất tự nộp.
_FACTS = [
    {"name": "DanhSachCccd", "value": [{
        "HoTen": "LÊ VĂN M", "SoDinhDanh": _CHU, "NgaySinh": "03/12/2000", "GioiTinh": "Nam",
        "NgayCap": "22/04/2021", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        # Thẻ in địa danh trước 01/7/2025.
        "NoiCuTru": {"tinh": "Thái Bình", "huyen": "Vũ Thư", "xa": "Minh Quang", "chiTietDuoiXa": "Thôn A"},
    }]},
    {"name": "NguoiTrongGiayTo", "value": [{"HoTen": "LÊ VĂN M", "SoDinhDanh": _CHU, "NgaySinh": "2000"}]},
    {"name": "ChuHoSo_HoTen", "value": "Lê Văn M"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_NgaySinh", "value": "2000"},
    {"name": "ChuHoSo_NgayCap", "value": "22/04/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Hưng Yên", "xa": "Vũ Thư", "chiTietDuoiXa": "Thôn A"}},
    {"name": "Don_DienThoai", "value": "0912 000 777"},
    {"name": "Don_Email", "value": "levanm@example.com"},
    {"name": "Don_NoiDungBienDong", "value": _NOI_DUNG},
    {"name": "Don_NguoiVietDon", "value": "Lê Văn M"},
]
# Bộ A: người đại diện theo ủy quyền viết đơn thay, kèm thẻ của người đại diện (in địa danh cũ).
_THE_DAI_DIEN = {
    "HoTen": "TRẦN VĂN K", "SoDinhDanh": _DAI_DIEN, "NgaySinh": "14/07/1978", "GioiTinh": "Nam",
    "NgayCap": "10/08/2021", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NoiCuTru": {"tinh": "Lào Cai", "huyen": "Thành phố Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ 3"},
}
_DAI_DIEN_FACTS = [
    {"name": "DaiDien_HoTen", "value": "Trần Văn K"},
    {"name": "DaiDien_SoDinhDanh", "value": _DAI_DIEN},
    {"name": "DaiDien_NgaySinh", "value": "14/07/1978"},
    {"name": "DaiDien_GioiTinh", "value": "Nam"},
    {"name": "DaiDien_NgayCap", "value": "10/08/2021"},
    {"name": "DaiDien_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "DaiDien_DiaChi", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "chiTietDuoiXa": "Tổ dân phố 3"}},
    {"name": "DaiDien_DienThoai", "value": "0912 555 000"},
    {"name": "DaiDien_Email", "value": "tranvank@example.com"},
]
_TO_KHAI = {"submitterMode": "owner_as_submitter"}


def _bo_a(**doi):
    facts = []
    for f in _FACTS:
        if f["name"] == "DanhSachCccd":
            f = {**f, "value": [*f["value"], dict(_THE_DAI_DIEN)]}
        elif f["name"] == "NguoiTrongGiayTo":
            f = {**f, "value": [*f["value"], {"HoTen": "TRẦN VĂN K", "SoDinhDanh": _DAI_DIEN, "NgaySinh": "14/07/1978"},
                                {"HoTen": "Trần Văn K", "SoDinhDanh": _DAI_DIEN}]}  # lời chứng ghi lại lần nữa
        elif f["name"] == "Don_NguoiVietDon":
            f = {**f, "value": "Trần Văn K"}
        facts.append(f)
    return [*facts, *_DAI_DIEN_FACTS]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _ctx(name, number, **extra):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}, **extra}


def _popup_match(url: str, body: str = "") -> str:
    """Giả lập popup.detectProcedureKeyFromSignals: bước 0 textPriority, bước 1 urlIncludes, bước 3 textIncludes."""
    from app.procedures.ke_khai_links import with_ke_khai_detect_urls
    from app.procedures.registry import public_list

    url, body = url.lower(), body.lower()
    rules = [p for p in with_ke_khai_detect_urls(public_list())
             if (p.get("detect") or {}) and not p.get("detectDisabled") and not p["detect"].get("detectDisabled")]

    def in_scope(detect):
        scope = detect.get("urlScope") or []
        return not scope or any(s.lower() in url for s in scope)

    def best_text(priority_only: bool) -> str:
        best, best_score = "", 0
        for p in rules:
            detect = p["detect"]
            phrases = [ph.lower() for ph in detect.get("textIncludes") or [] if ph]
            if priority_only and not detect.get("textPriority"):
                continue
            if body and in_scope(detect) and phrases and all(ph in body for ph in phrases):
                score = sum(len(ph) for ph in phrases)
                if score > best_score:
                    best, best_score = p["key"], score
        return best

    if found := best_text(True):
        return found
    for p in rules:
        if in_scope(p["detect"]) and any(u and u.lower() in url for u in p["detect"].get("urlIncludes") or []):
            return p["key"]
    return best_text(False)


# ---------------------------------------------------------------- registry / nhận diện

def test_registry_hai_cong_cung_pipeline_va_trung_key_ke_khai():
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert test["label"] == chinh["label"] + " - test"
    assert chinh["supportsSplitDocuments"] is True and test["supportsSplitDocuments"] is True
    assert chinh["collectFormContext"] is True and chinh["hasAttachmentStep"] is True
    assert test["detect"]["urlScope"] == ["dichvucongtest.laocai.gov.vn/vi/"]
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.115692"


def test_nhan_dien_trang_chon_truong_hop_va_trang_nop():
    chon = "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115692&MaDVC=1.115692.01"
    assert _popup_match(chon) == _KEY
    form = "https://dichvucong.laocai.gov.vn/vi/padsvc/apply-online/6aa4ffffbe4ea839f303eeee?agency=1&process=2"
    body = (
        "Lào Cai - Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đối với trường "
        "hợp hộ gia đình, cá nhân đã được cấp giấy chứng nhận đối với một phần diện tích của thửa đất, phần diện tích "
        "còn lại chưa đủ điều kiện cấp giấy chứng nhận theo quy định của pháp luật UBND Phường Cam Đường"
    )
    assert _popup_match(form, body) == _KEY
    assert _popup_match(form.replace("dichvucong.", "dichvucongtest."), body) == _KEY + "-test"


# ---------------------------------------------------------------- mapper: Bộ B, người sử dụng đất tự nộp

def test_tu_nop_dia_chi_theo_don_ghi_chu_nguyen_van():
    fields, warnings = mapper.enrich(_FACTS, _ctx("LÊ VĂN M", _CHU))
    values = _values(fields)
    assert not any(k in values for k in ("data[fullname]", "data[identityNumber]", "data[birthday]"))
    assert values["data[gender]"] == "Nam" and values["data[identityDate]"] == "22/04/2021"
    assert values["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Tỉnh/Phường-Xã theo mục 1 c) Đơn (thẻ in Thái Bình cũ) — cả hai khối.
    assert values["data[province]"] == values["data[ownerProvince]"] == "Tỉnh Hưng Yên"
    assert values["data[district]"].endswith("Vũ Thư") and values["data[ownerDistrict]"].endswith("Vũ Thư")
    assert values["data[address]"] == values["data[ownerAddress]"] == "Thôn A"
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0912000777"
    assert values["data[email]"] == values["data[ownerEmail]"] == "levanm@example.com"
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "LÊ VĂN M" and values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerBirthday]"] == "03/12/2000" and values["data[ownerGender]"] == "Nam"
    # Ghi chú = nguyên văn mục 2, chỉ gộp xuống dòng.
    assert values["data[tenHoSo]"] == " ".join(_NOI_DUNG.split())
    assert "data[isOwnerDossier]" not in values and "data[fax]" not in values
    assert not any("khác nơi thường trú" in w for w in warnings)
    assert all(f["name"].startswith("data[") for f in fields)


def test_theo_to_khai_khong_dai_dien_lay_nguoi_su_dung_dat_mo_khoa():
    fields, warnings = mapper.enrich(_FACTS, _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    assert [f["name"] for f in fields[:3]] == ["data[fullname]", "data[identityNumber]", "data[birthday]"]
    khoa = {f["name"]: f["value"] for f in fields if f.get("enableInput")}
    assert khoa == {"data[fullname]": "LÊ VĂN M", "data[identityNumber]": _CHU, "data[birthday]": "03/12/2000"}
    values = _values(fields)
    assert values["data[province]"] == "Tỉnh Hưng Yên" and values["data[phoneNumber]"] == "0912000777"
    assert any("mở khoá" in w for w in warnings)


def test_noi_cap_c06_thanh_bo_cong_an():
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"]
    facts = [{**f, "value": "Cục Cảnh sát đăng ký, quản lý cư trú và dữ liệu quốc gia về dân cư"}
             if f["name"] == "ChuHoSo_NoiCap" else f for f in facts]
    values = _values(mapper.enrich(facts, _ctx("LÊ VĂN M", _CHU))[0])
    assert values["data[ownerIdentityAgency22]"] == "Bộ Công An"


# ---------------------------------------------------------------- mapper: Bộ A, người đại diện nộp thay

def _khoi_dai_dien(values):
    assert values["data[gender]"] == "Nam" and values["data[identityDate]"] == "10/08/2021"
    # Giấy ủy quyền (địa danh mới "Tổ dân phố 3") thắng địa chỉ in trên thẻ ("Tổ 3", thành phố Lào Cai cũ).
    assert values["data[province]"] == "Tỉnh Lào Cai" and values["data[district]"].endswith("Cam Đường")
    assert values["data[address]"] == "Tổ dân phố 3"
    assert values["data[phoneNumber]"] == "0912555000" and values["data[email]"] == "tranvank@example.com"
    # Khối chủ hồ sơ vẫn là người sử dụng đất.
    assert values["data[ownerFullname]"] == "LÊ VĂN M" and values["data[ownerIdentityNumber]"] == _CHU
    assert values["data[ownerPhoneNumber]"] == "0912000777" and values["data[ownerProvince]"] == "Tỉnh Hưng Yên"


def test_bo_a_theo_to_khai_nguoi_nop_la_nguoi_dai_dien_mo_khoa():
    fields, warnings = mapper.enrich(_bo_a(), _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    assert [f["name"] for f in fields[:3]] == ["data[fullname]", "data[identityNumber]", "data[birthday]"]
    khoa = {f["name"]: f["value"] for f in fields if f.get("enableInput")}
    assert khoa == {"data[fullname]": "TRẦN VĂN K", "data[identityNumber]": _DAI_DIEN, "data[birthday]": "14/07/1978"}
    _khoi_dai_dien(_values(fields))
    assert any("mở khoá" in w and "Trần Văn K" in w for w in warnings)
    assert not any(f["comp"] == "dom-expect" and f["name"] == "data[phoneNumber]" for f in fields)


def test_bo_a_theo_to_khai_dai_dien_trung_tai_khoan_khong_mo_khoa():
    fields, warnings = mapper.enrich(_bo_a(), _ctx("TRẦN VĂN K", _DAI_DIEN, **_TO_KHAI))
    assert not any(f.get("enableInput") for f in fields)
    _khoi_dai_dien(_values(fields))
    assert not any("mở khoá" in w for w in warnings)


def test_bo_a_theo_tai_khoan_dai_dien_dang_nhap():
    fields, _ = mapper.enrich(_bo_a(), _ctx("TRẦN VĂN K", _DAI_DIEN))
    assert not any(f.get("enableInput") for f in fields)
    _khoi_dai_dien(_values(fields))


def test_bo_a_theo_tai_khoan_chu_dang_nhap_lay_so_tren_don():
    values = _values(mapper.enrich(_bo_a(), _ctx("LÊ VĂN M", _CHU))[0])
    assert values["data[phoneNumber]"] == "0912000777" and values["data[province]"] == "Tỉnh Hưng Yên"
    assert values["data[identityDate]"] == "22/04/2021"


def test_bo_a_chi_co_ten_nguoi_viet_don_van_lay_nguoi_dai_dien():
    facts = [f for f in _bo_a() if not f["name"].startswith("DaiDien_")]
    fields, _ = mapper.enrich(facts, {"formContext": {}, **_TO_KHAI})
    khoa = {f["name"]: f["value"] for f in fields if f.get("enableInput")}
    # Số CCCD / ngày sinh bù từ thẻ + Giấy ủy quyền của chính người viết đơn.
    assert khoa == {"data[fullname]": "TRẦN VĂN K", "data[identityNumber]": _DAI_DIEN, "data[birthday]": "14/07/1978"}
    values = _values(fields)
    assert values["data[identityDate]"] == "10/08/2021" and values["data[province]"] == "Tỉnh Lào Cai"


def test_khoi_dai_dien_trung_nguoi_su_dung_dat_bi_bo_qua():
    facts = [*_FACTS, {"name": "DaiDien_HoTen", "value": "Lê Văn M"}, {"name": "DaiDien_SoDinhDanh", "value": _CHU}]
    fields, _ = mapper.enrich(facts, _ctx("ĐỖ THỊ H", _KHAC, **_TO_KHAI))
    assert {f["name"]: f["value"] for f in fields if f.get("enableInput")}["data[fullname]"] == "LÊ VĂN M"


def test_don_thieu_nguoi_su_dung_dat_khong_lay_the_nguoi_dai_dien():
    facts = [f for f in _bo_a() if not f["name"].startswith("ChuHoSo_") or f["name"] == "ChuHoSo_DiaChiDon"]
    facts = [{**f, "value": [dict(_THE_DAI_DIEN)]} if f["name"] == "DanhSachCccd" else f for f in facts]
    fields, warnings = mapper.enrich(facts, _ctx("TRẦN VĂN K", _DAI_DIEN))
    values = _values(fields)
    assert "data[ownerFullname]" not in values
    assert not any("thẻ căn cước duy nhất" in w for w in warnings)
    assert any("Không xác định được chủ hồ sơ" in w for w in warnings)
    # Thẻ người đại diện vẫn dùng cho khối người nộp.
    assert values["data[identityDate]"] == "10/08/2021"


def test_don_thieu_nguoi_su_dung_dat_khong_dai_dien_lay_the_duy_nhat():
    facts = [f for f in _FACTS if not f["name"].startswith("ChuHoSo_") or f["name"] == "ChuHoSo_DiaChiDon"]
    facts = [f for f in facts if f["name"] != "Don_NguoiVietDon"]
    fields, warnings = mapper.enrich(facts, _ctx("ĐỖ THỊ H", _KHAC))
    assert _values(fields)["data[ownerFullname]"] == "LÊ VĂN M"
    assert any("Không đọc được người sử dụng đất ở mục 1 của Đơn" in w for w in warnings)


def test_khong_co_noi_dung_bien_dong_khong_ghi_chu():
    facts = [f for f in _FACTS if f["name"] != "Don_NoiDungBienDong"]
    assert "data[tenHoSo]" not in _values(mapper.enrich(facts, _ctx("LÊ VĂN M", _CHU))[0])


# ---------------------------------------------------------------- đính kèm

_ROWS = [
    {"index": 1, "componentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm "
                                  "theo Quyết định số 47/2026/QĐ-UBND"},
    {"index": 2, "componentName": "Giấy chứng nhận đã cấp"},
    {"index": 3, "componentName": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp "
                                  "thực hiện thủ tục đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện"},
    {"index": 4, "componentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo theo Mẫu số 24 ban hành "
                                  "kèm theo Quyết định số 47/2026/QĐ-UBND"},
    {"index": 5, "componentName": "Thông báo xác nhận kết quả đăng ký đất đai"},
]
_DON_A = (
    "BẢN MÔ PHỎNG\nMẫu số 24. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
    "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n1. Người sử dụng đất … Căn cước công dân số …\n"
    "2. Nội dung biến động: … Giấy chứng nhận … Chưa có Thông báo xác nhận kết quả đăng ký đất đai đối với phần diện "
    "tích còn lại.\n3. Giấy tờ nộp kèm: Giấy ủy quyền …"
)
_DON_A_2 = (
    "chính;\n(3) Không có giấy tờ khác nộp kèm theo.\nCam đoan nội dung kê khai trên đơn là đúng sự thật\nNgười viết "
    "đơn\nTrần Văn K\n(Người đại diện theo ủy quyền – Giấy ủy quyền ngày …)\nHướng dẫn kê khai đơn: …"
)
_DON_B = _DON_A.replace("Chưa có Thông báo xác nhận kết quả đăng ký đất đai đối với phần diện tích còn lại",
                        "Đã có Thông báo xác nhận kết quả đăng ký đất đai số 12/TB-KT ngày …")
_GCN = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY CHỨNG NHẬN\nQUYỀN SỬ DỤNG ĐẤT\nQUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN "
    "LIỀN VỚI ĐẤT\nI. Người sử dụng đất … Ông: LÊ VĂN M\nCCCD số: …"
)
_GCN_2 = "II. Thửa đất, nhà ở và tài sản khác gắn liền với đất\n1. Thửa đất: a) Thửa đất số: 41"
_GCN_3 = "III. Sơ đồ thửa đất, nhà ở và tài sản khác gắn liền với đất\nĐường nội bộ"
_GCN_4 = "IV. Những thay đổi sau khi cấp Giấy chứng nhận\nNội dung thay đổi và cơ sở pháp lý"
_UQ = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY ỦY QUYỀN\n(V/v thực hiện thủ tục đăng ký, cấp Giấy chứng nhận quyền sử "
    "dụng đất …)\nI. BÊN ỦY QUYỀN … Căn cước công dân số …"
)
_UQ_2 = "Bên A ủy quyền cho Bên B thay mặt … kê khai, ký Đơn đăng ký biến động đất đai (Mẫu số 24) …"
_UQ_3 = "LỜI CHỨNG CỦA NGƯỜI THỰC HIỆN CHỨNG THỰC\nChứng thực: Ông … Căn cước công dân số …"
_TB = (
    "ỦY BAN NHÂN DÂN PHƯỜNG CAM ĐƯỜNG\nPHÒNG KINH TẾ, HẠ TẦNG VÀ ĐÔ THỊ\nSố: 12/TB-KT\nTHÔNG BÁO\nXác nhận kết quả "
    "đăng ký đất đai\nKính gửi: Ông LÊ VĂN M … Căn cước công dân số … Giấy chứng nhận quyền sử dụng đất …"
)
_CCCD = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nCĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố / No.: …"


def test_phan_loai_theo_tieu_de_som_nhat():
    for text in (_DON_A, _DON_A_2, _DON_B):
        assert planner.phan_loai(text)[0] == "don_mau_24"
    for text in (_GCN, _GCN_2, _GCN_3, _GCN_4):
        assert planner.phan_loai(text)[0] == "gcn"
    for text in (_UQ, _UQ_2, _UQ_3):
        assert planner.phan_loai(text)[0] == "van_ban_dai_dien"
    assert planner.phan_loai(_TB)[0] == "thong_bao_xac_nhan"
    assert planner.phan_loai(_CCCD)[0] == "cccd"
    assert planner.phan_loai("QUYẾT ĐỊNH về việc …")[0] == "other"
    # OCR rỗng → tên tệp (Đơn xét trước: tên Đơn có chữ "ThongBao").
    assert planner.phan_loai("", "A1_Don_Mau24_ChuaCoThongBao.pdf") == ("don_mau_24", "filename")
    assert planner.phan_loai("", "A2_GCN_da_cap.pdf") == ("gcn", "filename")
    assert planner.phan_loai("", "A3_Giay_uy_quyen.pdf") == ("van_ban_dai_dien", "filename")
    assert planner.phan_loai("", "B2_Thong_bao_xac_nhan_KQ_dang_ky_dat_dai.pdf") == ("thong_bao_xac_nhan", "filename")
    assert planner.phan_loai("", "PL_CCCD_mo_phong.pdf") == ("cccd", "filename")
    assert planner.phan_loai("", "scan.pdf") == ("other", "default")


def test_bo_a_vao_dong_1_2_3():
    files = [{"name": "don.pdf"}, {"name": "gcn.pdf"}, {"name": "uq.pdf"}]
    for rows in (_ROWS, None):
        items, warnings, classified = planner.build_plan_items(files, {0: _DON_A, 1: _GCN, 2: _UQ}, rows)
        assert [(i["fileIndex"], i["componentIndex"]) for i in items] == [(0, 1), (1, 2), (2, 3)]
        assert [i["documentName"] for i in items] == [
            "Đơn đăng ký biến động đất đai Mẫu số 24", "Giấy chứng nhận đã cấp", "Văn bản về việc đại diện"]
        assert all(i["target"] == "attp-row" and i["untickUnplannedRows"] is True for i in items)
        assert {c["bo"] for c in classified} == {"A"}
        assert warnings == []


def test_bo_b_vao_dong_4_5():
    files = [{"name": "don.pdf"}, {"name": "tb.pdf"}]
    for rows in (_ROWS, None):
        items, warnings, _ = planner.build_plan_items(files, {0: _DON_B, 1: _TB}, rows)
        assert [(i["fileIndex"], i["componentIndex"]) for i in items] == [(0, 4), (1, 5)]
        assert items[0]["componentName"].startswith("Đơn đăng ký biến động") and "theo theo" in items[0]["componentName"]
        assert warnings == []


def test_bo_b_giay_cua_bo_a_vao_dong_don_canh_bao():
    files = [{"name": "don.pdf"}, {"name": "tb.pdf"}, {"name": "gcn.pdf"}, {"name": "cccd.jpg"}]
    items, warnings, _ = planner.build_plan_items(files, {0: _DON_B, 1: _TB, 2: _GCN, 3: _CCCD}, _ROWS)
    assert [i["componentIndex"] for i in items] == [4, 5, 4, 4]
    assert any("gcn.pdf" in w and "cccd.jpg" in w and "dòng Đơn" in w for w in warnings)


def test_chi_co_don_chon_bo_theo_chu_don_va_bao_thieu():
    items, warnings, _ = planner.build_plan_items([{"name": "don.pdf"}], {0: _DON_B}, _ROWS)
    assert [i["componentIndex"] for i in items] == [4]
    assert any("Thông báo xác nhận" in w and "chưa nhận ra" in w for w in warnings)
    items, warnings, _ = planner.build_plan_items([{"name": "don.pdf"}], {0: _DON_A}, _ROWS)
    assert [i["componentIndex"] for i in items] == [1]
    assert any("Giấy chứng nhận đã cấp" in w and "chưa nhận ra" in w for w in warnings)


def test_bo_a_cccd_vao_dong_don_khong_bo_tep():
    files = [{"name": "don.pdf"}, {"name": "gcn.pdf"}, {"name": "cccd.jpg"}]
    items, warnings, _ = planner.build_plan_items(files, {0: _DON_A, 1: _GCN, 2: _CCCD}, _ROWS)
    assert [i["componentIndex"] for i in items] == [1, 2, 1]
    assert items[2]["documentName"] == "Căn cước"
    assert any("cccd.jpg" in w and "CCCD không phải thành phần hồ sơ" in w for w in warnings)


def test_vuot_6mb_canh_bao_theo_dong():
    big = "data:application/pdf;base64," + "A" * (9 * 1024 * 1024)
    _, warnings, _ = planner.build_plan_items([{"name": "gcn.pdf", "dataUrl": big}], {0: _GCN}, _ROWS)
    assert any("dòng thứ 2" in w and "6 MB" in w for w in warnings)


# ---------------------------------------------------------------- tách giấy tờ

_PAGES = [_DON_A, _DON_A_2, _GCN, _GCN_2, _GCN_3, _GCN_4, _UQ, _UQ_2, _UQ_3]


def _pdf_data_url(pages: int) -> str:
    with fitz.open() as doc:
        for n in range(pages):
            doc.new_page().insert_text((72, 72), f"page {n + 1}")
        data = doc.tobytes()
    return "data:application/pdf;base64," + base64.b64encode(data).decode("ascii")


def _ocr_text(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {n + 1}/{len(pages)} ─────\n{text}" for n, text in enumerate(pages))


@pytest.fixture
def gia_lap(monkeypatch):
    """OCR giả: tệp gốc "Bộ A trọn bộ" ra chữ 9 trang; tệp con lấy chữ nạp sẵn (ocr.preset_texts)."""
    original = _pdf_data_url(len(_PAGES))

    async def fake_ocr(files):
        return [{"name": f.get("name"),
                 "text": ocr.preset_text(f.get("dataUrl")) or (_ocr_text(_PAGES) if f.get("dataUrl") == original else "")}
                for f in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    return [FileItem(name="BoA_TronBo.pdf", type="application/pdf", dataUrl=original, role="other")]


def test_bat_tach_bo_a_tron_bo_dung_dong_gop_lien_trang_khong_sot_trang(gia_lap, monkeypatch):
    async def fake_segment(pages_by_file):
        # LLM mở giấy mới ở trang 2 Đơn, các trang GCN, trang lời chứng.
        return {0: [(0, "Đơn"), (1, "Đơn tr2"), (2, "GCN"), (3, "GCN 2"), (4, "Sơ đồ"), (5, "Thay đổi"),
                    (6, "Giấy ủy quyền"), (8, "Lời chứng")]}

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", fake_segment)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True, "attachmentContext": {"components": _ROWS}}))
    items = result["attachments"]
    assert [(i["componentIndex"], i["documentName"], i["sourceSegments"]) for i in items] == [
        (1, "Đơn đăng ký biến động đất đai Mẫu số 24", [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
        (2, "Giấy chứng nhận đã cấp", [{"fileIndex": 0, "pageIndexes": [2, 3, 4, 5]}]),
        (3, "Văn bản về việc đại diện", [{"fileIndex": 0, "pageIndexes": [6, 7, 8]}]),
    ]
    assert all(i["fileIndex"] == 0 and i["target"] == "attp-row" for i in items)


def test_gop_doan_khong_gop_khac_loai_hoac_khong_lien_trang():
    def item(t, row, pages):
        return {"target": "attp-row", "detectedType": t, "componentIndex": row, "documentName": "x",
                "sourceSegments": [{"fileIndex": 0, "pageIndexes": pages}]}

    out = planner_tach.gop_doan_lien_trang([
        item("cccd", 1, [0]), item("cccd", 1, [1]),  # hai thẻ khác người → không gộp
        item("gcn", 2, [2]), item("gcn", 2, [4]),    # không liền trang → không gộp
    ])
    assert len(out) == 4


def test_tat_tach_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def must_not_split(pages_by_file):
        raise AssertionError("tắt tách thì không được chia trang")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", must_not_split)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}):
        items = asyncio.run(dispatcher.plan(gia_lap, options))["attachments"]
        assert len(items) == 1 and "sourceSegments" not in items[0]
        assert items[0]["componentIndex"] == 1
        assert items[0]["documentName"] == "Đơn đăng ký biến động đất đai Mẫu số 24"


def test_tach_loi_quay_ve_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def broken(pages_by_file):
        raise RuntimeError("LLM hỏng")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", broken)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))
    items = result["attachments"]
    assert len(items) == 1 and "sourceSegments" not in items[0] and items[0]["fileIndex"] == 0
    assert any("Tách giấy tờ" in e for e in result["errors"])
