"""[Lai Châu] Giao đất, cho thuê đất (mã 1.115577).

Khóa theo file mapping "Mapping_GiaoDat_Buoc2_ThongTinNguoiNop" + ảnh ánh xạ đính kèm:
  - process: người đề nghị là TỔ CHỨC → "Đối tượng nộp" = Tổ chức, tên tổ chức + quyết định thành lập (Số/Ngày/Nơi cấp
    GCN/GP) + trụ sở + điện thoại từ Đơn Mẫu số 01; ô cá nhân chỉ từ thẻ CCCD người đi nộp, không thẻ thì giữ ô cổng;
    người đề nghị là CÁ NHÂN thì như thủ tục Lai Châu khác (thiếu thì xoá ô cổng đổ sẵn);
  - attach: bảng 9 dòng, Đơn + tài liệu gửi kèm chung dòng 1 (Đơn đứng đầu), quyết định dự án chung dòng 9, dòng 2–8
    không tick, CCCD vào "Giấy tờ khác", tệp quá 6 MB bị loại, tệp sát ngưỡng cảnh báo.

Dữ liệu trong test là PLACEHOLDER, không phải hồ sơ thật.
"""

import base64

from app.pipelines._shared import fold
from app.pipelines.giao_dat_cho_thue_dat_lai_chau.attach import planner
from app.pipelines.giao_dat_cho_thue_dat_lai_chau.process import mapper
from app.pipelines.giao_dat_cho_thue_dat_lai_chau.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "giao-dat-cho-thue-dat-lai-chau"
ORG = "Ban Quản lý dự án đầu tư xây dựng các công trình Mẫu tỉnh Lai Châu"


def _fields(fields: list[dict]) -> dict:
    return {item["name"]: item for item in fields}


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields if not item.get("clear")}


def _org_facts(**extra) -> list[dict]:
    """Hồ sơ như mẫu: Đơn của tổ chức, KHÔNG có thẻ CCCD người đi nộp."""
    base = {
        "Don_NguoiDeNghi": ORG,
        "Don_LoaiNguoiDeNghi": "Tổ chức",
        "Don_QdThanhLapSo": "123/QĐ-UBND",
        "Don_QdThanhLapNgay": "1/6/2016",
        "Don_QdThanhLapCoQuan": "UBND tỉnh Lai Châu",
        "Don_DiaChi": {"tinh": "tỉnh Lai Châu", "xa": "phường Mẫu", "chiTietDuoiXa": "Số 1, Đường Mẫu"},
        "Don_DienThoai": "02130.000.001",
        "Pd_ChuDauTu": "Ban Quản lý dự án khác",
    }
    base.update(extra)
    return [{"name": name, "value": value} for name, value in base.items() if value is not None]


CARD = {
    "Cccd_HoTen": "TRẦN VĂN MẪU", "Cccd_SoDinhDanh": "012000000001", "Cccd_NgaySinh": "3/4/1990",
    "Cccd_GioiTinh": "Nam", "Cccd_NgayCap": "05/06/2024", "Cccd_NoiCap": "BỘ CÔNG AN",
    "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Xã Mẫu Hai", "chiTietDuoiXa": "Thôn Mẫu"},
}


# ---------------------------------------------------------------- process/mapper


def test_mapper_to_chuc_khong_the_dien_o_to_chuc_giu_o_ca_nhan():
    fields, warnings = mapper.enrich(_org_facts())
    values = _values(fields)

    assert values["CongDan__select_1"] == "Tổ chức"
    assert values["CongDan_tenCoQuanToChuc"] == ORG
    # Quyết định thành lập = "GCN/GP" của đơn vị sự nghiệp (mapping STT 22–24).
    assert values["CongDan_soGCNGP"] == "123/QĐ-UBND"
    assert values["CongDan_ngayCapGCNGP"] == "01/06/2016"
    assert values["CongDan_noiCapGCNGP"] == "UBND tỉnh Lai Châu"
    # Nhóm địa chỉ theo TRỤ SỞ trên Đơn khi khai là tổ chức.
    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu"
    assert values["CongDan_maPhuongXa"] == "Phường Mẫu"
    assert values["CongDan_diaChi"] == "Số 1, Đường Mẫu"
    assert values["CongDan_diDong"] == "02130000001"
    # Không thẻ: ô cá nhân KHÔNG phát, KHÔNG xoá (người nộp = chủ tài khoản), chỉ nhắc kiểm tra.
    for name in ("CongDan_tenCongDan", "CongDan_ngaySinhCongDan", "CongDan_soCmnd", "CongDan_noiOHienTai"):
        assert name not in _fields(fields)
    assert not any(item.get("clear") for item in fields)
    assert any("Giới tính" in w and "Dân tộc" in w for w in warnings)


def test_mapper_to_chuc_co_the_nguoi_di_nop():
    fields, warnings = mapper.enrich(_org_facts(**CARD))
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "TRẦN VĂN MẪU"
    assert values["CongDan_ngaySinhCongDan"] == "03/04/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_soCmnd"] == values["CongDan_soCCCD"] == "012000000001"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"
    # Tỉnh/Xã/Số nhà vẫn theo trụ sở; nơi ở / thường trú là của CÁ NHÂN → theo thẻ, không lấy trụ sở.
    assert values["CongDan_diaChi"] == "Số 1, Đường Mẫu"
    assert values["CongDan_noiOHienTai"] == values["CongDan_diaChiThuongTru"] == "Thôn Mẫu, Xã Mẫu Hai, Tỉnh Lai Châu"
    assert warnings == []


def test_mapper_ten_to_chuc_du_phong_theo_chu_dau_tu_va_nhan_dien_to_chuc_theo_ten():
    values = _values(mapper.enrich(_org_facts(Don_NguoiDeNghi=None))[0])
    assert values["CongDan_tenCoQuanToChuc"] == "Ban Quản lý dự án khác"

    # LLM bỏ sót loại người đề nghị → nhận tổ chức theo tên.
    values = _values(mapper.enrich(_org_facts(Don_LoaiNguoiDeNghi=None))[0])
    assert values["CongDan__select_1"] == "Tổ chức"


def test_mapper_ca_nhan_xoa_o_thieu_va_khong_phat_o_to_chuc():
    facts = [{"name": k, "value": v} for k, v in {
        "Don_NguoiDeNghi": "Lê Thị Mẫu", "Don_LoaiNguoiDeNghi": "Cá nhân",
        "Don_DiaChi": {"tinh": "Lai Châu", "xa": "Xã Mẫu", "chiTietDuoiXa": "Bản Mẫu"},
        "Don_QdThanhLapSo": "999/QĐ-UBND",
    }.items()]
    fields, warnings = mapper.enrich(facts)
    values, by_name = _values(fields), _fields(fields)

    assert values["CongDan__select_1"] == "Cá nhân"
    assert values["CongDan_tenCongDan"] == "LÊ THỊ MẪU"
    assert values["CongDan_noiOHienTai"] == "Bản Mẫu, Xã Mẫu, Tỉnh Lai Châu"
    assert "CongDan_tenCoQuanToChuc" not in by_name and "CongDan_soGCNGP" not in by_name
    assert by_name["CongDan_ngaySinhCongDan"]["clear"] is True and by_name["CongDan_ngaySinhCongDan"]["markEmpty"]
    assert all(item["comp"] == "dom-input" for item in fields if item.get("clear"))
    assert any("Ngày sinh" in w for w in warnings)

    # Tài khoản chính là người đề nghị → giữ ô cổng.
    kept, _ = mapper.enrich(facts + [{"name": "Don_SoGiayTo", "value": "012000000009"}],
                            {"formContext": {"applicantIdentityNumber": "012000000009"}})
    assert not any(item.get("clear") for item in kept)


def test_schema_ui_va_o_khong_phat():
    fields, _ = mapper.enrich(_org_facts(**CARD))
    assert set(_fields(fields)) <= set(UI_COMP_BY_NAME)
    for name in ("CongDan_fax", "CongDan_website", "CongDan_maDMDiaChi", "CongDan_diaChiNuocNgoai",
                 "CongDan_maDMQuocGia"):
        assert name not in UI_COMP_BY_NAME
    assert UI_COMP_BY_NAME["CongDan__select_1"] == "dom-select"
    assert {"Don_NguoiDeNghi", "Don_QdThanhLapSo", "Pd_ChuDauTu", "Don_DiaChi"} <= ALLOWED


# ---------------------------------------------------------------- attach/planner

_TEXTS = {
    "don.pdf": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ GIAO ĐẤT\nKính gửi: Chủ tịch UBND phường Mẫu\n"
               "8. Theo Quyết định phê duyệt dự án đầu tư xây dựng\n13. Biểu tổng hợp diện tích, các quyết định thu hồi đất",
    "bien-ban.pdf": "BIÊN BẢN XÁC NHẬN CÔNG TÁC CHỈNH LÝ GCN QSD ĐẤT\nThực hiện Quyết định phê duyệt dự án đầu tư",
    "xac-nhan-1.pdf": "UBND THÀNH PHỐ\nV/v xác nhận đã hoàn thành công tác bồi thường, hỗ trợ, tái định cư công trình",
    "xac-nhan-2.pdf": "TT PHÁT TRIỂN QUỸ ĐẤT\nVề việc xác nhận đã hoàn thành công tác bồi thường, hỗ trợ (lần 2)",
    "bieu.pdf": "BẢNG TỔNG HỢP DIỆN TÍCH KHU ĐẤT\nPHỤC VỤ CÔNG TÁC XIN GIAO ĐẤT",
    "chu-truong.pdf": "QUYẾT ĐỊNH\nVề chủ trương đầu tư\nDự án Hồ chứa nước Mẫu",
    "phe-duyet.pdf": "QUYẾT ĐỊNH\nV/v Phê duyệt dự án đầu tư xây dựng\nCăn cứ Quyết định về chủ trương đầu tư",
    "thu-hoi.pdf": "QUYẾT ĐỊNH\nVề việc thu hồi đất để phát triển kinh tế - xã hội",
    "cccd.pdf": "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name:\nTRẦN VĂN MẪU",
    "anh-khac.jpg": "Biên lai thu phí",
}


def _files(names: list[str], sizes: dict | None = None) -> list[dict]:
    out = []
    for name in names:
        size = (sizes or {}).get(name)
        data = base64.b64encode(b"x" * size).decode() if size else "QQ=="
        out.append({"name": name, "type": "application/pdf", "dataUrl": f"data:application/pdf;base64,{data}"})
    return out


def _ocr(names: list[str]) -> list[dict]:
    return [{"name": name, "text": _TEXTS[name]} for name in names]


def test_bang_9_dong_tu_khoa_khong_chong_nhau():
    assert [slot["slotIndex"] for slot in planner.SLOTS] == list(range(9))
    assert planner.SLOTS[0]["slotName"].startswith("Mẫu số 01. Đơn đề nghị giao đất")
    assert planner.SLOTS[8]["slotName"].startswith("Văn bản phê duyệt dự án đầu tư")
    assert len({slot["slotKey"] for slot in planner.SLOTS}) == 9
    for slot in planner.SLOTS:
        for keyword in slot["slotKeywords"]:
            owners = [other["slotIndex"] for other in planner.SLOTS if keyword in fold(other["slotName"])]
            assert owners == [slot["slotIndex"]], keyword


def test_dinh_tuyen_ho_so_mau_dong_1_va_dong_9_theo_thu_tu_anh():
    # Thứ tự tải lên xáo trộn; dòng 1 vẫn Đơn đứng đầu rồi biên bản → xác nhận → biểu; dòng 9 chủ trương trước.
    names = ["phe-duyet.pdf", "bieu.pdf", "xac-nhan-2.pdf", "don.pdf", "xac-nhan-1.pdf", "bien-ban.pdf",
             "chu-truong.pdf", "cccd.pdf"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    slots = [(item["fileName"], item["slotIndex"]) for item in attachments if item["target"] == "fixed-slot"]
    # Hai văn bản xác nhận cùng loại → giữ thứ tự tải lên.
    assert slots == [
        ("don.pdf", 0), ("bien-ban.pdf", 0), ("xac-nhan-2.pdf", 0), ("xac-nhan-1.pdf", 0), ("bieu.pdf", 0),
        ("chu-truong.pdf", 8), ("phe-duyet.pdf", 8),
    ]
    assert all(item["tickRow"] for item in attachments if item["target"] == "fixed-slot")
    assert not any(1 <= item.get("slotIndex", -1) <= 7 for item in attachments)
    identity = [item for item in attachments if item["target"] == "new"]
    assert [item["componentName"] for item in identity] == ["Căn cước người nộp - Trần Văn Mẫu"]
    assert warnings == []


def test_quyet_dinh_thu_hoi_vao_dong_1_va_canh_bao_thieu_don():
    names = ["thu-hoi.pdf", "anh-khac.jpg"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _ocr(names), {})

    assert attachments[0]["slotIndex"] == 0 and attachments[0]["detectedType"] == "quyet_dinh_thu_hoi"
    assert attachments[1]["target"] == "new" and attachments[1]["componentName"] == "anh-khac"
    assert any("Giấy tờ khác" in w for w in warnings)
    assert any("Chưa thấy Đơn" in w for w in warnings)


def test_llm_thang_rule_llm_other_ve_rule_ocr_rong_theo_ten_tep():
    names = ["bieu.pdf", "phe-duyet.pdf"]
    attachments, _, classified = planner.build_plan_items(
        _files(names), _ocr(names), {0: "trich_do", 1: "other"}
    )
    assert [entry["source"] for entry in classified] == ["llm", "rule"]
    assert attachments[0]["detectedType"] == "trich_do" and attachments[1]["slotIndex"] == 8

    files = _files(["4Bieutonghopdientichkhudat_signed.pdf"])
    attachments, _, _ = planner.build_plan_items(files, [{"name": files[0]["name"], "text": ""}], {})
    assert attachments[0]["detectedType"] == "bieu_tong_hop" and attachments[0]["slotIndex"] == 0


def test_tep_qua_6mb_bi_loai_tep_sat_nguong_canh_bao():
    names = ["don.pdf", "bieu.pdf"]
    files = _files(names, {"don.pdf": 7 * 1024 * 1024, "bieu.pdf": 6_100_000})
    attachments, warnings, classified = planner.build_plan_items(files, _ocr(names), {})

    assert [item["fileName"] for item in attachments] == ["bieu.pdf"]
    assert classified[0]["skipped"] is True
    assert any("vượt giới hạn 6 MB" in w and "don.pdf" in w for w in warnings)
    assert any("sát giới hạn 6 MB" in w and "6.100.000" in w for w in warnings)


# ---------------------------------------------------------------- registry + trợ lý


def test_registry_va_ke_khai_links_cung_key():
    procedure = get_procedure(KEY)
    assert procedure["label"].startswith("[Lai Châu]")
    assert procedure["hasAttachmentStep"] is True and "6 MB" in procedure["uploadHint"]
    assert callable(get_pipeline(KEY)) and callable(get_attach_pipeline(KEY))

    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.115577" and link["needsAgencySelect"] is True
    assert link["label"].startswith("Lai Châu - ")
    assert not link.get("provinceOnlyAgency") and not link.get("selectSo")
    # Trang nộp in "1.115577 - <tên thủ tục>": đủ mọi cụm nhận diện; trang của 1.115578 thì không khớp.
    page = ("Một phần 1.115577 - Giao đất, cho thuê đất đối với trường hợp giao đất, cho thuê đất không đấu giá quyền sử "
            "dụng đất Nơi tiếp nhận hồ sơ")
    phrases = procedure["detect"]["textIncludes"]
    assert all(fold(p) in fold(page) for p in phrases)
    assert not all(fold(p) in fold(page.replace("1.115577", "1.115578")) for p in phrases)


def test_tro_ly_cung_key_va_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(KEY)
    assert procedure["provinceOnly"] == ["laichau"]
    assert procedure["laiChauFeeStep"] and procedure["agencyProvince"] == "Lai Châu"
    assert procedure["detect"] == get_procedure(KEY)["detect"]
    assert procedure["keKhaiUrl"] == next(item["url"] for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert get_procedure(KEY)["label"] == "[Lai Châu] " + procedure["label"]
    assert handfree.get_pipeline(KEY) is get_pipeline(KEY)
    assert handfree.get_attach_pipeline(KEY) is get_attach_pipeline(KEY)
    assert handfree.is_allowed_in_province(procedure, "laichau")
    assert not handfree.is_allowed_in_province(procedure, "bacninh")
    assert "Lai Châu" not in procedure["shortLabel"]
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "du_an"}
    assert PROCEDURE_HMONG[KEY] and PROCEDURE_HINTS[KEY]
