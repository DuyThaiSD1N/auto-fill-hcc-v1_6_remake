"""Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu thụ — hạ áp (Bộ Công Thương, 1.115377)."""

import base64

import fitz

from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.attach import planner
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process import mapper
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process import runner as process_runner
from app.process.schemas import FileItem
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process.prompt import EXTRA_RULES
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process.schema import (
    ALLOWED,
    PANEL_KEYS,
    UI_COMP_BY_NAME,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "thong-bao-phat-trien-nguon-dien-mat-troi-mai-nha"
_ACCOUNT = {"formContext": {"applicantFullname": "Nguyễn Văn An", "applicantIdentityNumber": "001090000001"}}


def _notice(**overrides):
    values = {
        "TB_DiaDanh": "Hà Nội",
        "TB_NgayLap": "05/09/2026",
        "TB_KinhGui": "UBND PHƯỜNG MẪU",
        "TB_Ten": "Nguyễn Văn An",
        "TB_SoDinhDanh": "001090000001",
        "TB_DiaChi": {
            "tinh": "Thành phố Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 1 phố Mẫu",
            "fullText": "Số 1 phố Mẫu, phường Hoàn Kiếm, thành phố Hà Nội",
        },
        "TB_DienThoai": "0900000001",
        "TB_MaKhachHang": "PA01 0000 0001",
        "TB_ViTriLapDat": "Trên mái nhà",
        "TB_KetCau": "Hệ khung, mái bê tông",
        "TB_ChieuCao": "9.5",
        "TB_DienTichMai": "80 m2",
        "TB_CongSuatPV": "10",
        "TB_LuuTru": "5",
        "TB_Inverter": "8",
        "TB_PhuongAn": "5.2",
        "TB_ThoiGianDuKien": "10/2026",
        "TB_TenCamKet": "nguyễn văn an",
        "TB_NguoiKy": "Nguyễn Văn An",
    }
    values.update(overrides)
    return values


def _cccd():
    return {
        "Cccd_HoTen": "NGUYỄN VĂN AN",
        "Cccd_SoDinhDanh": "001090000001",
        "Cccd_NgaySinh": "01/02/1990",
        "Cccd_NgayCap": "03/04/2022",
        "Cccd_NoiCuTru": {"tinh": "Thành phố Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 9 phố Khác"},
    }


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return {f["name"]: f for f in fields}, warnings


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.115377"
    assert link["url"].endswith("019f1695-894f-72b8-80a8-2fee368722be")
    assert link["needsAgencySelect"] is True and "selectSo" not in link
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    assert proc["hasAttachmentStep"] is True and proc["detect"]["textPriority"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    # Tên package trùng key để tra.
    assert planner.__name__.split(".")[2] == KEY.replace("-", "_")


def test_ca_nhan_dien_panel_ca_nhan_va_don_vi():
    fields, warnings = _run(_notice())
    assert fields["data[pn3][loaiDoiTuong]"]["value"] == "Cá nhân"
    assert fields["data[pn3][kinhGui]"]["value"] == "UBND PHƯỜNG MẪU"
    assert fields["data[pn3][fullname]"]["value"] == "NGUYỄN VĂN AN"
    assert fields["data[pn3][province]"]["value"] == "Hà Nội"
    assert fields["data[pn3][district1]"]["value"] == "Hoàn Kiếm"
    assert fields["data[pn3][address]"]["value"] == "Số 1 phố Mẫu"
    assert fields["data[pn3][phonenlh]"]["value"] == "0900000001"
    assert fields["data[pn3][maSoKhachHang]"]["value"] == "PA0100000001"
    assert fields["data[pn3][chieuCaoCongTrinh]"]["value"] == "9.5 m"
    assert fields["data[pn3][dienTichMai]"]["value"] == "80 m²"
    assert fields["data[pn3][tongCongSuatPV]"]["value"] == "10 kWp"
    assert fields["data[pn3][tongLuuTruDien]"]["value"] == "5 kWh"
    assert fields["data[pn3][tongCongSuatInverter]"]["value"] == "8 kW"
    assert fields["data[pn3][thoiGianDuKien]"]["value"] == "10/2026"
    assert fields["data[pn3][tenChuHoCamKet]"]["value"] == "Nguyễn Văn An"
    assert fields["data[pn3][chuhoky]"]["value"] == "Nguyễn Văn An"
    assert fields["data[pn3][tinhThanhPhoNopDon]"]["value"] == "Hà Nội"
    assert fields["data[pn3][ngayNopDon]"]["value"] == "05/09/2026"
    assert fields["data[noidungyeucaugiaiquyet]"]["value"].startswith("Thông báo phát triển nguồn điện mặt trời")
    assert not any(name.endswith("ToChuc]") for name in fields)
    assert not warnings


def test_phuong_an_dien_du_tick_dung_option():
    fields, _ = _run(_notice())
    box = fields["data[pn3][pa][]"]
    assert box["comp"] == "dom-checkbox" and box["value"] is True
    assert box["optionValue"] == "khongBan" and box["optionLabel"].startswith("5.2. Không bán")

    fields, _ = _run(_notice(TB_PhuongAn="Đồng ý bán sản lượng điện dư"))
    assert fields["data[pn3][pa][]"]["optionValue"] == "dongYBan"

    fields, warnings = _run(_notice(TB_PhuongAn=None))
    assert "data[pn3][pa][]" not in fields
    assert any("mục 5" in w for w in warnings)


def test_to_chuc_theo_ten_hoac_ma_so_doanh_nghiep():
    for overrides in (
        {"TB_Ten": "HỘ KINH DOANH CỬA HÀNG MẪU", "TB_SoDinhDanh": None},
        {"TB_Ten": "Mẫu Xanh", "TB_MaSoDoanhNghiep": "0100000001", "TB_SoDinhDanh": None},
    ):
        fields, _ = _run(_notice(**overrides), _ACCOUNT)
        assert fields["data[pn3][loaiDoiTuong]"]["value"] == "Tổ chức"
        assert fields["data[pn3][tenToChuc]"]["value"] == overrides["TB_Ten"]
        assert fields["data[pn3][provinceToChuc]"]["value"] == "Hà Nội"
        assert fields["data[pn3][dienThoaiToChuc]"]["value"] == "0900000001"
        assert fields["data[pn3][phuongAnXuLyDienDuToChuc][]"]["optionValue"] == "khongBan"
        assert fields["data[pn3][nguoiDaiDienToChucKy]"]["value"] == "Nguyễn Văn An"
        assert not any(name in fields for name, _ in PANEL_KEYS.values())
        # Tổ chức không bao giờ dùng ô tích "chủ hồ sơ = tài khoản" và phải xóa CCCD cổng điền sẵn.
        assert fields["data[isOwnerDossier]"]["value"] is False
        assert fields["data[ownerIdentityNumber]"]["value"] == ""
    assert fields["data[ownertaxCode]"]["value"] == "0100000001"


def test_ho_truong_khong_bi_nhan_nham_la_to_chuc():
    fields, _ = _run(_notice(TB_Ten="Trương Thị Mẫu"))
    assert fields["data[pn3][loaiDoiTuong]"]["value"] == "Cá nhân"


def test_chu_ho_so_trung_tai_khoan_thi_tich_de_cong_tu_chep():
    fields, _ = _run({**_notice(), **_cccd()}, _ACCOUNT)
    assert fields["data[isOwnerDossier]"]["value"] is True
    assert "data[ownerFullname]" not in fields
    assert fields["data[phoneNumber]"]["value"] == "0900000001"
    assert fields["data[identityDate]"]["value"] == "03/04/2022"
    assert fields["data[address]"]["value"] == "Số 9 phố Khác", "khối tài khoản theo nơi cư trú trên CCCD"
    assert fields["data[pn3][address]"]["value"] == "Số 1 phố Mẫu", "tờ khai theo địa chỉ trên Thông báo"


def test_chu_ho_so_khac_tai_khoan_thi_dien_tuong_minh():
    other = {"formContext": {"applicantFullname": "Lê Thị Bình", "applicantIdentityNumber": "001090000009"}}
    fields, warnings = _run({**_notice(), **_cccd()}, other)
    assert fields["data[isOwnerDossier]"]["value"] is False
    assert fields["data[ownerFullname]"]["value"] == "NGUYỄN VĂN AN"
    assert fields["data[ownerIdentityNumber]"]["value"] == "001090000001"
    assert fields["data[ownerPhoneNumber]"]["value"] == "0900000001"
    assert fields["data[ownerAddress]"]["value"].startswith("Số 1 phố Mẫu")
    assert "data[fullname]" not in fields and "data[phoneNumber]" not in fields
    assert any("không khớp tài khoản" in w for w in warnings)


def test_thong_so_lay_ban_ve_khi_thong_bao_bo_trong_va_canh_bao_khi_lech():
    values = _notice(TB_LuuTru=None, TB_Inverter="10", BanVe_LuuTru="5", BanVe_Inverter="8")
    fields, warnings = _run(values)
    assert fields["data[pn3][tongLuuTruDien]"] == {
        "name": "data[pn3][tongLuuTruDien]", "comp": "dom-input", "value": "5 kWh", "default": True,
    }
    assert fields["data[pn3][tongCongSuatInverter]"]["value"] == "10 kW"
    assert any("inverter" in w and "Bản vẽ" in w for w in warnings)


def test_canh_bao_chu_dau_tu_ban_ve_khac_nguoi_thong_bao():
    _, warnings = _run(_notice(BanVe_ChuDauTu="Hộ kinh doanh Cửa hàng Mẫu"))
    assert any("chủ đầu tư" in w for w in warnings)
    _, warnings = _run(_notice(BanVe_ChuDauTu="NGUYỄN VĂN AN"))
    assert not any("chủ đầu tư" in w for w in warnings)


def test_thieu_kinh_gui_va_vi_tri_thi_mac_dinh_co_danh_dau():
    fields, _ = _run(_notice(TB_KinhGui=None, TB_ViTriLapDat=None))
    assert fields["data[pn3][kinhGui]"]["value"] == "UBND Phường Hoàn Kiếm"
    assert fields["data[pn3][kinhGui]"]["default"] is True
    assert fields["data[pn3][viTriLapDat]"]["value"] == "Trên mái nhà"
    assert fields["data[pn3][viTriLapDat]"]["default"] is True


def test_moi_field_mapper_phat_deu_co_trong_ui_va_prompt_dung_field_hop_le():
    for values, options in ((_notice(), _ACCOUNT), ({**_notice(), **_cccd()}, _ACCOUNT),
                            (_notice(TB_Ten="Công ty TNHH Mẫu"), None)):
        fields, _ = _run(values, options)
        assert all(name in UI_COMP_BY_NAME for name in fields)
    for name in ("TB_PhuongAn", "TB_TenCamKet", "TB_NguoiKy", "BanVe_ChuDauTu"):
        assert name in ALLOWED and name in EXTRA_RULES


def test_dinh_kem_dinh_tuyen_theo_loai():
    files = [{"name": n} for n in (
        "thong bao.pdf", "ban ve.pdf", "gcn.pdf", "hinh anh.pdf", "co.pdf", "cccd.jpg", "bien nhan.pdf",
        "anh.xlsx", "la.pdf",
    )]
    llm = {
        0: {"docType": "thong_bao", "bundle": False},
        1: {"docType": "ban_ve", "bundle": False},
        2: {"docType": "tai_lieu_cong_trinh", "bundle": False},
        3: {"docType": "hinh_anh", "bundle": False},
        4: {"docType": "thiet_bi", "bundle": False},
        5: {"docType": "cccd", "bundle": False},
        6: {"docType": "ket_qua", "bundle": False},
        8: {"docType": "other", "bundle": False},
    }
    texts = {6: "GIẤY TIẾP NHẬN HỒ SƠ VÀ HẸN TRẢ KẾT QUẢ"}
    items, warnings, classified = planner.build_plan_items(files, texts, llm)
    by_file = {item["fileName"]: item for item in items}
    # Mọi tệp đều được đính, trừ bảng tính.
    assert set(by_file) == {f["name"] for f in files} - {"anh.xlsx"}

    main = "Thông báo theo Mẫu số 01 tại Phụ lục III"
    for name in ("thong bao.pdf", "hinh anh.pdf", "co.pdf", "cccd.jpg", "bien nhan.pdf", "la.pdf"):
        assert by_file[name]["target"] == "attp-row" and by_file[name]["componentName"] == main
    assert by_file["cccd.jpg"]["documentName"] == "Căn cước công dân"
    assert by_file["bien nhan.pdf"]["documentName"] == "Giấy tiếp nhận hồ sơ và hẹn trả kết quả"
    assert by_file["ban ve.pdf"]["target"] == "add-document-dialog"
    assert by_file["ban ve.pdf"]["componentName"] == "Bản vẽ thiết kế lắp đặt nguồn điện"
    assert by_file["gcn.pdf"]["loaiBan"] == "Bản sao"
    assert all(by_file[n]["fallbackComponentName"] == main for n in ("ban ve.pdf", "gcn.pdf"))
    assert by_file["la.pdf"]["documentName"] == "la.pdf"
    assert by_file["thong bao.pdf"]["documentName"] == "Thông báo phát triển điện mặt trời mái nhà"
    assert all(len(item["documentName"]) <= 50 for item in items)
    assert {c["fileName"] for c in classified if c.get("skipped")} == {"anh.xlsx"}
    assert any("bảng tính" in w for w in warnings)
    assert not any("Không tìm thấy" in w for w in warnings)


def test_dinh_kem_giay_co_quan_lap_dat_ten_theo_loai():
    files = [{"name": n} for n in ("a.pdf", "b.pdf", "c.pdf", "d.pdf")]
    texts = {
        0: "GIẤY TIẾP NHẬN HỒ SƠ VÀ HẸN TRẢ KẾT QUẢ Mã hồ sơ: H00.000-000000-0000001",
        1: "PHIẾU KIỂM SOÁT QUÁ TRÌNH GIẢI QUYẾT HỒ SƠ",
        2: "ỦY BAN NHÂN DÂN PHƯỜNG MẪU Số: 12/TB-UBND THÔNG BÁO về việc lắp đặt",
        3: "",
    }
    llm = {i: {"docType": "ket_qua", "bundle": False} for i in range(4)}
    items, _, _ = planner.build_plan_items(files, texts, llm)
    assert [item["documentName"] for item in items] == [
        "Giấy tiếp nhận hồ sơ và hẹn trả kết quả",
        "Phiếu kiểm soát quá trình giải quyết hồ sơ",
        "Thông báo của Ủy ban nhân dân",
        "d.pdf",
    ]
    assert all(item["target"] == "attp-row" for item in items)


def test_dinh_kem_rule_du_phong_khi_khong_co_llm():
    files = [{"name": n} for n in ("a.pdf", "b.pdf", "c.pdf", "d.pdf")]
    texts = {
        0: "THÔNG BÁO Phát triển nguồn điện mặt trời mái nhà tự sản xuất I. THÔNG TIN CHUNG",
        1: "UỶ BAN NHÂN DÂN PHƯỜNG MẪU Số: 12/TB-UBND về việc lắp đặt nguồn điện mặt trời mái nhà",
        2: "TÊN BẢN VẼ/ DRAWING NAME: MẶT BẰNG BỐ TRÍ TẤM PV",
        3: "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU NHÀ Ở",
    }
    items, warnings, _ = planner.build_plan_items(files, texts)
    # Thông báo UBND cũng nhắc tên thủ tục nhưng phải nhận là ket_qua, không phải Thông báo Mẫu 01.
    assert [item["detectedType"] for item in items] == ["thong_bao", "ket_qua", "ban_ve", "tai_lieu_cong_trinh"]
    assert not any("Không tìm thấy" in w for w in warnings)


def test_dinh_kem_canh_bao_thieu_giay_bat_buoc_va_tep_gop():
    items, warnings, _ = planner.build_plan_items(
        [{"name": "gop.pdf"}, {"name": "tb2.pdf"}],
        {},
        {0: {"docType": "thong_bao", "bundle": True}, 1: {"docType": "thong_bao", "bundle": False}},
    )
    assert [item["documentName"] for item in items] == [
        "Thông báo phát triển điện mặt trời mái nhà", "Thông báo phát triển điện mặt trời mái nhà 2",
    ]
    assert any("gộp nhiều loại" in w for w in warnings)
    assert any("nhiều bản Thông báo" in w for w in warnings)
    assert any("Bản vẽ thiết kế" in w for w in warnings)


def _pdf_data_url(pages: int) -> str:
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"Trang {i + 1}")
    raw = doc.tobytes()
    doc.close()
    return "data:application/pdf;base64," + base64.b64encode(raw).decode("ascii")


def _page_count(data_url: str) -> int:
    with fitz.open(stream=base64.b64decode(data_url.split(",", 1)[1]), filetype="pdf") as doc:
        return doc.page_count


async def test_tep_gop_nhieu_trang_chi_ocr_vai_trang_dau(monkeypatch):
    # Hồ sơ thật kèm tệp gộp ~50 trang: OCR cả tệp quá trần thời gian → cả lô OCR hỏng.
    long_pdf = _pdf_data_url(12)
    seen: dict[str, list[int]] = {}

    async def fake_compact_run(files_by_role, **_kwargs):
        seen["fill"] = [_page_count(f["dataUrl"]) for files in files_by_role.values() for f in files]
        return {"fields": [], "errors": []}

    async def fake_ocr(files, **_kwargs):
        seen["attach"] = [_page_count(f["dataUrl"]) for f in files]
        return [{"name": f["name"], "type": f["type"], "text": ""} for f in files]

    monkeypatch.setattr(process_runner.runner, "run", fake_compact_run)
    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)

    await process_runner.run({"doc": [{"name": "gop.pdf", "type": "application/pdf", "dataUrl": long_pdf}]}, {})
    out = await planner.plan([FileItem(name="gop.pdf", type="application/pdf", dataUrl=long_pdf, role="doc")])

    assert seen == {"fill": [4], "attach": [4]}
    # Kế hoạch đính kèm trỏ theo fileIndex → extension vẫn tải bản gốc đủ trang lên cổng.
    assert out["attachments"][0]["fileIndex"] == 0
