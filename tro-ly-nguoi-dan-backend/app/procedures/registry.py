"""Danh mục thủ tục: key, label, roles, useDangKyBy.

Bản Trợ lý người dân: 5 thủ tục pilot (chốt 2026-07-21, docs/01-be-skeleton.md)
+ khai-tu, dang-ky-lai-ket-hon, dang-ky-nhan-cha-me-con, ket-hon-nuoc-ngoai (2026-08,
ẩn khỏi card gợi ý — gọi tên/detect vẫn chạy). Thêm thủ tục = entry + import + 2 map.

`_PIPELINE` map key → module pipeline xử lý (process); `_ATTACH_PIPELINE` → đính kèm.
"""
# Pipeline theo thủ tục (package-by-feature, app/pipelines/<thủ tục>/{process,attach}).
from app.pipelines.khai_sinh_lien_thong.attach import plan as khai_sinh_lien_thong_attach
from app.pipelines.khai_sinh_lien_thong.process import run as khai_sinh_lien_thong_process
from app.pipelines.ket_hon.attach import plan as ket_hon_attach
from app.pipelines.ket_hon.process import run as ket_hon_process
from app.pipelines.ket_hon_lai.attach import plan as ket_hon_lai_attach
from app.pipelines.ket_hon_lai.process import run as ket_hon_lai_process
from app.pipelines.ket_hon_nuoc_ngoai.attach import plan as ket_hon_nuoc_ngoai_attach
from app.pipelines.ket_hon_nuoc_ngoai.process import run as ket_hon_nuoc_ngoai_process
from app.pipelines.khai_tu.attach import plan as khai_tu_attach
from app.pipelines.khai_tu.process import run as khai_tu_process
from app.pipelines.khai_tu_dang_ky_lai.attach import plan as khai_tu_dang_ky_lai_attach
from app.pipelines.khai_tu_dang_ky_lai.process import run as khai_tu_dang_ky_lai_process
from app.pipelines.khai_sinh_dang_ky_lai.attach import plan as khai_sinh_dang_ky_lai_attach
from app.pipelines.khai_sinh_dang_ky_lai.process import run as khai_sinh_dang_ky_lai_process
from app.pipelines.nhan_cha_me_con.attach import plan as nhan_cha_me_con_attach
from app.pipelines.nhan_cha_me_con.process import run as nhan_cha_me_con_process
from app.pipelines.dang_ky_giam_ho.attach import plan as dang_ky_giam_ho_attach
from app.pipelines.dang_ky_giam_ho.process import run as dang_ky_giam_ho_process
from app.pipelines.trich_luc.attach import plan as trich_luc_attach
from app.pipelines.trich_luc.process import run as trich_luc_process
from app.pipelines.xac_nhan_tthn.attach import plan as xac_nhan_tthn_attach
from app.pipelines.xac_nhan_tthn.process import run as xac_nhan_tthn_process
from app.pipelines.chung_thuc_ban_sao.attach import plan as chung_thuc_ban_sao_attach
from app.pipelines.chung_thuc_chu_ky.attach import plan as chung_thuc_chu_ky_attach

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
        # Cổng React MỚI dichvucong.gov.vn: trang chi tiết thủ tục → khối "Chọn cơ quan
        # thực hiện" (tỉnh + xã) → Đồng ý → kê khai. Engine: content/portal-dvc.js.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fac-7489-b53b-a15eb239a6fe",
        "needsAgencySelect": True,
        # optional:true = KHÔNG tính vào điều kiện "đã đủ" — kết hôn còn tờ khai, giấy tờ khác...
        # có slot tuỳ chọn thì phiên KHÔNG tự chốt, chờ người dân bấm Xong.
        "requiredDocs": [
            {"key": "cccd_nam", "name": "CCCD bên nam", "icon": "🪪", "sides": 2},
            {"key": "cccd_nu", "name": "CCCD bên nữ", "icon": "🪪", "sides": 2},
            {"key": "to_khai", "name": "Tờ khai đăng ký kết hôn (nếu có)", "icon": "📄", "sides": 1, "optional": True},
            {"key": "khac", "name": "Giấy tờ chứng minh tình trạng hôn nhân / giấy tờ khác (nếu có)",
             "icon": "📎", "sides": 5, "optional": True},
        ],
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần: process chụp tokens+bbox, phơi qua /api/v1/review
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của bên nam.\n"
            "2. CCCD của bên nữ.\n"
            "Không cần chọn trước giấy tờ là của chồng hay vợ; hệ thống tự phân biệt theo giới tính trên CCCD.\n"
            "Bước 3: hệ thống có thể đính kèm CCCD bên nam/bên nữ vào thành phần hồ sơ mới."
        ),
    },
    {
        "key": "dang-ky-giam-ho",
        "detect": {"textIncludes": ["Thủ tục đăng ký giám hộ"], "headingDisabled": True},
        "label": "Thủ tục đăng ký giám hộ",
        "shortLabel": "Đăng ký Giám hộ",
        "subtitle": "Đăng ký giám hộ cho người được giám hộ",
        "icon": "🤝",
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-671b-75fa-82fb-8ad05a37f638",
        "mode": "agent",
        "hasAttachmentStep": True,
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
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-867c-72db-b6a7-dcbd8c763807",
        "needsAgencySelect": True,
        # TỜ KHAI là giấy CHÍNH (chứa đủ thông tin sự kiện hộ tịch để kê khai); giấy hộ tịch
        # cũ chỉ bổ trợ khi có — thực tế CCCD + tờ khai là fill trọn form.
        "requiredDocs": [
            {"key": "cccd", "name": "CCCD của người yêu cầu", "icon": "🪪", "sides": 2},
            {"key": "to_khai", "name": "Tờ khai cấp bản sao trích lục hộ tịch", "icon": "📄", "sides": 1},
            {"key": "ho_tich", "name": "Giấy tờ hộ tịch cũ: giấy khai sinh / giấy chứng nhận "
             "kết hôn / trích lục khai tử (nếu có)", "icon": "📜", "sides": 1},
            {"key": "khac", "name": "Văn bản ủy quyền / giấy tờ khác (nếu có)",
             "icon": "📎", "sides": 5, "optional": True},
        ],
        # Chế độ agent: không gắn role, BE tự suy luận từ text OCR.
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần (doc-type đã theo cơ quan cấp sẵn)
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người yêu cầu.\n"
            "2. Giấy tờ hộ tịch cần cấp bản sao: giấy khai sinh, giấy đăng ký kết hôn hoặc trích lục khai tử.\n"
            "3. Nếu có: văn bản ủy quyền hoặc giấy tờ chứng minh cư trú."
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
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN/trích lục/khai tử.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e13-728a-a0cd-635811d8432e",
        "needsAgencySelect": True,
        # Giấy tờ nước ngoài (hộ chiếu/CMND nước khác) OCR có thể không tự nhận loại →
        # bà con bấm 📸 theo dòng (hint) hoặc rơi vào "khác"; pipeline vẫn dùng đủ file.
        "requiredDocs": [
            {"key": "cccd_nam", "name": "Giấy tờ tùy thân bên nam (CCCD / hộ chiếu nước ngoài)",
             "icon": "🪪", "sides": 2},
            {"key": "cccd_nu", "name": "Giấy tờ tùy thân bên nữ (CCCD / hộ chiếu nước ngoài)",
             "icon": "🪪", "sides": 2},
            {"key": "khac", "name": "Giấy xác nhận tình trạng hôn nhân nước ngoài / khám tâm thần / "
             "giấy tờ khác (nếu có)", "icon": "📎", "sides": 5, "optional": True},
        ],
        "mode": "agent",
        "hasAttachmentStep": True,
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
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN/trích lục/khai tử.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6711-733d-b674-f82cb6606242",
        "needsAgencySelect": True,
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
        "hasAttachmentStep": True,
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
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/khai tử/TTHN/trích lục.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6eac-7598-b88b-15f8a61b366a",
        "needsAgencySelect": True,
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
        "hasAttachmentStep": True,
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đăng ký lại khai sinh (nếu có).\n"
            "2. Các giấy tờ khác: CCCD của cha/mẹ, bản sao/trích lục giấy khai sinh cũ, "
            "giấy tờ thay thế (học bạ, hộ chiếu…) — bà con đưa hết vào mục Giấy tờ khác.\n"
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
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN/trích lục.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fac-7489-b53b-9c6c958f2da4",
        "needsAgencySelect": True,
        # Giấy báo tử BẮT BUỘC (nguồn chính của sự kiện chết); tờ khai bổ trợ khi có.
        "requiredDocs": [
            {"key": "cccd", "name": "CCCD của người yêu cầu", "icon": "🪪", "sides": 2},
            {"key": "bao_tu", "name": "Giấy báo tử / giấy tờ thay Giấy báo tử", "icon": "📃", "sides": 1},
            {"key": "to_khai", "name": "Tờ khai đăng ký khai tử (nếu có)", "icon": "📄", "sides": 1,
             "optional": True},
        ],
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người yêu cầu.\n"
            "2. Giấy báo tử/giấy chứng tử hoặc giấy tờ thay giấy báo tử.\n"
            "3. Tờ khai đăng ký khai tử bản giấy nếu có.\n"
            "Không cần chọn trước giấy tờ là CCCD, giấy báo tử hay tờ khai; hệ thống tự phân biệt theo nội dung OCR.\n"
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
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6ebc-709e-8678-a9f8b66738f2",
        "needsAgencySelect": True,
        # Cổng eForm hộ tịch dùng các component x-*; extension đã có fill-legacy tương ứng.
        "requiredDocs": [
            {"key": "to_khai", "name": "Tờ khai đăng ký lại khai tử bản giấy", "icon": "📄", "sides": 1, "optional": True},
            {"key": "cccd", "name": "CCCD/giấy tờ tùy thân của người yêu cầu và người đã chết", "icon": "🪪", "sides": 4},
            {"key": "bao_tu", "name": "Giấy chứng tử/trích lục khai tử hoặc giấy tờ chứng minh sự kiện chết", "icon": "📃", "sides": 5},
            {"key": "khac", "name": "Giấy tờ khác", "icon": "📎", "sides": 5, "optional": True},
        ],
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đăng ký lại khai tử bản giấy nếu có.\n"
            "2. CCCD/giấy tờ tùy thân của người yêu cầu và người đã chết.\n"
            "3. Giấy chứng tử, trích lục khai tử hoặc giấy tờ chứng minh sự kiện chết.\n"
            "4. Giấy tờ khác nếu có.\n"
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
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn/TTHN/trích lục/khai tử.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fa6-722f-ac1a-e949c8ce3418",
        "needsAgencySelect": True,
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
        "hasAttachmentStep": True,
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
        "key": "xac-nhan-tinh-trang-hon-nhan",
        "detect": {"urlIncludes": ["maThuTuc=1.004873"]},
        "label": "Thủ tục cấp Giấy xác nhận tình trạng hôn nhân",
        "shortLabel": "Xác nhận tình trạng hôn nhân",
        "subtitle": "Cấp giấy xác nhận độc thân / tình trạng hôn nhân",
        "icon": "💍",
        # Cổng React mới (Bộ Tư pháp) — cùng wizard với kết hôn: chọn cơ quan → Nộp trực
        # tuyến → modal Thông tin chung → chủ hồ sơ → kê khai.
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6eb3-7019-bf3f-fc58c9ee44b9",
        "needsAgencySelect": True,
        "requiredDocs": [
            {"key": "cccd", "name": "CCCD của người được cấp giấy xác nhận", "icon": "🪪", "sides": 2},
            {"key": "to_khai", "name": "Tờ khai cấp giấy xác nhận tình trạng hôn nhân (nếu có)",
             "icon": "📄", "sides": 1, "optional": True},
            {"key": "khac", "name": "Giấy tờ chứng minh: quyết định ly hôn / trích lục khai tử / "
             "giấy chứng nhận kết hôn (nếu có)", "icon": "📎", "sides": 5, "optional": True},
        ],
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,  # TẠM TẮT rà soát bbox (đỡ 1 lượt OCR token — pipeline nhanh hơn); bật lại khi cần
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người được cấp giấy xác nhận tình trạng hôn nhân.\n"
            "Mặc định người yêu cầu là bản thân; không cần chọn trước vai trò giấy tờ.\n"
            "Bước 3: hệ thống có thể đính kèm CCCD hoặc giấy tờ điều kiện vào thành phần hồ sơ phù hợp."
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
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e22-77ef-819f-e49460350904",
        "needsAgencySelect": True,
        # Thủ tục attach-only tại quầy đi thẳng từ Thành phần hồ sơ sang nhận tệp;
        # không hiển thị card xin consent và không tạo consent_logs.
        "requiresConsent": False,
        # Một loại duy nhất, nhận lặp không giới hạn. sides=1 chỉ là số tệp tối thiểu;
        # repeatable giữ phiên mở để người dân tiếp tục thêm tệp rồi chủ động bấm Đã đủ.
        "requiredDocs": [
            {"key": "khac", "name": "Giấy tờ cần chứng thực bản sao", "icon": "📄",
             "sides": 1, "repeatable": True},
        ],
        "mode": "attach",
        "hasAttachmentStep": True,
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
        "keKhaiUrl": "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e2e-7359-b42f-d5dc8d74741b",
        "needsAgencySelect": True,
        # Attach-only tại quầy: đi thẳng Thành phần hồ sơ → nhận tệp, KHÔNG card consent/consent_logs.
        "requiresConsent": False,
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
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Các giấy tờ, văn bản cần chứng thực chữ ký/điểm chỉ (không giới hạn số lượng).\n"
            "2. Căn cước công dân của người yêu cầu."
        ),
    },
]


# Map procedure key → hàm pipeline.run
_PIPELINE = {
    "khai-sinh-dang-ky": khai_sinh_lien_thong_process,
    "ket-hon": ket_hon_process,
    "ket-hon-nuoc-ngoai": ket_hon_nuoc_ngoai_process,
    "dang-ky-lai-ket-hon": ket_hon_lai_process,
    "khai-sinh-dang-ky-lai": khai_sinh_dang_ky_lai_process,
    "khai-tu": khai_tu_process,
    "khai-tu-dang-ky-lai": khai_tu_dang_ky_lai_process,
    "dang-ky-nhan-cha-me-con": nhan_cha_me_con_process,
    "dang-ky-giam-ho": dang_ky_giam_ho_process,
    "trich-luc-ks": trich_luc_process,
    "xac-nhan-tinh-trang-hon-nhan": xac_nhan_tthn_process,
}

# Map procedure key → hàm đính kèm (mỗi thủ tục thêm 1 dòng ở đây, router chỉ dispatch qua registry).
_ATTACH_PIPELINE = {
    "khai-sinh-dang-ky": khai_sinh_lien_thong_attach,
    "ket-hon": ket_hon_attach,
    "ket-hon-nuoc-ngoai": ket_hon_nuoc_ngoai_attach,
    "dang-ky-lai-ket-hon": ket_hon_lai_attach,
    "khai-sinh-dang-ky-lai": khai_sinh_dang_ky_lai_attach,
    "khai-tu": khai_tu_attach,
    "khai-tu-dang-ky-lai": khai_tu_dang_ky_lai_attach,
    "dang-ky-nhan-cha-me-con": nhan_cha_me_con_attach,
    "dang-ky-giam-ho": dang_ky_giam_ho_attach,
    "trich-luc-ks": trich_luc_attach,
    "xac-nhan-tinh-trang-hon-nhan": xac_nhan_tthn_attach,
    "chung-thuc-ban-sao": chung_thuc_ban_sao_attach,
    "chung-thuc-chu-ky": chung_thuc_chu_ky_attach,
}

_BY_KEY = {p["key"]: p for p in PROCEDURES}


def get_procedure(key: str) -> dict | None:
    return _BY_KEY.get(key)


def get_pipeline(key: str):
    return _PIPELINE.get(key)


def get_attach_pipeline(key: str):
    return _ATTACH_PIPELINE.get(key)


def public_list() -> list[dict]:
    return PROCEDURES
