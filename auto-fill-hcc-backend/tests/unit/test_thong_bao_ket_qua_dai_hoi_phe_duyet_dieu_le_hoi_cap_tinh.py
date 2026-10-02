"""Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội (cấp tỉnh) — 1.012943.

Khoá: đăng ký đủ registry + ke_khai_links; mẫu khai điền đúng field-key; tích "Người nộp là chủ hồ sơ" giữ nguyên khi
không có CCCD người ký; bảng 7 dòng đính đúng (danh sách kèm tờ trình → dòng 1, báo cáo tổng kết đính tạm dòng 6, dòng
điều kiện bỏ tick); lược trang Báo cáo tổng kết trước khi gửi LLM.
"""

from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.attach import planner
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.process import mapper, runner
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, public_list

_KEY = "thong-bao-ket-qua-dai-hoi-phe-duyet-dieu-le-hoi-cap-tinh"


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _facts(**kw):
    return [{"name": k, "value": v} for k, v in kw.items()]


_BASE_FACTS = dict(
    TenHoi="Hội Cựu giáo chức thành phố Bình An",
    SoVanBan="12/TTr-CGCBA",
    NgayDaiHoi="17 và 18 tháng 9 năm 2026",
    LoaiDaiHoi="nhiệm kỳ",
    LanThu="Lần thứ I",
    NhiemKy="2026 – 2031",
    DiaDiem="Hội trường Khách sạn Hoa Sen, số 5 đường Lê Lợi, phường Minh An",
    NoiDung="QUYẾT NGHỊ\nI. Thông qua báo cáo tổng kết.\n\n4. Đại hội đã bầu Ban Chấp hành gồm 21 ủy viên.",
    NguoiKy_TMBCH="Trần Văn Bình",
    DanhMucHoSo=[
        "Tờ trình số 12/TTr-CGCBA",
        "Danh sách Ban Chấp hành nhiệm kỳ 2026-2031",
        "Nghị quyết Đại hội đại biểu lần thứ I",
        "Báo cáo tổng kết hoạt động nhiệm kỳ 2020-2026",
        "Biên bản bầu cử Ban chấp hành, Ban kiểm tra",
        "Căn cước công dân",
    ],
)


def test_registry_va_ke_khai_links_dung_key():
    entry = next(p for p in public_list() if p["key"] == _KEY)
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["label"].endswith("(cấp tỉnh)")
    assert get_pipeline(_KEY) is not None
    assert get_attach_pipeline(_KEY) is not None
    link = next(i for i in KE_KHAI_LINKS if i.get("key") == _KEY)
    assert link["code"] == "1.012943"


def test_mau_khai_dien_dung_field_key():
    fields, _ = mapper.enrich(_facts(**_BASE_FACTS), {"formContext": {"applicantFullname": "Lê Thị Hoa",
                                                                       "applicantIdentityNumber": "001090000123"}})
    v = _values(fields)
    assert v["data[TenHoi]"] == "Hội Cựu giáo chức thành phố Bình An"
    assert v["data[So]"] == "12/TTr-CGCBA"
    assert v["data[NgayTl]"] == "17/09/2026"
    assert v["data[DaiHoiTl]"] == "Đại hội nhiệm kỳ"
    assert v["data[NhiemKy]"] == "Lần thứ I, nhiệm kỳ 2026-2031"
    assert v["data[ToChucTai]"].startswith("Hội trường Khách sạn Hoa Sen")
    assert v["data[NoiDung]"].startswith("QUYẾT NGHỊ\nI. Thông qua")
    assert v["data[TM.BCH]"] == "Trần Văn Bình"
    # Tờ trình là chính mẫu khai, CCCD không phải giấy gửi kèm.
    assert v["data[HoSo][0][textField1]"] == "Danh sách Ban Chấp hành nhiệm kỳ 2026-2031"
    assert v["data[HoSo][0][textField2]"] == "Danh sách"
    assert v["data[HoSo][2][textField2]"] == "Báo cáo"
    assert v["data[HoSo][3][textField2]"] == "Biên bản"
    assert "data[HoSo][4][textField1]" not in v
    assert v["data[hoSoDinhKem][1][textField2]"] == "Bản chính"
    # Không có CCCD người ký → giữ tích, không phát Phần II; giới tính suy từ số định danh tài khoản.
    assert v["data[isOwnerDossierCheck]"] is True
    assert "data[ownerFullname]" not in v
    assert v["data[gender]"] == "Nam"


def test_cccd_nguoi_ky_khac_tai_khoan_thi_bo_tich_va_dien_phan_ii():
    facts = dict(_BASE_FACTS, ChuHoSo_HoTen="Trần Văn Bình", ChuHoSo_SoDinhDanh="049056000111",
                 ChuHoSo_NgayCap="01/07/2024", ChuHoSo_GioiTinh="Nam")
    fields, warnings = mapper.enrich(_facts(**facts), {"formContext": {"applicantFullname": "Lê Thị Hoa"}})
    v = _values(fields)
    assert v["data[isOwnerDossierCheck]"] is False
    assert v["data[ownerFullname]"] == "Trần Văn Bình"
    assert v["data[ownerIdentityNumber]"] == "049056000111"
    names = [f["name"] for f in fields]
    assert names.index("data[isOwnerDossierCheck]") < names.index("data[ownerFullname]")
    assert any("bỏ tích" in w for w in warnings)


def test_dai_hoi_bat_thuong_va_sai_lech_thanh_canh_bao():
    facts = dict(_BASE_FACTS, LoaiDaiHoi="Đại hội bất thường", SaiLech=["Nghị quyết ghi tháng 8, Tờ trình ghi tháng 9"])
    fields, warnings = mapper.enrich(_facts(**facts), {})
    assert _values(fields)["data[DaiHoiTl]"] == "Đại hội bất thường"
    assert any("tháng 8" in w for w in warnings)


def _pages(*texts):
    return {i: t for i, t in enumerate(texts, start=1)}


def _plan(types_by_range, texts):
    pages = _pages(*texts)
    raw_files = [{"name": "ho-so.pdf", "type": "application/pdf"}]
    file_meta = {0: {"pageCount": len(texts), "pageBoundariesAvailable": True}}
    raw = [{"fileIndex": 0, "pageFrom": a, "pageTo": b, "type": t, "documentName": ""} for a, b, t in types_by_range]
    segments = planner._validated_segments(raw, raw_files, file_meta, [])
    return planner.build_plan_items(raw_files, segments, file_meta, {0: pages})


_SAMPLE_TEXTS = (
    "HỘI CỰU GIÁO CHỨC CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM TỜ TRÌNH V/v báo cáo kết quả Đại hội Kính gửi Sở Nội vụ",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM DANH SÁCH BAN CHẤP HÀNH (Kèm theo tờ trình số 12 ngày 25 tháng 9)",
    "29. Ông Nguyễn Văn A, UVBCH",
    "NGHỊ QUYẾT Đại hội đại biểu lần thứ I QUYẾT NGHỊ",
    "BÁO CÁO TỔNG KẾT HOẠT ĐỘNG NHIỆM KỲ 2020-2026",
    "BÁO CÁO KINH PHÍ TỪ NĂM 2021 ĐẾN NĂM 2025",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BIÊN BẢN BẦU CỬ (BCH) (có danh sách kèm theo)",
    "HỘI CỰU GIÁO CHỨC DANH SÁCH BCH nhiệm kỳ 2026-2031",
    "BIÊN BẢN Trích họp BCH lần thứ nhất",
)


def test_bang_7_dong_dinh_dung_theo_anh_xa():
    attachments, classified, warnings = _plan(
        [(1, 1, "bao_cao_ket_qua"), (2, 3, "danh_sach"), (4, 4, "nghi_quyet_dai_hoi"), (5, 5, "bao_cao_tong_ket"),
         (6, 6, "other"), (7, 7, "bien_ban"), (8, 8, "danh_sach"), (9, 9, "bien_ban")],
        _SAMPLE_TEXTS,
    )
    rows = {a["componentIndex"]: a for a in attachments}
    assert sorted(rows) == [1, 3, 5, 6]
    assert [s["pageIndexes"] for s in rows[1]["sourceSegments"]] == [[0], [1, 2]]
    assert [s["pageIndexes"] for s in rows[3]["sourceSegments"]] == [[6], [7], [8]]
    # Trang báo cáo kinh phí không có quốc hiệu → nối vào Báo cáo tổng kết, cùng dòng 6.
    assert [s["pageIndexes"] for s in rows[6]["sourceSegments"]] == [[4, 5]]
    assert all(a["loaiBan"] == "Bản chính" and a["target"] == "attp-row" for a in attachments)
    assert set(attachments[0]["untickRows"]) == {planner._ROWS[i]["componentName"] for i in (2, 4, 7)}
    assert any("Chương trình hoạt động riêng" in w for w in warnings)
    assert any("Biên bản đại hội" in w for w in warnings)
    assert any("Điều lệ" in w for w in warnings)


def test_danh_sach_khong_kem_to_trinh_thi_vao_dong_3():
    attachments, _, _ = _plan([(1, 1, "danh_sach")], ("DANH SÁCH BAN KIỂM TRA nhiệm kỳ 2026-2031",))
    assert attachments[0]["componentIndex"] == 3


def test_khong_bo_sot_trang_khi_llm_khong_tra_gi():
    attachments, _, _ = _plan([], _SAMPLE_TEXTS)
    covered = [i for a in attachments for s in a["sourceSegments"] for i in (s["pageIndexes"] or range(9))]
    assert sorted(covered) == list(range(9))


def test_luoc_trang_bao_cao_tong_ket_giu_trang_tieu_de():
    text = "\n".join([
        "Trang 1/4", "TỜ TRÌNH V/v báo cáo kết quả Đại hội",
        "Trang 2/4", "BÁO CÁO TỔNG KẾT HOẠT ĐỘNG NHIỆM KỲ 2020-2026 " + "nội dung " * 200,
        "Trang 3/4", "2 lực, sức khỏe và tạo điều kiện để hoạt động ... nội dung bỏ",
        "Trang 4/4", "NGHỊ QUYẾT Đại hội QUYẾT NGHỊ I. Thông qua",
    ])
    out = runner.trim_bulky_pages([{"name": "a.pdf", "text": text}])[0]["text"]
    assert "BÁO CÁO TỔNG KẾT" in out
    assert "nội dung bỏ" not in out
    assert "QUYẾT NGHỊ I. Thông qua" in out
    assert "lược bớt" in out


def test_so_van_ban_thieu_phan_so_viet_tay_thi_canh_bao():
    _, warnings = mapper.enrich(_facts(**dict(_BASE_FACTS, SoVanBan="00/Tr-CGCBA")), {})
    assert any("Số văn bản" in w for w in warnings)
    _, warnings = mapper.enrich(_facts(**_BASE_FACTS), {})
    assert not any("Số văn bản" in w for w in warnings)


def test_cat_toan_van_quyet_nghi_tu_ocr_ke_ca_doan_cuoi():
    ocr = "\n".join([
        "Trang 1/2",
        "Căn cứ Nghị quyết số 5 của Ban chấp hành về việc tổ chức đại hội",
        "QUYẾT NGHỊ",
        "Không phải đoạn này (thiếu tiêu đề Nghị quyết đại hội).",
        "Trang 2/2",
        "NGHỊ QUYẾT",
        "Đại hội đại biểu Hội Cờ tướng tỉnh Bình An lần thứ III",
        "QUYẾT NGHỊ",
        "I. Thông qua báo cáo tổng kết nhiệm kỳ 2021-2026 với các nội dung trọng tâm sau. " + "x " * 60,
        "Trang 3/3",
        "2",
        "4. Đại hội đã bầu Ban Chấp hành gồm 21 Ủy viên.",
        "Nghị quyết này đã được 100% đại biểu tham dự Đại hội biểu quyết thông qua.",
        "T/M. BAN CHẤP HÀNH",
        "CHỦ TỊCH",
        "Trần Văn Bình",
    ])
    text = runner.extract_quyet_nghi(ocr)
    assert text.startswith("I. Thông qua báo cáo tổng kết")
    assert text.endswith("biểu quyết thông qua.")
    assert "Trang 3/3" not in text and "\n2\n" not in text
    assert "Trần Văn Bình" not in text
    assert runner.extract_quyet_nghi("QUYẾT NGHỊ\nngắn") is None
