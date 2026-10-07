"""Hộ tịch trên trang nộp MỘT TRANG của Cổng DVC quốc gia (dichvucong.gov.vn/nop-ho-so).

Registry usage: ``"flowProfile": "tu-phap-moi"``. Bấm "Nộp trực tuyến" là vào thẳng trang có
cả form SurveyJS, bảng thành phần hồ sơ và ô "Hình thức nhận kết quả" — không có modal "Thông
tin chung" (bản thân / ủy quyền), không có bước chủ hồ sơ, không có thanh bước. Điều phối luồng
nằm ở ``chat/tu_phap_moi.py``.
"""

TU_PHAP_MOI_FLOW: dict = {
    "needsAgencySelect": True,
    "hasAttachmentStep": True,
    # Không có wizard: mọi việc trên cùng một trang nên không khai số bước.
    "singlePageDossier": True,
    "guidedSteps": {
        # Không bật luồng dẫn từng bước của wizard; chỉ dùng bộ khai cách nhận kết quả.
        "enabled": False,
        "submitLabel": "Lưu và nộp hồ sơ",
        # `label` phải đúng NGUYÊN VĂN option của ô "Hình thức nhận kết quả" (cc-select) —
        # FE khớp option theo nhãn đã fold dấu. Cổng chọn sẵn option đầu.
        # `needsInput`: chỉ bưu điện mọc khối "THÔNG TIN NHẬN KẾT QUẢ" (người nhận, điện thoại,
        # đơn vị vận chuyển, tỉnh, xã, địa chỉ); trợ lý chỉ kiểm tra, không điền hộ.
        "resultMethods": [
            {"key": "counter", "label": "Trả kết quả tại bộ phận tiếp nhận và trả kết quả",
             "icon": "🏢", "desc": "Nhận kết quả trực tiếp tại bộ phận một cửa.", "default": True},
            {"key": "postal", "label": "Trả kết quả qua đường bưu điện", "icon": "📮",
             "desc": "Bưu điện chuyển kết quả tới địa chỉ người nhận.", "needsInput": True},
            {"key": "online", "label": "Trả kết quả trên môi trường mạng (kết quả có ký số)",
             "icon": "🌐", "desc": "Nhận bản điện tử có ký số trên hệ thống."},
        ],
    },
}
