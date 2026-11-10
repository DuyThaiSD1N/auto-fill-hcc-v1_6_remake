"""Tờ khai bản giấy (Mẫu số 1) của luồng hỏi đáp thành lập hộ kinh doanh không giấy tờ — dữ liệu giả."""
import io

import pytest
from docx import Document

from app.channels.handfree.chat import hkd_tro_ly as hkd
from app.channels.handfree.chat import pipeline_runner, router
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.hkd_tro_ly import to_khai
from app.channels.handfree.chat.intents import Intent

PROC = {"key": "dang-ky-kinh-doanh", "businessWorkflow": "create"}


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    async def no_user(conv, sess):
        return None
    monkeypatch.setattr(pipeline_runner, "_load_owner_user", no_user)


async def _conv(docx=True, mode="khong_giay"):
    caps = {hkd.CAPABILITY: True, hkd.PREPARE_CAPABILITY: True, **({hkd.DOCX_CAPABILITY: True} if docx else {})}
    conv = {"_id": "c-docx", "procedure_key": "dang-ky-kinh-doanh", "client_capabilities": caps, "lang": "vi", "consent": {"accepted": True},
            "location": {"province": "Tỉnh Mẫu", "ward": "Phường Mẫu Một"}}
    conv["hkd"] = await hkd._base_state(conv, mode)
    conv["hkd"]["values"].update(
        dia_chi_kd={"tinh": "Tỉnh Mẫu", "xa": "Mẫu Một", "diaChi": "Số 1 đường Thử", "quocGia": "Việt Nam"},
        dien_thoai="0900000000", ten_ho="Thử Nghiệm", von=50000000, noi_o="giong")
    return conv


def _text(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            parts += [c.text for c in row.cells]
    return "\n".join(parts)


def test_so_tien_bang_chu():
    assert to_khai.so_thanh_chu(100000000) == "Một trăm triệu đồng"
    assert to_khai.so_thanh_chu(1250000) == "Một triệu hai trăm năm mươi nghìn đồng"
    assert to_khai.so_thanh_chu(21000000) == "Hai mươi mốt triệu đồng"
    assert to_khai.so_thanh_chu(215000000) == "Hai trăm mười lăm triệu đồng"


async def test_chu_ho_la_nguoi_dang_nhap_lay_nhan_than_extension_doc_lai_sau_sao_chep():
    conv = await _conv()
    st = conv["hkd"]
    st["values"].update(chu_ho_la_ban=True, chu_the="ca_nhan")
    st.update(block=hkd._blocks(st).index("chu-ho-kinh-doanh"), phase="copy")
    await hkd.handle(conv, PROC, Intent("event", "hkd_copied", {
        "page": "chu-ho-kinh-doanh", "copied": True,
        "owner": {"hoTen": "Người Mẫu", "ngaySinh": "01/02/1990", "gioiTinh": "Nam", "soDinhDanh": "000000000001"}}))
    text = _text(to_khai.to_docx(hkd.to_khai_data(conv)))
    assert "Tôi là (ghi họ tên bằng chữ in hoa): NGƯỜI MẪU" in text
    assert "000000000001" in text and "01/02/1990" in text
    assert "Kính gửi: Phòng Kinh tế, Hạ tầng và Đô thị Phường Mẫu Một" in text
    assert "HỘ KINH DOANH THỬ NGHIỆM" in text and "50.000.000 (Năm mươi triệu đồng)" in text
    assert "☒ Cá nhân" in text


async def test_o_khong_co_du_lieu_in_dong_cham_va_khong_tu_chep_dien_thoai_email():
    conv = await _conv()
    data = hkd.to_khai_data(conv)
    text = _text(to_khai.to_docx(data))
    assert "Điện thoại (nếu có): ...................." in text, "điện thoại chủ hộ không lấy từ điện thoại hộ"
    assert "Giới tính: ......" in text and "Tên hộ kinh doanh viết tắt (nếu có): ...." in text
    assert data.thueDiaChi is None, "địa chỉ thuế chỉ kê khai khi khác trụ sở"


async def test_xa_dung_phong_kinh_te_va_ho_gia_dinh_ke_ca_chu_ho_trong_bang_thanh_vien():
    conv = await _conv()
    conv["location"]["ward"] = "Xã Mẫu Hai"
    st = conv["hkd"]
    st["values"].update(chu_ho_ho_ten="Chủ Hộ Mẫu", chu_the="ho_gia_dinh")
    st["members"] = [{"tv_ho_ten": "Thành Viên Mẫu", "tv_gioi_tinh": "Nữ", "tv_ngay_sinh": "03/04/1995",
                      "tv_so_dinh_danh": "000000000002", "tv_noi_o": "giong"}]
    data = hkd.to_khai_data(conv)
    assert data.kinhGui == "Phòng Kinh tế Xã Mẫu Hai"
    text = _text(to_khai.to_docx(data))
    assert text.index("Chủ Hộ Mẫu") < text.index("Thành Viên Mẫu") and "☒ Các thành viên hộ gia đình" in text


async def test_nut_tai_to_khai_chi_khi_extension_khai_co_va_luong_khong_giay():
    for docx, mode, want in ((True, "khong_giay", True), (False, "khong_giay", False), (True, "bo_sung", False)):
        conv = await _conv(docx, mode)
        r = hkd._finish(conv, ("", ""))
        assert (hkd.DOCX_SEND in [c["send"] for c in r.chips]) is want, (docx, mode)


async def test_bam_tai_to_khai_tra_lenh_tai_file_va_giu_nut_cua_buoc():
    conv = await _conv()
    hkd._finish(conv, ("", ""))
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_docx"))
    action = r.actions[0]
    assert action["type"] == "download_file" and action["path"].endswith("/conversations/c-docx/hkd-to-khai.docx")
    assert [c["send"] for c in r.chips] == ["__action:hkd_prepare", hkd.ATTACH_DOCS_SEND, hkd.DOCX_SEND]
    hkd._done(conv, ("", ""))
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_docx"))
    assert r.actions and r.actions[0]["type"] == "download_file", "hội thoại xong vẫn tải được"
    assert vi.HKD_DOCX_READY["md"] == r.display_md


async def test_duong_tai_chi_cho_hoi_thoai_hkd_khong_giay(monkeypatch):
    conv = await _conv()

    async def owned(conv_id, user):
        return conv
    monkeypatch.setattr(router.access, "get_owned_conversation", owned)
    res = await router.hkd_to_khai_docx("c-docx", user={"id": "u1"})
    assert res.media_type.endswith("wordprocessingml.document") and res.body[:2] == b"PK"
    conv["hkd"]["mode"] = "bo_sung"
    with pytest.raises(Exception):
        await router.hkd_to_khai_docx("c-docx", user={"id": "u1"})


async def test_dinh_kem_giay_to_sau_khi_tai_to_khai_chi_lap_ke_hoach_dinh_roi_ve_chuan_bi(monkeypatch):
    from app.channels.handfree.chat import flow

    conv = await _conv()
    st = conv["hkd"]
    conv["state"] = "filling"
    hkd._finish(conv, ("", ""))
    assert hkd.ATTACH_DOCS_SEND not in [c["send"] for c in hkd._phase_chips(conv)], "chưa tải tờ khai thì chưa có nút"
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_docx"))
    assert [c["send"] for c in r.chips] == ["__action:hkd_prepare", hkd.ATTACH_DOCS_SEND, hkd.DOCX_SEND]

    # Bấm "Đính kèm giấy tờ" → bước chọn cách gửi như luồng thường.
    r = await hkd.handle(conv, PROC, Intent("action", "hkd_attach_docs"))
    assert conv["state"] == "ask_doc_method" and r.cards and r.cards[0]["kind"] == "doc_options"
    assert flow._docs_done_label_for_conv(conv) == vi.HKD_ATTACH_DOCS_DONE_LABEL

    # Chốt giấy tờ → chỉ lập kế hoạch đính kèm (không đọc giấy để điền lại).
    spawned = []

    async def two_files(_sid):
        return {"received": 2, "total": 2, "files_count": 2}
    monkeypatch.setattr(flow.upload_service, "progress_of", two_files)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: (spawned.append(coro.__qualname__), coro.close()))
    conv["upload_session_id"] = "sid-1"
    r = await flow._docs_complete(conv, {})
    assert spawned == ["run_hkd_attach"] and conv["pipeline_status"] == "hkd_attaching"
    assert "Đã nhận **2 tệp**" in r.display_md
    assert not hkd.needs_review(conv, PROC), "không được khởi động vòng bổ sung theo giấy"

    # Phân loại xong → lưu lại khối cuối kèm tệp.
    conv.update(pipeline_status="hkd_attach_ready", attach_plan=[{"fileIndex": 0, "fileName": "a.pdf"},
                                                                  {"fileIndex": 1, "fileName": "b.pdf"}],
                attach_plan_fids=["f1", "f2"])
    r = await hkd.handle(conv, PROC, Intent("event", "business_ready"))
    save = next(a for a in r.actions if a["type"] == "start_business_registration")
    assert len(save["attachments"]) == 2 and save["session_id"] == "sid-1"
    assert save["businessFlow"]["pageOrder"] == [hkd._blocks(st)[-1]]

    # Cổng báo xong → về bước Chuẩn bị, giữ nút đính thêm / tải tờ khai.
    r = await hkd.handle(conv, PROC, Intent("action", "business_report", {"ok": True, "attached": 2}))
    assert st["phase"] == "ready_prepare" and conv["state"] == "filling" and "Đã đính **2 tệp**" in r.display_md
    assert [c["send"] for c in r.chips] == ["__action:hkd_prepare", hkd.ATTACH_DOCS_SEND, hkd.DOCX_SEND]
    assert conv["business_attached_fids"] == ["f1", "f2"], "đính thêm lần sau chỉ đính tệp mới"


async def test_sau_khi_chuan_bi_xong_khong_con_nut_dinh_kem():
    conv = await _conv()
    st = conv["hkd"]
    st.update(docx_downloaded=True, phase="ready_submit", submit_on=True)
    assert hkd.ATTACH_DOCS_SEND not in [c["send"] for c in hkd._phase_chips(conv)]
