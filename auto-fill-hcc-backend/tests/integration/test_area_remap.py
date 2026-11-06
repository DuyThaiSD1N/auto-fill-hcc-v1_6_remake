from app.pipelines._shared import area_remap


def test_numeric_house_token_is_not_remapped_to_commune(monkeypatch):
    monkeypatch.setitem(
        area_remap._REMAP,
        ("lam dong", "1"),
        {"tinh": "Lâm Đồng", "xa": "Phường 1 Bảo Lộc"},
    )

    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương",
        "diaChi": "Cò/1 Đồng Tâm",
    })

    assert result == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương",
        "diaChi": "Cò/1 Đồng Tâm",
    }


def test_explicit_commune_number_still_remaps(monkeypatch):
    monkeypatch.setitem(
        area_remap._REMAP,
        ("lam dong", "1"),
        {"tinh": "Lâm Đồng", "xa": "Phường 1 Bảo Lộc"},
    )

    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường 1",
        "diaChi": "Đồng Tâm",
    })

    assert result["xa"] == "Phường 1 Bảo Lộc"
    assert result["diaChi"] == "Đồng Tâm"


def test_explicit_commune_does_not_scan_street_name(monkeypatch):
    monkeypatch.setitem(
        area_remap._REMAP,
        ("lam dong", "bui thi xuan"),
        {"tinh": "Lâm Đồng", "xa": "Phường Lang Biang - Đà Lạt"},
    )

    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương - Đà Lạt",
        "diaChi": "216 Bùi Thị Xuân",
    })

    assert result == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương - Đà Lạt",
        "diaChi": "216 Bùi Thị Xuân",
    }


def _ha_noi(xa, dia_chi="Số 1 ngõ 2", **kwargs):
    return area_remap.remap_area({"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": xa, "diaChi": dia_chi}, **kwargs)


def test_ha_noi_split_ward_uses_remaining_part_destination():
    # NQ 1656: Phú La một phần vào Dương Nội, phần còn lại vào Kiến Hưng.
    assert _ha_noi("Phú La")["xa"] == "Phường Kiến Hưng"
    assert _ha_noi("Phường Phú La")["xa"] == "Phường Kiến Hưng"
    assert _ha_noi("Hà Cầu")["xa"] == "Phường Kiến Hưng"


def test_ha_noi_same_fold_key_units_resolve_by_label_and_accent():
    assert _ha_noi("Phường Vạn Phúc")["xa"] == "Phường Hà Đông"
    assert _ha_noi("Xã Vạn Phúc")["xa"] == "Xã Nam Phù"
    assert _ha_noi("Xã Vân Phúc")["xa"] == "Xã Phúc Lộc"
    assert _ha_noi("Xã Quang Trung")["xa"] == "Xã Kiều Phú"


def test_ha_noi_ward_in_two_districts_needs_district():
    assert _ha_noi("Quang Trung")["xa"] == ""
    assert _ha_noi("Quang Trung", huyen_hint="Hà Đông")["xa"] == "Phường Kiến Hưng"
    assert _ha_noi("Quang Trung", dia_chi="Số 1, quận Đống Đa")["xa"] == "Phường Kim Liên"


def test_ha_noi_ward_split_three_ways_is_not_guessed():
    assert _ha_noi("Phường Nhân Chính")["xa"] == "Phường Nhân Chính"


def test_ha_noi_bare_current_name_is_not_taken_as_old_ward():
    # "Phường Thanh Trì" (Hoàng Mai cũ) đi Vĩnh Hưng, nhưng tên trần là xã Thanh Trì hiện hành.
    assert _ha_noi("Thanh Trì")["xa"] == "Xã Thanh Trì"
    assert _ha_noi("Phường Thanh Trì")["xa"] == "Phường Vĩnh Hưng"


def test_commune_name_starting_like_village_is_kept():
    assert _ha_noi("Sóc Sơn") == {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Xã Sóc Sơn", "diaChi": "Số 1 ngõ 2"}
    assert _ha_noi("Xã Tô Hiệu")["xa"] == "Xã Phú Xuyên"
    assert _ha_noi("Tổ 3", dia_chi="") == {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "", "diaChi": "Tổ 3"}


def test_bac_ninh_old_village_renamed_to_to_dan_pho_in_detail():
    def dia_chi(xa, chi_tiet):
        return area_remap.remap_area({"tinh": "Bắc Ninh", "xa": xa, "diaChi": chi_tiet})["diaChi"]

    assert dia_chi("Ngũ Thái", "Thôn Cửu Yên") == "Tổ dân phố Vũ Kiệt"
    assert dia_chi("Xuân Lâm", "THÔN DOÃN THƯỢNG") == "Tổ dân phố Thanh Lâm"
    assert dia_chi("Phường Song Liễu", "Khu phố Ngọc Lâm") == "Tổ dân phố Ngọc Liễu"
    assert dia_chi("Song Liễu", "Xóm.Ngọc Tỉnh") == "Tổ dân phố Liễu Khê"
    assert dia_chi("Song Liễu", "TDP Ngọc Tỉnh") == "TDP Liễu Khê"
    assert dia_chi("Song Liễu", "Số 5 Ngọc Tỉnh") == "Số 5 Liễu Khê"
    # Tên dài khớp trọn, không bị "Mãn Xá" cắt đôi; đổi xong gọi lại vẫn y nguyên.
    assert dia_chi("Hà Mãn", "Thôn Mãn Xá Đông") == "Tổ dân phố Mãn Xá"
    assert dia_chi("Song Liễu", "Thôn Mãn Xá") == "Tổ dân phố Mãn Xá"
    assert dia_chi("Song Liễu", "Tổ dân phố Mãn Xá") == "Tổ dân phố Mãn Xá"
    assert dia_chi("Song Liễu", "Thôn Đồng Ngư") == "Tổ dân phố Đồng Ngư"


def test_lai_chau_muong_kim_old_ban_renamed_in_detail():
    def dia_chi(xa, chi_tiet):
        return area_remap.remap_area({"tinh": "Lai Châu", "xa": xa, "diaChi": chi_tiet})["diaChi"]

    assert dia_chi("Mường Kim", "Bản Ngã Ba") == "Bản Chiềng Ban"
    assert dia_chi("Xã Mường Kim", "Bản Chiềng Ban 2") == "Bản Nà Dân"
    assert dia_chi("Mường Kim", "Bản Chiềng Ban 1") == "Bản Chiềng Ban"
    assert dia_chi("Mường Kim", "Thôn Mường 2") == "Bản Mường"
    assert dia_chi("Mường Kim", "BẢN CÁP NA 3") == "BẢN Cáp Na"
    # Xã cũ Tà Mung / Pha Mu cũng về Xã Mường Kim rồi mới đổi bản.
    assert dia_chi("Tà Mung", "Bản Nậm Pắt") == "Bản Tà Mung"
    assert dia_chi("Pha Mu", "Bản Chít") == "Bản Pha Mu"
    # Bản không sắp xếp giữ nguyên, "Chít" bên trong không bị đổi.
    assert dia_chi("Mường Kim", "Bản Hua Chít") == "Bản Hua Chít"
    assert dia_chi("Mường Kim", "Bản Pá Chít Tấu") == "Bản Pá Chít Tấu"
    assert dia_chi("Mường Kim", "Bản Mường, xã Mường Kim") == "Bản Mường, xã Mường Kim"


def test_village_rename_only_inside_its_ward():
    result = area_remap.remap_area({"tinh": "Bắc Ninh", "xa": "Trí Quả", "diaChi": "Thôn Thanh Bình"})
    assert result["xa"] == "Phường Trí Quả"
    assert result["diaChi"] == "Thôn Thanh Bình"


def test_quang_ninh_ten_trung_xa_phuong_theo_nhan():
    def xa(ten):
        return area_remap.remap_area({"tinh": "Tỉnh Quảng Ninh", "xa": ten, "diaChi": ""})["xa"]

    # Phường Hạ Long mới (NQ 1679 khoản 43) không bị nhầm với xã Hạ Long cũ của Vân Đồn.
    assert xa("Phường Hạ Long") == "Phường Hạ Long"
    assert xa("Hạ Long") == "Phường Hạ Long"
    assert xa("Xã Hạ Long") == "Đặc khu Vân Đồn"
    assert xa("Phường Hải Hòa") == "Phường Móng Cái 1"
    assert xa("Phường Bắc Sơn") == "Phường Vàng Danh"
    assert xa("Xã Bắc Sơn") == "Xã Hải Sơn"
    assert xa("Phường Thanh Sơn") == "Phường Uông Bí"
    assert xa("Xã Thanh Sơn") == "Xã Ba Chẽ"
    # Tên trần trùng ở hai đơn vị khác đích: không đoán.
    assert xa("Bắc Sơn") == "Bắc Sơn"


def test_quang_ninh_don_vi_nhap_truoc_2025():
    def xa(ten):
        return area_remap.remap_area({"tinh": "Quảng Ninh", "xa": ten, "diaChi": ""})["xa"]

    # NQ 837/NQ-UBTVQH14 (1/1/2020)
    assert xa("Xã Phú Hải") == "Xã Quảng Hà"
    assert xa("Quảng Thắng") == "Xã Quảng Hà"
    assert xa("Tình Húc") == "Xã Bình Liêu"
    assert xa("Thị trấn Trới") == "Phường Hoành Bồ"
    # NQ 1199/NQ-UBTVQH15 (1/11/2024)
    assert xa("Minh Cầm") == "Xã Lương Minh"
    assert xa("Tân Việt") == "Phường An Sinh"
    assert xa("Phường Hòa Lạc") == "Phường Móng Cái 1"
    assert xa("Yết Kiêu") == "Phường Hồng Gai"
    # Nhập vào đơn vị sau đó bị chia 2 nơi: để nguyên, cán bộ tự chọn.
    assert xa("Cẩm Hải") == "Cẩm Hải"
    assert xa("Điền Công") == "Điền Công"


def _viet_tat(tinh, xa="", quoc_gia="Việt Nam"):
    out = area_remap.remap_area({"quocGia": quoc_gia, "tinh": tinh, "xa": xa, "diaChi": "Số 1"})
    return out["tinh"], out["xa"]


def test_tinh_viet_tat_tren_don_doi_ra_ten_day_du():
    assert _viet_tat("KH") == ("Khánh Hòa", "")
    assert _viet_tat("Tỉnh KH") == ("Khánh Hòa", "")
    assert _viet_tat("K.Hòa") == ("Khánh Hòa", "")
    assert _viet_tat("LĐ") == ("Lâm Đồng", "")
    assert _viet_tat("Q.Ngãi") == ("Quảng Ngãi", "")
    assert _viet_tat("TT-Huế") == ("Huế", "")
    assert _viet_tat("TP.HCM") == ("Hồ Chí Minh", "")
    # Viết tắt tỉnh cũ đi qua bảng sáp nhập y như tên đầy đủ.
    assert _viet_tat("LA") == ("Tây Ninh", "")
    # "NT" là Ninh Thuận hay Nha Trang thì cũng về Khánh Hòa.
    assert _viet_tat("NT") == ("Khánh Hòa", "")
    # Tên đầy đủ không bị đụng.
    assert _viet_tat("Khánh Hòa") == ("Khánh Hòa", "")


def test_tinh_viet_tat_khong_xoa_xa_dung():
    assert _viet_tat("KH", "Phường Nha Trang") == ("Khánh Hòa", "Phường Nha Trang")
    assert _viet_tat("LĐ", "Phường Xuân Hương - Đà Lạt") == ("Lâm Đồng", "Phường Xuân Hương - Đà Lạt")


def test_tinh_viet_tat_mo_ho_lay_xa_lam_bang_chung():
    assert _viet_tat("QN", "Phường Hạ Long") == ("Quảng Ninh", "Phường Hạ Long")
    assert _viet_tat("HN", "Phường Ba Đình") == ("Hà Nội", "Phường Ba Đình")
    # "ĐL" là Đà Lạt chứ không phải Đắk Lắk khi xã thuộc Đà Lạt.
    assert _viet_tat("ĐL", "Phường Lâm Viên - Đà Lạt") == ("Lâm Đồng", "Phường Lâm Viên - Đà Lạt")
    # Không có xã để gỡ: giữ nguyên như cũ, không đoán.
    assert _viet_tat("QN") == ("QN", "")
    assert _viet_tat("HN") == ("HN", "")


def test_tinh_viet_tat_khong_ap_cho_dia_chi_nuoc_ngoai():
    assert _viet_tat("TQ", quoc_gia="Trung Quốc") == ("TQ", "")


def _dia_chi(tinh, xa, huyen=None, dia_chi="Thôn 1"):
    out = area_remap.remap_area({"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": dia_chi}, huyen_hint=huyen)
    return out["tinh"], out["xa"]


def test_tuyen_quang_ten_cu_khong_kem_huyen_trong_bang():
    # Bảng cũ ghi "Xã Bằng Cốc (huyện Hàm Yên)": giấy tờ ghi "Xã Bằng Cốc" không bao giờ khớp.
    assert _dia_chi("Tuyên Quang", "Xã Bằng Cốc") == ("Tuyên Quang", "Xã Hàm Yên")
    assert _dia_chi("Hà Giang", "Thị trấn Đồng Văn") == ("Tuyên Quang", "Xã Đồng Văn")
    assert _dia_chi("Hà Giang", "Pả Vi") == ("Tuyên Quang", "Xã Mèo Vạc")
    # Tả Lủng có ở cả Đồng Văn lẫn Mèo Vạc: cần huyện, thiếu thì để trống nhưng tỉnh phải là tỉnh mới.
    assert _dia_chi("Hà Giang", "Xã Tả Lủng") == ("Tuyên Quang", "")
    assert _dia_chi("Hà Giang", "Xã Tả Lủng", huyen="Mèo Vạc") == ("Tuyên Quang", "Xã Mèo Vạc")
    assert _dia_chi("Hà Giang", "Xã Tả Lủng", dia_chi="Thôn 1, huyện Đồng Văn") == ("Tuyên Quang", "Xã Đồng Văn")


def test_tuyen_quang_xa_chia_hai_noi():
    # NQ 1684: một phần → khoản trước, phần còn lại → khoản sau; chọn nơi nhận phần còn lại.
    assert _dia_chi("Tuyên Quang", "Xã Kim Phú") == ("Tuyên Quang", "Phường Minh Xuân")
    assert _dia_chi("Hà Giang", "Xã Yên Định") == ("Tuyên Quang", "Xã Ngọc Đường")
    assert _dia_chi("Hà Giang", "Phường Quang Trung") == ("Tuyên Quang", "Phường Hà Giang 2")
    # Một nơi giữ tên cũ thì vẫn chọn nơi đó.
    assert _dia_chi("Tuyên Quang", "Xã Thái Bình") == ("Tuyên Quang", "Xã Thái Bình")
    assert _dia_chi("Hà Giang", "Xã Việt Lâm") == ("Tuyên Quang", "Xã Việt Lâm")


def test_tuyen_quang_don_vi_nhap_2024():
    # NQ 1106/NQ-UBTVQH15 (1/9/2024): Hồng Lạc + Vân Sơn → xã Hồng Sơn.
    assert _dia_chi("Tuyên Quang", "Xã Hồng Lạc") == ("Tuyên Quang", "Xã Hồng Sơn")
    assert _dia_chi("Tuyên Quang", "Vân Sơn") == ("Tuyên Quang", "Xã Hồng Sơn")


def test_hung_yen_phuong_thi_tran_cu():
    # Bảng cũ ghi "An Tảo (phường)", "Như Quỳnh (thị trấn)": giấy tờ ghi kèm nhãn không khớp.
    assert _dia_chi("Hưng Yên", "Phường An Tảo") == ("Hưng Yên", "Phường Phố Hiến")
    assert _dia_chi("Hưng Yên", "Thị trấn Như Quỳnh") == ("Hưng Yên", "Xã Như Quỳnh")
    assert _dia_chi("Thái Bình", "Thị trấn Diêm Điền") == ("Hưng Yên", "Xã Thái Thuỵ")
    assert _dia_chi("Thái Bình", "Phường Kỳ Bá") == ("Hưng Yên", "Phường Trần Lãm")


def test_hung_yen_xa_chia_hai_noi():
    # NQ 1666 khoản 27/29: Đình Dù một phần vào Như Quỳnh, phần còn lại vào Đại Đồng.
    assert _dia_chi("Hưng Yên", "Xã Đình Dù") == ("Hưng Yên", "Xã Đại Đồng")
    assert _dia_chi("Hưng Yên", "Xã Ngọc Thanh") == ("Hưng Yên", "Phường Sơn Nam")
    # Lạc Đạo: nơi giữ tên cũ.
    assert _dia_chi("Hưng Yên", "Xã Lạc Đạo") == ("Hưng Yên", "Xã Lạc Đạo")


def test_hung_yen_thai_binh_don_vi_nhap_2024():
    # NQ 1248/NQ-UBTVQH15 (1/12/2024): Hồng Nam → Phương Nam → (2025) Tân Hưng.
    assert _dia_chi("Hưng Yên", "Xã Hồng Nam") == ("Hưng Yên", "Xã Tân Hưng")
    assert _dia_chi("Hưng Yên", "Xã Bình Kiều") == ("Hưng Yên", "Xã Khoái Châu")
    assert _dia_chi("Hưng Yên", "Phường Quang Trung") == ("Hưng Yên", "Phường Phố Hiến")
    # NQ 1201/NQ-UBTVQH15 (1/11/2024): Quỳnh Bảo → Trang Bảo Xá → (2025) Quỳnh An.
    assert _dia_chi("Thái Bình", "Xã Quỳnh Bảo") == ("Hưng Yên", "Xã Quỳnh An")
    # Đông Quang cũ (Đông Hưng) khác Đông Quang lập năm 2024 (Tiền Hải): cần huyện.
    assert _dia_chi("Thái Bình", "Xã Đông Quang", huyen="Đông Hưng") == ("Hưng Yên", "Xã Nam Đông Hưng")
    assert _dia_chi("Thái Bình", "Xã Đông Quang", huyen="Tiền Hải") == ("Hưng Yên", "Xã Đông Tiền Hải")
    assert _dia_chi("Thái Bình", "Xã Đông Quang") == ("Hưng Yên", "")


def test_tinh_moi_ten_cu_cua_tinh_cu_khac_theo_nhan():
    # Thị trấn Yên Phú (Bắc Mê, Hà Giang) khác xã Yên Phú (Hàm Yên, Tuyên Quang) hiện hành.
    assert _dia_chi("Tuyên Quang", "Thị trấn Yên Phú") == ("Tuyên Quang", "Xã Bắc Mê")
    assert _dia_chi("Tuyên Quang", "Xã Yên Phú") == ("Tuyên Quang", "Xã Yên Phú")
    assert _dia_chi("Tuyên Quang", "Thị trấn Vinh Quang") == ("Tuyên Quang", "Xã Hoàng Su Phì")
    assert _dia_chi("Hưng Yên", "Phường Tiền Phong") == ("Hưng Yên", "Phường Thái Bình")
    assert _dia_chi("Hưng Yên", "Xã Tiền Phong") == ("Hưng Yên", "Xã Hồng Quang")
    # Thái Hưng có ở Thái Thụy và Hưng Hà (Thái Bình cũ): không đoán, không trả tên cũ đã mất.
    assert _dia_chi("Hưng Yên", "Xã Thái Hưng") == ("Hưng Yên", "")
    # So có dấu: Việt Hùng (Vũ Thư) khác Việt Hưng (Văn Lâm).
    assert _dia_chi("Hưng Yên", "Việt Hùng") == ("Hưng Yên", "Xã Vạn Xuân")
    assert _dia_chi("Hưng Yên", "Việt Hưng") == ("Hưng Yên", "Xã Đại Đồng")


def test_tinh_moi_kem_huyen_cu_cua_tinh_cu_khac():
    assert _dia_chi("Hưng Yên", "Xã Minh Tân", huyen="Đông Hưng") == ("Hưng Yên", "Xã Tiên Hưng")
    assert _dia_chi("Tuyên Quang", "Xã Tân Thành", huyen="Bắc Quang") == ("Tuyên Quang", "Xã Tân Quang")
    # "Tân Hòa" là tên có thật của Thái Bình cũ: không bị sửa chính tả sang "Tân Học".
    assert _dia_chi("Hưng Yên", "Xã Tân Hòa", huyen="Hưng Hà") == ("Hưng Yên", "Xã Ngự Thiên")


def test_tinh_cu_ten_trung_khong_huyen_van_doi_tinh_moi():
    assert _dia_chi("Thái Bình", "Xã Minh Tân") == ("Hưng Yên", "")
