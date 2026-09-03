from app.pipelines.khai_sinh_lien_thong.process.mapper import enrich


def _values(fields):
    return {field["name"]: field["value"] for field in fields}


def test_ten_con_bo_me_chu_ho_duoc_viet_in_hoa():
    values = _values(enrich([
        {"name": "Gcs_HoTenCon", "value": "Nguyễn  văn Bé"},
        {"name": "CccdNam_HoTen", "value": "Phạm văn Bố"},
        {"name": "CccdNam_SoDinhDanh", "value": "012345678901"},
        {"name": "CccdNu_HoTen", "value": "Trần thị Mẹ"},
        {"name": "CccdNu_SoDinhDanh", "value": "098765432109"},
        {"name": "Ct01_ChuHoHoTen", "value": "Lê văn Chủ hộ"},
        {"name": "Ct01_ChuHoSoDinhDanh", "value": "011111111111"},
    ]))

    assert (values["Ho"], values["ChuDem"], values["Ten"]) == ("NGUYỄN", "VĂN", "BÉ")
    assert values["ChaHoTen"] == "PHẠM VĂN BỐ"
    assert (values["ChaHo"], values["ChaChuDem"], values["ChaTen"]) == ("PHẠM", "VĂN", "BỐ")
    assert (values["MeHo"], values["MeChuDem"], values["MeTen"]) == ("TRẦN", "THỊ", "MẸ")
    assert values["DkttChuHo"] == "LÊ VĂN CHỦ HỘ"
    assert values["NycQuanHe"]["chaTen"] == "PHẠM VĂN BỐ"
    assert values["NycQuanHe"]["meTen"] == "TRẦN THỊ MẸ"

