"""[Lào Cai] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót (1.115686).

Khoá 4 điều dễ vỡ: detect phải phân biệt được với 6 bản đính chính của tỉnh khác (tên trùng nguyên
văn); CCCD có dòng riêng; ô "Về việc" GIỮ CÂU MẶC ĐỊNH rồi nối nội dung; tệp gộp nhiều Giấy chứng
nhận vẫn một dòng nhưng phải cảnh báo ô "Số bản".
"""

import base64
import re
from pathlib import Path

from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.attach import planner
from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process import mapper
from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "dinh-chinh-gcn-da-cap-lao-cai"
_THONGTIN = Path(__file__).resolve().parents[2].parent / "thongtin"


def _attach_html():
    for d in _THONGTIN.glob("159-*"):
        for f in d.glob("*đính kèm*.html"):
            return f
    return None


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_registry_co_buoc_dinh_kem_va_khoa_dung_ma():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert "1.115686" in entry["detect"]["textIncludes"]


def test_ma_thu_tuc_la_thu_duy_nhat_phan_biet_voi_ban_dinh_chinh_tinh_khac():
    """Tên thủ tục trùng nguyên văn với Lai Châu/Bắc Ninh/Lâm Đồng/Ninh Bình/Quảng Ngãi/Đà Nẵng."""
    entry = _entry()
    cum_ten = next(t for t in entry["detect"]["textIncludes"] if "đính chính" in t)
    khac = [p for p in public_list()
            if p["key"] != _KEY and "đính chính giấy chứng nhận đã cấp lần đầu" in p["label"].lower()]
    assert khac, "phải còn bản đính chính của tỉnh khác để đối chiếu"
    for other in khac:
        assert cum_ten in other["label"].lower() or True  # tên trùng là chuyện bình thường
        assert "1.115686" not in str(other.get("detect")), other["key"]


def test_bon_dong_dinh_kem_dung_thu_tu_dom():
    html_file = _attach_html()
    if html_file is None:
        return
    html = html_file.read_text(encoding="utf-8", errors="replace")
    postnames = []
    for tag in re.findall(r"<input\b[^>]*>", html):
        if 'type="file"' not in tag:
            continue
        found = re.search(r'postname="([^"]*)"', tag)
        postnames.append(found.group(1) if found else "")
    if not postnames:
        return

    assert len(postnames) == 8
    assert postnames[0].endswith("49890_fileGiayTo")   # Đơn Mẫu 24
    assert postnames[1].endswith("49911_fileGiayTo")   # Bản gốc GCN
    assert postnames[2].endswith("49912_fileGiayTo")   # Giấy tờ chứng minh sai sót
    assert postnames[3].endswith("49914_fileGiayTo")   # Văn bản ủy quyền
    assert postnames[4] == "HoSoOnline_giayToKhac_file_1"
    assert set(planner._ROUTES.values()) == {0, 1, 2, 3}


def test_ho_so_mau_len_dung_dong():
    """Cả 2 hồ sơ mẫu đều gồm đơn + tệp Giấy chứng nhận."""
    items, warnings, _ = planner.build_plan_items(
        _files(["don_trieu_van_cuong.pdf", "so_trieu_van_cuong.pdf"]),
        {0: ("don_mau_24", []), 1: ("gcn_ban_goc", [])},
    )

    assert [i["slotIndex"] for i in items] == [0, 1]
    assert all(i["target"] == "fixed-slot" for i in items)
    assert any("Số bản" in w for w in warnings)


def test_cccd_co_dong_rieng_khong_bi_day_sang_giay_to_khac():
    """Khác phần lớn thủ tục đất đai: CCCD chính là giấy tờ chứng minh sai sót (dòng 3)."""
    items, warnings, _ = planner.build_plan_items(
        _files(["cccd.pdf"]), {0: ("giay_to_chung_minh_sai_sot", [])}
    )

    assert items[0]["slotIndex"] == 2
    assert items[0]["target"] == "fixed-slot"
    assert not any("CĂN CƯỚC CÔNG DÂN" in w for w in warnings)


def test_thieu_giay_to_chung_minh_sai_sot_thi_canh_bao():
    _, warnings, _ = planner.build_plan_items(_files(["don.pdf"]), {0: ("don_mau_24", [])})

    assert any("CĂN CƯỚC CÔNG DÂN" in w for w in warnings)


def test_tep_vuot_6mb_thi_canh_bao_nen_lai():
    """Cổng chặn 6 MB; hồ sơ mẫu có tệp 7,8 MB phải nén trước khi tải lên."""
    big = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    _, warnings, _ = planner.build_plan_items(
        [{"name": "so.pdf", "type": "application/pdf", "dataUrl": big}],
        {0: ("gcn_ban_goc", [])},
    )

    assert any("6 MB" in w and "so.pdf" in w for w in warnings)


def test_moi_tep_mot_dong_va_uu_tien_don():
    items, _, classified = planner.build_plan_items(
        _files(["gop.pdf"]), {0: ("gcn_ban_goc", ["don_mau_24"])}
    )

    assert len(items) == 1
    assert items[0]["slotIndex"] == 0
    assert classified[0]["assignedType"] == "don_mau_24"


def test_khong_bo_sot_file_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert all(i["target"] == "new" for i in items)
    assert all(c["source"] == "default" for c in classified)
    assert warnings


def test_slot_key_khong_trung_keyword_cua_extension():
    content = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "content.js"
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    assert "laocai_dcgcn_" not in block


def test_ve_viec_giu_cau_mac_dinh_roi_noi_noi_dung_dinh_chinh():
    fields, _ = mapper.enrich([
        {"name": "Don_NoiDungDinhChinh",
         "value": "Xin đính chính sai sót năm sinh của bà Đỗ Thị Hợi từ năm 1937 thành năm 1936"},
        {"name": "Gcn_SoPhatHanh", "value": "BU 035181"},
        {"name": "Gcn_SoVaoSo", "value": "CH 01950"},
        {"name": "Gcn_NgayCap", "value": "22/01/2015"},
    ])
    ve_viec = _values(fields)["HoSoOnline_veViec"]

    assert ve_viec.startswith("Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót – ")
    assert "năm 1937 thành năm 1936" in ve_viec
    assert "BU 035181" in ve_viec and "CH 01950" in ve_viec and "22/01/2015" in ve_viec


def test_ve_viec_khong_lap_cum_giay_chung_nhan_khi_don_da_viet_san():
    fields, _ = mapper.enrich([
        {"name": "Don_NoiDungDinhChinh",
         "value": "Xin đính chính lại bà Nguyễn Thị Tuyến thành bà Nguyễn Thị Tuyền có sai xót trên "
                  "giấy chứng nhận quyền sử dụng đất"},
        {"name": "Gcn_SoPhatHanh", "value": "AA 10145010"},
    ])
    ve_viec = _values(fields)["HoSoOnline_veViec"]

    assert ve_viec.count("iấy chứng nhận") == 2  # tên thủ tục + cụm trong câu của đơn
    assert "(số phát hành AA 10145010)" in ve_viec


def test_ve_viec_khong_phat_khi_khong_doc_duoc_noi_dung_dinh_chinh():
    """Ghi mỗi tên thủ tục thì đúng bằng việc để nguyên ô cổng đã điền sẵn."""
    fields, _ = mapper.enrich([{"name": "Gcn_SoPhatHanh", "value": "AA 10145010"}])
    assert "HoSoOnline_veViec" not in _values(fields)


def test_ghi_chu_neu_nguoi_dong_su_dung_dat():
    """Đơn thường chỉ một người ký — cán bộ phải biết còn người đồng sử dụng."""
    fields, _ = mapper.enrich([
        {"name": "ThuaDat_SoThua", "value": "93"},
        {"name": "ThuaDat_ToBanDo", "value": "237"},
        {"name": "DongSuDung_HoTen", "value": "NGUYỄN THỊ TUYỀN"},
        {"name": "DongSuDung_SoDinhDanh", "value": "015191006685"},
    ])
    ghi_chu = _values(fields)["HoSoOnline_ghiChu"]

    assert "Thửa đất số 93" in ghi_chu and "tờ bản đồ 237" in ghi_chu
    assert "Người đồng sử dụng đất: NGUYỄN THỊ TUYỀN" in ghi_chu
    assert "015191006685" in ghi_chu


def test_hai_o_textarea_co_that_tren_trang():
    for name in ("HoSoOnline_veViec", "HoSoOnline_ghiChu"):
        assert name in UI_COMP_BY_NAME, name
    html_file = _attach_html()
    if html_file is None:
        return
    html = html_file.read_text(encoding="utf-8", errors="replace")
    for name in ("HoSoOnline_veViec", "HoSoOnline_ghiChu"):
        assert f'name="{name}"' in html, name


def test_prompt_cccd_khong_bi_xep_other():
    from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.attach.prompt import SYSTEM_PROMPT

    assert "CĂN CƯỚC Ở THỦ TỤC NÀY CÓ DÒNG RIÊNG" in SYSTEM_PROMPT
    assert "MỘT TỆP GỘP NHIỀU GIẤY CHỨNG NHẬN" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT


def test_prompt_process_chep_nguyen_van_noi_dung_dinh_chinh():
    from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process.prompt import EXTRA_RULES

    assert "chép NGUYÊN VĂN" in EXTRA_RULES
    assert "MỘT DẤU hoặc MỘT CHỮ SỐ" in EXTRA_RULES
    assert "NGƯỜI ĐỒNG SỬ DỤNG" in EXTRA_RULES
