"""Unit test pipeline "[Đà Nẵng] Đăng ký tài sản gắn liền với thửa đất đã được cấp GCN..." — mã 1.013995.

Mapper: chủ hồ sơ tổ chức (tên đầy đủ, mã DN, chọn "Tổ chức", bỏ tích), ô khoá theo tài khoản không phát,
giới tính/ngày cấp/nơi cấp chỉ từ CCCD khớp tài khoản, SĐT ưu tiên di động. Planner: PDF gộp "Đơn + GCN" tách
theo trang, văn bản thẩm định vào dòng 5, loại bản theo cổng. Dữ liệu đều là ví dụ bịa.
"""

from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn.attach import planner as P
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn.process import mapper
from app.pipelines.dang_ky_tai_san_gan_lien_thua_dat_da_cap_gcn.process.runner import find_submitter_card
from app.procedures import registry

KEY = "dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn"
NOP_ID = "001203098765"
CTX = {"formContext": {"applicantFullname": "Trần Văn Bình", "applicantIdentityNumber": NOP_ID}}


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _to_chuc(**extra):
    base = dict(
        ChuHoSo_LoaiChuThe="Tổ chức",
        ChuHoSo_HoTen="Công ty TNHH Thương mại - Dịch vụ và Sản xuất An Phú",
        ChuHoSo_SoDinhDanh="0401234567",
        ChuHoSo_DiaChi={"quocGia": "Việt Nam", "tinh": "TP Đà Nẵng", "xa": "P. Liên Chiểu",
                        "diaChi": "Lô A1, Đường số 5, KCN Hòa Khánh"},
        ChuHoSo_DienThoai="0236 3111 222 / 0905 123 456",
        ChuHoSo_Email="anphu@example.com",
        NoiDungBienDong="Đăng ký bổ sung nhà xưởng xây dựng mới",
        NguoiNop_HoTen="TRẦN VĂN BÌNH",
        NguoiNop_SoDinhDanh=NOP_ID,
        NguoiNop_GioiTinh="Nam",
        NguoiNop_NgayCap="01/07/2024",
        NguoiNop_NoiCap="Bộ Công an",
    )
    base.update(extra)
    return base


def _by(out):
    return {f["name"]: f["value"] for f in out}


def test_registry_khop_key_ke_khai_links():
    assert registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY)
    assert registry.get_attach_pipeline(KEY)


def test_chu_ho_so_to_chuc_nop_thay():
    out, warnings = mapper.enrich(_fields(**_to_chuc()), CTX)
    got = _by(out)
    assert got["data[chonDoiTuong]"] == "Tổ chức"
    assert got["data[isOwnerDossier]"] is False
    assert got["data[ownerFullname]"] == "Công ty TNHH Thương mại - Dịch vụ và Sản xuất An Phú"
    assert got["data[organization]"] == got["data[ownerFullname]"]
    assert got["data[taxCode]"] == "0401234567"
    # Liên hệ + địa chỉ trụ sở của chủ hồ sơ; SĐT ưu tiên di động.
    assert got["data[phoneNumber]"] == "0905123456"
    assert got["data[email]"] == "anphu@example.com"
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường Liên Chiểu"
    assert got["data[address]"] == "Lô A1, Đường số 5, KCN Hòa Khánh"
    # Nhân thân người nộp: chỉ ô không khoá, từ CCCD khớp tài khoản.
    assert got["data[gender]"] == "Nam"
    assert got["data[identityDate]"] == "01/07/2024"
    assert got["data[identityAgency]"]
    for locked in ("data[fullname]", "data[birthday]", "data[identityNumber]"):
        assert locked not in got
    # Câu khung của cổng + nội dung biến động.
    request = got["data[noidungyeucaugiaiquyet]"]
    assert request.startswith("ÔNG/BÀ: Công ty TNHH Thương mại - Dịch vụ và Sản xuất An Phú ĐỀ NGHỊ GIẢI QUYẾT")
    assert request.endswith("Nội dung biến động: Đăng ký bổ sung nhà xưởng xây dựng mới")
    assert any("dòng 8" in w for w in warnings)


def test_cccd_khong_khop_tai_khoan_thi_khong_dien_nhan_than_nguoi_nop():
    out, warnings = mapper.enrich(_fields(**_to_chuc(NguoiNop_SoDinhDanh="001190011111")), CTX)
    got = _by(out)
    for name in ("data[gender]", "data[identityDate]", "data[identityAgency]"):
        assert name not in got
    assert got["data[ownerFullname]"]
    assert any("không có CCCD khớp" in w for w in warnings)


def test_khong_co_tai_khoan_thi_khong_dien_nhan_than_nguoi_nop():
    got = _by(mapper.enrich(_fields(**_to_chuc()), {})[0])
    assert "data[gender]" not in got
    assert got["data[isOwnerDossier]"] is False  # tổ chức thì luôn bỏ tích


def test_ca_nhan_tu_nop_tich_chu_ho_so():
    values = _to_chuc(
        ChuHoSo_LoaiChuThe="Cá nhân",
        ChuHoSo_HoTen="TRẦN VĂN BÌNH",
        ChuHoSo_SoDinhDanh=NOP_ID,
        ChuHoSo_DienThoai="0905123456",
    )
    got = _by(mapper.enrich(_fields(**values), CTX)[0])
    assert got["data[chonDoiTuong]"] == "Cá nhân"
    assert got["data[isOwnerDossier]"] is True
    assert "data[organization]" not in got and "data[taxCode]" not in got


def test_dia_chi_cu_truoc_sap_nhap_remap_phuong_moi():
    values = _to_chuc(ChuHoSo_DiaChi={"quocGia": "Việt Nam", "tinh": "thành phố Đà Nẵng",
                                      "xa": "phường Hòa Khánh Bắc", "huyen": "quận Liên Chiểu",
                                      "diaChi": "Lô A1"})
    got = _by(mapper.enrich(_fields(**values), CTX)[0])
    assert got["data[district]"] == "Phường Liên Chiểu"


def test_neo_nguoi_nop_chi_nhan_trang_cccd():
    don = f"ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI\nNgười viết đơn: TRẦN VĂN BÌNH {NOP_ID}"
    cccd = f"CĂN CƯỚC\nSố định danh cá nhân: {NOP_ID}\nHọ, chữ đệm và tên khai sinh: TRẦN VĂN BÌNH"
    docs = [{"text": f"Trang 1/2\n{don}\nTrang 2/2\n{cccd}"}]
    idx, chunk = find_submitter_card(docs, "tran van binh", NOP_ID)
    assert idx == 1 and "CĂN CƯỚC" in chunk and "ĐƠN ĐĂNG KÝ" not in chunk
    assert find_submitter_card([{"text": don}], "tran van binh", NOP_ID) is None


# ---------------- Planner ----------------
_DON = "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\nMẫu số 18\n3. Giấy tờ ... (1) Giấy chứng nhận đã cấp"
_GCN_BIA = "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT QUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN LIỀN VỚI ĐẤT AB 123456"
_GCN_TRONG = "Thửa đất số: 7, tờ bản đồ số: 12\nIII. Sơ đồ thửa đất\nSố vào sổ cấp GCN: CT01234"
_THAM_DINH = (
    "V/v thông báo kết quả thẩm định báo cáo nghiên cứu khả thi đầu tư xây dựng\n"
    "Cơ quan có thẩm quyền cấp giấy phép xây dựng chịu trách nhiệm ..."
)


def _plan_files(files: list[list[tuple[str, str]]]):
    """files = [[(type LLM trả, ocr text trang), ...], ...] — mỗi file có header trang."""
    raw_files, meta, page_text, full, raw_segments = [], {}, {}, {}, []
    for fi, pages in enumerate(files):
        raw_files.append({"name": f"file{fi}.pdf", "type": "application/pdf"})
        meta[fi] = {"pageCount": len(pages), "pageBoundariesAvailable": True}
        page_text[fi] = {i + 1: text for i, (_, text) in enumerate(pages)}
        full[fi] = "\n".join(text for _, text in pages)
        raw_segments += [
            {"fileIndex": fi, "pageFrom": i + 1, "pageTo": i + 1, "type": t, "documentName": ""}
            for i, (t, _) in enumerate(pages)
        ]
    errors: list[str] = []
    segments = P._validated_segments(raw_segments, raw_files, meta, errors)
    return P.build_plan_items(raw_files, segments, meta, page_text, full)


def test_pdf_gop_don_gcn_tach_trang_va_gop_gcn_2_trang():
    attachments, classified, warnings = _plan_files([
        [("don_mau_18", _DON), ("gcn_da_cap", _GCN_BIA), ("gcn_da_cap", _GCN_TRONG)],
        [("ho_so_thiet_ke", _THAM_DINH), ("ho_so_thiet_ke", "trang 2 của văn bản thẩm định")],
    ])
    rows = [(a["fileIndex"], a["componentIndex"], (a.get("sourceSegments") or [{}])[0].get("pageIndexes"))
            for a in attachments]
    # Trang 1 → dòng 1; trang 2-3 gộp 1 file → dòng 2; file thẩm định nguyên file → dòng 5 (không tách).
    assert rows == [(0, 1, [0]), (0, 2, [1, 2]), (1, 5, None)]
    assert [a["loaiBan"] for a in attachments] == ["Bản chính", "Bản sao", "Bản sao"]
    assert all(a["target"] == "attp-row" for a in attachments)
    assert not any("Mẫu số 18" in w or "Giấy chứng nhận đã cấp (dòng 2" in w for w in warnings)
    assert any("Sơ đồ nhà ở" in w for w in warnings)


def test_cccd_bo_qua_va_rule_du_phong_khi_llm_tra_other():
    attachments, classified, _ = _plan_files([
        [("other", _DON), ("other", _GCN_BIA), ("other", _GCN_TRONG), ("other", _THAM_DINH),
         ("cccd", "CĂN CƯỚC CÔNG DÂN")],
    ])
    assert [(a["detectedType"], a["sourceSegments"][0]["pageIndexes"]) for a in attachments] == [
        ("don_mau_18", [0]), ("gcn_da_cap", [1, 2]), ("ho_so_thiet_ke", [3]),
    ]
    assert classified[-1]["target"] == "skip"


def test_rule_giay_phep_xay_dung_va_uy_quyen():
    assert P._rule_type("GIẤY PHÉP XÂY DỰNG Số: 12/GPXD") == "giay_to_148_149"
    assert P._rule_type("HỢP ĐỒNG ỦY QUYỀN\nBên được ủy quyền: ...") == "van_ban_dai_dien"
    assert P._rule_type("BẢN VẼ HOÀN CÔNG nhà xưởng") == "so_do_cong_trinh"


def test_component_name_dong_3_khong_trung_dong_4():
    row3 = P._ROWS["giay_to_148_149"]["componentName"].lower()
    row4_portal = (
        "(4) Sơ đồ nhà ở, công trình xây dựng, trừ trường hợp đã nộp một trong các loại giấy tờ quy định tại "
        "các Điều 148, Điều 149 của Luật Đất đai mà có sơ đồ phù hợp với hiện trạng nhà ở"
    ).lower()
    assert row3 not in row4_portal
