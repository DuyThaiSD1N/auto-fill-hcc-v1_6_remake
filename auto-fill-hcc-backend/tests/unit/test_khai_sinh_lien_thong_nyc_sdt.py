from app.pipelines.khai_sinh_lien_thong.process.mapper import enrich


def _fields(fields):
    return {field["name"]: field for field in enrich(fields)}


def _ho_so(**extra):
    base = [
        {"name": "Tk_HoTenCon", "value": "NGUYỄN TRẦN ĐĂN CHI"},
        {"name": "ThongTinBo_HoTen", "value": "NGUYỄN TRẦN ĐĂNG VINH"},
        {"name": "ThongTinBo_SoDinhDanh", "value": "068095003430"},
        {"name": "ThongTinMe_HoTen", "value": "TRẦN VŨ ĐAN THANH"},
        {"name": "ThongTinMe_SoDinhDanh", "value": "068195010524"},
    ]
    base += [{"name": name, "value": value} for name, value in extra.items()]
    return base


def test_gui_sdt_kem_ten_nguoi_yeu_cau_de_extension_so_khop():
    field = _fields(_ho_so(
        LienHe_SoDienThoai="0981828309",
        Tk_NguoiYeuCau_HoTen="Nguyễn Trần Đăng Vinh",
    ))["NycSdt"]

    assert field["comp"] == "sdt-nguoiyeucau"
    assert field["value"] == {"sdt": "0981828309", "ten": "NGUYỄN TRẦN ĐĂNG VINH"}


def test_so_dien_thoai_duoc_chuan_hoa_truoc_khi_gui():
    field = _fields(_ho_so(
        LienHe_SoDienThoai="98I8283O9",
        Tk_NguoiYeuCau_HoTen="NGUYỄN TRẦN ĐĂNG VINH",
    ))["NycSdt"]

    assert field["value"]["sdt"] == "0981828309"


def test_khong_gui_sdt_khi_to_khai_khong_co_nguoi_yeu_cau():
    assert "NycSdt" not in _fields(_ho_so(LienHe_SoDienThoai="0981828309"))


def test_khong_gui_sdt_khi_giay_to_khong_doc_duoc_so():
    assert "NycSdt" not in _fields(_ho_so(Tk_NguoiYeuCau_HoTen="NGUYỄN TRẦN ĐĂNG VINH"))
