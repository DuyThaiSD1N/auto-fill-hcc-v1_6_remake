"""Kết hôn — luật tách địa chỉ của lượt trích và các chuẩn hoá tất định của mapper cho địa chỉ, nơi cấp."""
from app.pipelines.ket_hon.process import base_prompt, mapper, prompt


def test_prompt_giu_cac_cau_tach_dia_chi():
    assert "dấu phẩy / gạch nối / xuống dòng" in base_prompt.BASE_PROMPT
    rules = prompt.EXTRA_RULES
    assert "tinh CHỈ chứa tên tỉnh / thành phố trực thuộc trung ương" in rules
    # Câu "cụm sát tỉnh là cấp huyện thì bỏ" của khối cũ làm trống ô xã khi thẻ in "số nhà, tên đường, <quận cũ nay là
    # tên phường>, <thành phố>" → không đưa lại.
    assert "ĐẾM TỪ CUỐI khi liệt kê không nhãn" not in rules
    assert "KHÔNG đưa tên xã / huyện / tỉnh vào chiTietDuoiXa" in rules


def test_dia_chi_hai_cap_co_xa_hien_hanh_thi_giu_ten_tren_giay():
    # "Tân Tiến" vừa là xã hiện hành của Tuyên Quang, vừa là tên một xã cũ đã nhập vào xã khác.
    two_level = {"_tach": "chi tiết: — | xã: Tân Tiến | huyện (bỏ): — | tỉnh: TQ", "quocGia": "Việt Nam",
                 "tinh": "TQ", "xa": "Tân Tiến", "diaChi": ""}
    assert mapper._area(two_level)["xa"] == "Xã Tân Tiến"
    # Giấy còn ghi huyện: địa chỉ cũ, vẫn quy đổi theo bảng sáp nhập như trước.
    old = {**two_level, "_tach": "chi tiết: — | xã: Tân Tiến | huyện (bỏ): Yên Sơn | tỉnh: Tuyên Quang"}
    assert mapper._area(old)["xa"] == mapper.remap_area({"quocGia": "Việt Nam", "tinh": "TQ", "xa": "Tân Tiến", "diaChi": ""})["xa"]


def test_noi_cap_viet_tat_tren_to_khai_ra_ten_co_quan_day_du():
    fields = [{"name": "ToKhaiNu_HoTen", "value": "LÊ THỊ HANH"}, {"name": "ToKhaiNu_SoDinhDanh", "value": "001185000007"},
              {"name": "ToKhaiNu_NoiCap", "value": "Cục CS QLHC về TTXH"}]
    out = {field["name"]: field["value"] for field in mapper.enrich(fields, {})}
    assert out["NoiCapDD_BenNu"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_tinh_viet_tat_bi_chep_vao_cho_huyen_van_la_dia_chi_hai_cap():
    area = {"_tach": "chi tiết: Thôn A | xã: Tân Tiến | huyện (bỏ): TQ | tỉnh: —", "quocGia": "Việt Nam", "tinh": "TQ",
            "xa": "Tân Tiến", "diaChi": "Thôn A"}
    assert mapper._area(area)["xa"] == "Xã Tân Tiến"


def test_o_tinh_lech_tinh_chep_tren_dong_tach_thi_theo_dong_tach():
    area = {"_tach": "chi tiết: — | xã: Yên Bình | huyện (bỏ): — | tỉnh: Lào Cai", "quocGia": "Việt Nam",
            "tinh": "Thành phố Hồ Chí Minh", "xa": "Yên Bình", "diaChi": ""}
    assert mapper._area(area)["tinh"] == "Lào Cai"
    # Dòng tách không ghi tỉnh (giấy chỉ ghi thành phố thuộc tỉnh): giữ tỉnh model suy ra.
    assert mapper._area({**area, "_tach": "chi tiết: — | xã: Yên Bình | huyện (bỏ): — | tỉnh: —", "tinh": "Lào Cai"})["tinh"] == "Lào Cai"


def test_ngay_cap_cua_tai_khoan_khong_hop_le_thi_giu_ngay_cap_tren_giay():
    fields = [{"name": "BenNu_HoTen", "value": "LÊ THỊ HANH"}, {"name": "BenNu_SoDinhDanh", "value": "001185000007"},
              {"name": "BenNu_NgaySinh", "value": "05/03/1985"}, {"name": "BenNu_NgayCap", "value": "10/05/2022"}]
    account = {"applicantFullname": "LÊ THỊ HANH", "applicantIdentityNumber": "001185000007", "applicantBirthday": "05/03/1985",
               "applicantGender": "2"}
    issued = lambda day: {f["name"]: f["value"] for f in mapper.enrich(fields, {"formContext": {**account, "applicantIdDate": day}})}["NgayCapDD_BenNu"]
    assert issued("05/03/1985") == "10/05/2022"   # trùng ngày sinh
    assert issued("01/01/2031") == "10/05/2022"   # ở tương lai
    assert issued("12/06/2023") == "12/06/2023"   # hợp lệ: tài khoản vẫn thắng như trước


def test_nguoi_viet_chua_doc_duoc_noi_cu_tru_van_chon_trong_nuoc():
    out = {f["name"]: f["value"] for f in mapper.enrich([{"name": "BenNu_HoTen", "value": "LÊ THỊ HANH"}], {})}
    assert out["NoiCuTru_BenNu"] == "1" and "NoiCuTru_BenNu_TrongNuoc" not in out
    assert "NoiCuTru_BenNam" not in out   # bên chưa có nhân thân thì không đụng


def test_o_tinh_ghi_ten_nuoc_thi_lay_cum_chep_nguyen_van():
    area = {"_tach": "chi tiết: Thôn A | xã: Tân Tiến | huyện (bỏ): TQ | tỉnh: —", "quocGia": "Việt Nam", "tinh": "Việt Nam",
            "xa": "Tân Tiến", "diaChi": "Thôn A"}
    out = mapper._area(area)
    assert out["tinh"] == "Tuyên Quang" and out["xa"] == "Xã Tân Tiến"


def test_ben_chi_co_van_ban_ly_hon_thi_nhan_chu_tai_khoan_trung_ten_duong_su():
    fields = [{"name": n, "comp": "x-input", "value": v} for n, v in {
        "BenNam_TinhTrangHonNhan": "3", "BenNam_BanAnLyHon_So": "01/2021/QĐST-HNGĐ",
        "BenNam_BanAnLyHon_DuongSu": "Lê Thị A; Trần Văn B"}.items()]
    account = {"applicantFullname": "TRẦN VĂN B", "applicantGender": "1", "applicantIdentityNumber": "001090000001",
               "applicantBirthday": "01/01/1990"}
    ui = lambda ctx: {f["name"]: f["value"] for f in mapper.enrich(fields, {"formContext": ctx})}
    out = ui(account)
    assert out["HoTenBenNam"] == "TRẦN VĂN B" and out["SoDinhDanh_BenNam"] == "001090000001"
    assert "TTHN_LyHonBenNam" in out
    named = [*fields, {"name": "BenNam_HoTen", "comp": "x-input", "value": "Trần Văn B"}]
    assert {f["name"]: f["value"] for f in mapper.enrich(named, {"formContext": account})}["SoDinhDanh_BenNam"] == "001090000001"
    # Chủ tài khoản không phải đương sự / khác giới → không nhận, khối bên đó vẫn bỏ như cũ.
    assert "HoTenBenNam" not in ui({**account, "applicantFullname": "TRẦN VĂN C"})
    assert "HoTenBenNam" not in ui({**account, "applicantGender": "2"})
