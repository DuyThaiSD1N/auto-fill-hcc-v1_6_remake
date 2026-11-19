"""Khai sinh cho người đã có hồ sơ: các lỗi phân vai / lọc field / thanh tra đợt 2 đo trên trace prod (giá trị giả)."""
from app.pipelines._shared.thanh_tra.ho_so import Case
from app.pipelines.khai_sinh_co_ho_so.process import mapper, reason
from app.pipelines.khai_sinh_co_ho_so.thanh_tra import chu_the, dinh_danh, giay_to


def _role(name, ident="Không xác định", birth="Không xác định", gender="Không xác định", source="Bản cam đoan"):
    return (f"Họ tên: {name}\nSố CCCD/CMND: {ident}\nNgày sinh: {birth}\nGiới tính: {gender}\nDân tộc: Không xác định\n"
            f"Quốc tịch: Việt Nam\nTrạng thái: còn sống\nNguồn: {source}\nCăn cứ phân vai: theo giấy")


def test_dong_quan_he_con_la_nguoi_khac_khong_phai_ban_than():
    assert reason._normalized_relation("Con một") == "khác"
    assert reason._normalized_relation("Cháu nội") == "khác"
    assert reason._normalized_relation("Người được ủy quyền") == "khác"
    assert reason._normalized_relation("Ba") == ""  # miền Nam gọi cha là "ba": không ép "khác"


def test_khong_to_khai_nguoi_cam_doan_trung_con_la_ban_than_du_agent_ghi_cha():
    con = _role("Nguyễn Văn Con", "001083000001", "01/01/1983", "Nam")
    sections = {"con": con, "cha": _role("Nguyễn Văn Cha", "001051000002", "01/01/1951", "Nam"), "me": ""}
    raw = "<quan_he_nguoi_yeu_cau>\nKết luận: cha\nCăn cứ: agent\n</quan_he_nguoi_yeu_cau>"
    requester = con + "\nVai trò đồng thời: con"
    relation, _ = reason._validated_relation(raw, sections, False, ("", ""), [], requester)
    assert relation == "bản thân"


def test_to_khai_ghi_con_nhung_nguoi_yeu_cau_la_cha():
    cha = _role("Trần Văn Cha", "001060000003", "01/01/1960", "Nam")
    sections = {"con": _role("Trần Văn Con", "001090000004", "01/01/1990", "Nam"), "cha": cha, "me": ""}
    doc = {"name": "to-khai.pdf", "text": "TỜ KHAI ĐĂNG KÝ KHAI SINH\nQuan hệ với người được khai sinh: Con\n"}
    relation, _ = reason._validated_relation("", sections, True, ("", ""), [doc], cha)
    assert relation == "cha"


def test_mat_sau_the_cap_truoc_2024_khong_ghi_bo_cong_an():
    back = ("BỘ CÔNG AN\nCỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
            "Ngày, tháng, năm / Date, month, year: 09/05/2021\nBỘ CÔNG AN\n"
            "IDVNM0580000011001058000011<<1\n5801011F4101011VNM<<<<<<<<<<<8\nTRAN<<THI<A<<<<<<<<<<<<<<<<<<<")
    backs = reason._mrz_card_backs([{"name": "the.pdf", "text": back}])
    assert backs["001058000011"]["issue_place"] == reason.ISSUER_CUC


def test_nam_sinh_cha_me_giu_khi_khoi_con_hop_ly_du_field_con_doc_lech():
    fields = [{"name": "Subject_BirthDate", "comp": "x", "value": "21/05/1938"},
              {"name": "Father_BirthDateOrYear", "comp": "x", "value": "1928"}]
    context = "<con>\n" + _role("Lê Thị Con", birth="21/05/1978") + "\n</con>\n<cha>\n" + _role("Lê Văn Cha", birth="1928") + "\n</cha>"
    out = {f["name"]: f["value"] for f in reason._parent_birth_from_context(fields, context)}
    assert out.get("Father_BirthDateOrYear") == "1928"


def test_tai_khoan_khong_de_dia_chi_giay_to():
    options = {"formContext": {"applicantFullname": "PHẠM VĂN A", "applicantIdentityNumber": "001080000005",
                               "applicantAddress": {"diaChi": "SỐ NHÀ 1 ĐƯỜNG X", "tinh": "56", "xa": "22366"}}}
    person = mapper._with_account({"ho_ten": "Phạm Văn A", "so_dinh_danh": "001080000005",
                                   "noi_cu_tru": {"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Nha Trang",
                                                  "diaChi": "1 X"}}, options)
    assert person["noi_cu_tru"]["diaChi"] == "1 X"
    assert person["ho_ten"] == "PHẠM VĂN A"


def test_cha_con_trung_ten_the_mrz_cua_con_khong_thanh_so_cha():
    # MRZ duy nhất đọc được là thẻ của con (sinh 1975); cha cùng họ tên sinh 1946 → không đề xuất đổi số cha.
    text = "IDVNM0750000011001075000011<<1\n7505101M4101011VNM<<<<<<<<<<<8\nBUI<<THANH<SANG<<<<<<<<<<<<<<<<"
    role = chu_the.ROLE_BY_KEY["cha"]
    person = {"name": "BÙI THANH SANG", "number": "001046000012", "birth": "18/10/1946", "ethnic": ""}
    assert giay_to._mrz_card(role, person, [{"name": "the.pdf", "text": text}]) is None


def test_nam_sinh_de_xuat_trai_so_dinh_danh_hoac_tre_hon_con_bi_chan():
    person = {"name": "X", "number": "012169000001", "birth": "29/12/1969", "ethnic": ""}
    assert dinh_danh._impossible_birth("1990", person, 1986)
    assert not dinh_danh._impossible_birth("1969", person, 1986)
    assert dinh_danh._impossible_birth("1975", {"number": ""}, 1986)


def test_sanitize_dung_lai_nguoi_duoc_khai_sinh_khi_trich_nham_the_khac():
    con = _role("Thào Thị Con", "012092000006", "03/10/1992", "Nữ")
    context = (f"<nguoi_yeu_cau>\n{con}\nVai trò đồng thời: con\n</nguoi_yeu_cau>\n<con>\n{con}\n</con>\n"
               "<to_khai_dang_ky_khai_sinh>\nCó tờ khai đăng ký khai sinh: Không\n</to_khai_dang_ky_khai_sinh>")
    fields = [{"name": "Subject_FullName", "comp": "x-input", "value": "VÀNG A KHÁC"},
              {"name": "Subject_IdNumber", "comp": "x-input", "value": "012205000007"},
              {"name": "Subject_BirthDate", "comp": "x-date", "value": "08/09/2005"}]
    out = {f["name"]: f for f in reason.sanitize_extracted_fields(fields, context)}
    assert out["Subject_FullName"]["value"] == "Thào Thị Con"
    assert out["Subject_IdNumber"]["value"] == "012092000006"
    assert out["Subject_FullName"].get("default") is True


def test_the_nguoi_dang_nhap_cung_ho_hon_tuoi_la_cha():
    card = {"name": "CỨ A CHA", "id": "012082000008", "year": 1982, "gender": "nam",
            "section": "Họ tên: CỨ A CHA\nSố CCCD/CMND: 012082000008\nNgày sinh: 01/01/1982\nGiới tính: Nam"}
    sections = {"con": _role("CỨ THỊ CON", birth="15/12/2007", gender="Nữ"), "cha": "", "me": ""}
    out = reason._applicant_card_as_father(sections, card)
    assert reason._role_id(out["cha"]) == "012082000008"
    relation, _ = reason._validated_relation("", out, False, ("CỨ A CHA", "012082000008"), [], "")
    assert relation == "cha"
    # Khác họ (cán bộ quét kèm thẻ của mình) → không nhận làm cha.
    other = {**card, "name": "LÒ VĂN CÁN BỘ"}
    assert reason._applicant_card_as_father(sections, other)["cha"] == ""


def test_cmnd_mau_cu_chung_trang_voi_cccd_nguoi_khac_tach_thanh_hai_the():
    text = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY CHỨNG MINH NHÂN DÂN\nSỐ 045000009\nHọ tên: LÒ THỊ A\n"
            "Sinh ngày 15-6-1988\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nCĂN CƯỚC CÔNG DÂN\nSố / No.: 012073000010\n"
            "Họ và tên / Full name:\nLÒ VĂN B\nNgày sinh / Date of birth: 02/03/1973\nGiới tính / Sex: Nam\n")
    people = [reason._person_from_document(unit) for unit in reason._identity_units([{"name": "the.pdf", "text": text}])]
    assert [(p["name"], p["id"]) for p in people] == [("LÒ THỊ A", "045000009"), ("LÒ VĂN B", "012073000010")]


def test_noi_cap_viet_tat_bo_ca():
    from app.pipelines._shared.compact_agent.issuer import ISSUER_BO_CONG_AN, normalize_issuer
    assert normalize_issuer("Bộ CA cấp") == ISSUER_BO_CONG_AN


def test_ngay_cap_noi_cap_doc_tu_dong_giay_to_tuy_than_ban_cam_doan():
    docs = [{"name": "cam-doan.pdf", "text": "Giấy tờ tùy thân (3): CCCD 012085000005 Do Bộ CA cấp ngày 27/08/2025"}]
    sections = {"cha": _role("B", "012085000005", "1985", "Nam"), "con": "", "me": ""}
    cha = reason._apply_id_line_facts(sections, docs)["cha"]
    assert reason._labeled_value(cha, "Ngày cấp") == "27/08/2025"
    assert reason._labeled_value(cha, "Nơi cấp") == reason.ISSUER_BO_CONG_AN


def test_noi_cap_the_12_so_theo_ngay_cap():
    values = {"Father_IdNumber": "012082000009", "Father_IdIssueDate": "04/11/2024",
              "Father_IdIssuePlace": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"}
    assert mapper._issuer_or_default(values, "Father") == "Bộ Công an"
    assert mapper._issuer_or_default({**values, "Father_IdIssuePlace": "Công an tỉnh X"}, "Father") == "Bộ Công an"
    old = {"Father_IdNumber": "012082000009", "Father_IdIssueDate": "04/11/2014", "Father_IdIssuePlace": "Công an tỉnh X"}
    assert mapper._issuer_or_default(old, "Father") == "Công an tỉnh X"


def test_ho_cha_it_dau_hon_nhung_hai_giay_co_quan_in_cung_cach_viet():
    docs = [
        {"name": "tk.pdf", "text": "TỜ KHAI ĐĂNG KÝ KHAI SINH\nHọ, chữ đệm, tên người cha: TIẾN VĂN AN"},
        {"name": "cd.pdf", "text": "BẢN CAM ĐOAN\nHọ và tên người cha: TIẾN VĂN AN"},
        {"name": "tl.pdf", "text": "TRÍCH LỤC KHAI SINH\nHọ, chữ đệm, tên người cha: Tiên Văn An"},
        {"name": "gks.pdf", "text": "GIẤY KHAI SINH\nỦY BAN NHÂN DÂN\nHọ và tên người đi khai sinh: Tiên Văn An"},
    ]
    assert dinh_danh.spelling_wins("TIẾN VĂN AN", "TIÊN VĂN AN", docs)
    assert not dinh_danh.spelling_wins("TIÊN VĂN AN", "TIẾN VĂN AN", docs)
    assert not dinh_danh._printed_mark_variant("TIẾN VĂN AN", "TIEN VĂN AN", docs)  # chữ trơn = OCR rơi dấu


def test_thang_viet_tay_net_gach_doc_thanh_so_1():
    assert reason.fix_slash_month("10/21/1937") == "10/2/1937"
    assert reason.fix_slash_month("5/71/1990") == "5/7/1990"
    assert reason.fix_slash_month("10/11/1937") == "10/11/1937"  # tháng 11 có thật: giữ
    assert reason.fix_slash_month("1937") == "1937"
    out = mapper.enrich([{"name": "Mother_FullName", "comp": "x-input", "value": "Phan Thị A"},
                         {"name": "Mother_BirthDateOrYear", "comp": "x-input", "value": "10/21/1937"}], {})
    assert {f["name"]: f.get("value") for f in out}.get("NamSinhMeKS") in ("10/2/1937", "10/02/1937")
