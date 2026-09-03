"""Metadata và thứ tự thủ tục chỉ dành cho kênh Handfree.

Core process/attach luôn lấy từ ``app.procedures.registry``. File này được port từ
registry Handfree cũ để giữ nguyên card, flow profile và checklist, nhưng không còn
sở hữu bản sao pipeline nghiệp vụ.
"""
from app.channels.handfree.owner_info import run as tu_phap_owner_info
from app.channels.handfree.flow_profiles import resolve_flow_profile
from app.procedures import registry as core_registry

PROCEDURES: list[dict] = [
    {
        "key": "khai-sinh-dang-ky",
        # Liên thông nằm trên cổng riêng (lienthong.dichvucong.gov.vn), không có heading chuẩn
        # → nhận diện THEO URL (mã thủ tục 2.000986 trên route ke-khai).
        "detect": {
            "urlIncludes": ["lienthong.dichvucong.gov.vn/#/ke-khai/2.000986"],
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
        "keKhaiUrl": "https://lienthong.dichvucong.gov.vn/#/ke-khai/2.000986",
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
        "agencyFillPlan": [
            {"name": "IsNuocNgoai", "comp": "select", "value": "Không có yếu tố nước ngoài"},
            {"name": "CqdkksDiaChi", "comp": "diachi",
             "value": {"tinh": "{province}", "xa": "{ward}"}},
            {"name": "DkksTruongHop", "comp": "select", "value": "Đã xác định được cả cha lẫn mẹ"},
            {"name": "CqdkttIsDkks", "comp": "checkbox", "value": True},
            {"name": "DkttTruongHop", "comp": "select",
             "value": "Con về với cha, mẹ; cha, mẹ là chủ sở hữu chỗ ở hợp pháp"},
        ],
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
        # Chưa có URL định danh mới đã được xác minh nên không tạo card điều hướng hỏng.
        # Gọi tên thủ tục hoặc nhận diện URL cũ vẫn dispatch đúng pipeline.
        "hiddenFromList": True,
        "review": False,
        "mode": "agent",
        "hasAttachmentStep": True,
        # Client cũ không gửi option sẽ giữ nguyên từng file; chỉ boolean True mới tách theo trang.
        "supportsSplitDocuments": True,
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
        # Một loại duy nhất, nhận lặp không giới hạn. sides=1 chỉ là số tệp tối thiểu;
        # repeatable giữ phiên mở để người dân tiếp tục thêm tệp rồi chủ động bấm Đã đủ.
        "requiredDocs": [
            {"key": "khac", "name": "Giấy tờ cần chứng thực bản sao", "icon": "📄",
             "sides": 1, "repeatable": True},
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
    "trich-luc-ks",
    "xac-nhan-tinh-trang-hon-nhan",
    "khai-sinh-dang-ky-lai",
    "khai-tu",
    "dang-ky-kinh-doanh",
)
_PUBLIC_TRAILING_KEYS = (
    "chung-thuc-ban-sao",
    "chung-thuc-chu-ky",
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


def _validate_profile_dispatch() -> None:
    """Fail fast when a profiled procedure is missing one of its backend engines."""
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
