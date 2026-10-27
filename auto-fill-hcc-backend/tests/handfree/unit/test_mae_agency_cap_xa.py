"""Hộp thoại chọn cơ quan của cổng bộ khi thủ tục giải quyết ở CẤP XÃ.

Hai thủ tục Bộ Nội vụ ("người có công từ trần", "trợ cấp thờ cúng liệt sĩ") và ATTP nông, lâm,
thủy sản của Bộ NN&MT dùng chung
component `form#ngSelectAgencyForm1` với các cổng iGate khác, nhưng chọn Tỉnh + **Phường/Xã**
chứ không phải Sở/Ban ngành. Bản extension trên chợ chỉ biết gạt radio "Sở/Ban ngành" → BE
phải gác bằng `supportsMaeWardAgency`, thiếu cờ thì dặn chọn tay thay vì bắn lệnh gạt nhầm cấp.
"""
import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.flow import Intent
from app.channels.handfree.procedure_registry import get_procedure

WARD_CLIENT = {"supportsMaeWardAgency": True}
OLD_CLIENT = {"supportsRating": True}
LOC = {"province": "Tỉnh Quảng Ngãi", "ward": "Phường Nghĩa Lộ"}

# Mọi thủ tục chọn cơ quan cấp xã phải cư xử giống hệt nhau — thêm thủ tục mới thì thêm key vào
# đây, không chép cả bộ test.
WARD_KEYS = ["uu-dai-ncc-tu-tran", "tro-cap-tho-cung-liet-si", "cap-gcn-attp-nong-lam-thuy-san",
             "cap-lai-to-quoc-ghi-cong", "cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong",
             "bo-sung-than-nhan-liet-si", "tham-vieng-mo-liet-si", "giai-quyet-che-do-khang-chien",
             "mai-tang-dan-cong-hoa-tuyen", "ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat"]
# Host cổng bộ + mã nhận diện trên cổng bộ + uuid DVCQG của từng thủ tục: uuid CHỈ có trên
# dichvucong.gov.vn, mã/id SPA chỉ có trên cổng bộ → urlScope thiếu một host là nửa số urlIncludes
# thành vô dụng (urlScope gate theo OR). ATTP nông lâm thủy sản (Bộ NN&MT) không có mã trên URL
# cổng bộ nên neo bằng id SPA apply-online như registry lõi.
WARD_URL_IDS = {
    "uu-dai-ncc-tu-tran": ("dichvucongbnv.moha.gov.vn", "MaTTHC=1.010824",
                           "019d2bfa-fc36-7611-9219-adb6dee5774f"),
    "tro-cap-tho-cung-liet-si": ("dichvucongbnv.moha.gov.vn", "MaTTHC=1.010803",
                                 "019d2bfa-fc0c-7046-b5dc-04303a18608d"),
    "cap-gcn-attp-nong-lam-thuy-san": ("dichvucongnnmt.mae.gov.vn", "apply-online/693a99efda87c4718ece1bc7",
                                       "019d2bfa-b57f-73cc-856f-0255333fcb48"),
    "cap-lai-to-quoc-ghi-cong": ("dichvucongbnv.moha.gov.vn", "MaTTHC=1.010778",
                                 "019d2bfa-fbf8-727d-a4be-847d1f9944ce"),
    "cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong": ("dichvucongbnv.moha.gov.vn", "MaTTHC=1.010814",
                                                          "019d2bfa-fc21-710a-9e17-59cdb35c723b"),
    "bo-sung-than-nhan-liet-si": ("dichvucongbnv.moha.gov.vn", "MaTTHC=1.010825",
                                  "019d2bfa-fc36-74e9-9909-551c04aa6c27"),
    "tham-vieng-mo-liet-si": ("dichvucongbnv.moha.gov.vn", "MaTTHC=1.013750",
                              "019d2bfb-2324-7555-8e56-024dcdb30038"),
    "giai-quyet-che-do-khang-chien": ("dichvucongbnv.moha.gov.vn", "MaTTHC=1.010819",
                                      "019d2bfa-fc33-7068-b98d-1b1eba21519f"),
    # ke_khai_links ghi key khác ("giai-quyet-che-do-mai-tang-dan-cong-hoa-tuyen") → uuid + mã khai tay.
    "mai-tang-dan-cong-hoa-tuyen": ("dichvucongbnv.moha.gov.vn", "MaTTHC=1.014359",
                                    "019d2bfb-2b25-777d-a825-2823012ce7ec"),
    "ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat": ("dichvucongnnmt.mae.gov.vn", "MaTTHC=1.013997",
                                                           "019d2bfa-8686-732b-b2d5-e6a422f1b242"),
}


def _conv(caps, key):
    return {
        "_id": "t-moha", "state": "guide_login", "history": [], "milestones": [],
        "procedure_key": key,
        "client_capabilities": dict(caps),
        "location": dict(LOC),
    }


def _proc(key):
    return get_procedure(key) or {}


@pytest.mark.parametrize("key", WARD_KEYS)
def test_dvcqg_van_chon_du_tinh_va_xa(key):
    """Ngoài DVCQG các thủ tục này chọn tỉnh + xã của tài khoản — không gạt toggle "Sở"."""
    proc = _proc(key)
    assert proc.get("agencyProvinceOnly") is None, "bật cờ này là ward bị bỏ trống"
    assert proc.get("agencySoFirst") is None, "gạt toggle Sở là chọn nhầm cấp cơ quan"
    assert proc.get("agencyDeptLabel") is None, "cấp xã thì không có tên Sở để đọc"
    assert proc["maePortal"] is True and proc["maeAgencyLevel"] == "ward"
    assert flow._agency_ward_display(proc, LOC) == "Phường Nghĩa Lộ"


@pytest.mark.parametrize("key", WARD_KEYS)
def test_detect_bat_duoc_ca_trang_dvcqg_lan_cong_bo(key):
    detect = _proc(key)["detect"]
    host, ma_tthc, uuid = WARD_URL_IDS[key]
    assert set(detect["urlScope"]) == {host, "dichvucong.gov.vn"}
    assert ma_tthc in detect["urlIncludes"]
    assert uuid in detect["urlIncludes"]
    assert _proc(key)["keKhaiUrl"].endswith(uuid)


@pytest.mark.parametrize("key", WARD_KEYS)
def test_hop_thoai_cong_bo_gui_lenh_chon_phuong_xa(key):
    conv = _conv(WARD_CLIENT, key)
    r = flow._variant_fill_agency_reply(conv, _proc(key), LOC)
    assert r.actions == [{
        "type": "fill_mae_agency",
        "province": "Tỉnh Quảng Ngãi",
        "ward": "Phường Nghĩa Lộ",
        "agencyLevel": "ward",
        "agency": "",
        "variant": "",
        "variantMatch": "",
        "variantAvoid": "",
    }]
    assert "Phường Nghĩa Lộ" in r.display_md
    assert "Sở" not in r.display_md, "cấp xã mà đọc tên Sở là sai cơ quan"


@pytest.mark.parametrize("key", WARD_KEYS)
def test_client_cu_khong_nhan_lenh_ma_duoc_dan_chon_tay(key):
    conv = _conv(OLD_CLIENT, key)
    r = flow._variant_fill_agency_reply(conv, _proc(key), LOC)
    assert r.actions == [], "engine cũ nhận lệnh này sẽ gạt sang Sở/Ban ngành"
    assert "Phường/Xã" in r.display_md and "Phường Nghĩa Lộ" in r.display_md


@pytest.mark.parametrize("key", WARD_KEYS)
def test_bao_loi_cung_doc_dung_cap_xa(key):
    conv = _conv(WARD_CLIENT, key)
    r = flow._handle_guide_login(
        conv, Intent("event", "mae_agency_failed", {"value": "không thấy ô xã"}))
    assert "Phường Nghĩa Lộ" in r.display_md
    assert "Sở/Ban ngành" not in r.display_md
    assert r.chips and r.chips[0]["send"] == "__event:sso_success"


@pytest.mark.parametrize("key", WARD_KEYS)
def test_bang_giay_to_bam_dung_o_co_dinh_cua_planner(key):
    """requiredDocs là thứ công dân đọc để mang giấy; slot cố định của planner core đứng trước
    theo đúng thứ tự ô trên cổng, và luôn phải còn ô catch-all cho tệp lạ."""
    docs = _proc(key)["requiredDocs"]
    assert docs[-1]["key"] == "khac", "thiếu catch-all → tệp lạ báo 'chưa nhận ra loại'"
    assert "hideRepeatableHint" not in _proc(key), "ô cố định: dồn một chỗ là sai ô"


def test_tho_cung_liet_si_theo_dung_ba_o_co_dinh_cua_planner():
    from app.pipelines.tro_cap_tho_cung_liet_si.attach.planner import SLOTS

    docs = _proc("tro-cap-tho-cung-liet-si")["requiredDocs"]
    assert [s["slotKey"] for s in SLOTS] == ["van_ban_uy_quyen", "don_de_nghi", "bang_tqgc"]
    assert [d["key"] for d in docs[:3]] == [s["slotKey"] for s in SLOTS]
    # Ủy quyền chỉ có khi các thân nhân cử một người đứng thờ cúng → không bắt buộc, dù nằm ô 1.
    assert docs[0]["optional"] is True
    assert "optional" not in docs[1] and "optional" not in docs[2]


def test_cap_lai_bang_tqgc_theo_dung_hai_o_co_dinh_cua_planner():
    from app.pipelines.cap_lai_to_quoc_ghi_cong.attach.planner import SLOTS

    docs = _proc("cap-lai-to-quoc-ghi-cong")["requiredDocs"]
    assert [s["slotKey"] for s in SLOTS] == ["don_de_nghi_mau16", "bang_tqgc_cu"]
    assert [d["key"] for d in docs[:2]] == [s["slotKey"] for s in SLOTS]
    # Bằng cũ chỉ "nếu còn" (mất bằng là lý do cấp lại) → không bắt buộc, dù nằm ô 2.
    assert "optional" not in docs[0] and docs[1]["optional"] is True


@pytest.mark.parametrize("key, pipeline", [
    ("cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong", "cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong"),
    ("bo-sung-than-nhan-liet-si", "bo_sung_than_nhan_liet_si"),
    ("tham-vieng-mo-liet-si", "tham_vieng_mo_liet_si"),
    ("giai-quyet-che-do-khang-chien", "giai_quyet_che_do_khang_chien"),
    ("sua-doi-thong-tin-ho-so-nguoi-co-cong", "sua_doi_thong_tin_ho_so_nguoi_co_cong"),
])
def test_giay_to_nguoi_co_cong_dung_thu_tu_o_co_dinh_cua_planner(key, pipeline):
    from importlib import import_module

    slots = import_module(f"app.pipelines.{pipeline}.attach.planner").SLOTS
    docs = _proc(key)["requiredDocs"]
    assert [d["key"] for d in docs[:len(slots)]] == [s["slotKey"] for s in slots]
    assert docs[-1]["key"] == "khac"


def test_mai_tang_dan_cong_tach_rieng_o_giay_chung_tu():
    """Planner dồn mọi tệp vào ô 1, riêng trích lục khai tử vào ô 2 (cổng không có "Thêm giấy tờ")."""
    from app.pipelines.mai_tang_dan_cong.attach.planner import SLOTS

    docs = _proc("mai-tang-dan-cong-hoa-tuyen")["requiredDocs"]
    assert [s["slotIndex"] for s in SLOTS] == [0, 1]
    assert [d["key"] for d in docs[:2]] == ["qd_tro_cap", "giay_chung_tu"]


@pytest.mark.parametrize("key", ["di-chuyen-ho-so-nguoi-huong-tro-cap", "sua-doi-thong-tin-ho-so-nguoi-co-cong"])
def test_thu_tuc_di_chuyen_ho_so_giu_nguyen_nhanh_so(key):
    """Thủ tục cùng cổng nhưng ở cấp Sở không được lây nhánh cấp xã."""
    move = get_procedure(key) or {}
    conv = _conv(WARD_CLIENT, key)
    r = flow._variant_fill_agency_reply(conv, move, LOC)
    action = r.actions[0]
    assert action["agency"] == "Sở Nội vụ"
    assert "agencyLevel" not in action
    assert r.display_md == vi.AGENCY_DEPT_DIALOG_AUTOFILL_GUIDE["md"].format(
        province="Tỉnh Quảng Ngãi", agency="Sở Nội vụ")


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])


def test_di_chuyen_ho_so_dinh_dung_dong_theo_thu_tu_cong_moi():
    """Cổng đã đổi thứ tự bảng Thành phần hồ sơ: dòng 1 bản sao CCCD / xác nhận cư trú, dòng 2 đơn Mẫu số 27.
    Extension tìm ô theo slotIndex nên số dòng phải đúng thứ tự trên cổng."""
    from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import SLOTS

    assert [(s["slotIndex"], s["slotKey"]) for s in SLOTS] == [(0, "cccd"), (1, "don_mau_27")]
