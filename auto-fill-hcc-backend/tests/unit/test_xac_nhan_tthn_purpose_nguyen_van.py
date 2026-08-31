"""Mục đích sử dụng giấy XNTTHN phải giữ NGUYÊN VĂN, không cắt cụt.

Luật cũ trong prompt bảo "BỎ phần chú thích trong ngoặc", agent áp luôn cho cả mệnh đề nối bằng dấu
phẩy nên "Giao dịch nhà, đất, không có giá trị sử dụng để đăng ký kết hôn" bị rút còn "Giao dịch
nhà, đất". Mệnh đề đó là nội dung phải gõ vào ô "Nhập mục đích(*)" của cổng, thiếu là hồ sơ sai.
"""

from app.pipelines.xac_nhan_tthn.process.mapper import enrich
from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES

_MUC_DICH = "Giao dịch nhà, đất, không có giá trị sử dụng để đăng ký kết hôn"


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


def test_mapper_khong_dung_cham_vao_muc_dich():
    """Mapper chỉ chuyển tiếp — mọi cắt xén nếu có đều đến từ prompt."""
    result = _by_name(enrich([
        {"name": "Cccd_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "Cccd_SoDinhDanh", "value": "001066023420"},
        {"name": "Purpose", "value": _MUC_DICH},
    ]))

    assert result["nhapmucdichkhac"]["value"] == _MUC_DICH


def test_prompt_cam_cat_ngan_muc_dich():
    prompt = EXTRA_RULES

    assert "TUYỆT ĐỐI KHÔNG cắt ngắn mục đích" in prompt
    assert "không có giá trị sử dụng để đăng ký kết hôn" in prompt
    # Luật cũ đã gây lỗi: không được để nó quay lại.
    assert "BỎ phần chú thích trong ngoặc" not in prompt
