"""Metadata và thứ tự thủ tục chỉ dành cho kênh Handfree.

Core process/attach luôn lấy từ ``app.procedures.registry``. File này được port từ
registry Handfree cũ để giữ nguyên card, flow profile và checklist, nhưng không còn
sở hữu bản sao pipeline nghiệp vụ.
"""
import re
from copy import deepcopy

from app.channels.handfree.owner_info import run as tu_phap_owner_info
from app.channels.handfree.flow_profiles import resolve_flow_profile
from app.procedures import agency_plans
from app.procedures import ke_khai_links as core_ke_khai_links
from app.procedures import portal_submit as core_portal_submit
from app.procedures import registry as core_registry
from app.pipelines._shared.naming import fold

# Cổng Bộ Xây dựng: nhãn "Trường hợp giải quyết" có chữ "nhà ở riêng lẻ" → form nhánh nhà ở
# (element ...NhaO); còn lại là nhánh công trình (...KhongTheoTuyen). Dùng chung cho GPXD mới
# và sửa chữa, cải tạo (cùng process cap_giay_phep_xay_dung, đọc options["constructionVariant"]).
_GPXD_CASE_OPTIONS = [
    {"match": "nha o rieng le", "options": {"constructionVariant": "nha_o_rieng_le"}},
    {"match": "", "options": {"constructionVariant": "khong_theo_tuyen"}},
]

# Cổng Bắc Ninh (Liferay): khối "Thông tin trong trường hợp được ủy quyền" (doiTuongKhac*). Công dân chọn
# đối tượng thực hiện có ủy quyền → run_process chạy thêm pipeline purpose="authorized_person" (cùng logic
# nút "Điền thông tin người ủy quyền" của auto-fill) và ghép vào lệnh điền; extension tick ô bổ sung, chọn
# loại đối tượng (subjectOption) rồi mới điền khối đó.
_BN_AUTHORIZED_PERSON = {
    "executionSubjects": ["authorized_person", "enterprise_authorized"],
    "subjectOption": "Cá nhân khác là Công dân Việt Nam",
}

# Cổng Bộ Y tế dichvucongbyt.moh.gov.vn (stepper iGate 1 Thông tin hồ sơ → 2 Thành phần hồ sơ →
# 3 Hình thức nhận kết quả → 4 Nộp hồ sơ = màn đã nộp). Đính kèm xong: nút sang bước 3 (trợ lý bấm
# "Tiếp tục"), chọn ô mat-select[formcontrolname="receivingKind"] theo thẻ, rồi NHẮC công dân tự tích ô
# cam đoan + nhập Mã xác nhận (captcha) và bấm nộp — hai việc đó trợ lý không làm hộ (selfSubmit).
# Nhãn option đúng nguyên văn trên cổng (crawl 23/10/2026); cổng chọn sẵn "Nhận trực tuyến". Chọn bưu
# điện thì cổng mọc 2 ô tích không bắt buộc "Đăng ký nộp hồ sơ tại nhà" / "Đăng ký nhận kết quả tại nhà".
# Gán cho MỌI thủ tục có urlScope cổng này ở cuối danh sách; thủ tục tự khai guidedSteps thì giữ nguyên.
_BYT_HOST = "dichvucongbyt.moh.gov.vn"
_BYT_RESULT_STEP = 3
_BYT_GUIDED_STEPS = {
    "attachToResult": True,
    # Extension cũ không có engine bấm "Tiếp tục"/chọn mat-select → giữ câu "tự bấm Nộp hồ sơ" cũ.
    "capability": "supportsIgateResultStep",
    "selfSubmit": True,
    "attachmentStepLabel": "Thành phần hồ sơ",
    "resultStepLabel": "Hình thức nhận kết quả",
    "nextLabel": "Tiếp tục",
    # Nút nộp ở bước 3 ghi "Tiếp tục" (cùng nhãn nút chuyển bước), không phải "Nộp hồ sơ".
    "submitLabel": "Tiếp tục",
    "resultMethods": [
        {"key": "online", "label": "Nhận trực tuyến", "icon": "🌐",
         "desc": "Nhận bản điện tử ngay trên hệ thống.", "default": True},
        {"key": "direct", "label": "Nhận trực tiếp", "icon": "🏛️",
         "desc": "Đến cơ quan tiếp nhận để nhận kết quả."},
        {"key": "postal", "label": "Nhận trực tiếp tại nhà qua bưu điện", "icon": "📮",
         "desc": "Bưu điện trả kết quả tại nhà, phí bưu chính trả trực tiếp cho nhân viên bưu điện.",
         "needsInput": True},
    ],
}

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
        "shortLabel": "Liên thông đăng ký khai sinh",
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
        # Dẫn đủ 6 bước của cổng liên thông (chat/lien_thong.py), chỉ bật cho extension khai
        # supportsLienThongFlow. resultGroups: các ô "hình thức nhận kết quả" ở bước 5, mỗi giấy tờ
        # một ô; `place` = ô chữ "nơi nhận" đi kèm để đọc cho công dân nghe.
        "lienThongFlow": {
            "resultGroups": [
                {"name": "DkksNkqHinhThuc", "label": "Giấy khai sinh", "place": "DkksNoiTra"},
                {"name": "DkttNkqHinhThuc", "label": "Đăng ký thường trú"},
                {"name": "BhytNkqHinhThuc", "label": "Thẻ BHYT", "place": "BhytNkqTaiCoQuan"},
                {"name": "CapTheCCNkqHinhThuc", "label": "Thẻ căn cước", "place": "CapTheCCNkqTaiCoQuan"},
            ],
        },
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
        "key": "khai-sinh-dang-ky-thuong",
        "detect": {
            "urlScope": ["://dichvucong.gov.vn/nop-ho-so"],
            "textIncludes": ["thủ tục đăng ký khai sinh", "người được đăng ký khai sinh"],
            "textPriority": True,
            "headingDisabled": True,
        },
        "label": "Thủ tục đăng ký khai sinh",
        "shortLabel": "Đăng ký Khai sinh",
        "subtitle": "Chỉ đăng ký khai sinh (không kèm thường trú, BHYT)",
        "icon": "👶",
        # Trang nộp một trang của Cổng DVC quốc gia (form + đính kèm + nhận kết quả).
        "flowProfile": "tu-phap-moi",
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
        # Checklist phiên QR/scan. Tờ khai + CCCD là nguồn chính điền form; attach planner tự
        # phân loại theo nội dung (cử người giám hộ / cam đoan / giấy tờ chỗ ở…) nên các giấy tờ
        # chứng minh gom chung slot "khac". Mỗi nhóm tính theo TỆP.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đăng ký giám hộ", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người yêu cầu và người giám hộ",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "ho_tich", "name": "Giấy khai sinh hoặc giấy tờ tùy thân của người được giám hộ",
             "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản cử người giám hộ, giấy tờ chứng minh điều kiện giám hộ "
             "(nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu có)", "icon": "📜",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox như các thủ tục tư pháp khác; bật lại khi cần
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
        "key": "dang-ky-cham-dut-giam-ho",
        "detect": {"textIncludes": ["Thủ tục đăng ký chấm dứt giám hộ"], "headingDisabled": True},
        "label": "Thủ tục đăng ký chấm dứt giám hộ",
        "shortLabel": "Chấm dứt Giám hộ",
        "subtitle": "Đăng ký chấm dứt việc giám hộ đã đăng ký",
        "icon": "🤝",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6724-715f-822c-28e986912730",
        # Checklist phiên QR/scan. Bảng thành phần chỉ có STT2 "Giấy tờ làm căn cứ chấm dứt giám
        # hộ" + STT3 "Văn bản ủy quyền": attach planner gom mọi giấy căn cứ/CCCD/khai sinh vào STT2.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đăng ký chấm dứt giám hộ", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người yêu cầu và người giám hộ",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "ho_tich", "name": "Giấy khai sinh hoặc giấy tờ tùy thân của người được giám hộ",
             "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Trích lục đăng ký giám hộ, giấy tờ làm căn cứ chấm dứt giám hộ "
             "(nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu có)", "icon": "📜",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,  # TẠM TẮT rà soát bbox như các thủ tục tư pháp khác; bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đăng ký chấm dứt giám hộ.\n"
            "2. CCCD/CMND của người yêu cầu và người giám hộ.\n"
            "3. Giấy khai sinh/giấy tờ định danh của người được giám hộ.\n"
            "4. Trích lục đăng ký giám hộ và giấy tờ làm căn cứ chấm dứt giám hộ (nếu có)."
            "\nBước 3: tờ khai bản giấy thêm thành phần hồ sơ mới; giấy tờ làm căn cứ chấm dứt, "
            "giấy khai sinh và CCCD/căn cước vào STT 2; văn bản ủy quyền vào STT 3."
        ),
    },
    {
        "key": "trich-luc-ks",
        "detect": {
            "urlScope": ["://dichvucong.gov.vn/nop-ho-so"],
            "textIncludes": [
                "cấp bản sao trích lục hộ tịch, bản sao giấy khai sinh",
                "thông tin người được cấp giấy tờ hộ tịch",
            ],
            "textPriority": True,
            "headingDisabled": True,
        },
        "label": "Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh",
        "shortLabel": "Bản sao Trích lục hộ tịch",
        "subtitle": "Trích lục khai sinh, kết hôn, khai tử",
        "icon": "📜",
        # Trang nộp một trang của Cổng DVC quốc gia (form + đính kèm + nhận kết quả).
        "flowProfile": "tu-phap-moi",
        "supportsSplitDocuments": True,
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
        "supportsSplitDocuments": True,
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
        "supportsSplitDocuments": True,
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
        # Cùng eForm "Tờ khai đăng ký khai sinh" với đăng ký lại khai sinh (1.004884) nhưng người được
        # khai sinh CHƯA TỪNG đăng ký khai sinh, chỉ có sẵn hồ sơ, giấy tờ cá nhân (CCCD, học bạ...).
        # Planner đính kèm chưa có nhánh tách giấy tờ → không bật supportsSplitDocuments.
        "key": "khai-sinh-da-co-ho-so",
        "detect": {"urlIncludes": ["maThuTuc=1.004772"]},
        "label": "Thủ tục đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân",
        "shortLabel": "Khai sinh (đã có giấy tờ cá nhân)",
        "subtitle": "Khai sinh cho người chưa từng đăng ký nhưng đã có CCCD, học bạ, bằng cấp…",
        "icon": "🪪",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6711-733d-b674-fc3d805e70c8",
        # Mỗi slot tính theo TỆP, không theo mặt; checklist tự hiện "Đã nhận X tệp".
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "khac", "name": "Hồ sơ, giấy tờ cá nhân đã có (CCCD, học bạ, bằng cấp, thẻ BHYT…)",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai đăng ký khai sinh (nếu có)", "icon": "📄",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cam_doan", "name": "Bản cam đoan chưa được đăng ký khai sinh (nếu có)",
             "icon": "✍️", "sides": 1, "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu có)", "icon": "📜",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Hồ sơ, giấy tờ cá nhân đã có: CCCD, thẻ BHYT, giấy tờ cư trú, học bạ, bằng tốt nghiệp, "
            "giấy chứng nhận kết hôn, trích lục khai tử của cha/mẹ...\n"
            "2. Tờ khai đăng ký khai sinh và bản cam đoan chưa được đăng ký khai sinh (nếu có).\n"
            "3. Văn bản ủy quyền (nếu nhờ người khác làm thay).\n"
            "Hệ thống tự nhận dạng người được khai sinh, cha, mẹ theo nội dung giấy tờ.\n"
            "Bước 3: bản cam đoan vào STT 2; giấy tờ cá nhân dồn chung vào STT 3; ủy quyền vào STT 5."
        ),
    },
    {
        "key": "khai-tu",
        "detect": {
            "urlIncludes": ["formalityId=019d2bfd-3fac-7489-b53b-9c6c958f2da4"],
            "urlScope": ["//dichvucong.gov.vn/nop-ho-so"],
            "textIncludes": ["thủ tục đăng ký khai tử", "người được đăng ký khai tử"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thủ tục đăng ký khai tử",
        "shortLabel": "Đăng ký Khai tử",
        "subtitle": "Thủ tục đăng ký khai tử trong nước",
        "icon": "🕯️",
        # Trang nộp một trang của Cổng DVC quốc gia (form + đính kèm + nhận kết quả).
        "flowProfile": "tu-phap-moi",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fac-7489-b53b-9c6c958f2da4",
        # Cài đặt "Tách giấy tờ" → planner chia tệp theo trang, đặt từng giấy vào đúng dòng có sẵn.
        "supportsSplitDocuments": True,
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
        "key": "khai-tu-lien-thong",
        # Liên thông khai tử nằm trên cổng riêng lienthong.dichvucong.gov.vn (SPA hash-route, Angular)
        # như liên thông khai sinh → nhận diện THEO URL, mã 1.006714 (cùng URL với app/procedures/registry.py
        # — đổi mã một bên phải đổi cả bên kia). KHÁC "khai-tu" ở trên (Cổng DVC quốc gia, SurveyJS).
        "detect": {
            "urlIncludes": ["lienthong.dichvucong.gov.vn/#/ke-khai/1.006714"],
            "headingDisabled": True,
        },
        "review": False,  # cùng lý do với liên thông khai sinh: đỡ 1 lượt OCR rà soát bbox
        "label": "Liên thông đăng ký khai tử, xóa đăng ký thường trú, trợ cấp mai táng phí",
        "shortLabel": "Liên thông đăng ký khai tử",
        "subtitle": "Khai tử + xóa đăng ký thường trú + trợ cấp mai táng phí",
        "icon": "🕯️",
        "keKhaiUrl": "https://lienthong.dichvucong.gov.vn/#/ke-khai/1.006714",
        # Trích xuất dùng chung agent "khai-tu" nên checklist giữ cùng bộ key với "khai-tu".
        # CCCD chỉ để đọc thông tin, planner không đính (bước 04 chỉ có dòng giấy báo tử/chứng cứ thay thế).
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
        # Form Angular — chế độ agent: không gắn role, BE tự phân biệt người yêu cầu/người chết.
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân của người yêu cầu và người được khai tử nếu có (chỉ để đọc thông tin).\n"
            "2. Giấy báo tử hoặc giấy tờ thay thế giấy báo tử.\n"
            "3. Tờ khai đăng ký khai tử bản giấy nếu có.\n"
            "4. Giấy tờ liên quan khác.\n"
            "Người yêu cầu do cổng điền sẵn từ VNeID; thông tin chủ hộ và mai táng phí cán bộ tự chọn.\n"
            "Bước đính kèm: giấy báo tử và tờ khai vào dòng 1; chứng cứ thay thế giấy báo tử "
            "(người chết đã lâu) vào dòng 2."
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
        "supportsSplitDocuments": True,
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
        "supportsSplitDocuments": True,
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
        "key": "khai-sinh-ket-hop-nhan-cha-me-con",
        "detect": {"urlIncludes": ["maThuTuc=1.000689"]},
        "label": "Thủ tục đăng ký khai sinh kết hợp đăng ký nhận cha, mẹ, con",
        "shortLabel": "Khai sinh kết hợp nhận Cha, Mẹ, Con",
        "subtitle": "Khai sinh cho con đồng thời nhận cha, mẹ, con",
        "icon": "👶",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3faf-768a-9224-9cb889436133",
        # Bước Kê khai thông tin KHÔNG có tờ khai: hai mẫu điện tử nằm ở dòng 1, 2 của bảng Thành
        # phần hồ sơ, chỉ hiện ra khi công dân tự bấm nút "Khai tờ khai" của dòng đó. Trợ lý nhận
        # giấy tờ xong thì CHỜ: bảo công dân mở từng tờ khai rồi bấm "Điền tờ khai"; pipeline điền
        # đúng mẫu đang mở theo formVariant. Điền đủ hai tờ khai mới sang đính kèm như thường.
        "declarationEforms": [
            {"variant": "birth_registration", "row": 1, "label": "Tờ khai đăng ký khai sinh"},
            {"variant": "parent_child_recognition", "row": 2,
             "label": "Tờ khai đăng ký nhận cha, mẹ, con"},
        ],
        # Tờ khai giấy là nguồn chính của quan hệ cha/mẹ/con; CCCD sides=4 cho cha + mẹ × 2 mặt.
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đăng ký khai sinh và tờ khai nhận cha, mẹ, con",
             "icon": "📄", "sides": 2},
            {"key": "cccd", "name": "CCCD của người yêu cầu và các bên (cha, mẹ)", "icon": "🪪",
             "sides": 4},
            {"key": "chung_sinh", "name": "Giấy chứng sinh", "icon": "📃", "sides": 1},
            {"key": "khac", "name": "Chứng cứ quan hệ cha, mẹ, con (kết quả ADN…), giấy tờ chứng minh "
             "tình trạng hôn nhân (nếu có)", "icon": "📎", "sides": 5, "optional": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để điền cả hai mẫu điện tử:\n"
            "1. Tờ khai đăng ký khai sinh.\n"
            "2. Tờ khai đăng ký nhận cha, mẹ, con.\n"
            "3. Giấy chứng sinh.\n"
            "4. CCCD/Căn cước của người yêu cầu và các bên liên quan.\n"
            "5. Kết quả ADN hoặc văn bản xác nhận quan hệ cha, mẹ, con.\n"
            "6. Nếu có: giấy chứng tử, quyết định/bản án ly hôn chứng minh tình trạng hôn nhân.\n"
            "Điền: công dân bấm \"Khai tờ khai\" ở dòng 1 rồi dòng 2 của Thành phần hồ sơ, mỗi lần "
            "tờ khai mở ra thì bấm \"Điền tờ khai\" trong Trợ lý.\n"
            "Bước đính kèm: tờ khai giấy chỉ dùng để OCR; giấy chứng sinh vào STT 3; "
            "kết quả ADN/văn bản giám định vào STT 4; CCCD và chứng cứ tình trạng hôn nhân "
            "được thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "dang-ky-nuoi-con-nuoi-trong-nuoc",
        "detect": {"textIncludes": ["Đăng ký việc nuôi con nuôi trong nước"], "headingDisabled": True},
        "label": "Đăng ký việc nuôi con nuôi trong nước",
        "shortLabel": "Nuôi con nuôi trong nước",
        "subtitle": "Đăng ký việc nhận nuôi con nuôi trong nước",
        "icon": "🤱",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-9dae-705f-a893-0c4e1f0c32a7",
        # Giống khai sinh kết hợp nhận cha, mẹ, con: Kê khai thông tin KHÔNG có tờ khai, đơn xin nhận
        # con nuôi (eForm NCNV5) nằm ở dòng 5 bảng Thành phần hồ sơ, chỉ hiện khi công dân bấm "Khai tờ
        # khai". Dòng 6 (Đơn đăng ký nhu cầu nhận trẻ em) chưa có pipeline → không khai ở đây.
        "declarationEforms": [
            {"variant": "adoption_application", "row": 5, "label": "Đơn xin nhận con nuôi"},
        ],
        # Đơn là nguồn chính của cả hồ sơ; CCCD sides=4 cho cha + mẹ nuôi × 2 mặt.
        "requiredDocs": [
            {"key": "to_khai", "name": "Đơn xin nhận con nuôi", "icon": "📄", "sides": 4},
            {"key": "cccd", "name": "CCCD của cha, mẹ nuôi", "icon": "🪪", "sides": 4},
            {"key": "ho_tich", "name": "Giấy khai sinh của trẻ được nhận làm con nuôi", "icon": "📜",
             "sides": 1},
            {"key": "chung_minh_tthn", "name": "Giấy chứng nhận kết hôn (vợ chồng cùng nhận) hoặc giấy "
             "xác nhận tình trạng hôn nhân (người đơn thân)", "icon": "💍", "sides": 1},
            {"key": "suc_khoe", "name": "Giấy khám sức khỏe của cha, mẹ nuôi", "icon": "🩺", "sides": 2},
            {"key": "khac", "name": "Giấy tờ chứng minh chỗ ở, thu nhập; ảnh, giấy khám sức khỏe của trẻ; "
             "giấy tờ của cha/mẹ đẻ (nếu có)", "icon": "📎", "sides": 5, "optional": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để điền đơn xin nhận con nuôi:\n"
            "1. Đơn xin nhận con nuôi trong nước — nguồn chính của phần cha/mẹ nuôi, con nuôi, nơi trẻ đang sống.\n"
            "2. CCCD/căn cước của cha mẹ nuôi; giấy chứng nhận kết hôn (vợ chồng cùng nhận).\n"
            "3. Giấy khai sinh của trẻ.\n"
            "4. Giấy khám sức khỏe, giấy tờ chứng minh chỗ ở/thu nhập (sổ đỏ, bảng lương, xác nhận thu nhập), "
            "ảnh của trẻ, giấy tờ của mẹ đẻ nếu có.\n"
            "Điền: công dân bấm \"Khai tờ khai\" ở dòng 5 (Đơn xin nhận con nuôi) của Thành phần hồ sơ, "
            "tờ khai mở ra thì bấm \"Điền tờ khai\" trong Trợ lý.\n"
            "Bước đính kèm: CCCD cha mẹ nuôi→STT 1; giấy khám sức khỏe cha mẹ nuôi→STT 2; giấy tờ hoàn "
            "cảnh, chỗ ở, thu nhập→STT 3; giấy chứng nhận kết hôn→STT 4; STT 5–6 là tờ khai trên cổng, "
            "không đính file. Giấy khai sinh, giấy khám sức khỏe, ảnh của trẻ, CCCD/giấy tờ của mẹ đẻ "
            "được thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "thay-doi-cai-chinh-ho-tich",
        "detect": {
            "urlScope": ["://dichvucong.gov.vn/nop-ho-so"],
            "textIncludes": [
                "thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
                "thông tin về người có nội dung thay đổi",
            ],
            "textPriority": True,
            "headingDisabled": True,
        },
        "label": "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
        "shortLabel": "Cải chính hộ tịch",
        "subtitle": "Thay đổi, bổ sung thông tin hộ tịch",
        "icon": "📝",
        # Trang nộp một trang của Cổng DVC quốc gia (form + đính kèm + nhận kết quả).
        "flowProfile": "tu-phap-moi",
        # URL kê khai đã xác minh trong ke_khai_links.json (mã TTHC 1.004859).
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
        "detect": {
            "urlIncludes": ["formalityId=019d2bfd-6eb3-7019-bf3f-fc58c9ee44b9"],
            "urlScope": ["//dichvucong.gov.vn/nop-ho-so"],
            "textIncludes": [
                "thủ tục cấp giấy xác nhận tình trạng hôn nhân",
                "quan hệ với người được cấp giấy xác nhận tình trạng hôn nhân",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thủ tục cấp Giấy xác nhận tình trạng hôn nhân",
        "shortLabel": "Xác nhận tình trạng hôn nhân",
        "subtitle": "Cấp giấy xác nhận độc thân / tình trạng hôn nhân",
        "icon": "💍",
        # Trang nộp một trang của Cổng DVC quốc gia (form + đính kèm + nhận kết quả).
        "flowProfile": "tu-phap-moi",
        "supportsSplitDocuments": True,
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
            "Không cần chọn trước loại giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Bước 3: giấy XNTTHN đã cấp vào dòng 1, bản án ly hôn / giấy chứng tử vào dòng 2, văn bản ủy quyền "
            "dòng 3; giấy tờ khác đính chung dòng 2."
        ),
    },
    {
        "key": "xac-nhan-thong-tin-ho-tich",
        # Mã 2.002516, cổng Bộ Tư pháp. Pipeline trả HAI bộ ô: trang cổng Form.io (data[...]: Phần 1 người
        # nộp = người yêu cầu, Phần 2 chủ hồ sơ = người được xác nhận) và eForm hộ tịch x-* trong iframe
        # tokhaidientu; extension tách bộ theo frame (fill-core.js). Planner đính kèm chưa có nhánh tách
        # giấy tờ → không bật supportsSplitDocuments.
        "detect": {
            "urlIncludes": ["maThuTuc=2.002516"],
            "textIncludes": ["xác nhận thông tin hộ tịch"],
            "headingDisabled": True,
        },
        "label": "Xác nhận thông tin hộ tịch",
        "shortLabel": "Xác nhận thông tin hộ tịch",
        "subtitle": "Xác nhận thông tin hộ tịch đã đăng ký (khai sinh, kết hôn, khai tử…)",
        "icon": "🧾",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-a586-71fe-8c10-836e09f0a879",
        # Mỗi nhóm tính theo TỆP, không theo mặt; checklist tự hiện "Đã nhận X tệp".
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị xác nhận thông tin hộ tịch", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "ho_tich", "name": "Giấy khai sinh của người được xác nhận", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "CCCD của người yêu cầu và người được xác nhận (nếu có)", "icon": "🪪",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu có)", "icon": "🖋️",
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
            "1. Tờ khai đề nghị xác nhận thông tin hộ tịch (có chữ ký người yêu cầu).\n"
            "2. Giấy khai sinh của người được xác nhận.\n"
            "3. CCCD/CMND của người yêu cầu và của người được xác nhận (nếu có).\n"
            "4. Nếu có: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Bước Thành phần hồ sơ: dòng 1 là Tờ khai điện tử cổng tự sinh (tờ khai bản giấy không đính "
            "lại); giấy khai sinh + CCCD/CMND vào dòng 2; văn bản ủy quyền vào dòng 3."
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
        "key": "chung-thuc-phan-chia-di-san",
        # Cổng React mới (Bộ Tư pháp), cùng khung attach-only với chứng thực chữ ký / giao dịch tài
        # sản ngay trên: đi thẳng Thành phần hồ sơ, không consent, không bước chủ hồ sơ, KHÔNG
        # guidedSteps (luồng cũ).
        "detect": {
            "urlIncludes": [
                "019d2bfd-9daf-70da-8f48-223498332346",
                "maThuTuc=2.001406",
            ],
        },
        "label": "Chứng thực văn bản phân chia di sản mà di sản là động sản, quyền sử dụng đất, nhà ở",
        "shortLabel": "Chứng thực văn bản phân chia di sản",
        "subtitle": "Chứng thực văn bản thỏa thuận chia di sản thừa kế: động sản, đất đai, nhà ở",
        "icon": "📜",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-9daf-70da-8f48-223498332346",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Cổng có 2 dòng cố định: (1) giấy chứng nhận sở hữu/sử dụng, (2) dự thảo văn bản phân chia
        # di sản. Planner core mặc định GỘP: dự thảo → dòng 2, MỌI giấy khác gộp một PDF → dòng 1.
        # KHÔNG bật supportsSplitDocuments: giữ đúng mặc định gộp như bản đang chạy.
        # Ba ô bám đúng hai dòng của cổng + một ô gom phần còn lại; bộ phân loại lúc tải lên
        # (pipelines/chung_thuc_phan_chia_di_san/handfree) xếp tệp vào đúng ô, planner vẫn tự
        # phân loại lại theo nội dung lúc đính.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "so_huu", "name": "Giấy chứng nhận quyền sở hữu/sử dụng tài sản là di sản "
             "(sổ đỏ, đăng ký xe…)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "du_thao", "name": "Dự thảo văn bản thỏa thuận phân chia di sản", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy chứng nhận quyền sở hữu/quyền sử dụng hoặc giấy tờ thay thế của tài sản là di sản.\n"
            "2. Dự thảo văn bản thỏa thuận phân chia di sản thừa kế.\n"
            "3. Nếu có: giấy chứng tử/trích lục khai tử, phiếu đo đạc/chỉnh lý thửa đất, CCCD người "
            "được hưởng di sản, giấy ủy quyền đi nộp hồ sơ.\n"
            "Bước Thành phần hồ sơ: dự thảo vào dòng 2; mọi giấy tờ còn lại gộp chung một tệp PDF "
            "vào dòng 1."
        ),
    },
    {
        "key": "chung-thuc-tu-choi-nhan-di-san",
        # Cổng React mới (Bộ Tư pháp), cùng khung attach-only với phân chia di sản ngay trên: đi
        # thẳng Thành phần hồ sơ, không consent, không bước chủ hồ sơ, KHÔNG guidedSteps (luồng cũ).
        "detect": {
            "urlIncludes": [
                "019d2bfd-95e6-7578-ba2d-d1b4373cd174",
                "maThuTuc=2.001016",
            ],
        },
        "label": "Chứng thực văn bản từ chối nhận di sản",
        "shortLabel": "Chứng thực văn bản từ chối nhận di sản",
        "subtitle": "Chứng thực văn bản người thừa kế từ chối nhận phần di sản được hưởng",
        "icon": "📜",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-95e6-7578-ba2d-d1b4373cd174",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Cổng có 2 dòng cố định: (1) dự thảo văn bản từ chối nhận di sản, (2) GCN sở hữu/sử dụng +
        # CCCD + giấy chứng tử (planner gộp một PDF). Ủy quyền/giấy khác thêm thành phần mới.
        # KHÔNG bật supportsSplitDocuments: giữ mặc định gộp của planner core. Bộ phân loại lúc tải
        # lên (pipelines/chung_thuc_tu_choi_di_san/handfree) xếp tệp vào đúng ô, planner vẫn tự
        # phân loại lại theo nội dung lúc đính.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "du_thao", "name": "Dự thảo văn bản từ chối nhận di sản", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "so_huu", "name": "Giấy chứng nhận quyền sở hữu/sử dụng tài sản là di sản "
             "(sổ đỏ, đăng ký xe…)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Dự thảo văn bản từ chối nhận di sản.\n"
            "2. Giấy chứng nhận quyền sở hữu/quyền sử dụng hoặc giấy tờ thay thế của tài sản là di sản.\n"
            "3. Nếu có: căn cước của người từ chối, giấy chứng tử/trích lục khai tử của người để lại "
            "di sản, giấy ủy quyền đi nộp hồ sơ.\n"
            "Bước Thành phần hồ sơ: dự thảo vào dòng 1; giấy chứng nhận, căn cước, giấy chứng tử gộp "
            "chung một tệp PDF vào dòng 2; ủy quyền/giấy tờ khác thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "chung-thuc-di-chuc",
        # Cổng React mới (Bộ Tư pháp), cùng khung attach-only với từ chối nhận di sản ngay trên: đi
        # thẳng Thành phần hồ sơ, không consent, không bước chủ hồ sơ, KHÔNG guidedSteps (luồng cũ).
        "detect": {
            "urlIncludes": [
                "019d2bfd-95f0-7610-845f-c097f144bd55",
                "maThuTuc=2.001019",
            ],
        },
        "label": "Chứng thực di chúc",
        "shortLabel": "Chứng thực di chúc",
        "subtitle": "Chứng thực di chúc người lập định đoạt tài sản để lại cho người thừa kế",
        "icon": "📜",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-95f0-7610-845f-c097f144bd55",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Cổng có 2 dòng cố định: (1) dự thảo di chúc (planner gộp CCCD các bên vào cùng PDF),
        # (2) GCN sở hữu/sử dụng tài sản. Không có dự thảo thì CCCD thêm thành phần mới.
        # KHÔNG bật supportsSplitDocuments: giữ mặc định gộp của planner core. Bộ phân loại lúc tải
        # lên (pipelines/chung_thuc_di_chuc/handfree) xếp tệp vào đúng ô, planner vẫn tự phân loại
        # lại theo nội dung lúc đính.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "du_thao", "name": "Dự thảo di chúc", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "so_huu", "name": "Giấy chứng nhận quyền sở hữu/sử dụng tài sản trong di chúc "
             "(sổ đỏ, đăng ký xe…)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Dự thảo di chúc.\n"
            "2. Giấy chứng nhận quyền sở hữu/quyền sử dụng hoặc giấy tờ thay thế của tài sản trong "
            "di chúc.\n"
            "3. Nếu có: căn cước của người lập di chúc và các bên liên quan.\n"
            "Bước Thành phần hồ sơ: dự thảo di chúc vào dòng 1, căn cước gộp chung một tệp PDF với "
            "dự thảo; giấy chứng nhận tài sản vào dòng 2."
        ),
    },
    {
        "key": "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich",
        # Cổng React mới (Bộ Tư pháp), cùng khung attach-only với phân chia di sản / giao dịch tài
        # sản: đi thẳng Thành phần hồ sơ, không consent, không bước chủ hồ sơ, KHÔNG guidedSteps
        # (luồng cũ), không hỏi gộp/tách nhiều hồ sơ.
        "detect": {
            "urlIncludes": [
                "019d2bfd-8e59-72ab-ae1a-a2985865d253",
                "maThuTuc=2.000913",
            ],
        },
        "label": "Chứng thực việc sửa đổi, bổ sung, hủy bỏ giao dịch",
        "shortLabel": "Chứng thực sửa đổi, bổ sung, hủy bỏ giao dịch",
        "subtitle": "Sửa đổi, bổ sung hoặc hủy bỏ hợp đồng, giao dịch đã được chứng thực",
        "icon": "📝",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e59-72ab-ae1a-a2985865d253",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Cổng có 2 dòng cố định: (1) dự thảo sửa đổi/bổ sung/hủy bỏ + giấy tờ tài sản liên quan
        # (planner gộp một PDF), (2) giao dịch/hợp đồng cũ đã chứng thực. CCCD/ủy quyền/giấy khác
        # thêm thành phần mới. Bộ phân loại lúc tải lên (pipelines/chung_thuc_sua_doi_giao_dich/
        # handfree) xếp tệp vào đúng ô; planner vẫn tự phân loại lại theo nội dung lúc đính.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "du_thao", "name": "Dự thảo văn bản sửa đổi, bổ sung, hủy bỏ giao dịch",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "giao_dich_cu", "name": "Giao dịch/hợp đồng cũ đã được chứng thực",
             "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "so_huu", "name": "Giấy chứng nhận quyền sở hữu/sử dụng tài sản (nếu giao dịch "
             "liên quan tài sản)", "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Dự thảo văn bản sửa đổi, bổ sung, hủy bỏ giao dịch.\n"
            "2. Giao dịch/hợp đồng cũ đã được chứng thực.\n"
            "3. Nếu giao dịch liên quan tài sản phải đăng ký: giấy chứng nhận quyền sở hữu/sử dụng "
            "hoặc giấy tờ thay thế.\n"
            "4. Nếu có: căn cước của các bên, văn bản ủy quyền hoặc giấy tờ khác.\n"
            "Bước Thành phần hồ sơ: dự thảo và giấy tờ tài sản gộp một PDF vào dòng 1; giao dịch cũ "
            "đã chứng thực vào dòng 2; giấy tờ còn lại thêm thành phần hồ sơ mới."
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
        "key": "chung-thuc-chu-ky-nguoi-dich-khong-ctv",
        # Mã TTHC 2.001008. Anh em của bản CTV (2.000992), dùng chung planner
        # chung_thuc_chu_ky_nguoi_dich_ctv: dòng 1 bản dịch, tệp sau thêm thành phần mới.
        "detect": {
            "urlIncludes": [
                "019d2bfd-95d4-72d6-be00-ed0e9e5dd66a",
                "maThuTuc=2.001008",
            ],
        },
        "label": (
            "Chứng thực chữ ký người dịch mà người dịch không phải là cộng tác viên dịch thuật của "
            "Ủy ban nhân dân cấp xã"
        ),
        "shortLabel": "Chứng thực chữ ký người dịch (không CTV)",
        "subtitle": "Chứng thực chữ ký người dịch tự do, không phải cộng tác viên dịch thuật",
        "icon": "🌐",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-95d4-72d6-be00-ed0e9e5dd66a",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Planner không biết tệp thuộc ô nào (phiên không truyền doc_key xuống) mà xếp theo thứ
        # tự: tệp ĐẦU vào dòng 1. Vì vậy chỉ mở một ô bản dịch; bằng cấp/chứng chỉ ngoại ngữ và
        # giấy tùy thân của người dịch xuất trình tại quầy.
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
            "Người dịch mang bằng cấp/chứng chỉ ngoại ngữ và giấy tờ tùy thân để xuất trình tại quầy."
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
        "key": "cap-ban-sao-so-goc",
        # Cổng React mới (Bộ Tư pháp), cùng khung attach-only với nhóm chứng thực ngay trên: đi
        # thẳng Thành phần hồ sơ, không consent, không bước chủ hồ sơ, KHÔNG guidedSteps (luồng cũ).
        "detect": {
            "urlIncludes": [
                "019d2bfd-8e5d-72f9-8cf2-c71780251483",
                "maThuTuc=2.000908",
            ],
        },
        "label": "Cấp bản sao từ sổ gốc",
        "shortLabel": "Cấp bản sao từ sổ gốc",
        "subtitle": "Xin bản sao giấy tờ từ sổ gốc cơ quan đang lưu giữ",
        "icon": "📚",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e5d-72f9-8cf2-c71780251483",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Cổng có 2 dòng cố định: (1) giấy tờ chứng minh quan hệ với người được cấp bản chính,
        # (2) giấy tờ tùy thân người yêu cầu. Khóa ô trùng loại của bộ phân loại chung lúc tải lên
        # (ho_tich: khai sinh/kết hôn/trích lục; cccd) nên không cần bộ phân loại riêng; giấy khác
        # (báo tử, sổ hộ khẩu…) do LLM theo tên ô. Planner core tự định tuyến lại theo OCR lúc đính.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "ho_tich", "name": "Giấy tờ chứng minh quan hệ với người được cấp bản chính "
             "(giấy khai sinh, giấy chứng nhận kết hôn, giấy báo tử…)", "icon": "📄",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người yêu cầu", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân của người yêu cầu.\n"
            "2. Nếu người yêu cầu không phải người được cấp bản chính: giấy tờ chứng minh quan hệ "
            "(giấy khai sinh, giấy chứng nhận kết hôn, giấy báo tử/trích lục khai tử…).\n"
            "Bước Thành phần hồ sơ: giấy tờ chứng minh quan hệ vào dòng 1; căn cước vào dòng 2."
        ),
    },
    {
        "key": "bau-to-truong-to-hoa-giai",
        # Cổng React mới (Bộ Tư pháp — hòa giải ở cơ sở), cùng khung attach-only với nhóm chứng thực
        # ngay trên: đi thẳng Thành phần hồ sơ, không consent, không bước chủ hồ sơ, KHÔNG
        # guidedSteps. Cổng hiển thị tên "Thủ tục công nhận tổ trưởng tổ hòa giải (cấp xã)".
        "detect": {
            "urlIncludes": [
                "019d2bfd-95cf-74f7-8f8e-81c925ae839a",
                "maThuTuc=2.000950",
            ],
        },
        "label": "Thủ tục bầu tổ trưởng tổ hòa giải (cấp xã)",
        "shortLabel": "Bầu tổ trưởng tổ hòa giải",
        "subtitle": "Đề nghị công nhận tổ trưởng tổ hòa giải sau khi bầu ở thôn, tổ dân phố",
        "icon": "🤝",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-95cf-74f7-8f8e-81c925ae839a",
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        # Cổng có 2 dòng cố định: (1) biên bản bầu (Mẫu 04, kèm Mẫu 01), (2) văn bản đề nghị công
        # nhận (Mẫu 07, kèm Mẫu 06/10). Không có bộ phân loại riêng: LLM chung xếp theo tên ô lúc
        # tải lên; planner (bau_to_truong_to_hoa_giai.attach) tự phân loại lại theo OCR lúc đính,
        # gộp nhiều tệp cùng dòng thành một PDF và bỏ qua giấy ngoài hai nhóm.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "bien_ban", "name": "Biên bản kết quả biểu quyết bầu tổ trưởng tổ hòa giải "
             "(Mẫu 04, kèm biên bản bầu hòa giải viên nếu có)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "de_nghi", "name": "Văn bản đề nghị công nhận tổ trưởng tổ hòa giải (Mẫu 07, "
             "kèm danh sách hòa giải viên nếu có)", "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Biên bản kết quả biểu quyết bầu tổ trưởng tổ hòa giải (Mẫu 04), kèm biên bản bầu "
            "hòa giải viên (Mẫu 01) nếu có.\n"
            "2. Giấy đề nghị công nhận tổ trưởng tổ hòa giải (Mẫu 07), kèm danh sách đề nghị công nhận "
            "hòa giải viên (Mẫu 06) và tổng hợp danh sách hòa giải viên (Mẫu 10) nếu có.\n"
            "Bước Thành phần hồ sơ: biên bản vào dòng 1, văn bản đề nghị vào dòng 2; nhiều tệp cùng "
            "dòng được gộp thành một PDF."
        ),
    },
    {
        "key": "yeu-cau-tro-giup-phap-ly",
        # Mã TTHC 2.000829 (Bộ Tư pháp), nộp tại Sở Tư pháp (ke_khai_links: selectSo). DVCQG "Chọn
        # cơ quan thực hiện": chọn Tỉnh → gạt toggle "Sở" (KHÔNG chọn sở cụ thể) → Đồng ý → "Nộp
        # trực tuyến" kết quả ĐẦU TIÊN (Sở Tư pháp) — agencyProvinceOnly + agencySoFirst. Sau đó là
        # wizard tư pháp 4 bước: bước Kê khai là eForm "ĐƠN YÊU CẦU TRỢ GIÚP PHÁP LÝ" (legacy x-*).
        "detect": {
            "urlIncludes": [
                "019d2bfd-8e3d-737e-8aca-295dd1f2ea9f",
                "maThuTuc=2.000829",
            ],
            "textIncludes": ["Thủ tục yêu cầu trợ giúp pháp lý"],
            "headingDisabled": True,
        },
        "label": "Thủ tục yêu cầu trợ giúp pháp lý",
        "shortLabel": "Yêu cầu trợ giúp pháp lý",
        "subtitle": "Xin luật sư, trợ giúp viên pháp lý giúp miễn phí (Sở Tư pháp)",
        "icon": "⚖️",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e3d-737e-8aca-295dd1f2ea9f",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Tư pháp",
        # Modal "Thông tin chung" của thủ tục cấp Sở có thêm Cấp thực hiện → Thủ tục → Cơ quan thực
        # hiện → Đơn vị tiếp nhận (ô sau nạp theo ô trước). Extension chọn theo thứ tự này (khớp
        # chuỗi con, fold dấu), ô còn trống sau đó (Đơn vị tiếp nhận) lấy lựa chọn đầu.
        "infoModalFields": [
            {"label": "Cấp thực hiện", "value": "Cấp Tỉnh"},
            {"label": "Thủ tục", "value": "trợ giúp pháp lý"},
            {"label": "Cơ quan thực hiện", "value": "Sở Tư pháp"},
        ],
        # Bắc Ninh: cổng xếp thủ tục vào Cấp thực hiện "Đơn vị khác" (không phải Cấp Tỉnh), cơ quan
        # là Trung tâm Trợ giúp pháp lý nhà nước chứ không phải Sở Tư pháp. Khóa = province_slug.
        "infoModalFieldsByProvince": {
            "bacninh": [
                {"label": "Cấp thực hiện", "value": "Đơn vị khác"},
                {"label": "Tỉnh thành", "value": "Bắc Ninh"},
                {"label": "Thủ tục", "value": "trợ giúp pháp lý"},
                {"label": "Cơ quan thực hiện", "value": "Trung tâm Trợ giúp pháp lý"},
            ],
        },
        # Planner (yeu_cau_tro_giup_phap_ly.attach) tự phân loại lại theo OCR lúc đính: giấy chứng
        # minh diện + CCCD gộp một PDF vào dòng 1; dòng 2 là Tờ khai cổng tự sinh, không đính đè;
        # đơn bản giấy / ủy quyền / giấy khác thêm thành phần hồ sơ mới.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "chung_minh_dien", "name": "Giấy tờ chứng minh thuộc diện trợ giúp pháp lý "
             "(thông báo của cơ quan tố tụng, giấy chứng nhận hộ nghèo, xác nhận khuyết tật…)",
             "icon": "📃", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người được trợ giúp pháp lý", "icon": "🪪",
             "sides": 2, "repeatable": True},
            {"key": "don", "name": "Đơn yêu cầu trợ giúp pháp lý bản giấy (Mẫu 02-TP-TGPL, nếu có)",
             "icon": "📄", "sides": 1, "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu có)", "icon": "📜",
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
            "1. Giấy tờ chứng minh thuộc diện được trợ giúp pháp lý — thường là Thông báo về trợ giúp "
            "pháp lý của cơ quan tiến hành tố tụng; hoặc giấy chứng nhận hộ nghèo, xác nhận khuyết tật…\n"
            "2. Căn cước công dân của người được trợ giúp pháp lý (cả 2 mặt).\n"
            "3. Nếu có: Đơn yêu cầu trợ giúp pháp lý bản giấy (Mẫu 02-TP-TGPL), văn bản ủy quyền.\n"
            "Bước Thành phần hồ sơ: giấy chứng minh diện + căn cước gộp một tệp vào dòng 1; dòng 2 là "
            "Tờ khai cổng tự sinh; đơn bản giấy, ủy quyền thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su",
        # Mã TTHC 1.000688 (Bộ Tư pháp), nộp tại Sở Tư pháp (ke_khai_links: selectSo). Cùng luồng
        # chọn cơ quan cấp Sở với "yeu-cau-tro-giup-phap-ly": chọn Tỉnh → gạt toggle "Sở" → Đồng ý
        # → "Nộp trực tuyến" kết quả ĐẦU TIÊN (Sở Tư pháp). Wizard tư pháp 4 bước, bước Kê khai là
        # eForm "VĂN BẢN ĐỀ NGHỊ CẤP/CẤP LẠI CHỨNG CHỈ HÀNH NGHỀ LUẬT SƯ" (legacy x-*). Cụm text đủ
        # dài để không trùng thủ tục cấp CCHN luật sư thường (không miễn đào tạo).
        "detect": {
            "urlIncludes": [
                "019d2bfd-3faa-71b6-96ab-51618971aa7f",
                "maThuTuc=1.000688",
            ],
            "textIncludes": ["cấp chứng chỉ hành nghề luật sư đối với người được miễn đào tạo nghề luật sư"],
            "headingDisabled": True,
        },
        "label": (
            "Cấp Chứng chỉ hành nghề luật sư đối với người được miễn đào tạo nghề luật sư, miễn tập sự "
            "hành nghề luật sư"
        ),
        "shortLabel": "Chứng chỉ hành nghề luật sư (miễn tập sự)",
        "subtitle": "Cựu thẩm phán, kiểm sát viên, điều tra viên… xin chứng chỉ luật sư (Sở Tư pháp)",
        "icon": "👨‍⚖️",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3faa-71b6-96ab-51618971aa7f",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Tư pháp",
        "infoModalFields": [
            {"label": "Cấp thực hiện", "value": "Cấp Tỉnh"},
            {"label": "Thủ tục", "value": "miễn đào tạo nghề luật sư"},
            {"label": "Cơ quan thực hiện", "value": "Sở Tư pháp"},
        ],
        # Planner (cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.attach) tự phân loại lại theo
        # OCR, KHÔNG tách trang: bằng → dòng 1; giấy chứng minh miễn tập sự → dòng 2; sức khỏe → dòng
        # 3; giải trình/cam kết + Phiếu LLTP → dòng 4; dòng 5 là Tờ khai cổng tự sinh; văn bản đề nghị
        # bản giấy / CCCD / ủy quyền thêm thành phần hồ sơ mới.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "de_nghi", "name": "Văn bản đề nghị cấp Chứng chỉ hành nghề luật sư bản giấy đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "bang", "name": "Bằng cử nhân luật / thạc sỹ luật (bản sao chứng thực)", "icon": "🎓",
             "sides": 1, "repeatable": True},
            {"key": "mien_tap_su", "name": "Giấy tờ chứng minh được miễn tập sự (quyết định bổ nhiệm "
             "thẩm phán, kiểm sát viên, điều tra viên…, quyết định nghỉ hưu / xuất ngũ)", "icon": "📃",
             "sides": 1, "repeatable": True},
            {"key": "suc_khoe", "name": "Giấy chứng nhận sức khỏe", "icon": "🩺",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "lltp", "name": "Phiếu lý lịch tư pháp; văn bản giải trình, cam kết (nếu có)",
             "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị", "icon": "🪪",
             "sides": 2, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi giấy tờ một tệp, hệ thống KHÔNG tách trang):\n"
            "1. Văn bản đề nghị cấp Chứng chỉ hành nghề luật sư bản giấy đã ký — nguồn chính của tờ khai.\n"
            "2. Bằng cử nhân luật / thạc sỹ luật (bản sao chứng thực).\n"
            "3. Quyết định bổ nhiệm chức danh tư pháp, quyết định nghỉ hưu / xuất ngũ — chứng minh được "
            "miễn tập sự.\n"
            "4. Giấy chứng nhận sức khỏe; Phiếu lý lịch tư pháp; văn bản giải trình, cam kết (nếu có).\n"
            "5. Căn cước công dân (nếu có) để đối chiếu nhân thân.\n"
            "Nên đăng nhập cổng bằng tài khoản VNeID của chính người đề nghị. Bước Thành phần hồ sơ: bằng "
            "→ dòng 1; giấy miễn tập sự → dòng 2; sức khỏe → dòng 3; giải trình + Phiếu LLTP → dòng 4; "
            "dòng 5 là Tờ khai cổng tự sinh; văn bản đề nghị bản giấy thêm thành phần hồ sơ mới."
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
        "provinceOnly": ["danang", "bacninh"],  # chỉ account Đà Nẵng, Bắc Ninh thấy + gọi được
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
        "shortLabel": "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc",
        "subtitle": "Sở Giáo dục và Đào tạo",
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
        # Luồng chung cổng Bộ Xây dựng (flow_profiles/__init__.py: XAY_DUNG_FLOW).
        "flowProfile": "xay-dung",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
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
            "textIncludes": ["Thực hiện trợ cấp hưu trí xã hội"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thực hiện trợ cấp hưu trí xã hội",
        "shortLabel": "Trợ cấp hưu trí xã hội — thực hiện",
        "subtitle": "Thực hiện trợ cấp hưu trí xã hội",
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
            {"key": "don", "name": "Văn bản đề nghị hưởng trợ cấp hưu trí xã hội (Mẫu số 01)",
             "icon": "📄",
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
            "1. Văn bản đề nghị hưởng trợ cấp hưu trí xã hội (Mẫu số 01) — nguồn chính để điền form.\n"
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
        "key": "cap-gcn-attp-nong-lam-thuy-san",
        # Mã TTHC 2.001827, cổng Bộ NN&MT dichvucongnnmt.mae.gov.vn — KHÁC thủ tục ATTP Bộ Y tế ngay
        # trên (quán ăn, bếp ăn): đây là cơ sở sản xuất, kinh doanh thực phẩm nông, lâm, thủy sản.
        # Key TRÙNG lõi → pipeline process/attach tự nối. Thủ tục cấp huyện cũ, nay giải quyết ở CẤP
        # XÃ: ke_khai_links chọn đủ Tỉnh + Xã (không provinceOnlyAgency/selectSo) → DVCQG KHÔNG
        # agencyProvinceOnly/agencySoFirst; trang MAE "chọn nơi và loại" (form#ngSelectAgencyForm1)
        # gạt radio "Phường/Xã" + chọn xã = maePortal + maeAgencyLevel "ward" như hai thủ tục cấp xã
        # Bộ Nội vụ. Trang kê khai apply-online/<id> không có mã → thêm cụm tên (hai cụm AND, cụm sau
        # chặn nhầm với ATTP Bộ Y tế).
        "detect": {
            "urlScope": ["dichvucongnnmt.mae.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "019d2bfa-b57f-73cc-856f-0255333fcb48",
                "apply-online/693a99efda87c4718ece1bc7",
                "process=695dbb6de184634c1f3648af",
            ],
            "textIncludes": ["cơ sở đủ điều kiện an toàn thực phẩm", "nông, lâm, thủy sản"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, "
            "kinh doanh thực phẩm nông, lâm, thủy sản"
        ),
        "shortLabel": "Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm (nông, lâm, thủy sản)",
        "subtitle": "Cho cơ sở sản xuất, kinh doanh nông sản, lâm sản, thủy sản làm thực phẩm",
        "icon": "🌾",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-b57f-73cc-856f-0255333fcb48",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        # Wizard MAE: 1 Thông tin hồ sơ (kê khai Form.io) → 2 Thành phần hồ sơ → 3 → 4 Nộp hồ sơ.
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Planner lõi: Đơn Phụ lục I và Thuyết minh Phụ lục II vào hai dòng attp-row cố định, CCCD
        # (gộp 2 mặt) đi "Thêm giấy tờ", giấy ĐKKD chỉ để điền form, giấy lạ dồn vào dòng Đơn (ô
        # "khac" cuối bảng để tệp lạ không bị báo "chưa nhận ra loại").
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm "
             "(Phụ lục I) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "thuyet_minh", "name": "Bản thuyết minh về cơ sở vật chất, trang thiết bị, dụng cụ bảo "
             "đảm điều kiện an toàn thực phẩm (Phụ lục II)", "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nộp hồ sơ, thêm CCCD chủ / đại diện cơ "
             "sở nếu nộp thay", "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "dkkd", "name": "Giấy chứng nhận đăng ký kinh doanh / doanh nghiệp / hộ kinh doanh "
             "(nếu có, để đối chiếu)", "icon": "🏪", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm theo Phụ lục I, đã "
            "ký — nguồn chính để điền form.\n"
            "2. Bản thuyết minh điều kiện bảo đảm an toàn thực phẩm theo Phụ lục II.\n"
            "3. Căn cước công dân của người nộp hồ sơ; nếu người nộp khác chủ / đại diện cơ sở thì thêm "
            "căn cước của chủ / đại diện cơ sở.\n"
            "4. Nếu có: Giấy chứng nhận đăng ký kinh doanh / doanh nghiệp / hộ kinh doanh để đối chiếu.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước Thành phần hồ sơ: Đơn vào dòng Phụ lục I, bản thuyết minh vào dòng Phụ lục II; căn cước "
            "(gộp 2 mặt) xếp vào mục 'Thêm giấy tờ'; giấy đăng ký kinh doanh chỉ dùng để điền form."
        ),
    },
    {
        "key": "cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te",
        # Mã TTHC 1.014104, cổng Bộ Y tế (CÙNG wizard iGate/Form.io với ATTP ngay trên) nhưng nộp tại
        # SỞ Y tế: ke_khai_links đặt selectSo → DVCQG chọn Tỉnh → gạt toggle "Sở" (KHÔNG chọn sở cụ
        # thể) → Đồng ý → "Nộp trực tuyến" kết quả ĐẦU TIÊN (agencyProvinceOnly + agencySoFirst).
        # Sau đó cổng Bộ Y tế mở trang nps/apply "Chọn trường hợp giải quyết" (Đơn vị thực hiện +
        # Trường hợp giải quyết + Đồng ý) Y HỆT hộp thoại Bộ Xây dựng → dùng luồng chung "xay-dung"
        # (maePortal + maeDialogChoice: đọc lựa chọn từ cổng, nhiều lựa chọn thì hỏi công dân).
        # Trang kê khai là apply-online/<ObjectId> không có mã → cần cụm tên; cụm có "cấp lại, điều
        # chỉnh" nên không lẫn thủ tục cấp GCN dược lần đầu.
        "flowProfile": "xay-dung",
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.014104",
                "MaTTHC=1.014104",
                "019d2bff-3cdc-755a-a2a6-714d0c0b1361",
            ],
            "textIncludes": ["cấp lại, điều chỉnh giấy chứng nhận đủ điều kiện kinh doanh dược"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp lại, điều chỉnh Giấy chứng nhận đủ điều kiện kinh doanh dược thuộc thẩm quyền của Sở "
                 "Y tế (Cơ sở bán buôn thuốc, nguyên liệu làm thuốc; Cơ sở bán lẻ thuốc bao gồm nhà thuốc, "
                 "quầy thuốc, tủ thuốc trạm y tế xã, cơ sở chuyên bán lẻ dược liệu, thuốc dược liệu, thuốc cổ "
                 "truyền)",
        "shortLabel": "Cấp lại, điều chỉnh Giấy chứng nhận đủ điều kiện kinh doanh dược",
        "subtitle": "Cho nhà thuốc, quầy thuốc, cơ sở bán buôn thuốc đổi tên, địa chỉ, người phụ trách (Sở Y tế)",
        "icon": "💊",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-3cdc-755a-a2a6-714d0c0b1361",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ 6 dòng cố định (planner core): Đơn cấp lại Mẫu 11 / GCN bị ghi sai /
        # Đơn điều chỉnh Mẫu 12 / CCHN dược / giấy tờ pháp lý thay đổi / thuyết minh an ninh → tắt
        # hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị điều chỉnh (Mẫu số 12) hoặc cấp lại (Mẫu số 11) Giấy "
             "chứng nhận đủ điều kiện kinh doanh dược — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "dkkd", "name": "Giấy chứng nhận đăng ký hộ kinh doanh / doanh nghiệp (bản mới nhất) "
             "và Giấy chứng nhận đạt GPP nếu có", "icon": "🏪", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ cơ sở, thêm CCCD người nộp nếu nộp thay",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "gcn_cu", "name": "Giấy chứng nhận đủ điều kiện kinh doanh dược đã cấp (nếu bị ghi "
             "sai)", "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cchn", "name": "Chứng chỉ hành nghề dược (nếu thay đổi người phụ trách chuyên môn)",
             "icon": "🎓", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác (tài liệu thuyết minh bảo đảm an ninh "
             "Mẫu 11 PL II…)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF):\n"
            "1. Đơn đề nghị điều chỉnh Giấy chứng nhận đủ điều kiện kinh doanh dược (Mẫu số 12) HOẶC "
            "Đơn đề nghị cấp lại (Mẫu số 11), đã ký — nguồn chính để điền form.\n"
            "2. Giấy chứng nhận đăng ký hộ kinh doanh / doanh nghiệp (bản mới nhất, chứng minh tên/địa chỉ "
            "đã thay đổi) và Giấy chứng nhận đạt GPP nếu có.\n"
            "3. Căn cước công dân của chủ cơ sở; nếu người khác nộp thay: thêm căn cước của người nộp.\n"
            "4. Tùy trường hợp: Giấy chứng nhận bị ghi sai (cấp lại), Chứng chỉ hành nghề dược (thay đổi "
            "người phụ trách chuyên môn), tài liệu thuyết minh bảo đảm an ninh (Mẫu 11 PL II).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là chủ cơ sở kinh doanh dược; ô Ghi chú điền nội dung xin điều chỉnh / lý do cấp lại.\n"
            "Bước Thành phần hồ sơ: mỗi giấy tờ vào đúng dòng (Đơn Mẫu 12 → dòng 3, giấy đăng ký hộ kinh "
            "doanh + GPP → dòng 5...); căn cước chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "dang-ky-hanh-nghe",
        # Mã TTHC 1.012275 (khám bệnh, chữa bệnh — NĐ 96/2023), CÙNG khung entry dược ngay trên: cổng
        # Bộ Y tế, nộp tại SỞ Y tế (ke_khai_links đặt selectSo) → agencyProvinceOnly + agencySoFirst,
        # rồi trang nps/apply "Chọn trường hợp giải quyết" nếu cổng mở → luồng chung "xay-dung".
        # Key TRÙNG lõi → pipeline process/attach tự nối. Phần I người nộp cổng tự đổ từ VNeID; mapper
        # lõi bỏ tích isOwnerDossierCheck và điền Phần II = cơ sở khám bệnh, chữa bệnh.
        # Cụm tên NGẮN, dễ lẫn ("đăng ký hành nghề công chứng", dòng "Danh sách đăng ký hành nghề" của
        # thủ tục giấy phép hành nghề…) → như lõi: tắt heading, KHÔNG bật textPriority để URL có mã
        # luôn thắng.
        "flowProfile": "xay-dung",
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.012275",
                "MaTTHC=1.012275",
                "019d2bff-1db1-707d-ab58-f95681fb13f2",
            ],
            "textIncludes": ["Đăng ký hành nghề"],
            "headingDisabled": True,
        },
        "label": "Đăng ký hành nghề",
        "shortLabel": "Đăng ký người hành nghề khám bệnh, chữa bệnh",
        "subtitle": "Cho phòng khám, nha khoa, cơ sở khám chữa bệnh báo danh sách người hành nghề (Sở Y tế)",
        "icon": "🩺",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-1db1-707d-ab58-f95681fb13f2",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ 4 dòng cố định (planner lõi attp-row): danh sách lần đầu / đã thay đổi /
        # Báo cáo / đã bổ sung → tắt hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "danh_sach", "name": "Danh sách đăng ký người hành nghề (Mẫu 01 Phụ lục II Nghị định "
             "96/2023/NĐ-CP) — đã ký, đóng dấu", "icon": "📋", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng đầu cơ sở (người ký danh sách)",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "ds_thay_doi", "name": "Danh sách đăng ký hành nghề đã thay đổi hoặc đã bổ sung (nếu "
             "có)", "icon": "📝", "sides": 1, "optional": True, "repeatable": True},
            {"key": "bao_cao", "name": "Báo cáo (nếu có)", "icon": "📄", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Danh sách đăng ký người hành nghề (Mẫu 01 Phụ lục II Nghị định 96/2023/NĐ-CP) của cơ sở "
            "khám bệnh, chữa bệnh, có ký tên, đóng dấu — nguồn chính để điền form.\n"
            "2. Căn cước công dân (mặt trước + mặt sau) của người đứng đầu cơ sở, người ký danh sách.\n"
            "3. Nếu có: Báo cáo; danh sách ĐÃ THAY ĐỔI hoặc ĐÃ BỔ SUNG người hành nghề.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Phần người nộp cổng tự lấy từ tài khoản VNeID; chủ hồ sơ là cơ sở khám bệnh, chữa bệnh. Số "
            "điện thoại, email của cơ sở phải tự nhập.\n"
            "Bước Thành phần hồ sơ: danh sách → dòng 1, danh sách đã thay đổi → dòng 2, Báo cáo → dòng 3, "
            "danh sách đã bổ sung → dòng 4; căn cước chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep",
        # Mã TTHC 1.012292, CÙNG khung entry "dang-ky-hanh-nghe" ngay trên: cổng Bộ Y tế, nộp tại SỞ Y
        # tế (ke_khai_links đặt selectSo) → agencyProvinceOnly + agencySoFirst, rồi trang nps/apply "Chọn
        # trường hợp giải quyết" nếu cổng mở → luồng chung "xay-dung". Key TRÙNG lõi → pipeline
        # process/attach tự nối (lõi tự quyết tự nộp / nộp thay theo tài khoản, điền ô Ghi chú).
        # Trang kê khai là apply-online/<ObjectId> không có mã → cụm tên như lõi: cụm đầu "điều chỉnh…"
        # đủ tách khỏi "cấp mới giấy phép hành nghề trong giai đoạn chuyển tiếp" (cùng cụm thứ hai).
        "flowProfile": "xay-dung",
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.012292",
                "MaTTHC=1.012292",
                "019d2bff-1db3-774c-81c5-200c7dcc25a1",
            ],
            "textIncludes": [
                "điều chỉnh giấy phép hành nghề trong giai đoạn chuyển tiếp",
                "kiểm tra đánh giá năng lực hành nghề",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Điều chỉnh giấy phép hành nghề trong giai đoạn chuyển tiếp đối với hồ sơ nộp từ ngày 01 "
                 "tháng 01 năm 2024 đến thời điểm kiểm tra đánh giá năng lực hành nghề đối với các chức "
                 "danh bác sỹ, y sỹ, điều dưỡng, hộ sinh, kỹ thuật y, dinh dưỡng lâm sàng, cấp cứu viên "
                 "ngoại viện, tâm lý lâm sàng",
        "shortLabel": "Điều chỉnh giấy phép hành nghề khám bệnh, chữa bệnh (giai đoạn chuyển tiếp)",
        "subtitle": "Cho bác sĩ, y sĩ, điều dưỡng, hộ sinh… thay đổi phạm vi hành nghề (Sở Y tế)",
        "icon": "🩺",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-1db3-774c-81c5-200c7dcc25a1",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ 10 dòng cố định (planner lõi attp-row, mỗi tệp đúng một dòng) → tắt
        # hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị điều chỉnh giấy phép hành nghề (Mẫu 08 Phụ lục I Nghị định "
             "96/2023/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gphn", "name": "Giấy phép hành nghề / chứng chỉ hành nghề đã cấp", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "van_bang", "name": "Văn bằng đào tạo (bằng chuyên khoa, bằng tốt nghiệp…) liên quan "
             "đến phạm vi đề nghị", "icon": "🎓", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người hành nghề, thêm CCCD người nộp nếu nộp "
             "thay", "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "chung_chi", "name": "Chứng chỉ đào tạo liên quan đến phạm vi đề nghị bổ sung (nếu có)",
             "icon": "📝", "sides": 1, "optional": True, "repeatable": True},
            {"key": "thuc_hanh", "name": "Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07 Phụ lục I, "
             "nếu có)", "icon": "🏥", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác (giấy chứng nhận bài thuốc gia truyền…)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (đều là của NGƯỜI HÀNH NGHỀ đề nghị điều chỉnh):\n"
            "1. Đơn đề nghị (Mẫu 08 Phụ lục I Nghị định 96/2023/NĐ-CP), đã ký, ghi rõ trường hợp và phạm "
            "vi hành nghề đề nghị — nguồn chính để điền form.\n"
            "2. Giấy phép hành nghề / chứng chỉ hành nghề đã cấp.\n"
            "3. Văn bằng đào tạo (bằng chuyên khoa, bằng tốt nghiệp…) liên quan đến phạm vi đề nghị.\n"
            "4. Căn cước công dân (2 mặt) của người hành nghề; nếu người khác nộp thay: thêm căn cước của "
            "người nộp.\n"
            "5. Nếu có: chứng chỉ đào tạo liên quan, Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07), "
            "giấy chứng nhận bài thuốc gia truyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là người hành nghề; ô Ghi chú lấy trường hợp + phạm vi hành nghề trên Đơn.\n"
            "Bước Thành phần hồ sơ: mỗi tệp vào đúng một dòng (Đơn → dòng Đơn Mẫu 08 đầu tiên, giấy phép "
            "đã cấp → dòng 'b) giấy phép hành nghề đã cấp', văn bằng → dòng 'c) văn bằng đào tạo'...); "
            "căn cước chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "cap-moi-giay-phep-hanh-nghe-chuyen-tiep",
        # Mã TTHC 1.012289, CÙNG cổng + CÙNG form với entry "điều chỉnh" ngay trên (bản đó thêm ô Ghi
        # chú) → chép khung: nộp tại SỞ Y tế → agencyProvinceOnly + agencySoFirst, luồng chung
        # "xay-dung". ke_khai_links của mã này CHƯA có selectSo (bản điều chỉnh có) — mở trang DVCQG
        # kiểm hộp chọn cơ quan rồi thêm cho khớp. Key TRÙNG lõi → pipeline process/attach tự nối (lõi
        # tự quyết tự nộp / nộp thay theo tài khoản). Trang kê khai không có mã → cụm tên như lõi: cụm
        # đầu "cấp mới…" đủ tách khỏi bản "điều chỉnh" (cùng cụm thứ hai).
        "flowProfile": "xay-dung",
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.012289",
                "MaTTHC=1.012289",
                "019d2bff-1db7-73d4-8e28-7b1fd65945b7",
            ],
            "textIncludes": [
                "cấp mới giấy phép hành nghề trong giai đoạn chuyển tiếp",
                "kiểm tra đánh giá năng lực hành nghề",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp mới giấy phép hành nghề trong giai đoạn chuyển tiếp đối với hồ sơ nộp từ ngày 01 "
                 "tháng 01 năm 2024 đến thời điểm kiểm tra đánh giá năng lực hành nghề đối với các chức "
                 "danh bác sỹ, y sỹ, điều dưỡng, hộ sinh, kỹ thuật y, dinh dưỡng lâm sàng, cấp cứu viên "
                 "ngoại viện, tâm lý lâm sàng",
        "shortLabel": "Cấp mới giấy phép hành nghề khám bệnh, chữa bệnh (giai đoạn chuyển tiếp)",
        "subtitle": "Cho bác sĩ, y sĩ, điều dưỡng, hộ sinh… xin giấy phép hành nghề lần đầu (Sở Y tế)",
        "icon": "🩺",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-1db7-73d4-8e28-7b1fd65945b7",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ dòng cố định a–h (planner lõi attp-row, mỗi loại giấy tờ một dòng) →
        # tắt hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp giấy phép hành nghề (Mẫu 08 Phụ lục I Nghị định "
             "96/2023/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "van_bang", "name": "Văn bằng chuyên môn (bằng tốt nghiệp / cử nhân)", "icon": "🎓",
             "sides": 1, "repeatable": True},
            {"key": "suc_khoe", "name": "Giấy khám sức khỏe do cơ sở khám bệnh, chữa bệnh đủ điều kiện cấp",
             "icon": "🏥", "sides": 1, "repeatable": True},
            {"key": "so_yeu_ly_lich", "name": "Sơ yếu lý lịch tự thuật của người hành nghề (Mẫu 09 Phụ lục I)",
             "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "thuc_hanh", "name": "Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07 Phụ lục I)",
             "icon": "📋", "sides": 1, "repeatable": True},
            {"key": "anh", "name": "02 ảnh chân dung 4x6 nền trắng (chụp trong 6 tháng)", "icon": "🖼️",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người hành nghề, thêm CCCD người nộp nếu nộp "
             "thay", "icon": "🪪", "sides": 2, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (đều là của NGƯỜI HÀNH NGHỀ đề nghị cấp phép):\n"
            "1. Đơn đề nghị cấp giấy phép hành nghề khám bệnh, chữa bệnh (Mẫu 08 Phụ lục I Nghị định "
            "96/2023/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Văn bằng chuyên môn (bằng tốt nghiệp / cử nhân).\n"
            "3. Giấy khám sức khỏe do cơ sở khám bệnh, chữa bệnh đủ điều kiện cấp.\n"
            "4. Sơ yếu lý lịch tự thuật của người hành nghề (Mẫu 09 Phụ lục I).\n"
            "5. Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07 Phụ lục I).\n"
            "6. 02 ảnh chân dung 4x6 nền trắng, chụp trong 6 tháng.\n"
            "7. Căn cước công dân (2 mặt) của người hành nghề; nếu người khác nộp thay: thêm căn cước của "
            "người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là người hành nghề. Tự nộp thì giữ tích 'Người nộp là chủ hồ sơ', cổng tự chép "
            "sang phần chủ hồ sơ; nộp thay thì bỏ tích và điền riêng hai phần.\n"
            "Bước Thành phần hồ sơ: mỗi giấy tờ vào đúng dòng (a Đơn Mẫu 08, b văn bằng, d sức khỏe, e sơ "
            "yếu lý lịch, g xác nhận thực hành, h ảnh chân dung); căn cước chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "cap-moi-giay-phep-hoat-dong-kham-benh-chua-benh",
        # Mã TTHC 1.012278, CÙNG khung Form.io với 2 entry giấy phép hành nghề chuyển tiếp ngay trên: cổng
        # Bộ Y tế, nộp tại SỞ Y tế (ke_khai_links đặt selectSo) → agencyProvinceOnly + agencySoFirst, luồng
        # chung "xay-dung". Key TRÙNG lõi → pipeline process/attach tự nối. KHÁC ở chỗ chủ hồ sơ là CƠ SỞ
        # khám bệnh, chữa bệnh (người đại diện ký Đơn Mẫu 02); tên, địa chỉ, giờ làm việc của cơ sở lõi
        # tóm vào ô Ghi chú. Trang kê khai là ObjectId không có mã → cụm TÊN thủ tục như lõi (bảng Bước 2
        # bị ẩn khi đang ở Bước 1 nên không dùng tên dòng đính kèm).
        "flowProfile": "xay-dung",
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.012278",
                "MaTTHC=1.012278",
                "019d2bff-1dae-71ac-95d8-374403c4ee5e",
            ],
            "textIncludes": ["cấp mới giấy phép hoạt động khám bệnh, chữa bệnh"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp mới giấy phép hoạt động khám bệnh, chữa bệnh",
        "shortLabel": "Cấp mới giấy phép hoạt động cơ sở khám bệnh, chữa bệnh",
        "subtitle": "Cho phòng khám, nha khoa, cơ sở khám chữa bệnh xin giấy phép hoạt động (Sở Y tế)",
        "icon": "🏥",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-1dae-71ac-95d8-374403c4ee5e",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ 11 dòng cố định (planner lõi attp-row, mỗi tệp đúng một dòng) → tắt
        # hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp mới giấy phép hoạt động (Mẫu 02 Phụ lục II Nghị định "
             "96/2023/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "dang_ky", "name": "Giấy chứng nhận đăng ký hộ kinh doanh / doanh nghiệp (hoặc quyết "
             "định thành lập cơ sở)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "gphn", "name": "Chứng chỉ / giấy phép hành nghề và giấy xác nhận quá trình hành nghề "
             "(Mẫu 11) của người chịu trách nhiệm chuyên môn", "icon": "🩺", "sides": 1, "repeatable": True},
            {"key": "ke_khai", "name": "Bản kê khai cơ sở vật chất, thiết bị y tế, nhân sự (Mẫu 08) kèm giấy "
             "tờ chứng minh (văn bằng, chứng chỉ đào tạo, hợp đồng…)", "icon": "📋", "sides": 1,
             "repeatable": True},
            {"key": "danh_sach", "name": "Danh sách đăng ký người hành nghề (Mẫu 01 Phụ lục II)", "icon": "📝",
             "sides": 1, "repeatable": True},
            {"key": "danh_muc", "name": "Danh mục chuyên môn kỹ thuật đề xuất", "icon": "📑", "sides": 1,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đại diện cơ sở, thêm CCCD người nộp nếu nộp "
             "thay", "icon": "🪪", "sides": 2, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Điều lệ bệnh viện (Mẫu 03) / tài liệu nguồn tài chính cơ sở nhân đạo "
             "(nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (của CƠ SỞ khám bệnh, chữa bệnh đề nghị cấp giấy phép hoạt động):\n"
            "1. Đơn đề nghị cấp mới giấy phép hoạt động (Mẫu 02 Phụ lục II Nghị định 96/2023/NĐ-CP), đã ký "
            "— nguồn chính để điền form.\n"
            "2. Giấy chứng nhận đăng ký hộ kinh doanh / doanh nghiệp (hoặc quyết định thành lập).\n"
            "3. Chứng chỉ hành nghề + giấy xác nhận quá trình hành nghề (Mẫu 11) của người chịu trách nhiệm "
            "chuyên môn.\n"
            "4. Bản kê khai cơ sở vật chất, thiết bị y tế, nhân sự (Mẫu 08) và giấy tờ chứng minh: văn bằng, "
            "chứng chỉ đào tạo, quyết định, hợp đồng…\n"
            "5. Danh sách đăng ký hành nghề (Mẫu 01) và Danh mục chuyên môn kỹ thuật.\n"
            "6. Nếu có: căn cước người đại diện cơ sở; căn cước người nộp thay; điều lệ bệnh viện (Mẫu 03); "
            "tài liệu nguồn tài chính cơ sở nhân đạo.\n"
            "Nên để MỖI giấy tờ một tệp riêng — tệp scan gộp quá dài chỉ đọc được mấy trang đầu.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là người đại diện cơ sở; tên, địa chỉ, giờ làm việc của cơ sở ghi vào ô Ghi chú.\n"
            "Bước Thành phần hồ sơ: Đơn → dòng 1, giấy đăng ký → dòng 2, chứng chỉ hành nghề + giấy xác nhận "
            "→ dòng 3, bản kê khai + giấy tờ chứng minh → dòng 5, danh sách hành nghề → dòng 6, danh mục kỹ "
            "thuật → dòng 8; dòng bệnh viện / nhân đạo chỉ đính khi có giấy tờ; căn cước chỉ dùng ở bước "
            "thông tin."
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
        "key": "doi-cap-lai-giay-xac-nhan-khuyet-tat",
        # CÙNG cổng Bộ Y tế, cùng eForm Mẫu số 01 và cùng wizard với "xac-dinh-muc-do-khuyet-tat";
        # khác mã TTHC nên URL tách được. Khác ở bước đính kèm: bảng thành phần hồ sơ CHỈ MỘT DÒNG
        # (Đơn đề nghị Mẫu số 01) → planner dồn mọi tệp vào dòng đó, nên bật hideRepeatableHint.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.001653",
                "019d2bfe-b7ab-731d-844a-5e232b77afef",
            ],
            # Trang dùng chung eForm với thủ tục xác định mức độ → cụm "mức độ khuyết tật" có thể
            # xuất hiện ở đây; lấy cụm tên riêng "cấp lại giấy xác nhận khuyết tật".
            "textIncludes": ["cấp lại giấy xác nhận khuyết tật"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Đổi, cấp lại Giấy xác nhận khuyết tật",
        "shortLabel": "Đổi, cấp lại Giấy xác nhận khuyết tật (mất, hư hỏng)",
        "subtitle": "Cấp đổi hoặc cấp lại Giấy xác nhận khuyết tật bị mất, hư hỏng",
        "icon": "♿",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-b7ab-731d-844a-5e232b77afef",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp đổi, cấp lại Giấy xác nhận khuyết tật "
             "(Mẫu số 01) — đã ký, đã tích ô Cấp lại hoặc Cấp đổi", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người khuyết tật hoặc người đại diện "
             "đứng đơn", "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "giay_xac_nhan_cu", "name": "Giấy xác nhận khuyết tật cũ (nếu còn, khi cấp "
             "đổi hoặc giấy bị hư hỏng)", "icon": "♿", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp đổi, cấp lại Giấy xác nhận khuyết tật (Mẫu số 01), đã ký và đã "
            "tích ô Cấp lại hoặc Cấp đổi — nguồn chính để điền form.\n"
            "2. Căn cước công dân của người khuyết tật hoặc người đại diện đứng đơn.\n"
            "3. Nếu còn: Giấy xác nhận khuyết tật cũ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "LƯU Ý: người khuyết tật và người đại diện/người nộp hồ sơ có thể là HAI người khác "
            "nhau — không ghép thông tin của hai người vào nhau.\n"
            "Bước Thành phần hồ sơ: cổng chỉ có ĐÚNG MỘT dòng (Đơn đề nghị Mẫu số 01) nên mọi tệp "
            "đều được đính vào dòng đó; tệp không phải Đơn đề nghị vẫn đính được nhưng có cảnh "
            "báo để cán bộ soát."
        ),
    },
    {
        "key": "ho-tro-mai-tang-1116910",
        # Mã TTHC 1.116910, thay mã cũ 1.001731 (entry Auto Fill "ho-tro-mai-tang" vẫn giữ cho trang
        # mã cũ; cả hai key dùng chung pipeline ho_tro_mai_tang). CÙNG cổng Bộ Y tế, cùng khung với "ho-tro-mai-tang-huu-tri-xa-hoi"; khác NHÓM ĐỐI TƯỢNG
        # (bảo trợ xã hội thay vì người hưởng trợ cấp hưu trí xã hội). Bảng thành phần hồ sơ cũng
        # chỉ một dòng Tờ khai → hideRepeatableHint.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.116910",
                "01a0f66e-63a3-749a-a9d8-2dcbeda6af79",
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
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/01a0f66e-63a3-749a-a9d8-2dcbeda6af79",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 04)", "icon": "📄",
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
            "1. Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 04) — nguồn chính để điền form.\n"
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
            {"key": "to_khai", "name": "Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 02)", "icon": "📄",
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
            "1. Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 02) — nguồn chính để điền form.\n"
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
        "key": "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang",
        # Mã 1.116909 (NĐ 335/2026/NĐ-CP) — bản MỚI của "tro-cap-xa-hoi-hang-thang" (1.001776) ở trên:
        # CÙNG cổng Bộ Y tế, cùng cách chọn cơ quan (Tỉnh + Xã), cùng wizard. Bảng thành phần hồ sơ 2
        # dòng (Mẫu số 01 / Mẫu số 02) → KHÔNG đặt hideRepeatableHint. URL SPA của cổng không mang mã
        # → nhận trang theo cụm tên CHỈ thủ tục này có ("trợ cấp xã hội và nhận chăm sóc"); nhãn thủ
        # tục cũ không chứa cụm này, và cụm của thủ tục cũ ("...hàng tháng") không khớp "hằng tháng".
        # Cờ subjectAsSubmitter (phường Yên Bái) do pipeline_runner đặt theo tài khoản.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.116909",
                "01a0f668-d09b-7368-9850-3c8288daf506",
            ],
            "textIncludes": ["trợ cấp xã hội và nhận chăm sóc"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng, hỗ trợ kinh phí nhận chăm sóc, "
            "nuôi dưỡng hằng tháng"
        ),
        "shortLabel": "Trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng hằng tháng (NĐ 335)",
        "subtitle": "Trợ cấp xã hội, hỗ trợ kinh phí nhận chăm sóc, nuôi dưỡng theo NĐ 335/2026",
        "icon": "🤝",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/01a0f668-d09b-7368-9850-3c8288daf506",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị trợ cấp xã hội (Mẫu số 01) hoặc Tờ khai "
             "nhận chăm sóc, nuôi dưỡng (Mẫu số 02) theo NĐ 335/2026 — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của đối tượng hưởng trợ cấp và của người "
             "giám hộ/người khai thay", "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: Giấy xác nhận khuyết tật, Giấy khai "
             "sinh, Giấy xác nhận thông tin về cư trú", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đề nghị trợ cấp xã hội (Mẫu số 01) HOẶC Tờ khai nhận chăm sóc, nuôi dưỡng "
            "(Mẫu số 02) theo NĐ 335/2026/NĐ-CP, đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của đối tượng hưởng trợ cấp và của người giám hộ/người khai thay.\n"
            "3. Nếu có: Giấy xác nhận khuyết tật, Giấy khai sinh, Giấy xác nhận thông tin về cư trú.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là ĐỐI TƯỢNG hưởng trợ cấp; người giám hộ/người khai thay điền vào phần người "
            "nộp. Đối tượng không có số điện thoại thì dùng số của người khai thay.\n"
            "Bước Thành phần hồ sơ: Tờ khai Mẫu 01 + căn cước + giấy xác nhận khuyết tật đính chung "
            "dòng Mẫu số 01; Tờ khai Mẫu 02 vào dòng Mẫu số 02 (không có thì bỏ trống dòng này)."
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
        "flowProfile": "xay-dung",
        # Đường DỰ PHÒNG cho extension chưa đọc được hộp thoại (thiếu supportsMaeDialogChoice):
        # hỏi 2 trường hợp khai sẵn. portalMatch/portalAvoid là token ĐÃ FOLD DẤU để khớp option
        # trong ô "Trường hợp giải quyết". Option ĐẦU là mặc định (chip tô đậm).
        # pipelineOptions: ép nhánh form công trình cho mapper, khỏi đoán lại từ giấy tờ.
        "variants": {
            # Hai trường hợp ngang hàng → hai chip cùng màu, không tô đậm riêng option đầu.
            "equalChips": True,
            "options": [
                {"key": "nha_o_rieng_le", "label": "Nhà ở riêng lẻ",
                 "chip": "🏠 Nhà ở riêng lẻ", "portalMatch": "nha o rieng le",
                 "desc": "xây nhà ở của hộ gia đình, cá nhân",
                 "pipelineOptions": {"constructionVariant": "nha_o_rieng_le"}},
                {"key": "cong_trinh", "label": "Công trình cấp III, cấp IV",
                 "chip": "🏢 Công trình cấp III, cấp IV",
                 "portalMatch": "cong trinh", "portalAvoid": "nha o rieng le",
                 "desc": "công trình cấp III, cấp IV, không phải nhà ở riêng lẻ",
                 "pipelineOptions": {"constructionVariant": "khong_theo_tuyen"}},
            ],
        },
        # Trường hợp người dân chọn trên hộp thoại (nhãn đọc từ cổng) → tuỳ chọn pipeline.
        # Khớp theo cụm đã fold dấu, luật ĐẦU TIÊN khớp thắng; match rỗng = mặc định.
        "caseOptions": _GPXD_CASE_OPTIONS,
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
    # ── Các thủ tục cổng Bộ Xây dựng dùng luồng chung "xay-dung" ──
    # Key TRÙNG registry lõi (app/procedures/registry.py) để process/attach tự nối. keKhaiUrl lấy
    # từ app/procedures/data/ke_khai_links.json. Cách chọn cơ quan trên DVCQG theo đúng
    # ke_khai_links: selectSo → agencyProvinceOnly + agencySoFirst.
    {
        "key": "dieu-chinh-giay-phep-xay-dung",
        "flowProfile": "xay-dung",
        "label": (
            "Cấp điều chỉnh giấy phép xây dựng đối với công trình cấp III, cấp IV và nhà ở riêng lẻ"
        ),
        "shortLabel": "Điều chỉnh giấy phép xây dựng",
        "subtitle": "Điều chỉnh giấy phép xây dựng đã được cấp (thiết kế, quy mô, công năng)",
        "icon": "📝",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-9097-7135-94e7-f539d8b0cc19",
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị điều chỉnh giấy phép xây dựng (Mẫu số 02) — đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gpxd", "name": "Giấy phép xây dựng đã được cấp (kèm bản vẽ đã cấp)",
             "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "ban_ve", "name": "Bộ bản vẽ thiết kế xây dựng điều chỉnh", "icon": "📐",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ hộ / người nộp", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy chứng nhận quyền sử dụng đất, giấy ủy quyền hoặc giấy "
             "tờ khác (nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị điều chỉnh giấy phép xây dựng (Mẫu số 02), đã ký.\n"
            "2. Giấy phép xây dựng đã được cấp (kèm bản vẽ đã cấp).\n"
            "3. Bộ bản vẽ thiết kế xây dựng điều chỉnh.\n"
            "4. Căn cước công dân của chủ hộ / người nộp.\n"
            "5. Nếu có: Giấy chứng nhận quyền sử dụng đất, giấy ủy quyền, giấy chứng nhận đăng "
            "ký doanh nghiệp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        # Registry lõi tách 2 key theo quy trình (nhà ở riêng lẻ / công trình) nhưng CÙNG process
        # và attach. Trợ lý chỉ khai MỘT thủ tục: trường hợp người dân chọn trên hộp thoại quyết
        # định nhánh form qua caseOptions (sua_chua_cai_tao_gpxd nhận constructionVariant truyền vào).
        "key": "sua-chua-cai-tao-gpxd-nha-o-rieng-le",
        "code": "1.013229",  # ke_khai_links ghi mã này dưới key "...-cong-trinh"
        "flowProfile": "xay-dung",
        "label": (
            "Cấp giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV và nhà "
            "ở riêng lẻ"
        ),
        "shortLabel": "Cấp phép sửa chữa, cải tạo",
        "subtitle": "Giấy phép sửa chữa, cải tạo nhà ở riêng lẻ hoặc công trình cấp III, cấp IV",
        "icon": "🔨",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-909c-759d-9dc9-416500074f0f",
        "variants": {
            "options": [
                {"key": "nha_o_rieng_le", "label": "Nhà ở riêng lẻ",
                 "chip": "🏠 Nhà ở riêng lẻ", "portalMatch": "nha o rieng le",
                 "desc": "sửa chữa, cải tạo nhà ở của hộ gia đình, cá nhân",
                 "pipelineOptions": {"constructionVariant": "nha_o_rieng_le"}},
                {"key": "cong_trinh", "label": "Công trình cấp III, cấp IV",
                 "chip": "🏢 Công trình cấp III, cấp IV",
                 "portalMatch": "cong trinh", "portalAvoid": "nha o rieng le",
                 "desc": "công trình cấp III, cấp IV, không phải nhà ở riêng lẻ",
                 "pipelineOptions": {"constructionVariant": "khong_theo_tuyen"}},
            ],
        },
        "caseOptions": _GPXD_CASE_OPTIONS,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp giấy phép xây dựng (Mẫu số 01) — đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất (sổ đỏ) hoặc giấy tờ về "
             "quyền sử dụng đất", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "ban_ve", "name": "Bản vẽ hiện trạng và bản vẽ thiết kế sửa chữa, cải tạo",
             "icon": "📐", "sides": 1, "repeatable": True},
            {"key": "anh", "name": "Ảnh chụp hiện trạng công trình và công trình lân cận",
             "icon": "📷", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ hộ / người nộp", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy ủy quyền hoặc giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp giấy phép xây dựng (Mẫu số 01), đã ký.\n"
            "2. Giấy chứng nhận quyền sử dụng đất hoặc giấy tờ hợp pháp về đất đai.\n"
            "3. Bản vẽ hiện trạng bộ phận công trình sửa chữa, cải tạo và bộ bản vẽ thiết kế.\n"
            "4. Ảnh chụp hiện trạng công trình và công trình lân cận.\n"
            "5. Căn cước công dân của chủ hộ / người nộp; nếu ủy quyền: giấy ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cung-cap-thong-tin-quy-hoach",
        "flowProfile": "xay-dung",
        "label": "Cung cấp thông tin quy hoạch đô thị và nông thôn",
        "shortLabel": "Cung cấp thông tin quy hoạch",
        "subtitle": "Xin thông tin quy hoạch của thửa đất, khu vực",
        "icon": "🗺️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-9852-71ed-96f2-8110da8fd4f0",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        "requiredDocs": [
            {"key": "don", "name": "Đơn (văn bản) đề nghị cung cấp thông tin quy hoạch — đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nộp", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất của thửa đất cần tra cứu",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy ủy quyền hoặc giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn (văn bản) đề nghị cung cấp thông tin quy hoạch, đã ký.\n"
            "2. Căn cước công dân của người nộp.\n"
            "3. Giấy chứng nhận quyền sử dụng đất của thửa đất cần tra cứu quy hoạch.\n"
            "4. Nếu nộp thay: giấy ủy quyền.\n"
            "Hệ thống gộp đơn, giấy chứng nhận và căn cước thành 1 tệp để đính kèm."
        ),
    },
    {
        "key": "cap-phep-long-duong-via-he",
        "flowProfile": "xay-dung",
        "label": "Cấp phép sử dụng tạm thời lòng đường, vỉa hè vào mục đích khác",
        "shortLabel": "Sử dụng tạm thời lòng đường, vỉa hè",
        "subtitle": "Xin phép dùng tạm lòng đường, vỉa hè (sự kiện, tập kết vật liệu...)",
        "icon": "🚧",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-90a2-7673-a2f5-9ba3da842499",
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp phép sử dụng tạm thời lòng đường, vỉa hè — đã "
             "ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "phuong_an", "name": "Phương án sử dụng / sơ đồ vị trí", "icon": "🗺️",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nộp / người đại diện",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy chứng nhận đăng ký doanh nghiệp, giấy cam kết, hợp đồng "
             "thuê nhà hoặc giấy tờ khác (nếu có)", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp phép sử dụng tạm thời lòng đường, vỉa hè, đã ký.\n"
            "2. Phương án sử dụng hoặc sơ đồ vị trí.\n"
            "3. Căn cước công dân của người nộp / người đại diện.\n"
            "4. Nếu có: giấy chứng nhận đăng ký doanh nghiệp, giấy cam kết, hợp đồng thuê nhà, "
            "giấy phép cũ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cap-giay-phep-lien-van-viet-lao",
        # Cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io) — Phần I người nộp + Phần II đề nghị cùng trang
        # kê khai. Danh sách phương tiện (Phần III) nạp từ hồ sơ xe của tài khoản → người dân tự
        # bấm "Thêm xe"; extension chỉ điền Phần I/II và tick dòng đính kèm.
        "flowProfile": "xay-dung",
        "label": "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào",
        "shortLabel": "Giấy phép liên vận Việt Nam - Lào",
        "subtitle": "Cấp mới / cấp lại giấy phép liên vận cho xe đi Lào",
        "icon": "🚚",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-2aa0-754f-9f94-b2b89ed0f198",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        "requiredDocs": [
            {"key": "don", "name": "Giấy đề nghị cấp, cấp lại Giấy phép liên vận Việt Nam - Lào "
             "— đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng đơn", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "dang_ky_xe", "name": "Giấy chứng nhận đăng ký xe ô tô của phương tiện",
             "icon": "🚗", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Hợp đồng dự án tại Lào, quyết định cử đi công tác, hợp đồng "
             "thuê xe (nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị cấp, cấp lại Giấy phép liên vận Việt Nam - Lào, đã ký.\n"
            "2. Căn cước công dân của người đứng đơn.\n"
            "3. Giấy chứng nhận đăng ký xe ô tô của phương tiện xin cấp phép.\n"
            "4. Nếu có: hợp đồng/tài liệu công trình, dự án tại Lào; quyết định cử đi công tác (xe "
            "công vụ); hợp đồng thuê phương tiện (xe không chính chủ).\n"
            "Danh sách phương tiện trên đơn: bạn tự bấm 'Thêm xe' và chọn biển số đã đăng ký.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cap-giay-phep-chat-ha-cay-xanh",
        "provinceOnly": ["danang"],  # đặc thù Đà Nẵng: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.002693, cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io dom-* + attach attp-row 2 dòng: Đơn
        # Mẫu 01 / Ảnh hiện trạng cây). Key TRÙNG lõi → process/attach tự nối. Bảng kê cây là datagrid
        # data[panel][tbantest][i][...], fill-core.js đã có nhánh datagrid (bấm "Thêm dòng").
        # ke_khai_links khai selectSoProvinces ["danang"] (tỉnh khác chọn cấp xã) + autoConfirm false.
        # Registry trợ lý chưa có cờ chọn Sở theo tỉnh → chỉ mở cho Đà Nẵng, chọn Sở như NOXH Bộ Xây dựng.
        "flowProfile": "xay-dung",
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.002693",
                "019d2bfe-230c-75d8-8979-11b8bdc68e6c",
            ],
            "textIncludes": [
                "cấp giấy phép chặt hạ, dịch chuyển cây xanh",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp giấy phép chặt hạ, dịch chuyển cây xanh",
        "shortLabel": "Giấy phép chặt hạ, dịch chuyển cây xanh",
        "subtitle": "Xin phép chặt hạ hoặc di dời cây xanh đô thị (Sở Xây dựng)",
        "icon": "🌳",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-230c-75d8-8979-11b8bdc68e6c",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp giấy phép chặt hạ, dịch chuyển cây xanh (Mẫu số 01) "
             "có bảng kê cây xanh — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ hồ sơ", "icon": "🪪",
             "sides": 2, "repeatable": True},
            {"key": "anh_hien_trang", "name": "Ảnh chụp hiện trạng cây xanh cần chặt hạ, dịch chuyển",
             "icon": "🌳", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất (nếu có)", "icon": "📜",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd_nguoi_nop", "name": "Căn cước công dân của người nộp thay (nếu có)",
             "icon": "🪪", "sides": 2, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (của CHỦ HỒ SƠ — người/tổ chức đề nghị cấp phép):\n"
            "1. Đơn đề nghị cấp giấy phép chặt hạ, dịch chuyển cây xanh (Mẫu số 01) có bảng kê cây "
            "xanh, đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của chủ hồ sơ.\n"
            "3. Ảnh chụp hiện trạng cây xanh cần chặt hạ, dịch chuyển.\n"
            "4. Nếu có: giấy chứng nhận quyền sử dụng đất.\n"
            "5. Nếu người khác nộp thay: thêm căn cước của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Trợ lý điền Phần I (người nộp), Phần II (chủ hồ sơ + nội dung đơn), bảng kê cây xanh (nhiều "
            "dòng), lý do và thông tin ký.\n"
            "Bước đính kèm: Đơn Mẫu 01 vào dòng 'Đơn đề nghị' (Bản chính), ảnh hiện trạng vào dòng 'Ảnh "
            "chụp hiện trạng cây xanh'."
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
        "key": "tam-ngung-kinh-doanh",
        # HkdOnline, businessWorkflow "suspension" — cùng wizard "Chọn loại đăng ký thay đổi" với
        # chấm dứt (radio SUSPEN, có AutoPostBack). Bootstrap dừng ở màn TRA CỨU hộ kinh doanh để
        # nhận giấy tờ trước (mã số nằm trong GCN), pipeline xong FE mới đi nốt wizard rồi điền
        # trang DW_SUSPENSIONEdit (từ ngày / đến ngày / lý do) + Người nộp hồ sơ.
        "detect": {
            "urlIncludes": [
                "hokinhdoanh.dkkd.gov.vn",
                "019d2bfb-d768-7446-bd77-3bb11051041c",
            ],
            "headingDisabled": True,
        },
        "label": "Tạm ngừng kinh doanh hộ kinh doanh",
        "shortLabel": "Tạm ngừng hộ kinh doanh",
        "subtitle": "Tạm ngừng hộ kinh doanh trong một thời gian rồi kinh doanh lại",
        "icon": "⏸️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-d768-7446-bd77-3bb11051041c",
        "needsAgencySelect": True,
        "businessWorkflow": "suspension",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "thong_bao", "name": "Giấy đề nghị đăng ký tạm ngừng kinh doanh (ghi rõ thời "
             "gian và lý do tạm ngừng) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn_cu", "name": "Giấy chứng nhận đăng ký hộ kinh doanh (để lấy mã số tra "
             "cứu)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Căn cước công dân, văn bản ủy quyền hoặc giấy tờ khác",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        # Chỉ 2 trang: nội dung tạm ngừng + người nộp hồ sơ (khớp registry lõi).
        "pages": [
            {"key": "tam-ngung-hoat-dong", "label": "Tạm ngừng kinh doanh"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị đăng ký tạm ngừng kinh doanh, đã ký (ghi rõ tạm ngừng từ ngày ... đến "
            "hết ngày ..., lý do tạm ngừng).\n"
            "2. Giấy chứng nhận đăng ký hộ kinh doanh — QUAN TRỌNG: hệ thống lấy mã số hộ kinh "
            "doanh từ đây để tra cứu.\n"
            "3. Nếu có: căn cước công dân, văn bản ủy quyền hoặc giấy tờ khác.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cap-lai-cap-doi-gcn-ho-kinh-doanh",
        # HkdOnline, businessWorkflow "reissue" — KHÁC chấm dứt/tạm ngừng: rẽ ngay ở màn chọn loại
        # đăng ký (radio REI, không qua "Chọn loại đăng ký thay đổi"). Bootstrap dừng ở màn TRA CỨU
        # hộ kinh doanh để nhận giấy tờ trước (mã số nằm trong Giấy đề nghị/GCN), pipeline xong FE
        # mới đi nốt wizard rồi điền trang DW_RE_ISSUANCEEdit (cấp lại/cấp đổi + lý do) + Người nộp.
        "detect": {
            "urlIncludes": [
                "hokinhdoanh.dkkd.gov.vn",
                "019d2bfc-d9d1-7475-8e58-1aa4479901eb",
            ],
            "headingDisabled": True,
        },
        "label": "Cấp lại, cấp đổi Giấy chứng nhận đăng ký hộ kinh doanh",
        "shortLabel": "Cấp lại GCN hộ kinh doanh",
        "subtitle": "Xin cấp lại GCN hộ kinh doanh bị mất, hỏng hoặc cấp đổi sang mẫu mới",
        "icon": "📑",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfc-d9d1-7475-8e58-1aa4479901eb",
        "needsAgencySelect": True,
        "businessWorkflow": "reissue",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "de_nghi", "name": "Giấy đề nghị cấp lại/cấp đổi Giấy chứng nhận đăng ký hộ "
             "kinh doanh (Mẫu số 2) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn_cu", "name": "Giấy chứng nhận đăng ký hộ kinh doanh cũ (nếu còn — để "
             "lấy mã số tra cứu)", "icon": "📑", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Căn cước công dân, văn bản ủy quyền hoặc giấy tờ khác",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        # Chỉ 2 trang: thông tin đề nghị cấp lại + người nộp hồ sơ (khớp registry lõi).
        "pages": [
            {"key": "thong-tin-de-nghi-cap-lai", "label": "Thông tin đề nghị cấp lại GCN/GXNTĐ"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị cấp lại/cấp đổi Giấy chứng nhận đăng ký hộ kinh doanh (Mẫu số 2), đã "
            "ký — QUAN TRỌNG: hệ thống lấy mã số hộ kinh doanh và lý do cấp lại từ đây.\n"
            "2. Nếu còn: Giấy chứng nhận đăng ký hộ kinh doanh cũ.\n"
            "3. Nếu có: căn cước công dân, văn bản ủy quyền hoặc giấy tờ khác.\n"
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
        "label": "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        # Thủ tục Bắc Ninh: label = label registry lõi bỏ tiền tố "[Tỉnh Bắc Ninh] "; shortLabel chỉ CẮT
        # GỌN tên hành chính (giữ chữ gốc, không đổi sang "sổ đỏ", không thêm "(Bắc Ninh)"); tên đã
        # ngắn thì không đặt shortLabel.
        "shortLabel": "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất",
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
        "bacNinhAuthorizedPerson": _BN_AUTHORIZED_PERSON,
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
        "label": "Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        "shortLabel": "Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất",
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
        "bacNinhAuthorizedPerson": _BN_AUTHORIZED_PERSON,
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
    {
        "key": "dinh-chinh-gcn-da-cap-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 18) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh + agencySoFirst.
        # Key TRÙNG auto-fill → pipeline process/attach tự nối. Cổng BN đã chuyển thủ tục sang
        # 1.115436 (cấp tỉnh, DVCQG "chọn Sở"); giữ 1.115476 cho link cũ. Detect y hệt lõi, KHÔNG
        # thêm textIncludes: "đính chính giấy chứng nhận đã cấp" là tiền tố của "...đã cấp lần đầu
        # có sai sót" (dinh-chinh-sai-sot-bac-ninh) → textPriority sẽ cướp trang của nhau.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115436", "maThuTucHanhChinh=1.115476"],
            "headingDisabled": True,
        },
        "label": "Đính chính giấy chứng nhận đã cấp",
        "subtitle": "Sửa thông tin ghi sai trên Giấy chứng nhận quyền sử dụng đất tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f02e5-91cd-7697-8bb3-89bd36d1fa8a",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai (Mẫu số 18) — đã kê khai, ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ / "
             "sổ hồng)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "sai_sot", "name": "Giấy tờ chứng minh sai sót (giấy khai sinh, căn cước, "
             "quyết định...)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền hoặc giấy tờ khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) đã kê khai, ký — nguồn chính điền đơn.\n"
            "2. Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ/sổ hồng).\n"
            "3. Giấy tờ chứng minh sai sót thông tin trên Giấy chứng nhận (giấy khai sinh, căn "
            "cước, quyết định...).\n"
            "4. Căn cước công dân của người sử dụng đất; nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dang-ky-bien-dong-thoa-thuan-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 18) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key TRÙNG auto-fill
        # → process chung 1.115468, attach riêng (plan_thoa_thuan, 18 thành phần). ke_khai_links
        # chỉ khai provinceOnlyAgency (KHÔNG selectSo) → không agencySoFirst. Detect y hệt lõi,
        # KHÔNG thêm textIncludes: tên thủ tục dài, đầu tên trùng các thủ tục đăng ký biến động khác.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115470"],
            "headingDisabled": True,
        },
        "label": (
            "Đăng ký biến động đối với trường hợp thay đổi quyền sử dụng đất, quyền sở hữu "
            "tài sản gắn liền với đất theo thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng; "
            "quyền sử dụng đất xây dựng công trình trên mặt đất phục vụ cho việc vận hành, khai thác sử dụng "
            "công trình ngầm, quyền sở hữu công trình ngầm; bán tài sản, điều chuyển, chuyển nhượng quyền sử "
            "dụng đất là tài sản công theo quy định của pháp luật về quản lý, sử dụng tài sản công; nhận "
            "quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất theo kết quả giải quyết tranh chấp, "
            "khiếu nại, tố cáo về đất đai hoặc bản án, quyết định của Tòa án, quyết định thi hành án của cơ "
            "quan thi hành án đã được thi hành; quyết định hoặc phán quyết của Trọng tài thương mại Việt Nam "
            "về giải quyết tranh chấp giữa các bên phát sinh từ hoạt động thương mại liên quan đến đất đai; "
            "nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất do xử lý tài sản thế chấp là "
            "quyền sử dụng đất, tài sản gắn liền với đất đã được đăng ký, bao gồm cả xử lý khoản nợ có nguồn "
            "gốc từ khoản nợ xấu của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài"
        ),
        "shortLabel": (
            "Đăng ký biến động theo thỏa thuận của hộ gia đình hoặc của vợ và chồng, kết quả giải "
            "quyết tranh chấp, xử lý tài sản thế chấp"
        ),
        "subtitle": "Sang tên sổ đỏ theo thỏa thuận vợ chồng/hộ gia đình, bản án, xử lý thế chấp tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f1681-0ec2-72f9-a55f-b81cd1fb36fd",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai (Mẫu số 18) — đã kê khai, ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ / "
             "sổ hồng)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "can_cu", "name": "Văn bản căn cứ biến động (thỏa thuận hộ gia đình/vợ chồng, "
             "bản án, quyết định giải quyết tranh chấp, hợp đồng xử lý thế chấp...)", "icon": "📑",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng tên sau biến động",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền, giấy kết hôn/ly hôn, bản vẽ tách thửa "
             "hoặc giấy tờ khác", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "bacNinhAuthorizedPerson": _BN_AUTHORIZED_PERSON,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) người đứng tên sau biến động đã kê khai, "
            "ký — nguồn chính điền đơn.\n"
            "2. Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ/sổ hồng).\n"
            "3. Văn bản căn cứ biến động: thỏa thuận của các thành viên hộ gia đình hoặc của vợ và "
            "chồng; bản án, quyết định của Tòa án, quyết định thi hành án; quyết định giải quyết "
            "tranh chấp; hợp đồng/văn bản xử lý tài sản thế chấp.\n"
            "4. Căn cước công dân của người đứng tên sau biến động; nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dang-ky-bien-dong-dat-dai-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 18) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key TRÙNG auto-fill
        # → process/attach 1.115468 (16 thành phần TP-H05) tự nối. ke_khai_links khai selectSo →
        # agencySoFirst. Detect y hệt lõi, KHÔNG thêm textIncludes: đầu tên trùng 1.115470 và các
        # thủ tục đăng ký biến động khác.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115468"],
            "headingDisabled": True,
        },
        "label": (
            "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất "
            "trong các trường hợp chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án dồn "
            "điền, đổi thửa; chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn "
            "liền với đất, góp vốn bằng quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất; cho thuê, "
            "cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng; bán hoặc tặng "
            "cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất thuê của Nhà nước theo hình "
            "thức thuê đất trả tiền hàng năm; mua bán nhà ở có thời hạn"
        ),
        "shortLabel": (
            "Đăng ký biến động quyền sử dụng đất trong các trường hợp chuyển đổi, chuyển nhượng, "
            "thừa kế, tặng cho, góp vốn"
        ),
        "subtitle": "Đăng ký biến động khi chuyển nhượng, thừa kế, tặng cho, góp vốn quyền sử dụng đất tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f1670-20cd-712b-b05b-59235ae8a21b",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai (Mẫu số 18) bên nhận chuyển quyền "
             "— đã kê khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ / "
             "sổ hồng)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "hop_dong", "name": "Hợp đồng/văn bản chuyển quyền (chuyển nhượng, tặng cho, "
             "thừa kế, góp vốn...) đã công chứng/chứng thực", "icon": "📑", "sides": 1,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của bên nhận chuyển quyền",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền, tờ khai thuế, giấy kết hôn/khai sinh hoặc "
             "giấy tờ khác", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "bacNinhAuthorizedPerson": _BN_AUTHORIZED_PERSON,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) bên NHẬN chuyển quyền đã kê khai, ký — "
            "nguồn chính điền đơn.\n"
            "2. Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ/sổ hồng).\n"
            "3. Hợp đồng/văn bản chuyển quyền (chuyển đổi, chuyển nhượng, tặng cho, thừa kế, góp vốn, "
            "cho thuê, mua bán nhà ở có thời hạn) kèm lời chứng công chứng/chứng thực.\n"
            "4. Căn cước công dân của bên nhận chuyển quyền; nếu nộp thay: văn bản ủy quyền (bắt buộc).\n"
            "5. Tờ khai thuế, lệ phí trước bạ, giấy kết hôn/khai sinh, biên bản bàn giao đất (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "tach-hop-thua-dat-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 22) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key TRÙNG auto-fill
        # → process/attach 1.115458 (4 thành phần TP-H05) tự nối. ke_khai_links khai selectSo →
        # agencySoFirst. Detect y hệt lõi, KHÔNG thêm textIncludes.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115458"],
            "headingDisabled": True,
        },
        "label": "Tách thửa đất hoặc hợp thửa đất",
        "subtitle": "Chia một thửa đất thành nhiều thửa hoặc gộp nhiều thửa thành một tại Bắc Ninh",
        "icon": "📐",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f1258-75a5-72c7-916e-b0299f0b17c3",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 22) — đã kê "
             "khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ / "
             "sổ hồng)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "ban_ve", "name": "Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22a)",
             "icon": "📐", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Văn bản của cơ quan có thẩm quyền về tách/hợp thửa, văn bản ủy "
             "quyền, giấy phép đo đạc hoặc giấy tờ khác", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 22) người sử dụng đất đã kê khai, ký — "
            "nguồn chính điền đơn.\n"
            "2. Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ/sổ hồng).\n"
            "3. Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22a).\n"
            "4. Căn cước công dân của người sử dụng đất; nếu nộp thay: văn bản ủy quyền.\n"
            "5. Văn bản của cơ quan có thẩm quyền thể hiện nội dung tách/hợp thửa, giấy phép hoạt động "
            "đo đạc và bản đồ của đơn vị lập bản vẽ (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cap-doi-gcn-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 18) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key TRÙNG auto-fill
        # → process/attach 1.115464 (TP-H05.000026/000040/000057 + "File đính kèm khác") tự nối.
        # ke_khai_links khai selectSo → agencySoFirst. Detect y hệt lõi, KHÔNG thêm textIncludes.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115464"],
            "headingDisabled": True,
        },
        "label": "Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
        "shortLabel": "Cấp đổi Giấy chứng nhận quyền sử dụng đất",
        "subtitle": "Đổi sổ đỏ/sổ hồng cũ, rách, hỏng hoặc đo đạc lại sang Giấy chứng nhận mới tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f12a3-93d3-71ae-8f20-1cfb89cab2b6",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai (Mẫu số 18) — đã kê khai, ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp cần cấp đổi "
             "(sổ đỏ / sổ hồng)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "trich_do", "name": "Mảnh trích đo bản đồ địa chính thửa đất hoặc phiếu đề nghị "
             "đo đạc (khi cấp đổi do đo đạc lại)", "icon": "📐", "sides": 1, "optional": True,
             "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền hoặc giấy tờ khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) người sử dụng đất đã kê khai, ký — nguồn "
            "chính điền đơn.\n"
            "2. Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp cần cấp đổi (sổ đỏ/sổ hồng).\n"
            "3. Căn cước công dân của người sử dụng đất; nếu nộp thay: văn bản ủy quyền.\n"
            "4. Mảnh trích đo bản đồ địa chính thửa đất hoặc phiếu đề nghị đo đạc (nếu cấp đổi do "
            "đo đạc lại).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dang-ky-dat-dai-lan-dau-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 15) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key TRÙNG auto-fill
        # → process/attach 1.115443 (21 dòng TP-H05) tự nối. ke_khai_links (1.115443) KHÔNG khai
        # provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã của tài khoản, không agencyProvinceOnly,
        # không agencySoFirst. Detect y hệt lõi, KHÔNG thêm textIncludes: 1.115443 là mã quốc gia,
        # urlScope khóa host để cổng iGate tỉnh khác không nhận nhầm.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115443"],
            "headingDisabled": True,
        },
        "label": (
            "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử "
            "dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu"
        ),
        "shortLabel": "Đăng ký đất đai, cấp Giấy chứng nhận quyền sử dụng đất lần đầu",
        "subtitle": "Kê khai đăng ký đất đai và xin cấp Giấy chứng nhận quyền sử dụng đất lần đầu tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f0347-7cb9-732a-bce1-a787258e29e1",
        "needsAgencySelect": True,
        "agencyProvince": "Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15) — đã "
             "kê khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "nguon_goc", "name": "Giấy tờ về nguồn gốc sử dụng đất (giấy giao đất, giấy tờ mua "
             "bán, chuyển nhượng, tặng cho, thừa kế...)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "trich_do", "name": "Trích lục/trích đo bản đồ địa chính thửa đất (nếu có)",
             "icon": "📐", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Danh sách đồng sử dụng (Mẫu 15a), giấy chứng nhận kết hôn, tờ "
             "khai/chứng từ nghĩa vụ tài chính, văn bản ủy quyền hoặc giấy tờ khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15) người sử dụng đất đã kê khai, "
            "ký — nguồn chính điền đơn.\n"
            "2. Giấy tờ về nguồn gốc sử dụng đất (giấy giao đất, giấy tờ mua bán, chuyển nhượng, tặng "
            "cho viết tay, giấy tờ thừa kế...).\n"
            "3. Căn cước công dân của người sử dụng đất; nếu nộp thay: văn bản ủy quyền.\n"
            "4. Trích lục/trích đo bản đồ địa chính, Danh sách đồng sử dụng (Mẫu 15a), giấy chứng nhận "
            "kết hôn, tờ khai/chứng từ nghĩa vụ tài chính (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "thu-hoi-gcn-cap-sai-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm 2896 — đơn đăng ký đất đai) — cùng nền 2 tab
        # CÙNG TRANG với biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key
        # TRÙNG auto-fill → process/attach 1.115447 (TP-H05.000177/000174) tự nối. ke_khai_links
        # (1.115447) KHÔNG khai provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã của tài khoản,
        # không agencyProvinceOnly, không agencySoFirst. Detect y hệt lõi, KHÔNG thêm textIncludes:
        # 1.115447 là mã quốc gia, urlScope khóa host để cổng iGate tỉnh khác không nhận nhầm.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115447"],
            "headingDisabled": True,
        },
        "label": (
            "Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định do người sử dụng "
            "đất, chủ sở hữu tài sản gắn liền với đất phát hiện và cấp lại Giấy chứng nhận sau khi thu hồi"
        ),
        "shortLabel": (
            "Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định và cấp lại Giấy chứng nhận"
        ),
        "subtitle": "Đề nghị thu hồi sổ đỏ cấp lần đầu không đúng quy định và cấp lại sổ mới tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f1100-edad-7436-8505-177fbd9aa9e2",
        "needsAgencySelect": True,
        "agencyProvince": "Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "van_ban_kien_nghi", "name": "Văn bản kiến nghị việc cấp Giấy chứng nhận không đúng "
             "quy định (thường là Biên bản họp gia đình)", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận quyền sử dụng đất đang xin thu hồi (sổ đỏ / "
             "sổ hồng)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền hoặc giấy tờ khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Văn bản kiến nghị việc cấp Giấy chứng nhận không đúng quy định (thường là Biên bản họp "
            "gia đình) — nguồn chính thông tin thửa đất.\n"
            "2. Bản gốc Giấy chứng nhận quyền sử dụng đất đang xin thu hồi (sổ đỏ/sổ hồng).\n"
            "3. Căn cước công dân của người sử dụng đất; nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dinh-chinh-sai-sot-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 18) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key TRÙNG auto-fill
        # → process/attach 1.115446 (4 nhóm: Đơn Mẫu 18, bản gốc GCN, giấy tờ chứng minh sai sót,
        # ủy quyền) tự nối. ke_khai_links (1.115446) KHÔNG khai provinceOnlyAgency / selectSo → chọn
        # đủ Tỉnh + Phường/Xã của tài khoản, không agencyProvinceOnly, không agencySoFirst. Detect y
        # hệt lõi, KHÔNG thêm textIncludes: tên trùng tiền tố với dinh-chinh-gcn-da-cap-bac-ninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115446"],
            "headingDisabled": True,
        },
        "label": "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "subtitle": "Sửa thông tin ghi sai trên Giấy chứng nhận cấp lần đầu tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f10fb-9fa4-7462-9c30-f264a10e839b",
        "needsAgencySelect": True,
        "agencyProvince": "Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai (Mẫu số 18) — đã kê khai, ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp lần đầu (sổ đỏ / "
             "sổ hồng)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "sai_sot", "name": "Giấy tờ chứng minh sai sót (giấy khai sinh, căn cước, "
             "quyết định...)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền hoặc giấy tờ khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) đã kê khai, ký — nguồn chính điền đơn.\n"
            "2. Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp lần đầu (sổ đỏ/sổ hồng).\n"
            "3. Giấy tờ chứng minh sai sót thông tin trên Giấy chứng nhận (giấy khai sinh, căn "
            "cước, quyết định...).\n"
            "4. Căn cước công dân của người sử dụng đất; nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "giao-thue-chuyen-muc-dich-dat-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 01/02) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key TRÙNG auto-fill
        # → process/attach 1.115438 (cấp xã; ô GCN KQ005881, CCCD/ủy quyền vào ô bổ sung) tự nối.
        # ke_khai_links (1.115438) KHÔNG khai provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã
        # của tài khoản, không agencyProvinceOnly, không agencySoFirst. Detect y hệt lõi, KHÔNG thêm
        # textIncludes: tên thủ tục trùng bản Ninh Bình/Quảng Ngãi/Đà Nẵng, urlScope khóa host.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115438"],
            "headingDisabled": True,
        },
        "label": (
            "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất; giao đất và giao rừng; "
            "cho thuê đất và cho thuê rừng; gia hạn sử dụng đất"
        ),
        "shortLabel": "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất",
        "subtitle": "Xin giao đất, thuê đất, chuyển mục đích hoặc gia hạn sử dụng đất tại Bắc Ninh",
        "icon": "🏞️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f0304-d67f-75ee-8bab-4b9e18b0b9d0",
        "needsAgencySelect": True,
        "agencyProvince": "Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất "
             "(Mẫu số 01/02) — đã kê khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất (sổ đỏ / sổ hồng) hoặc quyết "
             "định giao đất, cho thuê đất", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền, Đơn Mẫu 01/04, phương án sử dụng tầng đất mặt "
             "(Mẫu 26) hoặc giấy tờ khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 01/02) người "
            "đề nghị đã kê khai, ký — nguồn chính điền đơn.\n"
            "2. Bản gốc/bản sao Giấy chứng nhận quyền sử dụng đất (sổ đỏ/sổ hồng) hoặc quyết định giao "
            "đất, cho thuê đất.\n"
            "3. Căn cước công dân của người đề nghị; nếu nộp thay: văn bản ủy quyền.\n"
            "4. Đơn Mẫu 01/04, phương án sử dụng tầng đất mặt (Mẫu 26) khi chuyển mục đích đất "
            "chuyên trồng lúa (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dang-ky-bien-dong-chuyen-nhuong-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm Mẫu 18) — cùng nền 2 tab CÙNG TRANG với
        # biện pháp bảo đảm → samePageAttach + agencyProvince cố định Bắc Ninh. Key TRÙNG auto-fill
        # → process/attach 1.013831 (KQ005897 đơn, KQ0777 GCN, KQ005898 hợp đồng…) tự nối. Mã cũ chưa
        # đổi sang 1.1154xx; phạm vi hẹp hơn 1.115468 (dang-ky-bien-dong-dat-dai-bac-ninh). Không có mục
        # ke_khai_links riêng → keKhaiUrl là trang DVCQG 1.013831, chọn Sở như 1.115468. Lõi detect KHÔNG
        # có urlScope; ở đây thêm để cổng iGate tỉnh khác (Lào Cai/Lâm Đồng/Đà Nẵng cùng mã) không nhận
        # nhầm. KHÔNG thêm textIncludes: đầu tên trùng 1.115468 / 1.115470.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.013831"],
            "headingDisabled": True,
        },
        "label": (
            "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất "
            "trong các trường hợp chuyển nhượng, thừa kế, tặng cho, góp vốn bằng quyền sử dụng đất, quyền "
            "sở hữu tài sản gắn liền với đất; cho thuê, cho thuê lại quyền sử dụng đất"
        ),
        "shortLabel": (
            "Đăng ký biến động quyền sử dụng đất trong các trường hợp chuyển nhượng, thừa kế, tặng "
            "cho, góp vốn; cho thuê, cho thuê lại"
        ),
        "subtitle": "Sang tên khi chuyển nhượng, thừa kế, tặng cho, góp vốn, cho thuê quyền sử dụng đất tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-7ece-728d-9b60-6563e0a7a94e",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai (Mẫu số 18) bên nhận chuyển quyền "
             "— đã kê khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ / "
             "sổ hồng)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "hop_dong", "name": "Hợp đồng/văn bản chuyển quyền (chuyển nhượng, tặng cho, "
             "thừa kế, góp vốn, cho thuê...) đã công chứng/chứng thực", "icon": "📑", "sides": 1,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của bên nhận chuyển quyền",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền, bản vẽ tách thửa, mảnh trích đo hoặc giấy tờ "
             "khác", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) bên NHẬN chuyển quyền đã kê khai, ký — "
            "nguồn chính điền đơn.\n"
            "2. Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp (sổ đỏ/sổ hồng).\n"
            "3. Hợp đồng/văn bản chuyển quyền (chuyển nhượng, tặng cho, thừa kế, góp vốn, cho thuê, "
            "cho thuê lại) kèm lời chứng công chứng/chứng thực.\n"
            "4. Căn cước công dân của bên nhận chuyển quyền; nếu nộp thay: văn bản ủy quyền.\n"
            "5. Bản vẽ tách thửa, mảnh trích đo, văn bản đồng ý của bên nhận thế chấp (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "ho-tro-nguoi-cao-tuoi-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm) — ATTACH-ONLY: cổng tự điền nhân thân từ
        # VNeID, trợ lý chỉ đính kèm (1 thành phần bắt buộc: Tờ khai Mẫu 01 → KQ001012). Key TRÙNG
        # auto-fill → attach planner tự nối. mode "attach" + samePageAttach: flow coi ô đính kèm trên
        # trang là bước đính kèm luôn, chạy planner ngay khi đủ giấy tờ; FE tự bấm tab "Tải thành phần
        # hồ sơ". ke_khai_links (1.014589) KHÔNG khai provinceOnlyAgency / selectSo → chọn đủ Tỉnh +
        # Phường/Xã của tài khoản (UBND xã tiếp nhận), không agencyProvinceOnly, không agencySoFirst.
        # Detect y hệt lõi; urlScope khóa host để cổng tỉnh khác không nhận nhầm.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.014589"],
            "headingDisabled": True,
        },
        "label": (
            "Hỗ trợ cho Người cao tuổi từ đủ 70 tuổi đến dưới 75 tuổi; Người cao tuổi dưới "
            "75 tuổi thường trú trên địa bàn tỉnh, là Đảng viên được tặng huy hiệu 40 năm tuổi đảng trở "
            "lên, không có lương hưu, trợ cấp bảo hiểm xã hội, trợ cấp xã hội hàng tháng"
        ),
        "shortLabel": (
            "Hỗ trợ cho Người cao tuổi từ đủ 70 tuổi đến dưới 75 tuổi; Người cao tuổi là Đảng viên "
            "được tặng huy hiệu 40 năm tuổi đảng"
        ),
        "subtitle": (
            "Hỗ trợ hằng tháng cho người cao tuổi 70–dưới 75 tuổi hoặc đảng viên có huy hiệu 40 năm "
            "tuổi đảng, không có lương hưu, trợ cấp tại Bắc Ninh"
        ),
        "icon": "👴",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d7c4f-0f4f-756f-a7db-e8f96edb8171",
        "needsAgencySelect": True,
        "agencyProvince": "Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị hưởng trợ cấp xã hội (Mẫu số 01) — đã kê "
             "khai, có xác nhận của UBND xã", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người cao tuổi (nếu có)", "icon": "🪪",
             "sides": 2, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Kết quả tra cứu thông tin dân cư hoặc giấy tờ khác (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đề nghị hưởng trợ cấp xã hội (Mẫu số 01) đã kê khai, có xác nhận của UBND xã.\n"
            "2. Nếu có: căn cước công dân của người cao tuổi; kết quả tra cứu thông tin dân cư.\n"
            "Cổng tự điền thông tin nhân thân từ tài khoản VNeID — thủ tục này chỉ đính kèm. "
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "ho-tro-chi-phi-hoa-tang-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm 1.014582) — key TRÙNG auto-fill → process/attach
        # tự nối. Process mặc định purpose "registration_form" → mapper phát bn-input theo NAME
        # element_757xx (người chết mục I / người đứng ra hỏa táng mục II), fillFormBacNinh khớp theo
        # NAME. Đính 2 thành phần bắt buộc: Đơn Mẫu 01 → KQ001004, Hợp đồng hỏa táng → KQ001005; giấy tờ
        # khác vào ô đính kèm bổ sung. Khối "người được ủy quyền" (doiTuongKhac*) chỉ điền khi công dân
        # chọn đối tượng có ủy quyền (bacNinhAuthorizedPerson). ke_khai_links (1.014582) KHÔNG khai
        # provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã (UBND xã tiếp nhận), không
        # agencyProvinceOnly, không agencySoFirst. Detect y hệt lõi; urlScope khóa host.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.014582"],
            "headingDisabled": True,
        },
        "label": "Thủ tục hỗ trợ chi phí hỏa táng (bao gồm cả điện táng) trên địa bàn tỉnh Bắc Ninh",
        "shortLabel": "Thủ tục hỗ trợ chi phí hỏa táng (bao gồm cả điện táng)",
        "subtitle": "Xin hỗ trợ chi phí hỏa táng, điện táng cho người mất tại Bắc Ninh",
        "icon": "⚱️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d7cdb-1107-74c7-8cd2-ccc4e24b47d1",
        "needsAgencySelect": True,
        "agencyProvince": "Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị hỗ trợ kinh phí hỏa táng (Mẫu số 01) — đã kê khai, ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "hop_dong", "name": "Hợp đồng dịch vụ hỏa táng / điện táng với cơ sở hỏa táng",
             "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "khai_tu", "name": "Trích lục khai tử / Giấy báo tử (nếu có)", "icon": "📜",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng ra hỏa táng (nếu có)", "icon": "🪪",
             "sides": 2, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền, hóa đơn dịch vụ hoặc giấy tờ khác (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "bacNinhAuthorizedPerson": _BN_AUTHORIZED_PERSON,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị hỗ trợ kinh phí hỏa táng (Mẫu số 01) đã kê khai, ký — nguồn chính điền đơn.\n"
            "2. Hợp đồng dịch vụ hỏa táng/điện táng với cơ sở hỏa táng.\n"
            "3. Nếu có: trích lục khai tử/giấy báo tử; hóa đơn dịch vụ; căn cước công dân của người "
            "đứng ra hỏa táng; văn bản ủy quyền.\n"
            "Nếu nộp thay theo ủy quyền, chọn đối tượng \"Người khác ủy quyền\" để trợ lý điền phần "
            "thông tin người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dang-ky-nha-o-xa-hoi-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm 2836, 1.014632) — khung giống hỏa táng. Key TRÙNG
        # auto-fill → process/attach tự nối. Process mặc định purpose "registration_form" → mapper phát
        # bn-input theo NAME element_762xx (Mẫu 02: người kê khai, vợ/chồng, đối tượng, tỉnh dự án),
        # fillFormBacNinh khớp theo NAME. Đính 1 thành phần bắt buộc KQ005445: Mẫu 02 → Bản chính,
        # CCCD + Giấy kết hôn → Bản sao; giấy tờ đối tượng vào ô đính kèm bổ sung. Khối "người được ủy
        # quyền" (doiTuongKhac*) chỉ điền khi công dân chọn đối tượng có ủy quyền (bacNinhAuthorizedPerson).
        # ke_khai_links (1.014632) KHÔNG khai provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã,
        # không agencyProvinceOnly, không agencySoFirst. urlScope khóa host: thủ tục nhà ở xã hội của Bộ
        # Xây dựng ("cho-thue-thue-mua-nha-o-xa-hoi") nằm ở dvc.moc.gov.vn và chỉ mở cho Đà Nẵng.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.014632"],
            "headingDisabled": True,
        },
        "label": (
            "Đăng ký mua, thuê mua, thuê nhà ở xã hội, vay vốn để hộ gia đình, cá nhân tự xây dựng "
            "hoặc cải tạo, sửa chữa nhà ở"
        ),
        "shortLabel": "Đăng ký mua, thuê mua, thuê nhà ở xã hội",
        "subtitle": "Xác nhận điều kiện nhà ở để mua, thuê, thuê mua nhà ở xã hội hoặc vay vốn tại Bắc Ninh",
        "icon": "🏘️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-985c-732b-822b-460f2199467e",
        "needsAgencySelect": True,
        "agencyProvince": "Bắc Ninh",
        "samePageAttach": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "mau_02", "name": "Giấy xác nhận về điều kiện nhà ở (Mẫu số 02) — đã kê khai, ký "
             "(hộ gia đình thường 2 bản: vợ và chồng)", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người kê khai và vợ/chồng", "icon": "🪪",
             "sides": 2, "repeatable": True},
            {"key": "ket_hon", "name": "Giấy chứng nhận kết hôn (nếu đã kết hôn)", "icon": "💍",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền, giấy xác nhận nơi làm việc hoặc giấy tờ chứng minh "
             "đối tượng (nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "bacNinhAuthorizedPerson": _BN_AUTHORIZED_PERSON,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy xác nhận về điều kiện nhà ở (Mẫu số 02) đã kê khai, ký — nguồn chính điền đơn. Hồ sơ "
            "hộ gia đình thường có 2 bản (vợ và chồng).\n"
            "2. Căn cước công dân của người kê khai và vợ/chồng.\n"
            "3. Giấy chứng nhận kết hôn (nếu đã kết hôn).\n"
            "4. Nếu có: văn bản ủy quyền; giấy xác nhận của doanh nghiệp/nơi làm việc; giấy tờ chứng minh "
            "đối tượng.\n"
            "Nếu nộp thay theo ủy quyền, chọn đối tượng \"Người khác ủy quyền\" để trợ lý điền phần "
            "thông tin người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
]

for _procedure in PROCEDURES:
    if (_BYT_HOST in ((_procedure.get("detect") or {}).get("urlScope") or [])
            and "guidedSteps" not in _procedure):
        _procedure["guidedSteps"] = deepcopy(_BYT_GUIDED_STEPS)
        _procedure["wizard"] = {**(_procedure.get("wizard") or {}), "resultStep": _BYT_RESULT_STEP}

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
    "khai-tu-lien-thong",
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


def variant_pipeline_options(proc: dict | None, conv: dict | None) -> dict:
    """Tên cũ — chỉ nhánh `procedure_variant` của case_pipeline_options."""
    variant = str((conv or {}).get("procedure_variant") or "")
    return case_pipeline_options(proc, {"procedure_variant": variant}) if variant else {}


_CODE_PARAM_RE = re.compile(r"(?:mathutuc(?:hanhchinh)?|matthc)=([12]\.\d{6})\b", re.IGNORECASE)
# Mã TTHC quốc gia theo key — nguồn chung với Auto Fill (app/procedures/data/ke_khai_links.json).
_LINK_CODE_BY_KEY: dict[str, str] = {}
for _link in core_ke_khai_links.KE_KHAI_LINKS:
    if _link.get("key") and _link.get("code"):
        _LINK_CODE_BY_KEY.setdefault(str(_link["key"]), str(_link["code"]))


def procedure_code(proc: dict | None) -> str:
    """Mã TTHC quốc gia (vd "1.013225") để công dân tìm thủ tục theo mã số.

    Thứ tự: "code" khai thẳng trên entry → ke_khai_links theo key → mã nằm trong URL nhận diện
    (maThuTuc= / maThuTucHanhChinh= / MaTTHC=). Không có → "" (thủ tục chỉ tìm được theo tên).
    """
    if not proc:
        return ""
    if proc.get("code"):
        return str(proc["code"])
    if proc.get("key") in _LINK_CODE_BY_KEY:
        return _LINK_CODE_BY_KEY[proc["key"]]
    match = _CODE_PARAM_RE.search(str(proc.get("detect") or ""))
    return match.group(1) if match else ""


def case_pipeline_options(proc: dict | None, conv: dict | None) -> dict:
    """Tuỳ chọn pipeline theo TRƯỜNG HỢP GIẢI QUYẾT công dân đã chốt (vd nhánh form nhà ở riêng
    lẻ / công trình) — để mapper khỏi đoán lại từ giấy tờ.

    Nguồn 1: nhãn ô "Trường hợp giải quyết" đọc từ cổng (mae_dialog_*) khớp `caseOptions` theo cụm
    đã fold dấu, luật đầu tiên khớp thắng (match rỗng = mặc định). Nguồn 2 (extension cũ): key
    `procedure_variant` → `variants.options[].pipelineOptions`. Không có gì → {} (mapper tự suy).
    """
    if not proc or not conv:
        return {}
    process = (conv.get("mae_dialog_options") or {}).get("process") or {}
    labels = process.get("options") or []
    picked = (conv.get("mae_dialog_choice") or {}).get("process")
    if isinstance(picked, int) and 0 <= picked < len(labels):
        label = labels[picked]
    else:
        label = process.get("current") or (labels[0] if labels else "")
    if label and proc.get("caseOptions"):
        folded = fold(label)
        for rule in proc["caseOptions"]:
            if fold(rule.get("match") or "") in folded:
                return dict(rule.get("options") or {})
    variant = str(conv.get("procedure_variant") or "")
    for option in (proc.get("variants") or {}).get("options") or []:
        if variant and option.get("key") == variant:
            return dict(option.get("pipelineOptions") or {})
    return {}


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
