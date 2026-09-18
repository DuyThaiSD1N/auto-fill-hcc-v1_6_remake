"""Planner đính kèm CTV (kênh Handfree) — thuần tất định, không OCR/LLM."""
from app.pipelines.chung_thuc_chu_ky_nguoi_dich_ctv.attach import plan
from app.pipelines.chung_thuc_chu_ky_nguoi_dich_ctv.attach.planner import COMPONENT_NAME
from app.process.schemas import FileItem

PROCEDURE = "chung-thuc-chu-ky-nguoi-dich-ctv"


def _files(count: int) -> list[FileItem]:
    return [
        FileItem(name=f"ban-dich-{i + 1}.pdf", type="application/pdf", dataUrl="", role="")
        for i in range(count)
    ]


async def test_gop_ho_so_tep_dau_vao_dong_co_dinh_cac_tep_sau_them_thanh_phan():
    result = await plan(_files(3), {"splitMode": False})
    items = result["attachments"]

    assert len(items) == 3
    # Tệp đầu đi vào dòng cố định STT1 có sẵn trên cổng.
    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert items[0]["componentName"] == COMPONENT_NAME
    assert items[0]["needsAddComponent"] is False
    # Các tệp sau thêm thành phần mới, KHÔNG dùng componentIndex.
    assert [i["target"] for i in items[1:]] == ["new", "new"]
    assert all(i["needsAddComponent"] is True for i in items[1:])
    assert all(i["componentIndex"] is None for i in items[1:])


async def test_gop_ho_so_ten_thanh_phan_khong_bao_gio_trung_nhau():
    """Cổng không cho hai thành phần trùng tên; backend phải đánh số sẵn, không để frontend sửa."""
    items = (await plan(_files(4), {"splitMode": False}))["attachments"]
    names = [i["componentName"] for i in items]

    assert len(set(names)) == len(names)
    assert names[1].endswith(" 2")
    assert names[2].endswith(" 3")
    assert names[3].endswith(" 4")


async def test_tach_ho_so_moi_ban_dich_deu_vao_dong_co_dinh_cua_ho_so_rieng():
    """Tách: frontend cắt plan thành mỗi tệp một hồ sơ nên KHÔNG tệp nào phải thêm thành phần."""
    items = (await plan(_files(3), {"splitMode": True}))["attachments"]

    assert all(i["target"] == "existing" for i in items)
    assert all(i["componentIndex"] == 1 for i in items)
    assert all(i["needsAddComponent"] is False for i in items)
    assert all(i["componentName"] == COMPONENT_NAME for i in items)


async def test_mot_tep_thi_gop_hay_tach_deu_ra_cung_ket_qua():
    gop = (await plan(_files(1), {"splitMode": False}))["attachments"]
    tach = (await plan(_files(1), {"splitMode": True}))["attachments"]

    assert gop == tach
    assert gop[0]["target"] == "existing"


async def test_khong_co_tep_thi_tra_plan_rong_khong_no():
    result = await plan([], {})

    assert result["attachments"] == []
    assert result["errors"] == []
