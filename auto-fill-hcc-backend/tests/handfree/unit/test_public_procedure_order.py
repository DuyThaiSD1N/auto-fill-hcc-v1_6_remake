from app.channels.handfree.procedure_registry import public_list


def test_public_procedure_cards_put_common_civil_status_first_and_certification_last():
    keys = [procedure["key"] for procedure in public_list()]

    # Chứng thực bản sao dùng nhiều tại quầy → vị trí 3 (yêu cầu 09/09/2026);
    # chứng thực chữ ký vẫn chốt cuối danh sách.
    assert keys[:7] == [
        "ket-hon",
        "khai-sinh-dang-ky",
        "chung-thuc-ban-sao",
        "trich-luc-ks",
        "xac-nhan-tinh-trang-hon-nhan",
        "khai-sinh-dang-ky-lai",
        "khai-tu",
    ]
    assert keys[-1] == "chung-thuc-chu-ky"
    assert len(keys) == len(set(keys))
