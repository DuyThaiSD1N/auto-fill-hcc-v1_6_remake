"""Liên thông khai tử (1.006714): mapper sang formcontrolname của cổng liên thông + đính kèm bước 04.

Kỳ vọng lấy theo mapping BA "126_Liên thông khai tử- Quảng ngãi". Dữ liệu dưới đây là hồ sơ GIẢ,
không dùng dữ liệu công dân trong bộ mẫu của BA.
"""

import json

from app.pipelines.khai_tu import process as khai_tu_process
from app.pipelines.khai_tu_lien_thong import attach as lien_thong_attach
from app.pipelines.khai_tu_lien_thong import process as lien_thong_process
from app.pipelines.khai_tu_lien_thong.attach import planner
from app.pipelines.khai_tu_lien_thong.process import mapper
from app.pipelines.khai_tu_lien_thong.process.schema import UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "khai-tu-lien-thong"

_DOSSIER = {
    "NguoiYeuCau_HoTen": "Trần Thị Mai",
    "NguoiYeuCau_SoDinhDanh": "001190000001",
    "NguoiYeuCau_NgayCap": "10/05/2021",
    "NguoiYeuCau_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiYeuCau_NoiCuTru": {"tinh": "Quảng Ngãi", "xa": "Nghĩa Lộ", "diaChi": "Tổ 1"},
    "ToKhai_QuanHeNguoiYeuCau": "Mẹ",
    # Ảnh thẻ CCCD của chính người yêu cầu — BA dòng 3-4 lấy ngày sinh + giới tính từ đây.
    "Cccd_HoTen": "Trần Thị Mai",
    "Cccd_SoDinhDanh": "001190000001",
    "Cccd_NgaySinh": "24/04/1994",
    "Cccd_GioiTinh": "Nữ",
    "Cccd_NgayCap": "10/05/2021",
    "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiMat_HoTen": "Lê Văn An",
    "NguoiMat_NgaySinh": "07/03/2019",
    "NguoiMat_GioiTinh": "Nam",
    "NguoiMat_DanToc": "kinh",
    "NguoiMat_QuocTich": "Việt Nam",
    "NguoiMat_SoDinhDanh": "001219000002",
    "NguoiMat_NgayCapGiayTo": "06/11/2024",
    "NguoiMat_NoiCapGiayTo": "Bộ Công an",
    "NguoiMat_NoiCuTruCuoiCung": {"tinh": "Tỉnh Quảng Ngãi", "xa": "Phường Nghĩa Lộ", "diaChi": "Tổ 1"},
    "NguoiMat_NgayMat": "01/08/2026",
    "NguoiMat_GioMat": "18:15",
    "NguoiMat_NguyenNhanMat": "Bị bệnh",
    "NguoiMat_NoiChet": {"tinh": "Quảng Ngãi", "xa": "Sơn Hạ", "diaChi": "Thôn 2"},
    "Gbt_So": "01",
    "Gbt_CoQuanCap": "UBND xã Sơn Hạ",
    "Gbt_NgayCap": "11/08/2026",
    "CopyRequest_WantsCopy": "Có",
    "CopyRequest_Quantity": "3",
}
_NOTICE_OCR = "ỦY BAN NHÂN DÂN\nXÃ SƠN HẠ\nSố: 01/UBND-GBT\nGIẤY BÁO TỬ\nHọ tên người chết: Lê Văn An"


def _enrich(values: dict, options: dict | None = None, ocr_text: str = "") -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options, ocr_text=ocr_text)


def _by_name(rows: list[dict]) -> dict:
    return {row["name"]: row for row in rows}


def test_khai_tu_lien_thong_registered_with_own_pipelines():
    procedure = get_procedure(KEY)
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert "CHƯA hỗ trợ" not in procedure["uploadHint"]
    assert get_pipeline(KEY) is lien_thong_process.run
    assert get_attach_pipeline(KEY) is lien_thong_attach.plan
    # Thủ tục khai tử trên cổng cũ giữ nguyên pipeline của nó.
    assert get_pipeline("khai-tu") is khai_tu_process.run


def test_khai_tu_lien_thong_ke_khai_link_matches_detect_url():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.006714"
    assert get_procedure(KEY)["detect"]["urlIncludes"][0] in link["url"]


def test_mapper_fills_deceased_block_with_portal_field_names():
    rows = _by_name(_enrich(_DOSSIER, {}, _NOTICE_OCR))
    values = {name: row["value"] for name, row in rows.items()}

    assert (values["NdktHo"], values["NdktChuDem"], values["NdktTen"]) == ("LÊ", "VĂN", "AN")
    assert values["NdktNgaySinh"] == "07/03/2019"
    assert values["NdktGioiTinh"] == "Nam"
    assert values["NdktSoGiayto"] == "001219000002"
    assert values["NdktNgayCapGiayTo"] == "06/11/2024"
    assert values["NdktNoiCapGiayTo"] == "Bộ Công an"
    assert values["NdktMaQuoctich"] == "Việt Nam"
    assert values["NdktMaDantoc"] == "Kinh"
    assert values["NctccDiaChi"] == {"tinh": "Quảng Ngãi", "xa": "Nghĩa Lộ", "diaChi": "Tổ 1"}
    assert rows["NctccLoaiCutru"]["default"] is True
    # BA dòng 31 đòi cả giờ phút → extension chọn định dạng "Ngày/Tháng/Năm giờ:phút".
    assert values["NctccNgayChet"] == "01/08/2026 18:15"
    assert values["NoichetDiachi"] == {"tinh": "Quảng Ngãi", "xa": "Sơn Hạ", "diaChi": "Thôn 2"}
    assert values["NguyenNhanChet"] == "Bị bệnh"
    assert values["GbtLoaiGiayto"] == "Giấy báo tử"
    assert values["GbtSogiayto"] == "01/UBND-GBT"
    assert values["GbtNgaycap"] == "11/08/2026"
    assert values["GbtNoicap"] == "UBND xã Sơn Hạ"
    assert values["CapBanSao"] == "1"
    assert values["BanSaoSoluong"] == "3"


def test_mapper_emits_only_fields_ba_says_to_fill():
    """BA: dòng có nguồn giấy tờ (hoặc có giá trị mặc định) thì điền; "Tự nhập" / "Không có trong
    giấy tờ đã cung cấp" thì để cán bộ tự làm."""
    rows = _enrich(_DOSSIER, {}, _NOTICE_OCR)
    names = [row["name"] for row in rows]

    def comp_hop_le(row):
        khai = UI_COMP_BY_NAME[row["name"]]
        return row["comp"] in khai if isinstance(khai, tuple) else row["comp"] == khai

    assert all(comp_hop_le(row) for row in rows)
    # Nhánh "Hưởng theo luật BHXH" BA đã bỏ khỏi phạm vi 2026-09-14.
    bhxh = ("IsChungTuBhxh", "NdktMasobhxh", "Cqmtp", "LoaiTroCap", "IsCqtc", "Bhxh", "MtpTien")
    assert not [n for n in names if n.startswith(bhxh)]
    khong_dien = {
        "NycSdt", "NycEmail",                                    # BA: Tự nhập
        "NoichetIsNoiCuTruCuoiCung", "GbtIsKhongCap",            # BA: Tự chọn, mẫu "Không tick"
        "XoaChuhoIsNguoiDuocKhaiTu", "XoaChuhoIsNyc",            # chủ hộ là dữ kiện hộ khẩu
        "NnmtpSdt", "NnmtpQqDiaChi", "MtpTienHinhthuc",
        "DtBtxh", "LdtbxhThoigianMaitang", "BtxhNmtDiaChi",      # cần chứng từ mai táng
        "NccDoiTuong", "NccQdinhSo", "NccQdinhNgay", "NccQdinhDonvi", "NccTyleThuongtat", "NccQqDiaChi",
    }
    assert not (set(names) & khong_dien)
    # Radio bản sao phải đi trước ô số lượng để Angular kịp hiện ô.
    assert names.index("CapBanSao") < names.index("BanSaoSoluong")


def test_requester_block_is_never_overwritten():
    """Cổng đã đổ khối người yêu cầu từ tài khoản đăng nhập (CSDL dân cư): chính xác hơn OCR và có
    thể lệch dấu so với giấy tờ (mẫu BA: tờ khai "Thủy" ↔ giấy báo tử "Thùy"). Chỉ chọn quan hệ."""
    names = [row["name"] for row in _enrich(_DOSSIER, {}, _NOTICE_OCR)]
    assert [n for n in names if n.startswith("Nyc")] == ["NycQuanHe"]
    # Danh tính người nhận mai táng phí cũng không gõ lại từ OCR.
    assert not [n for n in names if n.startswith("Canhan") and n != "CanhanIsNyc"]


def test_household_head_copies_from_requester_block_and_infers_relation():
    """BA dòng 47-49. Hai ô đầu lấy giá trị người yêu cầu; quan hệ suy ngược từ tờ khai."""
    rows = _by_name(_enrich(_DOSSIER, {}))
    assert rows["XoaChuhoHoten"]["comp"] == "sao-tu-o"
    assert rows["XoaChuhoHoten"]["value"] == {"tu": "NycHoTen"}
    assert rows["XoaChuhoGiayto"]["value"] == {"tu": "NycSoGiayto"}
    # Tờ khai: mẹ khai cho con → người được khai tử là "Con" của chủ hộ.
    assert rows["XoaChuhoQuanhe"]["value"] == "Con"
    assert all(rows[ten]["default"] is True for ten in ("XoaChuhoHoten", "XoaChuhoGiayto", "XoaChuhoQuanhe"))


def test_allowance_recipient_uses_the_portal_checkbox():
    """BA không bảo tick, nhưng tick là cách cổng tự chuyển danh tính người nhận (chính xác hơn OCR).
    Đánh dấu vàng để cán bộ bỏ tick khi người nhận là người khác."""
    rows = _by_name(_enrich(_DOSSIER, {}))
    assert rows["CanhanIsNyc"]["comp"] == "checkbox"
    assert rows["CanhanIsNyc"]["value"] is True and rows["CanhanIsNyc"]["default"] is True
    assert rows["NnmtpQuanheNguoichet"]["value"] == "Mẹ"
    assert rows["NnmtpQqMaQuocgia"]["value"] == "Việt Nam"
    assert rows["NccQqMaQuocgia"]["value"] == "Việt Nam"


def test_inverse_relation_uses_portal_catalog_labels():
    """Nhãn phải nằm trong danh mục của cổng; không chắc thì bỏ trống chứ không đoán."""
    assert mapper._quan_he_nguoc("Mẹ", "Nam") == "Con"
    assert mapper._quan_he_nguoc("Cha đẻ", "Nữ") == "Con"
    assert mapper._quan_he_nguoc("Vợ", "") == "Chồng"
    assert mapper._quan_he_nguoc("Chồng", "") == "Vợ"
    assert mapper._quan_he_nguoc("Con", "Nam") == "Cha"
    assert mapper._quan_he_nguoc("Con", "Nữ") == "Mẹ"
    assert mapper._quan_he_nguoc("Cháu", "Nam") == "Ông"
    assert mapper._quan_he_nguoc("Anh", "") == "Em"
    assert mapper._quan_he_nguoc("Em", "Nữ") == "Chị"
    # Thiếu giới tính người chết ở nhóm cần giới tính, hoặc quan hệ lạ → bỏ trống.
    assert mapper._quan_he_nguoc("Con", "") == ""
    assert mapper._quan_he_nguoc("Bạn", "Nam") == ""
    assert mapper._quan_he_nguoc("", "Nam") == ""


def test_death_notice_number_recovers_full_serial_from_ocr():
    assert mapper._death_notice_number("01", "Số: 01/UBND-GBT") == "01/UBND-GBT"
    assert mapper._death_notice_number("1", "SỐ 01 / UBND-GBT.") == "01/UBND-GBT"
    assert mapper._death_notice_number("01", "Số: 01/TLKT-BS") == "01"
    assert mapper._death_notice_number("5", "Số: 12/UBND-GBT") == "5"
    assert mapper._death_notice_number("07/GBT", "Số: 07/UBND-GBT") == "07/GBT"


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


_DECLARATION_OCR = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI ĐĂNG KÝ KHAI TỬ\n"
    "Số Giấy báo tử/Giấy tờ thay thế Giấy báo tử: ..."
)
_IDENTITY_OCR = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001190000001\nHọ và tên / Full name: TRẦN THỊ MAI"


def _fake_ocr(texts: list[str]):
    async def fake_ocr_per_file(files):
        assert len(files) == len(texts)
        return [{"name": f["name"], "text": text} for f, text in zip(files, texts)]
    return fake_ocr_per_file


async def test_attach_puts_notice_then_declaration_on_row_1_without_llm(monkeypatch):
    async def fail_chat(*_args, **_kwargs):
        raise AssertionError("tiêu đề chuẩn không được tốn lượt gọi LLM")

    monkeypatch.setattr(planner.ocr, "ocr_per_file", _fake_ocr([_DECLARATION_OCR, _IDENTITY_OCR, _NOTICE_OCR]))
    monkeypatch.setattr(planner.client, "chat", fail_chat)

    result = await planner.plan([_file("image.pdf"), _file("image.pdf"), _file("image.pdf")], {}, {})

    assert result["errors"] == []
    assert [item["fileIndex"] for item in result["attachments"]] == [2, 0]
    assert {item["slotIndex"] for item in result["attachments"]} == {0}
    assert all(item["repeatUpload"] and item["target"] == "fixed-slot" for item in result["attachments"])
    assert [item["documentName"] for item in result["attachments"]] == ["Giấy báo tử", "Tờ khai đăng ký khai tử"]
    classified = [row["docType"] for row in result["extracted"]["classified"]]
    assert classified == ["paper_declaration", "identity", "death_notice"]


async def test_attach_scanned_declaration_with_notice_page_counts_as_notice(monkeypatch):
    combined = _DECLARATION_OCR + "\n--- Trang 2/2 ---\n" + _NOTICE_OCR
    monkeypatch.setattr(planner.ocr, "ocr_per_file", _fake_ocr([combined]))

    result = await planner.plan([_file("ho_so.pdf")], {}, {})

    assert result["errors"] == []
    assert result["attachments"][0]["slotIndex"] == 0
    assert result["attachments"][0]["documentName"] == "Giấy báo tử"


async def test_attach_uses_row_2_when_llm_finds_proof_and_no_notice(monkeypatch):
    calls = []

    async def fake_chat(messages, **_kwargs):
        calls.append(messages)
        prompt = messages[1]["content"]
        assert "Ảnh bia mộ" in prompt and "TỜ KHAI" not in prompt  # chỉ gửi tài liệu chưa nhận ra
        return json.dumps({"documents": [{"index": 1, "docType": "death_event_proof"}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", _fake_ocr([_DECLARATION_OCR, "Ảnh bia mộ, mất năm 1990"]))
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan([_file("to_khai.pdf"), _file("bia_mo.jpg")], {}, {})

    assert len(calls) == 1
    assert [(item["fileIndex"], item["slotIndex"]) for item in result["attachments"]] == [(1, 1), (0, 1)]
    assert result["errors"] == []


async def test_attach_does_not_trust_a_mere_mention_of_giay_bao_tu(monkeypatch):
    """Ảnh chụp màn hình cổng có chữ "GIẤY BÁO TỬ THY.pdf" trong danh sách tệp, không phải giấy báo tử."""
    screenshot = (
        "DỊCH VỤ CÔNG LIÊN THÔNG ĐĂNG KÝ KHAI TỬ, XÓA ĐĂNG KÝ THƯỜNG TRÚ\n"
        "Trợ lý hồ sơ HCC\nGIẤY BÁO TỬ THY.pdf\nTK THY.pdf\nQuét và nhập dữ liệu"
    )
    calls = []

    async def fake_chat(messages, **_kwargs):
        calls.append(messages)
        return json.dumps({"documents": [{"index": 1, "docType": "other"}]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", _fake_ocr([_NOTICE_OCR, screenshot]))
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan([_file("gbt.pdf"), _file("anh_man_hinh.png")], {}, {})

    assert len(calls) == 1, "tài liệu chưa chắc phải đưa LLM quyết, không tự nhận là giấy báo tử"
    assert [item["fileIndex"] for item in result["attachments"]] == [0]
    assert result["extracted"]["skipped"] == ["anh_man_hinh.png"]


def test_rule_accepts_notice_title_merged_into_one_line():
    merged = "ỦY BAN NHÂN DÂN XÃ A Số: 01/UBND-GBT GIẤY BÁO TỬ Họ tên người chết: Nguyễn Văn B"
    assert planner._rule_type(merged) == planner._DOC_DEATH_NOTICE


async def test_attach_reports_missing_notice_and_skips_identity(monkeypatch):
    monkeypatch.setattr(planner.ocr, "ocr_per_file", _fake_ocr([_IDENTITY_OCR]))

    result = await planner.plan([_file("cccd.pdf")], {}, {})

    assert result["attachments"] == []
    assert result["extracted"]["skipped"] == ["cccd.pdf"]
    assert any("Không tìm thấy Giấy báo tử" in error for error in result["errors"])
