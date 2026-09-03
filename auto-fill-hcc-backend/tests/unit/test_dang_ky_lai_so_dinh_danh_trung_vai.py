"""Tờ khai ghi NHẦM cùng một số CCCD cho cả con/cha/mẹ (người dân chép số của chính mình).

Số bị trùng vai KHÔNG định danh được ai → phải bỏ khỏi <con>/<cha>/<me>; nếu giữ lại thì
_validate_family_sections xoá trắng cả hai vai cha/mẹ ("trùng con" / "cha có giới tính Nữ")
và form mất sạch mục III + IV, dù hồ sơ có CCCD riêng của cha mẹ đọc được.
"""

from app.pipelines.khai_sinh_dang_ky_lai.process import reason


def _declaration(subject_id: str, mother_id: str, father_id: str) -> list[dict]:
    text = "\n".join([
        "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH",
        "Kính gửi: UBND xã Hiệp Hòa, tỉnh Bắc Ninh",
        "Họ, chữ đệm, tên người yêu cầu: Trần Thị Huệ",
        "Ngày, tháng, năm sinh: 31/12/1980",
        "Nơi cư trú: Thôn Sơn Quả, xã Hiệp Hòa, tỉnh Bắc Ninh",
        f"Giấy tờ tùy thân: CCCD/CC số {subject_id}, Cục CSQLHC về TTXH cấp ngày 25/8/2021",
        "Quan hệ với người được khai sinh: bản thân",
        "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:",
        "Họ, chữ đệm, tên: Trần Thị Huệ",
        "Ngày, tháng, năm sinh: 31/12/1980",
        "Giới tính: Nữ Dân tộc: Kinh Quốc tịch: Việt Nam",
        f"Giấy tờ tùy thân: CCCD/CC số {subject_id}, Cục CSQLHC về TTXH cấp ngày 25/8/2021",
        "Họ, chữ đệm, tên người mẹ: Nguyễn Thị Tuệ",
        "Năm sinh: 1960 Dân tộc: Kinh Quốc tịch: Việt Nam",
        "Nơi cư trú: Thôn Sơn Quả, xã Hiệp Hòa, tỉnh Bắc Ninh",
        f"Giấy tờ tùy thân: CCCD/CC số {mother_id}, Cục CSQLHC về TTXH cấp ngày 25/8/2021",
        "Họ, chữ đệm, tên người cha: Trần Văn Lành",
        "Năm sinh: 1956 Dân tộc: Kinh Quốc tịch: Việt Nam",
        "Nơi cư trú: Thôn Sơn Quả, xã Hiệp Hòa, tỉnh Bắc Ninh",
        f"Giấy tờ tùy thân: CCCD/CC số {father_id}, Cục CSQLHC về TTXH cấp ngày 17/12/2021",
    ])
    return [{"name": "to-khai.pdf", "text": text, "role": ""}]


def _role_section(tag: str, name: str, identity: str, birth: str, gender: str) -> str:
    return "\n".join([
        f"Họ tên: {name}",
        f"Số CCCD/CMND: {identity}",
        f"Ngày sinh: {birth}",
        f"Giới tính: {gender}",
        "Dân tộc: Kinh",
        "Quốc tịch: Việt Nam",
        "Trạng thái: còn sống",
        "Nguồn: cccd.pdf",
        f"Căn cứ phân vai: CCCD của {tag}",
    ])


def test_so_dinh_danh_trung_ca_ba_vai_thi_bi_bo_khoi_khoi_gia_dinh():
    roles = reason._declaration_roles(_declaration("024180006636", "024180006636", "024180006636"))

    assert set(roles) >= {"con", "me", "cha"}
    for tag in ("con", "me", "cha"):
        assert roles[tag]["id"] == "", tag
        assert "Số CCCD/CMND: Không xác định" in roles[tag]["section"], tag
    # Họ tên giữ nguyên để còn ghép được với CCCD thật theo tên.
    assert roles["me"]["name"] == "Nguyễn Thị Tuệ"
    assert roles["cha"]["name"] == "Trần Văn Lành"


def test_nguoi_yeu_cau_trung_con_van_giu_so_dinh_danh():
    """Người yêu cầu đồng thời là con là chuyện BÌNH THƯỜNG, không được coi là trùng vai.

    Chỉ số trùng giữa con/cha/mẹ mới là bằng chứng tờ khai ghi nhầm, nên <nguoi_yeu_cau>
    không được tính vào phép đếm — nếu tính, ca "tự đi làm cho mình" sẽ mất số của con.
    """
    roles = reason._declaration_roles(_declaration("024180006636", "024160009529", "024056008465"))

    assert roles["nguoi_yeu_cau"]["id"] == "024180006636"
    assert roles["con"]["id"] == "024180006636"
    assert roles["me"]["id"] == "024160009529"
    assert roles["cha"]["id"] == "024056008465"


def test_cha_me_khong_bi_xoa_khi_to_khai_ghi_nham_so_cua_con():
    """Ca thật (trace 6a98f655): tờ khai chép số của con sang cả mục cha lẫn mục mẹ."""
    documents = _declaration("024180006636", "024180006636", "024180006636")
    llm_sections = {
        "con": _role_section("con", "Trần Thị Huệ", "024180006636", "31/12/1980", "Nữ"),
        "me": _role_section("mẹ", "Nguyễn Thị Tuệ", "024160009529", "03/06/1960", "Nữ"),
        "cha": _role_section("cha", "Trần Văn Lành", "024056008465", "01/11/1956", "Nam"),
    }

    repaired = reason._validate_family_sections(
        reason._repair_family_from_declaration(llm_sections, documents)
    )

    assert reason._role_name(repaired["me"]) == "Nguyễn Thị Tuệ"
    assert reason._role_name(repaired["cha"]) == "Trần Văn Lành"
    assert reason._role_id(repaired["me"]) == "024160009529"
    assert reason._role_id(repaired["cha"]) == "024056008465"
