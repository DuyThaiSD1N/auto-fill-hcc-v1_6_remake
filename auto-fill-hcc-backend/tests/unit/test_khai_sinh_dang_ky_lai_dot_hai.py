"""Thanh tra + điền đợt 2 của đăng ký lại khai sinh (tên, số giả)."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Result
from app.pipelines.khai_sinh_dang_ky_lai import thanh_tra
from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra import chu_the, dia_chi, dinh_danh, dot_hai
from app.procedures.registry import PROCEDURES

_DECLARATION = """TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
Họ, chữ đệm, tên người mẹ: TRẦN THỊ THIEM
Dân tộc: Sáu chín
Họ, chữ đệm, tên người cha: LÊ VĂN SOAN
Người yêu cầu
(Ký, ghi rõ họ, chữ đệm, tên)"""
_DEATH_CERT = """TRÍCH LỤC KHAI TỬ
Họ, chữ đệm, tên: TRẦN THỊ THIỀM
Dân tộc: Kinh"""


def _record(name, *, role="", handwritten=False, text="", number="", ethnic="", birth_text=""):
    return {"name": name, "number": number, "birth": None, "birth_text": birth_text, "ethnic": ethnic, "role": role,
            "doc": 1, "text": text or name, "handwritten": handwritten}


def _links(role_key, values, records):
    role = chu_the.ROLE_BY_KEY[role_key]
    person = chu_the.identity(values, role)
    return role, person, [link for record in records if (link := dinh_danh._belongs(record, role, person, []))]


def test_registry_bat_dot_hai_form_cu():
    entry = next(p for p in PROCEDURES if p["key"] == "khai-sinh-dang-ky-lai")
    assert entry["secondPass"] == "legacy"


def test_vai_tren_trang_so_theo_tu():
    me = chu_the.ROLE_BY_KEY["me"]
    assert chu_the.plays("Mẹ", me)
    assert chu_the.plays("mẹ của người được khai sinh", me)
    assert not chu_the.plays("mẹ nuôi", me)
    assert not chu_the.plays("người được khai sinh", me)


def test_ho_ten_gan_trung():
    assert dinh_danh.close_name("TRẦN THỊ THIEM", "Trần Thị Thiềm")
    assert dinh_danh.close_name("LÊ VĂN SOAN", "LÊ VĂN SOẠN")
    assert not dinh_danh.close_name("LÊ VĂN AN", "LÊ VĂN AN BÌNH")
    assert not dinh_danh.close_name("LÊ VĂN AN", "PHẠM THỊ HOA")


_DECLARATION_HEAD = "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH"


def _docs(*texts):
    return [{"name": f"{i}.pdf", "text": text} for i, text in enumerate(texts)]


def test_ten_tren_giay_in_thang_to_khai_viet_tay():
    values = {"Mother_FullName": "TRẦN THỊ THIEM"}
    birth = "GIẤY KHAI SINH\nHọ, chữ đệm, tên người mẹ: TRẦN THỊ THIỀM"
    records = [_record("TRẦN THỊ THIEM", role="mẹ", handwritten=True, text=_DECLARATION),
               _record("TRẦN THỊ THIỀM", role="người chết", text=_DEATH_CERT),
               _record("TRẦN THỊ THIỀM", role="mẹ", text=birth)]
    role, person, links = _links("me", values, records)
    finding = dinh_danh.name_finding(role, person, links, _docs(_DECLARATION, _DEATH_CERT, birth))
    assert finding and finding.values == {"Mother_FullName": "TRẦN THỊ THIỀM"} and finding.backed


def test_khong_doi_khi_ban_de_xuat_chi_la_ban_roi_dau():
    values = {"Mother_FullName": "TRẦN THỊ THIỀM"}
    text = "BẢN SAO\nHọ tên mẹ: TRẦN THỊ THIÊM"
    records = [_record("TRẦN THỊ THIỀM", role="mẹ", handwritten=True),
               _record("TRẦN THỊ THIÊM", role="mẹ", text=text)]
    role, person, links = _links("me", values, records)
    assert dinh_danh.name_finding(role, person, links, _docs(text, text)) is None


def test_trich_luc_thang_ban_cam_doan():
    values = {"Father_FullName": "LÊ VĂN SOAN"}
    ours, theirs = "BẢN CAM ĐOAN\nCha tôi: LÊ VĂN SOAN", "TRÍCH LỤC\nHọ tên cha: LÊ VĂN SOẠN"
    records = [_record("LÊ VĂN SOẠN", role="cha", text=theirs)]
    role, person, links = _links("cha", values, records)
    finding = dinh_danh.name_finding(role, person, links, _docs(ours, theirs))
    assert finding.values == {"Father_FullName": "LÊ VĂN SOẠN"}


def test_ban_cam_doan_thang_to_khai():
    values = {"Mother_FullName": "TRẦN THỊ HÙN"}
    declaration = f"{_DECLARATION_HEAD}\nHọ, chữ đệm, tên người mẹ: Trần Thị Hùn\n(Ký, ghi rõ họ, chữ đệm, tên)"
    pledge = "BẢN CAM ĐOAN\nTôi có mẹ đẻ là Trần Thị Hùy"
    records = [_record("Trần Thị Hùy", role="mẹ", text=pledge)]
    role, person, links = _links("me", values, records)
    finding = dinh_danh.name_finding(role, person, links, _docs(declaration, pledge))
    assert finding.values == {"Mother_FullName": "Trần Thị Hùy"}


def test_cung_hang_nhieu_giay_hon_thang():
    # Ba cách viết chỉ khác dấu: thẻ đọc rơi dấu, ô bảng giấy khai sinh đọc một kiểu, dòng người đi khai sinh của giấy
    # khai sinh + tờ khai cùng ghi kiểu thứ ba (lượt đọc trang không nêu) → kiểu thứ ba nhiều giấy hơn.
    values = {"Mother_FullName": "TRẦN THỊ THÂN"}
    card = "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name: TRẦN THỊ THÂN"
    birth = "GIẤY KHAI SINH\n| Họ và tên | TRẦN THỊ THẨN |\nNgười đi khai sinh: Trần Thị Thản"
    declaration = f"{_DECLARATION_HEAD}\nHọ, chữ đệm, tên mẹ: Trần Thị Thản\n(Ký, ghi rõ họ, chữ đệm, tên)"
    records = [_record("TRẦN THỊ THẨN", role="mẹ", text=birth)]
    role, person, links = _links("me", values, records)
    finding = dinh_danh.name_finding(role, person, links, _docs(card, birth, declaration))
    assert dinh_danh.base._name_key(finding.values["Mother_FullName"]) == dinh_danh.base._name_key("TRẦN THỊ THẢN")


def test_ten_ngan_lech_hai_chu_la_nguoi_khac():
    assert not dinh_danh.close_name("NGUYỄN THỊ NAM", "NGUYỄN THỊ NỤ")
    assert dinh_danh.close_name("NGUYỄN THỊ MÁT", "NGUYỄN THỊ MÍT")


def test_doi_chu_cai_khi_chu_luot_trich_co_tren_giay_khac_thi_khong_doi():
    # Chữ cái của lượt trích đã có trên giấy khai sinh → cách viết khác chữ (dù nhiều giấy hơn) là tên người khác.
    values = {"Father_FullName": "LÊ VĂN SOAN"}
    ours, theirs = "GIẤY KHAI SINH\nHọ tên cha: LÊ VĂN SOAN", "TRÍCH LỤC\nHọ tên cha: LÊ VĂN TOAN"
    records = [_record("LÊ VĂN SOAN", role="cha", text=ours), _record("LÊ VĂN TOAN", role="cha", text=theirs)]
    role, person, links = _links("cha", values, records)
    assert dinh_danh.name_finding(role, person, links, _docs(ours, theirs, theirs)) is None


def test_dem_theo_trang_trong_mot_tep():
    one_file = ("CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name: MẠC VĂN THƯỜNG\n─── Trang 2/3 ───\nBẢN CAM ĐOAN\nTôi là Mạc Văn"
                " Thưởng\n─── Trang 3/3 ───\nGIẤY XÁC NHẬN\nÔng Mạc Văn Thưởng")
    assert dinh_danh.spelling_support("MẠC VĂN THƯỞNG", _docs(one_file))["giay"] == 2


def test_dem_trang_tach_dau_thanh():
    documents = _docs(_DECLARATION, _DEATH_CERT)
    assert dinh_danh.spelling_support("TRẦN THỊ THIỀM", documents) == {"giay": 1, "ban_in": 1, "card": 0, "cam_doan": 0, "to_khai": 0}
    assert dinh_danh.spelling_support("Trần Thị Thiem", documents) == {"giay": 1, "ban_in": 0, "card": 0, "cam_doan": 0, "to_khai": 1}


def test_so_dinh_danh_khac_han_la_nguoi_khac():
    values = {"Subject_FullName": "NGUYỄN VĂN AN", "Subject_IdNumber": "001090000001"}
    records = [_record("NGUYỄN VĂN ẤN", number="001090999999", text="CĂN CƯỚC\nNGUYỄN VĂN ẤN")]
    _, _, links = _links("con", values, records)
    assert links == []


def test_dan_toc_ngoai_danh_muc_lay_theo_giay_khac():
    values = {"Mother_FullName": "TRẦN THỊ THIỀM", "Mother_Ethnicity": "Sáu chín"}
    records = [_record("TRẦN THỊ THIỀM", role="mẹ", handwritten=True, ethnic="Sáu chín", text=_DECLARATION),
               _record("TRẦN THỊ THIỀM", role="người chết", ethnic="Kinh", text=_DEATH_CERT,
                       birth_text="")]
    role = chu_the.ROLE_BY_KEY["me"]
    person = chu_the.identity(values, role)
    links = [dinh_danh._Link(records[0], "đứng ở dòng mẹ trên giấy", False),
             dinh_danh._Link(records[1], "trùng họ tên", False)]
    finding = dinh_danh.ethnic_finding(role, person, links, [])
    assert finding and finding.values == {"Mother_Ethnicity": "Kinh"}
    assert "Dân tộc: Kinh" in finding.quote


def test_dan_toc_hop_le_khong_doi_theo_to_khai_viet_tay():
    values = {"Mother_FullName": "TRẦN THỊ THIỀM", "Mother_Ethnicity": "Kinh"}
    records = [_record("TRẦN THỊ THIỀM", role="mẹ", handwritten=True, ethnic="Tày", text="Dân tộc: Tày")]
    role = chu_the.ROLE_BY_KEY["me"]
    links = [dinh_danh._Link(records[0], "đứng ở dòng mẹ trên giấy", False)]
    assert dinh_danh.ethnic_finding(role, chu_the.identity(values, role), links, []) is None


def test_ten_thon_tren_giay_in_thang_to_khai():
    documents = [
        {"name": "to_khai.pdf", "text": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH\nNơi cư trú: Thôn Tân Tiến, xã Hoà Bình\n"
                                        "(Ký, ghi rõ họ, chữ đệm, tên)"},
        {"name": "trich_luc.pdf", "text": "TRÍCH LỤC KHAI TỬ\nNơi cư trú: Thôn Tân Hiền, xã Hoà Bình, tỉnh Bắc Ninh"},
    ]
    value = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Hòa Bình", "diaChi": "Thôn Tân Tiến"}
    finding = dia_chi.address_finding("Mother_ResidenceDomestic", value, documents, dia_chi.printed_lines(documents))
    assert finding and finding.values["Mother_ResidenceDomestic"]["diaChi"] == "Thôn Tân Hiền"
    assert finding.doc == 2


def test_ten_thon_da_co_tren_giay_in_hoac_khac_xa_thi_khong_de_xuat():
    documents = [{"name": "a.pdf", "text": "TRÍCH LỤC KHAI SINH\nNơi cư trú: Thôn Tân Tiến, xã Hoà Bình\nThôn Tân Hiền, xã Yên Lạc"}]
    value = {"tinh": "Bắc Ninh", "xa": "Hòa Bình", "diaChi": "Thôn Tân Tiến"}
    assert dia_chi.address_finding("Father_ResidenceDomestic", value, documents,
                                   dia_chi.printed_lines(documents)) is None
    other = {"tinh": "Bắc Ninh", "xa": "Hòa Bình", "diaChi": "Thôn Tân Hiến"}
    assert dia_chi.address_finding("Father_ResidenceDomestic", other, documents,
                                   dia_chi.printed_lines(documents)) is not None
    far = [{"name": "b.pdf", "text": "TRÍCH LỤC KHAI SINH\nThôn Tân Hiền, xã Yên Lạc"}]
    self_made = [{"name": "c.pdf", "text": "BẢN CAM ĐOAN\nThôn Tân Hiền, xã Hoà Bình"}]
    assert dia_chi.address_finding("Father_ResidenceDomestic", other, self_made,
                                   dia_chi.printed_lines(self_made)) is None
    assert dia_chi.address_finding("Father_ResidenceDomestic", other, far, dia_chi.printed_lines(far)) is None


def test_noi_sinh_lay_thon_tren_dong_ghi_dung_xa_hien_tai():
    documents = [{"name": "a.pdf", "text": "Nơi sinh: Thôn Cũ Một, xã Đông Lỗ, huyện Hiệp Hòa, tỉnh Bắc Giang\n"
                                           "Nơi sinh: TDP Mới Hai, phường Hòa Bình, thành phố Bắc Ninh"}]
    old = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Phường Hòa Bình", "diaChi": "Thôn Cũ Một"}
    finding = dia_chi.declared_detail_finding("Subject_BirthPlaceDomestic", old, documents)
    assert finding and finding.values["Subject_BirthPlaceDomestic"]["diaChi"] == "TDP Mới Hai"
    blank = {**old, "diaChi": ""}
    assert dia_chi.declared_detail_finding("Subject_BirthPlaceDomestic", blank, documents).values[
        "Subject_BirthPlaceDomestic"]["diaChi"] == "TDP Mới Hai"


def test_noi_sinh_giu_chi_tiet_da_co_tren_dong_dung_xa():
    documents = [{"name": "a.pdf", "text": "Quê quán: Tổ dân phố Mới Hai, phường Hòa Bình\n"
                                           "Quê quán: TDP Khác Ba, phường Yên Lạc"}]
    same = {"tinh": "Bắc Ninh", "xa": "Hòa Bình", "diaChi": "TDP Mới Hai"}
    assert dia_chi.declared_detail_finding("Subject_HometownDomestic", same, documents) is None
    # Dòng chỉ ghi xã khác (nơi khác) không phải căn cứ; chi tiết không phải tên đơn vị thì không đụng.
    other = [{"name": "a.pdf", "text": "Quê quán: TDP Khác Ba, phường Yên Lạc"}]
    assert dia_chi.declared_detail_finding("Subject_HometownDomestic", {**same, "diaChi": ""}, other) is None
    house = {**same, "diaChi": "Số 12 đường Một"}
    assert dia_chi.declared_detail_finding("Subject_HometownDomestic", house, documents) is None


def test_nguoi_chet_khong_soat_dia_chi():
    documents = [{"name": "a.pdf", "text": "Thôn Tân Hiền, xã Hoà Bình"}]
    value = {"tinh": "Bắc Ninh", "xa": "Hòa Bình", "diaChi": "Đã chết"}
    assert dia_chi.address_finding("Mother_ResidenceDomestic", value, documents,
                                   dia_chi.printed_lines(documents)) is None


def test_ho_ten_thong_nhat_di_theo_phan_quyet():
    options = {"_reasoning_context": "<quan_he_nguoi_yeu_cau>\nKết luận: bản thân\nHọ tên thống nhất: NGUYỄN VĂN AN\n"}
    out = dot_hai._with_self_name(options, {"Subject_FullName": "NGUYỄN VĂN AN"},
                                  {"Subject_FullName": "NGUYỄN VĂN ẤN"})
    assert "Họ tên thống nhất: NGUYỄN VĂN ẤN" in out["_reasoning_context"]
    same = dot_hai._with_self_name(options, {"Subject_FullName": "A B C"}, {"Subject_FullName": "A B C"})
    assert same is options


def test_patch_chi_va_o_phan_quyet_lam_doi(monkeypatch):
    async def fake_review(documents, values, options=None):
        return Result({**values, "Mother_FullName": "TRẦN THỊ THIỀM"}, [{"inspector": "dinh_danh"}], {})

    def fake_enrich(fields, options=None):
        values = {f["name"]: f["value"] for f in fields}
        return [{"name": "HoTenMeKS", "comp": "x-input", "value": values.get("Mother_FullName")},
                {"name": "HoTenChaKS", "comp": "x-input", "value": values.get("Father_FullName")}]

    monkeypatch.setattr(dot_hai, "review", fake_review)
    monkeypatch.setattr(dot_hai.mapper, "enrich", fake_enrich)
    raw = [{"name": "Mother_FullName", "value": "TRẦN THỊ THIEM"}, {"name": "Father_FullName", "value": "LÊ VĂN AN"}]
    # Lượt đầu nơi gọi pipeline đã chỉnh ô cha (theo tài khoản) — không được coi là phán quyết làm đổi.
    base = [{"name": "HoTenMeKS", "comp": "x-input", "value": "TRẦN THỊ THIEM"},
            {"name": "HoTenChaKS", "comp": "x-input", "value": "LÊ VĂN ÂN"}]
    out = asyncio.run(dot_hai.patch([], raw, base, {}))
    assert [(f["name"], f["value"], f["from"], f["by"]) for f in out["fields"]] == [
        ("HoTenMeKS", "TRẦN THỊ THIỀM", "TRẦN THỊ THIEM", "dinh_danh")]


def test_review_dung_hai_thanh_tra():
    assert [inspector.key for inspector in thanh_tra.INSPECTORS] == ["dinh_danh", "giay_to", "dia_chi"]


def test_nhieu_giay_hon_thang_mot_giay_co_quan_cap():
    values = {"Father_FullName": "LÊ VĂN NƠI"}
    declaration = f"{_DECLARATION_HEAD}\nHọ, chữ đệm, tên người cha: Lê Văn Nơi\n(Ký, ghi rõ họ, chữ đệm, tên)"
    pledge = "BẢN CAM ĐOAN\nCha tôi là Lê Văn Nơi"
    birth = "GIẤY KHAI SINH\nHọ, chữ đệm, tên người cha: LÊ VĂN HỚI"
    records = [_record("LÊ VĂN HỚI", role="cha", text=birth)]
    role, person, links = _links("cha", values, records)
    assert dinh_danh.name_finding(role, person, links, _docs(declaration, pledge, birth)) is None


def _account_docs(*texts, name="ĐINH VĂN TÙNG", number="001057000001"):
    return [*_docs(*texts), dinh_danh.account_document({"formContext": {"applicantFullname": name,
                                                                        "applicantIdentityNumber": number}})]


def test_ten_tai_khoan_thang_moi_giay_khi_trung_so():
    role = chu_the.ROLE_BY_KEY["cha"]
    person = {"name": "ĐINH VĂN TÙY", "number": "001057000001", "birth": "", "ethnic": ""}
    finding = dinh_danh.account_finding(role, person, _account_docs("TRÍCH LỤC\nHọ tên cha: ĐINH VĂN TÙY"))
    assert finding.values == {"Father_FullName": "ĐINH VĂN TÙNG"}


def test_ten_tai_khoan_khac_han_thi_khong_dong():
    role = chu_the.ROLE_BY_KEY["me"]
    person = {"name": "NGÔ THỊ TÁM", "number": "", "birth": "", "ethnic": ""}
    assert dinh_danh.account_finding(role, person, _account_docs("x")) is None
    person = {"name": "ĐINH VĂN TÙY", "number": "001057000999", "birth": "", "ethnic": ""}
    assert dinh_danh.account_finding(chu_the.ROLE_BY_KEY["cha"], person, _account_docs("x")) is None


def test_tai_lieu_tai_khoan_khong_tinh_vao_dem_giay():
    assert dinh_danh.spelling_support("ĐINH VĂN TÙNG", _account_docs("x"))["giay"] == 0


# --- thanh tra giấy tờ tùy thân (số định danh theo MRZ, ngày cấp theo mặt sau thẻ) ---
_MRZ_BACK = """Ngày, tháng, năm / Date, month, year: 23/04/2021
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
IDVNM0601234567001160012345<<1
6001014F2601014VNM<<<<<<<<<<<0
TRAN<<THI<MAU<<<<<<<<<<<<<<<<<"""


def _giay_to_case(values, *texts):
    from app.pipelines._shared.thanh_tra.ho_so import Case
    return Case(_docs(*texts), "", values, {})


def test_so_dinh_danh_theo_mrz_khi_mat_the_doc_lech():
    from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra import giay_to
    case = _giay_to_case({"Mother_FullName": "TRẦN THỊ MẪU", "Mother_IdNumber": "001160012845"}, _MRZ_BACK)
    found = {f.unit.key: f.values for f in giay_to.findings_from(case)}
    assert found["me.so_dinh_danh"] == {"Mother_IdNumber": "001160012345"}
    assert found["me.ngay_cap"] == {"Mother_IdIssueDate": "23/04/2021"}


def test_ngay_cap_dang_co_chi_doi_khi_nhieu_giay_hon():
    from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra import giay_to
    values = {"Mother_FullName": "TRẦN THỊ MẪU", "Mother_IdNumber": "001160012345", "Mother_IdIssueDate": "28/04/2021"}
    tk = f"{_DECLARATION_HEAD}\nGiấy tờ tùy thân: CCCD số 001160012345 cấp ngày 28/04/2021"
    assert giay_to.findings_from(_giay_to_case(values, _MRZ_BACK, tk)) == []
    pledge = "BẢN CAM ĐOAN\nCCCD số 001160012345 cấp ngày 23/04/2021"
    found = giay_to.findings_from(_giay_to_case(values, _MRZ_BACK, tk, pledge))
    assert [f.values for f in found] == [{"Mother_IdIssueDate": "23/04/2021"}]


def test_mrz_nam_khong_vao_vai_me():
    from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra import giay_to
    # Số mã hoá giới tính nam (chữ số thứ tư là 0) thì không phải thẻ của mẹ dù trùng họ tên không dấu.
    back = _MRZ_BACK.replace("6001014F", "6001014M").replace("001160012345", "001060012345")
    case = _giay_to_case({"Mother_FullName": "TRẦN THỊ MẪU"}, back)
    assert not any(f.unit.key == "me.so_dinh_danh" for f in giay_to.findings_from(case))


def test_tai_khoan_ten_ngan_lech_hai_chu_khong_phai_cha():
    person = {"name": "VÀNG A SẨU", "number": "", "birth": "", "ethnic": ""}
    docs = _account_docs("x", name="VÀNG A LÀI", number="014200000001")
    assert dinh_danh.account_finding(chu_the.ROLE_BY_KEY["cha"], person, docs) is None


def test_ban_cam_doan_quet_lien_sau_to_khai_khong_tinh_la_viet_tay():
    text = (f"{_DECLARATION_HEAD}\nHọ, chữ đệm, tên người cha: Vũ Định Cướng\nBẢN CAM ĐOAN\n"
            "Họ và tên bố: VŨ ĐÌNH CƯỜNG")
    lines = dinh_danh.declaration_lines({"text": text})
    assert [handwritten for _, line, handwritten in lines if "CƯỜNG" in line] == [False]
    assert dinh_danh._letters_on_paper("VŨ ĐỊNH CƯỚNG", _docs(text))


def test_tai_khoan_cua_con_khong_ap_cho_cha_khi_khong_trung_so():
    person = {"name": "VŨ ĐỊNH CƯỚNG", "number": "", "birth": "", "ethnic": ""}
    docs = _account_docs("x", name="VŨ ĐÌNH DŨNG", number="037070000001")
    assert dinh_danh.account_finding(chu_the.ROLE_BY_KEY["cha"], person, docs) is None
    requester = {"name": "VŨ ĐÌNH DỦNG", "number": "", "birth": "", "ethnic": ""}
    finding = dinh_danh.account_finding(chu_the.ROLE_BY_KEY["nyc"], requester, docs)
    assert finding.values == {"Requester_FullName": "VŨ ĐÌNH DŨNG"}


# --- tên xã của địa chỉ mà ô xã trên cổng sẽ trống (ten_xa) ---

from app.pipelines.khai_sinh_dang_ky_lai.thanh_tra import ten_xa  # noqa: E402


def test_xa_ngoai_danh_muc_la_o_trong():
    assert ten_xa.blank_ward("Requester_ResidenceDomestic",
                             {"tinh": "Bắc Ninh", "xa": "Phường Hinh Bắtz", "diaChi": "Thôn A"})
    assert ten_xa.blank_ward("Requester_ResidenceDomestic",
                             {"tinh": "Bắc Ninh", "xa": "Phường Kinh Bắc", "diaChi": "Thôn A"}) is None
    assert ten_xa.blank_ward("Father_ResidenceDomestic", {"tinh": "", "xa": "", "diaChi": "Đã chết"}) is None


def test_rule_ten_xa_sau_chu_phuong_tren_dong_cua_o():
    docs = [{"name": "tk.pdf", "text": "Nơi cư trú: TDP(thôn). Tổ Một phường(xã). Kinh Bắc tỉnh(1) Bắc Ninh"}]
    value = {"tinh": "Bắc Ninh", "xa": "Tổ Một", "diaChi": "TDP(thôn)"}
    province, wards = ten_xa.blank_ward("Requester_ResidenceDomestic", value)
    assert ten_xa.rule_ward("Requester_ResidenceDomestic", value, province, wards, docs)[0] == "Phường Kinh Bắc"


def test_rule_cum_thu_hai_chi_khi_luot_trich_khong_co_chi_tiet():
    docs = [{"name": "tk.pdf", "text": "Nơi sinh: Bản Nậm Xyzt, Bình Lư, Lai Châu"}]
    value = {"tinh": "Lai Châu", "xa": "Bản Nậm Xyzt", "diaChi": ""}
    province, wards = ten_xa.blank_ward("Subject_BirthPlaceDomestic", value)
    assert ten_xa.rule_ward("Subject_BirthPlaceDomestic", value, province, wards, docs)[0] == "Xã Bình Lư"
    # Có chi tiết: cụm lượt trích lấy làm xã là cấp xã đọc lệch, cụm sau là cấp huyện → không lấy.
    docs = [{"name": "tk.pdf", "text": "Nơi sinh: Thôn Hai - Bản Nậm Xyzt - Bình Lư - Lai Châu"}]
    value = {"tinh": "Lai Châu", "xa": "Bản Nậm Xyzt", "diaChi": "Thôn Hai"}
    assert ten_xa.rule_ward("Subject_BirthPlaceDomestic", value, province, wards, docs) == ("", "")


def test_rule_khong_lay_thi_xa_va_dong_cua_nguoi_khac():
    docs = [{"name": "tk.pdf", "text": "Nơi cư trú: Thôn A - xã Tam Đa\nNơi cư trú: Thôn B - phường Kinh Bắc"}]
    value = {"tinh": "Bắc Ninh", "xa": "Tổ Ba", "diaChi": "Thôn B"}
    province, wards = ten_xa.blank_ward("Mother_ResidenceDomestic", value)
    assert ten_xa.rule_ward("Mother_ResidenceDomestic", value, province, wards, docs)[0] == "Phường Kinh Bắc"
    docs = [{"name": "cc.pdf", "text": "Quê quán: Thôn C, Thị xã Kinh Bắc"}]
    value = {"tinh": "Bắc Ninh", "xa": "", "diaChi": "Thôn C"}
    province, wards = ten_xa.blank_ward("Subject_HometownDomestic", value)
    assert ten_xa.rule_ward("Subject_HometownDomestic", value, province, wards, docs) == ("", "")


def test_llm_chon_xa_phai_co_tren_dong_trich(monkeypatch):
    docs = [{"name": "tk.pdf", "text": "Kính gửi: UBND phường Kinh Bắc\nNơi cư trú: Thôn A - phường Hinh Bắtz"}]
    value = {"tinh": "Bắc Ninh", "xa": "Phường Hinh Bắtz", "diaChi": "Thôn A"}

    async def answer(xa, line):
        async def chat(*args, **kwargs):
            return '{"xa": "%s", "dong_dia_chi": "%s", "dong_phu": ""}' % (xa, line)
        monkeypatch.setattr(ten_xa.base.client, "chat", chat)
        return await ten_xa.fixes({"Requester_ResidenceDomestic": value}, ("Requester_ResidenceDomestic",), docs,
                                  {"counterWard": "HCC phường Kinh Bắc"})

    fixed = asyncio.run(answer("Phường Kinh Bắc", "Kính gửi: UBND phường Kinh Bắc"))
    assert fixed["Requester_ResidenceDomestic"]["value"]["xa"] == "Phường Kinh Bắc"
    assert fixed["Requester_ResidenceDomestic"]["by"] == "llm"
    # Tên không có trên dòng LLM trích → không nhận; mã cũng không có căn cứ → không sửa.
    assert asyncio.run(answer("Phường Võ Cường", "Kính gửi: UBND phường Kinh Bắc")) == {}


def test_thanh_tra_dia_chi_de_xuat_xa_cho_o_trong(monkeypatch):
    docs = [{"name": "tk.pdf", "text": "Nơi cư trú: TDP(thôn). Tổ Một phường(xã). Kinh Bắc tỉnh(1) Bắc Ninh"}]
    value = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Tổ Một", "diaChi": "TDP(thôn)"}

    async def chat(*args, **kwargs):
        return '{"xa": ""}'
    monkeypatch.setattr(ten_xa.base.client, "chat", chat)
    case = dia_chi.Case(docs, "", {"Requester_ResidenceDomestic": value}, {})
    findings = asyncio.run(dia_chi.find(dia_chi.INSPECTOR, case, ""))
    assert [f.values["Requester_ResidenceDomestic"]["xa"] for f in findings] == ["Phường Kinh Bắc"]
    assert findings[0].backed and "danh mục hiện hành" in findings[0].evidence[0]


def test_rule_ten_xa_doc_lech_lay_theo_dong_kinh_gui():
    docs = [{"name": "tk.pdf", "text": "Kính gửi: (1)UBND Phường Kinh Bắc\nNơi cư trú: Thôn A - Phường Hinh Bắt - TP Bắc Ninh\n"
                                       "Nơi cư trú: Thôn B - phường Võ Cường"}]
    value = {"tinh": "Bắc Ninh", "xa": "Phường Hinh Bắt", "diaChi": "Thôn A"}
    province, wards = ten_xa.blank_ward("Requester_ResidenceDomestic", value)
    assert ten_xa.rule_ward("Requester_ResidenceDomestic", value, province, wards, docs) == (
        "Phường Kinh Bắc", "Kính gửi: (1)UBND Phường Kinh Bắc")
    # Tên gần giống chỉ có ở dòng địa chỉ khác (nơi ở của người khác) → không lấy.
    docs = [{"name": "tk.pdf", "text": "Nơi cư trú: Thôn B - phường Kinh Bắc\nNơi cư trú: Thôn A - Phường Hinh Bắt"}]
    assert ten_xa.rule_ward("Requester_ResidenceDomestic", value, province, wards, docs) == ("", "")


def test_nam_sinh_me_theo_don_in_thay_to_khai_viet_tay():
    don = "ĐƠN XIN XÁC NHẬN\nTôi là con của bà Trần Thị Mẫu sinh năm 1920, đã mất."
    values = {"Mother_FullName": "Trần Thị Mẫu", "Mother_BirthDateOrYear": "1936"}
    records = [_record("Trần Thị Mẫu", role="mẹ", handwritten=True, text="Năm sinh: 1936", birth_text="1936"),
               _record("Trần Thị Mẫu", role="mẹ", text=don, birth_text="1920")]
    [finding] = [f for f in dinh_danh.findings_from(records, values, [{"text": don}]) if f.unit.key == "me.nam_sinh"]
    assert finding.values == {"Mother_BirthDateOrYear": "1920"} and finding.backed
    assert finding.quote == "Tôi là con của bà Trần Thị Mẫu sinh năm 1920, đã mất."
    # Năm của lượt trích cũng có trên giấy in → không đổi.
    records.append(_record("Trần Thị Mẫu", role="mẹ", text="TRÍCH LỤC KHAI TỬ\nNăm sinh: 1936", birth_text="1936"))
    assert not [f for f in dinh_danh.findings_from(records, values, [{"text": don}]) if f.unit.key == "me.nam_sinh"]
