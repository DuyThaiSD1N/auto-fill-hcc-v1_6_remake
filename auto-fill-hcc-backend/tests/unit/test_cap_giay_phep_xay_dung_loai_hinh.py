"""GPXD cấp mới — ô "Loại hình công trình" 7 lựa chọn: mapper điền đúng nhãn của cổng và khối ô của loại hình đơn kê
khai (theo tuyến, tượng đài, theo giai đoạn ×2, dự án); quy trình "công trình" để LLM chọn loại hình."""
from app.channels.handfree.procedure_registry import case_pipeline_options, get_procedure
from app.pipelines.cap_giay_phep_xay_dung.process import mapper


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped):
    return {f["name"]: (f["value"], f["comp"]) for f in mapped}


BASE = [_field("CongTrinh_Ten", "Công trình A"), _field("CongTrinh_Loai", "Công trình dân dụng"),
        _field("CongTrinh_Cap", "Cấp III"), _field("CongTrinh_CotXayDung", "+0,45 m"),
        _field("CongTrinh_KhoangLui", "3 m")]


def _enrich(branch, *extra, variant="cong_trinh"):
    fields = [*BASE, _field("CongTrinh_Nhanh", branch), *extra]
    out, _ = mapper.enrich(fields, {"constructionVariant": variant})
    return _values(out)


def test_theo_tuyen_dien_chieu_dai_va_tung_khu_vuc():
    got = _enrich("theo_tuyen", _field("CongTrinh_TongChieuDai", "1.250 m"), _field("CongTrinh_KhuVuc", [
        {"khuVuc": "Đoạn 1", "chieuDai": "500", "cotXayDung": "1,2", "chieuCaoTinhKhong": "4,5", "doSau": "1,5"},
        {"khuVuc": "Đoạn 2", "chieuDai": "750"},
        {"chieuDai": "10"},
    ]))
    assert got["data[loaiCongTrinh]"][0] == "Công trình theo tuyến trong đô thị"
    assert got["data[tenCongTrinhTheoTuyen]"][0] == "Công trình A"
    assert got["data[capCongTrinhTheoTuyen]"] == ("III", "dom-select")
    assert got["data[khuVucTheoTuyen][0][khuVucTheoTuyen1]"] == ("Đoạn 1", "dom-input")
    assert got["data[khuVucTheoTuyen][0][doSauTheoTuyen]"][0] == "1.5"
    assert got["data[khuVucTheoTuyen][1][chieuDaiTheoTuyen]"][0] == "750"
    # Dòng không có tên khu vực không tạo hàng Form.io vô danh; cột thiếu thì bỏ trống cho vòng bổ sung hỏi.
    assert "data[khuVucTheoTuyen][2][chieuDaiTheoTuyen]" not in got
    assert "data[khuVucTheoTuyen][1][doSauTheoTuyen]" not in got
    assert "data[tenCongTrinhKhongTheoTuyen]" not in got


def test_tuong_dai():
    got = _enrich("tuong_dai", _field("CongTrinh_DienTichXayDung", "120"), _field("CongTrinh_ChieuCao", "12 m"))
    assert got["data[loaiCongTrinh]"][0] == "Công trình tượng đài, tranh hoành tráng"
    assert got["data[dienTichXayDungTuongDai]"][0] == "120"
    assert got["data[chieuCaoCongTrinhTuongDai]"][0] == "12"
    assert got["data[khoangLuiTuongDai]"][0] == "3"


def test_theo_giai_doan_khong_theo_tuyen_dien_dong_giai_doan_dau():
    got = _enrich("giai_doan_khong_theo_tuyen", _field("CongTrinh_TongDienTichSan", "300"),
                  _field("CongTrinh_SoTang", "3"))
    assert got["data[loaiCongTrinh]"][0] == "Theo giai đoạn cho công trình không theo tuyến"
    assert got["data[tenCongTrinhGiaiDoanKhongTheoTuyen]"][0] == "Công trình A"
    row = "data[giaiDoanKhongTheoTuyen][0]"
    assert got[f"{row}[capCongTrinhGiaiDoanKhongTheoTuyen]"] == ("III", "dom-select")
    assert got[f"{row}[tongDienTichSanGiaiDoanKhongTheoTuyen]"][0] == "300"
    assert got[f"{row}[soTangCongTrinhGiaiDoanKhongTheoTuyen]"][0] == "3"


def test_theo_giai_doan_theo_tuyen_dung_nhan_cong_va_khu_vuc_long():
    got = _enrich("giai_doan_theo_tuyen", _field("CongTrinh_TongChieuDai", "800"),
                  _field("CongTrinh_KhuVuc", [{"khuVuc": "Đoạn A", "chieuDai": "800"}]))
    # Nhãn nguyên văn của cổng (chữ "trinh" thiếu dấu) để Choices.js lọc ra đúng lựa chọn.
    assert got["data[loaiCongTrinh]"][0] == "Theo giai đoạn cho công trinh theo tuyến trong đô thị"
    row = "data[giaiDoanTheoTuyen][0]"
    assert got[f"{row}[tongChieuDaiCongTrinhGiaiDoanTheoTuyen]"][0] == "800"
    assert got[f"{row}[khuVucTheoTuyen][0][khuVucGiaiDoanTheoTuyen]"] == ("Đoạn A", "dom-input")


def test_cap_cho_du_an():
    got = _enrich("du_an", _field("DuAn_Ten", "Dự án B"), _field("DuAn_SoQuyetDinh", "12/QĐ-UBND"),
                  _field("DuAn_CoQuanPheDuyet", "UBND xã X"), _field("DuAn_NgayPheDuyet", "05/03/2026"),
                  _field("CongTrinh_ThongTinChuYeu", "Nhà 3 tầng, diện tích sàn 300 m2"))
    assert got["data[loaiCongTrinh]"][0] == "Cấp cho dự án"
    assert got["data[tenDuAn]"][0] == "Dự án B"
    assert got["data[ngayPheDuyet]"] == ("05/03/2026", "dom-date")
    row = "data[danhSachCongTrinh][0]"
    assert got[f"{row}[tenCongTrinhDuAn]"][0] == "Công trình A"
    assert got[f"{row}[thongTinChuYeuDuAn]"][0] == "Nhà 3 tầng, diện tích sàn 300 m2"
    assert got[f"{row}[capCongTrinhDuAn]"] == ("III", "dom-select")


def test_quy_trinh_cong_trinh_ma_llm_khong_xac_dinh_thi_giu_khong_theo_tuyen():
    out, _ = mapper.enrich(BASE, {"constructionVariant": "cong_trinh"})
    got = _values(out)
    assert got["data[loaiCongTrinh]"][0] == "Công trình không theo tuyến, tín ngưỡng, tôn giáo"
    assert "data[tenCongTrinhKhongTheoTuyen]" in got


def test_quy_trinh_ep_khong_theo_tuyen_cua_thu_tuc_sua_chua_van_giu_nguyen():
    got = _enrich("theo_tuyen", variant="khong_theo_tuyen")
    assert got["data[loaiCongTrinh]"][0] == "Công trình không theo tuyến, tín ngưỡng, tôn giáo"


def _picked(label):
    return {"mae_dialog_options": {"process": {"current": label, "options": [label]}}}


def test_hop_thoai_chon_quy_trinh_cong_trinh_cua_gpxd_cap_moi_de_llm_chon_loai_hinh():
    proc = get_procedure("cap-giay-phep-xay-dung-moi-nha-o-rieng-le")
    conv = _picked("(10 ngày làm việc) Cấp giấy phép xây dựng mới đối với công trình cấp III, cấp IV")
    assert case_pipeline_options(proc, conv).get("constructionVariant") == "cong_trinh"
    conv = _picked("(7 ngày làm việc) Cấp giấy phép xây dựng mới đối với nhà ở riêng lẻ")
    assert case_pipeline_options(proc, conv).get("constructionVariant") == "nha_o_rieng_le"
    # Thủ tục sửa chữa, cải tạo: quy trình công trình cũng có ô Loại hình công trình → LLM chọn loại hình.
    repair = get_procedure("sua-chua-cai-tao-gpxd-nha-o-rieng-le")
    conv = _picked("Cấp giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV")
    assert case_pipeline_options(repair, conv).get("constructionVariant") == "cong_trinh"
    conv = _picked("Cấp giấy phép xây dựng sửa chữa, cải tạo đối với nhà ở riêng lẻ")
    assert case_pipeline_options(repair, conv).get("constructionVariant") == "nha_o_rieng_le"


def test_sua_chua_chi_chon_loai_hinh_co_tren_to_khai_cua_thu_tuc():
    branches = ("khong_theo_tuyen", "theo_tuyen", "tuong_dai", "nha_o_rieng_le")
    for branch, label in (("theo_tuyen", "Công trình theo tuyến trong đô thị"),
                          ("tuong_dai", "Công trình tượng đài, tranh hoành tráng"),
                          ("du_an", "Công trình không theo tuyến, tín ngưỡng, tôn giáo"),
                          ("giai_doan_theo_tuyen", "Công trình không theo tuyến, tín ngưỡng, tôn giáo")):
        out, _ = mapper.enrich([*BASE, _field("CongTrinh_Nhanh", branch)],
                               {"constructionVariant": "cong_trinh", "constructionBranches": branches})
        assert _values(out)["data[loaiCongTrinh]"][0] == label, branch


async def test_quy_trinh_cong_trinh_sua_chua_de_llm_chon_trong_4_loai_hinh(monkeypatch):
    from app.pipelines.sua_chua_cai_tao_gpxd import process as repair

    seen = []

    async def fake_run(files_by_role, options):
        seen.append(options)
        return {}

    monkeypatch.setattr(repair, "_cap_moi_run", fake_run)
    await repair.run_cong_trinh({}, {})
    await repair.run_cong_trinh({}, {"constructionVariant": "nha_o_rieng_le"})
    assert [o["constructionVariant"] for o in seen] == ["cong_trinh", "nha_o_rieng_le"]
    assert seen[0]["constructionBranches"] == ("khong_theo_tuyen", "theo_tuyen", "tuong_dai", "nha_o_rieng_le")
