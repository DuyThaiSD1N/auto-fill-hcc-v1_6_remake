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

# Cổng Bộ Xây dựng: nhãn "Trường hợp giải quyết" có chữ "nhà ở riêng lẻ" → form nhánh nhà ở (element ...NhaO); còn lại
# là quy trình công trình có ô "Loại hình công trình" (GPXD mới 7 lựa chọn, sửa chữa cải tạo 4) → "cong_trinh" để mapper
# chọn theo đúng mục đơn kê khai. Dùng chung cho GPXD mới và sửa chữa, cải tạo (cùng process cap_giay_phep_xay_dung).
_GPXD_NEW_CASE_OPTIONS = [
    {"match": "nha o rieng le", "options": {"constructionVariant": "nha_o_rieng_le"}},
    {"match": "", "options": {"constructionVariant": "cong_trinh"}},
]

# Cổng iGate Tuyên Quang: mỗi quy trình ở ô "Trường hợp giải quyết" ra một FORM bước 1 khác nhau. Tên quy trình có cụm
# "iLis" / "VBDLIS" (vd "iLis cấp xã - 30 ngày", "1.013978_VBDLIS_20") → options.quyTrinh, pipeline lõi của key gốc tự
# chạy đúng form đó; quy trình còn lại ("5 bước 20 ngày"...) là form gốc.
_TQ_CASE_ILIS = {"match": "ilis", "options": {"quyTrinh": "ilis"}}
_TQ_CASE_VBDLIS = {"match": "vbdlis", "options": {"quyTrinh": "vbdlis"}}
_TQ_CASE_DEFAULT = {"match": "", "options": {}}
# Stepper 4 bước iGate như cổng Bộ Xây dựng; cờ riêng vì bản extension cũ chưa chạy content/bxd/*.js trên host này.
_TQ_BXD_FLOW = {
    "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
    "capability": "supportsBxdFlowTuyenQuang",
}
# Cổng iGate Khánh Hòa (dichvucong.khanhhoa.gov.vn): trang nps/apply "Chọn trường hợp giải quyết" + stepper 4 bước như
# Tuyên Quang; cờ riêng vì bản extension cũ chưa đọc trang đó / chưa chạy content/bxd/*.js trên host này. 1.013995 ra 4
# quy trình cùng một form: nhóm 2.x "đăng ký thay đổi về tài sản" chỉ đổi câu nội dung mặc định khi Đơn không ghi.
_KH_BXD_FLOW = {
    "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
    "capability": "supportsBxdFlowKhanhHoa",
}
_KH_TAI_SAN_CASE_OPTIONS = [
    {"match": "dang ky thay doi ve tai san", "options": {"truongHop": "thay_doi"}},
    {"match": "", "options": {}},
]

# Cổng Lai Châu (dichvucong.laichau.gov.vn, eForm Nth, mỗi bước một trang "Bước N - …"; chat/lai_chau.py, extension
# content/laichau/portal.js, cờ supportsLaiChauFeeStep): trang "Trường hợp nộp hồ sơ" đọc / chọn caseGroups, nút cam
# "Đồng ý và tiếp tục" ở mọi bước, bước 4 "Lệ phí hồ sơ" đọc / chọn groups. name = name ô trên cổng (crawl 09/11/2026);
# "loaiLePhi" = ô loaiLePhi_<mã loại lệ phí>; ô nơi nộp chỉ hiện khi trường hợp đòi. Nhận kết quả tại nhà mà địa chỉ
# trống → bấm "Lấy địa chỉ của Người nộp".
_LC_FEE_STEP = {
    "caseGroups": [
        {"name": "maCoQuan", "label": "Cơ quan giải quyết hồ sơ"},
        {"name": "maQttt", "label": "Trường hợp giải quyết"},
        {"name": "maQuanHuyenNop", "label": "Quận/Huyện nộp hồ sơ"},
        {"name": "maPhuongXaNop", "label": "Phường/Xã nộp hồ sơ"},
    ],
    "groups": [
        {"name": "maHinhThucNhanKetQua", "label": "Hình thức nhận kết quả"},
        {"name": "loaiLePhi", "label": "Mức lệ phí (đồng)"},
    ],
}

# Cổng Bắc Ninh (Liferay): khối "Thông tin trong trường hợp được ủy quyền" (doiTuongKhac*). Công dân chọn
# đối tượng thực hiện có ủy quyền → run_process chạy thêm pipeline purpose="authorized_person" (cùng logic
# nút "Điền thông tin người ủy quyền" của auto-fill) và ghép vào lệnh điền; extension tick ô bổ sung, chọn
# loại đối tượng (subjectOption) rồi mới điền khối đó.
_BN_AUTHORIZED_PERSON = {
    "executionSubjects": ["authorized_person", "enterprise_authorized"],
    "subjectOption": "Cá nhân khác là Công dân Việt Nam",
}

# Luồng tab cổng Bắc Ninh (chat/bac_ninh.py, extension khai supportsBacNinhTabFlow): trợ lý dẫn lần lượt 4 tab cùng
# trang "Chọn cơ quan tiếp nhận" → "Nhập đơn đăng ký" → "Tải thành phần hồ sơ" → "Thông tin đăng ký nhận kết quả",
# có vòng bổ sung ô ở hai tab đầu và nút Nộp hồ sơ ở tab cuối. resultMethods: radio noiNhanKetQua đúng value + nhãn
# trên cổng (value 4 "Tại các điểm tiếp nhận…" cổng để ẩn). Cổng tick sẵn value 1. points: chọn cách này cổng có thể hiện
# thêm danh sách "Điểm tiếp nhận" (radio noiNhanKetQuadiemTiepNhanId, theo cơ quan tiếp nhận) bắt chọn một điểm.
_BN_HOST = "dichvucong.bacninh.gov.vn"
_BN_TAB_FLOW = {
    "resultMethods": [
        {"value": "1", "label": "Tại nơi nộp hồ sơ (theo giấy hẹn trả)", "icon": "🏛️",
         "desc": "Đến nơi nộp hồ sơ nhận kết quả theo giấy hẹn trả.", "default": True, "points": True},
        {"value": "3", "label": "Tại nhà qua bưu chính công ích (VNPOST)", "icon": "📮",
         "desc": "Bưu điện trả kết quả tại nhà; công dân điền địa chỉ nhận trên trang.", "needsInput": True},
    ],
}

# Cổng dịch vụ công Quảng Ninh: thủ tục đặc thù tỉnh đi DVCQG (chọn tỉnh, thẻ "Nộp trực tuyến") rồi bị ném sang
# dichvucong.quangninh.gov.vn/nop-ho-so — bảng thủ tục (bấm "Nộp hồ sơ" đúng dòng), đăng nhập VNeID riêng của cổng
# tỉnh, modal "Thông tin chung" (chọn chi nhánh VPĐK). Link kê khai + provincePortalFlow lấy theo MÃ từ ke_khai_links ở
# cuối danh sách (cùng nguồn với content/portal-quangninh.js của Auto Fill); uploadHint lấy từ registry lõi.
_QN_HOST = "dichvucong.quangninh.gov.vn"
# Trang kết quả DVCQG ra thẻ UBND lẫn thẻ VPĐK cùng tên thủ tục (ke_khai_links submitCardIncludes).
_QN_VPDK_CARD = "Cơ quan thực hiện: Văn phòng Đăng ký đất đai"
# Chi nhánh VPĐK Auto Fill đang chọn trong modal "Thông tin chung" (ke_khai_links provincePortalFlow.agency).
_QN_VPDK_CO_TO = "Chi nhánh Văn phòng đăng ký đất đai số 12 Cô Tô"

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

# Chứng thực attach-only cổng React Bộ Tư pháp chạy toàn trình như chứng thực bản sao: dẫn đủ 4 bước, quét sớm ở bước
# chủ hồ sơ (một lần quét cả căn cước lẫn giấy cần chứng thực, điền chủ hồ sơ từ mọi giấy, ô còn trống thì hỏi bổ
# sung — chat/owner_review.py) rồi đính vào đúng các ô ở bước sau. Không khai ownerStepDocs: không thêm ô "căn cước
# chủ hồ sơ" riêng, không hỏi "chứng thực luôn thẻ này không" (chỉ bản sao có). Bản extension chưa khai
# supportsGuidedSteps/supportsOwnerScan giữ luồng cũ.
_TU_PHAP_ATTACH_GUIDED_STEPS = {
    "enabled": True,
    "ownerScan": True,
    # `label` đúng NGUYÊN VĂN chữ trên cổng (FE khớp công tắc theo nhãn); cùng bộ với chứng thực bản sao.
    "resultMethods": [
        {"key": "paper", "label": "Nhận kết quả bản giấy có đóng dấu", "icon": "📄",
         "desc": "Nhận bản giấy có đóng dấu của cơ quan.", "default": True},
        {"key": "online", "label": "Nhận kết quả trực tuyến", "icon": "🌐",
         "desc": "Nhận bản điện tử ngay trên hệ thống."},
        {"key": "postal", "label": "Dịch vụ bưu chính công ích", "icon": "📮",
         "desc": "Nhân viên bưu điện sẽ đến địa chỉ trả kết quả để trả hồ sơ.",
         "needsInput": True},
    ],
}


# Cổng Bộ VHTTDL (form liz, trang nộp một trang) — xem lizFlow ở entry thủ tục. commitLabel = nhãn ô cam kết NGUYÊN VĂN
# trên trang (extension khớp theo chữ, ô không có id). Hai cách nhận kết quả = ô "Đề nghị nhận kết quả bản giấy tại nhà
# qua Bưu chính công ích (VNPost)" bỏ tích / tích (extension gạt theo postOffice, không khớp nhãn dưới đây).
_LIZ_FLOW = {
    "commitLabel": ("Tôi cam kết chịu trách nhiệm trước pháp luật về tính hợp pháp, chính xác của các giấy tờ có trong "
                    "hồ sơ và cung cấp đầy đủ thông tin có liên quan"),
}
_LIZ_GUIDED_STEPS = {
    "enabled": False,
    "submitLabel": "Lưu và nộp hồ sơ",
    "resultMethods": [
        {"key": "counter", "label": "Nhận kết quả tại bộ phận một cửa", "icon": "🏢",
         "desc": "Không nhận qua bưu điện, đến bộ phận một cửa lấy kết quả.", "default": True},
        {"key": "postal", "label": "Nhận kết quả bản giấy tại nhà qua bưu điện (VNPost)", "icon": "📮",
         "desc": "Bưu điện chuyển kết quả tới địa chỉ người nhận.", "needsInput": True},
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
        # Cài đặt "Tách giấy tờ" → planner chia tệp gộp theo trang, mỗi giấy vào đúng dòng của nó.
        "key": "khai-sinh-da-co-ho-so",
        "detect": {"urlIncludes": ["maThuTuc=1.004772"]},
        "label": "Thủ tục đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân",
        "shortLabel": "Khai sinh (đã có giấy tờ cá nhân)",
        "subtitle": "Khai sinh cho người chưa từng đăng ký nhưng đã có CCCD, học bạ, bằng cấp…",
        "icon": "🪪",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6711-733d-b674-fc3d805e70c8",
        "supportsSplitDocuments": True,
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
        # Bước 01: hỏi đối tượng mai táng phí (agencyChoice) rồi điền tỉnh/xã + đối tượng. Chỉ khi luồng 6 bước bật.
        "agencyFillPlan": agency_plans.LIEN_THONG_KHAI_TU,
        # Dẫn đủ 6 bước như liên thông khai sinh (chat/lien_thong.py). Bản extension cũ đã khai supportsLienThongFlow
        # nhưng chưa điền được bước chọn cơ quan / ô cam đoan của khai tử → cần thêm cờ supportsLienThongKhaiTu.
        # Bước 5 (template khaitu-b5 của cổng): giấy khai tử cổng khoá "Đến cơ quan giải quyết"; mai táng phí là ô
        # chọn NHIỀU giá trị (bấm là cộng thêm, không thay) → chỉ hiển thị, không cho đổi trong thẻ.
        "lienThongFlow": {
            "capability": "supportsLienThongKhaiTu",
            "agencyChoice": {
                "name": "DtMaitangphi",
                "options": [
                    "Đối tượng được hưởng trợ cấp mai táng phí theo quy định của Luật BHXH",
                    "Đối tượng hưởng mai táng phí theo Pháp lệnh ưu đãi người có công",
                    "Đối tượng bảo trợ xã hội",
                    "Đối tượng nhận trợ cấp khẩn cấp",
                ],
            },
            "resultGroups": [
                {"name": "DkktNkqHinhthuc", "label": "Đăng ký khai tử", "place": "DkktNoiTra"},
                {"name": "QdhmtpNkqHinhthuc", "label": "Trợ cấp mai táng phí", "place": "MtpNkqTaicoquan",
                 "fixed": True},
            ],
        },
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
        # Planner có chế độ tách giấy theo trang (attach/dinh_kem_tach); chỉ boolean True mới tách.
        "supportsSplitDocuments": True,
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
        # Cán bộ hay scan cả bộ hồ sơ thành một PDF → planner tách theo cài đặt "Tách tệp có nhiều giấy tờ".
        "supportsSplitDocuments": True,
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
                 "purpose": "để tôi điền thông tin chủ hồ sơ",
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
                 "purpose": "để tôi điền thông tin người nộp hồ sơ",
                 "certifiedInto": "khac"},
                {"key": "giay_uy_quyen", "name": "Giấy ủy quyền", "icon": "📝", "sides": 1,
                 "purpose": "để tôi điền thông tin ủy quyền và đính kèm vào hồ sơ luôn"},
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS).
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        # sản ngay trên: không consent.
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS).
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        # Cổng React mới (Bộ Tư pháp), cùng khung attach-only với phân chia di sản ngay trên: không consent.
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS).
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        # Cổng React mới (Bộ Tư pháp), cùng khung attach-only với từ chối nhận di sản ngay trên: không consent.
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS).
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        # sản: không consent, không hỏi gộp/tách nhiều hồ sơ.
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS).
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
        # Cổng có 2 dòng cố định: (1) dự thảo sửa đổi/bổ sung/hủy bỏ, (2) giao dịch/hợp đồng cũ đã
        # chứng thực. Mỗi file một dòng, không gộp PDF: giấy tờ tài sản/CCCD/ủy quyền/giấy khác thêm
        # thành phần mới. Bộ phân loại lúc tải lên (pipelines/chung_thuc_sua_doi_giao_dich/
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
            "Bước Thành phần hồ sơ: mỗi file đính nguyên một dòng, không gộp — dự thảo vào dòng 1; "
            "giao dịch cũ đã chứng thực vào dòng 2; giấy tờ tài sản và giấy tờ khác thêm thành phần mới."
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS).
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS).
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        # Toàn trình như chứng thực bản sao (xem _TU_PHAP_ATTACH_GUIDED_STEPS); thẻ căn cước đã có ô riêng trong
        # thành phần hồ sơ nên checklist bước 1 chính là requiredDocs.
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        # Planner tách theo trang khi máy quầy bật "tách giấy tờ" (flow chỉ gửi khi engine cắt được trang).
        "supportsSplitDocuments": True,
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS); thẻ căn cước đã có ô riêng trong
        # thành phần hồ sơ nên checklist bước 1 chính là requiredDocs.
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        # ngay trên: không consent. Cổng hiển thị tên "Thủ tục công nhận tổ trưởng tổ hòa giải (cấp xã)".
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
        # Toàn trình như chứng thực chữ ký (xem _TU_PHAP_ATTACH_GUIDED_STEPS).
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
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
        "key": "dang-ky-tham-du-kiem-tra-ket-qua-tap-su-hanh-nghe-cong-chung",
        # Mã TTHC 1.013818 (Bộ Tư pháp), nộp tại Sở Tư pháp (ke_khai_links: selectSo). Chọn cơ quan cấp Sở y như
        # "cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su" ngay trên (Tỉnh → toggle "Sở" → "Nộp trực tuyến" kết
        # quả ĐẦU TIÊN); phần còn lại là attach-only như "bau-to-truong-to-hoa-giai": không điền tờ khai, toàn trình
        # _TU_PHAP_ATTACH_GUIDED_STEPS. Planner lõi xếp file vào 3 dòng cố định, mỗi file đính nguyên khối.
        "detect": {
            "urlIncludes": [
                "019d2bfd-7e7f-77f8-ba74-3f3328ddfa7c",
                "maThuTuc=1.013818",
            ],
            "textIncludes": ["đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng"],
            "headingDisabled": True,
        },
        "label": "Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng",
        "shortLabel": "Đăng ký kiểm tra kết quả tập sự công chứng",
        "subtitle": "Người tập sự công chứng đăng ký dự kỳ kiểm tra kết quả tập sự (Sở Tư pháp)",
        "icon": "📜",
        "flowProfile": "tu-phap",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-7e7f-77f8-ba74-3f3328ddfa7c",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Tư pháp",
        "infoModalFields": [
            {"label": "Cấp thực hiện", "value": "Cấp Tỉnh"},
            {"label": "Thủ tục", "value": "kiểm tra kết quả tập sự hành nghề công chứng"},
            {"label": "Cơ quan thực hiện", "value": "Sở Tư pháp"},
        ],
        "requiresConsent": False,
        "ownerInfo": {"enabled": False},
        "guidedSteps": deepcopy(_TU_PHAP_ATTACH_GUIDED_STEPS),
        # Không có bộ phân loại riêng: LLM chung xếp theo tên ô lúc tải lên; planner lõi tự phân loại lại theo OCR lúc
        # đính. Chứng từ nộp phí để optional: thiếu thì dòng 2 để trống kèm cảnh báo, không chặn người dân.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "quyet_dinh", "name": "Quyết định công nhận hoàn thành tập sự hành nghề công chứng (bản chính "
             "hoặc bản sao có chứng thực)", "icon": "📃", "sides": 1, "repeatable": True},
            {"key": "nop_phi", "name": "Biên lai / chứng từ nộp phí thẩm định tiêu chuẩn, điều kiện hành nghề công "
             "chứng", "icon": "🧾", "sides": 1, "optional": True, "repeatable": True},
            {"key": "giay_dang_ky", "name": "Giấy đăng ký tham dự kiểm tra kết quả tập sự (Mẫu TP-TSCC-10) đã ký",
             "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi giấy tờ một tệp, hệ thống KHÔNG tách trang):\n"
            "1. Quyết định công nhận hoàn thành tập sự hành nghề công chứng (bản chính hoặc bản sao có chứng thực).\n"
            "2. Biên lai / chứng từ nộp phí thẩm định tiêu chuẩn, điều kiện hành nghề công chứng.\n"
            "3. Giấy đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng (Mẫu TP-TSCC-10) đã ký.\n"
            "Bước Thành phần hồ sơ: Quyết định → dòng 1; chứng từ nộp phí → dòng 2; Giấy đăng ký → dòng 3. Mỗi tệp "
            "đính nguyên khối; giấy khác thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "cap-giay-phep-khai-thac-thuy-san",
        # Mở dần theo tỉnh thí điểm: Đà Nẵng, rồi Quảng Trị (danh mục TTHC cấp tỉnh thí điểm trợ lý, 02/11).
        "provinceOnly": ["danang", "quangtri"],
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
        # Cổng NN&MT iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd; cần cờ riêng
        # vì bản extension cũ chưa chạy content/bxd/*.js trên host này.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMae",
        },
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
        "key": "cap-gcn-dang-ky-tau-ca",
        # Mã TTHC 1.003650, CÙNG cổng NN&MT với giấy phép khai thác ngay trên: DVCQG chỉ chọn Tỉnh
        # (ke_khai_links provinceOnlyAgency) → trang MAE "chọn nơi và loại" chọn Sở NN&MT (maePortal);
        # "Trường hợp giải quyết" (đóng mới / mua bán / nhập khẩu…) hỏi công dân qua hộp thoại MAE như
        # thường. Key TRÙNG lõi → process (nhân thân chủ tàu + người nộp) / attach attp-row 16 dòng tự
        # nối. Form không có ô thông số tàu — tàu chỉ nằm ở file đính kèm.
        "detect": {
            "urlScope": ["dichvucongnnmt.mae.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "019d2bfa-2864-76fe-9234-7c54e1661f21",
                "apply-online/6943d234d7c2fb1812f2c3c4",
                "process=6a5dad038f4b564db2488af7",
            ],
            "textIncludes": ["cấp giấy chứng nhận đăng ký tàu cá"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp giấy chứng nhận đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản",
        "shortLabel": "Cấp giấy chứng nhận đăng ký tàu cá",
        "subtitle": "Đăng ký tàu cá đóng mới, mua bán, chuyển nhượng, nhập khẩu, thuê tàu trần, cải hoán",
        "icon": "🚢",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-2864-76fe-9234-7c54e1661f21",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nông nghiệp và Môi trường",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đăng ký tàu cá (Mẫu số 02a.ĐKT) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ tàu, thêm CCCD người nộp nếu nộp thay",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "an_toan_ky_thuat", "name": "Giấy chứng nhận an toàn kỹ thuật tàu cá (Mẫu số 05.BĐ)",
             "icon": "🛟", "sides": 1, "optional": True, "repeatable": True},
            {"key": "chuyen_nhuong", "name": "Hợp đồng mua bán / giấy tờ chuyển nhượng quyền sở hữu tàu "
             "(nếu mua bán, chuyển nhượng)", "icon": "🤝", "sides": 1, "optional": True, "repeatable": True},
            {"key": "gcn_cu", "name": "Giấy chứng nhận đăng ký tàu cá cũ / Giấy chứng nhận xóa đăng ký "
             "(nếu có)", "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "truoc_ba", "name": "Thông báo / biên lai nộp lệ phí trước bạ (nếu có)", "icon": "🧾",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy chứng nhận xuất xưởng, cải hoán, tờ khai hải quan, hợp đồng thuê "
             "tàu trần hoặc giấy tờ khác", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (của CHỦ TÀU — người/tổ chức đứng tên đăng ký):\n"
            "1. Tờ khai đăng ký tàu cá (Mẫu số 02a.ĐKT), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của chủ tàu (2 mặt); nếu người khác nộp thay thì thêm CCCD người nộp.\n"
            "3. Tùy trường hợp: Giấy chứng nhận an toàn kỹ thuật, Hợp đồng mua bán/chuyển nhượng tàu, Giấy "
            "chứng nhận đăng ký tàu cá cũ, Giấy chứng nhận xóa đăng ký, Thông báo nộp lệ phí trước bạ, Giấy "
            "chứng nhận xuất xưởng/cải hoán, tờ khai hải quan, hợp đồng thuê tàu trần.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ tàu là chủ MỚI (bên mua trong Hợp đồng / người khai Tờ khai 02a.ĐKT), không lấy chủ cũ "
            "trên Giấy chứng nhận đăng ký cũ. Thông tin tàu không nhập lại trên form, chỉ nằm ở file đính kèm.\n"
            "Bước Thành phần hồ sơ: mỗi giấy tờ vào đúng dòng (bản Scan tệp tin); ảnh tàu cần đính thủ "
            "công, căn cước chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "cap-van-ban-chap-thuan-tau-ca",
        # Mã TTHC 1.004344, CÙNG cổng NN&MT và cùng khung chọn cơ quan với "cap-gcn-dang-ky-tau-ca" ngay trên: DVCQG
        # chỉ chọn Tỉnh → trang MAE "chọn nơi và loại" chọn Sở NN&MT (maePortal). ke_khai_links chưa khai
        # provinceOnlyAgency như bản đăng ký tàu; thẩm quyền chấp thuận đóng mới, cải hoán tàu cá là cơ quan thủy
        # sản cấp tỉnh. Key TRÙNG lõi và ke_khai_links → process/attach (attp-row 1 dòng Tờ khai 12.TC) tự nối.
        "detect": {
            "urlScope": ["dichvucongnnmt.mae.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.004344",
                "019d2bfa-3821-734d-a521-ed615d1b1a97",
            ],
            # KHÁC đăng ký tàu cá ngay trên ("cấp giấy chứng nhận đăng ký tàu cá"): đây là xin phép TRƯỚC khi
            # đóng mới, cải hoán, thuê, mua tàu.
            "textIncludes": ["cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá Việt Nam",
        "shortLabel": "Chấp thuận đóng mới, cải hoán, thuê, mua tàu cá",
        "subtitle": "Xin phép trước khi đóng mới, cải hoán, thuê hoặc mua tàu cá",
        "icon": "🚢",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-3821-734d-a521-ed615d1b1a97",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nông nghiệp và Môi trường",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Bảng thành phần hồ sơ 1 dòng cố định (Tờ khai Mẫu 12.TC) nhận nhiều tệp: planner lõi đính MỌI tệp vào
        # dòng này (căn cước đặt tên "Căn cước công dân").
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai chấp thuận đóng mới / cải hoán / thuê / mua tàu cá (Mẫu số "
             "12.TC) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị, thêm CCCD người nộp nếu nộp thay",
             "icon": "🪪", "sides": 2, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (của NGƯỜI ĐỀ NGHỊ — chủ tàu, cá nhân hoặc tổ chức đề nghị):\n"
            "1. Tờ khai chấp thuận đóng mới / cải hoán / thuê / mua tàu cá (Mẫu số 12.TC), đã ký — nguồn chính "
            "để điền form.\n"
            "2. Căn cước công dân (2 mặt) của người đề nghị; nếu người khác nộp thay: thêm căn cước của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Tự nộp thì giữ tích 'Người nộp là chủ hồ sơ'; nộp thay thì bỏ tích và điền riêng hai phần. Trợ lý "
            "điền cả nội dung tờ khai (kính gửi, địa danh, mã định danh, địa chỉ) và thông số tàu.\n"
            "Bước Thành phần hồ sơ: bảng chỉ có một dòng 'Tờ khai theo Mẫu số 12.TC' (bản Scan tệp tin) nhận nhiều "
            "tệp — Tờ khai, căn cước và giấy tờ khác đều đính vào dòng này, mỗi tệp một tên riêng."
        ),
    },
    {
        "key": "cap-lai-chung-chi-hanh-nghe-thu-y",
        # Mã TTHC 1.005319, cổng NN&MT, CÙNG khung chọn cơ quan với "cap-gcn-dang-ky-tau-ca": ke_khai_links khai
        # provinceOnlyAgency + selectSo → DVCQG chỉ chọn Tỉnh, trang MAE "chọn nơi và loại" chọn Sở NN&MT (maePortal).
        # Key TRÙNG lõi và ke_khai_links → process/attach tự nối. Planner lõi (attp-row 1 dòng "Đơn đăng ký cấp
        # lại") đính Đơn + chứng chỉ cũ + ảnh vào dòng đó, BỎ căn cước (đã chạy thử hồ sơ bịa 25/10).
        "detect": {
            "urlScope": ["dichvucongnnmt.mae.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.005319",
                "019d2bfa-47c1-71d9-a6f9-c0f5829bb34e",
            ],
            # KHÁC gia hạn CCHN thú y (2.001064, entry "gia-han-chung-chi-hanh-nghe-thu-y"): "cấp lại" ≠ "gia hạn".
            "textIncludes": ["cấp lại chứng chỉ hành nghề thú y"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp lại Chứng chỉ hành nghề thú y",
        "shortLabel": "Cấp lại chứng chỉ hành nghề thú y",
        "subtitle": "Xin lại chứng chỉ hành nghề thú y bị mất, hư hỏng hoặc sai thông tin",
        "icon": "🐄",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-47c1-71d9-a6f9-c0f5829bb34e",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nông nghiệp và Môi trường",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Dẫn đủ 4 bước bằng luồng chung chat/bxd như các thủ tục khác của cổng NN&MT; bản extension cũ chưa chạy
        # bộ đọc Form.io của chat/bxd trên host này → cần cờ supportsBxdFlowMae.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMae",
        },
        "hasAttachmentStep": True,
        # Bảng thành phần hồ sơ 1 dòng nhận nhiều tệp (Đơn + chứng chỉ cũ + ảnh dồn chung).
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký cấp lại chứng chỉ hành nghề thú y (Mẫu 03.HNTY) — đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng đơn (chỉ để điền, không đính kèm)",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "cchn_cu", "name": "Chứng chỉ hành nghề thú y đã cấp (bản cũ, nếu còn)", "icon": "🐄",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "anh", "name": "Ảnh 4x6 nền xanh", "icon": "🖼️", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (của NGƯỜI ĐỨNG ĐƠN — người được cấp lại chứng chỉ):\n"
            "1. Đơn đăng ký cấp lại chứng chỉ hành nghề thú y (Mẫu 03.HNTY), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân (2 mặt) của người đứng đơn — để điền số căn cước, ngày cấp (đơn thường không ghi).\n"
            "3. Chứng chỉ hành nghề thú y đã cấp (bản cũ) — để lấy số đăng ký và ngày hết hiệu lực.\n"
            "4. Ảnh 4x6 nền xanh.\n"
            "5. Nếu người khác nộp thay: thêm căn cước của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Khối 'Thông tin chung' trên form là người ĐỨNG ĐƠN: trợ lý ghi đè thông tin tài khoản bằng thông tin "
            "trên đơn. Phạm vi hành nghề trợ lý tự tích theo đơn; dòng nào không khớp sẽ báo để tích tay.\n"
            "Bước Thành phần hồ sơ: Đơn 03.HNTY, chứng chỉ cũ và ảnh đều đính vào dòng 'Đơn đăng ký cấp lại' (Bản "
            "chính); căn cước chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat",
        # Mã TTHC 1.013997, giải quyết ở UBND CẤP XÃ (lõi ghi): DVCQG chọn đủ Tỉnh + Phường/Xã rồi sang cổng ngành
        # NN&MT — cùng khuôn cấp xã với "cap-gcn-attp-nong-lam-thuy-san" (maePortal + maeAgencyLevel "ward").
        # Key TRÙNG lõi và ke_khai_links → process/attach tự nối. Planner lõi (attp-row 1 dòng, tách/gộp trang
        # sourceSegments) gộp Đơn 2a/2b + mọi biên bản tiêu hủy vào dòng Đơn, BỎ căn cước (chạy thử 25/10).
        "detect": {
            "urlScope": ["dichvucongnnmt.mae.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.013997",
                "019d2bfa-8686-732b-b2d5-e6a422f1b242",
            ],
            "textIncludes": ["hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật (cơ sở sản xuất không thuộc lực lượng vũ trang "
            "nhân dân)"
        ),
        "shortLabel": "Hỗ trợ thiệt hại do dịch bệnh động vật (dịch tả lợn, cúm gia cầm…)",
        "subtitle": "Chủ hộ chăn nuôi xin hỗ trợ khi vật nuôi bị tiêu hủy do dịch bệnh",
        "icon": "🐖",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-8686-732b-b2d5-e6a422f1b242",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng NN&MT cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin phí, lệ phí" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd. Bản extension cũ khai
        # supportsBxdFlow mà chưa chạy content/bxd/*.js trên host này → cần thêm cờ supportsBxdFlowMae.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMae",
        },
        "hasAttachmentStep": True,
        "requiredDocs": [
            {"key": "don_de_nghi", "name": "Đơn đề nghị hỗ trợ thiệt hại do dịch bệnh động vật (Mẫu số 2a/2b, "
             "Nghị định 116/2025/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            # Cổng chỉ có MỘT dòng (Đơn đề nghị); biên bản nếu có đính chung dòng đó → không bắt buộc.
            {"key": "bien_ban_tieu_huy", "name": "Biên bản tiêu hủy động vật, sản phẩm động vật (đủ các trang "
             "chữ ký)", "icon": "📋", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ hộ (chỉ để điền, không đính kèm)", "icon": "🪪",
             "sides": 2, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF — hệ thống tự tách theo trang):\n"
            "1. Đơn đề nghị hỗ trợ thiệt hại do dịch bệnh động vật (Mẫu số 2a/2b, Nghị định 116/2025/NĐ-CP), đã ký "
            "— nguồn chính về chủ hộ, số căn cước, địa chỉ thường trú.\n"
            "2. Biên bản tiêu hủy động vật, sản phẩm động vật (một hoặc nhiều biên bản, đủ trang chữ ký).\n"
            "3. Nếu có: căn cước công dân của chủ hộ — để điền ngày sinh, ngày cấp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung. Ô Ghi chú được điền tóm tắt "
            "dịch bệnh + số con, khối lượng của từng biên bản.\n"
            "Bước Thành phần hồ sơ: Đơn đề nghị + các biên bản tiêu hủy gộp thành một tệp ở dòng 'Đơn đề nghị' "
            "(Bản chính), Đơn đứng trước; căn cước chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "hoa-giai-tranh-chap-dat-dai",
        # Mã TTHC 1.012812, UBND CẤP XÃ: DVCQG chọn đủ Tỉnh + Phường/Xã rồi sang cổng ngành NN&MT — cùng khuôn cấp xã
        # với "ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat" (maePortal + maeAgencyLevel "ward", wizard 4 bước).
        # Key TRÙNG lõi và ke_khai_links → process/attach tự nối: Form.io Phần I/II + Ghi chú = nội dung Đơn, bảng
        # attp-row 2 dòng (giấy tờ sử dụng đất = Bản sao, Đơn = Bản chính), mỗi file đính nguyên khối.
        "detect": {
            "urlScope": ["dichvucongnnmt.mae.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.012812",
                "019d2bfa-76e6-7468-b6f2-3d412e902b88",
            ],
            "textIncludes": ["hòa giải tranh chấp đất đai"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Hòa giải tranh chấp đất đai",
        "shortLabel": "Hòa giải tranh chấp đất đai tại UBND xã/phường",
        "subtitle": "Người dân xin UBND xã/phường hòa giải tranh chấp ranh giới, quyền sử dụng đất",
        "icon": "🤝",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-76e6-7468-b6f2-3d412e902b88",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMae",
        },
        "hasAttachmentStep": True,
        "requiredDocs": [
            {"key": "don_yeu_cau", "name": "Đơn yêu cầu hòa giải tranh chấp đất đai — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            # Cổng không đánh dấu bắt buộc ở dòng giấy tờ → không chặn người dân chưa có đủ giấy.
            {"key": "giay_to_dat", "name": "Giấy tờ liên quan đến việc sử dụng đất (giấy chuyển nhượng, sổ đỏ, hợp "
             "đồng ủy quyền, bản mô tả ranh giới, phiếu đo đạc…)", "icon": "📋", "sides": 1, "optional": True,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người viết đơn", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp — hệ thống KHÔNG tách trang):\n"
            "1. Đơn yêu cầu hòa giải tranh chấp đất đai, đã ký — nguồn chính về người yêu cầu (họ tên, ngày sinh, "
            "số căn cước, địa chỉ, số điện thoại); nội dung đơn được chép vào ô Ghi chú.\n"
            "2. Các giấy tờ liên quan đến việc sử dụng đất: giấy chuyển nhượng, hợp đồng ủy quyền, thông báo thuế "
            "đất, sổ hộ khẩu, bản mô tả ranh giới, phiếu đo đạc, mảnh trích đo, bản vẽ thửa đất.\n"
            "3. Nếu có: căn cước của người viết đơn — để điền giới tính, nơi cấp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung. Người viết đơn trùng tài "
            "khoản đăng nhập thì trợ lý điền phần người nộp và tích 'Người nộp hồ sơ là chủ hồ sơ'; nộp thay thì giữ "
            "phần người nộp theo tài khoản, điền người viết đơn ở phần chủ hồ sơ. Bật cài đặt 'Lấy người nộp theo tờ "
            "khai' thì phần người nộp luôn ghi theo người viết đơn.\n"
            "Bước Thành phần hồ sơ: giấy tờ sử dụng đất → dòng 1 (Bản sao); Đơn yêu cầu hòa giải → dòng 2 (Bản "
            "chính). Mỗi file đính nguyên khối."
        ),
    },
    {
        "key": "cap-ban-sao-van-bang-so-goc",
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
        # Cổng Bộ GD&ĐT cùng nền iGate với cổng Bộ Xây dựng (stepper 4 bước, tờ khai Form.io, bước 3 receivingKind +
        # cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        "key": "mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc",
        # Mã TTHC 1.014335, cổng Bộ GD&ĐT dvc.moet.gov.vn (Form.io dom-* + dom-expect, attach attp-row 2 dòng gộp PDF).
        # CÙNG nền iGate, cùng wizard với "cap-ban-sao-van-bang-so-goc" ngay trên và cũng KHÔNG có trang "chọn nơi
        # và loại", nhưng KHÁC ở cấp cơ quan: mapper lõi ghi UBND CẤP XÃ nơi sinh viên thường trú giải quyết và
        # ke_khai_links không khai selectSo → DVCQG chọn đủ Tỉnh + Phường/Xã (không agencyProvinceOnly/SoFirst).
        # Key TRÙNG lõi và ke_khai_links → process/attach tự nối.
        # Cổng Bộ GD&ĐT cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moet.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.014335",
                "019d2bf8-c7e3-746e-8437-305980ee5536",
            ],
            # Tiêu đề panel Đơn Phụ lục IV — chỉ thủ tục GDNN / đại học tư thục dùng Phụ lục IV NĐ 238 (như lõi).
            "textIncludes": ["đơn đề nghị chi trả tiền miễn giảm học phí theo mẫu tại phụ lục iv"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Đề nghị miễn, giảm học phí trong cơ sở giáo dục nghề nghiệp, cơ sở giáo dục đại học tư thục và cơ sở "
            "giáo dục nghề nghiệp, cơ sở giáo dục đại học thuộc tổ chức kinh tế, doanh nghiệp nhà nước"
        ),
        "shortLabel": "Miễn, giảm học phí (trường nghề, đại học tư thục)",
        "subtitle": "Sinh viên trường tư thục thuộc diện chính sách xin miễn, giảm học phí",
        "icon": "🎓",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf8-c7e3-746e-8437-305980ee5536",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Hai dòng cố định, mỗi dòng MỘT PDF gộp (planner lõi sourceFileIndexes): dòng giấy tờ chứng minh nhận cả
        # căn cước, giấy khai sinh, bằng tốt nghiệp (chạy thử 25/10).
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don_pl4", "name": "Đơn đề nghị chi trả tiền miễn, giảm học phí (Phụ lục IV Nghị định "
             "238/2025/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "xac_nhan_truong", "name": "Giấy xác nhận của trường (Phụ lục V hoặc mẫu của trường) hoặc giấy "
             "tờ chứng minh thuộc diện miễn, giảm (người có công, khuyết tật, hộ nghèo…)", "icon": "🏫",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của sinh viên; thêm CCCD cha/mẹ nếu nộp thay", "icon": "🪪",
             "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: giấy khai sinh, bằng tốt nghiệp, dự toán kinh phí cấp bù "
             "(Phụ lục VI)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (của HỌC SINH, SINH VIÊN được miễn, giảm học phí):\n"
            "1. Đơn đề nghị chi trả tiền miễn, giảm học phí (Phụ lục IV Nghị định 238/2025/NĐ-CP), đã ký — nguồn "
            "chính để điền form.\n"
            "2. Giấy xác nhận của trường (Phụ lục V hoặc mẫu của trường) hoặc giấy tờ chứng minh thuộc diện miễn, "
            "giảm (người có công, khuyết tật, hộ nghèo…).\n"
            "3. Căn cước công dân của sinh viên; nếu cha/mẹ nộp thay: thêm căn cước của người nộp.\n"
            "4. Nếu có: giấy khai sinh, bằng tốt nghiệp, dự toán kinh phí cấp bù (Phụ lục VI).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là sinh viên. Ô bắt buộc thiếu dữ liệu được tô đỏ để bổ sung tay.\n"
            "Bước Thành phần hồ sơ: dòng 1 gộp một PDF (giấy xác nhận của trường → giấy tờ chứng minh đối tượng → "
            "căn cước → giấy khai sinh → bằng tốt nghiệp); dòng 2 gộp một PDF (Đơn Phụ lục IV → dự toán Phụ lục VI)."
        ),
    },
    {
        "key": "cho-thue-thue-mua-nha-o-xa-hoi",
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
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Ở khối "Chọn cơ quan thực hiện" trên DVCQG, chọn Tỉnh rồi chuyển radio Phường/Xã sang Sở.
        # Kết quả có cả thẻ Sở Y tế và UBND xã; chốt thẻ Sở Y tế ở bước Nộp trực tuyến.
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
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyCardIncludes": "Cơ quan thực hiện: Sở Y tế",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng (stepper 4 bước, tờ khai Form.io, bước 3 receivingKind +
        # cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Dẫn đủ 4 bước bằng luồng chung chat/bxd như các thủ tục khác của cổng NN&MT; bản extension cũ chưa chạy
        # bộ đọc Form.io của chat/bxd trên host này → cần cờ supportsBxdFlowMae.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMae",
        },
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
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        "key": "cap-lai-giay-phep-hanh-nghe-truoc-2024",
        # Mã TTHC 1.012290, CÙNG cổng + CÙNG form (field-key trùng khít) với "cap-moi-giay-phep-hanh-nghe-chuyen-tiep":
        # nộp tại SỞ Y tế → agencyProvinceOnly + agencySoFirst, luồng chung "xay-dung" (ke_khai_links chưa có
        # selectSo, như bản cấp mới). Key TRÙNG lõi → process/attach tự nối. ke_khai_links ghi key khác
        # ("cap-lai-giay-phep-hanh-nghe-cap-truoc-2024") nên uuid + mã phải khai tay ở đây. Cụm đầu "cấp lại …
        # trước ngày 01 tháng 01 năm 2024" tách khỏi bản cấp mới / điều chỉnh (chung cụm thứ hai).
        "flowProfile": "xay-dung",
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.012290",
                "MaTTHC=1.012290",
                "019d2bff-1dcc-7496-8805-1623df922b71",
            ],
            "textIncludes": [
                "cấp lại giấy phép hành nghề đối với trường hợp được cấp trước ngày 01 tháng 01 năm 2024",
                "kiểm tra đánh giá năng lực hành nghề",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp lại giấy phép hành nghề đối với trường hợp được cấp trước ngày 01 tháng 01 năm 2024 "
                 "đối với hồ sơ nộp từ ngày 01 tháng 01 năm 2024 đến thời điểm kiểm tra đánh giá năng lực "
                 "hành nghề đối với các chức danh bác sỹ, y sỹ, điều dưỡng, hộ sinh, kỹ thuật y, dinh dưỡng "
                 "lâm sàng, cấp cứu viên ngoại viện, tâm lý lâm sàng",
        "shortLabel": "Cấp lại giấy phép hành nghề khám bệnh, chữa bệnh (cấp trước 01/01/2024)",
        "subtitle": "Cho bác sĩ, y sĩ, điều dưỡng… xin lại giấy phép hành nghề đã cấp trước 2024 (Sở Y tế)",
        "icon": "🩺",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-1dcc-7496-8805-1623df922b71",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ ~34 dòng cố định (planner lõi attp-row khớp dòng theo tên) → tắt hideRepeatableHint
        # mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don_de_nghi", "name": "Đơn đề nghị cấp lại giấy phép hành nghề (Mẫu 08 Phụ lục I Nghị định "
             "96/2023/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "giay_phep_cu", "name": "Chứng chỉ / giấy phép hành nghề đã được cấp", "icon": "🩺",
             "sides": 1, "repeatable": True},
            {"key": "anh_chan_dung", "name": "02 ảnh chân dung 4x6 nền trắng", "icon": "🖼️", "sides": 1,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người hành nghề, thêm CCCD người nộp nếu nộp thay",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: giấy khám sức khỏe, tài liệu chứng minh thông tin thay "
             "đổi, quyết định thu hồi giấy phép", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (đều là của NGƯỜI HÀNH NGHỀ đề nghị cấp lại):\n"
            "1. Đơn đề nghị cấp lại giấy phép hành nghề (Mẫu 08 Phụ lục I Nghị định 96/2023/NĐ-CP), đã ký — "
            "nguồn chính để điền form.\n"
            "2. Chứng chỉ / giấy phép hành nghề đã được cấp.\n"
            "3. 02 ảnh chân dung 4x6 nền trắng.\n"
            "4. Căn cước công dân (2 mặt) của người hành nghề; nếu người khác nộp thay: thêm căn cước của "
            "người nộp.\n"
            "5. Nếu có: giấy khám sức khỏe, tài liệu chứng minh thông tin thay đổi, quyết định thu hồi giấy phép.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là người hành nghề. Tự nộp thì giữ tích 'Người nộp là chủ hồ sơ'; nộp thay thì bỏ tích "
            "và điền riêng hai phần.\n"
            "Bước Thành phần hồ sơ: mỗi giấy tờ vào đúng dòng (Đơn Mẫu 08, giấy phép đã cấp, ảnh chân dung…); "
            "căn cước và giấy tờ chưa nhận ra được đính chung dòng Đơn."
        ),
    },
    {
        "key": "dieu-chinh-giay-phep-hoat-dong-kcb",
        # Mã TTHC 1.012280, CÙNG cổng + khung Form.io với "cap-moi-giay-phep-hoat-dong-kham-benh-chua-benh" ngay
        # trên: nộp tại SỞ Y tế → agencyProvinceOnly + agencySoFirst, luồng chung "xay-dung". Key TRÙNG lõi →
        # process/attach tự nối. ke_khai_links ghi key khác ("dieu-chinh-giay-phep-hoat-dong-kham-benh-chua-benh")
        # nên uuid + mã khai tay. Chủ hồ sơ là CƠ SỞ (mapper lõi chọn đối tượng tổ chức).
        "flowProfile": "xay-dung",
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.012280",
                "MaTTHC=1.012280",
                "019d2bff-1d9a-76c9-8537-4e29900dec8a",
            ],
            # KHÁC bản cấp mới ngay trên ("cấp mới giấy phép hoạt động …"): cụm "điều chỉnh" không có ở đó.
            "textIncludes": ["điều chỉnh giấy phép hoạt động khám bệnh, chữa bệnh"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Điều chỉnh giấy phép hoạt động khám bệnh, chữa bệnh",
        "shortLabel": "Điều chỉnh giấy phép hoạt động cơ sở khám bệnh, chữa bệnh",
        "subtitle": "Cho phòng khám, nha khoa đổi tên, quy mô, phạm vi hoạt động (Sở Y tế)",
        "icon": "🏥",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-1d9a-76c9-8537-4e29900dec8a",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ 5 dòng cố định (planner lõi attp-row) → tắt hideRepeatableHint mà profile
        # "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don_de_nghi", "name": "Đơn đề nghị điều chỉnh giấy phép hoạt động (Mẫu 02 Phụ lục II Nghị "
             "định 96/2023/NĐ-CP) — đã ký, đóng dấu", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "giay_phep_hoat_dong", "name": "Giấy phép hoạt động đã được cấp (kèm quyết định của Sở Y tế "
             "nếu có)", "icon": "🏥", "sides": 1, "repeatable": True},
            {"key": "quyet_dinh_to_chuc_lai", "name": "Quyết định tổ chức lại, đổi tên hoặc giấy tờ chứng minh "
             "việc thay đổi", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "ke_khai", "name": "Bản kê khai cơ sở vật chất, thiết bị, nhân sự (khi thay đổi quy mô, phạm "
             "vi, danh mục kỹ thuật)", "icon": "📋", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người ký Đơn, thêm CCCD người nộp nếu nộp thay",
             "icon": "🪪", "sides": 2, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (của CƠ SỞ khám bệnh, chữa bệnh đề nghị điều chỉnh):\n"
            "1. Đơn đề nghị điều chỉnh giấy phép hoạt động (Mẫu 02 Phụ lục II Nghị định 96/2023/NĐ-CP), đã ký, "
            "đóng dấu — nguồn chính để điền form.\n"
            "2. Giấy phép hoạt động khám bệnh, chữa bệnh đã được cấp (và quyết định của Sở Y tế kèm theo nếu có).\n"
            "3. Quyết định tổ chức lại / đổi tên hoặc giấy tờ chứng minh việc thay đổi.\n"
            "4. Nếu thay đổi quy mô, phạm vi, danh mục kỹ thuật: bản kê khai cơ sở vật chất, thiết bị, nhân sự.\n"
            "5. Căn cước công dân của người ký Đơn; nếu người khác nộp thay: thêm căn cước của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là cơ sở khám bệnh, chữa bệnh (người đại diện ký Đơn).\n"
            "Bước Thành phần hồ sơ: Đơn → dòng Đơn Mẫu 02; giấy phép + quyết định của Sở → dòng 'Bản gốc giấy "
            "phép hoạt động'; bản kê khai → dòng 'Bản kê khai cơ sở vật chất'; quyết định tổ chức lại, căn cước "
            "và giấy tờ khác → dòng 'điểm b khoản 3 Điều 54'."
        ),
    },
    {
        "key": "cap-chung-chi-hanh-nghe-duoc",
        # Mã TTHC 1.014092, cổng Bộ Y tế (Form.io, field-key trùng khít các thủ tục BYT): nộp tại SỞ Y tế
        # (ke_khai_links đặt selectSo) → agencyProvinceOnly + agencySoFirst, luồng chung "xay-dung". Key TRÙNG lõi
        # và ke_khai_links → process/attach + URL tự nối.
        "flowProfile": "xay-dung",
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.014092",
                "MaTTHC=1.014092",
                "019d2bff-3538-71fe-8b3b-2fe11f5d68a0",
            ],
            # Hai cụm đi cùng nhau (AND) như lõi: trang cấp lại / điều chỉnh GCN kinh doanh dược cũng có chữ
            # "chứng chỉ hành nghề dược" (dòng giấy tờ) nhưng không có "điều 28 của luật dược".
            "textIncludes": ["cấp chứng chỉ hành nghề dược", "điều 28 của luật dược"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp Chứng chỉ hành nghề dược (bao gồm cả trường hợp cấp Chứng chỉ hành nghề dược cho "
                 "người bị thu hồi Chứng chỉ hành nghề dược theo quy định tại các khoản 1, 2, 4, 5, 6, 7, "
                 "8, 9, 10, 11 Điều 28 của Luật Dược) theo hình thức xét hồ sơ",
        "shortLabel": "Cấp chứng chỉ hành nghề dược",
        "subtitle": "Cho dược sĩ xin chứng chỉ hành nghề dược theo hình thức xét hồ sơ (Sở Y tế)",
        "icon": "💊",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-3538-71fe-8b3b-2fe11f5d68a0",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ 8 dòng cố định (planner lõi attp-row; ảnh chân dung, căn cước đính chung dòng
        # Đơn) → tắt hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don_de_nghi", "name": "Đơn đề nghị cấp chứng chỉ hành nghề dược (Mẫu số 02) kèm ảnh chân "
             "dung 4x6 chụp trong 6 tháng — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "van_bang", "name": "Văn bằng chuyên môn (bằng tốt nghiệp dược)", "icon": "🎓", "sides": 1,
             "repeatable": True},
            {"key": "ly_lich_tu_phap", "name": "Phiếu lý lịch tư pháp", "icon": "📝", "sides": 1,
             "repeatable": True},
            {"key": "suc_khoe", "name": "Giấy chứng nhận đủ sức khỏe để hành nghề dược", "icon": "🏥",
             "sides": 1, "repeatable": True},
            {"key": "thoi_gian_thuc_hanh", "name": "Giấy xác nhận thời gian thực hành (Mẫu số 03)", "icon": "📋",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị, thêm CCCD người nộp nếu nộp thay",
             "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: giấy xác nhận cập nhật kiến thức dược (Mẫu số 08, khi "
             "bị thu hồi chứng chỉ), giấy công nhận tương đương văn bằng nước ngoài", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (đều là của NGƯỜI ĐỀ NGHỊ cấp chứng chỉ hành nghề dược):\n"
            "1. Đơn đề nghị cấp chứng chỉ hành nghề dược (Mẫu số 02), đã ký, kèm ảnh chân dung 4x6 chụp trong 6 "
            "tháng — nguồn chính để điền form.\n"
            "2. Căn cước công dân (2 mặt) của người đề nghị.\n"
            "3. Văn bằng chuyên môn (bằng tốt nghiệp dược).\n"
            "4. Phiếu lý lịch tư pháp.\n"
            "5. Giấy chứng nhận đủ sức khỏe để hành nghề dược.\n"
            "6. Giấy xác nhận thời gian thực hành (Mẫu số 03). Nếu bị THU HỒI chứng chỉ thì thay bằng giấy xác "
            "nhận hoàn thành đào tạo, cập nhật kiến thức chuyên môn về dược (Mẫu số 08).\n"
            "7. Nếu người khác nộp thay: thêm căn cước của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là người đề nghị. Tự nộp thì giữ tích 'Người nộp là chủ hồ sơ'; nộp thay thì bỏ tích và "
            "điền riêng hai phần.\n"
            "Bước Thành phần hồ sơ: mỗi giấy tờ vào đúng dòng (bản Scan tệp tin); ảnh chân dung và căn cước "
            "(không có dòng riêng) đính cùng dòng Đơn."
        ),
    },
    {
        "key": "cong-bo-co-so-du-dieu-kien-tiem-chung",
        # Mã TTHC 2.000655, hệ thống TTHC Bộ Y tế (Form.io dom-* + attach attp-row 1 dòng Văn bản thông báo): nộp
        # tại SỞ Y tế (ke_khai_links đặt selectSo) → agencyProvinceOnly + agencySoFirst, luồng chung "xay-dung".
        # Key TRÙNG lõi và ke_khai_links → process/attach + URL tự nối. Chủ hồ sơ là CƠ SỞ tiêm chủng (người đứng
        # đầu ký Thông báo); mapper lõi bỏ tích "Người nộp là chủ hồ sơ".
        "flowProfile": "xay-dung",
        # Cổng Bộ Y tế cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=2.000655",
                "MaTTHC=2.000655",
                "019d2bff-44df-7439-be21-a60e2bb7c9b8",
            ],
            "textIncludes": ["công bố cơ sở đủ điều kiện tiêm chủng"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Công bố cơ sở đủ điều kiện tiêm chủng",
        "shortLabel": "Công bố cơ sở đủ điều kiện tiêm chủng",
        "subtitle": "Cho phòng khám, cơ sở y tế công bố đủ điều kiện tiêm chủng (Sở Y tế)",
        "icon": "💉",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bff-44df-7439-be21-a60e2bb7c9b8",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Y tế",
        # Bảng thành phần hồ sơ 1 dòng cố định (Thông báo, gom cả Tờ trình + Danh sách) → tắt hideRepeatableHint
        # mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "thong_bao", "name": "Văn bản thông báo cơ sở đủ điều kiện tiêm chủng (mẫu Phụ lục Nghị định "
             "104/2016/NĐ-CP) kèm tờ trình, danh sách cơ sở — đã ký, đóng dấu", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nộp và của người đứng đầu cơ sở (chỉ để điền)",
             "icon": "🪪", "sides": 2, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Văn bản thông báo cơ sở đủ điều kiện tiêm chủng (mẫu Phụ lục Nghị định 104/2016/NĐ-CP), đã ký, "
            "đóng dấu — nguồn chính để điền form. Có thể tải cả file gộp Tờ trình + Danh sách cơ sở + Thông báo.\n"
            "2. Căn cước công dân của người nộp (tài khoản đang đăng nhập) — để bổ sung ngày sinh, giới tính, "
            "ngày cấp ở mục người nộp.\n"
            "3. Căn cước công dân của người đứng đầu cơ sở ghi trên Thông báo (bỏ qua nếu trùng người nộp).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là cơ sở tiêm chủng: trợ lý bỏ tích 'Người nộp là chủ hồ sơ' và điền chủ hồ sơ theo "
            "Thông báo (người đứng đầu, địa chỉ, điện thoại, email của cơ sở).\n"
            "Bước Thành phần hồ sơ: Thông báo (kèm Tờ trình, Danh sách) → dòng 'Văn bản thông báo đủ điều kiện "
            "tiêm chủng'; căn cước chỉ dùng ở bước thông tin."
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
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Planner lõi có nhánh tách theo trang (splitDocuments) → ô Đơn / ô CCCD chỉ nhận đúng trang của mình.
        "supportsSplitDocuments": True,
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
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Planner lõi có nhánh tách theo trang (splitDocuments) → PDF gộp thành từng tệp riêng mỗi giấy.
        "supportsSplitDocuments": True,
    },
    {
        "key": "cap-lai-to-quoc-ghi-cong",
        # Cổng Bộ Nội vụ, CÙNG cách chọn cơ quan CẤP XÃ với "tro-cap-tho-cung-liet-si" ngay trên
        # (ke_khai_links không có selectSo; đơn nộp qua UBND cấp xã rồi xã gửi công văn lên Sở).
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            # Chưa có snapshot trang kê khai nên chưa biết id SPA (apply-online/<id>, process=<id>)
            # → trang kê khai nhận bằng cụm tên. Hai cụm đi cùng nhau (AND): "tổ quốc ghi công" một
            # mình còn có trên trang thờ cúng liệt sĩ / di chuyển hồ sơ (mục giấy tờ Bằng TQGC).
            "urlIncludes": [
                "MaTTHC=1.010778",
                "019d2bfa-fbf8-727d-a4be-847d1f9944ce",
            ],
            "textIncludes": ["cấp lại bằng", "tổ quốc ghi công"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": 'Cấp lại Bằng "Tổ quốc ghi công"',
        "shortLabel": 'Cấp lại Bằng "Tổ quốc ghi công" cho gia đình liệt sĩ',
        "subtitle": "Xin lại Bằng Tổ quốc ghi công bị mất, hư hỏng",
        "icon": "🎖️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-fbf8-727d-a4be-847d1f9944ce",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" có HAI ô cố định (planner core trả fixed-slot 0/1) theo đúng thứ tự
        # dưới đây, phần còn lại đi "Thêm giấy tờ" → KHÔNG hideRepeatableHint.
        "requiredDocs": [
            {"key": "don_de_nghi_mau16", "name": "Đơn đề nghị cấp lại Bằng \"Tổ quốc ghi công\" "
             "(Mẫu số 16, Nghị định 131/2021/NĐ-CP) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "bang_tqgc_cu", "name": "Bằng \"Tổ quốc ghi công\" cũ (nếu còn, kể cả bản "
             "bị hư hỏng)", "icon": "🎖️", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "cong_van_ubnd", "name": "Công văn đề nghị của UBND cấp xã, danh sách đề nghị "
             "cấp lại (nếu đã có)", "icon": "🏛️", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp đổi/cấp lại Bằng \"Tổ quốc ghi công\" (Mẫu số 16, Phụ lục I Nghị định "
            "131/2021/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của người đề nghị — bổ sung số định danh, ngày/nơi cấp, nơi cư trú.\n"
            "3. Nếu có: Bằng \"Tổ quốc ghi công\" cũ, công văn của UBND cấp xã, danh sách đề nghị cấp lại.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "LƯU Ý: người đề nghị (còn sống, là chủ hồ sơ) và liệt sĩ là HAI người khác nhau — "
            "không lấy thông tin liệt sĩ trên đơn hay trên Bằng cũ điền cho người đề nghị.\n"
            "Bước Thành phần hồ sơ: Đơn Mẫu 16 vào ô 1, Bằng cũ vào ô 2; căn cước, công văn, danh "
            "sách xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong",
        # Cổng Bộ Nội vụ, chọn cơ quan CẤP XÃ như "tro-cap-tho-cung-liet-si": registry lõi ghi cổng chạy
        # "Quy trình liên thông Xã - Sở Nội vụ" (xã nhận hồ sơ rồi chuyển Sở).
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            # Trang kê khai không còn mã thủ tục trên URL → nhận bằng cụm tên (không đụng thủ tục nào khác;
            # cấp lại Bằng TQGC dùng "cấp lại bằng", không có "giấy chứng nhận người có công").
            "urlIncludes": [
                "MaTTHC=1.010814",
                "019d2bfa-fc21-710a-9e17-59cdb35c723b",
            ],
            "textIncludes": ["cấp bổ sung hoặc cấp lại giấy chứng nhận người có công"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Cấp bổ sung hoặc cấp lại giấy chứng nhận người có công do ngành Lao động - Thương binh và Xã hội "
            "quản lý và giấy chứng nhận thân nhân liệt sĩ"
        ),
        "shortLabel": "Cấp bổ sung, cấp lại giấy chứng nhận người có công, thân nhân liệt sĩ",
        "subtitle": "Xin lại giấy chứng nhận bị mất, hư hỏng hoặc cần bổ sung thông tin",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-fc21-710a-9e17-59cdb35c723b",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" có MỘT ô cố định (planner core trả fixed-slot 0: Đơn Mẫu 25), phần còn lại
        # đi "Thêm giấy tờ" → KHÔNG hideRepeatableHint.
        "requiredDocs": [
            {"key": "don_de_nghi_mau25", "name": "Đơn đề nghị cấp bổ sung hoặc cấp lại giấy chứng nhận "
             "(Mẫu số 25, Nghị định 131/2021/NĐ-CP) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người làm đơn", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "giay_chung_nhan_cu", "name": "Giấy chứng nhận đã cấp (bản bị hư hỏng hoặc cần bổ "
             "sung thông tin, nếu còn)", "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp bổ sung hoặc cấp lại giấy chứng nhận (Mẫu số 25, Phụ lục I Nghị định "
            "131/2021/NĐ-CP), đã ký — nguồn chính: diện người có công, quyết định hưởng trợ cấp, loại giấy "
            "chứng nhận, lý do.\n"
            "2. Căn cước công dân của người làm đơn — bổ sung số định danh, ngày/nơi cấp, nơi thường trú.\n"
            "3. Nếu có: giấy chứng nhận đã cấp (bản bị hư hỏng hoặc cần bổ sung thông tin).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước Thành phần hồ sơ: Đơn Mẫu 25 vào ô 1; giấy chứng nhận cũ, căn cước và giấy tờ khác xếp "
            "vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "bo-sung-than-nhan-liet-si",
        # Cổng Bộ Nội vụ, chọn cơ quan CẤP XÃ như "tro-cap-tho-cung-liet-si": hồ sơ kèm công văn đề nghị
        # của UBND cấp xã (xã nhận đơn rồi chuyển Sở).
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.010825",
                "maThuTuc=1.010825",
                "019d2bfa-fc36-74e9-9909-551c04aa6c27",
            ],
            # Cùng đơn Mẫu 26/06 với "sua-doi-thong-tin-ho-so-nguoi-co-cong" nhưng tên thủ tục khác hẳn
            # ("tình hình thân nhân" + "hồ sơ liệt sĩ") → cụm tên đủ tách.
            "textIncludes": ["bổ sung tình hình thân nhân trong hồ sơ liệt sĩ"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ",
        "shortLabel": "Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ",
        "subtitle": "Thêm, sửa thông tin thân nhân trong hồ sơ liệt sĩ",
        "icon": "🕯️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-fc36-74e9-9909-551c04aa6c27",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" có HAI ô cố định (planner core trả fixed-slot 0/1) theo đúng thứ tự dưới
        # đây, phần còn lại đi "Thêm giấy tờ" → KHÔNG hideRepeatableHint.
        "requiredDocs": [
            {"key": "giay_to_chung_minh_quan_he", "name": "Bản sao chứng thực giấy tờ chứng minh quan hệ "
             "với liệt sĩ (căn cước, giấy khai sinh, trích lục khai sinh, đăng ký kết hôn, lý lịch)",
             "icon": "👪", "sides": 1, "repeatable": True},
            {"key": "don_sua_doi_bo_sung", "name": "Đơn đề nghị sửa đổi, bổ sung thông tin trong hồ sơ "
             "liệt sĩ (Mẫu số 26, Nghị định 131/2021/NĐ-CP) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người khai", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: hồ sơ liệt sĩ, Bằng Tổ quốc ghi công, công văn "
             "của UBND cấp xã", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị sửa đổi, bổ sung thông tin trong hồ sơ liệt sĩ (Mẫu số 26/06, Phụ lục I Nghị "
            "định 131/2021/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của người khai — bổ sung số định danh, ngày/nơi cấp, nơi cư trú.\n"
            "3. Bản sao chứng thực giấy tờ chứng minh quan hệ với liệt sĩ của các thân nhân (căn cước, giấy "
            "khai sinh, trích lục khai sinh, đăng ký kết hôn, lý lịch).\n"
            "4. Nếu có: hồ sơ liệt sĩ, Bằng \"Tổ quốc ghi công\", công văn của UBND cấp xã.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "LƯU Ý: người khai (thân nhân còn sống) và liệt sĩ là HAI người khác nhau.\n"
            "Bước Thành phần hồ sơ: giấy tờ chứng minh quan hệ vào ô 1, Đơn Mẫu 26 vào ô 2; hồ sơ liệt "
            "sĩ, Bằng TQGC, công văn xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "tham-vieng-mo-liet-si",
        # Cổng Bộ Nội vụ, chọn cơ quan CẤP XÃ như "tro-cap-tho-cung-liet-si": thân nhân đề nghị UBND cấp xã
        # nơi cư trú cấp giấy giới thiệu đi thăm viếng.
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.013750",
                "019d2bfb-2324-7555-8e56-024dcdb30038",
            ],
            "textIncludes": ["thăm viếng mộ liệt sĩ"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thăm viếng mộ liệt sĩ",
        "shortLabel": "Thăm viếng mộ liệt sĩ (giấy giới thiệu, hỗ trợ chi phí)",
        "subtitle": "Xin giấy giới thiệu, hỗ trợ đi thăm viếng mộ liệt sĩ",
        "icon": "🕯️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-2324-7555-8e56-024dcdb30038",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" có BA ô cố định (planner core trả fixed-slot 0/1/2) theo đúng thứ tự dưới
        # đây, phần còn lại đi "Thêm giấy tờ" → KHÔNG hideRepeatableHint.
        "requiredDocs": [
            {"key": "ho_so_liet_si", "name": "Giấy báo tin mộ liệt sĩ, giấy xác nhận nơi liệt sĩ hy sinh "
             "(Mẫu 44) hoặc trích lục hồ sơ liệt sĩ", "icon": "🕯️", "sides": 1, "repeatable": True},
            {"key": "giay_chung_nhan_than_nhan", "name": "Giấy chứng nhận gia đình/thân nhân liệt sĩ hoặc "
             "quyết định trợ cấp thờ cúng liệt sĩ", "icon": "👪", "sides": 1, "repeatable": True},
            {"key": "don_gioi_thieu", "name": "Đơn đề nghị thăm viếng mộ liệt sĩ (Mẫu số 31, Nghị định "
             "131/2021/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: Bằng Tổ quốc ghi công", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị / giấy giới thiệu thăm viếng mộ liệt sĩ (Mẫu số 31/42, Phụ lục I Nghị định "
            "131/2021/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của người đề nghị — bổ sung số định danh, ngày/nơi cấp, nơi cư trú.\n"
            "3. Giấy báo tin mộ liệt sĩ, giấy xác nhận nơi hy sinh (Mẫu 44) hoặc trích lục hồ sơ liệt sĩ.\n"
            "4. Giấy chứng nhận gia đình/thân nhân liệt sĩ hoặc quyết định trợ cấp thờ cúng.\n"
            "5. Nếu có: Bằng \"Tổ quốc ghi công\".\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "LƯU Ý: người đề nghị (thân nhân còn sống) và liệt sĩ là HAI người khác nhau.\n"
            "Bước Thành phần hồ sơ: hồ sơ/trích lục liệt sĩ vào ô 1, giấy chứng nhận thân nhân vào ô 2, "
            "Đơn vào ô 3; căn cước, Bằng TQGC xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "giai-quyet-che-do-khang-chien",
        # Cổng Bộ Nội vụ, chọn cơ quan CẤP XÃ như "tro-cap-tho-cung-liet-si": Bản khai Mẫu 11 nộp ở UBND cấp
        # xã nơi thường trú (xã xác nhận rồi chuyển Sở).
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            # id SPA lấy từ registry lõi (cổng thật).
            "urlIncludes": [
                "MaTTHC=1.010819",
                "019d2bfa-fc33-7068-b98d-1b1eba21519f",
                "apply-online/6960726b36973e2430327813",
                "process=69706a4ce528a8797931839f",
            ],
            # Hai cụm đi cùng nhau (AND). Mai táng dân công hỏa tuyến cũng có "kháng chiến … nhiệm vụ quốc
            # tế" nhưng ghi "chống Pháp, chống Mỹ" và "nhiệm vụ", không có hai cụm này.
            "textIncludes": ["hoạt động kháng chiến giải phóng dân tộc", "làm nghĩa vụ quốc tế"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Giải quyết chế độ người hoạt động kháng chiến giải phóng dân tộc, bảo vệ Tổ quốc "
            "và làm nghĩa vụ quốc tế"
        ),
        "shortLabel": "Giải quyết chế độ người hoạt động kháng chiến, bảo vệ Tổ quốc",
        "subtitle": "Hưởng chế độ cho người tham gia kháng chiến",
        "icon": "🎖️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-fc33-7068-b98d-1b1eba21519f",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" có BA ô cố định (planner core trả fixed-slot 0/1/2) và KHÔNG có nút "Thêm
        # giấy tờ": căn cước, sổ BHXH chỉ là nguồn đọc để điền, planner không đính lên cổng.
        "requiredDocs": [
            {"key": "ban_khai", "name": "Bản khai cá nhân (Mẫu số 11, Nghị định 131/2021/NĐ-CP, có xác "
             "nhận UBND cấp xã) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "giay_bao_tu", "name": "Giấy báo tử hoặc trích lục khai tử (khi người hoạt động kháng "
             "chiến đã mất)", "icon": "🕯️", "sides": 1, "optional": True, "repeatable": True},
            {"key": "huy_chuong", "name": "Bản sao chứng thực Huân chương, Huy chương Kháng chiến, Chiến "
             "thắng hoặc quyết định tặng thưởng", "icon": "🎖️", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người hoạt động kháng chiến", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: sổ bảo hiểm xã hội", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản khai cá nhân theo Mẫu số 11 (Phụ lục I Nghị định 131/2021/NĐ-CP, có xác nhận UBND cấp "
            "xã), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của người hoạt động kháng chiến.\n"
            "3. Giấy chứng nhận Huân/Huy chương Kháng chiến, Chiến thắng (hoặc quyết định tặng thưởng).\n"
            "4. Nếu có: giấy báo tử/trích lục khai tử (người hoạt động kháng chiến đã mất), sổ bảo hiểm "
            "xã hội.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Người hoạt động kháng chiến còn sống là chủ hồ sơ; đã mất thì thân nhân đứng đại diện.\n"
            "Bước Thành phần hồ sơ: Bản khai Mẫu 11 vào ô 1, giấy báo tử vào ô 2 (nếu có), Huân/Huy "
            "chương vào ô 3. Cổng không có mục 'Thêm giấy tờ' nên căn cước, sổ BHXH chỉ dùng để điền."
        ),
    },
    {
        "key": "sua-doi-thong-tin-ho-so-nguoi-co-cong",
        # Cổng Bộ Nội vụ, chọn cơ quan CẤP SỞ như "di-chuyen-ho-so-nguoi-huong-tro-cap": đơn Mẫu 26 gửi Sở nơi
        # quản lý hồ sơ gốc người có công (Điều 174 NĐ 131/2021) → agencyProvinceOnly + agencySoFirst.
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.010826",
                "019d2bfb-03d5-777b-bdc9-f3ccadbd96f8",
            ],
            # Cùng đơn Mẫu 26 với "bo-sung-than-nhan-liet-si"; thủ tục đó không có hai cụm này.
            "textIncludes": ["bổ sung thông tin cá nhân", "hồ sơ người có công"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Sửa đổi, bổ sung thông tin cá nhân trong hồ sơ người có công",
        "shortLabel": "Sửa đổi, bổ sung thông tin cá nhân trong hồ sơ người có công",
        "subtitle": "Sửa họ tên, ngày sinh, quê quán… trong hồ sơ người có công",
        "icon": "✏️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-03d5-777b-bdc9-f3ccadbd96f8",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nội vụ",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" có HAI ô cố định (planner core trả fixed-slot 0/1) và KHÔNG có nút "Thêm
        # giấy tờ": giấy tờ khác chỉ là nguồn đọc để điền, planner bỏ qua khi đính.
        "requiredDocs": [
            {"key": "cccd", "name": "Bản sao chứng thực căn cước công dân của người có công hoặc thân nhân",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "don_mau_26", "name": "Đơn đề nghị sửa đổi, bổ sung thông tin cá nhân (Mẫu số 26, Nghị "
             "định 131/2021/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: bản khai thân nhân, giấy khai sinh, trích lục "
             "khai tử, Bằng Tổ quốc ghi công", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị sửa đổi, bổ sung thông tin cá nhân theo Mẫu số 26 (Phụ lục I Nghị định "
            "131/2021/NĐ-CP), đã ký — nguồn chính về nội dung sửa đổi.\n"
            "2. Căn cước công dân của người khai đơn — nguồn nhân thân người nộp.\n"
            "3. Nếu có: bản khai thân nhân, giấy khai sinh, trích lục khai tử, Bằng \"Tổ quốc ghi công\" "
            "để bổ sung nội dung đơn.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Người khai đơn là người nộp và là chủ hồ sơ; người có công chỉ xuất hiện trong nội dung đề nghị "
            "sửa.\n"
            "Bước Thành phần hồ sơ: căn cước vào ô 1, Đơn Mẫu 26 vào ô 2. Cổng không có mục 'Thêm giấy tờ' "
            "nên giấy tờ khác chỉ dùng để điền."
        ),
    },
    {
        "key": "mai-tang-dan-cong-hoa-tuyen",
        # Cổng Bộ Nội vụ, chọn cơ quan CẤP XÃ như "tro-cap-tho-cung-liet-si": thân nhân lập bản khai Mẫu
        # 02-MTP có xác nhận UBND cấp xã (QĐ 49/2015/QĐ-TTg). ke_khai_links ghi key khác
        # ("giai-quyet-che-do-mai-tang-dan-cong-hoa-tuyen", mã 1.014359) nên uuid + mã phải khai tay ở đây.
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=1.014359",
                "019d2bfb-2b25-777d-a825-2823012ce7ec",
            ],
            # Hai cụm đi cùng nhau (AND): "mai táng phí" một mình còn có ở các thủ tục mai táng khác.
            "textIncludes": ["mai táng phí", "dân công hỏa tuyến"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Giải quyết chế độ mai táng phí đối với dân công hỏa tuyến tham gia kháng chiến chống Pháp, "
            "chống Mỹ, chiến tranh bảo vệ Tổ quốc và làm nhiệm vụ quốc tế"
        ),
        "shortLabel": "Mai táng phí cho dân công hỏa tuyến tham gia kháng chiến",
        "subtitle": "Thân nhân nhận tiền mai táng khi dân công hỏa tuyến qua đời",
        "icon": "🕯️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-2b25-777d-a825-2823012ce7ec",
        "needsAgencySelect": True,
        "maePortal": True,
        "maeAgencyLevel": "ward",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        # Bước "Thành phần hồ sơ" chỉ có HAI ô cố định, KHÔNG có nút "Thêm giấy tờ": planner core dồn mọi tệp
        # vào ô 1 (ô nhận nhiều tệp), riêng trích lục khai tử vào ô 2.
        "requiredDocs": [
            {"key": "qd_tro_cap", "name": "Bản trích sao quyết định hưởng trợ cấp một lần của người đã "
             "mất", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "giay_chung_tu", "name": "Trích lục khai tử hoặc giấy chứng tử của người đã mất",
             "icon": "🕯️", "sides": 1, "repeatable": True},
            {"key": "ban_khai_02mtp", "name": "Bản khai của thân nhân đề nghị hưởng mai táng phí (Mẫu "
             "02-MTP, có xác nhận UBND cấp xã) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của thân nhân đứng khai", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ khác nếu có: biên bản họp đồng thuận của những người cùng hàng "
             "thừa kế (Mẫu 80A)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản khai của thân nhân đề nghị hưởng chế độ mai táng phí (Mẫu 02-MTP, có xác nhận UBND "
            "cấp xã) theo Quyết định số 49/2015/QĐ-TTg — nguồn chính để điền form.\n"
            "2. Bản trích sao quyết định hưởng chế độ trợ cấp một lần của người đã mất.\n"
            "3. Trích lục khai tử hoặc giấy chứng tử của người đã mất.\n"
            "4. Căn cước công dân của thân nhân đứng khai.\n"
            "5. Nếu có nhiều thân nhân: biên bản họp đồng thuận của những người cùng hàng thừa kế (Mẫu 80A).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "LƯU Ý: thân nhân đứng khai (còn sống, là chủ hồ sơ) và người đã mất là HAI người khác nhau.\n"
            "Bước Thành phần hồ sơ: trích lục khai tử vào ô 2; mọi giấy tờ còn lại gom vào ô 1."
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
        # Cổng Bộ Nội vụ cùng nền iGate với cổng Bộ Xây dựng (bước 3 tên "Thông tin bổ sung" nhưng vẫn là ô hình thức
        # nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Planner lõi có nhánh tách theo trang (splitDocuments) → PDF gộp thành từng tệp riêng mỗi giấy.
        "supportsSplitDocuments": True,
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
        # Cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Mã TTHC 1.116910, thay mã cũ 1.001731. CÙNG key với Auto Fill (5/11/2026 đã gỡ entry trùng "ho-tro-mai-tang"
        # và tiền tố "[Tỉnh Ninh Bình]" ở registry lõi); pipeline ho_tro_mai_tang: chủ hồ sơ = người chết. CÙNG cổng Bộ Y tế, cùng khung với "ho-tro-mai-tang-huu-tri-xa-hoi"; khác NHÓM ĐỐI TƯỢNG
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
        # Cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        "key": "tiep-nhan-doi-tuong-can-bao-ve-khan-cap-vao-co-so-tro-giup-xa-hoi",
        # Mã 1.116908 (NĐ 335/2026/NĐ-CP) — chép khuôn 1.116909 ngay trên: CÙNG cổng Bộ Y tế, cùng form
        # Form.io, cùng cách chọn cơ quan (Tỉnh + Xã), cùng wizard + luồng bxdFlow. Bảng thành phần hồ sơ 2
        # dòng (Tờ khai Mẫu số 04 / Biên bản tiếp nhận) → KHÔNG đặt hideRepeatableHint. URL SPA không mang mã
        # → nhận trang theo cụm "cần bảo vệ khẩn cấp", không có ở thủ tục anh em 1.116907 dù chung Mẫu số 04.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.116908",
                "01a0f65f-4713-7199-9b0c-d57f794ef14d",
            ],
            "textIncludes": ["Tiếp nhận đối tượng cần bảo vệ khẩn cấp"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã hội",
        "shortLabel": "Đưa đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã hội",
        "subtitle": "Chăm sóc, nuôi dưỡng khẩn cấp tại cơ sở trợ giúp xã hội theo NĐ 335/2026",
        "icon": "🛡️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/01a0f65f-4713-7199-9b0c-d57f794ef14d",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội "
             "(Mẫu số 04 theo NĐ 335/2026) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "bien_ban", "name": "Biên bản tiếp nhận có chữ ký người phát hiện, chính quyền hoặc "
             "công an xã, đại diện cơ sở trợ giúp xã hội", "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của đối tượng và của người giám hộ (để điền thông "
             "tin, không phải đính kèm)", "icon": "🪪", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội (Mẫu số 04 theo NĐ "
            "335/2026/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Biên bản tiếp nhận có chữ ký người phát hiện, chính quyền hoặc công an xã, đại diện cơ sở "
            "trợ giúp xã hội.\n"
            "3. Căn cước công dân của đối tượng và của người giám hộ (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là ĐỐI TƯỢNG cần bảo vệ khẩn cấp; người giám hộ điền vào phần người nộp. Đối tượng "
            "không có số điện thoại thì dùng số của người giám hộ.\n"
            "Bước Thành phần hồ sơ: Tờ khai Mẫu 04 vào dòng 1, Biên bản tiếp nhận vào dòng 2 (scan chung "
            "một tệp thì đính tệp đó ở cả hai dòng). Căn cước không đính kèm."
        ),
    },
    {
        "key": "tiep-nhan-doi-tuong-bao-tro-xa-hoi-co-hoan-canh-dac-biet-kho-khan-vao-co-so-tro-giup-xa-hoi",
        # Mã 1.116907 (NĐ 335/2026/NĐ-CP) — chép khuôn 1.116908 ngay trên: CÙNG cổng Bộ Y tế, form, Tờ khai Mẫu
        # số 04, cách chọn cơ quan (Tỉnh + Xã), wizard + bxdFlow. Bảng thành phần hồ sơ CHỈ một dòng (tờ khai);
        # tờ khai có thể chụp nhiều trang nên vẫn báo "không giới hạn số lượng" (không đặt hideRepeatableHint).
        # Nhận trang theo cụm "bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn", không có ở 1.116908 dù chung tờ khai.
        "detect": {
            "urlScope": ["dichvucongbyt.moh.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.116907",
                "01a0f653-8729-706c-9cc8-c3234469d7cf",
            ],
            "textIncludes": ["Tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn vào cơ sở trợ giúp xã hội",
        "shortLabel": "Đưa đối tượng bảo trợ xã hội khó khăn vào cơ sở trợ giúp xã hội",
        "subtitle": "Chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội theo NĐ 335/2026",
        "icon": "🏠",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/01a0f653-8729-706c-9cc8-c3234469d7cf",
        "needsAgencySelect": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Cùng nền iGate với cổng Bộ Xây dựng → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội "
             "(Mẫu số 04 theo NĐ 335/2026) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của đối tượng và của người giám hộ (để điền thông "
             "tin, không phải đính kèm)", "icon": "🪪", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội (Mẫu số 04 theo NĐ "
            "335/2026/NĐ-CP), đã ký — nguồn chính để điền form.\n"
            "2. Căn cước công dân của đối tượng và của người giám hộ (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ hồ sơ là ĐỐI TƯỢNG bảo trợ xã hội; người giám hộ điền vào phần người nộp. Đối tượng không "
            "có số điện thoại thì dùng số của người giám hộ.\n"
            "Bước Thành phần hồ sơ: chỉ một dòng Tờ khai Mẫu 04. Căn cước không đính kèm."
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
        # Dẫn đủ 4 bước của cổng Bộ Xây dựng (chat/bxd), chỉ bật cho extension khai supportsBxdFlow.
        # resultGroups: ô "Hình thức nhận kết quả" ở bước 3 (thẻ chọn dùng chung với cổng liên thông).
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
                 "pipelineOptions": {"constructionVariant": "cong_trinh"}},
            ],
        },
        # Trường hợp người dân chọn trên hộp thoại (nhãn đọc từ cổng) → tuỳ chọn pipeline.
        # Khớp theo cụm đã fold dấu, luật ĐẦU TIÊN khớp thắng; match rỗng = mặc định.
        "caseOptions": _GPXD_NEW_CASE_OPTIONS,
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
        # Dẫn đủ 4 bước của cổng Bộ Xây dựng (chat/bxd) như GPXD cấp mới — cùng stepper, cùng ô receivingKind.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Registry lõi tách 2 key theo quy trình (nhà ở riêng lẻ 15 ngày / công trình 10 ngày), CÙNG
        # process và attach, CÙNG trang DVCQG + hộp thoại "Chọn trường hợp giải quyết". Trợ lý cũng
        # tách 2 card: card nào thì hộp thoại chỉ giữ trường hợp của nhánh đó (maeDialogChoice
        # processMatch/processAvoid) và variants chỉ một lựa chọn → không hỏi lại. Lọc ra rỗng (cổng
        # đổi nhãn) thì vẫn hỏi; caseOptions theo nhãn đã chọn quyết định nhánh form như cũ.
        "key": "sua-chua-cai-tao-gpxd-nha-o-rieng-le",
        "code": "1.013229",  # ke_khai_links ghi mã này dưới key "...-cong-trinh"
        # Dẫn đủ 4 bước của cổng Bộ Xây dựng (chat/bxd) như GPXD cấp mới — cùng stepper, cùng ô receivingKind.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "flowProfile": "xay-dung",
        "maeDialogChoice": {"processMatch": "nha o rieng le"},
        "label": (
            "Cấp giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV và nhà "
            "ở riêng lẻ (nhà ở riêng lẻ)"
        ),
        "shortLabel": "Cấp phép sửa chữa, cải tạo nhà ở riêng lẻ",
        "subtitle": "Giấy phép sửa chữa, cải tạo nhà ở riêng lẻ của hộ gia đình, cá nhân",
        "icon": "🔨",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-909c-759d-9dc9-416500074f0f",
        "variants": {
            "options": [
                {"key": "nha_o_rieng_le", "label": "Nhà ở riêng lẻ",
                 "chip": "🏠 Nhà ở riêng lẻ", "portalMatch": "nha o rieng le",
                 "desc": "sửa chữa, cải tạo nhà ở của hộ gia đình, cá nhân",
                 "pipelineOptions": {"constructionVariant": "nha_o_rieng_le"}},
            ],
        },
        "caseOptions": _GPXD_NEW_CASE_OPTIONS,
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
        # Nhánh CÔNG TRÌNH của thủ tục ngay trên (mã QG 1.013229 ở ke_khai_links nằm dưới key này).
        # Key TRÙNG lõi → process run_cong_trinh (ô "Loại hình công trình" 4 lựa chọn theo đơn kê
        # khai) + attach sua_chua_gpxd tự nối. Hộp thoại chỉ giữ trường hợp KHÔNG phải nhà ở riêng lẻ.
        "key": "sua-chua-cai-tao-gpxd-cong-trinh",
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "flowProfile": "xay-dung",
        "maeDialogChoice": {"processAvoid": "nha o rieng le"},
        "label": (
            "Cấp giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV (công trình Không "
            "theo tuyến/Theo tuyến trong đô thị/Tín ngưỡng, tôn giáo/Tượng đài, tranh hoành tráng/Theo giai "
            "đoạn cho công trình không theo tuyến/Theo giai đoạn cho công trình theo tuyến trong đô thị/Dự án)"
        ),
        "shortLabel": "Cấp phép sửa chữa, cải tạo công trình",
        "subtitle": "Giấy phép sửa chữa, cải tạo công trình cấp III, cấp IV (không phải nhà ở riêng lẻ)",
        "icon": "🏢",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-909c-759d-9dc9-416500074f0f",
        "variants": {
            "options": [
                {"key": "cong_trinh", "label": "Công trình cấp III, cấp IV",
                 "chip": "🏢 Công trình cấp III, cấp IV",
                 "portalMatch": "cong trinh", "portalAvoid": "nha o rieng le",
                 "desc": "công trình cấp III, cấp IV, không phải nhà ở riêng lẻ",
                 "pipelineOptions": {"constructionVariant": "cong_trinh"}},
            ],
        },
        "caseOptions": _GPXD_NEW_CASE_OPTIONS,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp giấy phép xây dựng (Mẫu số 01) — đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất (sổ đỏ) hoặc giấy tờ về "
             "quyền sử dụng đất", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "ban_ve", "name": "Bản vẽ hiện trạng và bản vẽ thiết kế sửa chữa, cải tạo",
             "icon": "📐", "sides": 1, "repeatable": True},
            {"key": "anh", "name": "Ảnh chụp hiện trạng công trình và công trình lân cận",
             "icon": "📷", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân / Giấy chứng nhận đăng ký doanh nghiệp của chủ "
             "đầu tư", "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy ủy quyền, căn cước người được ủy quyền hoặc giấy tờ khác (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp giấy phép xây dựng (Mẫu số 01), đã ký — thông tin chủ đầu tư, địa điểm, "
            "loại hình và thông số công trình sửa chữa, cải tạo.\n"
            "2. Giấy chứng nhận quyền sử dụng đất hoặc giấy tờ hợp pháp về đất đai.\n"
            "3. Bản vẽ hiện trạng bộ phận công trình sửa chữa, cải tạo và bộ bản vẽ thiết kế.\n"
            "4. Ảnh chụp hiện trạng công trình và công trình lân cận.\n"
            "5. Căn cước công dân hoặc Giấy chứng nhận đăng ký doanh nghiệp của chủ đầu tư; nếu ủy quyền: "
            "giấy ủy quyền + căn cước người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cung-cap-thong-tin-quy-hoach",
        "flowProfile": "xay-dung",
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        # Mã TTHC 1.002693, cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io dom-* + attach attp-row 2 dòng: Đơn
        # Mẫu 01 / Ảnh hiện trạng cây). Key TRÙNG lõi → process/attach tự nối. Bảng kê cây là datagrid
        # data[panel][tbantest][i][...], fill-core.js đã có nhánh datagrid (bấm "Thêm dòng").
        # ke_khai_links khai selectSoProvinces ["danang"] (tỉnh khác chọn cấp xã) + autoConfirm false.
        # Registry trợ lý chưa có cờ chọn Sở theo tỉnh → chỉ mở cho Đà Nẵng, chọn Sở như NOXH Bộ Xây dựng.
        "flowProfile": "xay-dung",
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
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
        "key": "chap-thuan-dau-noi-tam",
        # Mã TTHC 1.000314, cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io dom-* + attach attp-row 3 dòng). Key TRÙNG
        # lõi → process/attach tự nối. ke_khai_links không khai selectSo/provinceOnlyAgency → DVCQG chọn đủ
        # Tỉnh + Phường/Xã như "cap-phep-long-duong-via-he"; hộp thoại "Chọn trường hợp giải quyết" của cổng vẫn
        # đọc lựa chọn thật (maeDialogChoice) rồi hỏi người dân.
        "flowProfile": "xay-dung",
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moc.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.000314",
                "019d2bfe-0b6a-755c-859a-4ec09fbd16c7",
            ],
            "textIncludes": ["chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác",
        "shortLabel": "Chấp thuận vị trí đấu nối tạm vào đường bộ",
        "subtitle": "Xin mở lối ra vào tạm từ công trường, dự án vào đường đang khai thác",
        "icon": "🛣️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-0b6a-755c-859a-4ec09fbd16c7",
        # Bảng thành phần hồ sơ 3 dòng cố định (planner core attp-row: HĐ thi công / chủ trương → dòng 1, Đơn →
        # dòng 2, bản vẽ → dòng 3) → tắt hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "hd_chu_truong", "name": "Hợp đồng thi công xây dựng hoặc văn bản chấp thuận chủ trương "
             "đầu tư (kèm công văn, hồ sơ pháp lý dự án)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "don_de_nghi", "name": "Văn bản đề nghị chấp thuận vị trí đấu nối tạm — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "ho_so_ban_ve", "name": "Hồ sơ thiết kế bản vẽ thi công nút giao đấu nối tạm, phương án tổ "
             "chức giao thông", "icon": "🗺️", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nộp (chỉ để điền, không đính kèm)",
             "icon": "🪪", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Văn bản đề nghị chấp thuận vị trí đấu nối tạm, đã ký — nguồn chính để điền form.\n"
            "2. Hợp đồng thi công xây dựng hoặc văn bản chấp thuận chủ trương đầu tư (kèm công văn, nghị "
            "quyết, hồ sơ pháp lý dự án).\n"
            "3. Hồ sơ thiết kế bản vẽ thi công nút giao đấu nối tạm, phương án tổ chức giao thông.\n"
            "4. Căn cước công dân của người nộp — chỉ để điền thông tin, không đính kèm.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Trợ lý điền Phần I (người nộp) và Phần II (đơn vị đề nghị, vị trí đấu nối, trường hợp, cam kết, "
            "người ký).\n"
            "Bước đính kèm: hợp đồng / chủ trương → dòng 1; Văn bản đề nghị → dòng 2; bản vẽ → dòng 3."
        ),
    },
    {
        "key": "gia-han-luu-hanh-phuong-tien-lao",
        # Mã TTHC 1.002063, cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io key PHẲNG + attach attp-row 2 dòng, engine tách
        # trang sourceSegments). Key TRÙNG lõi → process/attach tự nối. ke_khai_links ghi key khác
        # ("gia-han-luu-hanh-phuong-tien-lao-tai-viet-nam") nên uuid + mã phải khai tay ở đây; ke_khai khai
        # selectSo → agencyProvinceOnly + agencySoFirst như liên vận Việt – Lào.
        "flowProfile": "xay-dung",
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moc.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.002063",
                "019d2bfe-134f-7491-9d27-d7049d4567a6",
            ],
            # KHÁC "cap-giay-phep-lien-van-viet-lao" (cấp giấy phép): ở đây xe Lào đã vào Việt Nam, xin ở thêm.
            "textIncludes": ["gia hạn thời gian lưu hành tại việt nam cho phương tiện của lào"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Gia hạn thời gian lưu hành tại Việt Nam cho phương tiện của Lào",
        "shortLabel": "Gia hạn thời gian lưu hành tại Việt Nam cho xe Lào",
        "subtitle": "Xin ở lại thêm cho xe Lào đang lưu hành tại Việt Nam",
        "icon": "🚚",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-134f-7491-9d27-d7049d4567a6",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        # Bảng thành phần hồ sơ 2 dòng cố định (Giấy đề nghị / Giấy phép liên vận); giấy tờ khác planner đính
        # chung dòng 1 → tắt hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "giay_de_nghi", "name": "Giấy đề nghị gia hạn thời gian lưu hành tại Việt Nam (Mẫu số 07) "
             "— đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "giay_phep_lien_van", "name": "Giấy phép liên vận Việt Nam – Lào (bìa, trang thông tin xe, "
             "các trang có dấu nhập cảnh)", "icon": "🚚", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người xin gia hạn", "icon": "🪪",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ chứng minh lý do gia hạn, ví dụ báo giá sửa chữa xe (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (một file có thể gộp nhiều giấy — hệ thống tự tách theo trang):\n"
            "1. Giấy đề nghị gia hạn thời gian lưu hành của phương tiện tại Việt Nam (Mẫu số 07), đã ký — "
            "nguồn chính để điền form.\n"
            "2. Giấy phép liên vận Việt Nam – Lào (bìa, trang thông tin xe, các trang có dấu nhập cảnh).\n"
            "3. Căn cước công dân của người xin gia hạn — để điền ngày sinh, số căn cước, ngày cấp.\n"
            "4. Nếu có: giấy tờ chứng minh lý do gia hạn (ví dụ báo giá sửa chữa xe).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Giấy đề nghị → dòng 1; Giấy phép liên vận → dòng 2; giấy tờ khác đính chung dòng 1."
        ),
    },
    {
        "key": "dang-ky-lai-phuong-tien-chuyen-quyen-so-huu-khong-doi-co-quan",
        # Mã TTHC 1.004002, cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io dom-* + attach attp-row 4 dòng, engine tách/gộp
        # trang sourceSegments). Key TRÙNG lõi và ke_khai_links → process/attach + URL kê khai tự nối. ke_khai khai
        # selectSo → agencyProvinceOnly + agencySoFirst + "Sở Xây dựng".
        "flowProfile": "xay-dung",
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moc.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.004002",
                "019d2bfe-3a7b-7789-9f25-1ec7a3f64d81",
            ],
            "textIncludes": ["chuyển quyền sở hữu phương tiện nhưng không thay đổi cơ quan đăng ký"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Đăng ký lại phương tiện trong trường hợp chuyển quyền sở hữu phương tiện nhưng không thay đổi cơ quan "
            "đăng ký phương tiện"
        ),
        "shortLabel": "Đăng ký lại phương tiện thủy khi mua bán, cho tặng",
        "subtitle": "Sang tên tàu, thuyền, phương tiện thủy nội địa cho chủ mới",
        "icon": "⛴️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-3a7b-7789-9f25-1ec7a3f64d81",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        # Bảng thành phần hồ sơ 4 dòng cố định (planner core gom nhiều giấy vào một dòng) → tắt hideRepeatableHint
        # mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "bien_lai_truoc_ba", "name": "Giấy nộp tiền / biên lai lệ phí trước bạ", "icon": "🧾",
             "sides": 1, "repeatable": True},
            {"key": "gcn_an_toan_ky_thuat", "name": "Giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường của "
             "phương tiện (còn hiệu lực)", "icon": "🛟", "sides": 1, "repeatable": True},
            {"key": "hop_dong_mua_ban", "name": "Hợp đồng mua bán (bản sao chứng thực) hoặc giấy tờ cho, tặng, "
             "thừa kế; hóa đơn; giấy chứng nhận đăng ký phương tiện cũ", "icon": "📑",
             "sides": 1, "repeatable": True},
            {"key": "don_de_nghi", "name": "Đơn đề nghị đăng ký lại phương tiện (Mẫu số 07) của chủ mới và đơn "
             "đề nghị xóa đăng ký (Mẫu số 10) của bên bán — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đại diện chủ mới (chỉ để điền)", "icon": "🪪",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF — hệ thống tự tách theo trang):\n"
            "1. Đơn đề nghị đăng ký lại phương tiện thủy nội địa (Mẫu số 07) của chủ MỚI, đã ký — nguồn chính "
            "để điền form.\n"
            "2. Hợp đồng mua bán phương tiện (bản sao chứng thực) hoặc quyết định điều chuyển / giấy tờ cho, "
            "tặng, thừa kế.\n"
            "3. Giấy chứng nhận đăng ký phương tiện cũ; hóa đơn; đơn đề nghị xóa đăng ký (Mẫu số 10) của bên bán.\n"
            "4. Giấy nộp tiền / biên lai lệ phí trước bạ; giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường.\n"
            "5. Nếu có: căn cước công dân của người đại diện chủ mới — chỉ để điền thông tin người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: biên lai trước bạ → dòng 1; giấy an toàn kỹ thuật → dòng 2; hợp đồng + hóa đơn + "
            "giấy đăng ký cũ → dòng 3; Đơn 07 + Đơn xóa 10 → dòng 4."
        ),
    },
    {
        "key": "xoa-dang-ky-phuong-tien-thuy",
        # Mã TTHC 2.001659, cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io dom-* + attach attp-row 1 dòng Đơn), cùng cổng
        # và khuôn tờ khai với 1.004002 ngay trên. ke_khai_links ghi key khác ("xoa-dang-ky-phuong-tien") → khai tay
        # uuid + mã. ke_khai không khai selectSo (DVCQG ghi cơ quan thực hiện cả Sở Xây dựng lẫn UBND cấp xã) → chọn
        # đủ Tỉnh + Xã như Auto Fill, không agencyProvinceOnly/agencySoFirst.
        "flowProfile": "xay-dung",
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moc.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=2.001659",
                "019d2bfe-a039-75a8-85e4-a19d8132bb5d",
            ],
            "textIncludes": ["xóa đăng ký phương tiện thủy nội địa"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "2.001659",
        "label": "Xóa đăng ký phương tiện thủy nội địa",
        "shortLabel": "Xóa đăng ký phương tiện thủy",
        "subtitle": "Tàu, thuyền, sà lan đã bán, hư hỏng hoặc không dùng nữa — xin xóa đăng ký",
        "icon": "⛴️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-a039-75a8-85e4-a19d8132bb5d",
        # Bảng thành phần hồ sơ 1 dòng (Đơn) → mọi tệp vào dòng đó; tắt hideRepeatableHint mà profile bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị xóa đăng ký phương tiện thủy nội địa (Mẫu số 10) — đã ký, đóng dấu",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ phương tiện (cá nhân) hoặc người nộp thay",
             "icon": "🪪", "sides": 2, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (của CHỦ PHƯƠNG TIỆN — người/tổ chức đề nghị xóa đăng ký):\n"
            "1. Đơn đề nghị xóa đăng ký phương tiện thủy nội địa (Mẫu số 10), đã ký, đóng dấu — nguồn chính để điền.\n"
            "2. Chủ phương tiện là cá nhân: căn cước của chủ phương tiện; người khác nộp thay: thêm căn cước người "
            "nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: bảng chỉ có một dòng 'Đơn đề nghị xóa đăng ký phương tiện thủy nội địa' (Bản chính) — "
            "Đơn và căn cước, giấy tờ khác đều đính vào dòng đó."
        ),
    },
    {
        "key": "cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san",
        # Mã TTHC 1.012906, Sở Xây dựng (Form.io dom-* + attach attp-row 6 dòng, engine tách trang sourceSegments).
        # Key TRÙNG lõi và ke_khai_links → process/attach + URL tự nối. ke_khai khai selectSo → agencyProvinceOnly +
        # agencySoFirst + "Sở Xây dựng", luồng chung "xay-dung". Lõi không khai urlScope; đặt dvc.moc.gov.vn như các
        # thủ tục Sở Xây dựng khác — khi chạy thử phải xác nhận host trang kê khai.
        "flowProfile": "xay-dung",
        # Cổng Bộ Xây dựng iGate (stepper 4 bước, tờ khai Form.io) → dẫn đủ 4 bước bằng luồng chung chat/bxd.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moc.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "maThuTuc=1.012906",
                "019d2bfe-88c8-7158-8063-6f38da02b999",
            ],
            "textIncludes": ["cấp mới chứng chỉ hành nghề môi giới bất động sản"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp mới chứng chỉ hành nghề môi giới bất động sản",
        "shortLabel": "Cấp mới chứng chỉ hành nghề môi giới bất động sản",
        "subtitle": "Đăng ký dự thi sát hạch, xin chứng chỉ môi giới nhà đất (Sở Xây dựng)",
        "icon": "🏘️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-88c8-7158-8063-6f38da02b999",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        # Bảng thành phần hồ sơ 6 dòng cố định (planner lõi attp-row; Đơn trang 1 + CCCD trang 2 của cùng một PDF về
        # hai dòng) → tắt hideRepeatableHint mà profile "xay-dung" bật sẵn.
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "don_du_thi", "name": "Đơn đăng ký dự thi sát hạch có dán ảnh 4x6 (Phụ lục XXI Nghị định "
             "96/2024/NĐ-CP) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân 2 mặt của người đề nghị (bản sao chứng thực)", "icon": "🪪",
             "sides": 2, "repeatable": True},
            {"key": "bang_tot_nghiep", "name": "Bằng tốt nghiệp trung học phổ thông trở lên (bản sao chứng thực)",
             "icon": "🎓", "sides": 1, "repeatable": True},
            {"key": "gcn_khoa_hoc", "name": "Giấy chứng nhận hoàn thành khóa đào tạo, bồi dưỡng kiến thức hành nghề "
             "môi giới bất động sản (bản sao chứng thực)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "anh", "name": "02 ảnh 4x6 (và 02 phong bì dán tem nộp trực tiếp)", "icon": "🖼️", "sides": 1,
             "optional": True, "repeatable": True},
            {"key": "khac", "name": "Chứng chỉ do nước ngoài cấp kèm bản dịch (nếu có)", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF — hệ thống tự tách theo trang):\n"
            "1. Đơn đăng ký dự thi sát hạch có dán ảnh 4x6 (Phụ lục XXI Nghị định 96/2024/NĐ-CP), đã ký — nguồn chính "
            "để điền form.\n"
            "2. Căn cước công dân 2 mặt của người đề nghị (bản sao chứng thực).\n"
            "3. Bằng tốt nghiệp trung học phổ thông trở lên (bản sao chứng thực).\n"
            "4. Giấy chứng nhận hoàn thành khóa đào tạo, bồi dưỡng kiến thức hành nghề môi giới bất động sản (bản "
            "sao chứng thực).\n"
            "5. Nếu có: ảnh 4x6 rời; chứng chỉ do nước ngoài cấp kèm bản dịch.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Phần người nộp cổng lấy theo tài khoản đăng nhập; trợ lý điền phần còn lại và Đơn đăng ký dự thi.\n"
            "Bước Thành phần hồ sơ: bằng tốt nghiệp → dòng 1; căn cước → dòng 2; Đơn → dòng 3; chứng chỉ nước ngoài "
            "→ dòng 4 (không có thì bỏ tích); giấy chứng nhận khóa học → dòng 5; ảnh → dòng 6 (không có ảnh rời thì "
            "đính chung trang Đơn)."
        ),
    },
    {
        "key": "dang-ky-thay-doi-noi-dung-ho-kinh-doanh",
        # Cán bộ hay scan cả bộ hồ sơ thành một PDF → planner tách theo cài đặt "Tách tệp có nhiều giấy tờ".
        "supportsSplitDocuments": True,
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
        # Cán bộ hay scan cả bộ hồ sơ thành một PDF → planner tách theo cài đặt "Tách tệp có nhiều giấy tờ".
        "supportsSplitDocuments": True,
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
        # Cán bộ hay scan cả bộ hồ sơ thành một PDF → planner tách theo cài đặt "Tách tệp có nhiều giấy tờ".
        "supportsSplitDocuments": True,
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
        # Cán bộ hay scan cả bộ hồ sơ thành một PDF → planner tách theo cài đặt "Tách tệp có nhiều giấy tờ".
        "supportsSplitDocuments": True,
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
        # 1.115436 (cấp tỉnh, DVCQG "chọn Sở"); mã 1.115476 có thẻ riêng ngay dưới. Detect y hệt lõi, KHÔNG
        # thêm textIncludes: "đính chính giấy chứng nhận đã cấp" là tiền tố của "...đã cấp lần đầu
        # có sai sót" (dinh-chinh-sai-sot-bac-ninh) → textPriority sẽ cướp trang của nhau.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115436"],
            "headingDisabled": True,
        },
        # Hai mã cùng tên trên cổng → hậu tố theo đúng tên trường hợp cổng ghi để không chọn nhầm.
        "label": "Đính chính Giấy chứng nhận đã cấp (Trường hợp Giấy chứng nhận cấp lần đầu có sai sót)",
        "subtitle": "Mã 1.115436 · Sửa thông tin ghi sai trên Giấy chứng nhận quyền sử dụng đất tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f02e5-91cd-7697-8bb3-89bd36d1fa8a",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        # Cổng chọn sẵn cơ quan tiếp nhận (theo tài khoản / thủ tục) → không hỏi bước này.
        "bacNinhAgencyAsk": False,
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
        "key": "dinh-chinh-gcn-da-cap-1115476-bac-ninh",
        "provinceOnly": ["bacninh"],  # đặc thù Bắc Ninh: chỉ account tỉnh này thấy + gọi được
        # Cùng thủ tục với thẻ 1.115436 ngay trên nhưng theo mã 1.115476: DVCQG chỉ chọn Tỉnh
        # (ke_khai_links provinceOnlyAgency, KHÔNG selectSo) → không agencySoFirst, như thẻ thỏa thuận
        # 1.115470. Cổng BN mở eform cũ (nhóm GCN mã TP-H05.000040). Key TRÙNG lõi → process/attach dùng
        # chung pipeline đính chính Bắc Ninh. Khai "code" thẳng: ke_khai_links ghi mã này dưới key khác.
        # Detect y hệt lõi, KHÔNG textIncludes (lý do như thẻ trên).
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115476"],
            "headingDisabled": True,
        },
        "code": "1.115476",
        "label": "Đính chính Giấy chứng nhận đã cấp (Trường hợp Giấy chứng nhận đã đăng ký biến động có sai sót)",
        "subtitle": "Mã 1.115476 · Sửa thông tin ghi sai trên Giấy chứng nhận quyền sử dụng đất tại Bắc Ninh",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f169e-c716-76a7-b47e-269721b1d9c2",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Bắc Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai Bắc Ninh",
        "samePageAttach": True,
        # Cổng chọn sẵn cơ quan tiếp nhận (theo tài khoản / thủ tục) → không hỏi bước này.
        "bacNinhAgencyAsk": False,
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
            "thừa kế, tặng cho, góp vốn; cho thuê, cho thuê lại"
        ),
        "subtitle": (
            "Mã 1.115468 · Đăng ký biến động khi chuyển nhượng, thừa kế, tặng cho, góp vốn, cho thuê quyền "
            "sử dụng đất tại Bắc Ninh"
        ),
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
        # Thẻ mã CŨ: cùng nghiệp vụ với 1.115468 (thẻ mặc định khi công dân nói tên) → subtitle nêu mã để
        # phân biệt hai thẻ gần cùng tên.
        "subtitle": (
            "Mã cũ 1.013831 · Sang tên khi chuyển nhượng, thừa kế, tặng cho, góp vốn, cho thuê quyền sử dụng "
            "đất tại Bắc Ninh"
        ),
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
        # Cổng chọn sẵn cơ quan tiếp nhận (theo tài khoản / thủ tục) → không hỏi bước này.
        "bacNinhAgencyAsk": False,
        # Trang chỉ có 2 tab (Chọn cơ quan tiếp nhận / Tải thành phần hồ sơ): khối gửi hồ sơ / nhận kết quả qua bưu
        # chính công ích nằm ở tab đầu (cổng mặc định bưu chính), nút Nộp hồ sơ hiện ở tab đính kèm.
        "bacNinhTabFlow": {**_BN_TAB_FLOW, "twoTabs": True},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        # Khối "Thông tin trong trường hợp được ủy quyền" của thủ tục này điền NGƯỜI CAO TUỔI (loại đối tượng "Người
        # cao tuổi") khi có người nộp thay — cùng logic nút điền của auto-fill. Pipeline lõi chính là pipeline khối này.
        "bacNinhAuthorizedPerson": {**_BN_AUTHORIZED_PERSON, "subjectOption": "Người cao tuổi"},
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
        # Cổng chọn sẵn cơ quan tiếp nhận (theo tài khoản / thủ tục) → không hỏi bước này.
        "bacNinhAgencyAsk": False,
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
        # ĐI VÒNG như Auto Fill (popup-ke-khai-di-vong.js): 1.014632 chưa liên thông DVCQG ↔ Bắc Ninh,
        # "Nộp trực tuyến" ở trang DVCQG của nó không tới cổng tỉnh. Mở trang DVCQG của thủ tục CẦU
        # 1.014589 (hỗ trợ người cao tuổi, đã liên thông; chọn cơ quan y hệt: Tỉnh + Phường/Xã), tới
        # eform Bắc Ninh mang mã cầu thì flow (_doi_ma_thu_tuc_reply) mở lại URL đó với mã 1.014632.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d7c4f-0f4f-756f-a7db-e8f96edb8171",
        "doiMaThuTuc": {
            "host": "dichvucong.bacninh.gov.vn",
            "thamSo": "_org_bn_hoso_noptructuyen_maThuTucHanhChinh",
            "tu": "1.014589",
            "sang": "1.014632",
        },
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
    {
        # Cổng DVC Bộ Công an (bcaPortal — flow._bca_portal_on_page): chọn thẻ là mở thẳng trang kê khai,
        # không hỏi xác nhận nơi làm. Trên trang, trợ lý hỏi rồi chọn hộ Tỉnh + Xã/Phường/Đặc khu ở khối
        # "Cơ quan thực hiện" (chọn xong cổng mới hiện các mục sau), rồi mới xin giấy tờ để điền
        # (pipeline dang_ky_tam_tru). Mục "HỒ SƠ ĐÍNH KÈM" nằm ngay trên trang kê khai → samePageAttach:
        # điền xong hỏi, bấm "Đính kèm giấy tờ" là đính ngay trên trang (attach/planner.py,
        # engine attachFilesByBcaPlan).
        # URL giống hệt ke_khai_links.json (mã TTHC 1.004194) — sửa một bên phải sửa cả bên kia.
        "key": "dang-ky-tam-tru",
        "label": "Đăng ký tạm trú",
        "shortLabel": "Đăng ký tạm trú",
        "subtitle": "Kê khai trên Cổng dịch vụ công Bộ Công an",
        "icon": "🏠",
        "keKhaiUrl": (
            "https://dichvucong.dancuquocgia.gov.vn/portal/p/home/dang-ky-tam-tru.html?ma_thu_tuc=1.004194"
            "&TT=TAMTRU_01&TT_NAME=%C4%90%C4%83ng%20k%C3%BD%20t%E1%BA%A1m%20tr%C3%BA"
        ),
        "bcaPortal": True,
        "samePageAttach": True,
        "hasAttachmentStep": True,
        # Điền xong hỏi trước, công dân bấm "Đính kèm giấy tờ" mới đính (flow fill_report).
        "askBeforeAttach": True,
        # Đính xong nhắc tích ô cam kết cuối trang rồi mới bấm "Nộp hồ sơ" (flow._attach_done_template).
        "submitCommitLabel": "Tôi xin chịu trách nhiệm trước pháp luật về lời khai trên",
        # id ô tích cam kết trên trang → nút cam cùng nhãn để trợ lý tích hộ (flow._commit_chip).
        "submitCommitCheckbox": "chkCHECK_LIABILITY",
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai thay đổi thông tin cư trú (Mẫu CT01)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cho_o", "name": "Giấy tờ chứng minh chỗ ở hợp pháp (hợp đồng thuê/mượn/ở nhờ, "
             "Giấy chứng nhận quyền sử dụng đất…)", "icon": "🏠", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đăng ký tạm trú", "icon": "🪪",
             "sides": 2, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai thay đổi thông tin cư trú (Mẫu CT01) — nguồn chính điền đơn.\n"
            "2. Giấy tờ chứng minh chỗ ở hợp pháp: hợp đồng cho thuê/cho mượn/cho ở nhờ, Giấy chứng nhận quyền "
            "sử dụng đất…\n"
            "3. CCCD của người đăng ký tạm trú (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    # ── Đợt 26/10: 5 thủ tục, CHƯA chạy thử trên cổng thật. Cổng / cấp cơ quan suy từ code lõi; kiểm khi chạy. ──
    {
        "key": "dang-ky-noi-quy-lao-dong",
        # Mã TTHC 2.001955, cổng Bộ Nội vụ (Form.io + bảng attp-row 4 dòng cố định + dòng "Giấy ủy quyền" tạo qua
        # modal "+ Thêm giấy tờ" — target add-document-dialog, extension trợ lý có engine từ 1.13.6). Key TRÙNG lõi →
        # process/attach tự nối. Văn bản đề nghị gửi Sở Nội vụ → chọn cơ quan cấp Sở như "sua-doi-thong-tin-ho-so-
        # nguoi-co-cong" (ke_khai_links không khai selectSo, cấp Sở là suy từ nội dung hồ sơ — kiểm khi chạy thử).
        # Thủ tục của DOANH NGHIỆP: chủ hồ sơ là doanh nghiệp, người nộp là người đại diện hoặc người được ủy quyền.
        "detect": {
            "urlScope": ["dichvucongbnv.moha.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=2.001955",
                "019d2bfb-42a2-76ce-9565-812f8b562c71",
            ],
            "textIncludes": ["đăng ký nội quy lao động"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Đăng ký nội quy lao động của doanh nghiệp",
        "shortLabel": "Đăng ký nội quy lao động",
        "subtitle": "Doanh nghiệp đăng ký nội quy lao động với Sở Nội vụ",
        "icon": "📘",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-42a2-76ce-9565-812f8b562c71",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nội vụ",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        # Planner lõi tách / gộp theo trang (sourceSegments): có thể scan cả bộ hồ sơ vào MỘT PDF.
        "requiredDocs": [
            {"key": "giay_de_nghi", "name": "Văn bản đề nghị đăng ký nội quy lao động gửi Sở Nội vụ",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "noi_quy", "name": "Quyết định ban hành và toàn văn Nội quy lao động", "icon": "📘",
             "sides": 1, "repeatable": True},
            {"key": "bien_ban", "name": "Biên bản đối thoại / văn bản góp ý của tổ chức đại diện người lao động "
             "tại cơ sở", "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "ky_luat", "name": "Văn bản quy định về kỷ luật lao động, trách nhiệm vật chất (nếu có)",
             "icon": "📑", "sides": 1, "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Giấy ủy quyền (khi người nộp không phải người đại diện theo pháp luật)",
             "icon": "✍️", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy chứng nhận đăng ký doanh nghiệp, căn cước người nộp (nếu có) — chỉ dùng "
             "để điền", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF scan):\n"
            "1. Văn bản (công văn) đề nghị đăng ký nội quy lao động gửi Sở Nội vụ — nguồn chính cho thông tin "
            "doanh nghiệp.\n"
            "2. Quyết định ban hành Nội quy lao động và toàn văn Nội quy lao động.\n"
            "3. Biên bản hội nghị đối thoại / văn bản góp ý của tổ chức đại diện người lao động tại cơ sở.\n"
            "4. Văn bản quy định về kỷ luật lao động, trách nhiệm vật chất (nếu có).\n"
            "5. Giấy ủy quyền (khi người nộp không phải người đại diện theo pháp luật); căn cước nếu có.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân loại và tách trang theo nội dung.\n"
            "Bước Thành phần hồ sơ: Quyết định + Nội quy ghép một tệp vào dòng 1; biên bản góp ý dòng 2; văn bản "
            "kỷ luật dòng 3 (không có thì để trống); văn bản đề nghị dòng 4; Giấy ủy quyền thành dòng mới qua "
            "'+ Thêm giấy tờ'."
        ),
    },
    {
        "key": "cap-gcn-diem-tro-choi-dien-tu-cong-cong",
        # Mã TTHC 1.013792, cổng Bộ VHTTDL dichvucong.bvhttdl.gov.vn — Angular Material bọc custom element liz-* (DOM
        # bỏ formcontrolname) → engine content/fill-liz.js của extension trợ lý (từ 1.13.6) khớp ô theo (.group-header,
        # mat-label). Đính kèm 3 ô cố định (fixed-slot: Đơn 51a / CCCD chủ điểm / GCN hộ kinh doanh) trong
        # <app-upload-flie-multi>. Phần I "Thông tin chung" cổng tự điền. ke_khai_links không khai selectSo → DVCQG
        # chọn đủ Tỉnh + Phường/Xã (UBND cấp xã cấp giấy chứng nhận) — kiểm khi chạy thử.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.013792",
                "019d2bfd-ec30-74cf-b2d7-89358371679b",
            ],
            "headingDisabled": True,
        },
        "label": "Cấp giấy chứng nhận đủ điều kiện hoạt động điểm cung cấp dịch vụ trò chơi điện tử công cộng",
        "shortLabel": "Giấy chứng nhận điểm trò chơi điện tử công cộng",
        "subtitle": "Chủ quán game xin giấy chứng nhận đủ điều kiện hoạt động",
        "icon": "🎮",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-ec30-74cf-b2d7-89358371679b",
        "needsAgencySelect": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "giay_de_nghi", "name": "Đơn đề nghị cấp giấy chứng nhận (Mẫu số 51a) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ điểm", "icon": "🪪", "sides": 2, "repeatable": True},
            {"key": "gpkd", "name": "Giấy chứng nhận đăng ký hộ kinh doanh", "icon": "🏪", "sides": 1,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp giấy chứng nhận đủ điều kiện hoạt động điểm cung cấp dịch vụ trò chơi điện tử công "
            "cộng (Mẫu số 51a), đã ký.\n"
            "2. Căn cước công dân của chủ điểm.\n"
            "3. Giấy chứng nhận đăng ký hộ kinh doanh.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Chủ điểm là cá nhân nên người nộp, người được giải quyết và chủ hộ kinh doanh là cùng một người.\n"
            "Bước đính kèm: Đơn 51a, căn cước, giấy chứng nhận hộ kinh doanh vào đúng 3 ô cố định."
        ),
    },
    {
        "key": "ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang",
        "provinceOnly": ["danang"],  # đặc thù Đà Nẵng (Nghị quyết 75/2026/NQ-HĐND): chỉ account tỉnh này thấy + gọi được
        # Mã địa phương 3.000721, cổng DVC Đà Nẵng (Form.io + bảng attp-row 3 dòng: Đơn → dòng 1 Bản chính; Hợp đồng
        # hỏa táng + Biên bản giao nhận tro cốt → dòng 3 Bản sao; dòng 2 Quyết định hỗ trợ là KẾT QUẢ, planner gửi
        # untickRows để bỏ tick). Key TRÙNG lõi. Đây là thủ tục đầu tiên của trợ lý trên cổng Đà Nẵng: host, wizard
        # iGate 1/2 và chọn cơ quan Tỉnh + Phường/Xã đều là suy luận — kiểm khi chạy thử.
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["01a01d63-1115-70ae-b9e7-80298abb5b0c"],
            "textIncludes": ["Hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng",
        "shortLabel": "Hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng",
        "subtitle": "Gia đình nhận tiền hỗ trợ chở người mất đến cơ sở hỏa táng",
        "icon": "🕯️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/01a01d63-1115-70ae-b9e7-80298abb5b0c",
        "needsAgencySelect": True,
        "agencyProvince": "Đà Nẵng",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "giay_de_nghi", "name": "Đơn đề nghị hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng "
             "(mẫu Nghị quyết 75/2026/NQ-HĐND) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "hop_dong_hoa_tang", "name": "Hợp đồng dịch vụ hỏa táng và Biên bản giao nhận hũ đựng tro cốt",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng ra hỏa táng", "icon": "🪪", "sides": 2,
             "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền / giấy giới thiệu (nếu nộp thay)", "icon": "✍️",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng (Mẫu ban hành kèm Nghị "
            "quyết 75/2026/NQ-HĐND) đã kê khai, ký tên — nguồn chính: người đứng ra hỏa táng.\n"
            "2. Hợp đồng dịch vụ hỏa táng và Biên bản giao nhận hũ đựng tro cốt.\n"
            "3. Căn cước công dân của người đứng ra hỏa táng (và của người nộp thay nếu có).\n"
            "4. Nếu nộp thay: văn bản ủy quyền / giấy giới thiệu.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung. Có thể scan gộp nhiều "
            "giấy tờ trong một PDF.\n"
            "Bước đính kèm: Đơn vào dòng 1 (Bản chính); Hợp đồng + Biên bản giao nhận vào dòng 3 (Bản sao). Dòng 2 "
            "(Quyết định hỗ trợ của UBND) là kết quả giải quyết, không đính."
        ),
    },
    {
        "key": "dang-ky-lap-dat-su-dung-nuoc-sach",
        "provinceOnly": ["laichau"],  # mã địa phương Lai Châu: chỉ account tỉnh này thấy + gọi được
        # Mã địa phương 3.000598. Lõi phát field eForm iGate VNPT (CongDan_* dom-input / dom-select, CongDan_maPhuongXa
        # là ô Phường/Xã của eForm Lai Châu) và mọi ví dụ trong prompt là Lai Châu → suy ra cổng dichvucong.laichau.gov.vn
        # (CHƯA mở link kiểm). Đính kèm fixed-slot theo tên dòng (đơn hộ gia đình / tổ chức, giấy tờ nhà đất…) + căn
        # cước vào dòng thêm mới. Key TRÙNG lõi.
        "detect": {
            "urlScope": ["dichvucong.laichau.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["019ef895-259b-72b1-ba55-179108f16bb1"],
            "textIncludes": ["đăng ký lắp đặt sử dụng nước sạch"],
            "headingDisabled": True,
        },
        "label": "Thủ tục đăng ký lắp đặt sử dụng nước sạch",
        "shortLabel": "Đăng ký lắp đặt sử dụng nước sạch",
        "subtitle": "Đăng ký đấu nối, lắp đồng hồ và ký hợp đồng cấp nước sạch",
        "icon": "🚰",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019ef895-259b-72b1-ba55-179108f16bb1",
        "needsAgencySelect": True,
        "agencyProvince": "Lai Châu",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd", "name": "Căn cước công dân của người nộp hồ sơ", "icon": "🪪", "sides": 2,
             "repeatable": True},
            {"key": "giay_de_nghi", "name": "Đơn đề nghị đấu nối nước sạch và hợp đồng dịch vụ cấp nước (theo mẫu)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "nha_dat", "name": "Giấy chứng nhận quyền sử dụng đất / giấy tờ nhà đất hợp pháp",
             "icon": "🏠", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy đăng ký kinh doanh, quyết định thành lập, hợp đồng thuê nhà (nếu là "
             "doanh nghiệp, tổ chức)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân của người nộp hồ sơ.\n"
            "2. Đơn đăng ký / đơn đề nghị đấu nối nước sạch và hợp đồng dịch vụ cấp nước.\n"
            "3. Giấy chứng nhận quyền sử dụng đất / quyền sở hữu tài sản gắn liền với đất nếu là hộ gia đình, "
            "cá nhân.\n"
            "4. Giấy đăng ký kinh doanh / giấy tờ tổ chức nếu là doanh nghiệp, cơ quan, tổ chức.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "chuyen-doi-ten-hop-dong-nuoc-sach",
        "provinceOnly": ["laichau"],  # mã địa phương Lai Châu: chỉ account tỉnh này thấy + gọi được
        # Mã địa phương 3.000600, cùng cổng và cùng khung eForm với "dang-ky-lap-dat-su-dung-nuoc-sach" ngay trên
        # (cổng suy từ code lõi, CHƯA mở link kiểm). Đính kèm fixed-slot 7 dòng theo tên + dòng thêm mới. Key TRÙNG lõi.
        "detect": {
            "urlScope": ["dichvucong.laichau.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["019ef89f-fba4-7698-9dbb-f18e145be976"],
            "textIncludes": ["chuyển đổi tên trong hợp đồng dịch vụ sử dụng nước sạch"],
            "headingDisabled": True,
        },
        "label": "Thủ tục chuyển đổi tên trong Hợp đồng dịch vụ sử dụng nước sạch",
        "shortLabel": "Chuyển đổi tên trong hợp đồng sử dụng nước sạch",
        "subtitle": "Đổi tên người đứng tên hợp đồng cấp nước sạch",
        "icon": "🚰",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019ef89f-fba4-7698-9dbb-f18e145be976",
        "needsAgencySelect": True,
        "agencyProvince": "Lai Châu",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "cccd", "name": "Căn cước công dân của người nộp hồ sơ", "icon": "🪪", "sides": 2,
             "repeatable": True},
            {"key": "giay_de_nghi", "name": "Đơn xin đổi tên trong hợp đồng dịch vụ cấp nước", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "nha_dat", "name": "Giấy chứng nhận quyền sử dụng đất / hợp đồng chuyển nhượng nhà đất",
             "icon": "🏠", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy đăng ký kinh doanh, quyết định thành lập, giấy đồng thuận của chủ nhà "
             "(nếu là doanh nghiệp, tổ chức)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân của người nộp hồ sơ.\n"
            "2. Đơn xin đổi tên trong hợp đồng dịch vụ cấp nước.\n"
            "3. Giấy chứng nhận quyền sử dụng đất / quyền sở hữu tài sản gắn liền với đất (hoặc hợp đồng chuyển "
            "nhượng nhà đất).\n"
            "4. Nếu là doanh nghiệp, cơ quan, tổ chức: giấy đăng ký kinh doanh, quyết định thành lập hoặc giấy tờ "
            "thuê / ủy quyền liên quan.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "dang-ky-cap-giay-chung-nhan-doi-voi-toan-bo-dien-tich-dat-lai-chau",
        "provinceOnly": ["laichau"],  # đặc thù Lai Châu: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.115590, cùng cổng dichvucong.laichau.gov.vn và cùng khuôn với hai thẻ nước sạch ngay trên (DVCQG
        # chọn đủ Tỉnh + Phường/Xã, không wizard). Detect y hệt lõi; label = label lõi bỏ "[Lai Châu] ". Đính kèm
        # fixed-slot 5 dòng theo tên, CCCD vào "Giấy tờ khác". Key TRÙNG lõi. Chưa chạy thử trên cổng thật.
        "detect": {
            "urlScope": ["dichvucong.laichau.gov.vn"],
            "textIncludes": [
                "toàn bộ diện tích đất đang sử dụng theo quy định tại điểm b và điểm c khoản 2 Điều 24",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Đăng ký, cấp Giấy chứng nhận đối với toàn bộ diện tích đất đang sử dụng theo quy định tại điểm b và điểm "
            "c khoản 2 Điều 24 Nghị định số 101/2024/NĐ-CP"
        ),
        "shortLabel": "Đăng ký, cấp Giấy chứng nhận cho toàn bộ diện tích đất đang sử dụng",
        "subtitle": "Cấp Giấy chứng nhận khi diện tích thửa đất tăng thêm do thay đổi ranh giới so với giấy đã cấp",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f3bb9-231f-777d-a094-d8cfaff2f00d",
        "needsAgencySelect": True,
        "agencyProvince": "Lai Châu",
        "hasAttachmentStep": True,
        "laiChauFeeStep": _LC_FEE_STEP,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 16) — đã kê "
             "khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp (bản gốc), đủ trang những thay đổi sau khi cấp",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "trich_do", "name": "Mảnh trích đo bản đồ địa chính / Phiếu đo đạc chỉnh lý thửa đất",
             "icon": "📐", "sides": 1, "repeatable": True},
            {"key": "uy_quyen", "name": "Giấy ủy quyền / văn bản về việc đại diện (nếu nộp qua người đại diện)",
             "icon": "✍️", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ chứng minh phần diện tích tăng thêm, căn cước công dân (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 16) — nguồn chính điền người nộp; có "
            "thể scan chung một file với Giấy ủy quyền.\n"
            "2. Giấy chứng nhận đã cấp (bản gốc), chụp đủ trang những thay đổi sau khi cấp.\n"
            "3. Mảnh trích đo bản đồ địa chính / Phiếu đo đạc chỉnh lý thửa đất.\n"
            "4. Nếu nộp qua người đại diện: Giấy ủy quyền.\n"
            "5. Nếu có: giấy tờ chứng minh phần diện tích tăng thêm; căn cước công dân của người sử dụng đất.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Đơn → dòng 1, Giấy chứng nhận → dòng 2, Giấy ủy quyền → dòng 3 (file chung Đơn + ủy quyền "
            "đính vào cả dòng 1 và dòng 3), trích đo → dòng 4."
        ),
    },
    {
        "key": "chuyen-muc-dich-su-dung-dat-mien-nui-lai-chau",
        "provinceOnly": ["laichau"],  # đặc thù Lai Châu: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.115578, cùng cổng dichvucong.laichau.gov.vn và cùng khuôn với thẻ 1.115590 ngay trên (DVCQG chọn đủ
        # Tỉnh + Phường/Xã — Đơn gửi Chủ tịch UBND xã, không wizard). Detect y hệt lõi; label = label lõi bỏ "[Lai Châu] ".
        # Đính kèm fixed-slot 3 dòng theo tên, CCCD vào "Giấy tờ khác". Key TRÙNG lõi. Chưa chạy thử trên cổng thật.
        "detect": {
            "urlScope": ["dichvucong.laichau.gov.vn"],
            "textIncludes": [
                "1.115578",
                "chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi hết thời hạn sử dụng "
            "đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư (Đối với các xã miền núi, biên giới; đảo; vùng có "
            "điều kiện kinh tế - xã hội khó khăn; vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn)"
        ),
        "shortLabel": "Chuyển mục đích sử dụng đất (xã miền núi, biên giới)",
        "subtitle": "Xin chuyển đất nông nghiệp sang đất ở, chuyển hình thức hoặc gia hạn thời hạn sử dụng đất",
        "icon": "🏡",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f3675-adb4-70cc-b5e2-3d7a14ebde22",
        "needsAgencySelect": True,
        "agencyProvince": "Lai Châu",
        "hasAttachmentStep": True,
        "laiChauFeeStep": _LC_FEE_STEP,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị chuyển mục đích sử dụng đất (Mẫu số 02) — đã kê khai, ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất (bản gốc), đủ trang bổ sung", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "trich_luc", "name": "Bản trích lục / trích đo bản đồ địa chính thửa đất", "icon": "📐",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị", "icon": "🪪", "sides": 2,
             "optional": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị chuyển mục đích sử dụng đất (Mẫu số 02) — nguồn chính điền địa chỉ, số điện thoại.\n"
            "2. Giấy chứng nhận quyền sử dụng đất (bản gốc), chụp đủ trang bổ sung/nội dung thay đổi.\n"
            "3. Bản trích lục bản đồ địa chính hoặc trích đo bản đồ địa chính.\n"
            "4. Căn cước công dân của người đề nghị (ngày sinh, ngày cấp chỉ có trên thẻ).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Đơn → dòng Mẫu số 02, trích lục → dòng trích lục bản đồ, Giấy chứng nhận → dòng giấy chứng "
            "nhận; căn cước vào \"Giấy tờ khác\"."
        ),
    },
    {
        "key": "giao-dat-cho-thue-dat-lai-chau",
        "provinceOnly": ["laichau"],  # đặc thù Lai Châu: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.115577, cùng cổng dichvucong.laichau.gov.vn và cùng luồng với thẻ 1.115578 ngay trên (trang chọn trường
        # hợp → nút cam "Đồng ý và tiếp tục" → bước Lệ phí). Detect y hệt lõi; label = label lõi bỏ "[Lai Châu] ". Người đề
        # nghị thường là tổ chức (ban quản lý dự án) — "Đối tượng nộp" = Tổ chức. Đính kèm fixed-slot: Đơn + tài liệu gửi
        # kèm chung dòng 1, quyết định dự án chung dòng 9. Key TRÙNG lõi. Chưa chạy thử trên cổng thật.
        "detect": {
            "urlScope": ["dichvucong.laichau.gov.vn"],
            "textIncludes": [
                "1.115577",
                "giao đất, cho thuê đất đối với trường hợp giao đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Giao đất, cho thuê đất đối với trường hợp giao đất, cho thuê đất không đấu giá quyền sử dụng đất, không đấu "
            "thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất và trường hợp giao đất, cho thuê đất thông qua đấu "
            "thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất; giao đất và giao rừng; cho thuê đất và cho thuê "
            "rừng"
        ),
        "shortLabel": "Giao đất, cho thuê đất; giao đất và giao rừng; cho thuê đất và cho thuê rừng",
        "subtitle": "Xin Nhà nước giao đất, cho thuê đất để thực hiện dự án, kể cả giao rừng, cho thuê rừng",
        "icon": "🏗️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f3667-f9e9-77a9-be11-1079162144e9",
        "needsAgencySelect": True,
        "agencyProvince": "Lai Châu",
        "hasAttachmentStep": True,
        "laiChauFeeStep": _LC_FEE_STEP,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị giao đất, cho thuê đất (Mẫu số 01) — đã ký, đóng dấu", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "du_an", "name": "Quyết định phê duyệt dự án đầu tư / chủ trương đầu tư", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "kem_don", "name": "Tài liệu gửi kèm Đơn: xác nhận bồi thường GPMB, biên bản chỉnh lý GCN, biểu "
             "tổng hợp diện tích, trích đo bản đồ, quyết định thu hồi đất", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước của người đi nộp", "icon": "🪪", "sides": 2, "optional": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị giao đất, cho thuê đất (Mẫu số 01) — nguồn chính điền tên tổ chức, trụ sở, điện thoại.\n"
            "2. Quyết định phê duyệt dự án đầu tư / quyết định chủ trương đầu tư.\n"
            "3. Tài liệu gửi kèm Đơn: xác nhận hoàn thành bồi thường GPMB, biên bản chỉnh lý giấy chứng nhận, biểu tổng "
            "hợp diện tích, trích đo bản đồ địa chính khu đất, quyết định thu hồi đất.\n"
            "4. Căn cước của người đi nộp (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung. Mỗi tệp không quá 6 MB.\n"
            "Bước đính kèm: Đơn và tài liệu gửi kèm → dòng Mẫu số 01, quyết định dự án → dòng văn bản phê duyệt dự án; "
            "căn cước vào \"Giấy tờ khác\"."
        ),
    },
    {
        "key": "cap-lai-giay-chung-nhan-do-bi-mat-lai-chau",
        "provinceOnly": ["laichau"],  # đặc thù Lai Châu: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.115557, cùng cổng dichvucong.laichau.gov.vn và cùng luồng với thẻ 1.115578 (trang chọn trường hợp →
        # nút cam "Đồng ý và tiếp tục" → bước Lệ phí). KHÁC các thẻ Lai Châu trên: nộp tại SỞ (ke_khai_links selectSo) →
        # DVCQG chọn Tỉnh Lai Châu, gạt "Sở", bấm "Nộp trực tuyến" thẻ đầu — agencyProvinceOnly + agencySoFirst như
        # cấp lại GCN Quảng Ninh. Detect y hệt lõi; label = label lõi bỏ "[Lai Châu] ". Đính kèm fixed-slot: file scan
        # chung đính nguyên vào dòng Mẫu 16 + dòng Giấy chứng nhận đã cấp. Key TRÙNG lõi. Chưa chạy thử trên cổng thật.
        "detect": {
            "urlScope": ["dichvucong.laichau.gov.vn"],
            "textIncludes": [
                "1.115557",
                "cấp lại giấy chứng nhận do bị mất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp lại Giấy chứng nhận do bị mất",
        "shortLabel": "Cấp lại Giấy chứng nhận do bị mất",
        "subtitle": "Xin cấp lại giấy chứng nhận quyền sử dụng đất khi bị mất",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f2202-879c-7798-a85f-dc5e276efcf0",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Lai Châu",
        "agencyDeptLabel": "Sở Nông nghiệp và Môi trường",
        "hasAttachmentStep": True,
        "laiChauFeeStep": _LC_FEE_STEP,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai (Mẫu số 16) — đã kê khai, ký; có thể scan chung "
             "mọi giấy tờ vào một file", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản sao Giấy chứng nhận đã cấp / trang sổ địa chính (nếu có)", "icon": "📜",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người viết đơn", "icon": "🪪", "sides": 2,
             "optional": True},
            {"key": "kem_theo", "name": "Giấy tờ kèm theo khác: Bảng 16a, Phiếu xóa đăng ký thế chấp (Mẫu 03a), Đơn "
             "xác nhận lại thời hạn đất nông nghiệp (Mẫu 09), mảnh trích đo", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 16) — nguồn chính điền người nộp, địa chỉ, số điện thoại.\n"
            "2. Bản sao Giấy chứng nhận đã cấp / trang sổ địa chính của thửa đất (nếu có).\n"
            "3. Căn cước công dân của người viết đơn (ngày sinh, ngày cấp chỉ có trên thẻ).\n"
            "4. Nếu có: Bảng 16a, Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu 03a), Đơn xin xác nhận lại thời hạn "
            "sử dụng đất nông nghiệp (Mẫu 09), mảnh trích đo bản đồ địa chính.\n"
            "Có thể scan chung mọi giấy vào một file, Mẫu 16 đứng đầu. Hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: file chung → dòng Mẫu số 16 và dòng Giấy chứng nhận đã cấp; mảnh trích đo → dòng 3; giấy "
            "lẻ khác vào \"Giấy tờ khác\". Tệp trên 6 MB được nén lại trước khi đính."
        ),
    },
    # ── Thủ tục đất đai cổng iGate Khánh Hòa (04/11/2026) ──
    # Key TRÙNG lõi → process/attach tự nối; detect y hệt lõi (urlScope khanhhoa.gov.vn — tên thủ tục trùng bản tỉnh
    # khác); label = label lõi bỏ "Khánh Hòa - " (như Bắc Ninh). ke_khai_links không khai provinceOnlyAgency / selectSo
    # → DVCQG chọn đủ Tỉnh + Phường/Xã của tài khoản. "Nộp trực tuyến" sang cổng iGate tỉnh (cùng nền Tuyên Quang): trang
    # nps/apply "Chọn trường hợp giải quyết" rồi stepper 4 bước → cả 6 thủ tục Khánh Hòa đi luồng chung "xay-dung" +
    # bxdFlow như Tuyên Quang (09/11/2026; trước đó 4 thủ tục đầu khai wizard thường nên trợ lý không hỏi trường hợp,
    # không bổ sung ô, không có nút sang Thành phần hồ sơ / Hình thức nhận kết quả / Nộp hồ sơ). Mỗi thủ tục một form
    # cho mọi quy trình → không cần caseOptions ép form.
    {
        "key": "dang-ky-dat-dai-lan-dau-khanh-hoa",
        "provinceOnly": ["khanhhoa"],  # đặc thù Khánh Hòa: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.013978. Bảng đính kèm 20 dòng, mỗi file đính nguyên khối vào dòng của giấy chính trong file.
        "detect": {
            "urlScope": ["khanhhoa.gov.vn"],
            "textIncludes": [
                "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, "
                "quyền sở hữu tài sản gắn liền với đất lần đầu"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản "
            "gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước "
            "ngoài"
        ),
        "shortLabel": "Đăng ký đất đai, cấp Giấy chứng nhận quyền sử dụng đất lần đầu",
        "subtitle": "Kê khai đăng ký đất đai và xin cấp Giấy chứng nhận quyền sử dụng đất lần đầu tại Khánh Hòa",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-8678-770b-8917-1872078767cd",
        "flowProfile": "xay-dung",
        "agencyProvince": "Khánh Hòa",
        "bxdFlow": _KH_BXD_FLOW,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 19) — đã kê khai, ký; kèm "
             "tờ khai lệ phí trước bạ, thuế thu nhập cá nhân (nếu có)", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "nguon_goc", "name": "Giấy tờ về nguồn gốc đất (hợp đồng, giấy chuyển nhượng, tặng cho có chữ ký "
             "hai bên; giấy tờ theo Điều 137; giấy tờ thừa kế)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "trich_do", "name": "Phiếu xác nhận kết quả đo đạc, bản mô tả ranh giới, mảnh trích đo địa chính "
             "thửa đất", "icon": "📐", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất (nếu có)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền (nếu nộp thay), văn bản xác định thành viên hộ gia đình hoặc "
             "giấy tờ khác", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp):\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 19) đã kê khai, ký — nguồn chính điền người "
            "nộp, chủ hồ sơ, số thửa, số tờ, địa chỉ thửa đất; kèm tờ khai lệ phí trước bạ, thuế thu nhập cá nhân "
            "(nếu có).\n"
            "2. Giấy tờ về nguồn gốc đất: hợp đồng/giấy chuyển nhượng, tặng cho có chữ ký hai bên; giấy tờ theo Điều "
            "137; giấy tờ thừa kế.\n"
            "3. Phiếu xác nhận kết quả đo đạc, bản mô tả ranh giới, mảnh trích đo địa chính.\n"
            "4. Căn cước công dân của người sử dụng đất (nếu có); nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: mỗi file đính nguyên khối vào dòng của giấy chính trong file (Đơn → dòng 19, giấy "
            "chuyển quyền → dòng 1, trích đo → dòng 8)."
        ),
    },
    {
        "key": "giao-thue-chuyen-muc-dich-dat-khanh-hoa",
        "provinceOnly": ["khanhhoa"],  # đặc thù Khánh Hòa: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.013949, cùng template ba khối với đăng ký đất đai lần đầu ngay trên. Bảng đính kèm 15 dòng; giấy ủy
        # quyền / giấy giới thiệu thêm dòng qua "Thêm giấy tờ".
        "detect": {
            "urlScope": ["khanhhoa.gov.vn"],
            "textIncludes": [
                "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp giao đất, cho thuê đất không "
                "đấu giá quyền sử dụng đất",
                "gia hạn sử dụng đất khi hết thời hạn sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp giao đất, cho thuê đất không đấu "
            "giá quyền sử dụng đất, không đấu thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất; trường hợp giao "
            "đất, cho thuê đất thông qua đấu thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất; giao đất và giao "
            "rừng; cho thuê đất và cho thuê rừng, gia hạn sử dụng đất khi hết thời hạn sử dụng đất"
        ),
        "shortLabel": "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất",
        "subtitle": "Xin giao đất, thuê đất, chuyển mục đích hoặc gia hạn sử dụng đất tại Khánh Hòa",
        "icon": "🏞️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-867b-703e-a311-18fc1df76fc8",
        "flowProfile": "xay-dung",
        "agencyProvince": "Khánh Hòa",
        "bxdFlow": _KH_BXD_FLOW,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 06) — đã "
             "kê khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất đã cấp (đủ các trang)", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị (nếu có)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Giấy ủy quyền (kèm lời chứng), giấy giới thiệu (nếu nộp thay)", "icon": "✍️",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp):\n"
            "1. Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 06) đã kê khai, ký — nguồn "
            "chính điền nội dung yêu cầu, số điện thoại người đề nghị, địa điểm thửa đất.\n"
            "2. Giấy chứng nhận quyền sử dụng đất đã cấp (đủ các trang) — chủ hồ sơ, số thửa, số tờ, địa chỉ thửa "
            "đất.\n"
            "3. Căn cước công dân của người đề nghị (nếu có).\n"
            "4. Nếu nộp thay: giấy ủy quyền (kèm lời chứng), giấy giới thiệu.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Giấy chứng nhận → dòng 11, Đơn đề nghị → dòng 14, giấy ủy quyền/giấy giới thiệu thêm dòng "
            "qua 'Thêm giấy tờ' (không thêm được thì đính chung dòng 14)."
        ),
    },
    {
        "key": "cap-doi-gcn-khanh-hoa",
        "provinceOnly": ["khanhhoa"],  # đặc thù Khánh Hòa: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.012783 (05/11/2026), cùng template ba khối với hai thủ tục ngay trên; một form cho cả hai quy trình
        # 1.012783-1.1 / -1.2 nên không cần caseOptions. Bảng đính kèm 4 dòng; văn bản ủy quyền thêm qua "Thêm giấy tờ".
        # Khác hai thủ tục trên: ke_khai_links khai provinceOnlyAgency (KHÔNG selectSo) → DVCQG chỉ chọn Tỉnh Khánh Hòa,
        # bỏ ô Phường/Xã, không agencySoFirst. Trang kết quả ra thẻ VPĐK tỉnh rồi từng Chi nhánh VPĐK đất đai theo huyện
        # cũ → bấm thẻ chi nhánh của xã tài khoản (agencyCardIncludesByWard, lấy từ submitCardIncludesByWard ở cuối file).
        "detect": {
            "urlScope": ["khanhhoa.gov.vn"],
            "textIncludes": ["Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
        "shortLabel": "Cấp đổi Giấy chứng nhận quyền sử dụng đất",
        "subtitle": "Đổi Giấy chứng nhận quyền sử dụng đất cũ, rách, hư hỏng sang Giấy chứng nhận mới tại Khánh Hòa",
        "icon": "🔄",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-6f3b-7238-9e41-307101b01795",
        "flowProfile": "xay-dung",
        "agencyProvinceOnly": True,
        "agencyProvince": "Khánh Hòa",
        "bxdFlow": _KH_BXD_FLOW,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) — đã kê khai, "
             "ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận đã cấp (đủ các trang, kèm trang bổ sung)", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "trich_do", "name": "Mảnh trích đo bản đồ địa chính thửa đất (nếu đo đạc lại)", "icon": "📐",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất (nếu có)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu nộp thay)", "icon": "✍️", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp):\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) đã kê khai, ký — người sử dụng "
            "đất, số căn cước, địa chỉ, điện thoại, nội dung biến động.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp (đủ các trang, kèm trang bổ sung) — số thửa, số tờ, địa chỉ thửa đất.\n"
            "3. Mảnh trích đo bản đồ địa chính thửa đất (nếu đo đạc lại).\n"
            "4. Căn cước công dân của người sử dụng đất (nếu có); nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Giấy chứng nhận → dòng 1, mảnh trích đo → dòng 3, Đơn → dòng 4; văn bản ủy quyền thêm dòng "
            "qua 'Thêm giấy tờ' (không thêm được thì đính chung dòng 4)."
        ),
    },
    {
        "key": "dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-khanh-hoa",
        "provinceOnly": ["khanhhoa"],  # đặc thù Khánh Hòa: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.013831 (05/11/2026), cùng template ba khối và cùng cách chọn cơ quan với cấp đổi GCN ngay trên:
        # ke_khai_links khai provinceOnlyAgency → DVCQG chỉ chọn Tỉnh; thẻ Chi nhánh VPĐK đất đai theo xã lấy từ
        # submitCardIncludesByWard (agencyCardIncludesByWard gắn ở cuối file). Bảng đính kèm 13 dòng; tờ khai thuế, giấy
        # nộp tiền/quyết định xử phạt thêm dòng qua "Thêm giấy tờ".
        "detect": {
            "urlScope": ["khanhhoa.gov.vn"],
            "textIncludes": [
                "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các trường hợp chuyển "
                "đổi",
                "chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các trường hợp chuyển đổi "
            "quyền sử dụng đất nông nghiệp mà không theo phương án dồn điền, đổi thửa; chuyển nhượng, thừa kế, tặng cho "
            "quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất, góp vốn bằng quyền sử dụng đất, quyền sở hữu tài "
            "sản gắn liền với đất; cho thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ "
            "tầng; bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất thuê của Nhà nước theo "
            "hình thức thuê đất trả tiền hàng năm"
        ),
        "shortLabel": "Đăng ký biến động chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất",
        "subtitle": "Đăng ký sang tên khi nhận chuyển nhượng, tặng cho, thừa kế quyền sử dụng đất tại Khánh Hòa",
        "icon": "🤝",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-7ece-728d-9b60-6563e0a7a94e",
        "flowProfile": "xay-dung",
        "agencyProvinceOnly": True,
        "agencyProvince": "Khánh Hòa",
        "bxdFlow": _KH_BXD_FLOW,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) — đã kê khai, "
             "ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận đã cấp (đủ các trang, kèm trang bổ sung)", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "hop_dong", "name": "Hợp đồng chuyển nhượng/tặng cho hoặc văn bản phân chia, khai nhận di sản thừa "
             "kế (có công chứng)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai lệ phí trước bạ, tờ khai thuế thu nhập cá nhân", "icon": "🧾",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "trich_do", "name": "Phiếu đo đạc chỉnh lý / mảnh trích đo thửa đất (nếu có)", "icon": "📐",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nhận chuyển quyền (nếu có)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền (nếu nộp thay), giấy nộp tiền hoặc giấy tờ khác", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp):\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) đã kê khai, ký.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp (kèm trang bổ sung).\n"
            "3. Hợp đồng chuyển nhượng/tặng cho hoặc văn bản thỏa thuận, khai nhận, phân chia di sản thừa kế.\n"
            "4. Tờ khai lệ phí trước bạ, thuế thu nhập cá nhân; phiếu đo đạc chỉnh lý (nếu có); căn cước công dân; "
            "nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: phiếu đo đạc → dòng 1, Giấy chứng nhận → dòng 3, hợp đồng/văn bản thừa kế → dòng 4, Đơn → "
            "dòng 7, ủy quyền → dòng 10; tờ khai thuế và giấy nộp tiền thêm dòng qua 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn-khanh-hoa",
        "provinceOnly": ["khanhhoa"],  # đặc thù Khánh Hòa: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.013995 (05/11/2026), cùng template ba khối và cùng cách chọn cơ quan với cấp đổi GCN Khánh Hòa:
        # ke_khai_links khai provinceOnlyAgency → DVCQG chỉ chọn Tỉnh; thẻ Chi nhánh VPĐK đất đai theo xã lấy từ
        # submitCardIncludesByWard (agencyCardIncludesByWard gắn ở cuối file). Trang "Chọn trường hợp giải quyết" (Đơn vị
        # thực hiện + 4 quy trình 1.013995-1.1/1.2/2.1/2.2) → luồng chung "xay-dung" như 4 thủ tục Khánh Hòa trên:
        # trợ lý đọc các lựa chọn của trang, hỏi công dân, chọn hộ và bấm Đồng ý; ô Đơn vị thực hiện có nhiều chi nhánh
        # thì giữ chi nhánh của xã tài khoản (flow._narrow_mae_agency). Bảng đính kèm 8 dòng; tờ khai lệ phí trước bạ,
        # giấy nộp tiền, CCCD thêm dòng qua "Thêm giấy tờ". Trang nps/apply Khánh Hòa SUY cùng form#ngSelectAgencyForm
        # với cổng Bộ Y tế — chưa chạy thử trên cổng thật.
        "detect": {
            "urlScope": ["khanhhoa.gov.vn"],
            "textIncludes": ["tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận hoặc đăng ký thay đổi về tài sản gắn liền "
            "với đất so với nội dung đã đăng ký, gia hạn thời hạn sở hữu nhà ở của tổ chức nước ngoài, cá nhân nước ngoài "
            "theo quy định của pháp luật về nhà ở nội dung đã đăng ký"
        ),
        "shortLabel": "Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận",
        "subtitle": "Đăng ký bổ sung hoặc thay đổi nhà ở, công trình trên thửa đất đã có Giấy chứng nhận tại Khánh Hòa",
        "icon": "🏠",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-868b-77ba-8cfe-b3af7e63b81a",
        "flowProfile": "xay-dung",
        "agencyProvinceOnly": True,
        "agencyProvince": "Khánh Hòa",
        "bxdFlow": _KH_BXD_FLOW,
        "caseOptions": _KH_TAI_SAN_CASE_OPTIONS,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) — đã kê khai, "
             "ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp (đủ các trang)", "icon": "📜", "sides": 1,
             "repeatable": True},
            {"key": "giay_phep", "name": "Giấy phép xây dựng kèm hồ sơ thiết kế, bản vẽ (hoặc giấy tờ khác về quyền sở "
             "hữu nhà ở, công trình)", "icon": "🏗️", "sides": 1, "repeatable": True},
            {"key": "to_khai", "name": "Tờ khai lệ phí trước bạ, giấy nộp tiền vào ngân sách nhà nước", "icon": "🧾",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng tên (nếu có)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu nộp thay)", "icon": "✍️", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp):\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) đã kê khai, ký — người đứng tên, số "
            "căn cước, địa chỉ, điện thoại, nội dung biến động.\n"
            "2. Giấy chứng nhận đã cấp (đủ các trang).\n"
            "3. Giấy phép xây dựng kèm hồ sơ thiết kế, bản vẽ (hoặc giấy tờ khác về quyền sở hữu nhà ở, công trình).\n"
            "4. Tờ khai lệ phí trước bạ, giấy nộp tiền vào ngân sách nhà nước (nếu có); căn cước công dân; nếu nộp thay: "
            "văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Đơn → dòng 1, văn bản ủy quyền → dòng 3, Giấy chứng nhận → dòng 6, giấy phép xây dựng kèm bản "
            "vẽ → dòng 7 (sơ đồ nhà trong bộ bản vẽ không tải lại ở dòng 5); tờ khai lệ phí trước bạ, giấy nộp tiền, căn "
            "cước thêm dòng qua 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-khanh-hoa",
        "provinceOnly": ["khanhhoa"],  # đặc thù Khánh Hòa: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.013947 (05/11/2026), cùng cách đi như đăng ký tài sản 1.013995 ngay trên: DVCQG chỉ chọn Tỉnh + thẻ Chi
        # nhánh VPĐK đất đai theo xã (agencyCardIncludesByWard), trang "Chọn trường hợp giải quyết" của cổng (quy trình
        # 1.013947-1.1…, cùng một form) → luồng chung "xay-dung" đọc lựa chọn, hỏi công dân, chọn hộ. Bảng đính kèm 2 dòng:
        # Đơn → dòng 1, Giấy chứng nhận + Phiếu đo đạc → cùng dòng 2.
        "detect": {
            "urlScope": ["khanhhoa.gov.vn"],
            "textIncludes": ["Xác nhận tiếp tục sử dụng đất nông nghiệp"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Xác nhận tiếp tục sử dụng đất nông nghiệp",
        "subtitle": "Xin xác nhận lại thời hạn sử dụng đất nông nghiệp đã hết hạn ghi trên Giấy chứng nhận tại Khánh Hòa",
        "icon": "🌾",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-8677-74ff-8111-ee0c889b713f",
        "flowProfile": "xay-dung",
        "agencyProvinceOnly": True,
        "agencyProvince": "Khánh Hòa",
        "bxdFlow": _KH_BXD_FLOW,
        "requiredDocs": [
            {"key": "don", "name": "Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp (Mẫu số 09) — đã kê khai, ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp (đủ các trang, kèm trang bổ sung)", "icon": "📜", "sides": 1,
             "repeatable": True},
            {"key": "trich_do", "name": "Phiếu đo đạc chỉnh lý thửa đất / mảnh trích đo (nếu có)", "icon": "📐",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người sử dụng đất (nếu có)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu nộp thay)", "icon": "✍️", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp):\n"
            "1. Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp (Mẫu số 09) đã kê khai, ký — người sử dụng đất, "
            "ngày sinh, số căn cước, địa chỉ liên hệ, điện thoại, nội dung đề nghị.\n"
            "2. Giấy chứng nhận đã cấp (đủ các trang, kèm trang bổ sung).\n"
            "3. Phiếu đo đạc chỉnh lý thửa đất / mảnh trích đo (nếu có).\n"
            "4. Căn cước công dân (nếu có); nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Đơn → dòng 1, Giấy chứng nhận và Phiếu đo đạc → cùng dòng 2; văn bản ủy quyền, căn cước thêm "
            "dòng qua 'Thêm giấy tờ'."
        ),
    },
    # ── Thủ tục đất đai cổng iGate Tuyên Quang (04/11/2026) ──
    # Key TRÙNG lõi → process/attach tự nối; detect y hệt entry gốc của lõi (urlScope tuyenquang.gov.vn — tên thủ tục trùng
    # bản tỉnh khác); label = label lõi bỏ "Tuyên Quang - ". ke_khai_links không khai provinceOnlyAgency / selectSo →
    # DVCQG chọn đủ Tỉnh + Phường/Xã của tài khoản. "Nộp trực tuyến" sang cổng iGate tỉnh (cùng nền Bộ Xây dựng): hộp
    # thoại "Chọn trường hợp giải quyết" rồi stepper 4 bước → luồng chung "xay-dung": trợ lý đọc lựa chọn của hộp thoại,
    # hỏi công dân, chọn hộ và bấm Đồng ý. Mỗi quy trình một FORM: quy trình đã chọn → caseOptions → options.quyTrinh →
    # pipeline lõi của key gốc điền đúng form iLis / VBDLIS. variants là đường dự phòng khi extension không đọc được
    # hộp thoại (portalAvoid nhiều cụm nối "|"). Tên quy trình lấy theo file mapping — chưa chạy thử trên cổng thật.
    {
        "key": "dang-ky-dat-dai-lan-dau-tuyen-quang",
        "provinceOnly": ["tuyenquang"],  # đặc thù Tuyên Quang: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.013978. Ba quy trình: "5 bước 20 ngày" (form gốc), "iLis cấp xã - 30 ngày", "VBDLIS 20 ngày". Bảng
        # đính kèm 20 dòng chung, mỗi file đính nguyên khối vào dòng của giấy chính trong file.
        "detect": {
            "urlScope": ["tuyenquang.gov.vn"],
            "textIncludes": [
                "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, "
                "quyền sở hữu tài sản gắn liền với đất lần đầu"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản "
            "gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước "
            "ngoài"
        ),
        "shortLabel": "Đăng ký đất đai, cấp Giấy chứng nhận quyền sử dụng đất lần đầu",
        "subtitle": "Kê khai đăng ký đất đai và xin cấp Giấy chứng nhận quyền sử dụng đất lần đầu tại Tuyên Quang",
        "icon": "📜",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-8678-770b-8917-1872078767cd",
        "flowProfile": "xay-dung",
        "agencyProvince": "Tuyên Quang",
        "bxdFlow": _TQ_BXD_FLOW,
        "caseOptions": [_TQ_CASE_ILIS, _TQ_CASE_VBDLIS, _TQ_CASE_DEFAULT],
        "variants": {
            "equalChips": True,
            "options": [
                {"key": "nam_buoc", "label": "Quy trình 5 bước (20 ngày)", "chip": "📄 Quy trình 5 bước",
                 "portalAvoid": "ilis|vbdlis", "desc": "tờ khai người nộp, không có ô thửa đất"},
                {"key": "ilis", "label": "Quy trình iLis cấp xã (30 ngày)", "chip": "🗂️ Quy trình iLis cấp xã",
                 "portalMatch": "ilis", "desc": "tờ khai tách người nộp, thửa đất, chủ hồ sơ",
                 "pipelineOptions": {"quyTrinh": "ilis"}},
                {"key": "vbdlis", "label": "Quy trình VBDLIS (20 ngày)", "chip": "🗺️ Quy trình VBDLIS",
                 "portalMatch": "vbdlis", "desc": "tờ khai có số thửa, số tờ bản đồ, địa chỉ thửa đất",
                 "pipelineOptions": {"quyTrinh": "vbdlis"}},
            ],
        },
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 19) — đã kê khai, ký; kèm "
             "tờ khai lệ phí trước bạ, thuế thu nhập cá nhân (nếu có)", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "nguon_goc", "name": "Giấy tờ về nguồn gốc đất (hợp đồng, giấy chuyển nhượng, tặng cho có chữ ký "
             "hai bên; giấy tờ theo Điều 137; giấy tờ thừa kế)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "trich_do", "name": "Phiếu xác nhận kết quả đo đạc, bản mô tả ranh giới, mảnh trích đo địa chính "
             "thửa đất", "icon": "📐", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân hoặc giấy khai sinh của người sử dụng đất (nếu có)", "icon": "🪪",
             "sides": 2, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền (nếu nộp thay), văn bản xác định thành viên hộ gia đình hoặc "
             "giấy tờ khác", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp):\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 19) đã kê khai, ký — nguồn chính điền người "
            "nộp, chủ hồ sơ, điện thoại, địa chỉ, nội dung đề nghị, số thửa, số tờ; kèm tờ khai lệ phí trước bạ, thuế "
            "thu nhập cá nhân (nếu có).\n"
            "2. Giấy tờ về nguồn gốc đất: hợp đồng/giấy chuyển nhượng, tặng cho có chữ ký hai bên; giấy tờ theo Điều "
            "137; giấy tờ thừa kế.\n"
            "3. Phiếu xác nhận kết quả đo đạc, bản mô tả ranh giới, mảnh trích đo địa chính.\n"
            "4. Căn cước công dân hoặc giấy khai sinh của người sử dụng đất (nếu có); nếu nộp thay: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung. Có cả bản thường và bản ký số "
            "của cùng một tệp thì chỉ đọc và đính bản ký số.\n"
            "Bước đính kèm: mỗi file đính nguyên khối vào dòng của giấy chính trong file (Đơn → dòng 16, giấy "
            "chuyển quyền → dòng 4, trích đo → dòng 10)."
        ),
    },
    {
        "key": "dinh-chinh-gcn-cap-lan-dau-sai-sot-tuyen-quang",
        "provinceOnly": ["tuyenquang"],  # đặc thù Tuyên Quang: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.012796. Hai quy trình: quy trình thường (form gốc) và "iLis cấp xã" (form người nộp / thửa đất / chủ
        # hồ sơ / Giấy chứng nhận). Bảng đính kèm 8 dòng chung, dòng 5/6/7 lặp dòng 1/2/3.
        "detect": {
            "urlScope": ["tuyenquang.gov.vn"],
            "textIncludes": ["Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "shortLabel": "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "subtitle": "Sửa thông tin sai trên Giấy chứng nhận quyền sử dụng đất đã cấp tại Tuyên Quang",
        "icon": "✏️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-76cb-741b-996e-33d1ef50be50",
        "flowProfile": "xay-dung",
        "agencyProvince": "Tuyên Quang",
        "bxdFlow": _TQ_BXD_FLOW,
        "caseOptions": [_TQ_CASE_ILIS, _TQ_CASE_DEFAULT],
        "variants": {
            "equalChips": True,
            "options": [
                {"key": "thuong", "label": "Quy trình thường", "chip": "📄 Quy trình thường",
                 "portalAvoid": "ilis", "desc": "tờ khai người nộp, kèm người ủy quyền nếu có"},
                {"key": "ilis", "label": "Quy trình iLis cấp xã", "chip": "🗂️ Quy trình iLis cấp xã",
                 "portalMatch": "ilis", "desc": "tờ khai tách người nộp, thửa đất, chủ hồ sơ, Giấy chứng nhận",
                 "pipelineOptions": {"quyTrinh": "ilis"}},
            ],
        },
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18 hoặc Mẫu số "
             "11/ĐK) — đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp cần đính chính (đủ các trang)", "icon": "📜", "sides": 1,
             "repeatable": True},
            {"key": "chung_minh", "name": "Giấy tờ chứng minh sai sót (giấy khai sinh, trích lục kết hôn, hợp đồng, "
             "quyết định…)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người bị sai thông tin (nếu có)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Văn bản ủy quyền (nếu nộp thay)", "icon": "✍️", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (cả bộ có thể là một PDF scan gộp):\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18 hoặc Mẫu số 11/ĐK) đã ký — nguồn "
            "chính điền nội dung đính chính, số điện thoại.\n"
            "2. Giấy chứng nhận đã cấp cần đính chính.\n"
            "3. Giấy tờ chứng minh sai sót: CCCD của người bị sai thông tin, giấy khai sinh, trích lục kết hôn, hợp "
            "đồng chuyển nhượng, quyết định hoặc giấy xác nhận liên quan.\n"
            "4. Nếu nộp thay: văn bản về việc ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Giấy chứng nhận → dòng 1; giấy tờ chứng minh sai sót + CCCD → dòng 2 (Bản sao); văn bản ủy "
            "quyền → dòng 3; Đơn Mẫu số 11/ĐK → dòng 4; Đơn Mẫu số 18 → dòng 8. File gộp có Đơn đính nguyên một lần ở "
            "dòng Đơn."
        ),
    },
    {
        "key": "giao-thue-chuyen-muc-dich-dat-giao-rung-gia-han-tuyen-quang",
        "provinceOnly": ["tuyenquang"],  # đặc thù Tuyên Quang: chỉ account tỉnh này thấy + gọi được
        # Mã TTHC 1.013949. Hai quy trình: quy trình thường (form gốc) và "VBDLIS 25 ngày" (form thông tin chung + địa chỉ
        # thửa đất). Bảng đính kèm 14 dòng chung, dòng 11 trùng dòng 8.
        "detect": {
            "urlScope": ["tuyenquang.gov.vn"],
            "textIncludes": [
                "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp giao đất, cho thuê đất không "
                "đấu giá quyền sử dụng đất",
                "gia hạn sử dụng đất khi hết thời hạn sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp giao đất, cho thuê đất không đấu "
            "giá quyền sử dụng đất, không đấu thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất; trường hợp giao "
            "đất, cho thuê đất thông qua đấu thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất; giao đất và giao "
            "rừng; cho thuê đất và cho thuê rừng, gia hạn sử dụng đất khi hết thời hạn sử dụng đất"
        ),
        "shortLabel": "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất",
        "subtitle": "Xin giao đất, thuê đất, chuyển mục đích hoặc gia hạn sử dụng đất tại Tuyên Quang",
        "icon": "🏞️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-867b-703e-a311-18fc1df76fc8",
        "flowProfile": "xay-dung",
        "agencyProvince": "Tuyên Quang",
        "bxdFlow": _TQ_BXD_FLOW,
        "caseOptions": [_TQ_CASE_VBDLIS, _TQ_CASE_DEFAULT],
        "variants": {
            "equalChips": True,
            "options": [
                {"key": "thuong", "label": "Quy trình thường", "chip": "📄 Quy trình thường",
                 "portalAvoid": "vbdlis", "desc": "tờ khai người nộp, kèm người ủy quyền nếu có"},
                {"key": "vbdlis", "label": "Quy trình VBDLIS", "chip": "🗺️ Quy trình VBDLIS",
                 "portalMatch": "vbdlis", "desc": "tờ khai có số thửa, số tờ bản đồ, địa chỉ thửa đất",
                 "pipelineOptions": {"quyTrinh": "vbdlis"}},
            ],
        },
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 01) hoặc đơn "
             "gia hạn (Mẫu số 04) — đã kê khai, ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất đã cấp (đủ các trang)", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị (nếu có)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "uy_quyen", "name": "Giấy ủy quyền (kèm lời chứng thực) nếu nộp thay, giấy tờ dự án/phương án nếu "
             "có", "icon": "✍️", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên (mỗi bộ giấy có thể là một PDF gộp):\n"
            "1. Đơn đề nghị giao đất/cho thuê đất/chuyển mục đích sử dụng đất (Mẫu số 01) hoặc đơn gia hạn (Mẫu số 04) "
            "đã ký — nội dung đề nghị, số điện thoại, thửa đất, người đồng sử dụng.\n"
            "2. Giấy chứng nhận đã cấp (đủ các trang) — số, số vào sổ, ngày cấp, số thửa, số tờ.\n"
            "3. Căn cước công dân của người đề nghị (nếu có); nếu nộp thay: giấy ủy quyền kèm lời chứng thực.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Đơn Mẫu số 01 → dòng 2 (giấy ủy quyền, CCCD đính chung dòng này); Giấy chứng nhận → dòng "
            "4; hồ sơ gia hạn: Đơn Mẫu số 04 → dòng 14, Giấy chứng nhận → dòng 13."
        ),
    },
    # ── Thủ tục toàn quốc đã có pipeline Auto Fill, đưa lên trợ lý (01/11/2026) ──
    # Key TRÙNG lõi → process/attach tự nối qua core_registry. Cờ chọn cơ quan theo ke_khai_links: selectSo →
    # agencyProvinceOnly + agencySoFirst; provinceOnlyAgency → agencyProvinceOnly (+ maePortal cổng NN&MT). Cổng Bộ
    # Xây dựng dùng profile "xay-dung" + bxdFlow như các thủ tục cùng cổng. Cổng Bộ VHTTDL, Bộ Công Thương, Bộ Nội vụ
    # chưa có luồng dẫn bước riêng (content/bxd/portal.js không khai host) → luồng chung: chọn cơ quan, điền, đính
    # kèm, công dân tự chuyển bước và nộp. Chỉ đưa lên thủ tục đã có URL kê khai (cấp GCN ATTP Công Thương, khuyến
    # mại may rủi, thi tuyển Một cửa Bộ Nội vụ, xóa đăng ký phương tiện thủy, GCNKNCM chưa có → chưa lên). Chưa chạy
    # thử trên cổng thật — kiểm khi chạy thử.
    {
        "key": "thong-bao-san-pham-quang-cao-bang-ron",
        # Mã TTHC 1.004650, cổng Bộ VHTTDL (liz-*, engine content/fill-liz.js như điểm trò chơi điện tử).
        # ke_khai_links ghi key khác ("thong-bao-san-pham-quang-cao-bang-quang-cao-bang-ron") → khai tay uuid + mã.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.004650",
                "019d2bfd-d4c8-725d-8498-130caf913cf2",
            ],
        },
        "code": "1.004650",
        "label": "Thủ tục tiếp nhận hồ sơ thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn",
        "shortLabel": "Thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn",
        "subtitle": "Doanh nghiệp thông báo nội dung bảng quảng cáo, băng-rôn trước khi treo",
        "icon": "📢",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-d4c8-725d-8498-130caf913cf2",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        # Trang nộp MỘT TRANG (form liz + Thành phần hồ sơ + ô cam kết + ô VNPost + nút "Lưu và nộp hồ sơ"): extension
        # khai supportsLizFlow thì đi luồng trang một trang (chat/tu_phap_moi.py) — một nút điền + đính, bổ sung ô
        # trống, Tiếp tục = tích ô cam kết (nút nộp của cổng chỉ mở sau khi tích) + hỏi bưu điện, rồi nộp. Bản cũ đi
        # luồng chung như trước.
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "thong_bao", "name": "Thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn (Mẫu số 01)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn_dkdn", "name": "Giấy chứng nhận đăng ký doanh nghiệp", "icon": "🏢", "sides": 1,
             "repeatable": True},
            {"key": "ma_ket", "name": "Ma-két, bản phối cảnh, giấy tờ hợp chuẩn / hợp quy", "icon": "🖼️",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Thông báo khuyến mại, văn bản quyền sử dụng địa điểm, giấy phép xây dựng "
             "(nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn (Mẫu số 01) — nguồn chính để điền.\n"
            "2. Giấy chứng nhận đăng ký doanh nghiệp — để điền khối 'Thông tin người ủy quyền'.\n"
            "3. Ma-két, bản phối cảnh, giấy tờ hợp chuẩn / hợp quy.\n"
            "4. Nếu có: thông báo khuyến mại, văn bản quyền sử dụng địa điểm, giấy phép xây dựng.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Khối người nộp giữ nguyên thông tin tài khoản. Chưa tích ô cam kết thì nút 'Lưu và nộp hồ sơ' bị "
            "khoá — tự tích sau khi rà soát."
        ),
    },
    {
        "key": "cap-giay-phep-xuat-ban-tai-lieu-khong-kinh-doanh",
        # Mã TTHC 1.003868, cổng Bộ VHTTDL (liz-*). Khối 'Thông tin doanh nghiệp' là của CƠ SỞ IN, không phải tổ chức
        # đề nghị cấp phép — mapper lõi điền tách hai bên. Bảng đính kèm 4 dòng, không có dòng 'Giấy tờ khác'.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.003868",
                "019d90c9-cee7-727c-a855-ac24b8084e6f",
            ],
        },
        "label": "Cấp giấy phép xuất bản tài liệu không kinh doanh",
        "shortLabel": "Giấy phép xuất bản tài liệu không kinh doanh",
        "subtitle": "Cơ quan, tổ chức xin phép in tài liệu phát hành không thu tiền",
        "icon": "📚",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d90c9-cee7-727c-a855-ac24b8084e6f",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp giấy phép xuất bản tài liệu không kinh doanh (Mẫu số 04)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "ban_thao", "name": "Bản thảo tài liệu sẽ xuất bản", "icon": "📚", "sides": 1,
             "repeatable": True},
            {"key": "co_so_in", "name": "Giấy chứng nhận đăng ký doanh nghiệp và Giấy phép hoạt động in của cơ sở in",
             "icon": "🖨️", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Bản dịch tiếng Việt, văn bản ý kiến của cơ quan có thẩm quyền (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp giấy phép xuất bản tài liệu không kinh doanh (Mẫu số 04) — nguồn chính để điền.\n"
            "2. Bản thảo tài liệu sẽ xuất bản.\n"
            "3. Giấy chứng nhận đăng ký doanh nghiệp và Giấy phép hoạt động in của CƠ SỞ IN — để điền khối "
            "'Thông tin doanh nghiệp'.\n"
            "4. Nếu có: bản dịch tiếng Việt, văn bản nêu ý kiến của cơ quan có thẩm quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bảng đính kèm chỉ có 4 dòng: giấy tờ ngoài danh mục được đưa vào dòng 4 kèm cảnh báo. Tự tích ô cam "
            "kết thì nút 'Lưu và nộp hồ sơ' mới mở."
        ),
    },
    {
        "key": "cap-the-huong-dan-vien-du-lich-noi-dia",
        # Mã TTHC 1.004623, cổng Bộ VHTTDL (liz-*). Auto Fill chạy điền + đính kèm một lượt (fillWithAttach); trợ lý
        # đi hai bước như thường, cùng pipeline process/attach.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.004623",
                "019d7fa4-c5c7-744b-afcf-3c51350aa612",
            ],
            "textIncludes": ["cấp thẻ hướng dẫn viên du lịch nội địa"],
            "headingDisabled": True,
        },
        "label": "Thủ tục cấp thẻ hướng dẫn viên du lịch nội địa",
        "shortLabel": "Cấp thẻ hướng dẫn viên du lịch nội địa",
        "subtitle": "Xin thẻ hướng dẫn viên dẫn khách du lịch trong nước",
        "icon": "🧭",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d7fa4-c5c7-744b-afcf-3c51350aa612",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        # Trang nộp MỘT TRANG (form liz + Thành phần hồ sơ + ô cam kết + ô VNPost + nút "Lưu và nộp hồ sơ"): extension
        # khai supportsLizFlow thì đi luồng trang một trang (chat/tu_phap_moi.py) — một nút điền + đính, bổ sung ô
        # trống, Tiếp tục = tích ô cam kết (nút nộp của cổng chỉ mở sau khi tích) + hỏi bưu điện, rồi nộp. Bản cũ đi
        # luồng chung như trước.
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch nội địa (Mẫu số 04)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "van_bang", "name": "Bằng tốt nghiệp trung cấp trở lên (bản sao chứng thực)", "icon": "🎓",
             "sides": 1, "repeatable": True},
            {"key": "chung_chi", "name": "Chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa (khi văn bằng không thuộc "
             "chuyên ngành hướng dẫn du lịch)", "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "anh", "name": "Ảnh chân dung màu 3x4", "icon": "🖼️", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị (chỉ để điền)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp thẻ hướng dẫn viên du lịch nội địa (Mẫu số 04) — nguồn chính để điền.\n"
            "2. Bản sao chứng thực bằng tốt nghiệp trung cấp trở lên.\n"
            "3. Bản sao chứng thực chứng chỉ nghiệp vụ hướng dẫn du lịch nội địa (khi văn bằng không thuộc chuyên "
            "ngành hướng dẫn du lịch).\n"
            "4. Ảnh chân dung màu 3x4.\n"
            "5. Nếu có: căn cước của người đề nghị — để bổ sung ngày sinh, ngày cấp, địa chỉ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Khối 'Thông tin người nộp hồ sơ' chỉ được điền khi căn cước tài khoản trùng căn cước trên đơn.\n"
            "Bước đính kèm: Đơn → dòng 1; văn bằng + chứng chỉ → dòng 2; ảnh → dòng 3."
        ),
    },
    {
        "key": "cap-chung-chi-hanh-nghe-bao-quan-tu-bo-phuc-hoi-di-tich",
        # Mã TTHC 1.001822 (QT-09), cổng Bộ VHTTDL (liz-*) như thủ tục quảng cáo băng-rôn: nhận diện CẢ trang chi tiết
        # DVCQG (uuid) lẫn trang nộp /nop-ho-so?MaTTHC=1.001822 sau khi bấm "Nộp trực tuyến". ke_khai_links đặt selectSo
        # → DVCQG chọn Tỉnh rồi gạt "Sở". Key TRÙNG lõi → process/attach tự nối qua core_registry.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.001822",
                "019d2bfd-b558-70ee-a2f5-fb4c232b41dd",
            ],
        },
        "label": "Thủ tục cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích",
        "shortLabel": "Cấp chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích",
        "subtitle": "Kiến trúc sư, kỹ sư xin chứng chỉ hành nghề tu bổ di tích",
        "icon": "🏛️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-b558-70ee-a2f5-fb4c232b41dd",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        # Trang nộp MỘT TRANG (form liz + Thành phần hồ sơ + ô cam kết + ô VNPost + nút "Lưu và nộp hồ sơ") → luồng
        # trang một trang (chat/tu_phap_moi.py) như quảng cáo băng-rôn.
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (Mẫu số 51)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "chung_chi_hanh_nghe", "name": "Chứng chỉ hành nghề hoạt động xây dựng / kiến trúc (bản sao chứng "
             "thực)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "van_bang", "name": "Bằng tốt nghiệp đại học (bản sao chứng thực)", "icon": "🎓", "sides": 1,
             "repeatable": True},
            {"key": "anh", "name": "Ít nhất 02 ảnh màu 4x6", "icon": "🖼️", "sides": 1, "repeatable": True},
            {"key": "boi_duong", "name": "Chứng chỉ bồi dưỡng kiến thức bảo quản, tu bổ, phục hồi di tích (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị (chỉ để điền)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (Mẫu số 51) — nguồn chính để "
            "điền.\n"
            "2. Bản sao chứng thực Chứng chỉ hành nghề hoạt động xây dựng / kiến trúc và bằng tốt nghiệp đại học.\n"
            "3. Ít nhất 02 ảnh màu 4x6.\n"
            "4. Nếu có: chứng chỉ bồi dưỡng kiến thức bảo quản, tu bổ, phục hồi di tích; căn cước của người đề nghị.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Tài khoản trùng căn cước người đề nghị thì điền khối người nộp; nộp thay thì điền khối 'Thông tin người "
            "ủy quyền'.\n"
            "Bước đính kèm: Đơn → dòng 1; chứng chỉ hành nghề + bằng + chứng chỉ bồi dưỡng → dòng 2; ảnh → dòng 3."
        ),
    },
    {
        "key": "cap-lai-chung-chi-hanh-nghe-bao-quan-tu-bo-phuc-hoi-di-tich",
        # Mã TTHC 1.002003 (QT-10), cùng cổng Bộ VHTTDL (liz-*) và cùng cơ chế 2 trang với bản cấp mới 1.001822 ngay
        # trên: nhận diện CẢ trang chi tiết DVCQG (uuid) lẫn trang nộp /nop-ho-so?MaTTHC=1.002003. ke_khai_links đặt
        # selectSo → DVCQG chọn Tỉnh rồi gạt "Sở". Key TRÙNG lõi → process/attach tự nối qua core_registry.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.002003",
                "019d2bfd-b5a1-72a9-a768-957fc952b946",
            ],
        },
        "label": "Thủ tục cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích",
        "shortLabel": "Cấp lại chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích",
        "subtitle": "Chứng chỉ tu bổ di tích hết hạn, hỏng, mất hoặc cần bổ sung nội dung",
        "icon": "🏛️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-b5a1-72a9-a768-957fc952b946",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (Mẫu số "
             "51)", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "chung_chi_da_cap", "name": "Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích đã được cấp",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "anh", "name": "Ít nhất 02 ảnh màu 4x6", "icon": "🖼️", "sides": 1, "repeatable": True},
            {"key": "van_bang", "name": "Bản sao văn bằng, chứng chỉ (trường hợp bổ sung nội dung hành nghề)",
             "icon": "🎓", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị (chỉ để điền)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích (Mẫu số 51) — nguồn chính "
            "để điền.\n"
            "2. Chứng chỉ hành nghề đã được cấp.\n"
            "3. Ít nhất 02 ảnh màu 4x6.\n"
            "4. Nếu có: bản sao văn bằng, chứng chỉ (khi bổ sung nội dung hành nghề); căn cước của người đề nghị.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Tài khoản trùng căn cước người đề nghị thì điền khối người nộp; nộp thay thì điền khối 'Thông tin người "
            "ủy quyền'.\n"
            "Bước đính kèm: Đơn → dòng 1; chứng chỉ đã cấp + văn bằng, chứng chỉ khác → dòng 2; ảnh → dòng 3."
        ),
    },
    {
        "key": "to-chuc-bieu-dien-nghe-thuat",
        # Mã TTHC 1.009397 (NĐ 144/2020/NĐ-CP), cùng cổng Bộ VHTTDL (liz-*) và cùng cơ chế 2 trang với CCHN di tích
        # ngay trên: nhận diện CẢ trang chi tiết DVCQG (uuid) lẫn trang nộp /nop-ho-so?MaTTHC=1.009397. ke_khai_links
        # đặt selectSo → DVCQG chọn Tỉnh rồi gạt "Sở". Key TRÙNG lõi → process/attach tự nối qua core_registry.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.009397",
                "019d2bfd-e44a-7705-a455-6f7239cfe9de",
            ],
        },
        "label": "Thủ tục tổ chức biểu diễn nghệ thuật",
        "shortLabel": "Tổ chức biểu diễn nghệ thuật",
        "subtitle": "Công ty, đơn vị nghệ thuật xin tổ chức chương trình biểu diễn",
        "icon": "🎭",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-e44a-7705-a455-6f7239cfe9de",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "van_ban_de_nghi", "name": "Văn bản đề nghị tổ chức biểu diễn nghệ thuật (Mẫu số 02)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "kich_ban", "name": "Kịch bản, danh mục tác phẩm gắn với tác giả, người chịu trách nhiệm chính về "
             "nội dung", "icon": "🎼", "sides": 1, "repeatable": True},
            {"key": "gcn_dkdn", "name": "Giấy chứng nhận đăng ký doanh nghiệp (nếu có)", "icon": "🏢", "sides": 1,
             "optional": True, "repeatable": True},
            {"key": "giay_tiep_nhan", "name": "Giấy tiếp nhận / chấp thuận địa điểm biểu diễn (nếu có)", "icon": "📍",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Văn bản đề nghị tổ chức biểu diễn nghệ thuật (Mẫu số 02) — nguồn chính để điền.\n"
            "2. Kịch bản, danh mục tác phẩm gắn với tác giả, người chịu trách nhiệm chính về nội dung.\n"
            "3. Nếu có: Giấy chứng nhận đăng ký doanh nghiệp, giấy tiếp nhận địa điểm biểu diễn.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Tổ chức đề nghị được điền vào khối 'Thông tin người ủy quyền'.\n"
            "Bước đính kèm: Văn bản đề nghị + giấy tờ kèm theo → dòng 1; Kịch bản → dòng 2."
        ),
    },
    {
        "key": "cap-giay-chung-nhan-khoa-cap-nhat-kien-thuc-huong-dan-vien-du-lich",
        # Mã TTHC 1.004605 (QT-123), cùng cổng Bộ VHTTDL (liz-*) và cùng cơ chế 2 trang với thẻ HDV nội địa / CCHN di
        # tích ở trên: nhận diện CẢ trang chi tiết DVCQG (uuid) lẫn trang nộp /nop-ho-so?MaTTHC=1.004605. ke_khai_links
        # đặt selectSo → DVCQG chọn Tỉnh rồi gạt "Sở". Key TRÙNG lõi → process/attach tự nối qua core_registry.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.004605",
                "019d2bfd-d4aa-756f-b5fc-8a172aa4633a",
            ],
        },
        "label": (
            "Thủ tục cấp Giấy chứng nhận khóa cập nhật kiến thức cho hướng dẫn viên du lịch nội địa và hướng dẫn viên "
            "du lịch quốc tế"
        ),
        "shortLabel": "Cấp giấy chứng nhận khóa cập nhật kiến thức hướng dẫn viên du lịch",
        "subtitle": "Hướng dẫn viên đã có thẻ đăng ký học lớp cập nhật kiến thức",
        "icon": "🧭",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-d4aa-756f-b5fc-8a172aa4633a",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đăng ký tham dự khóa cập nhật kiến thức cho hướng dẫn viên du lịch (Mẫu số 06)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đăng ký (chỉ để điền)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "the_hdv", "name": "Thẻ hướng dẫn viên du lịch đã được cấp (chỉ để điền)", "icon": "🪪",
             "sides": 2, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đăng ký tham dự khóa cập nhật kiến thức cho hướng dẫn viên du lịch (Mẫu số 06) đã ký — nguồn chính để "
            "điền.\n"
            "2. Nếu có: căn cước, thẻ hướng dẫn viên của người đăng ký — chỉ để điền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Tài khoản trùng người đăng ký (căn cước, hoặc họ tên khi đơn chưa có số thật) thì điền khối người nộp; nộp "
            "thay thì điền khối 'Thông tin người ủy quyền'.\n"
            "Bước đính kèm: Đơn → dòng 1."
        ),
    },
    {
        "key": "cap-the-huong-dan-vien-du-lich-tai-diem-da-nang",
        # Mã TTHC 1.001440 (QT-115), cùng cổng Bộ VHTTDL (liz-*) và cùng cơ chế 2 trang với thẻ HDV nội địa 1.004623:
        # nhận diện CẢ trang chi tiết DVCQG (uuid) lẫn trang nộp /nop-ho-so?MaTTHC=1.001440. ke_khai_links đặt selectSo
        # → DVCQG chọn Tỉnh rồi gạt "Sở". Key TRÙNG lõi → process/attach tự nối qua core_registry. Nhãn không gắn tỉnh
        # (cổng bộ dùng chung cả nước) dù key lõi có đuôi "-da-nang".
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.001440",
                "019d2bfd-b526-75c8-a04d-beec224973cf",
            ],
        },
        "label": "Thủ tục cấp thẻ hướng dẫn viên du lịch tại điểm",
        "shortLabel": "Cấp thẻ hướng dẫn viên du lịch tại điểm",
        "subtitle": "Xin thẻ hướng dẫn viên dẫn khách tại một khu, điểm du lịch",
        "icon": "🧭",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-b526-75c8-a04d-beec224973cf",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch tại điểm (Mẫu số 06) — ghi tên điểm du "
             "lịch", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "anh", "name": "02 ảnh chân dung màu 3x4", "icon": "🖼️", "sides": 1, "repeatable": True},
            {"key": "chung_chi", "name": "Giấy chứng nhận / chứng chỉ nghiệp vụ hướng dẫn du lịch tại điểm, văn bằng "
             "(nếu có)", "icon": "📜", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị (chỉ để điền)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp thẻ hướng dẫn viên du lịch tại điểm (Mẫu số 06) — nguồn chính để điền; đơn phải ghi "
            "tên điểm du lịch.\n"
            "2. 02 ảnh chân dung màu 3x4.\n"
            "3. Nếu có: chứng chỉ nghiệp vụ hướng dẫn du lịch, văn bằng, căn cước của người đề nghị.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Khối 'Thông tin người nộp hồ sơ' chỉ được điền khi căn cước tài khoản trùng căn cước người đề nghị.\n"
            "Bước đính kèm: Đơn + chứng chỉ, văn bằng → dòng 1; ảnh → dòng 2."
        ),
    },
    {
        "key": "cap-doi-the-huong-dan-vien-du-lich-da-nang",
        # Mã TTHC 1.001432 (QT-113), cùng cổng Bộ VHTTDL (liz-*) và cùng cơ chế 2 trang với thẻ HDV nội địa ở trên.
        # ke_khai_links đặt selectSo → DVCQG chọn Tỉnh rồi gạt "Sở". Key TRÙNG lõi → process/attach tự nối.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.001432",
                "019d90c7-0901-71cb-ab99-2f6e20b9ce08",
            ],
        },
        "label": "Thủ tục cấp đổi thẻ hướng dẫn viên du lịch quốc tế, thẻ hướng dẫn viên du lịch nội địa",
        "shortLabel": "Cấp đổi thẻ hướng dẫn viên du lịch",
        "subtitle": "Thẻ hướng dẫn viên nội địa, quốc tế sắp hết hạn cần đổi thẻ mới",
        "icon": "🧭",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d90c7-0901-71cb-ab99-2f6e20b9ce08",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp đổi thẻ hướng dẫn viên du lịch (Mẫu số 05)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "the_hdv", "name": "Thẻ hướng dẫn viên du lịch đã được cấp", "icon": "🪪", "sides": 2,
             "repeatable": True},
            {"key": "gcn_cap_nhat", "name": "Giấy chứng nhận đã qua khóa cập nhật kiến thức hướng dẫn viên du lịch "
             "(bản sao chứng thực)", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "anh", "name": "01 ảnh chân dung màu 3x4", "icon": "🖼️", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị (chỉ để điền)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp đổi thẻ hướng dẫn viên du lịch (Mẫu số 05) — nguồn chính để điền: số thẻ, nơi cấp, "
            "ngày cấp, loại thẻ, lý do.\n"
            "2. Thẻ hướng dẫn viên du lịch đang có.\n"
            "3. Bản sao chứng thực Giấy chứng nhận đã qua khóa cập nhật kiến thức.\n"
            "4. 01 ảnh chân dung màu 3x4.\n"
            "5. Nếu có: căn cước của người đề nghị.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Khối 'Thông tin người nộp hồ sơ' chỉ được điền khi căn cước tài khoản trùng căn cước người đề nghị.\n"
            "Bước đính kèm: giấy chứng nhận cập nhật kiến thức → dòng 1; thẻ đã cấp → dòng 2; Đơn → dòng 3; ảnh → "
            "dòng 4."
        ),
    },
    {
        "key": "cap-lai-the-huong-dan-vien-du-lich-da-nang",
        # Mã TTHC 1.004614 (QT-122), cùng cổng Bộ VHTTDL (liz-*) và cùng cơ chế 2 trang với cấp đổi ngay trên.
        # ke_khai_links đặt selectSo → DVCQG chọn Tỉnh rồi gạt "Sở". Key TRÙNG lõi → process/attach tự nối.
        "detect": {
            "urlScope": ["dichvucong.bvhttdl.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "matthc=1.004614",
                "019d7fa0-f695-75df-8834-aa4c22e41529",
            ],
        },
        "label": "Thủ tục cấp lại thẻ hướng dẫn viên du lịch",
        "shortLabel": "Cấp lại thẻ hướng dẫn viên du lịch",
        "subtitle": "Thẻ hướng dẫn viên bị mất, hỏng hoặc cần thay đổi thông tin",
        "icon": "🧭",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d7fa0-f695-75df-8834-aa4c22e41529",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Văn hóa, Thể thao và Du lịch",
        "lizFlow": _LIZ_FLOW,
        "guidedSteps": _LIZ_GUIDED_STEPS,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp lại thẻ hướng dẫn viên du lịch (Mẫu số 05)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "anh", "name": "01 ảnh chân dung màu 3x4", "icon": "🖼️", "sides": 1, "repeatable": True},
            {"key": "giay_to_thay_doi", "name": "Bản sao chứng thực giấy tờ liên quan đến nội dung thay đổi (khi cấp "
             "lại để thay đổi thông tin trên thẻ)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị (chỉ để điền)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp lại thẻ hướng dẫn viên du lịch (Mẫu số 05) — nguồn chính để điền: số thẻ, nơi cấp, "
            "ngày cấp, loại thẻ, lý do.\n"
            "2. 01 ảnh chân dung màu 3x4.\n"
            "3. Khi cấp lại để thay đổi thông tin trên thẻ: bản sao chứng thực giấy tờ liên quan đến nội dung thay "
            "đổi.\n"
            "4. Nếu có: căn cước của người đề nghị.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Khối 'Thông tin người nộp hồ sơ' chỉ được điền khi căn cước tài khoản trùng căn cước người đề nghị.\n"
            "Bước đính kèm: giấy tờ thay đổi và giấy tờ khác → dòng 1; Đơn → dòng 2; ảnh → dòng 3. Căn cước không "
            "đính."
        ),
    },
    {
        "key": "gia-han-giay-phep-xay-dung",
        "flowProfile": "xay-dung",
        # Mã TTHC 1.013227, cổng Bộ Xây dựng — cùng stepper và ô receivingKind với điều chỉnh GPXD ngay trên, cấp xã
        # như điều chỉnh. GCN quyền sử dụng đất thành dòng mới qua "+ Thêm giấy tờ" (add-document-dialog).
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "label": (
            "Gia hạn giấy phép xây dựng đối với công trình cấp III, cấp IV (công trình Không theo tuyến/Theo tuyến "
            "trong đô thị/Tín ngưỡng, tôn giáo/Tượng đài, tranh hoành tráng/Sửa chữa, cải tạo/Theo giai đoạn cho "
            "công trình không theo tuyến/Theo giai đoạn cho công trình theo tuyến trong đô thị/Dự án) và nhà ở "
            "riêng lẻ"
        ),
        "shortLabel": "Gia hạn giấy phép xây dựng",
        "subtitle": "Xin thêm thời gian khởi công khi giấy phép xây dựng sắp hết hạn",
        "icon": "🏗️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-9097-700f-899f-6dfc532f0e6b",
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị gia hạn giấy phép xây dựng (Mẫu số 02) — đã ký", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của chủ hộ (hai vợ chồng thì đủ cả hai)", "icon": "🪪",
             "sides": 2, "repeatable": True},
            {"key": "gpxd", "name": "Giấy phép xây dựng đã được cấp (bản chính, đủ các trang)", "icon": "📑",
             "sides": 1, "repeatable": True},
            {"key": "gcn_qsdd", "name": "Giấy chứng nhận quyền sử dụng đất (đủ trang, gồm trang những thay đổi)",
             "icon": "🏠", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị gia hạn giấy phép xây dựng (Mẫu số 02), đã ký — nguồn chính để điền.\n"
            "2. Căn cước công dân 2 mặt của chủ hộ (hai vợ chồng thì đủ cả hai) — có thể gộp chung file với Đơn.\n"
            "3. Bản chính Giấy phép xây dựng đã được cấp (đủ các trang).\n"
            "4. Giấy chứng nhận quyền sử dụng đất (đủ trang, gồm trang 'Những thay đổi sau khi cấp').\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Đơn + căn cước → dòng 1; giấy phép xây dựng → dòng 2; giấy chứng nhận quyền sử dụng "
            "đất thành dòng mới qua '+ Thêm giấy tờ'."
        ),
    },
    {
        "key": "cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham",
        # Mã TTHC 2.000535, cổng Bộ Công Thương (bảng attp-row). Key TRÙNG lõi và ke_khai_links; uuid + mã
        # vẫn khai tay ở đây; ke_khai khai selectSo → Sở Công Thương.
        "detect": {
            "textIncludes": [
                "Cấp lại Giấy chứng nhận đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, kinh doanh thực phẩm",
            ],
            "urlIncludes": ["019d2bf8-32f5-71a9-8925-3524dc3d03fd"],
            "headingDisabled": True,
        },
        "code": "2.000535",
        "label": "Cấp lại Giấy chứng nhận đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, kinh doanh thực phẩm",
        "shortLabel": "Cấp lại giấy chứng nhận an toàn thực phẩm (Sở Công Thương)",
        "subtitle": "Cơ sở sản xuất, kinh doanh thực phẩm xin cấp lại giấy chứng nhận còn hạn",
        "icon": "🍱",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf8-32f5-71a9-8925-3524dc3d03fd",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Công Thương",
        # Cổng Bộ Công Thương cùng stepper iGate 4 bước với cổng NN&MT (1 Thông tin hồ sơ = kê khai, 2 Thành phần hồ
        # sơ): extension báo wizardStep trên host này → khai đúng bước, không thì BE hiểu theo mặc định tư pháp.
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp lại Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn_cu", "name": "Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm đã được cấp",
             "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy đăng ký doanh nghiệp, thuyết minh cơ sở vật chất, giấy tập huấn, giấy "
             "sức khỏe, giấy ủy quyền (nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp lại Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm.\n"
            "2. Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm đã được cấp.\n"
            "3. Nếu có: giấy đăng ký doanh nghiệp / địa điểm kinh doanh, bản thuyết minh cơ sở vật chất, giấy xác "
            "nhận tập huấn an toàn thực phẩm, giấy xác nhận đủ sức khỏe, giấy ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung."
        ),
    },
    {
        "key": "cap-gcn-attp-cong-thuong",
        # Mã TTHC 2.000591, bản CẤP LẦN ĐẦU của thủ tục cấp lại ngay trên — cùng cổng Bộ Công Thương, cùng cách chọn
        # cơ quan (ke_khai selectSo → Sở Công Thương). Key TRÙNG lõi và ke_khai_links → process/attach tự nối. Tiêu đề
        # chỉ khác bản cấp lại chữ "lại" → khai uuid + textPriority. maePortal chỉ chạy khi extension báo trang "Cơ
        # quan thực hiện" (maeAgencyBlock) như bản khuyến mại; không có ô "Trường hợp giải quyết".
        "detect": {
            "urlScope": ["dichvucong-tthc.moit.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["019d2bf8-330c-77dd-8058-19a40f5959f5"],
            "textIncludes": [
                "Cấp Giấy chứng nhận đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, kinh doanh thực phẩm",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "2.000591",
        "label": "Cấp Giấy chứng nhận đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, kinh doanh thực phẩm",
        "shortLabel": "Cấp giấy chứng nhận an toàn thực phẩm (Sở Công Thương)",
        "subtitle": "Cơ sở sản xuất, kinh doanh thực phẩm xin cấp giấy chứng nhận lần đầu",
        "icon": "🍱",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf8-330c-77dd-8058-19a40f5959f5",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Công Thương",
        "maePortal": True,
        "maeNoProcess": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        # Bảng thành phần hồ sơ 5 dòng cố định (planner lõi attp-row: Đơn 01a / Thuyết minh / GCN ĐKKD / tập huấn /
        # sức khỏe); căn cước, giấy ủy quyền đính chung dòng Đơn.
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm (Mẫu số 01a) "
             "— đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "thuyet_minh", "name": "Bản thuyết minh về cơ sở vật chất, trang thiết bị, dụng cụ (Mẫu 02a/02b)",
             "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "dkkd", "name": "Bản sao Giấy chứng nhận đăng ký kinh doanh / doanh nghiệp / hộ kinh doanh",
             "icon": "🏪", "sides": 1, "repeatable": True},
            {"key": "tap_huan", "name": "Giấy xác nhận đã được tập huấn kiến thức về an toàn thực phẩm", "icon": "📋",
             "sides": 1, "repeatable": True},
            {"key": "suc_khoe", "name": "Danh sách tổng hợp / giấy xác nhận đủ sức khỏe của chủ cơ sở và người trực "
             "tiếp sản xuất, kinh doanh", "icon": "🩺", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nộp hồ sơ, thêm giấy ủy quyền nếu nộp thay",
             "icon": "🪪", "sides": 2, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm (Mẫu số 01a), đã ký — nguồn "
            "chính để điền.\n"
            "2. Bản thuyết minh về cơ sở vật chất, trang thiết bị, dụng cụ (Mẫu 02a/02b).\n"
            "3. Giấy chứng nhận đăng ký kinh doanh / doanh nghiệp / hộ kinh doanh — tên cơ sở, mã số, địa chỉ, ngành "
            "nghề.\n"
            "4. Giấy xác nhận đã tập huấn kiến thức an toàn thực phẩm; danh sách / giấy xác nhận đủ sức khỏe.\n"
            "5. Căn cước của người nộp hồ sơ; nộp thay thì thêm giấy ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Đơn / Thuyết minh / Giấy đăng ký kinh doanh / Giấy tập huấn / Danh sách sức khỏe vào 5 "
            "dòng tương ứng; căn cước, giấy ủy quyền đính chung dòng Đơn."
        ),
    },
    {
        "key": "thong-bao-sua-doi-bo-sung-noi-dung-chuong-trinh-khuyen-mai",
        # Mã TTHC 2.001474, cổng Bộ Công Thương (attp-row MỘT dòng — mọi tệp đính vào đó). ke_khai_links ghi key khác
        # ("thong-bao-sua-doi-bo-sung-chuong-trinh-khuyen-mai") → khai tay uuid + mã; ke_khai khai selectSo.
        "detect": {
            "urlScope": ["dichvucong-tthc.moit.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["019d2bf8-428e-76a8-a8e8-65eee3365b73"],
            "textIncludes": ["2.001474", "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "2.001474",
        "label": "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại",
        "shortLabel": "Sửa đổi, bổ sung chương trình khuyến mại",
        "subtitle": "Thương nhân thông báo thay đổi chương trình khuyến mại đã đăng ký",
        "icon": "🎁",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf8-428e-76a8-a8e8-65eee3365b73",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Công Thương",
        # Sang cổng bộ còn trang "Cơ quan thực hiện" form#ngSelectAgencyForm1 (cùng component Bộ Nội vụ): chọn Tỉnh
        # thì cổng tự điền Sở Công Thương → bấm "Đồng ý và tiếp tục" = nhánh maePortal. Không có ô "Trường hợp giải
        # quyết" nên không khai variants; maeNoProcess báo extension khỏi chờ ô đó.
        "maePortal": True,
        "maeNoProcess": True,
        # Cổng Bộ Công Thương cùng stepper iGate 4 bước với cổng NN&MT (1 Thông tin hồ sơ = kê khai, 2 Thành phần hồ
        # sơ): extension báo wizardStep trên host này → khai đúng bước, không thì BE hiểu theo mặc định tư pháp.
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Dẫn đủ 4 bước (bổ sung ô → Thành phần hồ sơ → hình thức nhận kết quả → nộp) bằng luồng chung chat/bxd như
        # thủ tục điện mặt trời mái nhà cùng cổng; bản extension cũ chưa đọc Form.io trên host này → cờ riêng.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMoit",
        },
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "thong_bao", "name": "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại (Mẫu 06, bản "
             "đã ký số)", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đang đăng nhập nộp hồ sơ (nếu muốn điền khối tài "
             "khoản)", "icon": "🪪", "sides": 2, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại (Mẫu 06, bản đã ký số) — nguồn chính.\n"
            "2. Nếu muốn điền khối thông tin tài khoản: căn cước của chính người đang đăng nhập nộp hồ sơ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: mọi tệp đính vào dòng 'Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại', "
            "giữ nguyên tên tệp."
        ),
    },
    {
        "key": "dang-ky-khuyen-mai-may-rui-mot-tinh",
        # Mã TTHC 2.000004, cùng cổng Bộ Công Thương + cùng khuôn với 2.001474 ngay trên (attp-row 3 dòng: Đăng ký /
        # Thể lệ / Mẫu bằng chứng trúng thưởng). Key TRÙNG lõi và ke_khai_links (link thêm 10/11, uuid tra từ API DVCQG)
        # → process/attach + URL tự nối; ke_khai khai selectSo.
        "detect": {
            "urlScope": ["dichvucong-tthc.moit.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["019d2bf8-1b67-7594-877d-bcc66b5f4fd8"],
            "textIncludes": [
                "2.000004",
                "Đăng ký hoạt động khuyến mại đối với chương trình khuyến mại mang tính may rủi",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "2.000004",
        "label": (
            "Đăng ký hoạt động khuyến mại đối với chương trình khuyến mại mang tính may rủi thực hiện trên địa bàn 01 "
            "tỉnh, thành phố trực thuộc Trung ương"
        ),
        "shortLabel": "Đăng ký khuyến mại may rủi (bốc thăm, cào trúng thưởng)",
        "subtitle": "Thương nhân đăng ký chương trình bốc thăm, quay số trúng thưởng trong tỉnh",
        "icon": "🎁",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf8-1b67-7594-877d-bcc66b5f4fd8",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Công Thương",
        # Cùng trang "Cơ quan thực hiện" + stepper iGate 4 bước + cờ riêng như 2.001474 ngay trên.
        "maePortal": True,
        "maeNoProcess": True,
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMoit",
        },
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "dang_ky", "name": "Đăng ký thực hiện khuyến mại (Mẫu số 02 ĐP, đã ký, đóng dấu)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "the_le", "name": "Thể lệ chương trình khuyến mại (Mẫu số 03 ĐP)", "icon": "📜", "sides": 1,
             "repeatable": True},
            {"key": "mau_bang_chung", "name": "Mẫu bằng chứng xác định trúng thưởng (phiếu bốc thăm, thẻ cào…)",
             "icon": "🎟️", "sides": 1, "repeatable": True},
            {"key": "chat_luong", "name": "Giấy tờ về chất lượng hàng hóa dùng để khuyến mại (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đang đăng nhập nộp hồ sơ (nếu muốn điền khối tài "
             "khoản)", "icon": "🪪", "sides": 2, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đăng ký thực hiện khuyến mại (Mẫu số 02 ĐP, đã ký, đóng dấu) — nguồn chính để điền.\n"
            "2. Thể lệ chương trình khuyến mại (Mẫu số 03 ĐP).\n"
            "3. Mẫu bằng chứng xác định trúng thưởng (mẫu phiếu bốc thăm / thẻ cào).\n"
            "4. Nếu có: giấy tờ về chất lượng hàng hóa dùng để khuyến mại.\n"
            "5. Nếu muốn điền khối thông tin tài khoản: căn cước của chính người đang đăng nhập nộp hồ sơ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Đăng ký / Thể lệ / Mẫu bằng chứng vào 3 dòng tương ứng; giấy tờ chất lượng hàng hóa và "
            "giấy tờ khác đính chung dòng Đăng ký. Giữ nguyên tên tệp."
        ),
    },
    {
        "key": "thong-bao-phat-trien-nguon-dien-mat-troi-mai-nha",
        # Mã TTHC 1.115377, cổng một cửa Bộ Công Thương, tiếp nhận ở UBND cấp xã (DVCQG chọn Tỉnh + Xã). Bản vẽ và tài
        # liệu công trình thành dòng mới qua "+ Thêm giấy tờ" (add-document-dialog).
        "detect": {
            "urlIncludes": ["019f1695-894f-72b8-80a8-2fee368722be"],
            "textIncludes": ["Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất", "cấp điện áp hạ áp"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu thụ đấu nối với hệ thống điện "
            "quốc gia tại cấp điện áp hạ áp"
        ),
        "shortLabel": "Thông báo lắp điện mặt trời mái nhà",
        "subtitle": "Hộ gia đình, tổ chức lắp điện mặt trời mái nhà tự dùng, đấu nối lưới hạ áp",
        "icon": "☀️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f1695-894f-72b8-80a8-2fee368722be",
        "needsAgencySelect": True,
        # Cổng Bộ Công Thương cùng stepper iGate 4 bước với cổng NN&MT (1 Thông tin hồ sơ = kê khai, 2 Thành phần hồ
        # sơ, 3 Thông tin phí, lệ phí = hình thức nhận kết quả + cam đoan + mã xác nhận) → dẫn đủ 4 bước bằng luồng
        # chung chat/bxd. Bản extension cũ chưa chạy bộ đọc Form.io của chat/bxd trên host này → cần cờ
        # supportsBxdFlowMoit.
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMoit",
        },
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "thong_bao", "name": "Thông báo phát triển nguồn điện mặt trời mái nhà (Mẫu số 01) — đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "ban_ve", "name": "Bản vẽ thiết kế lắp đặt nguồn điện", "icon": "📐", "sides": 1,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đứng tên hoặc người đại diện", "icon": "🪪",
             "sides": 2, "repeatable": True},
            {"key": "khac", "name": "Giấy chứng nhận quyền sử dụng đất, giấy phép xây dựng, nghiệm thu PCCC, hình "
             "ảnh, chứng từ thiết bị (nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Thông báo phát triển nguồn điện mặt trời mái nhà (Mẫu số 01 Phụ lục III), đã ký — nguồn chính.\n"
            "2. Bản vẽ thiết kế lắp đặt nguồn điện.\n"
            "3. Căn cước của người đứng tên (cá nhân) hoặc người đại diện (tổ chức / hộ kinh doanh).\n"
            "4. Nếu có: giấy chứng nhận quyền sử dụng đất, giấy phép xây dựng, nghiệm thu PCCC; hình ảnh dự án; "
            "chứng từ thiết bị.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Thông báo vào dòng Mẫu số 01; bản vẽ và tài liệu công trình thêm dòng qua '+ Thêm giấy "
            "tờ' (không thêm được thì đính chung dòng Thông báo)."
        ),
    },
    {
        "key": "xet-tuyen-vien-chuc",
        # Mã 3.000601. Bước đính kèm chỉ có ô Phiếu đăng ký dự tuyển (slot 0); căn cước chỉ để đối chiếu người nộp.
        "detect": {
            "urlIncludes": ["019f1834-0004-71bd-abd7-6c634065e005"],
            "textIncludes": ["Thủ tục xét tuyển Viên chức (85/2023/NĐ-CP)"],
            "headingDisabled": True,
        },
        "label": "Thủ tục xét tuyển Viên chức (85/2023/NĐ-CP)",
        "shortLabel": "Xét tuyển viên chức",
        "subtitle": "Nộp phiếu đăng ký dự tuyển viên chức",
        "icon": "👩‍💼",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f1834-0004-71bd-abd7-6c634065e005",
        "needsAgencySelect": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "phieu_du_tuyen", "name": "Phiếu đăng ký dự tuyển (Mẫu số 01)", "icon": "📄", "sides": 1,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước của người nộp hồ sơ (khi khác người dự tuyển)", "icon": "🪪",
             "sides": 2, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu đăng ký dự tuyển theo Mẫu số 01.\n"
            "2. Nếu người nộp khác người dự tuyển: căn cước của người nộp hồ sơ.\n"
            "Hệ thống lấy chủ hồ sơ từ phiếu đăng ký, rồi so với thông tin người nộp trên form.\n"
            "Bước đính kèm: chỉ đính Phiếu đăng ký dự tuyển."
        ),
    },
    {
        "key": "xet-tuyen-cong-chuc",
        # Mã TTHC 1.014113. Bảng đính kèm ô cố định, planner chỉ đính Phiếu đăng ký dự tuyển.
        "detect": {
            "urlIncludes": ["019d2bfb-2326-7367-83e6-f242eef7cbc5"],
            "textIncludes": ["Xét tuyển công chức"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Xét tuyển công chức",
        "shortLabel": "Xét tuyển công chức",
        "subtitle": "Nộp phiếu đăng ký dự tuyển công chức theo hình thức xét tuyển",
        "icon": "🧑‍💼",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-2326-7367-83e6-f242eef7cbc5",
        "needsAgencySelect": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "phieu_du_tuyen", "name": "Phiếu đăng ký dự tuyển (Mẫu số 01)", "icon": "📄", "sides": 1,
             "repeatable": True},
            {"key": "khac", "name": "Căn cước / giấy tờ khác theo yêu cầu của cơ quan tuyển dụng (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu đăng ký dự tuyển theo Mẫu số 01.\n"
            "2. Nếu có: căn cước / giấy tờ định danh hoặc tài liệu khác theo yêu cầu của cơ quan tuyển dụng.\n"
            "Hệ thống lấy người nộp, chủ hồ sơ và toàn bộ mẫu khai chi tiết từ Phiếu đăng ký dự tuyển.\n"
            "Bước đính kèm: chỉ đính Phiếu đăng ký dự tuyển."
        ),
    },
    {
        "key": "thi-tuyen-cong-chuc",
        # Mã TTHC 1.014111. KHÁC "thi-tuyen-cong-chuc-mot-cua-moha" của Auto Fill (cổng Một cửa Bộ Nội vụ).
        "detect": {
            "urlIncludes": ["019d90b5-0f50-773c-88d5-07d6ef77b613"],
            "textIncludes": ["Thi tuyển công chức"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thi tuyển công chức",
        "shortLabel": "Thi tuyển công chức",
        "subtitle": "Nộp phiếu đăng ký dự thi tuyển công chức",
        "icon": "📝",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d90b5-0f50-773c-88d5-07d6ef77b613",
        "needsAgencySelect": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "phieu_du_tuyen", "name": "Phiếu đăng ký dự tuyển (Mẫu số 01)", "icon": "📄", "sides": 1,
             "repeatable": True},
            {"key": "khac", "name": "Căn cước / giấy tờ khác theo yêu cầu của cơ quan tuyển dụng (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu đăng ký dự tuyển theo Mẫu số 01.\n"
            "2. Nếu có: căn cước / giấy tờ định danh hoặc tài liệu khác theo yêu cầu của cơ quan tuyển dụng.\n"
            "Hệ thống lấy người nộp, chủ hồ sơ và toàn bộ mẫu khai chi tiết từ Phiếu đăng ký dự tuyển.\n"
            "Bước đính kèm: chỉ đính Phiếu đăng ký dự tuyển."
        ),
    },
    {
        "key": "gia-han-chung-chi-hanh-nghe-thu-y",
        # Mã TTHC 2.001064, cổng NN&MT, CÙNG khung chọn cơ quan với "cap-lai-chung-chi-hanh-nghe-thu-y": ke_khai_links
        # khai provinceOnlyAgency + selectSo → DVCQG chỉ chọn Tỉnh, trang MAE chọn Sở NN&MT. Văn bằng thành dòng mới qua
        # "+ Thêm giấy tờ" (add-document-dialog); dòng 'Giấy phép lao động' (người nước ngoài) planner bỏ tick.
        "detect": {
            "urlScope": ["dichvucongnnmt.mae.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "MaTTHC=2.001064",
                "019d2bfa-a5c7-766f-af92-cdc33555359c",
            ],
            "textIncludes": ["gia hạn chứng chỉ hành nghề thú y"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Gia hạn Chứng chỉ hành nghề thú y",
        "shortLabel": "Gia hạn chứng chỉ hành nghề thú y",
        "subtitle": "Gia hạn chứng chỉ hành nghề thú y sắp hoặc đã hết hiệu lực",
        "icon": "🐄",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-a5c7-766f-af92-cdc33555359c",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nông nghiệp và Môi trường",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        # Dẫn đủ 4 bước bằng luồng chung chat/bxd như các thủ tục khác của cổng NN&MT; bản extension cũ chưa chạy
        # bộ đọc Form.io của chat/bxd trên host này → cần cờ supportsBxdFlowMae.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
            "capability": "supportsBxdFlowMae",
        },
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký gia hạn Chứng chỉ hành nghề thú y (Mẫu 02.HNTY) — đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "suc_khoe", "name": "Giấy khám sức khỏe (bản chính)", "icon": "🩺", "sides": 1,
             "repeatable": True},
            {"key": "van_bang", "name": "Văn bằng / chứng chỉ chuyên môn (bản sao chứng thực)", "icon": "🎓",
             "sides": 1, "repeatable": True},
            {"key": "cchn_cu", "name": "Chứng chỉ hành nghề thú y đã cấp", "icon": "🐄", "sides": 1,
             "repeatable": True},
            {"key": "cccd", "name": "Căn cước của người đứng đơn, thêm căn cước người nộp nếu nộp thay (chỉ để "
             "điền)", "icon": "🪪", "sides": 2, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (của NGƯỜI ĐỨNG ĐƠN — người được gia hạn chứng chỉ):\n"
            "1. Đơn đăng ký gia hạn Chứng chỉ hành nghề thú y (Mẫu 02.HNTY), đã ký — nguồn chính để điền.\n"
            "2. Giấy khám sức khỏe (bản chính).\n"
            "3. Văn bằng / chứng chỉ chuyên môn (bản sao chứng thực).\n"
            "4. Chứng chỉ hành nghề thú y đã cấp — để lấy số đăng ký và ngày hết hiệu lực.\n"
            "5. Căn cước của người đứng đơn; người khác nộp thay thì thêm căn cước người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước Thành phần hồ sơ: Giấy khám sức khỏe → dòng 'Giấy chứng nhận sức khỏe'; Đơn → dòng 'Đơn đăng ký "
            "gia hạn'; văn bằng thêm dòng qua '+ Thêm giấy tờ'; căn cước chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "xoa-dang-ky-tau-ca",
        # Mã TTHC 1.003681, cổng NN&MT, CÙNG khung chọn cơ quan với "cap-gcn-dang-ky-tau-ca" (provinceOnlyAgency →
        # DVCQG chỉ chọn Tỉnh, trang MAE chọn Sở NN&MT). attp-row 4 dòng Mẫu 10/11/12/13.ĐKT; hợp đồng, GCN cũ, căn
        # cước tách riêng thêm dòng qua "Thêm giấy tờ".
        "detect": {
            "urlScope": ["dichvucongnnmt.mae.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": [
                "019d2bfa-286c-7701-adcc-2ef71bbbe72e",
                "apply-online/69394b62da87c4718eca03a3",
                "process=6a588c510c8bb839cdfb06c8",
            ],
            "textIncludes": ["xóa đăng ký tàu cá"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Xóa đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản",
        "shortLabel": "Xóa đăng ký tàu cá",
        "subtitle": "Xóa đăng ký tàu cá đã bán, chuyển nhượng, hỏng hoặc không còn sử dụng",
        "icon": "🚢",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfa-286c-7701-adcc-2ef71bbbe72e",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "maePortal": True,
        "agencyDeptLabel": "Sở Nông nghiệp và Môi trường",
        "wizard": {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4},
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai xóa đăng ký tàu cá (Mẫu số 10.ĐKT)", "icon": "📄", "sides": 1,
             "repeatable": True},
            {"key": "gcn_cu", "name": "Giấy chứng nhận đăng ký tàu cá cũ", "icon": "📜", "sides": 1,
             "repeatable": True},
            {"key": "ly_do", "name": "Giấy tờ chứng minh lý do xóa đăng ký (vd Hợp đồng mua bán tàu)", "icon": "🤝",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người đề nghị xóa đăng ký", "icon": "🪪", "sides": 2,
             "repeatable": True},
            {"key": "mau_khac", "name": "Mẫu 11.ĐKT, 12.ĐKT, 13.ĐKT (nếu thuộc trường hợp bắt buộc)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai xóa đăng ký tàu cá / tàu phục vụ nuôi trồng thủy sản (Mẫu số 10.ĐKT) — nguồn chính.\n"
            "2. Giấy chứng nhận đăng ký tàu cá cũ.\n"
            "3. Giấy tờ chứng minh lý do xóa đăng ký, ví dụ Hợp đồng mua bán / chuyển nhượng tàu cá.\n"
            "4. Căn cước của người đề nghị xóa đăng ký.\n"
            "5. Mẫu 11.ĐKT, 12.ĐKT, 13.ĐKT nếu hồ sơ thuộc trường hợp bắt buộc.\n"
            "Có thể tải một PDF gộp. Người nộp trên cổng giữ theo tài khoản.\n"
            "Bước Thành phần hồ sơ: Mẫu 10/11/12/13.ĐKT vào 4 dòng tương ứng; giấy tờ tách riêng thêm dòng qua "
            "'Thêm giấy tờ'."
        ),
    },
    {
        "key": "chia-tach-sap-nhap-hop-nhat-hoi-cap-tinh",
        # Mã TTHC 1.012945, Sở Nội vụ (ke_khai selectSo). Form.io + attp-row 7 dòng, engine tách/gộp trang
        # (sourceSegments) → có thể scan cả bộ hồ sơ vào một PDF.
        "detect": {
            "urlIncludes": ["019d2bfb-138e-725c-a0d7-46a5f07bc45b"],
            "textIncludes": ["chia, tách; sáp nhập; hợp nhất hội"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)",
        "shortLabel": "Chia, tách, sáp nhập, hợp nhất hội",
        "subtitle": "Hội cấp tỉnh xin chia, tách, sáp nhập hoặc hợp nhất",
        "icon": "🤝",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-138e-725c-a0d7-46a5f07bc45b",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Nội vụ",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị chia, tách, sáp nhập, hợp nhất hội (Mẫu số 10) — đã ký",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "de_an", "name": "Đề án", "icon": "📘", "sides": 1, "repeatable": True},
            {"key": "nghi_quyet", "name": "Nghị quyết, Biên bản họp Ban chấp hành; danh sách Ban chấp hành, Ban kiểm "
             "tra hội mới", "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "dieu_le", "name": "Dự thảo Điều lệ; văn bản xác nhận nơi dự kiến đặt trụ sở", "icon": "📑",
             "sides": 1, "repeatable": True},
            {"key": "ly_lich", "name": "Phiếu lý lịch tư pháp số 1 + Sơ yếu lý lịch của người dự kiến làm chủ tịch",
             "icon": "👤", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nộp (chỉ để điền)", "icon": "🪪", "sides": 2,
             "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF):\n"
            "1. Đơn đề nghị chia, tách, sáp nhập, hợp nhất hội (Mẫu số 10), đã ký.\n"
            "2. Đề án — lý do, tên gọi, địa chỉ trụ sở, nhân sự Ban chấp hành / Ban kiểm tra.\n"
            "3. Nghị quyết + Biên bản họp Ban chấp hành; danh sách Ban chấp hành, Ban kiểm tra hội mới.\n"
            "4. Dự thảo Điều lệ; văn bản xác nhận nơi dự kiến đặt trụ sở (nếu có).\n"
            "5. Phiếu lý lịch tư pháp số 1 + Sơ yếu lý lịch của người dự kiến làm chủ tịch — điền chủ hồ sơ.\n"
            "6. Căn cước của người nộp (tài khoản đăng nhập).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân loại và tách trang theo nội dung.\n"
            "Bước đính kèm: mỗi dòng một tệp gộp (đều Bản chính) — trụ sở dòng 1, Đơn dòng 2, Đề án dòng 3, Nghị "
            "quyết + Biên bản dòng 4, danh sách Ban chấp hành dòng 5, lý lịch dòng 6, Điều lệ dòng 7."
        ),
    },
    {
        "key": "bao-cao-to-chuc-dai-hoi-hoi-cap-tinh",
        # Mã TTHC 1.012942, Sở Nội vụ (ke_khai selectSo). Form.io + attp-row 18 dòng, engine tách/gộp trang.
        "detect": {
            "urlIncludes": ["019d2bfb-137c-7669-b668-60277b1a9cb7"],
            "textIncludes": ["báo cáo tổ chức đại hội thành lập, đại hội nhiệm kỳ, đại hội bất thường của hội"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Thủ tục báo cáo tổ chức đại hội thành lập, đại hội nhiệm kỳ, đại hội bất thường của hội (cấp tỉnh)"
        ),
        "shortLabel": "Báo cáo tổ chức đại hội hội",
        "subtitle": "Hội cấp tỉnh báo cáo trước khi tổ chức đại hội thành lập, nhiệm kỳ, bất thường",
        "icon": "🗓️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-137c-7669-b668-60277b1a9cb7",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Nội vụ",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "bao_cao", "name": "Văn bản báo cáo tổ chức đại hội + Nghị quyết Ban chấp hành về việc tổ chức "
             "đại hội", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "de_an_nhan_su", "name": "Đề án nhân sự, danh sách dự kiến Ban chấp hành; công văn cử cán bộ",
             "icon": "📘", "sides": 1, "repeatable": True},
            {"key": "du_thao", "name": "Dự thảo báo cáo tổng kết, báo cáo kiểm điểm, tài chính, số lượng hội viên",
             "icon": "📊", "sides": 1, "repeatable": True},
            {"key": "nghi_quyet", "name": "Dự thảo Nghị quyết đại hội; Dự thảo Điều lệ sửa đổi (nếu có)",
             "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "ly_lich", "name": "Sơ yếu lý lịch + Phiếu lý lịch tư pháp số 1 của nhân sự dự kiến Chủ tịch",
             "icon": "👤", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước công dân của người nộp (chỉ để điền)", "icon": "🪪", "sides": 2,
             "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF):\n"
            "1. Văn bản báo cáo tổ chức đại hội gửi Sở Nội vụ + Nghị quyết Ban chấp hành về việc tổ chức đại hội.\n"
            "2. Đề án nhân sự + danh sách dự kiến Ban chấp hành; công văn cử cán bộ / ý kiến đồng ý.\n"
            "3. Dự thảo báo cáo tổng kết, báo cáo kiểm điểm Ban chấp hành, Ban kiểm tra, tài chính, số lượng hội "
            "viên.\n"
            "4. Dự thảo Nghị quyết đại hội; Dự thảo Điều lệ sửa đổi (nếu có).\n"
            "5. Sơ yếu lý lịch + Phiếu lý lịch tư pháp số 1 của nhân sự dự kiến Chủ tịch — điền chủ hồ sơ.\n"
            "6. Căn cước của người nộp (tài khoản đăng nhập).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân loại và tách trang theo nội dung.\n"
            "Bước đính kèm: mỗi dòng một tệp gộp (đều Bản chính), dòng dùng tùy loại đại hội (thành lập / nhiệm kỳ "
            "/ bất thường)."
        ),
    },
    {
        "key": "thong-bao-ket-qua-dai-hoi-phe-duyet-dieu-le-hoi-cap-tinh",
        # Mã TTHC 1.012943, Sở Nội vụ (ke_khai selectSo). Form.io + attp-row 7 dòng, engine tách/gộp trang.
        "detect": {
            "urlIncludes": ["019d2bfb-138a-761e-a8e5-014dbed4f2be"],
            "textIncludes": ["thông báo kết quả đại hội", "phê duyệt điều lệ hội"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội (cấp tỉnh)",
        "shortLabel": "Thông báo kết quả đại hội, phê duyệt điều lệ hội",
        "subtitle": "Hội cấp tỉnh báo kết quả đại hội, xin duyệt đổi tên, điều lệ",
        "icon": "📣",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-138a-761e-a8e5-014dbed4f2be",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Nội vụ",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_trinh", "name": "Tờ trình / văn bản báo cáo kết quả đại hội gửi Sở Nội vụ", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "nghi_quyet", "name": "Nghị quyết đại hội", "icon": "📝", "sides": 1, "repeatable": True},
            {"key": "bien_ban", "name": "Biên bản đại hội, biên bản bầu cử, biên bản họp Ban chấp hành lần thứ nhất "
             "và các danh sách nhân sự", "icon": "📋", "sides": 1, "repeatable": True},
            {"key": "chuong_trinh", "name": "Chương trình hoạt động của hội (hoặc Báo cáo tổng kết nhiệm kỳ)",
             "icon": "📘", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Dự thảo Điều lệ sửa đổi, đơn đề nghị đổi tên, lý lịch Chủ tịch, căn cước người "
             "nộp (nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF):\n"
            "1. Tờ trình / văn bản báo cáo kết quả đại hội gửi Sở Nội vụ (kèm danh sách Ban chấp hành nếu có).\n"
            "2. Nghị quyết đại hội.\n"
            "3. Biên bản đại hội / biên bản bầu cử, biên bản họp Ban chấp hành lần thứ nhất và các danh sách nhân sự.\n"
            "4. Chương trình hoạt động của hội (không có thì đính tạm Báo cáo tổng kết nhiệm kỳ).\n"
            "5. Nếu có: Dự thảo Điều lệ sửa đổi, đơn đề nghị đổi tên hội, lý lịch Chủ tịch; căn cước người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân loại và tách trang theo nội dung.\n"
            "Bước đính kèm: Tờ trình dòng 1; Biên bản + danh sách dòng 3; Nghị quyết dòng 5; Chương trình hoạt động "
            "dòng 6; dòng đổi tên, Điều lệ, lý lịch chỉ đính khi có giấy tờ."
        ),
    },
    {
        "key": "dang-ky-nha-o-xa-hoi-tuyen-quang",
        "provinceOnly": ["tuyenquang"],
        # TTHC 1.014632 trên cổng Bộ Xây dựng (Form.io, 2 form kê khai + bảng attp-row 7 dòng).
        # Cấu hình riêng Tuyên Quang; cùng mã với luồng Bắc Ninh nhưng khác cổng và pipeline.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "urlIncludes": ["maThuTuc=1.014632", "019d2bfe-985c-732b-822b-460f2199467e"],
            "textIncludes": ["vay vốn để hộ gia đình, cá nhân tự xây dựng hoặc cải tạo, sửa chữa nhà ở"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Đăng ký mua, thuê mua, thuê nhà ở xã hội, vay vốn để hộ gia đình, cá nhân tự xây dựng "
            "hoặc cải tạo, sửa chữa nhà ở"
        ),
        "shortLabel": "Đăng ký nhà ở xã hội",
        "subtitle": "Xác nhận điều kiện nhà ở để mua, thuê mua, thuê nhà ở xã hội hoặc vay vốn tại Tuyên Quang",
        "icon": "🏘️",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-985c-732b-822b-460f2199467e",
        "flowProfile": "xay-dung",
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "needsAgencySelect": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "mau_05", "name": "Giấy tờ chứng minh điều kiện về thu nhập", "icon": "💰",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "mau_01", "name": "Giấy tờ chứng minh đối tượng được hưởng chính sách hỗ trợ về nhà ở xã hội",
             "icon": "📄", "sides": 1, "optional": True, "repeatable": True},
            {"key": "doi_tuong_thu_nhap", "name": "Giấy tờ chứng minh đối tượng, thu nhập", "icon": "📑",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "vay_von_tin_dung", "name": "Giấy tờ chứng minh điều kiện vay vốn tại tổ chức tín dụng",
             "icon": "🏦", "sides": 1, "optional": True, "repeatable": True},
            {"key": "vay_von_ngan_hang_csxh",
             "name": "Giấy tờ chứng minh điều kiện vay vốn qua Ngân hàng Chính sách xã hội",
             "icon": "🏦", "sides": 1, "optional": True, "repeatable": True},
            {"key": "mau_03", "name": "Giấy tờ chứng minh điều kiện nhà ở (có nhà dưới 15 m² sàn/người)",
             "icon": "🏠", "sides": 1, "optional": True, "repeatable": True},
            {"key": "mau_02", "name": "Giấy tờ chứng minh điều kiện về nhà ở (Mẫu số 02)", "icon": "🏠",
             "sides": 1, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Hồ sơ thường là một PDF gộp gồm Giấy xác nhận điều kiện nhà ở (Mẫu 02 hoặc Mẫu 03), Giấy "
            "chứng nhận quyền sử dụng đất, CCCD, CT07, giấy tờ hôn nhân và giấy tờ chứng minh đối tượng/"
            "thu nhập hoặc vay vốn. Hệ thống đọc người kê khai trên mẫu để điền thông tin người nộp và "
            "các phần trên tờ khai. Tệp có thể được đính vào nhiều dòng; không tự tách file. "
            "Dòng Mẫu 02/03 nhận thêm giấy tờ nhà đất, cư trú, căn cước và hôn nhân đi kèm."
        ),
    },
    {
        "key": "tham-dinh-bcnckt",
        "flowProfile": "xay-dung",
        # Mã TTHC 1.013239, cổng Bộ Xây dựng. ke_khai_links không khai selectSo nhưng thẩm định do Sở Xây dựng giải
        # quyết → chọn cơ quan cấp Sở như "dang-ky-noi-quy-lao-dong" (kiểm khi chạy thử).
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moc.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["019d2bfe-90c2-742a-9dfb-c6d2bdd9aac8"],
            "textIncludes": ["Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng/Báo cáo nghiên cứu khả thi đầu tư xây dựng điều "
            "chỉnh"
        ),
        "shortLabel": "Thẩm định báo cáo nghiên cứu khả thi đầu tư xây dựng",
        "subtitle": "Chủ đầu tư trình Sở Xây dựng thẩm định dự án",
        "icon": "📊",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-90c2-742a-9dfb-c6d2bdd9aac8",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        "requiredDocs": [
            {"key": "to_trinh", "name": "Tờ trình thẩm định Báo cáo nghiên cứu khả thi (Mẫu số 01)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước của người nộp hồ sơ (đại diện chủ đầu tư)", "icon": "🪪", "sides": 2,
             "repeatable": True},
            {"key": "khac", "name": "Quyết định ĐTM, chủ trương đầu tư, thỏa thuận đấu nối, danh sách nhà thầu, quy "
             "hoạch, hồ sơ khảo sát / thiết kế cơ sở, GCN đầu tư (nếu có)", "icon": "📎", "sides": 1,
             "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ trình thẩm định Báo cáo nghiên cứu khả thi (Mẫu số 01) — nguồn chính để điền.\n"
            "2. Căn cước người nộp hồ sơ (đại diện chủ đầu tư).\n"
            "3. Nếu có: quyết định phê duyệt ĐTM / giấy phép môi trường, văn bản chủ trương đầu tư, thỏa thuận đấu "
            "nối hạ tầng, danh sách nhà thầu + chứng chỉ, quyết định phê duyệt quy hoạch, hồ sơ khảo sát / thiết "
            "kế cơ sở, giấy chứng nhận đầu tư.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Ô không có trong Tờ trình (diện tích đất, chi phí xây dựng, mục tiêu đầu tư…) để trống cho cán bộ bổ "
            "sung. Bước đính kèm: mỗi loại giấy tờ vào một dòng."
        ),
    },
    {
        "key": "cap-bo-sung-xe-tap-lai-cap-lai-giay-phep-xe-tap-lai",
        "flowProfile": "xay-dung",
        # Mã TTHC 1.001751, cổng Bộ Xây dựng, Sở Xây dựng (ke_khai selectSo). attp-row 2 dòng.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moc.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["019d2bfe-1332-703e-951b-def74019fb46"],
            "textIncludes": ["cấp bổ sung xe tập lái, cấp lại giấy phép xe tập lái"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp bổ sung xe tập lái, cấp lại Giấy phép xe tập lái",
        "shortLabel": "Cấp bổ sung, cấp lại giấy phép xe tập lái",
        "subtitle": "Cơ sở đào tạo lái xe xin giấy phép cho xe tập lái",
        "icon": "🚗",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-1332-703e-951b-def74019fb46",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "danh_sach", "name": "Danh sách xe đề nghị cấp giấy phép xe tập lái — đã ký, đóng dấu",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "giay_to_xe", "name": "Chứng nhận đăng ký xe, chứng nhận kiểm định, hợp đồng thuê xe (nếu xe "
             "không thuộc sở hữu cơ sở)", "icon": "🚗", "sides": 1, "repeatable": True},
            {"key": "cccd", "name": "Căn cước của người nộp (chỉ để điền)", "icon": "🪪", "sides": 2,
             "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ liên quan khác", "icon": "📎", "sides": 1, "optional": True,
             "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Danh sách xe đề nghị cấp giấy phép xe tập lái của cơ sở đào tạo — đã ký, đóng dấu. Nguồn chính.\n"
            "2. Giấy tờ xe tập lái (có thể gộp một tệp): chứng nhận đăng ký xe, chứng nhận kiểm định, hợp đồng thuê "
            "xe.\n"
            "3. Nếu muốn điền phần người nộp: căn cước của người nộp (không đính kèm).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Bước đính kèm: Danh sách đề nghị → dòng 1; giấy tờ xe → dòng 2."
        ),
    },
    {
        "key": "cap-cap-lai-phu-hieu-xe-kinh-doanh-van-tai",
        "flowProfile": "xay-dung",
        # Mã TTHC 2.002288, cổng Bộ Xây dựng, Sở Xây dựng (ke_khai selectSo). Trợ lý điền xe đầu tiên trong bảng
        # 'Thêm phương tiện'; màu phù hiệu công dân tự chọn.
        "bxdFlow": {
            "resultGroups": [{"name": "receivingKind", "label": "Hình thức nhận kết quả"}],
        },
        "detect": {
            "urlScope": ["dvc.moc.gov.vn", "dichvucong.gov.vn"],
            "urlIncludes": ["019d2bfe-a055-702e-b40b-ed5848ebb0d9"],
            "textIncludes": ["cấp, cấp lại phù hiệu cho xe ô tô, xe bốn bánh có gắn động cơ kinh doanh vận tải"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp, cấp lại Phù hiệu cho xe ô tô, xe bốn bánh có gắn động cơ kinh doanh vận tải",
        "shortLabel": "Cấp, cấp lại phù hiệu xe kinh doanh vận tải",
        "subtitle": "Đơn vị vận tải xin phù hiệu cho xe ô tô kinh doanh",
        "icon": "🚌",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-a055-702e-b40b-ed5848ebb0d9",
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyDeptLabel": "Sở Xây dựng",
        "hideRepeatableHint": False,
        "requiredDocs": [
            {"key": "giay_de_nghi", "name": "Giấy đề nghị cấp (cấp lại) phù hiệu — đã ký, đóng dấu", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "dang_ky_xe", "name": "Chứng nhận đăng ký xe ô tô (kèm hợp đồng nếu xe không đứng tên đơn vị)",
             "icon": "🚌", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy phép kinh doanh vận tải, GCN đăng ký doanh nghiệp / HTX, căn cước người "
             "nộp (nếu có)", "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị cấp (cấp lại) phù hiệu của đơn vị kinh doanh vận tải — đã ký, đóng dấu. Nguồn chính.\n"
            "2. Chứng nhận đăng ký xe ô tô, kèm hợp đồng dịch vụ / hợp đồng thuê xe nếu xe không đứng tên đơn vị.\n"
            "3. Nếu có: giấy phép kinh doanh vận tải, GCN đăng ký doanh nghiệp / HTX; căn cước người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung.\n"
            "Trợ lý điền thông tin xe đầu tiên; màu phù hiệu tự chọn, soát rồi bấm 'Thêm'.\n"
            "Bước đính kèm: đăng ký xe + hợp đồng → dòng 1 (Bản sao); Giấy đề nghị → dòng 2 (Bản chính)."
        ),
    },
    {
        "key": "xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru",
        # Mã TTHC 1.013314, cổng tỉnh iGate (attp-row 1 dòng + "Thêm giấy tờ", engine tách/gộp trang). UBND cấp xã
        # tiếp nhận → DVCQG chọn Tỉnh + Xã.
        "detect": {
            "urlIncludes": ["019d2bf7-9660-707e-97b1-ef8876f54d3b"],
            "textIncludes": ["Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ ở do thuê, mượn, ở nhờ; "
            "nhà ở, đất ở không có tranh chấp quyền sở hữu nhà ở, quyền sử dụng đất ở, không thuộc địa điểm không "
            "được đăng ký thường trú mới"
        ),
        "shortLabel": "Xác nhận diện tích nhà ở để đăng ký thường trú",
        "subtitle": "Xác nhận chỗ thuê, mượn, ở nhờ đủ diện tích để đăng ký thường trú",
        "icon": "🏠",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf7-9660-707e-97b1-ef8876f54d3b",
        "needsAgencySelect": True,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở (Mẫu số 02) — "
             "đã ký", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở của chỗ ở (đủ bìa và các "
             "trang)", "icon": "🏠", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Hợp đồng thuê, mượn, ở nhờ; văn bản ủy quyền; căn cước người đề nghị (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "agent",
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể gộp chung một PDF):\n"
            "1. Tờ khai xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở tối thiểu (Mẫu số 02), đã ký — nguồn "
            "chính để điền.\n"
            "2. Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở của chỗ ở (đủ bìa và các trang).\n"
            "3. Nếu có: hợp đồng thuê, mượn, ở nhờ; văn bản ủy quyền khi nộp thay.\n"
            "4. Căn cước của người đề nghị (nếu có) — chỉ để điền ngày cấp, nơi cấp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân loại và tách trang theo nội dung.\n"
            "Bước đính kèm: Tờ khai → dòng 1; Giấy chứng nhận thêm dòng qua 'Thêm giấy tờ' (không thêm được thì "
            "đính chung dòng Tờ khai)."
        ),
    },
    # ── Thủ tục đặc thù Quảng Ninh (01/11/2026) ──
    # Key TRÙNG registry lõi → attach pipeline tự nối; label = label lõi bỏ "[Tỉnh Quảng Ninh] " (như Bắc Ninh); detect
    # y hệt lõi. Cả 14 là ATTACH-ONLY: cổng tỉnh chỉ có bước Thành phần hồ sơ (ví giấy tờ React/Radix). Cờ chọn cơ quan
    # ở DVCQG theo ke_khai_links của đúng mã: provinceOnlyAgency → agencyProvinceOnly, selectSo → agencySoFirst,
    # submitCardIncludes → agencyCardIncludes, agencyWard giữ nguyên. keKhaiUrl / provincePortalFlow / uploadHint gán ở
    # cuối danh sách (xem _QN_HOST); entry tự khai provincePortalFlow khi ke_khai_links không có (bên Auto Fill cán bộ
    # bấm tay dòng đó) — khi ấy chọn dòng theo cụm chữ đặc trưng của detect, không có rowIndex dự phòng.
    {
        "key": "dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115820 (ke_khai_links "dang-ky-dat-dai-tai-san-gan-lien-lan-dau-quang-ninh"): DVCQG chọn đủ Tỉnh + Xã.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "[Đặc thù] Thủ tục đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115820",
        "label": (
            "[Đặc thù] Thủ tục đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận quyền sử dụng đất, "
            "quyền sở hữu tài sản gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân cư, người "
            "gốc việt nam định cư ở nước ngoài - Trường hợp thực hiện thủ tục đăng ký đất đai, tài sản gắn liền với "
            "đất, cấp giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu (gồm trường "
            "hợp chưa thực hiện đăng ký đất đai lần đầu; trường hợp đã có thông báo kết quả đăng ký đất đai, tài sản "
            "gắn liền với đất không thể hiện đủ điều kiện cấp giấy chứng nhận) - Miền núi, hải đảo"
        ),
        "shortLabel": "Đăng ký đất đai, cấp giấy chứng nhận quyền sử dụng đất lần đầu - Miền núi, hải đảo",
        "subtitle": "Mã 1.115820 · Đăng ký và cấp Giấy chứng nhận lần đầu cho hộ gia đình, cá nhân tại Quảng Ninh",
        "icon": "🏞️",
        "needsAgencySelect": True,
        "agencyProvince": "Quảng Ninh",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15) đã kê khai",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "do_dac", "name": "Mảnh trích đo / phiếu đo đạc, xác nhận hiện trạng, ranh giới thửa đất (nếu có)",
             "icon": "📐", "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ về nguồn gốc đất, nghĩa vụ tài chính, tờ khai thuế, ủy quyền (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "dang-ky-bien-dong-chuyen-nhuong-quang-ninh-mien-nui-hai-dao",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115835 (ke_khai_links "dang-ky-bien-dong-dat-dai-quang-ninh"): provinceOnlyAgency + thẻ VPĐK.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "[Đặc thù] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
                "Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115835",
        "label": (
            "[Đặc thù] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các trường "
            "hợp chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án dồn điền, đổi thửa; chuyển "
            "nhượng, thừa kế, tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất, góp vốn bằng quyền "
            "sử dụng đất, quyền sở hữu tài sản gắn liền với đất; cho thuê, cho thuê lại quyền sử dụng đất trong dự "
            "án xây dựng kinh doanh kết cấu hạ tầng; bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản "
            "gắn liền với đất thuê của Nhà nước theo hình thức thuê đất trả tiền hàng năm; chuyển quyền khai thác "
            "khoáng sản theo quy định của pháp luật về địa chất và khoáng sản - Chuyển đổi quyền sử dụng đất nông "
            "nghiệp mà không theo phương án dồn điền, đổi thửa hoặc trường hợp chuyển nhượng, thừa kế, tặng cho "
            "quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất, góp vốn bằng quyền sử dụng đất, quyền sở hữu "
            "tài sản gắn liền với đất; bán, thừa kế, tặng cho hoặc góp vốn bằng tài sản gắn liền với đất được Nhà "
            "nước cho thuê đất thu tiền thuê đất hằng năm - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam "
            "định cư ở nước ngoài - Miền núi, hải đảo"
        ),
        "shortLabel": (
            "Đăng ký biến động quyền sử dụng đất: chuyển đổi, chuyển nhượng, thừa kế, tặng cho, góp vốn - "
            "Miền núi, hải đảo"
        ),
        "subtitle": "Mã 1.115835 · Sang tên sổ đỏ khi chuyển nhượng, thừa kế, tặng cho đất tại Quảng Ninh",
        "icon": "🤝",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp (sổ đỏ / sổ hồng)", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "hop_dong", "name": "Hợp đồng / văn bản chuyển nhượng, thừa kế, tặng cho, góp vốn",
             "icon": "🤝", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Mảnh trích đo, tờ khai thuế, lệ phí trước bạ, ủy quyền (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "chuyen-muc-dich-su-dung-dat-quang-ninh-mien-nui-hai-dao",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115811 (ke_khai_links "chuyen-muc-dich-su-dung-dat-quang-ninh"): DVCQG chọn đủ Tỉnh + Xã. ke_khai_links
        # không khai provincePortalFlow → chọn dòng theo cụm chữ của detect, cơ quan trong modal để lựa chọn đầu.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "[Đặc thù] Thủ tục chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất",
                "Trường hợp thuê đất trả tiền thuê đất hằng năm",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115811",
        "label": (
            "[Đặc thù] Thủ tục chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi "
            "hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư - Trường hợp thuê đất trả "
            "tiền thuê đất hằng năm hoặc trường hợp dự án có nhiều hình thức sử dụng đất mà không có trường hợp nào "
            "thuộc thẩm quyền của chủ tịch ủy ban nhân dân tỉnh theo quy định - Miền núi, hải đảo"
        ),
        "shortLabel": (
            "Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất - Trường hợp thuê đất "
            "trả tiền thuê đất hằng năm - Miền núi, hải đảo"
        ),
        "subtitle": "Mã 1.115811 · Chuyển mục đích, hình thức, gia hạn sử dụng đất thuê trả tiền hằng năm tại Quảng Ninh",
        "icon": "🔄",
        "needsAgencySelect": True,
        "agencyProvince": "Quảng Ninh",
        "provincePortalFlow": {
            "host": _QN_HOST,
            "rowIncludes": ["Trường hợp thuê đất trả tiền thuê đất hằng năm", "Miền núi, hải đảo"],
        },
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn chuyển mục đích (Mẫu 02) / chuyển hình thức (Mẫu 03) / gia hạn (Mẫu 23) / "
             "điều chỉnh thời hạn dự án (Mẫu 10)", "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Trích lục, quyết định / văn bản dự án, tờ khai thuế, ủy quyền (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "cap-doi-gcn-quang-ninh-mien-nui-hai-dao",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115848 (ke_khai_links "cap-doi-gcn-quyen-su-dung-dat-quang-ninh"): provinceOnlyAgency + thẻ VPĐK. ke_khai_links
        # không khai provincePortalFlow → chọn dòng theo cụm chữ của detect; chi nhánh VPĐK như các thủ tục VPĐK khác.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "[Đặc thù] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
                "Các trường hợp khác - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - "
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115848",
        "label": (
            "[Đặc thù] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất - Các trường "
            "hợp khác - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo"
        ),
        "shortLabel": "Cấp đổi Giấy chứng nhận quyền sử dụng đất - Các trường hợp khác - Miền núi, hải đảo",
        "subtitle": "Mã 1.115848 · Đổi sổ đỏ / sổ hồng đã cấp sang Giấy chứng nhận mới tại Quảng Ninh",
        "icon": "📜",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "provincePortalFlow": {
            "host": _QN_HOST,
            "rowIncludes": [
                "Các trường hợp khác - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - "
                "Miền núi, hải đảo",
            ],
            "agency": _QN_VPDK_CO_TO,
        },
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp (bản cần cấp đổi)", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Mảnh trích đo, tờ khai thuế, lệ phí trước bạ, ủy quyền (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "cap-doi-gcn-do-do-dac-khong-nvtc-quang-ninh-mien-nui-hai-dao",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # Biến thể CÙNG mã 1.115848 với thẻ ngay trên (đo đạc lại, không nghĩa vụ tài chính): cùng đường DVCQG, khác
        # dòng trên bảng cổng tỉnh → chọn dòng theo cụm chữ riêng của detect.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "[Đặc thù] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
                "do thay đổi kích thước các cạnh, diện tích, số hiệu của thửa đất do đo đạc",
                "Trường hợp không phải thực hiện nghĩa vụ tài chính",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115848",
        "label": (
            "[Đặc thù] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất - Trường hợp "
            "cấp đổi Giấy chứng nhận do thay đổi kích thước các cạnh, diện tích, số hiệu của thửa đất do đo đạc lập "
            "bản đồ địa chính, trích đo địa chính thửa đất mà ranh giới thửa đất không thay đổi - Trường hợp không "
            "phải thực hiện nghĩa vụ tài chính - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở "
            "nước ngoài - Miền núi, hải đảo"
        ),
        "shortLabel": (
            "Cấp đổi Giấy chứng nhận do thay đổi kích thước, diện tích thửa đất do đo đạc - Không phải thực hiện "
            "nghĩa vụ tài chính - Miền núi, hải đảo"
        ),
        "subtitle": "Mã 1.115848 · Đổi Giấy chứng nhận sau khi đo đạc lại thửa đất (ranh giới không đổi) tại Quảng Ninh",
        "icon": "📐",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "provincePortalFlow": {
            "host": _QN_HOST,
            "rowIncludes": [
                "do thay đổi kích thước các cạnh, diện tích, số hiệu của thửa đất do đo đạc",
                "Trường hợp không phải thực hiện nghĩa vụ tài chính",
                "Miền núi, hải đảo",
            ],
            "agency": _QN_VPDK_CO_TO,
        },
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp (bản cần cấp đổi)", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "do_dac", "name": "Mảnh trích đo / phiếu đo đạc chỉnh lý thửa đất", "icon": "📐",
             "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Tờ khai thuế, lệ phí trước bạ, ủy quyền (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "tach-hop-thua-dat-quang-ninh-mien-nui-hai-dao",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115832 (ke_khai_links "tach-thua-hop-thua-dat-quang-ninh"): provinceOnlyAgency + thẻ VPĐK.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "[Đặc thù] Tách thửa đất, hợp thửa đất",
                "Đối với trường hợp Tách thửa cùng tên - Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115832",
        "label": (
            "[Đặc thù] Tách thửa đất, hợp thửa đất - Đối với trường hợp Giấy chứng nhận đã cấp khi thực hiện các "
            "quyền của hộ gia đình, cá nhân, cộng đồng dân cư, người Việt Nam định cư ở nước ngoài được sở hữu nhà ở "
            "gắn liền với quyền sử dụng đất ở tại Việt Nam - Đối với trường hợp Tách thửa cùng tên - Miền núi, hải đảo"
        ),
        "shortLabel": "Tách thửa đất, hợp thửa đất - Tách thửa cùng tên - Miền núi, hải đảo",
        "subtitle": "Mã 1.115832 · Tách một thửa thành nhiều thửa hoặc gộp thửa, cùng người đứng tên, tại Quảng Ninh",
        "icon": "✂️",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 26)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "ban_ve", "name": "Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 27)", "icon": "📐",
             "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận đã cấp", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Tờ khai thuế, lệ phí trước bạ, văn bản cho phép tách / hợp thửa (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "dang-ky-tai-san-dat-quang-ninh-mien-nui-hai-dao",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115840 (ke_khai_links "dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn-quang-ninh"): provinceOnlyAgency + thẻ VPĐK.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "[Đặc thù] Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận",
                "Trường hợp phải thực hiện nghĩa vụ tài chính",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115840",
        "label": (
            "[Đặc thù] Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận hoặc đăng ký thay đổi về tài "
            "sản gắn liền với đất; gia hạn thời hạn sở hữu nhà ở của tổ chức, cá nhân nước ngoài - Trường hợp phải "
            "thực hiện nghĩa vụ tài chính - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước "
            "ngoài - Miền núi, hải đảo"
        ),
        "shortLabel": (
            "Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận - Phải thực hiện nghĩa vụ tài chính - "
            "Miền núi, hải đảo"
        ),
        "subtitle": "Mã 1.115840 · Đăng ký nhà, công trình xây trên đất đã có sổ đỏ tại Quảng Ninh",
        "icon": "🏠",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận đã cấp", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "tai_san", "name": "Giấy phép xây dựng, hồ sơ thiết kế, sơ đồ / phiếu đo đạc tài sản",
             "icon": "🏗️", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Giấy tờ chứng minh sở hữu tài sản, tờ khai thuế, lệ phí trước bạ (nếu có)",
             "icon": "📎", "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "dang-ky-bien-dong-doi-ten-quang-ninh-mien-nui-hai-dao",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115837 (ke_khai_links "dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-quang-ninh"): provinceOnlyAgency + thẻ VPĐK.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "[Đặc thù] Đăng ký biến động đối với trường hợp đổi tên hoặc thay đổi thông tin về người sử dụng đất",
                "đổi tên hoặc thay đổi thông tin về người sử dụng đất",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115837",
        "label": (
            "[Đặc thù] Đăng ký biến động đối với trường hợp đổi tên hoặc thay đổi thông tin về người sử dụng đất, chủ "
            "sở hữu tài sản gắn liền với đất - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước "
            "ngoài - Miền núi, hải đảo"
        ),
        "shortLabel": (
            "Đăng ký biến động do đổi tên hoặc thay đổi thông tin về người sử dụng đất - Miền núi, hải đảo"
        ),
        "subtitle": "Mã 1.115837 · Cập nhật tên, thông tin người đứng tên trên Giấy chứng nhận tại Quảng Ninh",
        "icon": "✏️",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "thay_doi", "name": "Giấy tờ chứng minh việc đổi tên / thay đổi thông tin người sử dụng đất",
             "icon": "🪪", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Bản gốc Giấy chứng nhận đã cấp", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Mảnh trích đo, văn bản cho phép đổi tên, ủy quyền (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "dang-ky-cap-gcn-toan-bo-dien-tich-dang-su-dung-quang-ninh",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115841: ke_khai_links khai agencyWard "Đặc khu Cô Tô" → DVCQG chọn Tỉnh + đúng xã đó, bỏ qua xã tài khoản.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "toàn bộ diện tích đất đang sử dụng quy định tại khoản 2 điều 24",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115841",
        "label": (
            "[Đặc thù] Thủ tục đăng ký, cấp giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất "
            "đối với toàn bộ diện tích đất đang sử dụng quy định tại khoản 2 Điều 24 Nghị định số 101/2024/NĐ-CP - "
            "Miền núi, hải đảo"
        ),
        "shortLabel": (
            "Đăng ký, cấp giấy chứng nhận đối với toàn bộ diện tích đất đang sử dụng (khoản 2 Điều 24 Nghị định "
            "101/2024/NĐ-CP) - Miền núi, hải đảo"
        ),
        "subtitle": "Mã 1.115841 · Cấp Giấy chứng nhận khi diện tích thực tế tăng thêm so với sổ đã cấp tại Quảng Ninh",
        "icon": "🗺️",
        "needsAgencySelect": True,
        "agencyProvince": "Quảng Ninh",
        "agencyWard": "Đặc khu Cô Tô",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp (bìa + trang chứng nhận, sơ đồ đất)", "icon": "📜",
             "sides": 1, "repeatable": True},
            {"key": "do_dac", "name": "Phiếu đo đạc chỉnh lý, xác nhận kết quả đo đạc hiện trạng thửa đất",
             "icon": "📐", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Tờ khai thuế, lệ phí trước bạ, ủy quyền (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "tinh-tien-su-dung-dat-nd-50-2026-quang-ninh",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115148: DVCQG chọn đủ Tỉnh + Xã; modal cổng tỉnh chọn "UBND Đặc khu Cô Tô" (ke_khai_links). CÙNG mã với bản
        # Quảng Ngãi — urlScope + provinceOnly giữ hai tỉnh không tráo nhau.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "tính lại tiền sử dụng đất",
                "50/2026/NĐ-CP",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115148",
        "label": (
            "Thủ tục tính hoặc tính lại tiền sử dụng đất theo quy định tại các điểm a, b, c và d khoản 2 Điều 12 "
            "Nghị định số 50/2026/NĐ-CP"
        ),
        "shortLabel": "Tính hoặc tính lại tiền sử dụng đất theo Nghị định số 50/2026/NĐ-CP",
        "subtitle": "Mã 1.115148 · Đề nghị tính lại tiền sử dụng đất đã nộp tại Quảng Ninh",
        "icon": "🧮",
        "needsAgencySelect": True,
        "agencyProvince": "Quảng Ninh",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đề nghị tính lại tiền sử dụng đất", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "kem_theo", "name": "Giấy tờ kèm theo đơn (quyết định, Giấy chứng nhận, thông báo và chứng từ nộp "
             "tiền…)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền hoặc giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "cap-lai-gcn-do-bi-mat-quang-ninh",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115849: ke_khai_links provinceOnlyAgency + selectSo → DVCQG chỉ chọn Tỉnh, gạt "Sở", thẻ đầu.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "Cấp lại Giấy chứng nhận do bị mất",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115849",
        "label": (
            "[Đặc thù] Cấp lại Giấy chứng nhận do bị mất - Trường hợp không phải thực hiện nghĩa vụ tài chính - Đối "
            "với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo"
        ),
        "shortLabel": "Cấp lại Giấy chứng nhận do bị mất - Không phải thực hiện nghĩa vụ tài chính - Miền núi, hải đảo",
        "subtitle": "Mã 1.115849 · Xin cấp lại sổ đỏ / sổ hồng bị mất tại Quảng Ninh",
        "icon": "🔁",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencySoFirst": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "mat_gcn", "name": "Giấy tờ về việc mất Giấy chứng nhận (bản cam kết, xác nhận niêm yết thông "
             "báo mất…)", "icon": "📑", "sides": 1, "repeatable": True},
            {"key": "do_dac", "name": "Phiếu đo đạc chỉnh lý / mảnh trích đo thửa đất (nếu có)", "icon": "📐",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Tờ khai thuế, lệ phí trước bạ, ủy quyền (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "dang-ky-bien-dong-chuyen-muc-dich-sdd-khong-xin-phep-quang-ninh",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.115846: ke_khai_links provinceOnlyAgency + thẻ VPĐK.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "Đăng ký biến động chuyển mục đích sử dụng đất không phải xin phép",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.115846",
        "label": (
            "[Đặc thù] Đăng ký biến động chuyển mục đích sử dụng đất không phải xin phép cơ quan nhà nước có thẩm "
            "quyền - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo"
        ),
        "shortLabel": (
            "Đăng ký biến động chuyển mục đích sử dụng đất không phải xin phép cơ quan nhà nước có thẩm quyền - "
            "Miền núi, hải đảo"
        ),
        "subtitle": "Mã 1.115846 · Đăng ký đổi mục đích sử dụng đất thuộc diện không phải xin phép tại Quảng Ninh",
        "icon": "🌾",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "don", "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)",
             "icon": "📄", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận đã cấp", "icon": "📜", "sides": 1, "repeatable": True},
            {"key": "khac", "name": "Tờ khai thuế, lệ phí trước bạ, mảnh trích đo, ủy quyền (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "xoa-dang-ky-bien-phap-bao-dam-quang-ninh",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.011443: ke_khai_links provinceOnlyAgency + thẻ VPĐK. textIncludes dài hơn cụm của thủ tục ĐĂNG KÝ ngay dưới
        # (chuỗi con) — giữ nguyên như lõi để trang xóa vẫn về đúng thẻ này.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.011443",
        "label": "Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        "subtitle": "Mã 1.011443 · Xóa thế chấp sổ đỏ sau khi trả xong khoản vay tại Quảng Ninh",
        "icon": "🔓",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "phieu", "name": "Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 02a)", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "van_ban", "name": "Văn bản của bên nhận bảo đảm (ngân hàng) đồng ý xóa đăng ký thế chấp",
             "icon": "🏦", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận bản gốc (nếu tài sản bảo đảm có Giấy chứng nhận)", "icon": "📜",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền hoặc giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "dang-ky-bien-phap-bao-dam-quang-ninh",
        "provinceOnly": ["quangninh"],  # đặc thù Quảng Ninh: chỉ account tỉnh này thấy + gọi được
        # 1.011441: ke_khai_links provinceOnlyAgency + thẻ VPĐK.
        "detect": {
            "urlScope": [_QN_HOST],
            "textIncludes": [
                "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "code": "1.011441",
        "label": "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        "subtitle": "Mã 1.011441 · Đăng ký thế chấp quyền sử dụng đất, nhà ở để vay vốn tại Quảng Ninh",
        "icon": "🔒",
        "needsAgencySelect": True,
        "agencyProvinceOnly": True,
        "agencyProvince": "Quảng Ninh",
        "agencyDeptLabel": "Văn phòng Đăng ký đất đai",
        "agencyCardIncludes": _QN_VPDK_CARD,
        "hasAttachmentStep": True,
        "hideRepeatableHint": True,
        "requiredDocs": [
            {"key": "phieu", "name": "Phiếu yêu cầu đăng ký biện pháp bảo đảm", "icon": "📄",
             "sides": 1, "repeatable": True},
            {"key": "hop_dong", "name": "Hợp đồng thế chấp quyền sử dụng đất, tài sản gắn liền với đất",
             "icon": "🏦", "sides": 1, "repeatable": True},
            {"key": "gcn", "name": "Giấy chứng nhận bản gốc (nếu tài sản bảo đảm có Giấy chứng nhận)", "icon": "📜",
             "sides": 1, "optional": True, "repeatable": True},
            {"key": "khac", "name": "Văn bản ủy quyền hoặc giấy tờ khác (nếu có)", "icon": "📎",
             "sides": 1, "optional": True, "repeatable": True},
        ],
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
    },
]

# Video hướng dẫn làm thủ tục (Google Drive, theo ID tệp). Ở lượt xác nhận thủ tục, trợ lý hiện mã QR của link
# + nút "Mở hướng dẫn"; ảnh QR do BE sinh (chat/flow.py:_procedure_guide_action). Thủ tục không có trong bảng thì
# không hiện. Sửa/thêm link chỉ cần sửa ở đây, không phải phát hành lại extension.
_HUONG_DAN_DRIVE_URL = "https://drive.google.com/file/d/{}/view?usp=drive_link"
_HUONG_DAN_DRIVE_ID = {
    "khai-sinh-dang-ky-lai": "1ObePKXQq2rS62F72ipMMmXVVS399rMs4",
    "xac-nhan-tinh-trang-hon-nhan": "1K72MmetiOzQuVywsyest5ZP-GpZGJS6G",
    "khai-sinh-dang-ky": "1GrI9R8FRMUpphFxsIH2QdGR3h1wojwlk",
    "ket-hon": "1yM72x0kkgS0ouLuCjejiTLGYJ0cEyFGR",
    "khai-sinh-dang-ky-thuong": "1_c-8Xx4O9KqTH9KbCG0uqQlPNRH3-2du",
    "chung-thuc-ban-sao": "1rv3_eC98iTnAZX0Bc9cKnWQLsGCPq9Bi",
    "thay-doi-cai-chinh-ho-tich": "1_pns6gVNa2gP0aIWI3FfcyVk1A05FCAB",
    "trich-luc-ks": "1obk7WGRKMMecQXT2sx0APLpfhYUH9Ywm",
    "khai-tu": "1uhQSm10k6DsJOvL96YoM-YURMnF2jABU",
    "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham": "1Z8ScsMCKgN4AfKQAG33yFknek5id9w4N",
    "tro-cap-tho-cung-liet-si": "1u9hAr0bbvbiKH_JY9rE1B98lRUYHxU-B",
    "dieu-chinh-giay-phep-xay-dung": "1MbZYhrbrfMNsx-edOgsi-Add6BFHpSUV",
    "ho-tro-mai-tang-1116910": "1-K38biVwl2zRrbR3M__Qy0pSDYOgc1Cq",
    "dieu-chinh-huu-tri-xa-hoi": "1-KXJ_zW4hn6cFoo2jHj4gASsfPqGZQl3",
    "cap-giay-phep-xay-dung-moi-nha-o-rieng-le": "1ORJtRrL3ty313uHRQbGAeZJBDJliGhjl",
    "ket-hon-nuoc-ngoai": "1eYQXb3VsN20bOYFFkKPWR3Kaqcvy5ViK",
    "dang-ky-kinh-doanh": "1nkFVTbD-aPwaKLMK4_qoTf080CvgYEXq",
    "chung-thuc-chu-ky": "11KgBXkRJBDUJBC8EJJJZrONv0zZm2jH4",
    "dang-ky-lai-ket-hon": "1dCLFbXDjZgq1N2R42jxEkXE-KeyLuWLi",
    "dang-ky-giam-ho": "1xyKfpKX0WSlGBmC1ixHrB1XLLwWbsEU2",
    "dang-ky-nhan-cha-me-con": "17s-RDK0BtVP_XQIQZTBsm_b1PLMBuVmO",
    "khai-tu-dang-ky-lai": "1gfEicBzNG1N8_RPXP8F2E3P9qHNV5j6j",
    "khai-sinh-da-co-ho-so": "1go4rCp-Br5Zb5ja-V6Hm3869p4uhhBw8",
    "xac-dinh-muc-do-khuyet-tat": "1Jd9FvVWRSQb2fkaHxkcsojZzmnrPofuS",
    "uu-dai-ncc-tu-tran": "1tGc8cnFPhX7gaWOGAwb0Z5t8NFfBfi13",
    "cap-ban-sao-van-bang-so-goc": "1zJFnnRdDnPNSGvogPT2ZMwRallxgDhbk",
    "yeu-cau-tro-giup-phap-ly": "1Ibn6YCXw03vDsflSwx74xAw6aTqayYnU",
    "dang-ky-cham-dut-giam-ho": "1U3McFslAYPfQV9Fx7vZpitVcxFL0Dtxd",
    "doi-cap-lai-giay-xac-nhan-khuyet-tat": "19jneTL-XRrmqz0-1boAdcdrSrLuv_n_w",
    "dang-ky-hanh-nghe": "1noRcH9RXzM7WRuC7A_YeTpsOymSwtaV0",
    "cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te": "1i9d4XLg4pZ658KA_MEIAC6qiKDbJZXd0",
    "di-chuyen-ho-so-nguoi-huong-tro-cap": "1RBzuyK8hJmE6Hzunvz9gN_vwKth_UFjv",
    "chung-thuc-giao-dich-tai-san": "1zmHHBGqmKvwQ2UNV13OJsI1KMXGxU8rd",
    "chung-thuc-phan-chia-di-san": "1OdeaVW389V0G4ELt2oJLAVBMYWdw9bqH",
    "chung-thuc-tu-choi-nhan-di-san": "16EguoFOnn3-grra3qMZUXHD4OBssDSkh",
    "chung-thuc-di-chuc": "1WeGi4P4TGrr92dNBEOjb4mkld19uF9RX",
    "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich": "14r9iWkv61mF00DV0xPr0tALU0G-abnpC",
    "chung-thuc-chu-ky-nguoi-dich-ctv": "1w3yqMBa9KnJ5n57sDh5vtIr4LtxzGelQ",
    "cap-ban-sao-so-goc": "1JjmwEVy0iR29rvOve1OXR_tK7mU108PM",
    "bau-to-truong-to-hoa-giai": "1EvXp7LtrPeK2zU9Ow0-E3AjlxTCdVFjv",
    "xac-nhan-thong-tin-ho-tich": "1WLuWT1MqITyX8IdsvpNmgxp84IpwCfMZ",
    "chung-thuc-chu-ky-nguoi-dich-khong-ctv": "1kAXCbfAp_yojO99FfVA9rDKii95hlgiI",
    "cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su": "1JaH3n4ynifkDHrEI4gEhSN1WkMsRqCB1",
    "dang-ky-nuoi-con-nuoi-trong-nuoc": "1kzwhFa08Oh3pjJw3IifNtFSrGAKakqhr",
    "cap-moi-giay-phep-hanh-nghe-chuyen-tiep": "1KumQ5tVo-DN40kkWw-xC8PERxrZtzNam",
    "dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep": "12kKYIFbtGNGaS0EcPEjpGwe5vxxXtwVf",
    "cap-lai-giay-phep-hanh-nghe-truoc-2024": "1PBpgeS9Ck68wbvDaxqptiMejJGNNiVbB",
    "cap-moi-giay-phep-hoat-dong-kham-benh-chua-benh": "1lHADxAbbec67gJ-ipKcrslM2851xsJda",
    "dieu-chinh-giay-phep-hoat-dong-kcb": "1vex-ipG6oOqF68aVk1hlsBUWQrGznfqf",
    "cap-chung-chi-hanh-nghe-duoc": "1FjMj-2c5avOpfzIIOptJfLbm_wa3260f",
    "cong-bo-co-so-du-dieu-kien-tiem-chung": "1cfEza6p82akH1WRxFXSJpQTSECYl8yf3",
    "cap-lai-to-quoc-ghi-cong": "19i4wQTMN-LKn47OwU7tZH8chwroG-AJu",
    "cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong": "1kui3Ah2HwSo-wmoqYBT3YKXvi9WYy6sv",
    "bo-sung-than-nhan-liet-si": "19inb6kr64sBz933Rsf867dH-T4--KCa2",
    "tham-vieng-mo-liet-si": "1SoKUS5aQJnWbCy_aPrx5AcJP4NgjTVz5",
    "giai-quyet-che-do-khang-chien": "1EOU-FByoS1pp7Ad0T3lgXnXCwNEWIQna",
    "sua-doi-thong-tin-ho-so-nguoi-co-cong": "1fKhfXW_qlu4ISZ7S1x-wrib3Ttv8qNSt",
    "mai-tang-dan-cong-hoa-tuyen": "1fxYwqzaxWPZwO5G6KuSQIZ2v2IipQr5Z",
    "dang-ky-noi-quy-lao-dong": "1Fxzg_pX1nYR-b8JfKAStWdoLRrAwZxDG",
    "mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc": "1qa7Mp22YYEM3zsiJMusVH-uOsV2gmX6o",
    "cung-cap-thong-tin-quy-hoach": "1FFJ_R8MnRpxB0A-IbWMb0g1frtIIm9fe",
    "cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san": "1SvVKk7I4miZ-FqAUvj1W0ok5rqaPZklN",
    "cap-phep-long-duong-via-he": "1DiliuPSz7j8HqpFk4tvtnopUFHPR9aEB",
    "cho-thue-thue-mua-nha-o-xa-hoi": "1k9-w93efKijs12F8hNTcTqEuLIgUFWEE",
    "cap-giay-phep-chat-ha-cay-xanh": "1jZB1r7lXeBC5YX-_PUUNJ6G7ofn5NQ-B",
    "chap-thuan-dau-noi-tam": "1ihKybJf-RK3LJUSg9iv8hZUzeGGHwHIz",
    "dang-ky-lai-phuong-tien-chuyen-quyen-so-huu-khong-doi-co-quan": "1Mou3jefByWfL4QmuEtD_ttuOvYLZzfXH",
    "sua-chua-cai-tao-gpxd-nha-o-rieng-le": "1MbZYhrbrfMNsx-edOgsi-Add6BFHpSUV",
    "sua-chua-cai-tao-gpxd-cong-trinh": "1MbZYhrbrfMNsx-edOgsi-Add6BFHpSUV",
    "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang": "1-KXJ_zW4hn6cFoo2jHj4gASsfPqGZQl3",
    "ho-tro-mai-tang-huu-tri-xa-hoi": "1GDoz34QhFI0mZxz6DxTSaU6_hD--Z9cA",
    "khai-sinh-ket-hop-nhan-cha-me-con": "1-4NCHDIL3KsYk3kiH2B-Xrb2RT7B_SV4",
    "ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat": "1Jvj6RVyw83klTWHRsAd-T-F0nNwphjEu",
    "khai-tu-lien-thong": "1ObCm2c2aH-sottJ3cP3UF_ZVIgnxFlvg",
    "cap-lai-chung-chi-hanh-nghe-thu-y": "1wIThquCWO04dMsjeYrrcthN7m6W3eWdZ",
    "cap-gcn-attp-nong-lam-thuy-san": "10umD5SFiBICTv8UHhjtOpek4ej7fwpgP",
    "thong-bao-phat-trien-nguon-dien-mat-troi-mai-nha": "133r-yPbvsIS_EkyFRhndszCMruJdgqro",
    "gia-han-giay-phep-xay-dung": "11XSVJ3DqZM3xS8kydbstt6rV6jc4pwFj",
    "cap-bo-sung-xe-tap-lai-cap-lai-giay-phep-xe-tap-lai": "14Dp3Pli0LsMQtLR9s7xDEYkZqYutAmpD",
    "cap-cap-lai-phu-hieu-xe-kinh-doanh-van-tai": "1VFWUcWo4Pnt0Hsgrjo2O3I6EjSIdOjWS",
    "dang-ky-bien-phap-bao-dam-bac-ninh": "1KqOohCb11PSnrdn6P2Mgzc0Z_VGGPmX_",
    "xoa-dang-ky-bien-phap-bao-dam-bac-ninh": "1FaqOgduTY9jWAs451OunYRu4Z99KZIYZ",
    "dang-ky-bien-dong-thoa-thuan-bac-ninh": "1zTl3Js7W0Ri6Td2QXIZPTWoaZGnJ8Gws",
    "dang-ky-bien-dong-dat-dai-bac-ninh": "108-0a8trlUmIIZuBqLmqXyJWMNyURRZx",
    "dang-ky-bien-dong-chuyen-nhuong-bac-ninh": "108-0a8trlUmIIZuBqLmqXyJWMNyURRZx",
    "ho-tro-chi-phi-hoa-tang-bac-ninh": "1ql6VHXFI8p3ia3qBmglHJD148Voys4u0",
    "ho-tro-nguoi-cao-tuoi-bac-ninh": "1j3prF7eQQdxmPn9TKQ2CyEg3a9wTbqC_",
    "dinh-chinh-gcn-da-cap-bac-ninh": "1d1CmmcR7a2HuGbaI8Co2iG9BKv3a1ohE",
    "dinh-chinh-gcn-da-cap-1115476-bac-ninh": "1k3TnymmUiY532Qfuy2Erw0KGraUd10ah",
    "dinh-chinh-sai-sot-bac-ninh": "1YZPRNi7p5nPfbvishwF3OkbGyDcaISec",
    "tach-hop-thua-dat-bac-ninh": "13NIfvl9S0H0VS2ECX-p7pvt-TQrpblQ6",
    "cap-doi-gcn-bac-ninh": "1EgMqWXq9pNIVf4yDr8jbUsTcu80m3zTc",
    # Sheet tổng hợp ghi tráo link hai dòng này; gắn theo tên video.
    "dang-ky-dat-dai-lan-dau-bac-ninh": "1EYa2OVeEAf2Gmlb7LKG1xpMwsIRJxc8L",
    "giao-thue-chuyen-muc-dich-dat-bac-ninh": "1kC_hPsAnMiFA_3roT2jEZMh-HnKK27E1",
    "thu-hoi-gcn-cap-sai-bac-ninh": "14mVZlc66NzxOv-hogmR8R8WS99g6-eXk",
    "dang-ky-nha-o-xa-hoi-bac-ninh": "18ORgS2a2_rgONFrBkBh83XDuCsatwJ9s",
}

_QN_LINKS_BY_CODE = {
    str(_qn_link["code"]): _qn_link for _qn_link in core_ke_khai_links.KE_KHAI_LINKS
    if _qn_link.get("code") and str(_qn_link.get("label") or "").startswith("Quảng Ninh - ")
}
# Cơ quan chọn ở ô thứ hai sau khi gạt "Sở", theo tỉnh — lấy THẲNG từ ke_khai_links (soAgencyByProvince), cùng nguồn
# với Auto Fill: vd Đà Nẵng 2.000591 nộp ở Chi cục An toàn thực phẩm thay vì Sở cổng điền sẵn.
_SO_AGENCY_BY_KEY = {
    str(_link["key"]): _link["soAgencyByProvince"] for _link in core_ke_khai_links.KE_KHAI_LINKS
    if _link.get("key") and _link.get("soAgencyByProvince")
}
# Thẻ "Nộp trực tuyến" phải bấm theo XÃ của tài khoản — lấy THẲNG từ ke_khai_links (submitCardIncludesByWard), cùng
# nguồn với Auto Fill: vd Khánh Hòa 1.012783 ra thẻ VPĐK tỉnh + từng Chi nhánh VPĐK đất đai, xã nào vào chi nhánh nấy.
_CARD_BY_WARD_BY_KEY = {
    str(_link["key"]): _link["submitCardIncludesByWard"] for _link in core_ke_khai_links.KE_KHAI_LINKS
    if _link.get("key") and _link.get("submitCardIncludesByWard")
}

for _procedure in PROCEDURES:
    if (_BYT_HOST in ((_procedure.get("detect") or {}).get("urlScope") or [])
            and "guidedSteps" not in _procedure):
        _procedure["guidedSteps"] = deepcopy(_BYT_GUIDED_STEPS)
        _procedure["wizard"] = {**(_procedure.get("wizard") or {}), "resultStep": _BYT_RESULT_STEP}
    # Mọi thủ tục trang nộp hồ sơ 4 tab cùng trang của cổng Bắc Ninh (cùng khuôn): luồng tab mới, hỏi cơ quan tiếp nhận;
    # thủ tục có khối người ủy quyền thì hỏi có điền không. Thủ tục tự khai giá trị (kể cả False) thì giữ nguyên.
    if (_BN_HOST in ((_procedure.get("detect") or {}).get("urlScope") or [])
            and _procedure.get("samePageAttach")):
        _procedure.setdefault("bacNinhTabFlow", deepcopy(_BN_TAB_FLOW))
        _procedure.setdefault("bacNinhAgencyAsk", True)
        _procedure.setdefault("bacNinhAuthorizedAsk", bool(_procedure.get("bacNinhAuthorizedPerson")))
    # Thủ tục đặc thù Quảng Ninh: link kê khai DVCQG + chặng cổng tỉnh lấy THẲNG từ ke_khai_links theo mã — cùng nguồn
    # với Auto Fill, đổi chi nhánh tiếp nhận ở đó là trợ lý đổi theo. Entry tự khai thì giữ nguyên.
    if _QN_HOST in ((_procedure.get("detect") or {}).get("urlScope") or []):
        _qn_link = _QN_LINKS_BY_CODE.get(str(_procedure.get("code") or "")) or {}
        _procedure.setdefault("keKhaiUrl", _qn_link.get("url") or "")
        if _qn_link.get("provincePortalFlow"):
            _procedure.setdefault("provincePortalFlow", deepcopy(_qn_link["provincePortalFlow"]))
        _procedure.setdefault(
            "uploadHint", (core_registry.get_procedure(_procedure["key"]) or {}).get("uploadHint") or "",
        )
    if _procedure.get("agencySoFirst") and _procedure["key"] in _SO_AGENCY_BY_KEY:
        _procedure.setdefault("agencySoByProvince", deepcopy(_SO_AGENCY_BY_KEY[_procedure["key"]]))
    if _procedure["key"] in _CARD_BY_WARD_BY_KEY:
        _procedure.setdefault("agencyCardIncludesByWard", deepcopy(_CARD_BY_WARD_BY_KEY[_procedure["key"]]))
    if _procedure["key"] in _HUONG_DAN_DRIVE_ID:
        _procedure["guideUrl"] = _HUONG_DAN_DRIVE_URL.format(_HUONG_DAN_DRIVE_ID[_procedure["key"]])

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

# Thủ tục "Hoàn thiện phần mềm" theo tỉnh — chép từ bảng theo dõi thủ tục (thu-tuc-20261110-1155.xlsx, xuất
# 10/11/2026; "STT" ở chú thích = cột STT của bảng). Bảng có cột cho 11 tỉnh ở _TINH_THEO_DOI: tài khoản thuộc
# một tỉnh trong đó chỉ thấy + gọi được thủ tục mà cột tỉnh ấy ghi "Hoàn thiện phần mềm" (Chưa cập nhật / Chưa
# có / Đã BA / Pending đều ẩn). Tỉnh ngoài bảng hoặc tài khoản thiếu tỉnh → không lọc (như provinceOnly).
# Lọc này CỘNG THÊM vào provinceOnly: bản riêng của tỉnh ghi _TAT_CA vẫn chỉ hiện ở tỉnh trong provinceOnly.
# Key vắng bảng = chưa hoàn thiện ở cả 11 tỉnh → thủ tục mới đưa lên trợ lý phải thêm dòng ở đây mới hiện.
_TINH_THEO_DOI = (
    "laichau", "bacninh", "lamdong", "danang", "quangninh", "ninhbinh",
    "quangngai", "laocai", "quangtri", "khanhhoa", "tuyenquang",
)
_TAT_CA = frozenset(_TINH_THEO_DOI)
_HOAN_THIEN_THEO_TINH: dict[str, frozenset[str]] = {
    "khai-sinh-dang-ky": _TAT_CA,  # STT 10 (bảng ghi mã 2.000986)
    "khai-sinh-dang-ky-thuong": _TAT_CA,
    "ket-hon": _TAT_CA,
    "dang-ky-giam-ho": _TAT_CA,
    "dang-ky-cham-dut-giam-ho": _TAT_CA,
    "trich-luc-ks": _TAT_CA,
    "ket-hon-nuoc-ngoai": _TAT_CA,
    "dang-ky-lai-ket-hon": _TAT_CA,
    "khai-sinh-dang-ky-lai": _TAT_CA,
    "khai-sinh-da-co-ho-so": _TAT_CA,
    "khai-tu": _TAT_CA,
    # STT 110: Tuyên Quang Chưa cập nhật. Khánh Hòa bảng vẫn ghi Chưa cập nhật nhưng user mở 10/11/2026.
    "khai-tu-lien-thong": _TAT_CA - {"tuyenquang"},
    "khai-tu-dang-ky-lai": _TAT_CA,
    "dang-ky-nhan-cha-me-con": _TAT_CA,
    "khai-sinh-ket-hop-nhan-cha-me-con": _TAT_CA,
    "dang-ky-nuoi-con-nuoi-trong-nuoc": _TAT_CA,
    "thay-doi-cai-chinh-ho-tich": _TAT_CA,
    "xac-nhan-tinh-trang-hon-nhan": _TAT_CA,
    "xac-nhan-thong-tin-ho-tich": _TAT_CA,
    "dang-ky-kinh-doanh": _TAT_CA,
    "chung-thuc-ban-sao": _TAT_CA,
    "chung-thuc-giao-dich-tai-san": _TAT_CA,
    "chung-thuc-phan-chia-di-san": _TAT_CA,
    "chung-thuc-tu-choi-nhan-di-san": _TAT_CA,
    "chung-thuc-di-chuc": _TAT_CA,
    "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich": _TAT_CA,
    # STT 155 ghi mã 2.000992 nhưng tên là bản "không phải CTV" → giữ cả hai bản
    "chung-thuc-chu-ky-nguoi-dich-ctv": _TAT_CA,
    "chung-thuc-chu-ky-nguoi-dich-khong-ctv": _TAT_CA,  # STT 155 (xem dòng trên)
    "chung-thuc-chu-ky": _TAT_CA,
    "cap-ban-sao-so-goc": _TAT_CA,
    "bau-to-truong-to-hoa-giai": _TAT_CA,
    "yeu-cau-tro-giup-phap-ly": _TAT_CA,
    "cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su": _TAT_CA,
    "dang-ky-tham-du-kiem-tra-ket-qua-tap-su-hanh-nghe-cong-chung": _TAT_CA,
    "cap-giay-phep-khai-thac-thuy-san": _TAT_CA,
    # STT 118: Bắc Ninh Pending; Khánh Hòa, Tuyên Quang Chưa cập nhật
    "cap-gcn-dang-ky-tau-ca": _TAT_CA - {"bacninh", "khanhhoa", "tuyenquang"},
    # STT 122: Bắc Ninh Pending; Khánh Hòa, Tuyên Quang Chưa cập nhật
    "cap-van-ban-chap-thuan-tau-ca": _TAT_CA - {"bacninh", "khanhhoa", "tuyenquang"},
    "cap-lai-chung-chi-hanh-nghe-thu-y": _TAT_CA,
    "ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat": frozenset(),  # không có trong bảng
    "hoa-giai-tranh-chap-dat-dai": frozenset(),  # không có trong bảng
    "cap-ban-sao-van-bang-so-goc": _TAT_CA,
    "mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc": _TAT_CA,
    "cho-thue-thue-mua-nha-o-xa-hoi": frozenset({"danang"}),  # STT 147: chỉ Đà Nẵng hoàn thiện
    "dieu-chinh-huu-tri-xa-hoi": _TAT_CA,
    "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham": _TAT_CA,
    "cap-gcn-attp-nong-lam-thuy-san": _TAT_CA,
    "cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te": _TAT_CA,
    "dang-ky-hanh-nghe": _TAT_CA,
    "dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep": _TAT_CA,
    "cap-moi-giay-phep-hanh-nghe-chuyen-tiep": _TAT_CA - {"tuyenquang"},  # STT 64: Tuyên Quang Chưa cập nhật
    "cap-moi-giay-phep-hoat-dong-kham-benh-chua-benh": _TAT_CA,
    "cap-lai-giay-phep-hanh-nghe-truoc-2024": frozenset({"danang"}),  # STT 66: chỉ Đà Nẵng hoàn thiện
    "dieu-chinh-giay-phep-hoat-dong-kcb": _TAT_CA,
    "cap-chung-chi-hanh-nghe-duoc": frozenset({"danang"}),  # STT 67: chỉ Đà Nẵng hoàn thiện
    "cong-bo-co-so-du-dieu-kien-tiem-chung": _TAT_CA,
    "di-chuyen-ho-so-nguoi-huong-tro-cap": frozenset({"danang"}),  # STT 124: chỉ Đà Nẵng hoàn thiện
    "tro-cap-tho-cung-liet-si": _TAT_CA,
    "cap-lai-to-quoc-ghi-cong": _TAT_CA,
    "cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong": _TAT_CA,
    "bo-sung-than-nhan-liet-si": _TAT_CA,
    "tham-vieng-mo-liet-si": _TAT_CA,
    "giai-quyet-che-do-khang-chien": _TAT_CA,
    "sua-doi-thong-tin-ho-so-nguoi-co-cong": _TAT_CA,
    "mai-tang-dan-cong-hoa-tuyen": _TAT_CA,
    "uu-dai-ncc-tu-tran": _TAT_CA,
    "xac-dinh-muc-do-khuyet-tat": _TAT_CA,
    "doi-cap-lai-giay-xac-nhan-khuyet-tat": _TAT_CA,
    "ho-tro-mai-tang-1116910": _TAT_CA,  # STT 36 (bảng ghi mã cũ 1.001731)
    "ho-tro-mai-tang-huu-tri-xa-hoi": _TAT_CA,
    "tro-cap-xa-hoi-hang-thang": _TAT_CA,
    "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang": _TAT_CA,
    "tiep-nhan-doi-tuong-can-bao-ve-khan-cap-vao-co-so-tro-giup-xa-hoi": _TAT_CA,
    "tiep-nhan-doi-tuong-bao-tro-xa-hoi-co-hoan-canh-dac-biet-kho-khan-vao-co-so-tro-giup-xa-hoi": _TAT_CA,
    "cap-giay-phep-xay-dung-moi-nha-o-rieng-le": _TAT_CA,
    "dieu-chinh-giay-phep-xay-dung": _TAT_CA,
    "sua-chua-cai-tao-gpxd-nha-o-rieng-le": _TAT_CA,
    "sua-chua-cai-tao-gpxd-cong-trinh": _TAT_CA,
    "cung-cap-thong-tin-quy-hoach": frozenset({"laichau", "bacninh"}),  # STT 98: chỉ Lai Châu, Bắc Ninh hoàn thiện
    "cap-phep-long-duong-via-he": frozenset({"danang"}),  # STT 138: chỉ Đà Nẵng hoàn thiện
    "cap-giay-phep-lien-van-viet-lao": _TAT_CA,
    "cap-giay-phep-chat-ha-cay-xanh": _TAT_CA,
    "chap-thuan-dau-noi-tam": frozenset(),  # không có trong bảng
    "gia-han-luu-hanh-phuong-tien-lao": _TAT_CA,
    "dang-ky-lai-phuong-tien-chuyen-quyen-so-huu-khong-doi-co-quan": frozenset(),  # không có trong bảng
    "cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san": _TAT_CA,
    "dang-ky-thay-doi-noi-dung-ho-kinh-doanh": _TAT_CA,
    "cham-dut-hoat-dong-ho-kinh-doanh": _TAT_CA,
    "tam-ngung-kinh-doanh": _TAT_CA,
    "cap-lai-cap-doi-gcn-ho-kinh-doanh": _TAT_CA,  # STT 106 (2.000575)
    "dang-ky-bien-phap-bao-dam-bac-ninh": _TAT_CA,
    "xoa-dang-ky-bien-phap-bao-dam-bac-ninh": _TAT_CA,
    "dinh-chinh-gcn-da-cap-bac-ninh": _TAT_CA,  # STT 103
    "dinh-chinh-gcn-da-cap-1115476-bac-ninh": _TAT_CA,  # STT 103
    "dang-ky-bien-dong-thoa-thuan-bac-ninh": _TAT_CA,  # STT 48
    "dang-ky-bien-dong-dat-dai-bac-ninh": _TAT_CA,
    "tach-hop-thua-dat-bac-ninh": _TAT_CA,  # STT 102
    "cap-doi-gcn-bac-ninh": _TAT_CA,  # STT 93
    "dang-ky-dat-dai-lan-dau-bac-ninh": _TAT_CA,  # STT 44
    "thu-hoi-gcn-cap-sai-bac-ninh": _TAT_CA,  # STT 101
    "dinh-chinh-sai-sot-bac-ninh": _TAT_CA,  # STT 43
    "giao-thue-chuyen-muc-dich-dat-bac-ninh": _TAT_CA,  # STT 99
    "dang-ky-bien-dong-chuyen-nhuong-bac-ninh": _TAT_CA,
    "ho-tro-nguoi-cao-tuoi-bac-ninh": _TAT_CA,
    "ho-tro-chi-phi-hoa-tang-bac-ninh": _TAT_CA,
    "dang-ky-nha-o-xa-hoi-bac-ninh": _TAT_CA,
    "dang-ky-tam-tru": frozenset(),  # không có trong bảng
    "dang-ky-noi-quy-lao-dong": _TAT_CA,
    "cap-gcn-diem-tro-choi-dien-tu-cong-cong": _TAT_CA,
    "ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang": _TAT_CA,
    "dang-ky-lap-dat-su-dung-nuoc-sach": _TAT_CA,
    "chuyen-doi-ten-hop-dong-nuoc-sach": _TAT_CA,
    "dang-ky-cap-giay-chung-nhan-doi-voi-toan-bo-dien-tich-dat-lai-chau": _TAT_CA,
    "chuyen-muc-dich-su-dung-dat-mien-nui-lai-chau": _TAT_CA,
    "giao-dat-cho-thue-dat-lai-chau": _TAT_CA,  # STT 178
    "cap-lai-giay-chung-nhan-do-bi-mat-lai-chau": _TAT_CA,  # STT 50
    "dang-ky-dat-dai-lan-dau-khanh-hoa": _TAT_CA,  # STT 44 + STT 229 (mã 1.013978)
    "giao-thue-chuyen-muc-dich-dat-khanh-hoa": _TAT_CA,
    "cap-doi-gcn-khanh-hoa": _TAT_CA,  # STT 93
    "dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-khanh-hoa": _TAT_CA,  # STT 41 + STT 208
    "dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn-khanh-hoa": _TAT_CA,  # STT 190
    "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-khanh-hoa": _TAT_CA,  # STT 207
    "dang-ky-dat-dai-lan-dau-tuyen-quang": _TAT_CA,  # STT 44 + STT 229 (mã 1.013978)
    "dinh-chinh-gcn-cap-lan-dau-sai-sot-tuyen-quang": _TAT_CA,
    "giao-thue-chuyen-muc-dich-dat-giao-rung-gia-han-tuyen-quang": _TAT_CA,
    "thong-bao-san-pham-quang-cao-bang-ron": _TAT_CA,
    "cap-giay-phep-xuat-ban-tai-lieu-khong-kinh-doanh": _TAT_CA,
    "cap-the-huong-dan-vien-du-lich-noi-dia": _TAT_CA,
    "cap-chung-chi-hanh-nghe-bao-quan-tu-bo-phuc-hoi-di-tich": _TAT_CA,
    "cap-lai-chung-chi-hanh-nghe-bao-quan-tu-bo-phuc-hoi-di-tich": _TAT_CA,
    "to-chuc-bieu-dien-nghe-thuat": _TAT_CA,
    "cap-giay-chung-nhan-khoa-cap-nhat-kien-thuc-huong-dan-vien-du-lich": _TAT_CA,
    "cap-the-huong-dan-vien-du-lich-tai-diem-da-nang": _TAT_CA,  # STT 194 (1.001440)
    "cap-doi-the-huong-dan-vien-du-lich-da-nang": _TAT_CA,  # STT 193 (1.001432)
    "cap-lai-the-huong-dan-vien-du-lich-da-nang": _TAT_CA,  # STT 192 (1.004614)
    "dang-ky-khuyen-mai-may-rui-mot-tinh": _TAT_CA,  # STT 195 (2.000004)
    "xoa-dang-ky-phuong-tien-thuy": _TAT_CA,  # STT 126 (2.001659)
    "gia-han-giay-phep-xay-dung": _TAT_CA,
    "cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham": _TAT_CA,
    "cap-gcn-attp-cong-thuong": _TAT_CA,
    "thong-bao-sua-doi-bo-sung-noi-dung-chuong-trinh-khuyen-mai": _TAT_CA,
    "thong-bao-phat-trien-nguon-dien-mat-troi-mai-nha": frozenset(),  # không có trong bảng
    "xet-tuyen-vien-chuc": frozenset({"laichau"}),  # STT 88: chỉ Lai Châu hoàn thiện
    "xet-tuyen-cong-chuc": frozenset({"laichau"}),  # STT 80: chỉ Lai Châu hoàn thiện
    "thi-tuyen-cong-chuc": frozenset({"laichau"}),  # STT 81: chỉ Lai Châu hoàn thiện
    "gia-han-chung-chi-hanh-nghe-thu-y": _TAT_CA,
    # STT 120: Bắc Ninh Pending; Khánh Hòa, Tuyên Quang Chưa cập nhật
    "xoa-dang-ky-tau-ca": _TAT_CA - {"bacninh", "khanhhoa", "tuyenquang"},
    "chia-tach-sap-nhap-hop-nhat-hoi-cap-tinh": _TAT_CA,
    "bao-cao-to-chuc-dai-hoi-hoi-cap-tinh": _TAT_CA,
    "thong-bao-ket-qua-dai-hoi-phe-duyet-dieu-le-hoi-cap-tinh": frozenset(),  # không có trong bảng
    "dang-ky-nha-o-xa-hoi-tuyen-quang": _TAT_CA,
    "tham-dinh-bcnckt": _TAT_CA,
    "cap-bo-sung-xe-tap-lai-cap-lai-giay-phep-xe-tap-lai": _TAT_CA,
    "cap-cap-lai-phu-hieu-xe-kinh-doanh-van-tai": _TAT_CA,
    # STT 197: chỉ Quảng Ngãi hoàn thiện
    "xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru": frozenset({"quangngai"}),
    "dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao": _TAT_CA,
    "dang-ky-bien-dong-chuyen-nhuong-quang-ninh-mien-nui-hai-dao": _TAT_CA,
    "chuyen-muc-dich-su-dung-dat-quang-ninh-mien-nui-hai-dao": _TAT_CA,  # STT 154 (bảng ghi mã 1.115860)
    "cap-doi-gcn-quang-ninh-mien-nui-hai-dao": _TAT_CA,
    "cap-doi-gcn-do-do-dac-khong-nvtc-quang-ninh-mien-nui-hai-dao": _TAT_CA,
    "tach-hop-thua-dat-quang-ninh-mien-nui-hai-dao": _TAT_CA,
    "dang-ky-tai-san-dat-quang-ninh-mien-nui-hai-dao": _TAT_CA,
    "dang-ky-bien-dong-doi-ten-quang-ninh-mien-nui-hai-dao": _TAT_CA,
    "dang-ky-cap-gcn-toan-bo-dien-tich-dang-su-dung-quang-ninh": frozenset(),  # STT 225: Quảng Ninh Chưa có
    "tinh-tien-su-dung-dat-nd-50-2026-quang-ninh": _TAT_CA,
    "cap-lai-gcn-do-bi-mat-quang-ninh": _TAT_CA,
    # STT 55: Quảng Ninh Chưa cập nhật
    "dang-ky-bien-dong-chuyen-muc-dich-sdd-khong-xin-phep-quang-ninh": frozenset(),
    "xoa-dang-ky-bien-phap-bao-dam-quang-ninh": _TAT_CA,
    "dang-ky-bien-phap-bao-dam-quang-ninh": frozenset(),  # STT 113: Quảng Ninh Chưa cập nhật
}


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
    for key in _HUONG_DAN_DRIVE_ID:
        if key not in _BY_KEY:
            raise RuntimeError(f"_HUONG_DAN_DRIVE_ID có key không tồn tại: {key}")
    for key, slugs in _HOAN_THIEN_THEO_TINH.items():
        if key not in _BY_KEY:
            raise RuntimeError(f"_HOAN_THIEN_THEO_TINH có key không tồn tại: {key}")
        if not slugs <= _TAT_CA:
            raise RuntimeError(f"_HOAN_THIEN_THEO_TINH[{key}] có tỉnh ngoài _TINH_THEO_DOI: {sorted(slugs - _TAT_CA)}")
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


def is_ready_in_province(proc: dict | None, province_slug: str | None) -> bool:
    """Tỉnh `province_slug` đã "Hoàn thiện phần mềm" thủ tục này chưa (bảng _HOAN_THIEN_THEO_TINH).

    Chỉ xét 11 tỉnh có cột trong bảng theo dõi; tỉnh khác / tài khoản thiếu tỉnh → True (không lọc,
    như is_allowed_in_province). Key vắng bảng = chưa hoàn thiện ở cả 11 tỉnh.
    """
    if not proc:
        return False
    if province_slug not in _TINH_THEO_DOI:
        return True
    return province_slug in _HOAN_THIEN_THEO_TINH.get(proc["key"], frozenset())


def is_visible_in_province(proc: dict | None, province_slug: str | None) -> bool:
    """Tài khoản tỉnh `province_slug` thấy + gọi được thủ tục: đúng tỉnh (provinceOnly) VÀ tỉnh đã hoàn thiện."""
    return is_allowed_in_province(proc, province_slug) and is_ready_in_province(proc, province_slug)


def public_list_for(province_slug: str | None) -> list[dict]:
    """public_list() đã lọc theo tỉnh account — bỏ thủ tục khóa tỉnh khác + thủ tục tỉnh này chưa hoàn thiện."""
    return [p for p in public_list() if is_visible_in_province(p, province_slug)]
