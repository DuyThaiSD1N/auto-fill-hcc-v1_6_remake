"""Đăng ký lại khai sinh: phân vai — luật thế hệ chỉ dự phòng, số trùng chỉ bỏ số, thẻ duy nhất của cha/mẹ."""
from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason


def _card(name: str, number: str, birth: str, gender: str) -> dict:
    return {
        "name": f"cccd-{number[-3:]}.pdf",
        "text": (
            f"CĂN CƯỚC CÔNG DÂN\nSố / No.: {number}\n"
            f"Họ và tên / Full name: {name}\n"
            f"Ngày sinh / Date of birth: {birth}\n"
            f"Giới tính / Sex: {gender} Quốc tịch / Nationality: Việt Nam"
        ),
    }


def _death(name: str, birth: str, gender: str) -> dict:
    return {
        "name": "trich-luc-khai-tu.pdf",
        "text": (
            "Phần ghi về người được khai tử:\n"
            f"Họ, chữ đệm, tên: {name}\n"
            f"Giới tính: {gender} Dân tộc: Kinh Quốc tịch: Việt Nam\n"
            f"Ngày, tháng, năm sinh: {birth}"
        ),
    }


def _role(name: str, number: str = "", birth: str = "", gender: str = "", status: str = "còn sống") -> str:
    return (
        f"Họ tên: {name}\nSố CCCD/CMND: {number or 'Không xác định'}\nNgày sinh: {birth or 'Không xác định'}\n"
        f"Giới tính: {gender or 'Không xác định'}\nDân tộc: Kinh\nQuốc tịch: Việt Nam\nTrạng thái: {status}\n"
        "Nguồn: giay-to.pdf\nCăn cứ phân vai: thử"
    )


def test_ghi_chu_ngoac_nhon_tach_khoi_ho_ten():
    assert reason.split_name_note("LÊ THỊ MẪU <Đã chết>") == ("LÊ THỊ MẪU", "Đã chết")
    assert reason._names_align("LÊ THỊ MẪU <Đã chết>", "Lê Thị Mẫu")


def test_so_cha_trung_so_con_chi_bo_so_giu_nguoi():
    sections = {
        "con": _role("LÊ VĂN THỬ", "001090000001", "01/01/1990", "Nam"),
        "cha": _role("LÊ VĂN GỐC", "001090000001", "1960", "Nữ"),
        "me": reason._unknown_role_section("không có"),
    }
    result = reason._validate_family_sections(sections)
    cha = result["cha"]
    assert reason._role_name(cha) == "LÊ VĂN GỐC"
    assert reason._role_id(cha) == ""
    assert reason._labeled_value(cha, "Giới tính") == "Không xác định"


def test_mot_the_kem_khai_tu_cung_the_he_khong_gan_lam_con():
    documents = [
        _card("TRẦN THỊ MẪU", "001160000002", "01/01/1960", "Nữ"),
        _death("LÊ VĂN GỐC", "01/01/1958", "Nam"),
    ]
    sections = {tag: reason._unknown_role_section("x") for tag in reason._FAMILY_TAGS}
    assert reason._is_unknown(reason._repair_single_identity_as_subject(sections, documents)["con"])


def test_mot_the_kem_khai_tu_the_he_truoc_van_la_con():
    documents = [
        _card("LÊ VĂN THỬ", "001190000003", "01/01/1990", "Nam"),
        _death("LÊ VĂN GỐC", "01/01/1958", "Nam"),
    ]
    sections = {tag: reason._unknown_role_section("x") for tag in reason._FAMILY_TAGS}
    result = reason._repair_single_identity_as_subject(sections, documents)
    assert reason._role_name(result["con"]) == "LÊ VĂN THỬ"


def test_the_he_khong_de_agent_khi_agent_chot_nguoi_khac_hop_ly():
    # Ba người đúng khuôn thế hệ, nhưng agent chốt người được đăng ký lại là người lớn (theo bản cam đoan)
    # và gia đình agent không tự mâu thuẫn → giữ agent.
    documents = [
        _card("LÊ VĂN THỬ", "001170000004", "01/01/1970", "Nam"),
        _card("LÊ THỊ CHÁU", "001195000005", "01/01/1995", "Nữ"),
        _death("LÊ VĂN GỐC", "01/01/1940", "Nam"),
    ]
    sections = {
        "con": _role("LÊ VĂN THỬ", "001170000004", "01/01/1970", "Nam"),
        "cha": _role("LÊ VĂN GỐC", "", "01/01/1940", "Nam", "đã chết"),
        "me": reason._unknown_role_section("x"),
    }
    result = reason._override_family_by_generation(sections, documents)
    assert reason._role_name(result["con"]) == "LÊ VĂN THỬ"


def test_agent_tu_mau_thuan_thi_khong_hop_ly():
    sections = {
        "con": _role("LÊ VĂN THỬ", "", "01/01/1970", "Nam"),
        "cha": _role("LÊ VĂN GỐC", "", "01/01/1965", "Nam"),
        "me": reason._unknown_role_section("x"),
    }
    assert not reason._agent_family_plausible(sections)
    sections["cha"] = _role("LÊ VĂN GỐC", "", "01/01/1940", "Nam")
    assert reason._agent_family_plausible(sections)


def test_nguoi_yeu_cau_la_me_mot_ho_ten_mot_so():
    values = {"Mother_FullName": "TRẦN THỊ MẪU", "Mother_IdNumber": "001160000002"}
    requester = {"ho_ten": "TRẦN THỊ MẨU", "so_dinh_danh": "001160000092"}
    mapper._unify_parent_requester(requester, values, "MeDe", False, {})
    assert requester["ho_ten"] == "TRẦN THỊ MẪU"
    assert requester["so_dinh_danh"] == "001160000002"


def test_nguoi_yeu_cau_khac_han_me_thi_khong_dong():
    values = {"Mother_FullName": "TRẦN THỊ MẪU", "Mother_IdNumber": "001160000002"}
    requester = {"ho_ten": "LÊ VĂN THỬ", "so_dinh_danh": "001190000003"}
    mapper._unify_parent_requester(requester, values, "MeDe", False, {})
    assert requester["ho_ten"] == "LÊ VĂN THỬ"


def test_agent_xep_the_duy_nhat_vao_con_bi_chuyen_sang_me():
    documents = [
        _card("TRẦN THỊ MẪU", "001160000002", "01/01/1960", "Nữ"),
        _death("LÊ VĂN GỐC", "01/01/1958", "Nam"),
    ]
    sections = {
        "con": _role("TRẦN THỊ MẪU", "001160000002", "01/01/1960", "Nữ"),
        "me": reason._unknown_role_section("x"),
        "cha": reason._unknown_role_section("x"),
    }
    result = reason._demote_single_card_spouse(sections, documents)
    assert reason._is_unknown(result["con"])
    assert reason._role_name(result["me"]) == "TRẦN THỊ MẪU"
    assert reason._role_name(result["cha"]) == "LÊ VĂN GỐC"


def test_ten_the_cung_so_nhung_khac_nguoi_khong_thanh_ten_thong_nhat():
    documents = [_card("TRẦN THỊ MẪU", "001160000002", "01/01/1960", "Nữ")]
    subject = _role("LÊ VĂN THỬ", "001160000002", "01/01/1990", "Nam")
    assert reason._self_card_name(subject, subject, documents) == ""
    ocr_lech = _role("TRẦN THỊ MẤU", "001160000002", "01/01/1960", "Nữ")
    assert reason._self_card_name(ocr_lech, ocr_lech, documents) == "TRẦN THỊ MẪU"


def _raw(requester: str, child: str, subject_in_relation: str) -> str:
    return (
        f"<nguoi_yeu_cau>\n{requester}\nVai trò đồng thời: mẹ\n</nguoi_yeu_cau>\n"
        f"<con>\n{child}\n</con>\n"
        f"<quan_he_nguoi_yeu_cau>\nNgười được đăng ký lại khai sinh: {subject_in_relation}\nKết luận: bản thân\n</quan_he_nguoi_yeu_cau>"
    )


def test_agent_ghi_con_la_con_cua_nguoi_yeu_cau_thi_theo_ket_luan_ban_than():
    requester = _role("LÊ THỊ CAM", "001168000006", "01/01/1968", "Nữ")
    daughter = _role("LÊ THỊ CHÁU", "001196000007", "01/01/1996", "Nữ")
    raw = _raw(requester, daughter, "Lê Thị Cam")
    sections = {"con": daughter, "me": reason._unknown_role_section("x"), "cha": reason._unknown_role_section("x")}
    result = reason._subject_from_relation_block(raw, sections, [])
    assert reason._role_name(result["con"]) == "LÊ THỊ CAM"


def test_ket_luan_quan_he_trung_con_thi_giu_nguyen():
    child = _role("LÊ THỊ CAM", "001168000006", "01/01/1968", "Nữ")
    raw = _raw(_role("TRẦN VĂN NỘP", "001170000008", "01/01/1970", "Nam"), child, "Lê Thị Cam")
    sections = {"con": child}
    assert reason._subject_from_relation_block(raw, sections, []) is sections


def test_the_he_thang_khi_nguoi_agent_chon_khong_co_the():
    # Gia đình đọc từ thẻ + hai giấy khai tử cha mẹ; agent lại chọn con của chủ thẻ (chỉ có tên trên giấy khai sinh).
    documents = [
        _card("LÊ VĂN THỬ", "001150000009", "01/01/1950", "Nam"),
        _death("LÊ VĂN GỐC", "01/01/1919", "Nam"),
        _death("TRẦN THỊ GỐC", "01/01/1920", "Nữ"),
    ]
    sections = {
        "con": _role("LÊ THỊ CHÁU", "", "01/01/1981", "Nữ"),
        "cha": _role("LÊ VĂN THỬ", "001150000009", "01/01/1950", "Nam"),
        "me": reason._unknown_role_section("x"),
    }
    result = reason._override_family_by_generation(sections, documents)
    assert reason._role_name(result["con"]) == "LÊ VĂN THỬ"



_TLKT = """TRÍCH LỤC KHAI TỬ
Phần ghi về người được khai tử:
Họ, chữ đệm, tên: LÊ VĂN GỐC
Ngày, tháng, năm sinh: 01/01/1940
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Giấy tờ tùy thân: Thẻ căn cước công dân số 001040000123, Cục CS QLHC về trật tự xã hội cấp ngày 23/04/2021
Phần ghi về người đi khai tử:
Giấy tờ tùy thân: CCCD số 001080000999 cấp ngày 01/01/2022"""


def test_giay_to_tuy_than_cua_nguoi_chet_tren_trich_luc_vao_khoi_cha():
    sections = {
        "con": _role("LÊ VĂN THỬ", "001190000003", "01/01/1990", "Nam"),
        "cha": _role("LÊ VĂN GỐC", "", "1940", "Nam", "đã chết"),
        "me": reason._unknown_role_section("x"),
    }
    cha = reason._apply_identity_card_facts(sections, [{"name": "tlkt.pdf", "text": _TLKT}])["cha"]
    assert reason._role_id(cha) == "001040000123"
    assert reason._labeled_value(cha, "Ngày cấp") == "23/04/2021"


def test_so_cccd_roi_so_0_dau_thi_bu_lai():
    out = mapper.enrich([{"name": "Mother_FullName", "value": "TRẦN THỊ MẪU"},
                         {"name": "Mother_IdNumber", "value": "51134004588"}], {})
    assert {f["name"]: f["value"] for f in out}["SoDinhDanhMe"] == "051134004588"


def test_ngay_cap_nguoi_yeu_cau_theo_the_trong_ho_so_khi_cung_so_tai_khoan():
    requester = {"ho_ten": "LÊ VĂN THỬ", "so_dinh_danh": "001190000003", "ngay_cap": "30/08/2021"}
    options = {"formContext": {"applicantFullname": "LÊ VĂN THỬ", "applicantIdentityNumber": "001190000003",
                               "applicantIdDate": "27/04/2024"}}
    assert mapper._with_account(requester, options)["ngay_cap"] == "30/08/2021"
    assert mapper._with_account({**requester, "ngay_cap": ""}, options)["ngay_cap"] == "27/04/2024"


def _card_no_colon(name: str, number: str, birth: str, gender: str) -> dict:
    # OCR thẻ rụng dấu ":" sau nhãn song ngữ số thẻ và giới tính.
    card = _card(name, number, birth, gender)
    text = card["text"].replace("Số / No.: ", "Số / No ").replace("Giới tính / Sex: ", "Giới tính / Sex ")
    return {**card, "text": text}


def test_the_ocr_thieu_dau_hai_cham_van_la_mot_nguoi_khi_phan_vai():
    child = _card_no_colon("LÊ VĂN THỬ", "001076000003", "01/01/1976", "Nam")
    person = reason._person_from_document(child)
    assert person and person["id"] == "001076000003" and person["year"] == 1976
    documents = [
        _death("TRẦN THỊ MẪU", "01/01/1941", "Nữ"),
        child,
        _card("LÊ VĂN GỐC", "001039000002", "01/01/1939", "Nam"),
    ]
    # Hai thẻ người còn sống → không phải ca "thẻ duy nhất của người góa", người con không bị hạ vai.
    assert reason._single_card_spouse(documents) is None


_TAP_SCAN = """───── Trang 1/3 ─────
GIẤY KHAI SINH
Họ, chữ đệm, tên: NGUYỄN THỊ CHỊ
Ngày, tháng, năm sinh: 01/01/1960
Giới tính: Nữ
Họ, chữ đệm, tên người mẹ: NGUYỄN VĂN BỐ
Họ, chữ đệm, tên người cha: TRẦN THỊ MẸ
───── Trang 2/3 ─────
TRÍCH LỤC KHAI TỬ
(BẢN SAO)
Họ, chữ đệm , tên : TRẦN THỊ MẸ
Ngày, tháng, năm sinh : 1935
Giới tính: Nữ Dân tộc: Kinh Quốc tịch: Việt Nam
───── Trang 3/3 ─────
TRÍCH LỤC KHAI TỬ
(BẢN SAO)
Họ, chữ đệm , tên : NGUYỄN VĂN BỐ
Ngày, tháng, năm sinh : 1930
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
"""

_UY_QUYEN = """GIẤY ỦY QUYỀN
1. Bên Ủy quyền:
- Họ tên: Nguyễn Văn Con
- Số CMND/CCCD/Hộ chiếu: 001065000001
2. Bên được Ủy quyền:
- Họ tên: Nguyễn Thị Chị
- Số CMND/CCCD/Hộ chiếu: 0271 001160000002
3. Nội dung Ủy quyền: Làm thủ tục đăng ký lại khai sinh
"""


def test_trich_luc_dau_cach_truoc_dau_phay_la_giay_rieng_khong_nuot_vao_giay_truoc():
    people = {p["name"]: p for p in reason._people_from_documents([{"name": "ho-so.pdf", "text": _TAP_SCAN}])}
    assert set(people) == {"TRẦN THỊ MẸ", "NGUYỄN VĂN BỐ"}
    assert all(reason._is_dead(p) for p in people.values())


def test_bo_the_nguoi_duoc_uy_quyen_de_luat_the_he_chot_gia_dinh():
    documents = [
        {"name": "ho-so.pdf", "text": _TAP_SCAN},
        {"name": "uy-quyen.pdf", "text": _UY_QUYEN},
        _card("NGUYỄN VĂN CON", "001065000001", "01/01/1965", "Nam"),
        _card("NGUYỄN THỊ CHỊ", "001160000002", "01/01/1960", "Nữ"),
    ]
    unknown = {tag: reason._unknown_role_section("x") for tag in ("con", "cha", "me")}
    result = reason._override_family_by_generation(unknown, documents)
    assert [reason._role_name(result[tag]) for tag in ("con", "cha", "me")] == [
        "NGUYỄN VĂN CON", "NGUYỄN VĂN BỐ", "TRẦN THỊ MẸ"]
