"""Ảnh HEIC (iPhone) đổi sang JPG: hàm đổi, lúc nhận tệp vào phiên tải ảnh và API cho panel Auto Fill."""
import base64
import io
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.image_convert import router as convert_router
from app.services import heic
from app.upload_session import router as upload_router
from app.upload_session import store


def _heic_bytes(size=(40, 20), orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, (200, 10, 10))
    out = io.BytesIO()
    kwargs = {}
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        kwargs["exif"] = exif.tobytes()
    image.save(out, format="HEIF", **kwargs)
    return out.getvalue()


def test_nhan_heic_theo_byte_dau_khong_theo_ten():
    data = _heic_bytes()
    assert heic.is_heic(data, "anh.jpg", "image/jpeg")
    assert not heic.is_heic(b"%PDF-1.7 xxxxxxxx", "anh.heic", "image/heic")
    assert heic.is_heic(None, "IMG_0001.HEIC", "")


def test_doi_sang_jpeg_va_xoay_theo_exif():
    jpeg = heic.to_jpeg(_heic_bytes((40, 20), orientation=6))  # 6 = xoay 90° khi hiển thị
    with Image.open(io.BytesIO(jpeg)) as image:
        assert image.format == "JPEG"
        assert image.size == (20, 40)


def test_tep_khong_phai_heic_giu_nguyen(tmp_path):
    path = tmp_path / "a.pdf"
    path.write_bytes(b"%PDF-1.7 noi dung")
    assert heic.convert_file_if_heic(path, "a.pdf", "application/pdf", 17) == ("a.pdf", "application/pdf", 17)
    assert path.read_bytes() == b"%PDF-1.7 noi dung"


def test_heic_hong_giu_tep_goc(tmp_path):
    path = tmp_path / "a.heic"
    broken = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 20
    path.write_bytes(broken)
    assert heic.convert_file_if_heic(path, "a.heic", "image/heic", len(broken))[0] == "a.heic"
    assert path.read_bytes() == broken


@pytest.fixture(autouse=True)
def _secure_capability_secret(monkeypatch):
    monkeypatch.setattr(upload_router.settings, "upload_capability_secret", "ab" * 32)


async def test_phien_tai_anh_luu_heic_thanh_jpg(monkeypatch, tmp_path):
    sess = {"_id": "HS-HEIC", "experience": "autofill", "owner_user_id": "u1", "files": []}
    monkeypatch.setattr(upload_router.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(store, "append_files_with_limit",
                        AsyncMock(side_effect=lambda _sid, metas, _limit: {**sess, "files": metas}))
    monkeypatch.setattr(upload_router, "broadcast", AsyncMock())

    result = await upload_router.upload_files(
        sess["_id"], [UploadFile(filename="IMG_0001.HEIC", file=io.BytesIO(_heic_bytes()))], "", sess)

    meta = result["accepted"][0]
    assert meta["name"] == "IMG_0001.jpg"
    assert meta["type"] == "image/jpeg"
    saved = store.read_file_bytes(sess["_id"], meta["fid"])
    assert saved[:2] == b"\xff\xd8" and meta["size"] == len(saved)


async def test_api_doi_heic_cho_panel():
    response = await convert_router.convert_image(
        UploadFile(filename="IMG_0002.heic", file=io.BytesIO(_heic_bytes())), {"_id": "u1"})
    assert response["name"] == "IMG_0002.jpg" and response["type"] == "image/jpeg"
    assert base64.b64decode(response["dataUrl"].split(",", 1)[1])[:2] == b"\xff\xd8"


async def test_api_tu_choi_tep_khong_phai_heic():
    with pytest.raises(HTTPException) as exc:
        await convert_router.convert_image(UploadFile(filename="a.pdf", file=io.BytesIO(b"%PDF-1.7 x" * 3)),
                                           {"_id": "u1"})
    assert exc.value.status_code == 400
