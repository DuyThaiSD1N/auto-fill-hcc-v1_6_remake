"""Metadata và thứ tự thủ tục chỉ dành cho kênh Handfree.

Core process/attach luôn lấy từ ``app.procedures.registry``. File này được port từ
registry Handfree cũ để giữ nguyên card, flow profile và checklist, nhưng không còn
sở hữu bản sao pipeline nghiệp vụ.
"""
from app.channels.handfree.owner_info import run as tu_phap_owner_info
from app.channels.handfree.flow_profiles import resolve_flow_profile
from app.procedures import agency_plans
from app.procedures import portal_submit as core_portal_submit
from app.procedures import registry as core_registry

PROCEDURES: list[dict] = [
    {
        "key": "khai-sinh-dang-ky",
        # Liên thông nằm trên cổng riêng (lienthong.dichvucong.gov.vn), không có heading chuẩn
        # → nhận diện THEO URL. Cổng chạy song song hai mã cho cùng biểu mẫu: 2.000986 (bản cũ) và
        # 2.000987 (bản đang dùng, có thêm bước cấp thẻ căn cước). Giữ CẢ HAI để hồ sơ mở bằng link
        # cũ vẫn nhận ra được. Giống hệt app/procedures/registry.py — sửa một bên phải sửa cả bên kia.
        "detect": {
            "urlIncludes": [
                "lienthong.dichvucong.gov.vn/#/ke-khai/2.000986",
                "lienthong.dichvucong.gov.vn/#/ke-khai/2.000987",
            ],
            "headingDisabled": True,
        },
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần (cổng Angular — srcHostFor theo formcontrolname)
        "label": (
            "Liên thông thủ tục hành chính về đăng ký khai sinh, đăng ký thường trú, "
            "cấp thẻ bảo hiểm y tế cho trẻ em dưới 6 tuổi"
        ),
        # Metadata cho card chọn thủ tục + action navigate của trợ lý (docs/03).
        "shortLabel": "Đăng ký Khai sinh (liên thông)",
        "subtitle": "Khai sinh + thường trú + BHYT cho trẻ dưới 6 tuổi",
        "icon": "👶",
        "keKhaiUrl": "https://lienthong.dichvucong.gov.vn/#/ke-khai/2.000987",
        # Checklist phiên QR (docs/05): classify.py route ảnh vào đúng ô theo OCR.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd_cha", "name": "Căn cước công dân cha", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "cccd_me", "name": "Căn cước công dân mẹ", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "chung_sinh", "name": "Giấy chứng sinh", "icon": "📃",
             "sides": 1, "repeatable": True},
            # Thay thế CCCD cha/mẹ khi không có: hệ thống lấy thông tin cha/mẹ từ giấy kết hôn.
            {"key": "ket_hon_cha_me", "name": "Giấy chứng nhận kết hôn của cha mẹ",
             "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Các giấy tờ khác liên quan",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        # Form mới (Angular) — chế độ agent: không gắn role, BE tự suy luận cha/mẹ/con.
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        # Bước 01 "Chọn cơ quan thực hiện" (Angular Material) — trợ lý điền hộ. Viết theo ĐÚNG
        # hợp đồng fields {name, comp, value} để FE dùng lại engine fillFormAngular (không thêm
        # logic fill mới). {province}/{ward} được flow thay bằng nơi ở của phiên trước khi gửi.
        # Chỉ điền khối khai sinh + 2 select "trường hợp" + giữ tick "Cùng địa bàn" (khối thường
        # trú tự mirror + khoá theo khối khai sinh). Ô "Cơ quan thực hiện" readonly tự suy — bỏ.
        "agencyFillPlan": agency_plans.LIEN_THONG_KHAI_SINH,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân cha.\n"
            "2. Căn cước công dân mẹ.\n"
            "3. Giấy chứng sinh.\n"
            "4. Giấy chứng nhận kết hôn của cha mẹ (nếu có).\n"
            "5. Các giấy tờ khác liên quan (nếu có).\n"
            "Bước 3: hệ thống có thể đính giấy chứng sinh vào thành phần hồ sơ có sẵn, "
            "hoặc thêm thành phần CCCD bố/mẹ nếu cần."
        ),
    },
    {
        # Đăng ký khai sinh ĐƠN LẺ (chỉ khai sinh) — KHÁC "khai-sinh-dang-ky" ở trên là liên
        # thông (khai sinh + thường trú + BHYT trên cổng lienthong.dichvucong.gov.vn Angular).
        # Thủ tục này chạy trên cổng React mới của Bộ Tư pháp, cùng wizard với kết hôn/khai tử.
        "key": "khai-sinh-dang-ky-thuong",
        "detect": {"urlIncludes": ["maThuTuc=1.001193"]},
        "label": "Thủ tục đăng ký khai sinh",
        "shortLabel": "Đăng ký Khai sinh",
        "subtitle": "Chỉ đăng ký khai sinh (không kèm thường trú, BHYT)",
        "icon": "👶",
        "flowProfile": "tu-phap",
        "supportsSplitDocuments": True,
        # URL kê khai đã xác minh trong ke_khai_links.json (mã TTHC 1.001193).
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fe0-70ac-b9d6-5e9e20d6eef7",
        # Mỗi slot tính theo TỆP, không theo mặt; checklist tự hiện "Đã nhận X tệp".
        "hideRepeatableHint": True,
        "requiredDocs": [
            # Gộp CCCD cha/mẹ/con vào MỘT slot (mode agent tự suy vai theo OCR, không cần
            # tách ô theo cha/mẹ); classify dồn mọi CCCD vào đây như khai tử/trích lục.
            {"key": "cccd", "name": "Căn cước công dân của cha, mẹ, con", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "chung_sinh", "name": "Giấy chứng sinh", "icon": "📃",
             "sides": 1, "repeatable": True},
            # Thay thế CCCD cha/mẹ khi không có: hệ thống lấy thông tin cha/mẹ từ giấy kết hôn.
            {"key": "ket_hon_cha_me", "name": "Giấy chứng nhận kết hôn của cha mẹ",
             "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Các giấy tờ khác liên quan",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân cha (cả 2 mặt).\n"
            "2. Căn cước công dân mẹ (cả 2 mặt).\n"
            "3. Giấy chứng sinh của con.\n"
            "4. Giấy chứng nhận kết hôn của cha mẹ (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt cha/mẹ/con theo nội dung.\n"
            "Bước 3: hệ thống có thể đính giấy chứng sinh vào thành phần hồ sơ có sẵn, "
            "hoặc thêm thành phần CCCD bố/mẹ nếu cần."
        ),
    },
    {
        "key": "ket-hon",
        "detect": {"urlIncludes": ["maThuTuc=1.000894"]},
        "label": "Thủ tục đăng ký kết hôn",
        "shortLabel": "Đăng ký Kết hôn",
        "subtitle": "Thủ tục đăng ký kết hôn trong nước",
        "icon": "❤️",
        "flowProfile": "tu-phap",
        "supportsSplitDocuments": True,
        # Cổng React MỚI dichvucong.gov.vn: trang chi tiết thủ tục → khối "Chọn cơ quan
        # thực hiện" (tỉnh + xã) → Đồng ý → kê khai. Engine: content/portal-dvc.js.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fac-7489-b53b-a15eb239a6fe",
        # Mỗi slot tính theo TỆP, không theo mặt: repeatable giữ dòng luôn mở và hiện
        # "Đã nhận X tệp". CCCD hai bên cần tối thiểu 1 tệp/bên; tờ khai/khác là tùy chọn.
        # Không đọc thành tiếng "không giới hạn số lượng" vì UI đã thể hiện bằng bộ đếm tệp.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd_nam", "name": "Căn cước công dân bên nam", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "cccd_nu", "name": "Căn cước công dân bên nữ", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai đăng ký kết hôn (nếu có)", "icon": "📄",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ chứng minh tình trạng hôn nhân hoặc giấy tờ khác",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần: process chụp tokens+bbox, phơi qua /api/v1/review
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân của bên nam.\n"
            "2. Căn cước công dân của bên nữ.\n"
            "Không cần chọn trước giấy tờ là của chồng hay vợ; hệ thống tự phân biệt theo giới tính "
            "trên căn cước công dân.\n"
            "Bước 3: hệ thống có thể đính kèm căn cước công dân bên nam/bên nữ vào thành phần hồ sơ mới."
        ),
    },
    {
        "key": "dang-ky-giam-ho",
        "detect": {"textIncludes": ["Thủ tục đăng ký giám hộ"], "headingDisabled": True},
        "label": "Thủ tục đăng ký giám hộ",
        "shortLabel": "Đăng ký Giám hộ",
        "subtitle": "Đăng ký giám hộ cho người được giám hộ",
        "icon": "🤝",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-671b-75fa-82fb-8ad05a37f638",
        "mode": "agent",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đăng ký giám hộ.\n"
            "2. CCCD/CMND của người yêu cầu và người giám hộ.\n"
            "3. Giấy khai sinh/giấy tờ định danh của người được giám hộ.\n"
            "4. Nếu có: trích xuất CSDL dân cư hoặc giấy tờ chứng minh điều kiện giám hộ."
            "\nBước 3: tờ khai bản giấy thêm thành phần hồ sơ mới; văn bản cử người giám hộ vào STT 2; "
            "bản cam đoan, sổ đỏ/giấy tờ chỗ ở, giấy khai sinh và mọi CCCD/căn cước vào STT 3; "
            "văn bản ủy quyền vào STT 4."
        ),
    },
    {
        "key": "trich-luc-ks",
        "detect": {"urlIncludes": ["maThuTuc=2.000635"]},
        "label": "Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh",
        "shortLabel": "Bản sao Trích lục hộ tịch",
        "subtitle": "Trích lục khai sinh, kết hôn, khai tử",
        "icon": "📜",
        "flowProfile": "tu-phap",
        "supportsSplitDocuments": True,
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-867c-72db-b6a7-dcbd8c763807",
        # TỜ KHAI là giấy CHÍNH (chứa đủ thông tin sự kiện hộ tịch để kê khai); giấy hộ tịch
        # cũ chỉ bổ trợ khi có — thực tế CCCD + tờ khai là fill trọn form.
        # Mỗi nhóm tính theo TỆP, không theo mặt; checklist tự hiện "Đã nhận X tệp".
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd", "name": "Căn cước công dân", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai cấp bản sao trích lục hộ tịch", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "ho_tich", "name": "Giấy tờ hộ tịch cũ như: giấy khai sinh hoặc giấy chứng nhận "
             "kết hôn hoặc trích lục khai tử (nếu có)", "icon": "📜", "sides": 1,
             "optional": True, "repeatable": True},
            {"key": "khac", "name": "Các giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        # Chế độ agent: không gắn role, BE tự suy luận từ text OCR.
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần (doc-type đã theo cơ quan cấp sẵn)
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân.\n"
            "2. Tờ khai cấp bản sao trích lục hộ tịch.\n"
            "3. Nếu có: giấy tờ hộ tịch cũ như giấy khai sinh, giấy chứng nhận kết hôn hoặc trích lục khai tử.\n"
            "4. Các giấy tờ liên quan khác."
        ),
    },
    {
        "key": "ket-hon-nuoc-ngoai",
        # Chưa có maThuTuc trên cổng → nhận diện theo tiêu đề (giống auto-fill).
        "detect": {"textIncludes": ["kết hôn có yếu tố nước ngoài"], "textPriority": True},
        "label": "Thủ tục đăng ký kết hôn có yếu tố nước ngoài",
        "shortLabel": "Kết hôn có yếu tố nước ngoài",
        "subtitle": "Kết hôn với người nước ngoài / công dân VN định cư ở nước ngoài",
        "icon": "🌏",
        "flowProfile": "tu-phap",
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN/trích lục/khai tử.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e13-728a-a0cd-635811d8432e",
        # Giấy tờ nước ngoài (hộ chiếu/CMND nước khác) OCR có thể không tự nhận loại →
        # công dân bấm 📸 theo dòng (hint) hoặc rơi vào "khác"; pipeline vẫn dùng đủ file.
        "requiredDocs": [
            {"key": "cccd_nam", "name": "Giấy tờ tùy thân bên nam (CCCD / hộ chiếu nước ngoài)",
             "icon": "🪪", "sides": 2},
            {"key": "cccd_nu", "name": "Giấy tờ tùy thân bên nữ (CCCD / hộ chiếu nước ngoài)",
             "icon": "🪪", "sides": 2},
            {"key": "khac", "name": "Giấy xác nhận tình trạng hôn nhân nước ngoài / khám tâm thần / "
             "giấy tờ khác (nếu có)", "icon": "📎", "sides": 5, "optional": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ tùy thân bên nam (CCCD Việt Nam hoặc giấy tờ nước ngoài: hộ chiếu/CMND + bản dịch công chứng).\n"
            "2. Giấy tờ tùy thân bên nữ.\n"
            "3. Nếu có: giấy xác nhận tình trạng hôn nhân của bên nước ngoài (đã hợp pháp hoá lãnh sự).\n"
            "Hệ thống tự phân biệt nam/nữ theo giới tính và đọc quốc tịch/nơi cư trú thật (không mặc định Việt Nam)."
        ),
    },
    {
        "key": "dang-ky-lai-ket-hon",
        "detect": {"urlIncludes": ["maThuTuc=1.004746"]},
        "label": "Thủ tục đăng ký lại kết hôn",
        "shortLabel": "Đăng ký lại Kết hôn",
        "subtitle": "Đăng ký lại kết hôn khi sổ hộ tịch/bản chính bị mất",
        "icon": "💞",
        "flowProfile": "tu-phap",
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN/trích lục/khai tử.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6711-733d-b674-f82cb6606242",
        # GCN kết hôn cũ BẮT BUỘC: nguồn duy nhất của số/ngày/nơi đăng ký trước đây + là
        # thành phần hồ sơ STT2. Key "ho_tich" để classify hiện tại tự nhận (GCN kết hôn).
        "requiredDocs": [
            {"key": "cccd_nam", "name": "CCCD bên nam", "icon": "🪪", "sides": 2},
            {"key": "cccd_nu", "name": "CCCD bên nữ", "icon": "🪪", "sides": 2},
            {"key": "ho_tich", "name": "Bản sao Giấy chứng nhận kết hôn cũ", "icon": "📜", "sides": 1},
            {"key": "to_khai", "name": "Tờ khai đăng ký lại kết hôn (nếu có)", "icon": "📄", "sides": 1,
             "optional": True},
            # Catch-all: bản cam đoan/ly hôn/giấy tờ liên quan không có ô riêng → xếp vào đây
            # thay vì "chưa nhận ra loại" (route_to_slot ưu tiên slot "khac" khi không khớp).
            {"key": "khac", "name": "Các giấy tờ khác (bản cam đoan, giấy tờ liên quan…)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của bên nam (chồng).\n"
            "2. CCCD của bên nữ (vợ).\n"
            "3. Bản sao Giấy chứng nhận kết hôn cũ (để lấy số/ngày/nơi đăng ký kết hôn trước đây).\n"
            "Không cần chọn trước giấy tờ là của chồng hay vợ; hệ thống tự phân biệt theo giới tính trên CCCD.\n"
            "Nếu thiếu CCCD của một bên, hệ thống lấy thông tin bên đó từ giấy chứng nhận kết hôn."
        ),
    },
    {
        "key": "khai-sinh-dang-ky-lai",
        "detect": {"urlIncludes": ["maThuTuc=1.004884"]},
        "label": "Thủ tục đăng ký lại khai sinh",
        "shortLabel": "Đăng ký lại Khai sinh",
        "subtitle": "Đăng ký lại khai sinh khi sổ hộ tịch/bản chính bị mất",
        "icon": "🍼",
        "flowProfile": "tu-phap",
        "supportsSplitDocuments": True,
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/khai tử/TTHN/trích lục.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6eac-7598-b88b-15f8a61b366a",
        # Chỉ 2 ô theo yêu cầu: Tờ khai + Các giấy tờ khác (catch-all). classify dồn CCCD cha/mẹ,
        # giấy khai sinh cũ (ho_tich), GCN… vào "khac" (repeatable). Pipeline agent tự suy vai
        # con/cha/mẹ + "đăng ký trước đây" từ toàn bộ giấy tờ (reason.py), không cần tách ô CCCD.
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đăng ký lại khai sinh", "icon": "📄", "sides": 1,
             "optional": True},
            {"key": "khac", "name": "Các giấy tờ khác để đăng ký lại khai sinh", "icon": "📎",
             "sides": 20, "repeatable": True, "optional": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đăng ký lại khai sinh (nếu có).\n"
            "2. Các giấy tờ khác: CCCD của cha/mẹ, bản sao/trích lục giấy khai sinh cũ, "
            "giấy tờ thay thế (học bạ, hộ chiếu…) — công dân đưa hết vào mục Giấy tờ khác.\n"
            "Hệ thống tự nhận dạng người được đăng ký, cha, mẹ và số/ngày/nơi đăng ký khai sinh trước đây."
        ),
    },
    {
        "key": "khai-tu",
        "detect": {"urlIncludes": ["maThuTuc=1.000656"]},
        "label": "Thủ tục đăng ký khai tử",
        "shortLabel": "Đăng ký Khai tử",
        "subtitle": "Thủ tục đăng ký khai tử trong nước",
        "icon": "🕯️",
        "flowProfile": "tu-phap",
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN/trích lục.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fac-7489-b53b-9c6c958f2da4",
        # Giấy báo tử BẮT BUỘC (nguồn chính của sự kiện chết); tờ khai bổ trợ khi có.
        # Mỗi nhóm tính theo TỆP, không theo mặt; checklist tự hiện "Đã nhận X tệp".
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd", "name": "Căn cước công dân", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "bao_tu", "name": "Giấy báo tử hoặc giấy tờ thay giấy báo tử", "icon": "📃",
             "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai đăng ký khai tử (nếu có)", "icon": "📄",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân.\n"
            "2. Giấy báo tử hoặc giấy tờ thay giấy báo tử.\n"
            "3. Tờ khai đăng ký khai tử bản giấy nếu có.\n"
            "4. Giấy tờ liên quan khác.\n"
            "Không cần chọn trước loại giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Bước 3: hệ thống đính giấy báo tử vào thành phần hồ sơ có sẵn, CCCD và tờ khai bản giấy là thành phần mới."
        ),
    },
    {
        "key": "khai-tu-dang-ky-lai",
        "detect": {"urlIncludes": ["maThuTuc=1.005461"]},
        "label": "Thủ tục đăng ký lại khai tử",
        "shortLabel": "Đăng ký lại Khai tử",
        "subtitle": "Đăng ký lại khai tử khi thông tin đăng ký trước đây bị mất hoặc hư hỏng",
        "icon": "🕯️",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6ebc-709e-8678-a9f8b66738f2",
        # Cổng eForm hộ tịch dùng các component x-*; extension đã có fill-legacy tương ứng.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd", "name": "Căn cước công dân hoặc giấy tờ tùy thân", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai đăng ký lại khai tử", "icon": "📄",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "bao_tu", "name": "Giấy chứng tử, trích lục khai tử hoặc giấy tờ chứng minh sự kiện chết",
             "icon": "📃", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân hoặc giấy tờ tùy thân.\n"
            "2. Tờ khai đăng ký lại khai tử nếu có.\n"
            "3. Giấy chứng tử, trích lục khai tử hoặc giấy tờ chứng minh sự kiện chết.\n"
            "4. Giấy tờ liên quan khác nếu có.\n"
            "Không cần chọn trước loại giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Hệ thống tự phân biệt người yêu cầu, người đã chết và thông tin đăng ký trước đây theo nội dung OCR.\n"
            "Bước 3: chỉ giấy chứng tử/giấy tờ chứng minh sự kiện chết vào STT 2; tờ khai, CCCD và giấy tờ khác thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "dang-ky-nhan-cha-me-con",
        "detect": {"textIncludes": ["Thủ tục đăng ký nhận cha, mẹ, con"], "headingDisabled": True},
        "label": "Thủ tục đăng ký nhận cha, mẹ, con",
        "shortLabel": "Nhận Cha, Mẹ, Con",
        "subtitle": "Đăng ký nhận cha, mẹ, con trong nước",
        "icon": "👨‍👩‍👧",
        "flowProfile": "tu-phap",
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN/trích lục/khai tử.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fa6-722f-ac1a-e949c8ce3418",
        # Tờ khai BẮT BUỘC (nguồn chính quan hệ + loại xác nhận); CCCD sides=4 cho tối đa
        # 2 người × 2 mặt (người yêu cầu thường là cha/mẹ; con có thể chưa có CCCD) — thiếu
        # thì bấm "Dừng & gửi tất cả". Giấy chứng sinh không có slot riêng → classify rơi
        # vào "khac" (fallthrough chung), pipeline vẫn dùng đủ file.
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đăng ký nhận cha, mẹ, con", "icon": "📄", "sides": 1},
            {"key": "cccd", "name": "CCCD người yêu cầu và các bên (cha/mẹ, con nếu có)",
             "icon": "🪪", "sides": 4},
            {"key": "ho_tich", "name": "Giấy khai sinh của con (nếu có)", "icon": "📜", "sides": 1,
             "optional": True},
            {"key": "khac", "name": "Chứng cứ quan hệ: kết quả ADN / văn bản y tế / "
             "giấy chứng sinh / cam đoan (nếu có)", "icon": "📎", "sides": 5, "optional": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đăng ký nhận cha, mẹ, con.\n"
            "2. CCCD/Căn cước của người yêu cầu và các bên liên quan.\n"
            "3. Giấy khai sinh/giấy chứng sinh của con.\n"
            "4. Chứng cứ chứng minh quan hệ cha, mẹ, con như kết quả xét nghiệm ADN."
            "\nBước 3: eForm online ở STT 1 bỏ qua; kết quả ADN/văn bản y tế/giám định vào STT 2; "
            "nếu không có văn bản xác nhận quan hệ thì văn bản cam đoan + người làm chứng vào STT 3; "
            "tờ khai bản giấy, CCCD/căn cước và giấy khai sinh/giấy chứng sinh thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "thay-doi-cai-chinh-ho-tich",
        "detect": {"urlIncludes": ["maThuTuc=1.004859"]},
        "label": "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
        "shortLabel": "Cải chính hộ tịch",
        "subtitle": "Thay đổi, bổ sung thông tin hộ tịch",
        "icon": "📝",
        "flowProfile": "tu-phap",
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/khai tử/TTHN. URL kê khai
        # đã xác minh trong ke_khai_links.json (mã TTHC 1.004859).
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-671e-714b-8fd6-8230c82f7867",
        "review": False,
        "mode": "agent",
        # Client cũ không gửi option sẽ giữ nguyên từng file; chỉ boolean True mới tách theo trang.
        "supportsSplitDocuments": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd", "name": "Căn cước công dân của người làm giấy tờ",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "ho_tich", "name": "Giấy tờ làm căn cứ thay đổi/cải chính (giấy khai sinh, "
             "trích lục hộ tịch, đăng ký kết hôn, khai tử, học bạ, bằng cấp, quyết định…)",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai đăng ký thay đổi, cải chính, bổ sung hộ tịch (nếu có)",
             "icon": "📄", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền và các giấy tờ khác (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ làm căn cứ thay đổi/cải chính: giấy khai sinh, trích lục hộ tịch, "
            "đăng ký kết hôn, khai tử, học bạ, bằng cấp, giấy xác nhận, quyết định hoặc "
            "giấy tờ liên quan khác.\n"
            "2. CCCD/CMND/Hộ chiếu có trong hồ sơ; có thể tải riêng từng mặt hoặc nhiều người.\n"
            "3. Nếu có: tờ khai bản giấy và văn bản ủy quyền."
        ),
    },
    {
        "key": "xac-nhan-tinh-trang-hon-nhan",
        "detect": {"urlIncludes": ["maThuTuc=1.004873"]},
        "label": "Thủ tục cấp Giấy xác nhận tình trạng hôn nhân",
        "shortLabel": "Xác nhận tình trạng hôn nhân",
        "subtitle": "Cấp giấy xác nhận độc thân / tình trạng hôn nhân",
        "icon": "💍",
        "flowProfile": "tu-phap",
        "supportsSplitDocuments": True,
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn: chọn cơ quan → Nộp trực
        # tuyến → modal Thông tin chung → chủ hồ sơ → kê khai.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6eb3-7019-bf3f-fc58c9ee44b9",
        # Mỗi nhóm tính theo TỆP, không theo mặt. Không đọc câu "không giới hạn số lượng"
        # vì checklist đã hiển thị trực tiếp "Đã nhận X tệp".
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd", "name": "CCCD của người được cấp giấy xác nhận", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai cấp giấy xác nhận tình trạng hôn nhân (nếu có)",
             "icon": "📄", "sides": 1, "optional": True, "repeatable": True},
            {"key": "chung_minh_tthn", "name": "Giấy tờ chứng minh tình trạng hôn nhân (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Các giấy tờ khác liên quan", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người được cấp giấy xác nhận tình trạng hôn nhân.\n"
            "2. Nếu có: tờ khai cấp giấy xác nhận tình trạng hôn nhân.\n"
            "3. Nếu có: giấy tờ chứng minh tình trạng hôn nhân.\n"
            "4. Các giấy tờ khác liên quan.\n"
            "Mặc định người yêu cầu là bản thân; không cần chọn trước vai trò giấy tờ.\n"
            "Bước 3: hệ thống có thể đính kèm CCCD hoặc giấy tờ điều kiện vào thành phần hồ sơ phù hợp."
        ),
    },
    {
        "key": "dang-ky-kinh-doanh",
        # Trang DVCQG chỉ là điểm vào. Sau đăng nhập, hồ sơ chạy trên HkdOnline WebForms
        # và reload toàn trang sau gần như mọi thao tác; extension nhận diện bằng DOM + domain.
        "detect": {
            "urlIncludes": [
                "019d2bfb-d76d-737f-81b9-69258b07240b",
                "hokinhdoanh.dkkd.gov.vn",
            ],
            "headingDisabled": True,
        },
        "label": "Đăng ký thành lập hộ kinh doanh",
        "shortLabel": "Đăng ký thành lập hộ kinh doanh",
        "subtitle": "Tạo mới hộ kinh doanh và tự điền toàn bộ hồ sơ",
        "icon": "🏪",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-d76d-737f-81b9-69258b07240b",
        "needsAgencySelect": True,
        "businessWorkflow": "create",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "giay_de_nghi", "name": "Giấy đề nghị đăng ký hộ kinh doanh",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân hoặc giấy tờ pháp lý của cá nhân",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu có)",
             "icon": "📝", "sides": 1, "optional": True, "repeatable": True},
            {"key": "bien_ban", "name": "Biên bản họp thành viên hộ gia đình (nếu có)",
             "icon": "📋", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Các giấy tờ liên quan khác",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "pages": [
            {"key": "hinh-thuc-dang-ky", "label": "Hình thức đăng ký"},
            {"key": "dia-chi", "label": "Địa chỉ"},
            {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
            {"key": "ten-ho-kinh-doanh", "label": "Tên hộ kinh doanh"},
            {"key": "chu-ho-kinh-doanh", "label": "Thông tin về chủ hộ kinh doanh"},
            {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
            {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị đăng ký hộ kinh doanh.\n"
            "2. Căn cước công dân hoặc giấy tờ pháp lý của cá nhân.\n"
            "3. Văn bản ủy quyền và biên bản họp thành viên hộ gia đình (nếu có).\n"
            "4. Các giấy tờ liên quan khác (nếu có)."
        ),
    },
    {
        "key": "chung-thuc-ban-sao",
        "detect": {
            "urlIncludes": [
                "019d2bfd-8e22-77ef-819f-e49460350904",
                "maThuTuc=2.000815",
            ],
        },
        "label": (
            "Chứng thực bản sao từ bản chính giấy tờ, văn bản do cơ quan, tổ chức có thẩm quyền "
            "của Việt Nam; cơ quan, tổ chức có thẩm quyền của nước ngoài; cơ quan, tổ chức có thẩm "
            "quyền của Việt Nam liên kết với cơ quan, tổ chức có thẩm quyền của nước ngoài cấp hoặc "
            "chứng nhận"
        ),
        "shortLabel": "Chứng thực bản sao",
        "subtitle": "Chứng thực bản sao từ bản chính giấy tờ, văn bản",
        "icon": "📑",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e22-77ef-819f-e49460350904",
        # Thủ tục attach-only tại quầy đi thẳng từ Thành phần hồ sơ sang nhận tệp;
        # không hiển thị card xin consent và không tạo consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Thủ tục ĐẦU TIÊN chạy luồng dẫn từng bước (nút chuyển bước + nút gửi hồ sơ ngay trong
        # sidebar). Chỉ client khai supportsGuidedSteps mới nhận; bản trên chợ giữ luồng cũ.
        "guidedSteps": {
            "enabled": True,
            "ownerScan": True,
            # Ô CHỈ có ở bước Thông tin chủ hồ sơ: căn cước dùng để ĐIỀN FORM, không phải giấy
            # đem đi chứng thực. Sang bước Thành phần hồ sơ ô này bị rút (sync_for_conversation).
            "ownerStepDocs": [
                {"key": "cccd_chu_ho_so", "name": "Căn cước công dân của chủ hồ sơ",
                 "icon": "🪪", "sides": 1,
                 "purpose": "để em điền thông tin chủ hồ sơ",
                 # Công dân chọn chứng thực luôn thẻ này → nó thành giấy đem đi chứng thực,
                 # phải chuyển sang ô dưới đây để còn hiện trên checklist ở bước sau.
                 "certifiedInto": "khac"},
            ],
            # Nhánh ỦY QUYỀN: trang đổi nhãn khối thành "Thông tin người nộp hồ sơ" và mọc
            # thêm khối "Thông tin ủy quyền cá nhân" (4 ô, đều bắt buộc, LUÔN trống khi mở
            # trang). Cùng bộ khóa với trên để mọi luật sau đó không phải phân nhánh; chỉ
            # đổi TÊN HIỂN THỊ cho đúng vai, và thêm ô giấy ủy quyền.
            "authorizationStepDocs": [
                {"key": "cccd_chu_ho_so", "name": "Căn cước công dân của người nộp hồ sơ",
                 "icon": "🪪", "sides": 1,
                 "purpose": "để em điền thông tin người nộp hồ sơ",
                 "certifiedInto": "khac"},
                {"key": "giay_uy_quyen", "name": "Giấy ủy quyền", "icon": "📝", "sides": 1,
                 "purpose": "để em điền thông tin ủy quyền và đính kèm vào hồ sơ luôn"},
            ],
            # Bước Thông tin nhận kết quả: cổng để CẢ BA công tắc tắt, không có mặc định nào.
            # `label` phải đúng NGUYÊN VĂN chữ trên cổng — FE khớp công tắc theo nhãn đã fold
            # dấu, KHÔNG theo id (id Radix kiểu ":r91:-form-item" sinh lại mỗi lần render).
            # `needsInput`: CHỈ bưu chính mới đòi thêm thông tin người nhận (kiểm trên cổng
            # thật 24/09/2026 — bản giấy và trực tuyến gạt xong là xong). Trợ lý chỉ tick,
            # không bao giờ điền hộ địa chỉ/người nhận.
            "resultMethods": [
                {"key": "paper", "label": "Nhận kết quả bản giấy có đóng dấu", "icon": "📄",
                 "desc": "Nhận bản giấy có đóng dấu của cơ quan.", "default": True},
                {"key": "online", "label": "Nhận kết quả trực tuyến", "icon": "🌐",
                 "desc": "Nhận bản điện tử ngay trên hệ thống."},
                {"key": "postal", "label": "Dịch vụ bưu chính công ích", "icon": "📮",
                 "desc": "Nhân viên bưu điện sẽ đến địa chỉ trả kết quả để trả hồ sơ.",
                 "needsInput": True},
            ],
        },
        # Một loại duy nhất, nhận lặp không giới hạn. sides=1 chỉ là số tệp tối thiểu;
        # repeatable giữ phiên mở để người dân tiếp tục thêm tệp rồi chủ động bấm Đã đủ.
        "requiredDocs": [
            {"key": "khac", "name": "Giấy tờ cần chứng thực bản sao", "icon": "📄",
             "sides": 1, "repeatable": True,
             "purpose": "để đính kèm vào Thành phần hồ sơ ở bước sau"},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ cần chứng thực bản sao (không giới hạn số lượng tệp).\n"
            "Tất cả tệp được đính kèm trong cùng một hồ sơ; hệ thống không phân loại nội dung."
        ),
    },
    {
        "key": "chung-thuc-giao-dich-tai-san",
        # Cổng React mới (Bộ Tư pháp). detect kèm cả UUID trang + maThuTuc như nhóm chứng thực.
        "detect": {
            "urlIncludes": [
                "019d2bfd-95fa-70ca-93fd-4cab11b87897",
                "maThuTuc=2.001035",
            ],
        },
        "label": "Chứng thực giao dịch liên quan đến tài sản là động sản, quyền sử dụng đất, nhà ở",
        "shortLabel": "Chứng thực giao dịch tài sản",
        "subtitle": "Chứng thực hợp đồng, giao dịch về động sản, đất đai, nhà ở",
        "icon": "🏘️",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-95fa-70ca-93fd-4cab11b87897",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Cổng có 2 dòng cố định: (1) giấy chứng nhận sở hữu/sử dụng → STT1, (2) dự thảo giao
        # dịch (bắt buộc) → STT2. Planner attach (core) tự phân loại lại theo OCR; CCCD/ủy quyền/
        # giấy khác thêm thành phần hồ sơ mới. Slot so_huu/du_thao khớp qua chụp-theo-dòng; chụp
        # chung không nhận ra loại thì rơi vào "khac" — planner vẫn tách đúng lúc đính.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "so_huu", "name": "Giấy chứng nhận quyền sở hữu/sử dụng tài sản (sổ đỏ, đăng ký xe…)",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "du_thao", "name": "Dự thảo giao dịch/hợp đồng", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân (nếu có)", "icon": "🪪",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền và giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy chứng nhận quyền sở hữu/sử dụng hoặc giấy tờ thay thế của tài sản "
            "(sổ đỏ, đăng ký xe…).\n"
            "2. Dự thảo giao dịch/hợp đồng (bắt buộc).\n"
            "3. Nếu có: CCCD, văn bản ủy quyền hoặc tài liệu khác; hệ thống sẽ thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "chung-thuc-chu-ky-nguoi-dich-ctv",
        "detect": {
            "urlIncludes": [
                "019d2bfd-95d3-7258-b613-a71dbf432f07",
                "maThuTuc=2.000992",
            ],
        },
        "label": (
            "Chứng thực chữ ký người dịch mà người dịch là cộng tác viên dịch thuật của "
            "Ủy ban nhân dân cấp xã, tổ chức hành nghề công chứng"
        ),
        "shortLabel": "Chứng thực chữ ký người dịch (CTV)",
        "subtitle": "Chứng thực chữ ký người dịch là cộng tác viên dịch thuật",
        "icon": "🌐",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-95d3-7258-b613-a71dbf432f07",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Cổng chỉ có MỘT dòng cố định "Bản dịch và giấy tờ, văn bản cần dịch." → một loại giấy
        # duy nhất, không phân loại. Gộp: tệp đầu vào dòng đó, tệp sau thêm thành phần mới (tên
        # do planner đánh số sẵn). Tách: mỗi bản dịch thành một hồ sơ riêng trên một tab riêng.
        "requiredDocs": [
            {"key": "khac", "name": "Bản dịch và giấy tờ, văn bản cần dịch", "icon": "📄",
             "sides": 1, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản dịch và giấy tờ, văn bản cần dịch (không giới hạn số lượng tệp).\n"
            "Có thể gộp tất cả vào một hồ sơ, hoặc tách mỗi bản dịch thành một hồ sơ riêng."
        ),
    },
    {
        "key": "chung-thuc-chu-ky",
        "detect": {
            "urlIncludes": [
                "019d2bfd-8e2e-7359-b42f-d5dc8d74741b",
                "maThuTuc=2.000884",
            ],
        },
        "label": (
            "Chứng thực chữ ký trong các giấy tờ, văn bản (áp dụng cho cả trường hợp chứng thực "
            "điểm chỉ và trường hợp người yêu cầu chứng thực không thể ký, không thể điểm chỉ được)"
        ),
        "shortLabel": "Chứng thực chữ ký",
        "subtitle": "Chứng thực chữ ký/điểm chỉ trên giấy tờ, văn bản",
        "icon": "✍️",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e2e-7359-b42f-d5dc8d74741b",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Form 2 ô cố định: giấy tờ cần chứng thực (STT1) + giấy tùy thân/CCCD (STT2). classify: CCCD
        # → ô cccd; mọi văn bản khác → ô "khac" (catch-all, repeatable giữ phiên mở). Planner attach
        # tự tách STT1/STT2 lại theo nội dung (không phụ thuộc slot).
        # Cả 2 ô repeatable: đếm theo "file", KHÔNG giới hạn số lượng (FE hiện "Đã nhận X tệp",
        # không hiện "x/2 mặt"). Người yêu cầu có thể gửi CCCD nhiều mặt/nhiều người.
        "requiredDocs": [
            {"key": "cccd", "name": "Căn cước công dân", "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Các giấy tờ cần chứng thực chữ ký", "icon": "📄",
             "sides": 1, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Các giấy tờ, văn bản cần chứng thực chữ ký/điểm chỉ (không giới hạn số lượng).\n"
            "2. Căn cước công dân của người yêu cầu."
        ),
    },
    {
        "key": "cap-giay-phep-khai-thac-thuy-san",
        "provinceOnly": ["danang"],  # đặc thù Đà Nẵng: chỉ account tỉnh này thấy + gọi được
        # Cổng Bộ Nông nghiệp & Môi trường (dichvucongnnmt.mae.gov.vn) — LUỒNG KHÁC hẳn tư pháp:
        # (1) DVCQG "Chọn cơ quan thực hiện": CHỈ chọn Tỉnh (bỏ xã) → Đồng ý → kết quả ĐẦU
        #     TIÊN "Nộp trực tuyến" chính là Sở NN&MT (agencyProvinceOnly).
        # (2) Trang MAE "chọn nơi và loại" (Angular Material, form#ngSelectAgencyForm1): bot điền
        #     Tỉnh + radio "Sở/Ban ngành" + chọn Sở NN&MT + "Trường hợp giải quyết" theo variant
        #     người dân đã chọn ở bước choose_variant, rồi bấm "Đồng ý và tiếp tục" (maePortal).
        # (3) Kê khai = wizard MAE bước 1 (Form.io data[...]), Thành phần hồ sơ = bước 2 (bảng
        #     mat-table, engine attp-row) → wizard KHÁC mặc định tu-phap 1/2/3.
        "detect": {
            "textIncludes": ["cấp, cấp lại giấy phép khai thác thủy sản"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp, cấp lại Giấy phép khai thác thủy sản",
        "shortLabel": "Giấy phép khai thác thủy sản",
        "subtitle": "Cấp mới / cấp lại giấy phép khai thác thủy sản cho tàu cá",
        "icon": "🐟",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-3815-712d-a33f-c571e5d7fdc2",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nông nghiệp và Môi trường",
        # Người dân chọn 1 trong 2 trường hợp NGAY sau khi xác nhận thủ tục (state choose_variant);
        # portalMatch/portalAvoid là token fold để FE khớp option "Trường hợp giải quyết" trên cổng
        # (mỗi tỉnh đặt tên khác nhau: "Trường hợp 1: Cấp mới..." / "TH1 - Cấp Giấy phép...").
        "variants": {
            "options": [
                {"key": "cap_moi", "label": "Cấp mới giấy phép", "chip": "🆕 Cấp mới giấy phép",
                 "portalMatch": "cap moi", "portalAvoid": "cap lai",
                 "desc": "chưa có giấy phép, xin cấp lần đầu"},
                {"key": "cap_lai", "label": "Cấp lại giấy phép", "chip": "🔁 Cấp lại giấy phép",
                 "portalMatch": "cap lai",
                 "desc": "đã có giấy phép nhưng bị mất, hư hỏng, hết hạn hoặc thay đổi thông tin"},
            ],
        },
        # Wizard MAE: bước 1 = Thông tin hồ sơ (kê khai Form.io), bước 2 = Thành phần hồ sơ
        # (đính kèm), bước 3 = phí/captcha, bước 4 = nộp. Không có bước "chủ hồ sơ" riêng
        # (ownerStep=5 là giá trị không bao giờ khớp — FE chỉ phát wizardStep 1-4).
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp hoặc cấp lại Giấy phép khai thác thủy sản", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ tàu, thêm CCCD người nộp nếu "
             "nộp thay", "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "giay_phep_cu", "name": "Giấy phép khai thác thủy sản cũ (nếu cấp lại)",
             "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp Giấy phép khai thác thủy sản (Mẫu 04.KT — cấp mới) HOẶC đơn đề "
            "nghị cấp lại (Mẫu 05.KT — cấp lại), đã ký.\n"
            "2. Căn cước công dân của chủ tàu (2 mặt); nếu người khác nộp thay thì thêm CCCD "
            "người nộp.\n"
            "3. Nếu cấp lại: tờ Giấy phép khai thác thủy sản cũ (để lấy số, ngày cấp, ngày hết hạn).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cap-ban-sao-van-bang-so-goc",
        "provinceOnly": ["danang"],  # đặc thù Đà Nẵng: chỉ account tỉnh này thấy + gọi được
        # Cổng Bộ GD&ĐT dvc.moet.gov.vn — CÙNG nền iGate với cổng NN&MT (wizard 4 bước:
        # 1 Thông tin hồ sơ = kê khai Form.io, 2 Thành phần hồ sơ = attp-row) nhưng KHÔNG có
        # trang "chọn nơi và loại": Nộp trực tuyến trên DVCQG → thẳng trang kê khai.
        # DVCQG "Chọn cơ quan thực hiện": chọn Tỉnh → chuyển toggle sang "Sở" (KHÔNG chọn sở
        # cụ thể trong combo) → Đồng ý → danh sách hiện ra, bấm "Nộp trực tuyến" kết quả ĐẦU
        # TIÊN (mặc định là Sở GD&ĐT) — agencySoFirst.
        "detect": {
            "urlScope": ["dvc.moet.gov.vn"],
            "textIncludes": ["cấp bản sao văn bằng, chứng chỉ từ sổ gốc"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc",
        "shortLabel": "Bản sao văn bằng, chứng chỉ",
        "subtitle": "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc (Sở Giáo dục và Đào tạo)",
        "icon": "🎓",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf8-df63-75bf-8bff-4c9d1f98674c",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Giáo dục và Đào tạo",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Phiếu yêu cầu cấp bản sao văn bằng, chứng chỉ (Mẫu BM04) "
             "— đã điền, đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ văn bằng (thêm CCCD người yêu "
             "cầu nếu làm thay)", "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "van_bang", "name": "Bản photo văn bằng / chứng chỉ cần cấp bản sao",
             "icon": "🎓", "sides": 1, "repeatable": True},
            {"key": "uy_quyen", "name": "Giấy ủy quyền / giấy tờ chứng minh quan hệ (nếu làm "
             "thay)", "icon": "🖋️", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu yêu cầu cấp bản sao văn bằng, chứng chỉ (Mẫu BM04) đã điền, đã ký.\n"
            "2. Căn cước công dân của chủ văn bằng.\n"
            "3. Bản photo văn bằng / chứng chỉ cần cấp bản sao.\n"
            "4. Nếu người khác yêu cầu thay: giấy ủy quyền hoặc giấy tờ chứng minh quan hệ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cho-thue-thue-mua-nha-o-xa-hoi",
        "provinceOnly": ["danang"],  # đặc thù Đà Nẵng: chỉ account tỉnh này thấy + gọi được
        # Cổng Bộ Xây dựng dvc.moc.gov.vn — CÙNG nền iGate với MAE/moet (wizard 1 kê khai,
        # 2 đính kèm; Form.io dom-* + attach attp-row 4 dòng). KHÔNG trang "chọn nơi và loại".
        # DVCQG "Chọn cơ quan thực hiện": chọn Tỉnh → gạt toggle sang "Sở" (KHÔNG chọn sở
        # cụ thể) → Đồng ý → "Nộp trực tuyến" kết quả ĐẦU TIÊN (Sở Xây dựng) — agencySoFirst.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "textIncludes": [
                "Cho thuê, cho thuê mua nhà ở xã hội do Nhà nước đầu tư xây dựng bằng vốn đầu tư công",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cho thuê, cho thuê mua nhà ở xã hội do Nhà nước đầu tư xây dựng bằng vốn đầu tư công",
        "shortLabel": "Thuê / thuê mua nhà ở xã hội",
        "subtitle": "Đăng ký thuê, thuê mua nhà ở xã hội vốn đầu tư công (Sở Xây dựng)",
        "icon": "🏠",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-88ac-71f9-b970-b83cf0372841",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Tờ đơn đăng ký thuê (hoặc thuê mua) nhà ở xã hội theo mẫu "
             "— đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người viết đơn", "icon": "🪪",
             "sides": 2, "repeatable": True},
            {"key": "doi_tuong", "name": "Giấy tờ chứng minh ĐỐI TƯỢNG chính sách (huân/huy "
             "chương, thương binh, thân nhân liệt sĩ, quân nhân... nếu có)", "icon": "🎖️",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "dieu_kien", "name": "Giấy tờ chứng minh ĐIỀU KIỆN nhà ở / thu nhập (xác "
             "nhận hộ nghèo, thu nhập, thực trạng nhà ở... nếu có)", "icon": "🧾",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ đơn đăng ký thuê (hoặc thuê mua) nhà ở xã hội theo mẫu, đã ký.\n"
            "2. Căn cước công dân của người viết đơn.\n"
            "3. Nếu có: giấy tờ chứng minh đối tượng chính sách (huân/huy chương, giấy chứng "
            "nhận thương binh, giấy báo tử liệt sĩ, giấy tờ quân nhân/công an...).\n"
            "4. Nếu có: giấy tờ chứng minh điều kiện nhà ở/thu nhập (xác nhận hộ nghèo, xác "
            "nhận thu nhập, thực trạng nhà ở...).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dieu-chinh-huu-tri-xa-hoi",
        # Cổng Bộ Y tế dichvucongbyt.moh.gov.vn — CÙNG nền iGate/Form.io với MAE/moet/moc:
        # wizard 1 "Thông tin hồ sơ" (kê khai dom-*) → 2 "Thành phần hồ sơ" (đính kèm) →
        # 3 phí/lệ phí + captcha (NÚT NỘP nằm ở đây) → 4 màn báo kết quả.
        # KHÁC ba cổng bộ kia ở bước chọn cơ quan: DVCQG chọn ĐỦ Tỉnh + Xã rồi vào THẲNG trang
        # kê khai — KHÔNG có toggle "Sở", KHÔNG có trang "chọn nơi và loại" của MAE. Vì vậy chỉ
        # đặt needsAgencySelect (bot tự chọn Tỉnh/Xã + Nộp trực tuyến), KHÔNG agencyProvinceOnly
        # / agencySoFirst. Luật nhận nút "Nộp hồ sơ" đã khai sẵn ở portal_submit (_FORMIO).
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.014027",
                "019d2bff-2d80-74d8-8515-90f6f61822f0",
            ],
            "textIncludes": ["Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội",
        "shortLabel": "Trợ cấp hưu trí xã hội — thực hiện, điều chỉnh, thôi hưởng",
        "subtitle": "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội",
        "icon": "👴",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-2d80-74d8-8515-90f6f61822f0",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Bảng thành phần hồ sơ của cổng CHỈ CÒN ĐÚNG MỘT DÒNG (Nghị định 176/2025/NĐ-CP) và đã
        # bỏ nút "Thêm giấy tờ" → planner dồn MỌI tệp vào dòng đó; các ô dưới đây chỉ để công dân
        # biết cần mang gì, không phải đích đến riêng.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Văn bản đề nghị hưởng trợ cấp hưu trí xã hội "
             "(Mẫu số 01, Nghị định 176/2025/NĐ-CP) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Văn bản đề nghị hưởng trợ cấp hưu trí xã hội (Mẫu số 01 ban hành kèm theo "
            "Nghị định số 176/2025/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của người đề nghị.\n"
            "Hệ thống lấy chủ hồ sơ từ mục thông tin người đề nghị hưởng trợ cấp hưu trí xã hội.\n"
            "Bước Thành phần hồ sơ: cổng chỉ còn ĐÚNG MỘT dòng nên mọi tệp đều được đính vào "
            "dòng đó; tệp không phải Văn bản đề nghị vẫn đính được nhưng có cảnh báo để cán bộ soát."
        ),
    },
    {
        "key": "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham",
        # Cổng Bộ Y tế, CÙNG khung với "dieu-chinh-huu-tri-xa-hoi" ngay trên: DVCQG chọn ĐỦ Tỉnh +
        # Xã rồi vào THẲNG trang kê khai (không có hộp thoại chọn cơ quan trong cổng), wizard iGate
        # 1 Thông tin hồ sơ → 2 Thành phần hồ sơ → 3 Hình thức nhận kết quả → 4 Nộp hồ sơ.
        # KHÁC hưu trí ở trang kết quả DVCQG: thủ tục do CẢ Sở Y tế lẫn UBND xã tiếp nhận nên ra
        # NHIỀU thẻ, thẻ đầu là cấp Sở — bấm "thẻ đầu" như mọi thủ tục khác là nộp nhầm cơ quan.
        # agencyCardIncludes chốt đúng thẻ UBND (cùng chuỗi Auto Fill đang dùng, ke_khai_links
        # submitCardIncludes).
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            # KHÔNG khai id apply-online/<id>: snapshot là của một tài khoản cụ thể, id đó đổi
            # theo đơn vị tiếp nhận.
            "urlIncludes": [
                "maThuTuc=1.013855",
                "019d2bff-2d33-76fe-bd90-4f37b18e4401",
            ],
            "textIncludes": ["cơ sở đủ điều kiện an toàn thực phẩm", "phạm vi quản lý của bộ y tế"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Cấp giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm đối với cơ sở kinh doanh "
            "dịch vụ ăn uống, cơ sở sản xuất thực phẩm thuộc phạm vi quản lý của Bộ Y tế"
        ),
        "shortLabel": "Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm (dịch vụ ăn uống)",
        "subtitle": "Cho quán ăn, nhà hàng, bếp ăn, cơ sở sản xuất thực phẩm thuộc Bộ Y tế",
        "icon": "🍲",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-2d33-76fe-bd90-4f37b18e4401",
        "needsAgencySelect": True,
        "agencyCardIncludes": "Cơ quan thực hiện: UBND",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Bảng thành phần hồ sơ chỉ có MỘT dòng "A. Thành phần hồ sơ: a)…e)" gom cả năm loại giấy →
        # planner core dồn mọi tệp vào dòng đó (fixed-slot attp_dossier, upload lặp). Các ô dưới đây
        # chỉ để công dân biết cần mang gì, không phải đích đến riêng.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp Giấy chứng nhận (Mẫu số 1 Phụ lục I, Nghị định "
             "155/2018/NĐ-CP)", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "dkkd", "name": "Bản sao Giấy chứng nhận đăng ký kinh doanh hoặc đăng ký doanh "
             "nghiệp (có ngành nghề phù hợp)", "icon": "🏪", "sides": 1, "repeatable": True},
            {"key": "thuyet_minh", "name": "Bản thuyết minh cơ sở vật chất, trang thiết bị, dụng cụ "
             "bảo đảm vệ sinh an toàn thực phẩm", "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "suc_khoe", "name": "Giấy xác nhận đủ sức khỏe của chủ cơ sở và người trực tiếp "
             "sản xuất, kinh doanh", "icon": "🩺", "sides": 1, "repeatable": True},
            {"key": "tap_huan", "name": "Danh sách người đã được tập huấn kiến thức an toàn thực phẩm "
             "(có xác nhận của chủ cơ sở)", "icon": "📋", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ cơ sở", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp Giấy chứng nhận (Mẫu số 1 Phụ lục I, Nghị định 155/2018/NĐ-CP) — "
            "nguồn chính để điền form.\n"
            "2. Căn cước công dân của chủ cơ sở.\n"
            "3. Bản sao Giấy chứng nhận đăng ký kinh doanh / đăng ký doanh nghiệp.\n"
            "4. Bản thuyết minh cơ sở vật chất, trang thiết bị; giấy xác nhận đủ sức khỏe; danh "
            "sách người đã tập huấn kiến thức an toàn thực phẩm.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước Thành phần hồ sơ: cổng chỉ có MỘT dòng 'A. Thành phần hồ sơ' gom mọi loại giấy "
            "nên mọi tệp đều được đính vào dòng đó."
        ),
    },
    {
        "key": "di-chuyen-ho-so-nguoi-huong-tro-cap",
        # Cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn (iGate + Form.io). Chọn cơ quan HAI BƯỚC:
        #  A. Hộp thoại DVCQG: chọn Tỉnh → bật "Sở" (KHÔNG chọn tên sở) → Đồng ý → mục "Nộp trực
        #     tuyến" đầu tiên = đúng luồng agencySoFirst sẵn có (ward bỏ trống: agencyProvinceOnly).
        #  B. Sang cổng bộ, hộp thoại form#ngSelectAgencyForm1 (CÙNG component trang chọn cơ quan
        #     của MAE): UBND Tỉnh → radio "Sở/Ban ngành" → Sở Nội vụ → "Đồng ý và tiếp tục" =
        #     nhánh maePortal. KHÔNG có ô "Trường hợp giải quyết" nên không khai variants — bot
        #     không hỏi gì, điền luôn.
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.010827",
                "019d2bfb-03d1-7738-83c0-e5b7b37f5bb0",
            ],
            # Trang kê khai (padsvc/apply-online/<id>) KHÔNG còn mã thủ tục trên URL → phải có cụm
            # tên để nhận ra khi công dân mở thẳng trang đó.
            "textIncludes": ["di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay đổi nơi thường trú",
        "shortLabel": "Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay đổi nơi thường trú",
        "subtitle": "Chuyển hồ sơ người có công sang nơi thường trú mới",
        "icon": "🎖️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-03d1-7738-83c0-e5b7b37f5bb0",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nội vụ",
        # Wizard cổng Bộ Nội vụ: 1 Thông tin hồ sơ → 2 Thành phần hồ sơ → 3 Thông tin bổ sung →
        # 4 Nộp hồ sơ (cùng cách đánh số với các cổng bộ khác).
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Bước đính kèm là HAI Ô CỐ ĐỊNH (planner core trả fixed-slot): ô 1 Đơn Mẫu 27, ô 2 căn cước
        # hoặc xác nhận cư trú CT07 → không bật hideRepeatableHint.
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị di chuyển hồ sơ (Mẫu số 27, Nghị định 131/2021/NĐ-CP)"
             " — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người hưởng trợ cấp ưu đãi", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "cu_tru", "name": "Giấy xác nhận thông tin về cư trú (Mẫu CT07) tại nơi thường "
             "trú mới", "icon": "🏠", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: bản khai thân nhân, giấy khai sinh, giấy "
             "chứng nhận gia đình liệt sĩ, Bằng Tổ quốc ghi công", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị di chuyển hồ sơ theo Mẫu số 27 (Phụ lục I Nghị định 131/2021/NĐ-CP), "
            "đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của người hưởng trợ cấp ưu đãi (người làm đơn).\n"
            "3. Giấy xác nhận thông tin về cư trú (Mẫu CT07) tại nơi thường trú mới.\n"
            "4. Nếu có: bản khai thân nhân, giấy khai sinh, giấy chứng nhận gia đình liệt sĩ, Bằng "
            "Tổ quốc ghi công, phiếu báo di chuyển hồ sơ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là người hưởng trợ cấp (người làm đơn); ai đi nộp thay thì hệ thống tự nhận ra.\n"
            "Bước Thành phần hồ sơ: Đơn Mẫu 27 vào ô 1; căn cước hoặc xác nhận cư trú vào ô 2."
        ),
    },
    {
        "key": "tro-cap-tho-cung-liet-si",
        # Cổng Bộ Nội vụ, CÙNG cách chọn cơ quan CẤP XÃ với "uu-dai-ncc-tu-tran" ngay dưới:
        # DVCQG chọn đủ Tỉnh + Phường/Xã, rồi hộp thoại form#ngSelectAgencyForm1 gạt radio
        # "Phường/Xã" + chọn xã + "Đồng ý và tiếp tục". Không có ô "Trường hợp giải quyết".
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            # Chưa có snapshot trang kê khai nên chưa biết id SPA (apply-online/<id>,
            # process=<id>). Trên cổng bộ, hai trang đó KHÔNG còn mã thủ tục trên URL →
            # nhận ra bằng cụm tên; tên thủ tục này không đụng thủ tục nào khác.
            "urlIncludes": [
                "MaTTHC=1.010803",
                "019d2bfa-fc0c-7046-b5dc-04303a18608d",
            ],
            "textIncludes": ["giải quyết chế độ trợ cấp thờ cúng liệt sĩ"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Giải quyết chế độ trợ cấp thờ cúng liệt sĩ",
        "shortLabel": "Giải quyết chế độ trợ cấp thờ cúng liệt sĩ",
        "subtitle": "Trợ cấp cho người được giao thờ cúng liệt sĩ",
        "icon": "🕯️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-fc0c-7046-b5dc-04303a18608d",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" có BA ô cố định (planner core trả fixed-slot 0/1/2) theo đúng
        # thứ tự dưới đây, phần còn lại đi "Thêm giấy tờ" → KHÔNG hideRepeatableHint.
        "requiredDocs": [
            {"key": "van_ban_uy_quyen", "name": "Văn bản ủy quyền thờ cúng liệt sĩ (khi các thân "
             "nhân ủy quyền cho một người đứng thờ cúng)", "icon": "✍️", "sides": 1,
             "optional": True, "repeatable": True},
            {"key": "don_de_nghi", "name": "Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt "
             "sĩ (Mẫu số 18, Nghị định 131/2021/NĐ-CP) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "bang_tqgc", "name": "Bản sao chứng thực từ Bằng \"Tổ quốc ghi công\"",
             "icon": "🎖️", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị thờ cúng", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "trich_luc_khai_tu", "name": "Trích lục khai tử của thân nhân liệt sĩ (khi "
             "người thờ cúng trước đó đã mất)", "icon": "🕯️", "sides": 1,
             "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt sĩ (Mẫu số 18, Phụ lục I "
            "Nghị định 131/2021/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Bản sao chứng thực từ Bằng \"Tổ quốc ghi công\" — lấy thông tin liệt sĩ (số bằng, "
            "số quyết định, quê quán).\n"
            "3. Căn cước công dân của người đề nghị — bổ sung số định danh, ngày/nơi cấp, nơi cư trú.\n"
            "4. Nếu có: văn bản ủy quyền thờ cúng, trích lục khai tử của thân nhân liệt sĩ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "LƯU Ý: người đề nghị (còn sống, là chủ hồ sơ) và liệt sĩ là HAI người khác nhau — "
            "không lấy thông tin trên Bằng Tổ quốc ghi công điền cho người đề nghị.\n"
            "Bước Thành phần hồ sơ: văn bản ủy quyền vào ô 1, Đơn Mẫu 18 vào ô 2, Bằng Tổ quốc "
            "ghi công vào ô 3; căn cước và trích lục khai tử xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "uu-dai-ncc-tu-tran",
        # CÙNG cổng Bộ Nội vụ và cùng wizard với "di-chuyen-ho-so-nguoi-huong-tro-cap", KHÁC HẲN
        # ở bước chọn cơ quan vì thủ tục này giải quyết ở CẤP XÃ ("Quy trình liên thông Xã - Sở
        # Nội vụ"), không phải ở Sở:
        #  A. Hộp thoại DVCQG: chọn ĐỦ Tỉnh + Phường/Xã của tài khoản rồi "Nộp trực tuyến" →
        #     chỉ needsAgencySelect, KHÔNG agencyProvinceOnly (ward rỗng = bỏ qua ô xã), KHÔNG
        #     agencySoFirst (gạt toggle "Sở" là chọn nhầm cấp).
        #  B. Sang cổng bộ, hộp thoại form#ngSelectAgencyForm1 (cùng component với MAE): Tỉnh →
        #     radio "Phường/Xã" (cổng đã tích SẴN) → xã → "Đồng ý và tiếp tục". Nhánh maePortal
        #     nhưng ở cấp xã → maeAgencyLevel "ward"; không có ô "Trường hợp giải quyết".
        "detect": {
            # Hai host: trang chi tiết thủ tục trên DVCQG (uuid) và cổng bộ (mã TTHC + id SPA).
            # Thiếu dichvucong.gov.vn thì uuid nằm trong urlIncludes cũng không bao giờ khớp.
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.010824",
                "019d2bfa-fc36-7611-9219-adb6dee5774f",
                "apply-online/69607677911c3f32013c0efc",
                "process=697032389ebae42b4c3841e6",
            ],
            # Trang kê khai/đính kèm không còn mã thủ tục trên URL. Hai cụm đi cùng nhau (AND):
            # "ưu đãi từ trần" một mình cũng đủ hiếm, nhưng cụm đầu chặn nhầm với thủ tục di
            # chuyển hồ sơ cùng cổng (trang đó cũng có chữ "trợ cấp ưu đãi").
            "textIncludes": ["hưởng trợ cấp khi người có công", "ưu đãi từ trần"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần",
        "shortLabel": "Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần",
        "subtitle": "Giải quyết chế độ cho thân nhân khi người có công từ trần",
        "icon": "🕯️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-fc36-7611-9219-adb6dee5774f",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" có ô CỐ ĐỊNH cho Bản khai Mẫu 12 (planner core trả fixed-slot
        # slotIndex 0), phần còn lại đi "Thêm giấy tờ" → KHÔNG hideRepeatableHint.
        "requiredDocs": [
            {"key": "ban_khai", "name": "Bản khai giải quyết chế độ ưu đãi khi người có công từ "
             "trần (Mẫu số 12, Nghị định 131/2021/NĐ-CP) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "trich_luc_khai_tu", "name": "Trích lục khai tử hoặc giấy báo tử của người có "
             "công đã từ trần", "icon": "🕯️", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người khai (người nhận trợ cấp)",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "giay_khai_sinh", "name": "Giấy khai sinh của con chưa đủ 18 tuổi (nếu thân "
             "nhân hưởng trợ cấp là con)", "icon": "👶", "sides": 1,
             "optional": True, "repeatable": True},
            {"key": "bien_ban_hop", "name": "Biên bản họp gia đình cử người nhận trợ cấp",
             "icon": "📝", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác: danh sách đề nghị trợ cấp, quyết "
             "định trợ cấp cũ của người từ trần", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản khai giải quyết chế độ ưu đãi khi người có công từ trần (Mẫu số 12, Phụ lục I "
            "Nghị định 131/2021/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Trích lục khai tử hoặc giấy báo tử của người có công đã từ trần.\n"
            "3. Căn cước công dân của người khai (người đứng tên nhận trợ cấp).\n"
            "4. Nếu có: giấy khai sinh (thân nhân là con chưa đủ 18 tuổi), biên bản họp gia đình, "
            "danh sách đề nghị trợ cấp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "LƯU Ý: người khai (còn sống, là chủ hồ sơ) và người có công đã từ trần là HAI người "
            "khác nhau — không ghép thông tin của hai người vào nhau.\n"
            "Bước Thành phần hồ sơ: Bản khai Mẫu 12 vào ô 1; trích lục khai tử, căn cước và các "
            "giấy còn lại xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "xac-dinh-muc-do-khuyet-tat",
        # Cổng Bộ Y tế, cùng cách chọn cơ quan + wizard với ba thủ tục trợ cấp/mai táng ở trên.
        # KHÁC HẲN ở bước đính kèm: KHÔNG phải một dòng gộp, mà là các Ô UPLOAD CỐ ĐỊNH — planner
        # core (pipelines/khuyet_tat) trả target="fixed-slot" cho từng ô. Vì vậy TUYỆT ĐỐI không
        # đặt hideRepeatableHint: dồn hết tệp vào một ô là sai ô ngay.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.001699",
                "019d2bfe-b7cd-76e9-b909-bcf437629cb8",
            ],
            # Không trùng chữ với nhóm trợ cấp/mai táng nên một cụm là đủ tách.
            "textIncludes": ["mức độ khuyết tật"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Xác định, xác định lại mức độ khuyết tật và cấp Giấy xác nhận khuyết tật",
        "shortLabel": "Xác định mức độ khuyết tật và cấp Giấy xác nhận khuyết tật",
        "subtitle": "Xác định hoặc xác định lại mức độ khuyết tật, cấp Giấy xác nhận khuyết tật",
        "icon": "♿",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-b7cd-76e9-b909-bcf437629cb8",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Tên các mục dưới đây bám đúng ba ô upload của cổng (SLOTS trong pipelines/khuyet_tat) để
        # công dân mang giấy theo đúng ô, không phải gom một đống.
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị xác định, xác định lại mức độ khuyết tật "
             "(Mẫu số 01) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "giay_to_khuyet_tat", "name": "Bản sao giấy tờ liên quan đến khuyết tật: "
             "bệnh án, giấy khám, giấy ra viện, giấy tờ điều trị hoặc phẫu thuật", "icon": "🏥",
             "sides": 1, "repeatable": True},
            {"key": "ket_luan_y_khoa", "name": "Bản sao kết luận của Hội đồng Giám định y khoa "
             "hoặc kết luận của cơ sở y tế (nếu có)", "icon": "🩺",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người khuyết tật hoặc người đại diện "
             "đứng đơn", "icon": "🪪", "sides": 1, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị xác định, xác định lại mức độ khuyết tật (Mẫu số 01), đã ký — nguồn "
            "chính để điền form.\n"
            "2. Căn cước công dân của người khuyết tật hoặc người đại diện đứng đơn.\n"
            "3. Bản sao giấy tờ liên quan đến khuyết tật: bệnh án, giấy khám, giấy ra viện, giấy "
            "tờ điều trị hoặc phẫu thuật.\n"
            "4. Nếu có: bản sao kết luận của Hội đồng Giám định y khoa hoặc của cơ sở y tế.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước Thành phần hồ sơ: trang có các Ô UPLOAD RIÊNG cho từng loại giấy tờ, mỗi giấy "
            "được đính vào đúng ô của nó."
        ),
    },
    {
        "key": "ho-tro-mai-tang",
        # CÙNG cổng Bộ Y tế, cùng khung với "ho-tro-mai-tang-huu-tri-xa-hoi"; khác NHÓM ĐỐI TƯỢNG
        # (bảo trợ xã hội thay vì người hưởng trợ cấp hưu trí xã hội). Bảng thành phần hồ sơ cũng
        # chỉ một dòng Tờ khai → hideRepeatableHint.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.001731",
                "019d2bfe-b7dd-7239-b166-b6cd79d326b8",
            ],
            # "mai táng" trơn trùng với thủ tục mai táng cho người hưởng trợ cấp hưu trí → phải kèm
            # vế nhóm đối tượng.
            "textIncludes": ["mai táng cho đối tượng bảo trợ xã hội"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội",
        "shortLabel": "Hỗ trợ chi phí mai táng — đối tượng bảo trợ xã hội",
        "subtitle": "Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội đã mất",
        "icon": "🕯️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-b7dd-7239-b166-b6cd79d326b8",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị hỗ trợ chi phí mai táng "
             "(Mẫu số 02, Nghị định 176/2025/NĐ-CP) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "chung_tu", "name": "Giấy chứng tử hoặc trích lục khai tử của người đã mất",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng đơn đề nghị", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 02 ban hành kèm theo Nghị định số "
            "176/2025/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Giấy chứng tử hoặc trích lục khai tử của đối tượng bảo trợ xã hội đã mất.\n"
            "3. Căn cước công dân của người đứng đơn đề nghị.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước Thành phần hồ sơ: cổng chỉ có ĐÚNG MỘT dòng nên mọi tệp đều được đính vào dòng "
            "đó; tệp không phải Tờ khai vẫn đính được nhưng có cảnh báo để cán bộ soát."
        ),
    },
    {
        "key": "ho-tro-mai-tang-huu-tri-xa-hoi",
        # CÙNG cổng Bộ Y tế, CÙNG cách chọn cơ quan và wizard với "dieu-chinh-huu-tri-xa-hoi".
        # Bảng thành phần hồ sơ CHỈ CÓ MỘT DÒNG (Tờ khai Mẫu số 02, NĐ 176/2025) → hideRepeatableHint
        # như hưu trí: planner dồn mọi tệp vào dòng đó.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.014028",
                "019d2bff-3508-7268-b54b-6ce79a8cbf0e",
            ],
            # Ba thủ tục cùng cổng dùng chung chữ với nhau: "trợ cấp hưu trí xã hội" (với thủ tục
            # hưu trí) và "mai táng" (với thủ tục mai táng cho đối tượng BẢO TRỢ xã hội). Phải lấy
            # cụm ghép cả hai vế mới tách được khỏi cả hai.
            "textIncludes": ["mai táng đối với đối tượng hưởng trợ cấp hưu trí"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Hỗ trợ chi phí mai táng đối với đối tượng hưởng trợ cấp hưu trí xã hội",
        "shortLabel": "Hỗ trợ chi phí mai táng — người hưởng trợ cấp hưu trí xã hội",
        "subtitle": "Hỗ trợ chi phí mai táng cho người đang hưởng trợ cấp hưu trí xã hội đã mất",
        "icon": "🕯️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-3508-7268-b54b-6ce79a8cbf0e",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị hỗ trợ chi phí mai táng "
             "(Mẫu số 02, Nghị định 176/2025/NĐ-CP) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "chung_tu", "name": "Giấy chứng tử hoặc trích lục khai tử của người đã mất",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng đơn đề nghị", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 02 ban hành kèm theo Nghị định số "
            "176/2025/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Giấy chứng tử hoặc trích lục khai tử của người hưởng trợ cấp đã mất.\n"
            "3. Căn cước công dân của người đứng đơn đề nghị.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước Thành phần hồ sơ: cổng chỉ có ĐÚNG MỘT dòng nên mọi tệp đều được đính vào dòng "
            "đó; tệp không phải Tờ khai vẫn đính được nhưng có cảnh báo để cán bộ soát."
        ),
    },
    {
        "key": "tro-cap-xa-hoi-hang-thang",
        # CÙNG cổng Bộ Y tế và CÙNG cách chọn cơ quan với "dieu-chinh-huu-tri-xa-hoi" (DVCQG chọn
        # đủ Tỉnh + Xã rồi vào thẳng trang kê khai, không toggle "Sở", không trang chọn nơi+loại).
        # KHÁC ở bước đính kèm: bảng thành phần hồ sơ là BẢNG NHIỀU DÒNG TÍCH CHỌN (engine attp-row
        # của core) chứ không phải một dòng duy nhất → KHÔNG đặt hideRepeatableHint, và checklist
        # phải liệt kê đúng các dòng để công dân mang đủ giấy.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.001776",
                "019d2bfe-b7e6-740b-9573-24f800e8664d",
            ],
            # Hai thủ tục trợ cấp của cùng cổng có tên rất giống nhau; cụm "chăm sóc, nuôi dưỡng"
            # là phần CHỈ thủ tục này có, dùng nó để không nhận nhầm sang hưu trí xã hội.
            "textIncludes": ["chăm sóc, nuôi dưỡng hàng tháng"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng, hỗ trợ kinh phí "
            "chăm sóc, nuôi dưỡng hàng tháng"
        ),
        "shortLabel": "Trợ cấp xã hội hàng tháng cho đối tượng bảo trợ xã hội",
        "subtitle": "Trợ cấp xã hội hàng tháng, hỗ trợ kinh phí chăm sóc, nuôi dưỡng",
        "icon": "🤝",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-b7e6-740b-9573-24f800e8664d",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị trợ giúp xã hội (Mẫu 1a/1b/1c/1d/1đ) "
             "hoặc Tờ khai nhận chăm sóc, nuôi dưỡng (Mẫu 2a/2b/03) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của đối tượng hưởng trợ cấp "
             "(trẻ em chưa có căn cước thì mang Giấy khai sinh)", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khuyet_tat", "name": "Giấy xác nhận khuyết tật hoặc Biên bản giám định "
             "y khoa (nếu đối tượng là người khuyết tật)", "icon": "♿",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: xác nhận cư trú, xác nhận nhiễm HIV, "
             "xác nhận đang mang thai, căn cước của người khai thay", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đề nghị trợ giúp xã hội (Mẫu 1a/1b/1c/1d/1đ) HOẶC Tờ khai nhận chăm sóc, "
            "nuôi dưỡng (Mẫu 2a/2b/03), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của đối tượng hưởng trợ cấp; đối tượng là trẻ em thì Giấy khai "
            "sinh thay cho căn cước.\n"
            "3. Nếu có: Giấy xác nhận khuyết tật hoặc Biên bản giám định y khoa, Giấy xác nhận "
            "thông tin về cư trú, giấy tờ xác nhận nhiễm HIV hoặc đang mang thai, và căn cước "
            "của người nộp thay.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là ĐỐI TƯỢNG hưởng trợ cấp, không phải người đi nộp thay.\n"
            "Bước Thành phần hồ sơ: bảng có nhiều dòng, mỗi giấy tờ được tích vào đúng dòng của nó."
        ),
    },
    {
        "key": "cap-giay-phep-xay-dung-moi-nha-o-rieng-le",
        # Cổng Bộ Xây dựng dvc.moc.gov.vn (cùng nền iGate/Form.io với NOXH). KHÁC NOXH: DVCQG
        # chọn ĐỦ Tỉnh + Xã (ke_khai_links KHÔNG khai selectSoProvinces) rồi cổng mở HỘP THOẠI
        # "Chọn trường hợp giải quyết" TRƯỚC trang kê khai. maePortal bật để vào nhánh
        # maeAgencyBlock — trợ lý hỏi công dân chọn trường hợp ĐÚNG LÚC hộp thoại đang mở,
        # rồi tự chọn + bấm "Đồng ý". Ai tự bấm sang trang kê khai thì không bị hỏi.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.013225",
                "019d2bfe-9088-744d-aa0a-e846b6dce3d5",
            ],
            "textIncludes": ["cấp giấy phép xây dựng mới"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Cấp giấy phép xây dựng mới đối với công trình cấp III, cấp IV và nhà ở riêng lẻ"
        ),
        "shortLabel": "Cấp phép xây dựng mới",
        "subtitle": "Giấy phép xây dựng nhà ở riêng lẻ hoặc công trình cấp III, cấp IV",
        "icon": "🏗️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-9088-744d-aa0a-e846b6dce3d5",
        "needsAgencySelect": True,
        "maePortal": True,
        # portalMatch/portalAvoid là token ĐÃ FOLD DẤU để khớp option trong ô "Trường hợp giải
        # quyết" — tên option do cổng đặt, không cố định, nên khớp theo cụm đặc trưng thay vì
        # nguyên văn. Option ĐẦU là mặc định (chip tô đậm).
        "variants": {
            "options": [
                {"key": "nha_o_rieng_le", "label": "Nhà ở riêng lẻ",
                 "chip": "🏠 Nhà ở riêng lẻ", "portalMatch": "nha o rieng le",
                 "desc": "xây nhà ở của hộ gia đình, cá nhân"},
                {"key": "cong_trinh", "label": "Công trình cấp III, cấp IV",
                 "chip": "🏢 Công trình cấp III, cấp IV",
                 "portalMatch": "cong trinh", "portalAvoid": "nha o rieng le",
                 "desc": "công trình cấp III, cấp IV, không phải nhà ở riêng lẻ"},
            ],
        },
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp giấy phép xây dựng — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất (sổ đỏ) hoặc giấy tờ về "
             "quyền sử dụng đất", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "ban_ve", "name": "Bản vẽ xin cấp phép xây dựng (kèm chứng chỉ năng lực / "
             "chứng chỉ hành nghề thiết kế nếu có)", "icon": "📐", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ hộ / người nộp", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp giấy phép xây dựng, đã ký.\n"
            "2. Giấy chứng nhận quyền sử dụng đất hoặc giấy tờ về quyền sử dụng đất.\n"
            "3. Bản vẽ xin cấp phép xây dựng; kèm bản kê khai/chứng chỉ năng lực thiết kế, "
            "chứng chỉ hành nghề chủ nhiệm/chủ trì thiết kế nếu có.\n"
            "4. Căn cước công dân của chủ hộ / người nộp.\n"
            "Bước Thành phần hồ sơ: bảng của cổng chia thành nhiều KHỐI theo LOẠI CÔNG TRÌNH, "
            "mỗi khối lặp lại gần như y hệt bộ giấy tờ — hệ thống tự nhận loại công trình từ "
            "đơn/bản vẽ để đính đúng khối."
        ),
    },
    {
        "key": "dang-ky-thay-doi-noi-dung-ho-kinh-doanh",
        # HkdOnline (cùng cổng thành lập mới) — businessWorkflow "change": wizard 4 bước
        # (chọn CHN → TRA CỨU hộ KD theo mã số → chọn CHAPAR + hỏi đổi tên → Bắt đầu), trang
        # điền ĐỘNG theo businessFlow.pageOrder (pipeline so GCN cũ vs Thông báo, chỉ dựng
        # trang cần sửa + Người nộp hồ sơ). Bootstrap pha 1 dừng ở màn tra cứu để nhận giấy
        # tờ TRƯỚC (mã số nằm trong Thông báo/GCN) — xem flow._guide_login_on_page.
        "detect": {
            "urlIncludes": ["hokinhdoanh.dkkd.gov.vn"],
            "headingDisabled": True,
        },
        "label": "Đăng ký thay đổi nội dung đăng ký hộ kinh doanh",
        "shortLabel": "Thay đổi nội dung hộ kinh doanh",
        "subtitle": "Đổi tên, địa chỉ, ngành nghề, chủ hộ, vốn... của hộ kinh doanh đang hoạt động",
        "icon": "🔁",
        # Cùng điểm vào DVCQG với thành lập mới (đích là HkdOnline); rẽ nhánh ở wizard chọn loại.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-d76d-737f-81b9-69258b07240b",
        "needsAgencySelect": True,
        "businessWorkflow": "change",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "thong_bao", "name": "Thông báo thay đổi nội dung đăng ký hộ kinh doanh "
             "— đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn_cu", "name": "Giấy chứng nhận đăng ký hộ kinh doanh hiện tại (để lấy "
             "mã số và nội dung cũ)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ hộ / người nộp", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu có)", "icon": "📝",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "bien_ban", "name": "Biên bản họp thành viên hộ gia đình (nếu có)",
             "icon": "📋", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Hợp đồng mua bán/tặng cho, giấy tờ thừa kế hoặc giấy tờ "
             "khác (nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        # 7 trang (không có "Hình thức đăng ký"); thực tế điền theo pageOrder động của pipeline.
        "pages": [
            {"key": "dia-chi", "label": "Địa chỉ"},
            {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
            {"key": "ten-ho-kinh-doanh", "label": "Tên hộ kinh doanh"},
            {"key": "chu-ho-kinh-doanh", "label": "Thông tin về chủ hộ kinh doanh"},
            {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
            {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Thông báo thay đổi nội dung đăng ký hộ kinh doanh (đã ký).\n"
            "2. Giấy chứng nhận đăng ký hộ kinh doanh hiện tại — QUAN TRỌNG: hệ thống lấy mã "
            "số hộ kinh doanh từ đây để tra cứu.\n"
            "3. Căn cước công dân của chủ hộ / người nộp.\n"
            "4. Nếu có: văn bản ủy quyền, biên bản họp thành viên hộ gia đình, hợp đồng mua "
            "bán/tặng cho/thừa kế.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cham-dut-hoat-dong-ho-kinh-doanh",
        # HkdOnline, businessWorkflow "dissolution" — ĐI CHUNG wizard với nhánh thay đổi: cổng
        # gộp cả hai vào màn "Chọn loại đăng ký thay đổi" (radio DISSOLU, có AutoPostBack). Vì
        # workflow != "create" nên flow tự đặt stop_at="search-business": bootstrap dừng ở màn
        # TRA CỨU hộ kinh doanh để nhận giấy tờ TRƯỚC (mã số nằm trong GCN), chạy pipeline xong
        # FE mới đi nốt wizard. Engine FE đã có sẵn nhánh dissolution (trang Dissolution.aspx).
        "detect": {
            "urlIncludes": [
                "hokinhdoanh.dkkd.gov.vn",
                "019d2bfb-d748-72d1-848f-3607bc86e647",
            ],
            "headingDisabled": True,
        },
        "label": "Chấm dứt hoạt động hộ kinh doanh",
        "shortLabel": "Chấm dứt hộ kinh doanh",
        "subtitle": "Đóng, chấm dứt hoạt động hộ kinh doanh đang hoạt động",
        "icon": "🛑",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-d748-72d1-848f-3607bc86e647",
        "needsAgencySelect": True,
        "businessWorkflow": "dissolution",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "thong_bao", "name": "Thông báo về việc chấm dứt hoạt động hộ kinh doanh "
             "(Mẫu số 1) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn_cu", "name": "Bản gốc Giấy chứng nhận đăng ký hộ kinh doanh (để lấy mã "
             "số tra cứu)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "thue", "name": "Thông báo của cơ quan thuế về chấm dứt hiệu lực mã số thuế "
             "/ hoàn thành nghĩa vụ thuế", "icon": "🧾", "sides": 1, "repeatable": True},
            {"key": "bien_ban", "name": "Biên bản họp thành viên hộ gia đình (nếu hộ gia đình "
             "cùng thành lập)", "icon": "📋", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Căn cước công dân, văn bản ủy quyền hoặc giấy tờ khác",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        # Chỉ 2 trang: nội dung chấm dứt + người nộp hồ sơ (khớp registry lõi).
        "pages": [
            {"key": "cham-dut-hoat-dong", "label": "Chấm dứt hoạt động"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Thông báo về việc chấm dứt hoạt động hộ kinh doanh (Mẫu số 1), đã ký.\n"
            "2. Bản gốc Giấy chứng nhận đăng ký hộ kinh doanh — QUAN TRỌNG: hệ thống lấy mã số "
            "hộ kinh doanh từ đây để tra cứu.\n"
            "3. Thông báo của cơ quan thuế về chấm dứt hiệu lực mã số thuế hoặc hoàn thành nghĩa "
            "vụ thuế.\n"
            "4. Nếu hộ gia đình cùng thành lập: biên bản họp thành viên hộ gia đình.\n"
            "5. Nếu có: căn cước công dân, văn bản ủy quyền hoặc giấy tờ khác.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dang-ky-bien-phap-bao-dam-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm 01a) — key TRÙNG auto-fill nên pipeline
        # process/attach tự nối qua core_registry. Đường vào: DVCQG chọn TỈNH BẮC NINH (cố định,
        # agencyProvince — thủ tục của riêng tỉnh, KHÔNG lấy tỉnh tài khoản) → gạt toggle "Sở"
        # (KHÔNG chọn sở cụ thể) → Đồng ý → "Nộp trực tuyến" kết quả ĐẦU TIÊN (Văn phòng ĐK đất
        # đai Bắc Ninh) — agencySoFirst. Trang eForm BN có 2 tab CÙNG TRANG (Nhập đơn đăng ký /
        # Tải thành phần hồ sơ, không wizard) → samePageAttach: điền xong bot tự lập kế hoạch và
        # đính kèm luôn, không chờ công dân chuyển bước; FE tự bấm tab trước khi điền/đính.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.011441"],
            "textIncludes": ["đăng ký biện pháp bảo đảm bằng quyền sử dụng đất"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Tỉnh Bắc Ninh] Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        "shortLabel": "Đăng ký biện pháp bảo đảm đất đai (Bắc Ninh)",
        "subtitle": "Đăng ký thế chấp quyền sử dụng đất, tài sản gắn liền với đất tại Bắc Ninh",
        "icon": "🏦",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-7e5d-7318-a451-84198f210213",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Phiếu yêu cầu đăng ký biện pháp bảo đảm (Mẫu 01a) — đã kê "
             "khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "hop_dong", "name": "Hợp đồng thế chấp / bảo đảm (kèm lời chứng công chứng "
             "nếu có)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất (sổ đỏ / sổ hồng)",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của bên bảo đảm / bên nhận bảo đảm",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "GCN đăng ký doanh nghiệp, giấy giới thiệu / ủy quyền hoặc "
             "giấy tờ khác", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu yêu cầu đăng ký biện pháp bảo đảm (Mẫu số 01a) đã kê khai, ký — nguồn "
            "chính điền đơn.\n"
            "2. Hợp đồng thế chấp/bảo đảm (kèm lời chứng công chứng nếu có).\n"
            "3. Giấy chứng nhận quyền sử dụng đất (sổ đỏ/sổ hồng).\n"
            "4. Căn cước công dân của bên bảo đảm/bên nhận; nếu nộp thay: giấy giới thiệu hoặc "
            "văn bản ủy quyền; tổ chức: Giấy chứng nhận đăng ký doanh nghiệp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "xoa-dang-ky-bien-phap-bao-dam-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm 03a) — anh em với đăng ký (1.011441),
        # cùng nền tảng 2 tab CÙNG TRANG → samePageAttach + agencyProvince cố định Bắc Ninh +
        # agencySoFirst. Key TRÙNG auto-fill → pipeline process/attach tự nối. ⚠ maTTHC=1.011443
        # TRÙNG trang hoàn thiện tài khoản VNeID (/vneidsso) nhưng trang đó detect theo PATH,
        # còn đây neo thêm textIncludes tên thủ tục → không nhầm.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.011443"],
            "textIncludes": ["xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Tỉnh Bắc Ninh] Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        "shortLabel": "Xóa đăng ký biện pháp bảo đảm đất đai (Bắc Ninh)",
        "subtitle": "Xóa thế chấp quyền sử dụng đất, tài sản gắn liền với đất tại Bắc Ninh",
        "icon": "🏦",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-7e53-77ba-aa3f-086a9b9717ba",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu 03a) — "
             "đã ký, có xác nhận của bên nhận bảo đảm (ngân hàng)", "icon": "📄", "sides": 1,
             "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất (bản gốc, gồm cả trang "
             "mục IV 'Những thay đổi sau khi cấp')", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "hop_dong", "name": "Hợp đồng thế chấp / văn bản xóa thế chấp (nếu có)",
             "icon": "📑", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người yêu cầu (bên bảo đảm)",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Giấy giới thiệu / văn bản ủy quyền hoặc giấy tờ khác",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a) đã ký, có chữ ký & con "
            "dấu bên nhận bảo đảm (ngân hàng) — nguồn chính điền phiếu.\n"
            "2. Bản gốc Giấy chứng nhận QSDĐ (sổ đỏ/sổ hồng), GỒM cả trang mục IV 'Những thay "
            "đổi sau khi cấp'.\n"
            "3. Căn cước công dân của người yêu cầu (bên bảo đảm); Hợp đồng thế chấp nếu có.\n"
            "4. Nếu nộp thay: Giấy giới thiệu / văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
]

# Materialize reusable flow capabilities once. Runtime and extension continue consuming
# the same resolved procedure contract; they never need procedure-specific profile logic.
PROCEDURES = [resolve_flow_profile(procedure) for procedure in PROCEDURES]


# Map procedure key → hàm pipeline.run
# Escape hatch cho thủ tục có owner extraction khác profile; map theo key luôn được ưu tiên.
_OWNER_INFO_PIPELINE_BY_PROCEDURE: dict[str, object] = {}

_OWNER_INFO_PIPELINE_BY_PROFILE = {
    "tu-phap": tu_phap_owner_info,
}

_BY_KEY = {p["key"]: p for p in PROCEDURES}

# Thứ tự card trên màn chào là ưu tiên trải nghiệm, độc lập với thứ tự khai báo pipeline.
# Giữ nhóm chứng thực ở cuối để các thủ tục hộ tịch thường dùng xuất hiện trước; thủ tục mới
# chưa được xếp hạng sẽ tự nằm ở giữa, không chen xuống sau hai card chứng thực.
_PUBLIC_PRIORITY_KEYS = (
    "ket-hon",
    "khai-sinh-dang-ky",
    # Chứng thực bản sao dùng nhiều tại quầy → kéo lên vị trí 3 (yêu cầu 09/09/2026);
    # chứng thực chữ ký vẫn nằm cuối danh sách.
    "chung-thuc-ban-sao",
    "trich-luc-ks",
    "xac-nhan-tinh-trang-hon-nhan",
    "khai-sinh-dang-ky-lai",
    "khai-tu",
    "dang-ky-kinh-doanh",
)
_PUBLIC_TRAILING_KEYS = (
    "chung-thuc-chu-ky",
)

# Thủ tục "hay dùng" hiện dạng ô (tile) ngay màn chào — phần còn lại nằm trong sheet "Xem tất
# cả". THỨ TỰ ở đây = thứ tự ô trái→phải, trên→dưới (FE xếp theo frequentOrder, độc lập thứ tự
# public_list). Đổi danh sách/thứ tự ô chỉ cần sửa tuple này (cấu hình BE, KHÔNG phát hành lại
# extension). Thủ tục vắng ở đây vẫn có trong sheet.
_HOME_FREQUENT_KEYS = (
    "ket-hon",
    "chung-thuc-ban-sao",
    "chung-thuc-chu-ky",
    "khai-sinh-dang-ky",
    "trich-luc-ks",
    "khai-sinh-dang-ky-lai",
    "xac-nhan-tinh-trang-hon-nhan",
    "dang-ky-kinh-doanh",
)


def get_procedure(key: str) -> dict | None:
    return _BY_KEY.get(key)


def get_pipeline(key: str):
    return core_registry.get_pipeline(key)


def get_owner_info_pipeline(key: str):
    direct = _OWNER_INFO_PIPELINE_BY_PROCEDURE.get(key)
    if direct is not None:
        return direct
    procedure = _BY_KEY.get(key) or {}
    return _OWNER_INFO_PIPELINE_BY_PROFILE.get(procedure.get("flowProfile"))


def get_attach_pipeline(key: str):
    return core_registry.get_attach_pipeline(key)


def portal_submit_rules() -> dict[str, dict]:
    """Nhận diện nút "Gửi hồ sơ" theo CỔNG — khai một chỗ duy nhất ở app/procedures/portal_submit.py."""
    return core_portal_submit.portal_submit_rules()


def _validate_profile_dispatch() -> None:
    """Fail fast when a profiled procedure is missing one of its backend engines."""
    for key in _HOME_FREQUENT_KEYS:
        if key not in _BY_KEY:
            raise RuntimeError(f"_HOME_FREQUENT_KEYS có key không tồn tại: {key}")
    for procedure in PROCEDURES:
        if not procedure.get("flowProfile"):
            continue
        key = procedure["key"]
        if (procedure.get("ownerInfo") or {}).get("enabled") and not get_owner_info_pipeline(key):
            raise RuntimeError(f"Thủ tục {key} bật ownerInfo nhưng thiếu owner pipeline.")
        if procedure.get("mode") != "attach" and not get_pipeline(key):
            raise RuntimeError(f"Thủ tục {key} dùng flow profile nhưng thiếu process pipeline.")
        if procedure.get("hasAttachmentStep") and not get_attach_pipeline(key):
            raise RuntimeError(f"Thủ tục {key} dùng flow profile nhưng thiếu attach pipeline.")


_validate_profile_dispatch()


def public_list() -> list[dict]:
    leading = [_BY_KEY[key] for key in _PUBLIC_PRIORITY_KEYS if key in _BY_KEY]
    reserved = {*_PUBLIC_PRIORITY_KEYS, *_PUBLIC_TRAILING_KEYS}
    middle = [procedure for procedure in PROCEDURES if procedure["key"] not in reserved]
    trailing = [_BY_KEY[key] for key in _PUBLIC_TRAILING_KEYS if key in _BY_KEY]
    return [*leading, *middle, *trailing]


def frequent_order(key: str) -> int | None:
    """Vị trí ô "hay dùng" (0-based) hoặc None nếu thủ tục không lên ô. FE xếp ô theo số này."""
    try:
        return _HOME_FREQUENT_KEYS.index(key)
    except ValueError:
        return None


def is_allowed_in_province(proc: dict | None, province_slug: str | None) -> bool:
    """Thủ tục có được hiện/chạy cho tài khoản tỉnh `province_slug` không.

    `provinceOnly` (list slug tỉnh) trên entry = KHÓA theo tỉnh. Vắng field → mọi tỉnh (mặc
    định, không đổi thủ tục cũ). `province_slug` rỗng (account thiếu tỉnh) → KHÔNG khóa, tránh
    ẩn nhầm hết.
    """
    if not proc:
        return False
    only = proc.get("provinceOnly")
    if not only:
        return True
    if not province_slug:
        return True
    return province_slug in only


def public_list_for(province_slug: str | None) -> list[dict]:
    """public_list() đã lọc theo tỉnh account — thủ tục khóa tỉnh khác bị bỏ khỏi màn chào."""
    return [p for p in public_list() if is_allowed_in_province(p, province_slug)]
