"""Cấp hộ chiếu phổ thông ở trong nước 1.001456 (Cổng DVC Bộ Công an): mapper ô form + đính kèm + nối registry / link
kê khai + trợ lý người dân."""
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process import mapper
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.schema import (
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    DE_NGHI_HET_HAN,
    DE_NGHI_KHAC,
    DE_NGHI_LAN_DAU,
    DE_NGHI_MAT,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "cap-ho-chieu-pho-thong-o-trong-nuoc"
# Hồ sơ mẫu bịa cùng khuôn bộ mẫu: người thành niên tự nộp, hộ chiếu cũ cấp trước sáp nhập tỉnh (nơi sinh tỉnh cũ),
# tờ khai đề nghị khác "đổi từ CMND sang căn cước", cha mẹ chỉ ghi năm sinh.
HO_SO = {
    "ToKhai_Ho": "TRẦN", "ToKhai_ChuDemTen": "VĂN AN", "ToKhai_GioiTinh": "Nam", "ToKhai_NgaySinh": "02/03/1985",
    "ToKhai_NoiSinh": "Hưng Yên", "ToKhai_SoDinhDanh": "0340 8500 0001", "ToKhai_NgayCap": "10/06/2021",
    "ToKhai_DienThoai": "0912.345.678",
    "ToKhai_ThuongTru": {"tinh": "Tỉnh Lai Châu", "xa": "Phường Đoàn Kết", "chiTietDuoiXa": "Tổ dân phố số 2"},
    "ToKhai_TamTru": {"tinh": "Lạng Sơn", "xa": "Phường Kỳ Lừa", "chiTietDuoiXa": "Số 10 Tổ 1, Khối 2"},
    "ToKhai_NgheNghiep": "Tự do", "ToKhai_Cha_NgaySinh": "1950", "ToKhai_Me_NgaySinh": "năm 1952",
    "ToKhai_VoChong_HoTen": "NGUYỄN THỊ BÌNH", "ToKhai_VoChong_NgaySinh": "1990",
    "ToKhai_HoChieuCu_So": "C1234567", "ToKhai_HoChieuCu_NgayCap": "01/02/2019",
    "ToKhai_NoiDungDeNghi": "Đề nghị khác. . Thay đổi từ CMND sang Căn cước",
    "ToKhai_DiaChiNhanHoChieu": "Phòng Quản lý XNC-Công an tỉnh Lai Châu",
    "ToKhai_DonViTiepNhan": "Phòng Quản lý XNC-Công an tỉnh Lai Châu",
    "HoChieu_So": "C1234567", "HoChieu_HoTen": "TRẦN VĂN AN", "HoChieu_NoiSinh": "THÁI BÌNH",
    "HoChieu_NgayCap": "01/02/2019", "HoChieu_NgayHetHan": "01/02/2029", "HoChieu_NoiCap": "Cục Quản lý xuất nhập cảnh",
}


def _enrich(values: dict):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {})


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_dien_dung_mapping_bo_mau():
    out, warnings = _enrich(HO_SO)
    assert _by(out) == {
        "CongDan__fsBCAHoCongDan": "TRẦN",
        "CongDan__fsBCAChuDemTen": "VĂN AN",
        "CongDan__fs_BCANoiKhaiSinhCD": "Hưng Yên",  # hộ chiếu ghi tỉnh cũ "THÁI BÌNH" → tỉnh sau sắp xếp
        "CongDan__fs_BCANgayCapCCCD": "10/06/2021",
        "CongDan__fs_BCANoiCapCCCD": "Cục CS QLHC về TTXH",  # CCCD 12 số cấp 2021 → suy theo ngày cấp
        "CongDan_diDong": "0912345678",
        "CongDan__fs_BCAQueQuanMaTinh": "Tỉnh Lai Châu",
        "CongDan__fs_BCAQueQuanMaQH": "Phường Đoàn Kết",
        "CongDan__fs_BCAQueQuanChiTiet": "Tổ dân phố số 2",
        "CongDan__fs_BCANoiOHienTaiMaTinh": "Tỉnh Lạng Sơn",
        "CongDan__fs_BCANoiOHienTaiMaQH": "Phường Kỳ Lừa",
        "CongDan__fs_BCADiaChiThuongTruCD": "Số 10 Tổ 1, Khối 2",
        "CongDan__fs_BCANgheNghiepCD": "Tự do",
        "CongDan__fs_BCANgaySinhChaCD": "1950",
        "CongDan__fs_BCANgaySinhMeCD": "1952",
        "CongDan__fsBCAHoVaTenVoChong": "NGUYỄN THỊ BÌNH",
        "CongDan__fs_BCANgaySinhVoChong": "1990",
        "CongDan__fs_BCAHoChieuPT": "C1234567",
        "CongDan__fs_BCANgayCapHoChieuPT": "01/02/2019",
        "CongDan__fs_BCANoiCapHCGanNhat": "Cục Quản lý xuất nhập cảnh",
        "CongDan__fs_BCANoiDungDeNghi": DE_NGHI_KHAC,
        "CongDan__fs_BCAChiTietDeNghi": "Thay đổi từ CMND sang Căn cước",
        "CongDan__fsBCAHoChieuGanChip": True,
        "CongDan__fs_BCANoiNhanHoChieu": True,
    }
    fields = {f["name"]: f for f in out}
    # Năm sinh cha/mẹ/vợ chồng: chọn định dạng "Năm" trước khi gõ; Phường/xã nạp theo tỉnh → chờ thêm.
    assert fields["CongDan__fs_BCANgaySinhChaCD"]["dateFormat"] == "Năm"
    assert fields["CongDan__fs_BCANgaySinhVoChong"]["dateFormat"] == "Năm"
    assert "dateFormat" not in fields["CongDan__fs_BCANgayCapCCCD"]
    assert fields["CongDan__fs_BCAQueQuanMaQH"]["waitMs"] == 8000 and fields["CongDan__fs_BCANoiOHienTaiMaQH"]["waitMs"]
    # Ô khoá do CSDLQG về dân cư đổ sẵn: không phát.
    for locked in ("CongDan_tenCongDan", "CongDan_soCmnd", "CongDan__fs_BCAGioiTinhCd", "CongDan__fs_BCANgaySinhCD",
                   "CongDan__fs_BCADanToc", "CongDan__fs_BCATonGiao", "CongDan__fs_BCAHoVaTenCha"):
        assert locked not in fields
    joined = " ".join(warnings)
    assert "Ảnh chân dung" in joined and "hoàn tiền" in joined and "Email" in joined
    assert "loại hộ chiếu" in joined  # tờ khai không thấy rõ ô đánh dấu → mặc định có chip, cảnh báo
    # Ô 17 theo cơ quan đã chọn ở bước chọn trường hợp → không phát, chỉ nhắc đơn vị trên tờ khai.
    assert "Công an tỉnh Lai Châu — kiểm tra ô 17" in joined


def test_noi_dung_de_nghi_va_loai_chip():
    by = _by(_enrich({**HO_SO, "ToKhai_NoiDungDeNghi": "Cấp lại hộ chiếu do bị mất",
                      "ToKhai_LoaiHoChieu": "khong_chip"})[0])
    assert by["CongDan__fs_BCANoiDungDeNghi"] == DE_NGHI_MAT and "CongDan__fs_BCAChiTietDeNghi" not in by
    assert by["CongDan__fsBCAHoKhongChieuGanChip"] is True and "CongDan__fsBCAHoChieuGanChip" not in by
    # Không có hộ chiếu cũ, mục 14 trống → cấp lần đầu, không phát ô mục 13.
    values = {k: v for k, v in HO_SO.items()
              if not k.startswith("HoChieu_") and k not in ("ToKhai_HoChieuCu_So", "ToKhai_HoChieuCu_NgayCap",
                                                             "ToKhai_NoiDungDeNghi")}
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCANoiDungDeNghi"] == DE_NGHI_LAN_DAU and "CongDan__fs_BCAHoChieuPT" not in by
    # Hộ chiếu cũ đã hết hạn, mục 14 trống → cấp lại do hết hạn.
    values = {**HO_SO, "HoChieu_NgayHetHan": "01/02/2020"}
    values.pop("ToKhai_NoiDungDeNghi")
    assert _by(_enrich(values)[0])["CongDan__fs_BCANoiDungDeNghi"] == DE_NGHI_HET_HAN


def test_giay_nguoi_khac_bi_bo_va_nhan_qua_buu_chinh_canh_bao():
    out, warnings = _enrich({**HO_SO, "HoChieu_HoTen": "TRẦN THỊ CÚC", "HoChieu_So": "C7654321",
                             "ToKhai_DiaChiNhanHoChieu": "Số 10 Tổ 1, Khối 2, Phường Kỳ Lừa, Tỉnh Lạng Sơn"})
    by = _by(out)
    # Hộ chiếu của người khác → lấy số + ngày cấp theo mục 13 tờ khai, nơi sinh theo tờ khai.
    assert by["CongDan__fs_BCAHoChieuPT"] == "C1234567" and by["CongDan__fs_BCANgayCapHoChieuPT"] == "01/02/2019"
    assert "CongDan__fs_BCANoiCapHCGanNhat" not in by and by["CongDan__fs_BCANoiKhaiSinhCD"] == "Hưng Yên"
    assert any("Hộ chiếu tải lên không phải của người đề nghị" in w for w in warnings)
    assert "CongDan__fs_BCANoiNhanHoChieu" not in by and any("Nhận qua bưu chính" in w for w in warnings)


def test_so_ho_chieu_ocr_doc_nham_va_mrz():
    # Chạy thật bộ mẫu 18/11: OCR đọc "5" thành "S" ở trang nhân thân và chen thêm "S" ở mục 13 tờ khai.
    out, warnings = _enrich({**HO_SO, "HoChieu_So": "CS234567", "ToKhai_HoChieuCu_So": "CS1234567"})
    assert _by(out)["CongDan__fs_BCAHoChieuPT"] == "C5234567"
    # Dòng MRZ đúng chữ số kiểm tra thắng số in trên trang; MRZ sai chữ số kiểm tra thì bỏ qua MRZ.
    mrz = "C1234567<0VNM8503029M2902014034085000001<<10"
    by = _by(_enrich({**HO_SO, "HoChieu_So": "CS234567", "HoChieu_MRZ": mrz})[0])
    assert by["CongDan__fs_BCAHoChieuPT"] == "C1234567"
    by = _by(_enrich({**HO_SO, "HoChieu_So": "C7654321", "HoChieu_MRZ": mrz.replace("<0VNM", "<3VNM")})[0])
    assert by["CongDan__fs_BCAHoChieuPT"] == "C7654321"
    # Tờ khai chen chữ thừa mà vẫn là cùng cuốn hộ chiếu → không cảnh báo lệch số.
    _, warnings = _enrich({**HO_SO, "HoChieu_MRZ": mrz, "ToKhai_HoChieuCu_So": "CS1234567"})
    assert not any("khác hộ chiếu tải lên" in w for w in warnings)


def test_fallback_ocr_khi_llm_bo_sot():
    to_khai = ("TỜ KHAI\n(Dùng cho công dân Việt Nam đề nghị cấp hộ chiếu phổ thông ở trong nước)\n"
               "13. Hộ chiếu phổ thông lần gần nhất (nếu có) số CS1234567 cấp ngày 01/02/2019\n"
               "14. Nội dung đề nghị(4) Đề nghị khác.. Thay đổi từ CMND sang Căn cước\n"
               "Cấp hộ chiếu không gắn chip điện tử ☐ Cấp hộ chiếu có gắn chip điện tử [X]")
    ho_chieu = "HỘ CHIẾU / PASSPORT\nP<VNMTRAN<<VAN<AN<<<<\nC1234567<0VNM8503029M2902014034085000001<<10"
    fields = mapper.ocr_fallback([{"name": "ToKhai_Ho", "value": "TRẦN"}],
                                 [{"name": "tk.pdf", "text": to_khai}, {"name": "hc.jpg", "text": ho_chieu}])
    assert fields["ToKhai_NoiDungDeNghi"] == "Đề nghị khác.. Thay đổi từ CMND sang Căn cước"
    assert fields["ToKhai_LoaiHoChieu"] == "co_chip" and fields["ToKhai_HoChieuCu_So"] == "CS1234567"
    assert fields["HoChieu_MRZ"].startswith("C1234567<0VNM")
    # LLM đã trả thì giữ nguyên; ô "không gắn chip" được đánh dấu → khong_chip.
    fields = mapper.ocr_fallback({"ToKhai_NoiDungDeNghi": "Cấp hộ chiếu lần đầu"},
                                 [{"text": to_khai.replace("điện tử ☐", "điện tử [X]").replace("tử [X]\n", "tử ☐\n")
                                   .replace("có gắn chip điện tử [X]", "có gắn chip điện tử ☐")}])
    assert fields["ToKhai_NoiDungDeNghi"] == "Cấp hộ chiếu lần đầu" and fields["ToKhai_LoaiHoChieu"] == "khong_chip"


def test_noi_sinh_nuoc_ngoai_va_dia_chi_cccd_du_phong():
    values = {**HO_SO, "HoChieu_NoiSinh": "NHẬT BẢN", "Cccd_HoTen": "Trần Văn An", "Cccd_SoDinhDanh": "034085000001",
              "Cccd_NgayCap": "10/06/2021", "Cccd_NoiCap": "Cục trưởng Cục Cảnh sát quản lý hành chính về trật tự xã hội",
              "Cccd_NoiThuongTru": {"tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "chiTietDuoiXa": "Tổ 2"}}
    values.pop("ToKhai_ThuongTru")
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCANoiKhaiSinhCD"] == "Nhật Bản"
    assert by["CongDan__fs_BCAQueQuanMaTinh"] == "Tỉnh Lai Châu" and by["CongDan__fs_BCAQueQuanChiTiet"] == "Tổ 2"
    assert by["CongDan__fs_BCANoiCapCCCD"] == "Cục CS QLHC về TTXH"


def test_schema_registry_link_va_detect():
    assert {"ToKhai_Ho", "ToKhai_Cha_NgaySinh", "HoChieu_So", "Cccd_NgayCap"} <= ALLOWED
    assert COMPACT_COMP_BY_NAME["ToKhai_ThuongTru"] == "x-select-area"
    assert COMPACT_COMP_BY_NAME["ToKhai_Cha_NgaySinh"] == "x-input"  # năm trần, không ép dd/mm/yyyy
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"]
    assert proc["detect"]["textIncludes"] == ["hộ chiếu phổ thông"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.001456" and link["label"] == proc["label"]
    assert link["needsAgencySelect"] is False and link["directSubmit"] is True and link["bcaSubmit"] is True
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert "matthc=1.001456" in public["detect"]["urlIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaHoChieu": True}


def test_tro_ly_cung_key_detect_hien_moi_tinh_va_mo_thang_trang_chon_truong_hop():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat.router import _clean_client_capabilities

    proc = hf.get_procedure(KEY)
    assert proc["detect"] == registry.get_procedure(KEY)["detect"] and proc["label"] == registry.get_procedure(KEY)["label"]
    assert proc["requiresCapability"] == "supportsBcaHoChieu" and proc["hasAttachmentStep"] is True
    assert proc["supportsSplitDocuments"] is True and hf.get_attach_pipeline(KEY) is registry.get_attach_pipeline(KEY)
    assert proc["keKhaiUrl"].endswith("chon-truong-hop-ho-so?ma-thu-tuc-public=29497")
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY) and "provinceOnly" not in proc
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert _clean_client_capabilities({"supportsBcaHoChieu": True})["supportsBcaHoChieu"] is True

    # Bản trợ lý chưa khai cờ: không dẫn vào cổng.
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert "chưa hỗ trợ" in r.display_md and not r.actions
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == proc["keKhaiUrl"]
    flow._handle_guide_login(conv, Intent("event", "page_status", {"loggedIn": True, "formKind": "standard"}))
    assert conv["state"] in ("ask_doc_method", "consent")


def test_tro_ly_tu_chon_co_quan_theo_tinh_chi_hoi_truong_hop_giai_quyet():
    caps = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
    # Tỉnh của TÀI KHOẢN trợ lý thắng nơi làm thủ tục đã chọn (user 18/11).
    conv = {"_id": "c1", "state": "greet", "procedure_key": None, "client_capabilities": caps,
            "auth_user": {"tinh": "Khánh Hòa", "province_slug": "khanhhoa"},
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    flow._start_guide_login(conv)
    turn = lambda kind, value, payload=None: asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))  # noqa: E731
    r = turn("event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    # Tới trang: extension tự dò ô + chọn sẵn ô cơ quan theo tỉnh công dân chọn lúc đầu (ưu tiên mục "Công an …").
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}],
                          "presets": [{"label": "Cơ quan giải quyết hồ sơ", "match": "khanh hoa", "prefer": "cong an"}]}]
    assert "**Trường hợp giải quyết**" in r.display_md
    # Extension đã chọn cơ quan, cổng hiện ô Trường hợp giải quyết (2 lựa chọn) → báo đã chọn + chỉ hỏi ô đó.
    agency = {"name": "maCoQuan", "present": True, "value": "Công an tỉnh Khánh Hòa", "options": ["Công an tỉnh Khánh Hòa"],
              "fixed": False, "label": "Cơ quan giải quyết hồ sơ", "required": True}
    case = {"name": "maQttt", "present": True, "value": "",
            "options": ["8 ngày làm việc - Cấp hộ chiếu phổ thông cho người đủ từ 14 tuổi",
                        "8 ngày làm việc - Cấp hộ chiếu phổ thông cho trẻ em dưới 14 tuổi"],
            "fixed": False, "label": "Trường hợp giải quyết", "required": True}
    r = turn("action", "lc_result_report", {"groups": [agency, case], "prepared": ["preset:maCoQuan"]})
    assert "Tôi đã chọn sẵn **Cơ quan giải quyết hồ sơ**: **Công an tỉnh Khánh Hòa**" in r.display_md
    trail = " ".join(a.get("md", "") for a in r.actions if a.get("type") == "trail_message")
    assert "**Trường hợp giải quyết**" in trail and "**Cơ quan giải quyết hồ sơ**" not in trail
    # Thẻ: dòng cơ quan chỉ hiện giá trị (không dãy nút tỉnh bị cắt 8 mục), dòng trường hợp có 2 nút.
    rows = {row["name"]: row for row in r.cards[0]["rows"]}
    assert rows["maCoQuan"]["fixed"] is True and rows["maCoQuan"]["options"] == []
    assert len(rows["maQttt"]["options"]) == 2
    # Cổng chặn / ô đổi → đọc lại vẫn kèm preset để chọn bù khi lượt đầu ô cơ quan chưa nạp kịp.
    r = turn("action", "lc_case_changed", {})
    assert r.actions[0]["prepare"] is False and r.actions[0]["presets"][0]["match"] == "khanh hoa"
    # Không biết tỉnh → không preset, công dân tự chọn cả hai ô trên thẻ.
    conv2 = {"_id": "c2", "state": "greet", "procedure_key": None, "client_capabilities": caps, "location": {}}
    flow._to_confirm_procedure(conv2, KEY)
    flow._start_guide_login(conv2)
    r = asyncio.run(flow._handle_turn_inner(conv2, Intent("event", "page_status",
                                                          {"loggedIn": True, "formKind": "", "lcStep": 1})))
    assert "presets" not in r.actions[0]


# ── Đính kèm: bảng Thành phần hồ sơ 2 dòng ──
import asyncio  # noqa: E402
import base64  # noqa: E402
import json  # noqa: E402

from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.attach import planner as attach_planner  # noqa: E402
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.attach.dinh_kem_khong_tach import (  # noqa: E402
    planner as whole_planner,
)
from app.process.schemas import FileItem  # noqa: E402
from app.services import ocr as ocr_service  # noqa: E402
from app.services.llm import client as llm_client  # noqa: E402

TO_KHAI = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI\n(Dùng cho công dân Việt Nam đề nghị cấp hộ chiếu phổ thông ở "
           "trong nước)\n1. Họ TRẦN Chữ đệm và tên VĂN AN\n13. Hộ chiếu phổ thông lần gần nhất (nếu có) số C1234567")
HO_CHIEU = ("HỘ CHIẾU / PASSPORT\nSố hộ chiếu / Passport No C1234567\nHọ và tên / Full name TRẦN VĂN AN\n"
            "P<VNMTRAN<<VAN<AN<<<<<<<<<<<<<<<<<<<<<<<<<<<")
HO_CHIEU_2 = "CƠ QUAN CẤP HỘ CHIẾU\nISSUING AUTHORITY\nCỤC QUẢN LÝ XUẤT NHẬP CẢNH"
KHAI_SINH = "GIẤY KHAI SINH\nHọ, chữ đệm, tên: TRẦN MINH KHANG"
ROW2 = ["ho chieu pho thong cap lan gan nhat"]


def _file(name: str, size: int = 10) -> FileItem:
    data = base64.b64encode(b"x" * size).decode()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}", role="other")


def _pdf_text(*pages: str) -> str:
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{text}" for i, text in enumerate(pages, 1))


def _mock_io(monkeypatch, texts: dict[str, str], llm):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, **_):
        return llm(messages) if callable(llm) else llm

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", fake_chat)


def _slots(result) -> dict:
    return {a["slotIndex"]: a for a in result["attachments"] if a["target"] == "fixed-slot"}


def test_dinh_kem_khong_tach_ho_chieu_va_to_khai_chung_dong_2(monkeypatch):
    # Ảnh ánh xạ: tờ khai [F2] tải trước vẫn đứng SAU hộ chiếu [F1] trong dòng 2; dòng 1 không tick.
    files = [_file("to-khai.pdf"), _file("ho-chieu.jpg")]
    texts = {"to-khai.pdf": TO_KHAI, "ho-chieu.jpg": HO_CHIEU + "\n" + HO_CHIEU_2}
    llm = json.dumps({"documents": [{"index": 0, "docType": "to_khai", "documentName": ""},
                                    {"index": 1, "docType": "ho_chieu", "documentName": ""}]})
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {}, {}))
    assert result["extracted"]["attachmentMode"] == "whole"
    slots = _slots(result)
    assert list(slots) == [1] and len(result["attachments"]) == 1
    row = slots[1]
    assert row["fileIndex"] == 1 and row["sourceFileIndexes"] == [1, 0] and row["tickRow"] is True
    assert row["slotKeywords"] == ROW2 and "sourceSegments" not in row
    assert any("đính kèm chung 2 giấy" in e for e in result["errors"])


def test_dinh_kem_luat_tieu_de_dai_dien_dong_1_va_cap_lan_dau(monkeypatch):
    files = [_file("ks.pdf"), _file("hc.pdf"), _file("tk.pdf")]
    texts = {"ks.pdf": KHAI_SINH, "hc.pdf": HO_CHIEU, "tk.pdf": TO_KHAI}
    _mock_io(monkeypatch, texts, "không phải JSON")  # LLM hỏng → luật theo tiêu đề
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": False}, {}))
    slots = _slots(result)
    assert slots[0]["fileIndex"] == 0 and slots[0]["slotKeywords"] == ["chung minh nguoi dai dien hop phap"]
    assert slots[1]["sourceFileIndexes"] == [1, 2]
    # Cấp lần đầu (không hộ chiếu cũ): dòng 2 trống, tờ khai không đính, cảnh báo; tệp > 6 MB bị loại.
    files = [_file("tk.pdf"), _file("to.pdf", 7 * 1024 * 1024)]
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    assert result["attachments"] == []
    assert any("dòng \"Hộ chiếu phổ thông cấp lần gần nhất\" để trống" in e for e in result["errors"])
    assert any("Chưa đính kèm 'tk.pdf'" in e for e in result["errors"])
    assert any("vượt giới hạn 6 MB" in e for e in result["errors"])


def test_dinh_kem_tach_dung_dong_khong_sot_trang(monkeypatch):
    # Một PDF gộp: tờ khai (1 trang) + hộ chiếu (2 trang) + trang trắng.
    files = [_file("ho-so.pdf")]
    texts = {"ho-so.pdf": _pdf_text(TO_KHAI, HO_CHIEU, HO_CHIEU_2, "~ . ~")}
    llm = json.dumps({
        "tep": [{"fileIndex": 0, "tieuDeTrang": ["Tờ khai đề nghị cấp hộ chiếu", "Hộ chiếu phổ thông", "", ""]}],
        "documents": [
            {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai"},
            {"fileIndex": 0, "pages": [2, 3], "docType": "ho_chieu", "documentName": "Hộ chiếu"},
            {"fileIndex": 0, "pages": [4], "docType": "blank_page", "documentName": ""},
        ],
    })
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["extracted"]["attachmentMode"] == "split"
    slots = _slots(result)
    assert list(slots) == [1]
    # Hộ chiếu trước, tờ khai sau, cùng một tệp ghép.
    assert slots[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}, {"fileIndex": 0, "pageIndexes": [0]}]
    # Không sót trang có chữ; trang 4 không có chữ là trang trắng → bỏ (khung chia trang dùng chung).
    pages = sorted(p for a in result["attachments"] for s in a.get("sourceSegments") or [] for p in s["pageIndexes"])
    assert pages == [0, 1, 2]


def test_dinh_kem_tach_loi_quay_ve_khong_tach(monkeypatch):
    files = [_file("hc.pdf"), _file("tk.pdf")]
    texts = {"hc.pdf": HO_CHIEU, "tk.pdf": TO_KHAI}

    def broken(_messages):
        raise RuntimeError("LLM sập")

    _mock_io(monkeypatch, texts, broken)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["errors"][0].startswith("attachment_agent (tách)")
    assert result["extracted"]["attachmentMode"] == "whole"
    assert _slots(result)[1]["sourceFileIndexes"] == [0, 1]
    assert not any(a.get("sourceSegments") for a in result["attachments"])
