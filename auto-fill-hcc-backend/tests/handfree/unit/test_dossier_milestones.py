"""Vòng đời hồ sơ Handfree: mốc BẮT ĐẦU (_start_guide_login) và mốc NỘP (bấm Gửi hồ sơ).

Hai mốc này là căn cứ phân biệt hồ sơ THẬT với hồ sơ làm dở, và để tính thời gian làm hồ sơ.
Chúng phải sống ngoài `conversations` (TTL 24h) — xem app/dossiers/repo.py.
"""
import asyncio
import re
from pathlib import Path
from datetime import datetime, timezone

from app.channels.handfree.chat import flow
from app.channels.handfree.chat.intents import Intent
from app.procedures.portal_submit import portal_submit_rules


def _conv(**kw):
    base = {
        "_id": "c-dossier-test", "state": "confirm_procedure", "history": [],
        "procedure_key": "khai-sinh-dang-ky", "location": {"province": "Bắc Ninh", "ward": "Phường Bắc Giang"},
        "auth_user": {"id": "u1", "username": "bacgiang", "name": "Phường Bắc Giang"},
        "awaiting_events": [], "milestones": [],
    }
    base.update(kw)
    return base


def test_start_guide_login_cham_moc_bat_dau():
    conv = _conv()
    flow._start_guide_login(conv)
    assert isinstance(conv["dossier_started_at"], datetime)


def test_moc_bat_dau_khong_bi_dat_lai_khi_quay_lai_buoc_xac_nhan():
    """Công dân xác nhận lại thủ tục không được làm hồ sơ "trẻ ra"."""
    conv = _conv()
    flow._start_guide_login(conv)
    first = conv["dossier_started_at"]
    flow._start_guide_login(conv)
    assert conv["dossier_started_at"] == first


def test_start_guide_login_gui_kem_luat_nhan_nut_nop():
    """Content script cần luật ngay từ đầu hồ sơ, không đợi tới lúc sắp nộp."""
    conv = _conv()
    reply = flow._start_guide_login(conv)
    armed = [a for a in reply.actions if a.get("type") == "arm_submit_watch"]
    assert armed and armed[0]["rules"] == portal_submit_rules()


def _handle(conv, intent):
    return asyncio.run(flow.handle_turn(conv, intent))


def test_bam_gui_ho_so_cham_moc_va_KHONG_lam_phien_cong_dan():
    """Chỉ ghi mốc: không đẻ bubble, không đổi state — khác hẳn event `submitted`."""
    conv = _conv(state="attaching")
    reply = _handle(conv, Intent("event", "submit_clicked", {"host": "h", "ref": "144865"}))
    assert isinstance(conv["submit_clicked_at"], datetime)
    assert conv["submit_dossier_ref"] == "144865"
    assert conv["state"] == "attaching"
    assert not reply.display_md and not reply.chips and not reply.cards


def test_bam_o_bat_ky_buoc_nao_deu_duoc_ghi():
    """Thiết kế cũ gác theo state="done" nên mất dấu ở mọi nhánh đi chệch (tự đính kèm tay,
    thủ tục không có bước đính kèm...). Tín hiệu này là sự thật về TRANG, không theo hội thoại."""
    for state in ("guide_login", "filling", "reviewing", "collecting_docs", "done"):
        conv = _conv(state=state)
        _handle(conv, Intent("event", "submit_clicked", {"host": "h", "ref": "1"}))
        assert conv.get("submit_clicked_at"), f"mất dấu ở state={state}"


def test_bam_nhieu_lan_thi_lan_cuoi_thang():
    conv = _conv(state="done")
    _handle(conv, Intent("event", "submit_clicked", {"host": "h", "ref": "1"}))
    first = conv["submit_clicked_at"]
    _handle(conv, Intent("event", "submit_clicked", {"host": "h", "ref": "2"}))
    assert conv["submit_clicked_at"] >= first
    assert conv["submit_dossier_ref"] == "2"


# (host, pathname+hash, có được tính là trang nộp không) — lấy từ URL THẬT của snapshot.
_URL_CASES = [
    ("dichvucongnganhtuphap.moj.gov.vn", "/nop-ho-so/144865", True),
    ("dichvucongnganhtuphap.moj.gov.vn", "/", False),
    ("dichvucongnganhtuphap.moj.gov.vn", "/ho-so-cua-toi", False),
    ("dichvucongnganhtuphap.moj.gov.vn", "/tra-cuu/nop-ho-so/1", False),
    ("dichvucongnganhtuphap.moj.gov.vn", "/nop-ho-so/144865/xem", False),
    # Liên thông định tuyến bằng HASH: khớp pathname không thôi là trượt sạch.
    ("lienthong.dichvucong.gov.vn", "/#/ke-khai/2.000987", True),
    ("lienthong.dichvucong.gov.vn", "/", False),
    ("lienthong.dichvucong.gov.vn", "/#/trang-chu", False),
    ("dichvucong.bacninh.gov.vn", "/web/guest/eform", True),
    ("dichvucong.bacninh.gov.vn", "/web/guest/profile", False),
    ("dichvucong.bacninh.gov.vn", "/web/guest/vneidsso", False),
    ("dvc.moc.gov.vn", "/vi/padsvc/apply-online/695f13ee9b680d19f366af71", True),
    ("dichvucong.danang.gov.vn", "/vi/padsvc/apply-online/68b01d569d1db539542d7399", True),
    ("dichvucong.danang.gov.vn", "/vi/padsvc/apply-online", False),
    ("dichvucong.danang.gov.vn", "/vi/padsvc/apply-online/68b01d569d1db539542d7399/xem", False),
    # HkdOnline: mỗi bước là MỘT trang .aspx riêng nên pathname đủ khoá bước cuối.
    ("hokinhdoanh.dkkd.gov.vn", "/HkdOnline/Forms/APP/ConfirmPrepare.aspx", True),
    ("hokinhdoanh.dkkd.gov.vn", "/HkdOnline/Forms/APP/Registration.aspx", False),
    ("hokinhdoanh.dkkd.gov.vn", "/HkdOnline/Forms/APP/ContactPerson.aspx", False),
    ("hokinhdoanh.dkkd.gov.vn", "/HkdOnline/Forms/APP/TaxInformation.aspx", False),
]


def test_luat_nhan_nut_chi_khop_dung_trang_nop_ho_so():
    """urlPattern là cổng chặn: khớp NGUYÊN `pathname + hash`, không phải "contains"."""
    rules = portal_submit_rules()
    for host, path, want in _URL_CASES:
        rule = rules[host]
        assert bool(re.match(rule["urlPattern"], path)) is want, f"{host} {path}"
    moj = re.match(rules["dichvucongnganhtuphap.moj.gov.vn"]["urlPattern"], "/nop-ho-so/144865")
    assert moj.group(1) == "144865"


def test_formio_khop_bang_THUOC_TINH_khong_phai_nhan():
    """Mười cổng dùng chung nền tảng Form.io: nút cuối KHÔNG có id, và nhãn đổi theo cổng/thủ
    tục — "Nộp hồ sơ", "Tiếp tục", "Thanh toán" (có phí). Mỏ neo CHÍNH phải là thuộc tính:
    đã kiểm snapshot màn cuối cả mười cổng, đúng MỘT phần tử mỗi trang mang form="captchaForm".

    buttonText ở đây chỉ là LƯỚI HAI phòng khi cổng bỏ thuộc tính đó (mất nó là mười cổng tắt
    tiếng cùng lúc) — và chỉ được chứa nhãn KHÔNG bao giờ xuất hiện ở bước giữa. Danh sách
    nhãn an toàn chốt ở tests/unit/test_portal_submit_rules.py.
    """
    rules = portal_submit_rules()
    for host in ("dichvucong.danang.gov.vn", "dvc.moc.gov.vn"):
        rule = rules[host]
        assert rule["buttonSelector"] == 'button[form="captchaForm"]'
        # "Tiếp tục" là nhãn của nút BƯỚC GIỮA (206 lần trong snapshot) → cấm tuyệt đối.
        assert "tiep tuc" not in (rule.get("buttonText") or [])
        # btn_next dùng chung với nút "Tiếp tục" của các bước trước → cấm khớp theo class đó.
        assert "btn_next" not in str(rule)


def test_lien_thong_khong_khoa_theo_id():
    """id="next" của cổng liên thông DÙNG CHUNG mọi bước; chỉ bước cuối đổi nhãn "Hoàn thành"."""
    rule = portal_submit_rules()["lienthong.dichvucong.gov.vn"]
    assert "next" not in (rule.get("buttonIds") or [])
    assert "hoan thanh" in rule["buttonText"]


def test_luat_nhan_nut_giu_ca_id_lan_nhan():
    """id sinh từ nhãn (kt_ + slug) nên đổi nhãn là hỏng cả hai — phải có đủ hai lưới.
    Đã đối chiếu 15 snapshot cổng tư pháp: chỉ bước CUỐI mới có nút này."""
    rule = portal_submit_rules()["dichvucongnganhtuphap.moj.gov.vn"]
    assert "kt_gui-ho-so" in rule["buttonIds"]
    assert {"gui ho so", "nop ho so"} <= set(rule["buttonText"])
    # Nút "next" của các bước TRƯỚC không được lọt vào danh sách.
    assert "kt_buoc-tiep-theo-cho-ban-than" not in rule["buttonIds"]
    assert "xem-truoc-to-khai" not in rule["buttonIds"]
    assert "btn-next" not in str(rule)  # data-e2e dùng chung mọi bước → không được dựa vào


def test_traces_luu_khoa_ho_so_dung_CHUNG_hai_kenh():
    """Handfree ghi conversation_id, Auto Fill ghi dossierId — VÀO CÙNG MỘT TRƯỜNG `dossier_id`
    (= dossiers._id) để báo cáo chỉ có một đường nối, không phải rẽ theo kênh.

    `dossier_ids` (số nhiều) là thứ KHÁC: id tổng hợp của lượt tách hồ sơ, phục vụ cách đếm cũ.
    """
    import inspect
    from app.traces import repo as traces_repo
    params = inspect.signature(traces_repo.create_trace).parameters
    assert "dossier_id" in params
    assert "conversation_id" not in params  # không được đẻ trường riêng cho từng kênh
    assert "dossier_ids" in params          # cách đếm cũ vẫn còn, không bị đụng vào


# ── Đọc cho trang quản trị ────────────────────────────────────────────────────────────────
def test_serialize_tinh_thoi_gian_lam_ho_so():
    from app.dossiers.repo import _serialize
    t0 = datetime(2026, 9, 10, 9, 12, tzinfo=timezone.utc)
    t1 = datetime(2026, 9, 10, 9, 31, tzinfo=timezone.utc)
    out = _serialize({"_id": "d1", "started_at": t0, "submit_clicked_at": t1, "submit_count": 3})
    assert out["durationMs"] == 19 * 60 * 1000
    assert out["submitCount"] == 3
    # Hồ sơ làm dở: không có mốc nộp → không bịa ra thời lượng.
    assert _serialize({"_id": "d2", "started_at": t0})["durationMs"] is None
    # Đồng hồ lệch khiến mốc nộp TRƯỚC mốc bắt đầu → thà bỏ trống còn hơn báo số âm.
    assert _serialize({"_id": "d3", "started_at": t1, "submit_clicked_at": t0})["durationMs"] is None


def test_loc_danh_sach_theo_moc_BAT_DAU():
    """Lọc theo mốc nộp sẽ đánh rơi hồ sơ làm dở — mà đó chính là thứ cần nhìn."""
    from app.dossiers.repo import _build_query
    t0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
    q = _build_query(user_id=None, procedure=None, experience=None, submitted=None,
                     date_from=t0, date_to=None)
    assert "started_at" in q and "submit_clicked_at" not in q

    assert _build_query(user_id=None, procedure=None, experience=None, submitted=True,
                        date_from=None, date_to=None)["submit_clicked_at"] == {"$ne": None}
    assert _build_query(user_id=None, procedure=None, experience=None, submitted=False,
                        date_from=None, date_to=None)["submit_clicked_at"] is None


def test_api_ho_so_gac_CUNG_cua_voi_trace():
    """Tên công dân + nhật ký giấy tờ cùng hạng PII với trace → không được dùng
    require_dashboard (dep đó cho cả tài khoản phường vào)."""
    src = (Path(__file__).resolve().parents[3] / "app" / "dossiers" / "router.py").read_text("utf-8")
    # Kiểm theo CHỖ DÙNG chứ không theo văn bản: chú thích trong file có nhắc tên dep kia để
    # giải thích vì sao không dùng nó.
    assert "Depends(require_trace_reader)" in src
    assert "Depends(require_dashboard)" not in src


def test_duong_CU_cung_cham_moc_nop_cho_extension_ban_cho():
    """Bản extension đang chạy chưa bắt được cú bấm nút; không chấm mốc từ đường cũ
    (dò chữ "nộp hồ sơ thành công") thì mọi hồ sơ đều hiện "chưa nộp"."""
    conv = _conv(state="done", attach_done=True)
    _handle(conv, Intent("event", "submitted", {}))
    assert isinstance(conv.get("submit_clicked_at"), datetime)


def test_ban_MOI_khong_bi_dem_gap_doi():
    """Bản mới bắn CẢ HAI: submit_clicked (lúc bấm) rồi submitted (lúc thấy trang thành công).
    Đường cũ phải giữ nguyên mốc của cú bấm, gán đè là thành hai sự kiện cho một lần nộp."""
    conv = _conv(state="done", attach_done=True)
    _handle(conv, Intent("event", "submit_clicked", {"host": "h", "ref": "1"}))
    clicked = conv["submit_clicked_at"]
    _handle(conv, Intent("event", "submitted", {}))
    assert conv["submit_clicked_at"] == clicked
    assert conv["submit_clicked_source"] == "click"


def test_do_chu_TRUOC_roi_moi_bam_cung_khong_dem_gap_doi():
    """Chiều NGƯỢC lại — lỗ hổng thật: cổng hiện "nộp hồ sơ thành công" trước (đường dò chữ
    chấm mốc), rồi công dân bấm thêm một nút khớp luật ngay trên trang đó.

    Router ghi một sự kiện MỚI mỗi khi mốc đổi, nên đẩy mốc ở cú bấm thứ hai là một lần nộp
    bị đếm thành hai. Cú bấm vẫn là nguồn ƯU TIÊN, nhưng khi mốc sẵn có nói về CHÍNH lần nộp
    này thì chỉ nâng nhãn nguồn, không dời mốc."""
    conv = _conv(state="done", attach_done=True)
    _handle(conv, Intent("event", "submitted", {}))
    from_text = conv["submit_clicked_at"]
    assert conv["submit_clicked_source"] == "text"

    _handle(conv, Intent("event", "submit_clicked", {"host": "h", "ref": "1"}))
    assert conv["submit_clicked_at"] == from_text, "mốc đổi = router ghi thêm sự kiện thứ hai"
    assert conv["submit_clicked_source"] == "click", "cú bấm vẫn phải được ghi nhận là nguồn"


def test_bam_TRUOC_thi_cu_bam_quyet_dinh_moc():
    """Thứ tự thường gặp: bấm nút rồi cổng mới hiện trang thành công. Mốc phải là của cú bấm
    (sớm hơn, chính xác hơn), và ref/host của cổng phải được giữ."""
    conv = _conv(state="done", attach_done=True)
    _handle(conv, Intent("event", "submit_clicked", {"host": "dichvucong.quangninh.gov.vn", "ref": "145156"}))
    assert conv["submit_clicked_source"] == "click"
    assert conv["submit_dossier_ref"] == "145156"
    assert conv["submit_portal_host"] == "dichvucong.quangninh.gov.vn"


def test_moc_thoi_gian_tra_ve_PHAI_kem_offset_UTC():
    """Driver không bật tz_aware → Mongo trả datetime NAIVE. Trả thẳng ra API thì trình duyệt
    hiểu là giờ địa phương và hiển thị lệch 7 tiếng (đã gặp thật trên trang Hồ sơ)."""
    from app.dossiers.repo import _serialize
    naive = datetime(2026, 9, 10, 8, 3)  # đúng dạng Mongo trả về: naive, giá trị là UTC
    out = _serialize({
        "_id": "d1", "started_at": naive, "submit_clicked_at": naive,
        "closed_at": naive, "submit_events": [{"at": naive}],
    })
    for value in (out["startedAt"], out["submittedAt"], out["closedAt"], out["submitEvents"][0]["at"]):
        assert value.endswith("+00:00"), value
    # replace() chứ không astimezone(): giờ phải giữ nguyên 08:03, không bị dời theo múi máy chủ.
    assert out["startedAt"].startswith("2026-09-10T08:03:00")


def test_ten_thu_tuc_lay_TEN_THAT_theo_khoa_khong_dung_shortLabel():
    """Handfree có shortLabel riêng cho card chọn thủ tục ("Chứng thực chữ ký"); báo cáo phải
    là tên hành chính đầy đủ. Tra lúc ĐỌC nên dòng đã lưu nhãn ngắn cũng hiện đúng, khỏi migrate."""
    from app.dossiers.repo import _serialize
    from app.procedures.registry import get_procedure
    that = get_procedure("chung-thuc-chu-ky")["label"]
    out = _serialize({
        "_id": "d1", "procedure": "chung-thuc-chu-ky",
        "procedure_label": "Chứng thực chữ ký",  # nhãn NGẮN đã lỡ lưu
    })
    assert out["procedureLabel"] == that
    assert out["procedureLabel"] != "Chứng thực chữ ký"
    # Thủ tục đã gỡ khỏi registry → giữ nhãn đã lưu chứ không để trống.
    assert _serialize({"_id": "d2", "procedure": "khong-ton-tai",
                       "procedure_label": "Tên cũ"})["procedureLabel"] == "Tên cũ"


def test_hkd_nut_nop_la_INPUT_khong_phai_button():
    """HkdOnline (ASP.NET) render nút nộp bằng <input type="submit">, nhãn nằm ở value.
    Content script phải bắt được input, không chỉ button/a — nếu không mất trắng cổng này."""
    from pathlib import Path as _P
    rule = portal_submit_rules()["hokinhdoanh.dkkd.gov.vn"]
    assert rule["buttonIds"] == ["ctl00_C_BtnSave"]
    assert "nop ho so vao co quan dkkd" in rule["buttonText"]
    root = _P(__file__).resolve().parents[4]
    for ext in ("auto-fill-hcc-extension", "tro-ly-nguoi-dan-extension"):
        src = (root / ext / "content.js").read_text("utf-8")
        assert 'input[type="submit"]' in src, ext
        assert 'tagName === "INPUT" ? el.value' in src, ext
