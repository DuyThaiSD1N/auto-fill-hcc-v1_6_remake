"""Tests cho thủ tục "Đăng ký hành nghề" (mã 1.012275 — Sở Y tế).

Chủ hồ sơ (Phần II) là CƠ SỞ khám bệnh, chữa bệnh: tên + địa chỉ lấy từ Danh sách đăng ký hành nghề, nhân
thân lấy từ CCCD người đứng đầu cơ sở. Phần I (tài khoản VNeID): không ghi đè họ tên/CCCD/ngày sinh cổng đổ,
chỉ bù giới tính, ngày/nơi cấp, nơi thường trú từ CCCD khớp tài khoản.
"""

from app.pipelines.dang_ky_hanh_nghe import process as agent
from app.pipelines.dang_ky_hanh_nghe.attach import plan as attach_plan
from app.pipelines.dang_ky_hanh_nghe.attach.planner import build_plan_items
from app.pipelines.dang_ky_hanh_nghe.process import mapper
from app.pipelines.dang_ky_hanh_nghe.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_hanh_nghe.process.schema import FIELDS
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-hanh-nghe"


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped}


def _ho_so() -> list[dict]:
    return [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_DiaChi", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Xã Mường Than", "diaChi": "Bản Nà A"}),
        _field("CoSo_NguoiChiuTrachNhiem", "Trần Văn Bình"),
        _field("NguoiDaiDien_HoTen", "TRẦN VĂN BÌNH"),
        _field("NguoiDaiDien_NgaySinh", "3/12/1990"),
        _field("NguoiDaiDien_GioiTinh", "Nam"),
        _field("NguoiDaiDien_SoDinhDanh", "0120 9000 0111"),
        _field("NguoiDaiDien_NgayCapCCCD", "01/07/2022"),
        _field("NguoiDaiDien_NoiCapCCCD", "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"),
    ]


def test_dang_ky_hanh_nghe_registered_and_link_nop_tai_so():
    proc = get_procedure(KEY)
    assert proc and proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert proc.get("uploadHint")
    assert get_pipeline(KEY) is agent.run
    assert get_attach_pipeline(KEY) is attach_plan

    link = next(item for item in KE_KHAI_LINKS if item.get("key") == KEY)
    assert link["code"] == "1.012275"
    assert link["selectSo"] is True


def test_dang_ky_hanh_nghe_schema_khong_co_field_nguoi_hanh_nghe_ca_nhan():
    names = {f["name"] for f in FIELDS}
    assert {"CoSo_Ten", "CoSo_DiaChi", "NguoiDaiDien_SoDinhDanh"} <= names


def test_dang_ky_hanh_nghe_dien_co_so_vao_chu_ho_so_khong_dung_phan_i():
    out, warnings = mapper.enrich(_ho_so(), {})
    d = _values(out)

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"
    assert d["data[ownerBirthday]"] == "03/12/1990"
    assert d["data[ownerGender]"] == "Nam"
    assert d["data[ownerIdentityNumber]"] == "012090000111"
    assert d["data[ownerIdentityDate]"] == "01/07/2022"
    assert d["data[ownerIdIssuePlace]"]
    assert d["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert d["data[ownerDistrict]"]
    assert d["data[ownerNation]"] == "Việt Nam"
    # Phần I là tài khoản VNeID — không phát ô nào.
    assert not any(
        name in d
        for name in ("data[chonDoiTuong]", "data[fullname]", "data[identityNumber]", "data[birthday]", "data[phoneNumber]")
    )
    # SĐT không có trong giấy tờ → không bịa, chỉ nhắc nhập tay.
    assert "data[ownerPhoneNumber]" not in d
    assert any("điện thoại" in w for w in warnings)


def test_dang_ky_hanh_nghe_ten_co_so_bo_dau_cham_cuoi():
    """Mục 1 danh sách ghi 'Tên cơ sở khám bệnh, chữa bệnh: Trạm Y tế xã A.' — ô tên không mang dấu chấm."""
    out, _ = mapper.enrich([_field("CoSo_Ten", "Trạm Y tế xã Mường Than.")], {})
    assert _values(out)["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"


def test_dang_ky_hanh_nghe_thieu_cccd_va_nhieu_co_so_thi_canh_bao():
    fields = [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_CacCoSoKhac", "Trung tâm Y tế huyện B; Trạm Y tế xã C"),
    ]
    out, warnings = mapper.enrich(fields, {})
    d = _values(out)

    assert d["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"
    assert "data[ownerIdentityNumber]" not in d
    assert any("CCCD của người đại diện" in w for w in warnings)
    assert any("Trung tâm Y tế huyện B" in w for w in warnings)


def test_dang_ky_hanh_nghe_dia_chi_chi_toi_cap_xa():
    """Mẫu 01 của trạm y tế xã: địa chỉ chỉ tới cấp xã, người ký là Giám đốc trạm, không CCCD."""
    fields = [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_DiaChi", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Xã Mường Than", "diaChi": ""}),
        _field("CoSo_NguoiChiuTrachNhiem", "Lê Văn An"),
    ]
    out, warnings = mapper.enrich(fields, {})
    d = _values(out)

    assert d["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"
    assert d["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert d["data[ownerDistrict]"] == "Xã Mường Than"
    # Ô địa chỉ chi tiết bắt buộc → không để trống, nhưng nhắc bổ sung.
    assert d["data[ownerAddress]"] == "Xã Mường Than"
    assert any("Địa chỉ chi tiết" in w for w in warnings)
    assert any("CCCD của người đại diện" in w for w in warnings)


def test_dang_ky_hanh_nghe_khong_dung_cccd_nguoi_nop_cho_chu_ho_so():
    """Danh sách do Lê Văn An ký + CCCD của người nộp Phạm Thị Hoa: LLM vẫn đổ CCCD người nộp vào
    NguoiDaiDien_* → mapper phải bỏ, không để ngày sinh/số CCCD người khác lên Phần II."""
    fields = [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_DiaChi", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Mường Than", "diaChi": "", "huyen": ""}),
        _field("CoSo_NguoiChiuTrachNhiem", "Lê Văn An"),
        _field("NguoiDaiDien_HoTen", "PHẠM THỊ HOA"),
        _field("NguoiDaiDien_NgaySinh", "11/08/1995"),
        _field("NguoiDaiDien_GioiTinh", "Nữ"),
        _field("NguoiDaiDien_SoDinhDanh", "001195000222"),
    ]
    out, warnings = mapper.enrich(fields, {"formContext": {"applicantFullname": "PHẠM THỊ HOA"}})
    d = _values(out)

    assert d["data[ownerFullname]"] == "Trạm Y tế xã Mường Than"
    for name in ("data[ownerBirthday]", "data[ownerGender]", "data[ownerIdentityNumber]",
                 "data[ownerIdentityDate]", "data[ownerIdIssuePlace]"):
        assert name not in d, name
    assert any("PHẠM THỊ HOA" in w and "Lê Văn An" in w for w in warnings)


def test_dang_ky_hanh_nghe_cccd_dung_nguoi_chiu_trach_nhiem_thi_van_dien():
    fields = [
        _field("CoSo_Ten", "Trạm Y tế xã Mường Than"),
        _field("CoSo_NguoiChiuTrachNhiem", "Lê Văn An"),
        _field("NguoiDaiDien_HoTen", "LÊ VĂN AN"),
        _field("NguoiDaiDien_NgaySinh", "02/03/1980"),
        _field("NguoiDaiDien_SoDinhDanh", "012080000123"),
    ]
    out, _ = mapper.enrich(fields, {"formContext": {"applicantFullname": "PHẠM THỊ HOA"}})
    d = _values(out)

    assert d["data[ownerIdentityNumber]"] == "012080000123"
    assert d["data[ownerBirthday]"] == "02/03/1980"


_TAI_KHOAN = {"formContext": {"applicantFullname": "Phạm Văn Long", "applicantIdentityNumber": "001204000777"}}


def _cccd_nguoi_nop() -> list[dict]:
    return [
        _field("NguoiNop_HoTen", "PHẠM VĂN LONG"),
        _field("NguoiNop_SoDinhDanh", "001204000777"),
        _field("NguoiNop_NgaySinh", "05/06/2004"),
        _field("NguoiNop_GioiTinh", "Nam"),
        _field("NguoiNop_NgayCapCCCD", "20/04/2021"),
        _field("NguoiNop_NoiCapCCCD", "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"),
        _field("NguoiNop_ThuongTru", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Xã Mường Than",
                                      "diaChi": "Bản Nà B"}),
    ]


def test_dang_ky_hanh_nghe_bu_phan_i_tu_cccd_nguoi_nop_khop_tai_khoan():
    """Cổng chỉ đổ họ tên/CCCD/ngày sinh theo VNeID; hồ sơ có CCCD riêng của người nộp (khác người đại diện)
    → bù giới tính, ngày/nơi cấp, nơi thường trú vào Phần I, không ghi đè ô cổng đã đổ, Phần II vẫn là cơ sở."""
    out, warnings = mapper.enrich(_ho_so() + _cccd_nguoi_nop(), _TAI_KHOAN)
    d = _values(out)

    assert d["data[gender]"] == "Nam"
    assert d["data[identityDate]"] == "20/04/2021"
    assert d["data[idIssuePlace]"]
    assert d["data[province]"] == "Tỉnh Lai Châu"
    assert d["data[district]"]
    assert d["data[address]"] == "Bản Nà B"
    for name in ("data[fullname]", "data[identityNumber]", "data[birthday]"):
        assert name not in d, name
    assert d["data[ownerIdentityNumber]"] == "012090000111"
    assert d["data[ownerGender]"] == "Nam"
    assert not any("CCCD của người nộp" in w for w in warnings)


def test_dang_ky_hanh_nghe_khong_bu_phan_i_khi_cccd_khac_tai_khoan():
    other = [f if f["name"] != "NguoiNop_SoDinhDanh" else _field("NguoiNop_SoDinhDanh", "001204000999")
             for f in _cccd_nguoi_nop()]
    out, warnings = mapper.enrich(_ho_so() + other, _TAI_KHOAN)
    d = _values(out)

    assert not any(name in d for name in ("data[gender]", "data[identityDate]", "data[province]", "data[address]"))
    assert any("CCCD của người nộp (Phạm Văn Long)" in w for w in warnings)


def test_dang_ky_hanh_nghe_giam_doc_tu_nop_bu_phan_i_tu_cccd_dai_dien():
    out, _ = mapper.enrich(
        _ho_so(), {"formContext": {"applicantFullname": "Trần Văn Bình", "applicantIdentityNumber": "012090000111"}}
    )
    d = _values(out)
    assert d["data[gender]"] == "Nam"
    assert d["data[identityDate]"] == "01/07/2022"
    assert d["data[ownerIdentityNumber]"] == "012090000111"


def test_dang_ky_hanh_nghe_context_luon_trich_nguoi_nop():
    from app.pipelines.dang_ky_hanh_nghe.process.runner import _submitter_context

    docs = [{"text": "CĂN CƯỚC CÔNG DÂN Số 001204000777 Họ và tên PHẠM VĂN LONG"}]
    # Coroutine không await gì → chạy thẳng, khỏi tạo event loop (Windows tạo loop cần socketpair).
    try:
        _submitter_context(docs, _TAI_KHOAN).send(None)
    except StopIteration as done:
        ctx = done.value
    assert 'result="co_giay_to"' in ctx
    assert "LUÔN trích NguoiNop_*" in ctx


def test_dang_ky_hanh_nghe_dien_sdt_co_so_khi_giay_to_co():
    fields = [_field("CoSo_Ten", "Công ty TNHH Nha khoa A"), _field("CoSo_DienThoai", "0912 345 678")]
    out, warnings = mapper.enrich(fields, {})
    assert _values(out)["data[ownerPhoneNumber]"] == "0912345678"
    assert not any("điện thoại" in w for w in warnings)


_OCR_HOP_DONG = (
    "===== ho-so.pdf (tiengnoi) =====\n"
    "───── Trang 1/2 ─────\nDANH SÁCH ĐĂNG KÝ HÀNH NGHỀ\n1. Tên cơ sở khám bệnh, chữa bệnh: Công ty TNHH Nha khoa A\n"
    "ĐẠI DIỆN CƠ SỞ\nTrần Văn Bình\n"
    "───── Trang 2/2 ─────\nHỢP ĐỒNG LAO ĐỘNG\nChúng tôi, một bên là ông: Trần Văn Bình\nChức vụ: Giám đốc\n"
    "Điện thoại: 0912345678\nVà một bên là bà: Phạm Thị Hoa\nSố CCCD/CMT: 001195000222\nCấp ngày: 28/06/2021\n"
)


def test_dang_ky_hanh_nghe_bo_cccd_lay_tu_hop_dong_lao_dong():
    """Hồ sơ không có thẻ CCCD của giám đốc; LLM gán số CCCD của NGƯỜI LAO ĐỘNG trong hợp đồng (giám đốc ký
    cùng trang) cho giám đốc → tên khớp người ký nhưng số không nằm trên thẻ CCCD nào → bỏ."""
    fields = [
        _field("CoSo_Ten", "Công ty TNHH Nha khoa A"),
        _field("CoSo_NguoiChiuTrachNhiem", "Trần Văn Bình"),
        _field("NguoiDaiDien_HoTen", "TRẦN VĂN BÌNH"),
        _field("NguoiDaiDien_SoDinhDanh", "001195000222"),
        _field("NguoiDaiDien_NgayCapCCCD", "28/06/2021"),
    ]
    out, warnings = mapper.enrich(fields, {}, ocr_text=_OCR_HOP_DONG)
    d = _values(out)
    assert "data[ownerIdentityNumber]" not in d
    assert "data[ownerIdentityDate]" not in d
    assert any("001195000222" in w and "thẻ CCCD" in w for w in warnings)


def test_dang_ky_hanh_nghe_giu_cccd_nam_tren_the():
    ocr = _OCR_HOP_DONG + (
        "===== cccd.jpg (tiengnoi) =====\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nCĂN CƯỚC CÔNG DÂN\n"
        "Số: 012 090 000 111\nHọ và tên: TRẦN VĂN BÌNH\n"
    )
    fields = [
        _field("CoSo_Ten", "Công ty TNHH Nha khoa A"),
        _field("CoSo_NguoiChiuTrachNhiem", "Trần Văn Bình"),
        _field("NguoiDaiDien_HoTen", "TRẦN VĂN BÌNH"),
        _field("NguoiDaiDien_SoDinhDanh", "012090000111"),
    ]
    out, _ = mapper.enrich(fields, {}, ocr_text=ocr)
    assert _values(out)["data[ownerIdentityNumber]"] == "012090000111"


def test_dang_ky_hanh_nghe_prompt_lay_nguoi_ky_khong_lay_dong_bang():
    """Cột 'Vị trí chuyên môn' ghi 'chịu trách nhiệm chuyên môn kỹ thuật' cho nhiều người hành nghề; người
    đứng đầu là người KÝ cuối danh sách. Dòng 'ĐIỂM TRẠM Y TẾ SỐ 1' giữa bảng không phải cơ sở khác."""
    desc = {f["name"]: f["desc"] for f in FIELDS}
    assert "KÝ cuối" in desc["CoSo_NguoiChiuTrachNhiem"]
    assert "chịu trách nhiệm chuyên môn kỹ thuật" in desc["CoSo_NguoiChiuTrachNhiem"]
    assert "ĐIỂM TRẠM Y TẾ SỐ 1" in desc["CoSo_CacCoSoKhac"]
    assert "ĐIỂM TRẠM Y TẾ SỐ 1" in EXTRA_RULES


DS_TEXT = (
    "DANH SÁCH ĐĂNG KÝ NGƯỜI HÀNH NGHỀ 1. Tên cơ sở khám bệnh, chữa bệnh: Trạm Y tế xã Mường Than. 2. Địa "
    "chỉ: xã Mường Than, tỉnh Lai Châu. STT Họ và tên Số giấy phép hành nghề/Số chứng chỉ hành nghề Phạm vi "
    "hành nghề"
)
BAO_CAO_TEXT = "SỞ Y TẾ LAI CHÂU TRẠM Y TẾ XÃ MƯỜNG THAN BÁO CÁO Về tình hình hoạt động khám bệnh, chữa bệnh"
CCCD_TEXT = "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM CĂN CƯỚC CÔNG DÂN Số 012090000111 Họ và tên TRẦN VĂN BÌNH"


def _files(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def test_dang_ky_hanh_nghe_attach_rule_xep_dung_dong_khi_llm_loi():
    files = _files("ds1.pdf", "ds2.pdf", "ds3.pdf", "baocao.pdf", "cccd.pdf")
    ocr = [
        {"name": "ds1.pdf", "text": DS_TEXT},
        {"name": "ds2.pdf", "text": DS_TEXT.replace("Mường Than", "C")},
        {"name": "ds3.pdf", "text": DS_TEXT.replace("Trạm Y tế xã Mường Than", "Trung tâm Y tế huyện B")},
        {"name": "baocao.pdf", "text": BAO_CAO_TEXT},
        {"name": "cccd.pdf", "text": CCCD_TEXT},
    ]
    items, warnings, classified = build_plan_items(files, ocr, {})

    by_file = {item["fileName"]: item for item in items}
    assert set(by_file) == {"ds1.pdf", "ds2.pdf", "ds3.pdf", "baocao.pdf"}
    for name in ("ds1.pdf", "ds2.pdf", "ds3.pdf"):
        assert by_file[name]["componentIndex"] == 1
        assert by_file[name]["target"] == "attp-row"
        assert by_file[name]["loaiBan"] == "Bản chính"
        # 3 file cùng dòng → giữ tên gốc để FE không coi là file trùng.
        assert by_file[name]["documentName"] == name
    assert by_file["baocao.pdf"]["componentIndex"] == 3
    assert by_file["baocao.pdf"]["documentName"] == "Báo cáo"
    assert any(c["fileName"] == "cccd.pdf" and c.get("skipped") for c in classified)
    assert not any("Danh sách đăng ký hành nghề" in w and "bắt buộc" in w for w in warnings)


def test_dang_ky_hanh_nghe_attach_llm_thay_doi_bo_sung_khong_lan_sang_dong_1():
    files = _files("ds.pdf", "thaydoi.pdf", "bosung.pdf", "la.pdf")
    ocr = [
        {"name": "ds.pdf", "text": DS_TEXT},
        {"name": "thaydoi.pdf", "text": DS_TEXT},
        {"name": "bosung.pdf", "text": DS_TEXT},
        {"name": "la.pdf", "text": "Hoá đơn bán hàng"},
    ]
    items, warnings, _ = build_plan_items(files, ocr, {0: "ds_lan_dau", 1: "ds_thay_doi", 2: "ds_bo_sung"})

    by_file = {item["fileName"]: item for item in items}
    assert by_file["ds.pdf"]["componentIndex"] == 1
    assert by_file["ds.pdf"]["documentName"].startswith("Danh sách đăng ký hành nghề (Mẫu 01")
    assert by_file["thaydoi.pdf"]["componentIndex"] == 2
    assert by_file["bosung.pdf"]["componentIndex"] == 4
    # componentName dòng 2/4 KHÔNG được chứa tên dòng 1, nếu không FE khớp "chứa nhau" sẽ rơi vào dòng 1.
    for name in ("thaydoi.pdf", "bosung.pdf"):
        assert "danh sách đăng ký hành nghề" not in by_file[name]["componentName"].lower()
    # File không xác định không bị đính bừa.
    assert "la.pdf" not in by_file
    assert any("la.pdf" in w for w in warnings)
    assert any("Báo cáo" in w for w in warnings)
