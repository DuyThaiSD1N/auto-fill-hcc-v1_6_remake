"""Kết hôn có yếu tố nước ngoài: mapper KHÔNG mặc định VN + bên nước ngoài đi nhánh riêng;
attach route đúng ô cố định STT2-6; registry entry bản tro-ly."""

import json

from app.pipelines.ket_hon_nuoc_ngoai.attach import planner as khnn_attach
from app.pipelines.ket_hon_nuoc_ngoai.process import mapper
from app.pipelines.ket_hon_nuoc_ngoai.process.mapper import FOREIGN_DOC_TYPE
from app.process.schemas import FileItem


def _fields(d):
    return [{"name": k, "value": v} for k, v in d.items()]


def _by_name(out):
    return {f["name"]: f for f in out}


def test_mapper_viet_va_nuoc_ngoai():
    out = _by_name(mapper.enrich(_fields({
        # Nam: người Việt (CCCD Cục Cảnh sát).
        "CccdNam_HoTen": "TRẦN VĂN A",
        "CccdNam_SoDinhDanh": "040203015844",
        "CccdNam_NgayCap": "02/07/2021",
        "CccdNam_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "CccdNam_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Xã Hợp Thành", "diaChi": "Xóm 1"},
        # Nữ: người Trung Quốc (chứng minh thư nước ngoài).
        "CccdNu_HoTen": "PHONG THỊ MỸ",
        "CccdNu_SoDinhDanh": "532524200001",
        "CccdNu_QuocTich": "Trung Quốc",
        "CccdNu_TenGiayTo": "Chứng minh thư",
        "CccdNu_NoiCap": "Cục công an huyện Nguyên Dương",
        "CccdNu_NoiCuTru": {"quocGia": "Trung Quốc", "diaChi": "Thôn Ma Lật Trại, trấn Nguyên Dương, Vân Nam"},
        "CccdNu_TinhTrangHonNhan": "chua_ket_hon",
    })))

    # Bên nam (VN): nhãn option mới theo nơi cấp, cư trú trong nước.
    assert out["LoaiGiayToDinhDanh_BenNam"]["value"] == "Thẻ căn cước công dân"
    assert out["QuocTichBenNam"]["value"] == "Việt Nam"
    assert out["NoiCuTru_BenNam"]["value"] == "1"
    assert out["NoiCuTru_BenNam_TrongNuoc"]["value"]["xa"] == "Hợp Thành"

    # Bên nữ (nước ngoài): KHÔNG mặc định VN — loại "Giấy tờ khác...", radio cư trú "2".
    assert out["LoaiGiayToDinhDanh_BenNu"]["value"] == FOREIGN_DOC_TYPE
    # Ô tên giấy tờ trên form thật là TenGiayTo_* (x-select-area) — không phải NhapTenGiayTo.
    assert out["TenGiayTo_BenNu"]["value"] == "Chứng minh thư"
    assert out["TenGiayTo_BenNu"]["comp"] == "x-select-area"
    assert "NhapTenGiayTo_BenNu" not in out
    assert out["QuocTichBenNu"]["value"] == "Trung Quốc"
    assert out["NoiCapDD_BenNu"]["value"] == "Cục công an huyện Nguyên Dương"  # giữ nguyên, không chuẩn hoá VN
    assert out["NoiCuTru_BenNu"]["value"] == "2"
    nn = out["NoiCuTru_BenNu_NuocNgoai"]["value"]
    assert nn["quocGia"] == "Trung Quốc" and "Ma Lật Trại" in nn["diaChi"]

    # Tình trạng hôn nhân "chưa kết hôn" → suy số lần kết hôn = 1 (widget x-input-number).
    assert out["LoaiTinhTrangHonNhan_BenNu"]["value"] == "Hiện tại chưa đăng ký kết hôn với ai"
    assert out["SoLanKetHon_BenNu"]["value"] == "1"
    assert out["SoLanKetHon_BenNu"]["comp"] == "x-input-number"

    # Không tác động radio "Loại đăng ký"; chỉ giữ mặc định không cấp bản sao.
    assert "loaiDangKy" not in out
    assert out["CapBanSao"]["value"] == "NO" and out["CapBanSao"].get("default") is True


def test_mapper_drop_dang_co_vo_chong():
    """LLM lỡ bịa 'đang có vợ/chồng' → DROP tất định (người đi đăng ký kết hôn luôn độc thân)."""
    out = _by_name(mapper.enrich(_fields({
        "CccdNam_HoTen": "TRẦN VĂN A",
        "CccdNam_TinhTrangHonNhan": "dang_co_vo_chong",
    })))
    assert "LoaiTinhTrangHonNhan_BenNam" not in out
    assert "SoLanKetHon_BenNam" not in out


async def test_attach_fixed_slots(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "kham.pdf", "text": "Giấy khám sức khỏe tâm thần"},
            {"name": "xnhn.pdf", "text": "Giấy xác nhận tình trạng hôn nhân"},
            {"name": "passport.pdf", "text": "PASSPORT"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "medical"},
            {"index": 1, "type": "marital_foreign"},
            {"index": 2, "type": "passport_foreign"},
            {"index": 3, "type": "identity_vn"},
        ]})

    monkeypatch.setattr(khnn_attach.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khnn_attach.client, "chat", fake_chat)

    files = [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")
             for n in ("kham.pdf", "xnhn.pdf", "passport.pdf", "cccd.pdf")]
    res = await khnn_attach.plan(files, {}, None)
    items = res["attachments"]

    assert items[0]["target"] == "existing" and items[0]["componentIndex"] == 2
    assert "tổ chức y tế" in items[0]["componentName"]
    assert items[1]["componentIndex"] == 3
    assert "tình trạng hôn nhân của người nước ngoài" in items[1]["componentName"]
    assert items[2]["componentIndex"] == 4 and "hộ chiếu" in items[2]["componentName"]
    assert items[3]["target"] == "new" and items[3]["documentName"] == "Căn cước công dân"


def test_registry_ket_hon_nuoc_ngoai_entry():
    from app.pipelines.ket_hon_nuoc_ngoai import process as agent
    from app.channels.handfree.procedure_registry import get_pipeline, get_procedure

    proc = get_procedure("ket-hon-nuoc-ngoai")
    assert get_pipeline("ket-hon-nuoc-ngoai") is agent.run
    assert not proc.get("hiddenFromList")  # đã đẩy lên card chọn thủ tục (2026-08-13)
    assert proc["needsAgencySelect"] is True
    assert proc["keKhaiUrl"].endswith("019d2bfd-8e13-728a-a0cd-635811d8432e")
    docs = {r["key"]: r for r in proc["requiredDocs"]}
    assert set(docs) == {"cccd_nam", "cccd_nu", "khac"}
    assert docs["khac"].get("optional") is True
