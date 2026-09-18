"""Lời thoại tiếng Việt của bot — TÁCH KHỎI logic (docs/03a §3, giọng theo prototype).

Quy ước: mỗi mục có `md` (hiện trong chat, được dùng markdown) và `tts` (đọc loa —
KHÔNG markdown, câu ngắn, số/tên đọc được). Sửa giọng điệu chỉ sửa file này.
{Chỗ trống} được flow.format() điền bằng str.format — đừng đổi tên biến trong ngoặc.
"""
# Card đánh giá dùng CHUNG với Auto Fill: phiếu gắn vào HỒ SƠ chứ không gắn vào hội thoại.
# Để mỗi kênh một bản là hai kênh hỏi khác câu rồi cộng chung vào một con số.
from app.dossiers.rating_card import RATING_CARD  # noqa: F401  (re-export cho flow.py)

GREET = {
    "md": (
        "**Xin chào công dân!** Em là **Trợ lý nhân dân**, hỗ trợ làm thủ tục hành chính công ạ.\n\n"
        "Công dân kiểm tra **nơi làm thủ tục** bên dưới rồi **chọn thủ tục** cần làm — "
        "bấm vào thẻ hoặc gõ/nói tên thủ tục đều được ạ."
    ),
    "tts": (
        "Xin chào công dân em là Trợ lý nhân dân. "
        "Công dân chọn thủ tục cần làm, bấm vào thẻ hoặc nói tên thủ tục đều được ạ."
    ),
}

GREET_RETURNING = {
    "md": "Công dân đang làm dở thủ tục **{procedure}** (đến bước: {step_label}). Công dân muốn **tiếp tục** hay **làm thủ tục khác** ạ?",
    "tts": "Công dân đang làm dở thủ tục {procedure}. Công dân muốn tiếp tục hay làm thủ tục khác ạ?",
}

CONFIRM_PROCEDURE = {
    "md": "Dạ, công dân muốn làm **{procedure}** tại **{ward}, {province}** đúng không ạ?",
    "tts": "Dạ công dân muốn làm thủ tục {procedure} tại {ward} {province} đúng không ạ?",
}

PROCEDURE_NOT_RECOGNIZED = {
    "md": (
        "Dạ em chưa nhận ra thủ tục công dân cần ạ. Hiện em hỗ trợ **{count} thủ tục** trong danh sách bên dưới — "
        "công dân bấm chọn hoặc nói lại tên giúp em nhé."
    ),
    "tts": "Dạ em chưa nhận ra thủ tục công dân cần. Công dân chọn trong danh sách hoặc nói lại tên giúp em nhé.",
}

# Thủ tục đặc thù tỉnh (provinceOnly) mà tài khoản đang đăng nhập ở tỉnh khác → không mở được.
PROCEDURE_PROVINCE_LOCKED = {
    "md": (
        "Dạ **{procedure}** hiện chỉ áp dụng ở **{provinces}** ạ. Tài khoản mình đang ở tỉnh khác "
        "nên chưa làm được thủ tục này. Công dân chọn thủ tục khác trong danh sách bên dưới giúp em nhé."
    ),
    "tts": (
        "Dạ thủ tục {procedure} hiện chỉ áp dụng ở {provinces}, tài khoản mình ở tỉnh khác nên "
        "chưa làm được ạ. Công dân chọn thủ tục khác giúp em nhé."
    ),
}

GUIDE_LOGIN = {
    "md": (
        "Em đang đưa công dân sang trang thủ tục. Nếu trang yêu cầu đăng nhập, công dân mở app **VNeID** "
        "trên điện thoại → chọn **Quét QR** → quét mã trên màn hình để đăng nhập ạ.\n\n"
        "Đăng nhập xong em sẽ tự nhận ra và hướng dẫn tiếp 😊"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Công dân mở app VNeID trên điện thoại chọn Quét QR, rồi quét mã trên màn hình để đăng nhập. "
    # "Đăng nhập xong em sẽ hướng dẫn tiếp ạ."
    # ),
    "tts": "Công dân mở app vi en ai đi trên điện thoại chọn Quét quy rờ, rồi quét mã trên màn hình để đăng nhập. Đăng nhập xong em sẽ hướng dẫn tiếp ạ.",
}

# Máy quét trả tệp lẻ tẻ (scan-bridge) → công dân chủ động bấm "Đã đưa đủ" khi xong. Câu này NỐI
# vào SCAN_PICK. (Đường chọn tệp tay khi máy chưa cài agent vẫn tự chốt theo đợt như trước.)
SCAN_AUTO_RUN_NOTE = {
    "md": " Xong hết, công dân bấm **\"Đã đưa đủ giấy tờ\"** ở dưới để em bắt đầu xử lý ạ.",
    "tts": " Xong hết thì công dân bấm nút Đã đưa đủ giấy tờ để em bắt đầu xử lý ạ.",
}

GUIDE_AGENCY_SELECT = {
    "md": (
        "Em đang mở trang thủ tục **{procedure}**. Em sẽ **tự chọn cơ quan thực hiện** "
        "(**{ward}, {province}**) và bấm **Nộp trực tuyến** giúp công dân."
    ),
    "tts": "Em đang mở trang thủ tục và sẽ tự chọn cơ quan {ward}, {province} rồi bấm nộp trực tuyến giúp công dân.",
}

# Thủ tục cổng Bộ NN&MT (agencyProvinceOnly): trang DVCQG chỉ cần chọn TỈNH rồi Đồng ý;
# kết quả đầu tiên "Nộp trực tuyến" chính là Sở chuyên ngành.
GUIDE_AGENCY_SELECT_PROVINCE = {
    "md": (
        "Em đang mở trang thủ tục **{procedure}**. Em sẽ **tự chọn tỉnh {province}**, bấm "
        "**Đồng ý** và chọn **{agency}** để **Nộp trực tuyến** giúp công dân."
    ),
    "tts": (
        "Em đang mở trang thủ tục và sẽ tự chọn tỉnh {province}, bấm đồng ý rồi nộp trực tuyến "
        "ở {agency} giúp công dân."
    ),
}

# Hỏi "Trường hợp giải quyết" (cấp mới / cấp lại) NGAY sau khi xác nhận thủ tục — lựa chọn
# này quyết định option trên cổng MAE nên phải chốt trước khi mở trang.
# Danh sách trường hợp do REGISTRY của từng thủ tục quyết định (variants.options) — dựng sẵn
# thành {options_md}/{options_tts} rồi mới nhét vào đây, nên câu này dùng chung cho mọi thủ tục
# có bước "Chọn trường hợp giải quyết", không riêng cấp mới/cấp lại.
CHOOSE_VARIANT = {
    "md": (
        "Dạ, thủ tục **{procedure}** đang ở bước **Chọn trường hợp giải quyết** ạ. "
        "Có {count} trường hợp:\n\n{options_md}\n\nCông dân chọn trường hợp nào ạ?"
    ),
    "tts": (
        "Dạ, mình đang ở bước chọn trường hợp giải quyết. Có {count} trường hợp: {options_tts}. "
        "Công dân chọn trường hợp nào ạ?"
    ),
}

CHOOSE_VARIANT_REMIND = {
    "md": "Dạ, công dân chọn giúp em một trường hợp bên dưới để em làm tiếp ạ:\n\n{options_md}",
    "tts": "Dạ, công dân chọn giúp em một trường hợp để em làm tiếp ạ: {options_tts}.",
}

# Bước "Chọn trường hợp giải quyết" ở dạng HỘP THOẠI chỉ có Đơn vị thực hiện + Trường hợp giải
# quyết (cổng Bộ Xây dựng) — không có ô Tỉnh/radio Sở như trang MAE nên không nhắc tới chúng.
VARIANT_DIALOG_AUTOFILL_GUIDE = {
    "md": (
        "Dạ, em chọn trường hợp **{variant_label}** rồi ấn **Đồng ý** để sang trang kê khai nhé ạ."
    ),
    "tts": (
        "Dạ, em chọn trường hợp {variant_label} rồi ấn đồng ý để sang trang kê khai nhé ạ."
    ),
}

# Trang MAE "chọn nơi và loại": bot tự điền Tỉnh + Sở + Trường hợp giải quyết rồi bấm
# "Đồng ý và tiếp tục" — câu hướng dẫn theo yêu cầu nghiệp vụ.
MAE_AGENCY_AUTOFILL_GUIDE = {
    "md": (
        "Dạ, em chọn **tỉnh {province}** và **{agency}**, em tự chọn trường hợp "
        "**{variant_label}** rồi ấn **Đồng ý và tiếp tục** để vào trang kê khai nhé ạ."
    ),
    "tts": (
        "Em đã chọn tỉnh {province} và {agency}, mình tự chọn cho em trường hợp "
        "{variant_label} rồi ấn đồng ý và tiếp tục để vào trang kê khai nhé ạ."
    ),
}

MAE_AGENCY_FAILED = {
    "md": (
        "⚠️ Em chưa chọn tự động được trên trang: *{error}*\n\n"
        "Công dân chọn tay giúp em: **Tỉnh {province}** → **Sở/Ban ngành** → **{agency}** → "
        "**Trường hợp {variant_label}** rồi bấm **Đồng ý và tiếp tục** ạ."
    ),
    "tts": (
        "Em chưa chọn tự động được ạ. Công dân chọn tay giúp em tỉnh {province}, mục sở ban "
        "ngành chọn {agency}, trường hợp {variant_label}, rồi bấm đồng ý và tiếp tục ạ."
    ),
}

# Liên thông: trang "Chọn cơ quan thực hiện" (Angular, KHÔNG có needsAgencySelect nên bot không
# tự chọn) → dặn người dân chọn tỉnh/xã + bấm tiếp, nói 1 lần; sang trang kê khai thì thôi.
AGENCY_MANUAL_GUIDE = {
    "md": (
        "Dạ, công dân **chọn cơ quan thực hiện** (tỉnh/xã) trên trang rồi bấm **tiếp tục** giúp em ạ "
        "— sang bước **kê khai** em hướng dẫn tiếp ngay 😊"
    ),
    "tts": (
        "Dạ công dân chọn cơ quan thực hiện gồm tỉnh và xã trên trang rồi bấm tiếp tục ạ. "
        "Sang bước kê khai em hướng dẫn tiếp ngay."
    ),
}

# Trợ lý ĐIỀN HỘ bước chọn cơ quan (liên thông khai sinh): loại khai sinh, tỉnh/xã theo nơi ở,
# trường hợp khai sinh/ĐKTT, tick "Cùng địa bàn". Điền xong người dân tự bấm "Chuyển bước tiếp theo".
AGENCY_AUTOFILL_GUIDE = {
    "md": (
        "Dạ, em **chọn giúp** công dân **cơ quan thực hiện** (khai sinh, thường trú, BHYT) theo nơi ở "
        "**{ward}, {province}** ạ. Chọn xong công dân bấm **Chuyển bước tiếp theo** giúp em nhé 😊"
    ),
    "tts": (
        "Dạ, em chọn giúp công dân cơ quan thực hiện theo nơi ở của công dân. "
        "Xong công dân bấm Chuyển bước tiếp theo giúp em ạ."
    ),
}

# MỘT CÂU duy nhất đọc TRÊN chính trang login SSO (Hướng A): xác nhận cơ quan + dặn VNeID/Quét QR
# gộp lại (không tách 2 bong bóng). Panel còn hiện → đọc đủ → đọc xong FE thu gọn
# (action collapse_after_tts ở flow) để lộ mã QR cho công dân quét.
QR_LOGIN_GUIDE = {
    "md": (
        "✅ Em đã chọn cơ quan **{ward}, {province}** và mở bước **đăng nhập** ạ. "
        "Công dân mở app **VNeID** trên điện thoại → chọn **Quét QR** → quét mã trên màn hình "
        "để đăng nhập ạ. Xong em hướng dẫn tiếp ngay 😊"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã chọn cơ quan {ward}, {province} và mở bước đăng nhập ạ. "
    # "Công dân mở app VNeID chọn Quét QR rồi quét mã trên màn hình để đăng nhập. Xong em hướng dẫn tiếp ạ."
    # ),
    "tts": "Em đã chọn cơ quan {ward}, {province} và mở bước đăng nhập ạ. Công dân mở app vi en ai đi chọn Quét quy rờ rồi quét mã trên màn hình để đăng nhập. Xong em hướng dẫn tiếp ạ.",
}

# Các modal xác thực nối tiếp dùng chung URL SSO. Extension chỉ nhận diện trạng thái trang;
# toàn bộ lời hướng dẫn vẫn do backend quản lý.
VNEID_LOGIN_CODE_GUIDE = {
    "md": (
        "Công dân vui lòng nhập **mã xác nhận đăng nhập** theo yêu cầu trên màn hình, "
        "sau đó bấm **Xác nhận** để tiếp tục ạ."
    ),
    "tts": (
        "Công dân vui lòng nhập mã xác nhận đăng nhập theo yêu cầu trên màn hình, "
        "sau đó bấm Xác nhận để tiếp tục ạ."
    ),
}

VNEID_DATA_SHARING_GUIDE = {
    "md": (
        "Công dân tích vào ô **“Tôi đã đọc và hiểu rõ nội dung mục đích; Quyền, nghĩa vụ "
        "của chủ thể dữ liệu và đồng ý với các nội dung này”**, sau đó bấm "
        "**Xác nhận chia sẻ**, rồi nhập **passcode 6 số của ứng dụng VNeID** để tiếp tục ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Công dân tích vào ô Tôi đã đọc và hiểu rõ nội dung mục đích, quyền và nghĩa vụ "
    # "của chủ thể dữ liệu, và đồng ý với các nội dung này. Sau đó bấm Xác nhận chia sẻ "
    # "rồi nhập passcode 6 số của ứng dụng VNeID để tiếp tục ạ."
    # ),
    "tts": "Công dân tích vào ô Tôi đã đọc và hiểu rõ nội dung mục đích, quyền và nghĩa vụ của chủ thể dữ liệu, và đồng ý với các nội dung này. Sau đó bấm Xác nhận chia sẻ rồi nhập passcode 6 số của ứng dụng vi en ai đi để tiếp tục ạ.",
}

VNEID_PASSCODE_GUIDE = {
    "md": (
        "Công dân vui lòng nhập **passcode VNeID gồm 6 chữ số** vào màn hình, "
        "sau đó bấm **Xác nhận** để tiếp tục ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Công dân vui lòng nhập passcode VNeID gồm 6 chữ số vào màn hình, "
    # "sau đó bấm Xác nhận để tiếp tục ạ."
    # ),
    "tts": "Công dân vui lòng nhập passcode vi en ai đi gồm 6 chữ số vào màn hình, sau đó bấm Xác nhận để tiếp tục ạ.",
}

# Người dân gõ/nói giữa lúc chờ — nhắc NGẮN theo đúng việc đang chờ, kèm nút phao.
WAIT_LOGIN_REMIND = {
    "md": (
        "Dạ, em đang chờ công dân **đăng nhập VNeID** ạ — mở app → **Quét QR** giúp em nhé. "
        "Nếu đã vào được trang kê khai mà em chưa nhận ra, công dân bấm nút dưới ạ."
    ),
    "tts": "Dạ em đang chờ công dân đăng nhập ạ. Nếu đã vào được trang kê khai, công dân bấm nút trên màn hình giúp em nhé.",
}

# Nút phao chỉ yêu cầu extension kiểm tra lại DOM, không phải lời xác nhận đã đăng nhập.
# Hai câu này được dùng khi chính lần kiểm tra tay cho thấy trang vẫn chưa sẵn sàng.
LOGIN_STILL_REQUIRED = {
    "md": (
        "Trang hiện tại vẫn đang ở bước **đăng nhập VNeID**. Công dân hoàn tất đăng nhập "
        "giúp em; khi vào trang làm hồ sơ em sẽ tự nhận ra ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Trang hiện tại vẫn đang ở bước đăng nhập VNeID. Công dân hoàn tất đăng nhập "
    # "giúp em. Khi vào trang làm hồ sơ em sẽ tự nhận ra ạ."
    # ),
    "tts": "Trang hiện tại vẫn đang ở bước đăng nhập vi en ai đi. Công dân hoàn tất đăng nhập giúp em. Khi vào trang làm hồ sơ em sẽ tự nhận ra ạ.",
}

PORTAL_NOT_READY = {
    "md": (
        "Em kiểm tra thấy trang hiện tại **chưa vào phần làm hồ sơ**. Công dân tiếp tục "
        "các bước trên cổng; khi trang hồ sơ mở em sẽ tự nhận ra ạ."
    ),
    "tts": (
        "Em kiểm tra thấy trang hiện tại chưa vào phần làm hồ sơ. Công dân tiếp tục "
        "các bước trên cổng. Khi trang hồ sơ mở em sẽ tự nhận ra ạ."
    ),
}

WAIT_PORTAL_REMIND = {
    "md": (
        "Dạ, em đang chờ trang chuyển sang **bước kê khai** ạ. "
        "Nếu công dân đã thấy form kê khai mà em chưa nhận ra, bấm nút dưới giúp em nhé."
    ),
    "tts": (
        "Dạ em đang chờ trang chuyển sang bước kê khai ạ. "
        "Nếu công dân đã thấy form kê khai mà em chưa nhận ra, bấm nút trên màn hình giúp em nhé."
    ),
}

WAIT_ATTACH_PORTAL_REMIND = {
    "md": (
        "Dạ, em đang chờ trang chuyển sang **Thành phần hồ sơ** ạ. Nếu công dân đã thấy bảng "
        "đính kèm mà em chưa nhận ra, bấm nút dưới giúp em nhé."
    ),
    "tts": (
        "Dạ em đang chờ trang chuyển sang thành phần hồ sơ ạ. Nếu công dân đã thấy bảng đính kèm, "
        "bấm nút trên màn hình giúp em nhé."
    ),
}

AGENCY_SELECT_FAILED = {
    "md": (
        "⚠️ Em chưa chọn được cơ quan tự động: *{error}*\n\n"
        "Công dân chọn tay giúp em: **{ward}, {province}** rồi bấm **Đồng ý** ạ."
    ),
    "tts": "Em chưa chọn tự động được công dân chọn tay giúp em rồi bấm đồng ý ạ.",
}

GUIDE_LOGIN_NO_URL = {
    "md": (
        "Dạ thủ tục **{procedure}** em chưa có sẵn đường dẫn trang kê khai. "
        "Công dân mở trang thủ tục trên cổng dịch vụ công giúp em, em sẽ tự nhận ra và hỗ trợ tiếp ạ."
    ),
    "tts": "Công dân mở trang thủ tục trên cổng dịch vụ công giúp em, em sẽ tự nhận ra và hỗ trợ tiếp ạ.",
}

# Intro chỉ nêu bước trên cổng đã tới; không lặp lại trạng thái đăng nhập.
ASK_DOC_METHOD = {
    "md": (
        "{intro_md} Để làm **{procedure}**, công dân cần chuẩn bị giấy tờ sau:\n\n{doc_list}\n\n"
        "**Công dân sẽ cung cấp giấy tờ bằng cách nào ạ?** Chọn 1 cách bên dưới:"
    ),
    "tts": (
        "{intro_tts} Công dân cần chuẩn bị: {doc_list_tts}. "
        "Công dân muốn cung cấp giấy tờ bằng cách nào ạ? Chụp bằng điện thoại hay scan tại quầy ạ?"
    ),
}

INTRO_LOGIN_OK = {"md": "", "tts": ""}
INTRO_FORM_REACHED = {"md": "Đã vào trang kê khai ✓", "tts": "Mình đã vào trang kê khai rồi ạ."}
INTRO_OWNER_REACHED = {
    "md": "Đã vào bước Thông tin chủ hồ sơ ✓",
    "tts": "Mình đã vào bước thông tin chủ hồ sơ rồi ạ.",
}
INTRO_ATTACH_REACHED = {
    "md": "Đã vào bước Thành phần hồ sơ ✓",
    "tts": "Mình đã vào bước thành phần hồ sơ rồi ạ.",
}

# Wizard hồ sơ cổng React (kết hôn): modal "Thông tin chung" → bước Thông tin chủ hồ sơ
# → bước Kê khai. Modal đã điền sẵn đúng cơ quan → bot bấm Xác nhận hộ LẶNG LẼ (không báo câu —
# đã bỏ CONFIRM_INFO_MODAL khỏi luồng theo yêu cầu; hành động confirm_info_modal vẫn chạy ở flow).

OWNER_INFO_GUIDE = {
    "md": (
        "Công dân điền **Thông tin chủ hồ sơ** (số điện thoại, thư điện tử, địa chỉ) rồi bấm "
        "nút tiếp tục của trang để sang **bước kê khai** giúp em ạ — vào đến nơi em hướng dẫn tiếp ngay 😊"
    ),
    "tts": (
        "Công dân điền thông tin chủ hồ sơ gồm số điện thoại, thư điện tử, địa chỉ, "
        "rồi bấm tiếp tục để sang bước kê khai ạ. Vào đến nơi em hướng dẫn tiếp ngay."
    ),
}

OWNER_INFO_ATTACH_GUIDE = {
    "md": (
        "Công dân điền **Thông tin chủ hồ sơ** (số điện thoại, thư điện tử, địa chỉ) rồi bấm "
        "nút tiếp tục của trang giúp em ạ, trang sẽ "
        "chuyển tới **Thành phần hồ sơ** và em hướng dẫn đính kèm ngay 😊"
    ),
    "tts": (
        "Công dân điền thông tin chủ hồ sơ gồm số điện thoại, thư điện tử, địa chỉ rồi bấm tiếp tục ạ. "
        "Trang sẽ chuyển tới thành phần hồ sơ."
    ),
}

DOCS_COMPLETE_OWNER = {
    "md": "Dạ, em đã nhận **{files_count} tệp** và đang xác định thông tin của đúng chủ hồ sơ…",
    "tts": "Dạ, em đã nhận giấy tờ và đang xác định thông tin của đúng chủ hồ sơ ạ.",
}
OWNER_PROCESSING = {
    "md": "Dạ em đang đối chiếu họ tên hoặc số định danh của chủ hồ sơ, sắp xong rồi ạ…",
    "tts": "Dạ em đang đối chiếu thông tin chủ hồ sơ, sắp xong rồi ạ.",
}
OWNER_FIELDS_READY = {
    "md": "Em đã xác định đúng chủ hồ sơ và tìm thấy **{count} thông tin**. Em điền vào trang ngay ạ.",
    "tts": "Em đã xác định đúng chủ hồ sơ và sẽ điền các thông tin tìm thấy ngay ạ.",
}
OWNER_FIELDS_UNMATCHED = {
    "md": (
        "Em thấy trong tài liệu công dân cung cấp **không có thông tin phù hợp** để điền vào phần "
        "**Thông tin chủ hồ sơ**. Công dân bổ sung các ô còn thiếu giúp em ạ."
    ),
    "tts": (
        "Em thấy trong tài liệu công dân cung cấp không có thông tin phù hợp để điền vào phần "
        "Thông tin chủ hồ sơ. Công dân bổ sung các ô còn thiếu giúp em ạ."
    ),
}
OWNER_FIELDS_EMPTY = {
    "md": (
        "Em chưa xác định chắc chắn được thông tin của chủ hồ sơ nên **không tự điền**. "
        "Công dân bổ sung các ô còn thiếu rồi bấm **Bước tiếp theo** giúp em ạ."
    ),
    "tts": "Em chưa xác định chắc chắn được chủ hồ sơ nên không tự điền. Công dân bổ sung rồi bấm bước tiếp theo giúp em ạ.",
}
OWNER_PIPELINE_ERROR = {
    "md": (
        "Em chưa đọc được thông tin chủ hồ sơ ({error}). Em sẽ không đoán dữ liệu; "
        "công dân điền phần còn thiếu rồi bấm **Bước tiếp theo** giúp em ạ."
    ),
    "tts": "Em chưa đọc được thông tin chủ hồ sơ nên không tự điền. Công dân điền phần còn thiếu rồi bấm bước tiếp theo giúp em ạ.",
}
OWNER_FILL_DONE = {
    "md": (
        "✅ Em đã điền xong **{completed}**.{missing_note}\n\n"
        "Công dân kiểm tra rồi bấm **Bước tiếp theo**."
    ),
    "tts": (
        "Em đã điền xong {completed}.{missing_tts} "
        "Công dân kiểm tra rồi bấm bước tiếp theo."
    ),
}
OWNER_FILL_NOT_APPLIED = {
    "md": (
        "Em đã đọc được dữ liệu nhưng trang **chưa nhận lệnh điền**: {error}. "
        "Công dân giữ nguyên trang này và chọn **Điền lại thông tin chủ hồ sơ** giúp em ạ."
    ),
    "tts": (
        "Em đã đọc được dữ liệu nhưng trang chưa nhận lệnh điền. "
        "Công dân giữ nguyên trang và chọn điền lại thông tin chủ hồ sơ giúp em ạ."
    ),
}
MAIN_FORM_PROCESSING = {
    "md": "Bây giờ em sẽ **điền thông tin kê khai** giúp công dân nhé.",
    "tts": "Bây giờ em sẽ điền thông tin kê khai giúp công dân nhé.",
}
WAIT_ATTACHMENT_PAGE = {
    "md": (
        "\n\nSau khi kiểm tra xong, công dân chuyển sang **Thành phần hồ sơ**; "
        "khi trang mở, em sẽ tự đính kèm giấy tờ vào hồ sơ ạ."
    ),
    "tts": (
        " Sau khi kiểm tra xong, công dân chuyển sang thành phần hồ sơ. "
        "Khi trang mở, em sẽ tự đính kèm giấy tờ vào hồ sơ ạ."
    ),
}
# Cổng 2 tab cùng trang (Bắc Ninh): công dân KHÔNG phải chuyển bước — bot tự mở tab
# "Tải thành phần hồ sơ" và đính kèm ngay sau khi điền xong đơn.
WAIT_ATTACHMENT_SAME_PAGE = {
    "md": (
        "\n\nGiờ em **chuyển sang phần Tải thành phần hồ sơ** và tự đính kèm giấy tờ vào "
        "hồ sơ — công dân chờ em thêm chút nhé ạ…"
    ),
    "tts": (
        " Giờ em chuyển sang phần tải thành phần hồ sơ và tự đính kèm giấy tờ vào hồ sơ. "
        "Công dân chờ em thêm chút nhé ạ."
    ),
}
# Chốt kết quả CẢ HAI bước (điền đơn + đính kèm) sau khi luồng cùng-trang chạy liền mạch.
SAME_PAGE_TWO_STEP_SUMMARY = {
    "md": (
        "\n\n📋 Tóm tắt: **Nhập đơn đăng ký** — điền {filled} ô ✓ · "
        "**Tải thành phần hồ sơ** — đính kèm {attached} tệp ✓"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # " Tóm tắt lại: phần nhập đơn đăng ký em đã điền {filled} ô, phần thành phần hồ sơ "
    # "em đã đính kèm {attached} tệp ạ."
    # ),
    "tts": " Tóm tắt lại: phần nhập đơn đăng ký em đã điền các ô, phần thành phần hồ sơ em đã đính kèm các tệp ạ.",
}
REFILL_PROCESSING = {
    "md": (
        "🔁 Em đang **đọc lại giấy tờ và điền lại thông tin kê khai**. "
        "Công dân giữ nguyên trang này và chờ em một chút ạ…"
    ),
    "tts": (
        "Em đang đọc lại giấy tờ và điền lại thông tin kê khai. "
        "Công dân giữ nguyên trang này và chờ em một chút ạ."
    ),
}
REFILL_ALREADY_RUNNING = {
    "md": "Dạ, em đang điền lại thông tin rồi ạ. Công dân chờ em một chút nhé.",
    "tts": "Dạ, em đang điền lại thông tin rồi ạ. Công dân chờ em một chút nhé.",
}
REFILL_WRONG_PAGE = {
    "md": (
        "Hiện mình không ở trang **Kê khai thông tin**. Công dân quay lại trang Kê khai, "
        "rồi bấm **Điền lại thông tin** giúp em nhé ạ."
    ),
    "tts": (
        "Hiện mình không ở trang kê khai thông tin. Công dân quay lại trang kê khai, "
        "rồi bấm điền lại thông tin giúp em nhé ạ."
    ),
}
REVIEW_ATTACHMENT_ACTION = {
    "md": (
        "\n\nSau khi kiểm tra xong, công dân chuyển sang **Thành phần hồ sơ**, rồi bấm "
        "**Đính kèm giấy tờ** trong Trợ lý để em thực hiện ạ."
    ),
    "tts": (
        " Sau khi kiểm tra xong, công dân chuyển sang thành phần hồ sơ, rồi bấm "
        "đính kèm giấy tờ trong Trợ lý để em thực hiện ạ."
    ),
}

# ── Xin phép xử lý dữ liệu cá nhân (Luật 91/2025/QH15) — TRƯỚC khi nhận/đọc giấy tờ ──
# Intro nối mốc trang hiện tại như ASK_DOC_METHOD; không đọc lại trạng thái đăng nhập.
CONSENT_INTRO = {
    "md": (
        "{intro_md} Trước khi nhận và đọc giấy tờ, em cần **công dân cho phép xử lý dữ liệu "
        "cá nhân** ạ. Công dân đọc nội dung trong thẻ dưới đây, tích **2 ô xác nhận** rồi bấm "
        "**Đồng ý và tự động điền** nhé. Nếu không đồng ý, công dân chọn **Tự nhập** — "
        "em sẽ không đọc giấy tờ ạ."
    ),
    "tts": (
        "{intro_tts} Trước khi nhận và đọc giấy tờ, em cần công dân cho phép xử lý dữ liệu cá nhân ạ. "
        "Trong thủ tục này em sẽ chỉ đọc: {doc_list_tts}, để tự động điền biểu mẫu và chuẩn bị "
        "tệp đính kèm. Công dân đọc nội dung trong thẻ, tích hai ô xác nhận, rồi bấm Đồng ý và tự động điền. "
        "Nếu không đồng ý, công dân chọn tự nhập, em sẽ không đọc giấy tờ ạ."
    ),
}

CONSENT_ATTACH_INTRO = {
    "md": (
        "{intro_md} Trước khi nhận và tự động đính kèm giấy tờ, em cần **công dân cho phép xử lý "
        "dữ liệu cá nhân** ạ. Công dân đọc nội dung trong thẻ dưới đây, tích **2 ô xác nhận** rồi "
        "bấm **Đồng ý và tự động đính kèm** nhé."
    ),
    "tts": (
        "{intro_tts} Trước khi nhận và tự động đính kèm {doc_list_tts}, em cần công dân cho phép "
        "xử lý dữ liệu cá nhân ạ. Công dân đọc nội dung trong thẻ, tích hai ô xác nhận rồi bấm đồng ý."
    ),
}

# Nội dung hiển thị TRONG card consent_form — server-driven, FE chỉ render.
CONSENT_CARD_TEXT = {
    "intro_md": (
        "Chỉ khi công dân bấm **Đồng ý và tự động điền**, em mới đọc, trích xuất và xử lý "
        "thông tin cần thiết từ các giấy tờ dưới đây, rồi tự động điền vào biểu mẫu trên trang."
    ),
    "scope_md": (
        "Em chỉ đọc thông tin cần thiết từ giấy tờ **công dân chủ động cung cấp** cho thủ tục này. "
        "Công dân kiểm tra và sửa được toàn bộ dữ liệu trước khi nộp hồ sơ."
    ),
    "purpose_md": (
        "**Mục đích chia sẻ, xử lý dữ liệu:** đọc chữ trên ảnh (OCR), chuẩn hoá thông tin, "
        "đối chiếu đúng chủ hồ sơ, tự động điền thông tin chủ hồ sơ, biểu mẫu kê khai và "
        "chuẩn bị tệp đính kèm; dữ liệu chỉ được **chia sẻ lên "
        "Cổng Dịch vụ công** để nộp hồ sơ theo yêu cầu của công dân. Hồ sơ đã xử lý "
        "(ảnh giấy tờ, kết quả đọc) được **lưu trên hệ thống** phục vụ đối soát và "
        "hỗ trợ giải quyết thủ tục."
    ),
    "checks": [
        "Tôi đã đọc, hiểu phạm vi giấy tờ, thông tin được xử lý và mục đích nêu trên; "
        "đồng ý cho Trợ lý nhân dân đọc, xử lý và tự động điền dữ liệu vào biểu mẫu.",
        "Tôi xác nhận tự chịu trách nhiệm về tính chính xác, hợp pháp của các thông tin "
        "nêu trên và về việc thực hiện thủ tục hành chính của mình.",
    ],
    "accept_label": "Đồng ý và tự động điền",
    "decline_label": "Không đồng ý · Tự nhập",
}

CONSENT_ATTACH_CARD_TEXT = {
    "intro_md": (
        "Chỉ khi công dân bấm **Đồng ý và tự động đính kèm**, em mới nhận các tệp công dân chủ động "
        "cung cấp và gắn chúng vào hồ sơ trên Cổng Dịch vụ công."
    ),
    "scope_md": (
        "Thủ tục này chỉ dùng **một loại giấy tờ** và không phân loại nội dung. Công dân có thể gửi "
        "nhiều tệp; tất cả được xử lý trong cùng một hồ sơ."
    ),
    "purpose_md": (
        "**Mục đích xử lý dữ liệu:** lưu tạm các tệp trong phiên làm thủ tục và tự động đính kèm "
        "chúng lên Cổng Dịch vụ công theo yêu cầu của công dân; không trích xuất dữ liệu để điền biểu mẫu."
    ),
    "checks": [
        "Tôi đã đọc, hiểu phạm vi giấy tờ và mục đích xử lý nêu trên; đồng ý cho Trợ lý nhân dân "
        "nhận, lưu tạm và tự động đính kèm các tệp tôi cung cấp vào hồ sơ.",
        "Tôi xác nhận tự chịu trách nhiệm về tính chính xác, hợp pháp của các giấy tờ đã cung cấp "
        "và về việc thực hiện thủ tục hành chính của mình.",
    ],
    "accept_label": "Đồng ý và tự động đính kèm",
    "decline_label": "Không đồng ý · Tự đính kèm",
}

# Toàn văn Điều 4 Luật 91/2025/QH15 — FE để trong khối mở rộng (details).
CONSENT_LEGAL_MD = """*Theo Luật số 91/2025/QH15 ngày 26/6/2025 — Luật Bảo vệ dữ liệu cá nhân*

**Điều 4. Quyền và nghĩa vụ của chủ thể dữ liệu cá nhân**

**1. Quyền của chủ thể dữ liệu cá nhân bao gồm:**

- a) Được biết về hoạt động xử lý dữ liệu cá nhân;
- b) Đồng ý hoặc không đồng ý, yêu cầu rút lại sự đồng ý cho phép xử lý dữ liệu cá nhân;
- c) Xem, chỉnh sửa hoặc yêu cầu chỉnh sửa dữ liệu cá nhân;
- d) Yêu cầu cung cấp, xóa, hạn chế xử lý dữ liệu cá nhân; gửi yêu cầu phản đối xử lý dữ liệu cá nhân;
- đ) Khiếu nại, tố cáo, khởi kiện, yêu cầu bồi thường thiệt hại theo quy định của pháp luật;
- e) Yêu cầu cơ quan có thẩm quyền hoặc cơ quan, tổ chức, cá nhân liên quan đến xử lý dữ liệu cá nhân thực hiện các biện pháp, giải pháp bảo vệ dữ liệu cá nhân của mình theo quy định của pháp luật.

**2. Nghĩa vụ của chủ thể dữ liệu cá nhân bao gồm:**

- a) Tự bảo vệ dữ liệu cá nhân của mình;
- b) Tôn trọng, bảo vệ dữ liệu cá nhân của người khác;
- c) Cung cấp đầy đủ, chính xác dữ liệu cá nhân của mình theo quy định của pháp luật, theo hợp đồng hoặc khi đồng ý cho phép xử lý dữ liệu cá nhân của mình;
- d) Chấp hành pháp luật về bảo vệ dữ liệu cá nhân và tham gia phòng, chống hoạt động xâm phạm dữ liệu cá nhân.

**3. Chủ thể dữ liệu cá nhân khi thực hiện quyền và nghĩa vụ của mình phải tuân thủ đầy đủ các nguyên tắc sau đây:**

- a) Thực hiện theo quy định của pháp luật; tuân thủ nghĩa vụ của chủ thể dữ liệu cá nhân theo hợp đồng. Việc thực hiện quyền và nghĩa vụ của chủ thể dữ liệu cá nhân phải nhằm mục đích bảo vệ quyền, lợi ích hợp pháp của chính chủ thể dữ liệu cá nhân đó;
- b) Không được gây khó khăn, cản trở việc thực hiện quyền, nghĩa vụ pháp lý của bên kiểm soát dữ liệu cá nhân, bên kiểm soát và xử lý dữ liệu cá nhân, bên xử lý dữ liệu cá nhân;
- c) Không được xâm phạm đến quyền, lợi ích hợp pháp của Nhà nước, cơ quan, tổ chức và cá nhân khác.

**4.** Cơ quan, tổ chức, cá nhân có trách nhiệm tạo điều kiện thuận lợi, không được gây khó khăn, cản trở việc thực hiện quyền và nghĩa vụ của chủ thể dữ liệu cá nhân theo quy định của pháp luật.

**5.** Khi nhận được yêu cầu của chủ thể dữ liệu cá nhân để thực hiện quyền của chủ thể dữ liệu cá nhân quy định tại khoản 1 Điều này, bên kiểm soát dữ liệu cá nhân, bên kiểm soát và xử lý dữ liệu cá nhân phải kịp thời thực hiện trong thời hạn theo quy định của pháp luật."""

CONSENT_ACCEPTED = {
    "md": (
        "✅ Đã ghi nhận sự đồng ý của công dân — mã nhật ký **{log_id}**, lúc {time}, "
        "bản nội dung v{version}."
    ),
    "tts": "Em đã ghi nhận sự đồng ý của công dân rồi ạ.",
}

CONSENT_DECLINED = {
    "md": (
        "Dạ em tôn trọng quyết định của công dân ✓ Em sẽ **không đọc và không xử lý** giấy tờ nào. "
        "Công dân tự điền biểu mẫu trên trang giúp em nhé — lúc nào muốn em hỗ trợ đọc–điền, "
        "công dân bấm **Xem lại và đồng ý** ạ."
    ),
    "tts": (
        "Dạ em tôn trọng quyết định của công dân. Em sẽ không đọc và không xử lý giấy tờ nào, "
        "công dân tự điền biểu mẫu trên trang nhé. Lúc nào muốn em hỗ trợ, công dân bấm xem lại và đồng ý ạ."
    ),
}

CONSENT_RESHOW = {
    "md": "Dạ, công dân đọc lại nội dung xin phép dưới đây rồi xác nhận giúp em ạ:",
    "tts": "Dạ, công dân đọc lại nội dung xin phép rồi xác nhận giúp em ạ.",
}

CONSENT_REMIND = {
    "md": (
        "Dạ công dân xác nhận **thẻ xin phép xử lý dữ liệu** bên trên giúp em ạ — "
        "đồng ý thì tích 2 ô rồi bấm **Đồng ý và tự động điền**, "
        "không thì chọn **Không đồng ý · Tự nhập** nhé."
    ),
    "tts": (
        "Dạ công dân xác nhận thẻ xin phép bên trên giúp em ạ. Đồng ý thì tích hai ô rồi bấm "
        "đồng ý và tự động điền, không thì chọn tự nhập nhé."
    ),
}

QR_WAITING = {
    "md": (
        "Dạ công dân chọn **📱 Gửi giấy tờ qua điện thoại** ✓\n\n"
        "Mời công dân mở **camera điện thoại**, quét **mã QR** dưới đây — "
        "điện thoại sẽ hiện trang chụp ảnh giấy tờ ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": "Mời công dân mở camera điện thoại rồi quét mã QR trên màn hình để tải ảnh giấy tờ lên ạ.",
    "tts": "Mời công dân mở camera điện thoại rồi quét mã quy rờ trên màn hình để tải ảnh giấy tờ lên ạ.",
}

MOBILE_CONNECTED = {
    "md": (
        "📱 Điện thoại đã kết nối ✓ Công dân **chụp lần lượt** theo danh sách trên điện thoại "
        "(CCCD chụp cả 2 mặt), hoặc **chọn nhiều ảnh có sẵn** — em tự nhận dạng và cập nhật "
        "tiến trình ngay tại đây ạ."
    ),
    "tts": (
        "Điện thoại đã kết nối rồi ạ. Công dân chụp lần lượt từng giấy tờ theo danh sách, "
        "căn cước chụp cả hai mặt. Em sẽ báo ngay khi nhận được từng ảnh ạ."
    ),
}

MOBILE_CONNECTED_ATTACH = {
    "md": (
        "📱 Điện thoại đã kết nối ✓ Công dân chụp hoặc chọn tất cả **giấy tờ cần chứng thực bản sao**. "
        "xong công dân bấm **Gửi tất cả** trên điện thoại ạ."
    ),
    "tts": (
        "Điện thoại đã kết nối rồi ạ. Công dân chụp hoặc chọn tất cả giấy tờ cần chứng thực bản sao, "
        "Xong công dân bấm gửi tất cả nhé."
    ),
}

# Chỉ nói SỐ ĐÃ NHẬN, không "x/y" — tổng gồm slot tuỳ chọn dễ làm công dân tưởng còn thiếu.
DOCS_COMPLETE_NEXT_STEP = {
    "md": (
        "✅ Em đã nhận **{files_count} tệp giấy tờ** theo phiên **{sid}**.\n\n"
        "Em đang **tự đọc (OCR)** và chuẩn bị điền vào form bên trái — "
        "khoảng nửa phút, công dân chờ em chút nhé…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã nhận {files_count} tệp giấy tờ. "
    # "Em đang tự đọc và chuẩn bị điền vào form bên trái, khoảng nửa phút, công dân chờ em chút nhé."
    # ),
    "tts": "Em đã nhận các tệp giấy tờ. Em đang tự đọc và chuẩn bị điền vào form bên trái, khoảng nửa phút, công dân chờ em chút nhé.",
}

DOCS_COMPLETE_ATTACH = {
    "md": (
        "✅ Em đã nhận **{files_count} tệp giấy tờ** theo phiên **{sid}**.\n\n"
        "Em đang chuẩn bị đính tất cả tệp vào **cùng một hồ sơ**, công dân chờ em chút ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã nhận {files_count} tệp giấy tờ. Em đang chuẩn bị đính tất cả tệp vào cùng một hồ sơ, "
    # "công dân chờ em chút ạ."
    # ),
    "tts": "Em đã nhận các tệp giấy tờ. Em đang chuẩn bị đính tất cả tệp vào cùng một hồ sơ, công dân chờ em chút ạ.",
}

DOCS_TARGET_UNKNOWN = {
    "md": (
        "Em chưa xác định được công dân đang đứng ở bước **Thông tin chủ hồ sơ**, "
        "**Kê khai thông tin** hay **Thành phần hồ sơ**. Em vẫn giữ nguyên các tệp đã nhận; "
        "công dân giữ đúng trang cần làm rồi bấm lại nút bên dưới giúp em ạ."
    ),
    "tts": (
        "Em chưa xác định được công dân đang đứng ở bước nào. Em vẫn giữ nguyên các tệp đã nhận. "
        "Công dân giữ đúng trang cần làm rồi bấm lại giúp em ạ."
    ),
}

BUSINESS_PREPARING = {
    "md": (
        "Em đã vào trang chủ của **Hệ thống thông tin đăng ký hộ kinh doanh**. Giờ em sẽ "
        "vào thẳng trang kê khai **Thành lập mới hộ kinh doanh** giúp công dân ạ. "
        "Công dân chờ em một chút, chưa cần thao tác trên trang."
    ),
    "tts": (
        "Em đã vào trang chủ của Hệ thống thông tin đăng ký hộ kinh doanh. Giờ em sẽ vào thẳng "
        "trang kê khai Thành lập mới hộ kinh doanh giúp công dân ạ. "
        "Công dân chờ em một chút, chưa cần thao tác trên trang."
    ),
}

# Luồng THAY ĐỔI nội dung ĐK hộ kinh doanh — bootstrap pha 1 chỉ tới màn tra cứu hộ KD.
BUSINESS_PREPARING_CHANGE = {
    "md": (
        "Em đã vào **Hệ thống thông tin đăng ký hộ kinh doanh**. Em sẽ chọn "
        "**Đăng ký thay đổi nội dung đăng ký hộ kinh doanh** và mở bước **tìm kiếm hộ kinh "
        "doanh** giúp công dân ạ. Công dân chờ em một chút, chưa cần thao tác trên trang."
    ),
    "tts": (
        "Em đã vào Hệ thống thông tin đăng ký hộ kinh doanh. Em sẽ chọn đăng ký thay đổi nội "
        "dung và mở bước tìm kiếm hộ kinh doanh giúp công dân ạ. "
        "Công dân chờ em một chút, chưa cần thao tác trên trang."
    ),
}

BUSINESS_DOCS_COMPLETE_CHANGE = {
    "md": (
        "✅ Em đã nhận **{files_count} tệp giấy tờ** theo phiên **{sid}**.\n\n"
        "Em đang đọc hồ sơ để lấy **mã số hộ kinh doanh**, so sánh nội dung hiện tại với đề "
        "nghị thay đổi và phân loại giấy tờ đính kèm. Xong em sẽ tự tra cứu và điền, công dân "
        "chờ em chút ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã nhận {files_count} tệp giấy tờ. Em đang đọc hồ sơ để lấy mã số hộ kinh doanh "
    # "và so sánh nội dung thay đổi. Công dân chờ em chút ạ."
    # ),
    "tts": "Em đã nhận các tệp giấy tờ. Em đang đọc hồ sơ để lấy mã số hộ kinh doanh và so sánh nội dung thay đổi. Công dân chờ em chút ạ.",
}

BUSINESS_READY_CHANGE = {
    "md": (
        "Em đã đọc xong giấy tờ ✓ Bây giờ em sẽ **tra cứu hộ kinh doanh theo mã số**, chọn "
        "loại đăng ký thay đổi, rồi tự điền các khối thông tin **cần sửa** và đính kèm hồ sơ. "
        "Trong lúc xử lý, công dân **chưa thao tác trên trang** giúp em ạ."
    ),
    "tts": (
        "Em đã đọc xong giấy tờ. Em sẽ tra cứu hộ kinh doanh theo mã số, chọn loại đăng ký "
        "thay đổi, rồi tự điền các khối cần sửa và đính kèm hồ sơ. "
        "Trong lúc xử lý công dân chưa thao tác trên trang giúp em ạ."
    ),
}

BUSINESS_DOCS_COMPLETE = {
    "md": (
        "✅ Em đã nhận **{files_count} tệp giấy tờ** theo phiên **{sid}**.\n\n"
        "Em đang đọc hồ sơ, chuẩn bị dữ liệu cho **8 khối thông tin** và phân loại giấy tờ "
        "đính kèm. Xong em sẽ tự điền lần lượt, công dân chờ em chút ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã nhận {files_count} tệp giấy tờ. Em đang chuẩn bị dữ liệu cho tám khối thông tin "
    # "và phân loại giấy tờ đính kèm. Công dân chờ em chút ạ."
    # ),
    "tts": "Em đã nhận các tệp giấy tờ. Em đang chuẩn bị dữ liệu cho tám khối thông tin và phân loại giấy tờ đính kèm. Công dân chờ em chút ạ.",
}

BUSINESS_READY = {
    "md": (
        "Em đã đọc xong giấy tờ ✓ Bây giờ em sẽ tự điền và lưu lần lượt **8 khối dữ liệu**, "
        "sau đó tự đính kèm hồ sơ. Trong lúc xử lý, công dân **chưa thao tác trên trang** giúp em ạ."
    ),
    "tts": (
        "Em đã đọc xong giấy tờ. Em sẽ tự điền và lưu lần lượt tám khối dữ liệu, rồi tự đính kèm hồ sơ. "
        "Trong lúc xử lý công dân chưa thao tác trên trang giúp em ạ."
    ),
}

BUSINESS_DONE = {
    "md": (
        "✅ Em đã điền đủ **{filled_pages}/{total_pages} khối dữ liệu** và đính kèm **{attached} tệp**.\n\n"
        "Công dân rà soát các thông tin đã điền ở từng khối và các tệp đã đính kèm giúp em nhé ạ. "
        "Sau khi kiểm tra xong, công dân tự bấm **Nộp hồ sơ** trên trang giúp em."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã điền đủ {filled_pages} trên {total_pages} khối dữ liệu và đính kèm {attached} tệp. "
    # "Công dân rà soát các thông tin đã điền ở từng khối và các tệp đã đính kèm giúp em nhé ạ. "
    # "Sau khi kiểm tra xong, công dân tự bấm nộp hồ sơ trên trang giúp em."
    # ),
    "tts": "Em đã điền đủ các khối dữ liệu và đính kèm các tệp. Công dân rà soát các thông tin đã điền ở từng khối và các tệp đã đính kèm giúp em nhé ạ. Sau khi kiểm tra xong, công dân tự bấm nộp hồ sơ trên trang giúp em.",
}

BUSINESS_STOPPED = {
    "md": (
        "⏹️ Em đã dừng tiến trình tự động kê khai theo yêu cầu.\n\n"
        "**Tiến độ:** {fill_status}\n\n"
        "**Đính kèm:** {attachment_status}\n\n"
        "Các thông tin đã lưu trên cổng vẫn được giữ lại."
    ),
    "tts": (
        "Em đã dừng tiến trình tự động kê khai theo yêu cầu. {fill_status_tts}. "
        "{attachment_status_tts}. Các thông tin đã lưu trên cổng vẫn được giữ lại ạ."
    ),
}

BUSINESS_FAILED_PROGRESS = {
    "md": (
        "⚠️ Luồng tự động kê khai đang dừng tại một bước: *{error}*\n\n"
        "**Tiến độ:** {fill_status}\n\n"
        "**Đính kèm:** {attachment_status}\n\n"
        "Các thông tin đã lưu trên cổng vẫn được giữ lại. Công dân bấm **Thử lại** để em xử lý lại ạ."
    ),
    "tts": (
        "Luồng tự động kê khai đang dừng tại một bước. {fill_status_tts}. "
        "{attachment_status_tts}. Các thông tin đã lưu trên cổng vẫn được giữ lại. "
        "Công dân bấm thử lại để em xử lý lại ạ."
    ),
}

BUSINESS_FAILED = {
    "md": (
        "⚠️ Luồng tự điền hộ kinh doanh đang dừng tại một bước: *{error}*\n\n"
        "Dữ liệu và giấy tờ vẫn được giữ lại. Công dân bấm **Thử lại** để em tiếp tục từ trạng thái hiện tại ạ."
    ),
    "tts": (
        "Luồng tự điền hộ kinh doanh đang dừng tại một bước. Dữ liệu vẫn được giữ lại. "
        "Công dân bấm thử lại để em tiếp tục ạ."
    ),
}

DOCS_FORCED_MISSING = {
    "md": (
        "Dạ công dân chốt gửi với **{files_count} tệp**. Em vẫn đọc và điền phần có được; "
        "thiếu thông tin nào em sẽ hỏi lại ạ. Đang xử lý, công dân chờ chút…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Dạ công dân chốt gửi với {files_count} tệp. Em vẫn đọc và điền phần có được, "
    # "thiếu thông tin nào em sẽ hỏi lại ạ. Đang xử lý công dân chờ chút nhé."
    # ),
    "tts": "Dạ công dân chốt gửi với các tệp hiện có. Em vẫn đọc và điền phần có được, thiếu thông tin nào em sẽ hỏi lại ạ. Đang xử lý công dân chờ chút nhé.",
}

FILL_READY = {
    "md": (
        "Xong rồi ạ! Em đã đọc được **{count} trường thông tin** và đang điền vào form bên trái. "
        "Công dân nhìn sang form **kiểm tra lại** giúp em nhé — ô viền **vàng** là em đặt mặc định, "
        "ô viền **đỏ** là còn thiếu."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã đọc được {count} trường thông tin và đang điền vào form bên trái. "
    # "Công dân nhìn sang form kiểm tra lại giúp em nhé. Ô viền vàng là em đặt mặc định, "
    # "ô viền đỏ là còn thiếu ạ."
    # ),
    "tts": "Em đã đọc được các trường thông tin và đang điền vào form bên trái. Công dân nhìn sang form kiểm tra lại giúp em nhé. Ô viền vàng là em đặt mặc định, ô viền đỏ là còn thiếu ạ.",
}

FILL_REPORT_REVIEW = {
    "md": (
        "Em điền được **{filled} ô** ✓{missing_note}\n\n"
        "Công dân rà lại trên form và sửa trực tiếp ô nào chưa đúng."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em điền xong {filled} ô rồi ạ. Công dân rà lại trên form và sửa trực tiếp "
    # "ô nào chưa đúng giúp em ạ."
    # ),
    "tts": "Em điền xong các ô rồi ạ. Công dân rà lại trên form và sửa trực tiếp ô nào chưa đúng giúp em ạ.",
}

PIPELINE_ERROR = {
    "md": (
        "⚠️ Em gặp lỗi khi đọc giấy tờ: *{error}*\n\n"
        "Công dân bấm **thử lại** giúp em, hoặc chụp lại giấy tờ rõ hơn ạ."
    ),
    "tts": "Em gặp lỗi khi đọc giấy tờ công dân bấm thử lại giúp em nhé.",
}

ATTACH_PIPELINE_ERROR = {
    "md": (
        "⚠️ Em gặp lỗi khi chuẩn bị đính kèm giấy tờ: *{error}*\n\n"
        "Các tệp đã nhận vẫn còn trong phiên; công dân bấm **thử lại** giúp em ạ."
    ),
    "tts": "Em gặp lỗi khi chuẩn bị đính kèm. Các tệp vẫn còn, công dân bấm thử lại giúp em nhé.",
}

ATTACH_PLANNING = {
    "md": "Dạ, em đang **lập kế hoạch đính kèm** giấy tờ vào thành phần hồ sơ, chờ em chút ạ…",
    "tts": "Em đang lập kế hoạch đính kèm giấy tờ, công dân chờ chút ạ.",
}

ATTACH_RUNNING = {
    "md": "Dạ, em đang **đính kèm giấy tờ vào hồ sơ** rồi ạ. Công dân chờ em hoàn tất một chút nhé.",
    "tts": "Dạ em đang đính kèm giấy tờ vào hồ sơ rồi ạ. Công dân chờ em hoàn tất một chút nhé.",
}

ATTACH_REQUEST_ON_DECLARATION = {
    "md": (
        "Mình đang ở trang **Kê khai thông tin**. Công dân rà soát lại form rồi chuyển sang "
        "bước **Thành phần hồ sơ** giúp em nhé; sang đó em sẽ tự đính kèm giấy tờ ạ."
    ),
    "tts": (
        "Mình đang ở trang kê khai thông tin. Công dân rà soát lại form rồi chuyển sang bước "
        "thành phần hồ sơ giúp em nhé. Sang đó em sẽ tự đính kèm giấy tờ ạ."
    ),
}

ATTACH_REQUEST_UNKNOWN = {
    "md": (
        "Em chưa nhận rõ yêu cầu. Công dân nói lại ngắn gọn, ví dụ "
        "**“đính kèm giấy tờ”** giúp em ạ."
    ),
    "tts": (
        "Em chưa nhận rõ yêu cầu. Công dân nói lại ngắn gọn, ví dụ đính kèm giấy tờ "
        "giúp em ạ."
    ),
}

# Máy quầy đã chọn "mỗi tài liệu một hồ sơ riêng" trong Cài đặt → không hỏi giữa luồng,
# nhưng phải BÁO vì tách hồ sơ mở nhiều tab (câu này nối vào sau DOCS_COMPLETE_ATTACH).
ATTACH_MODE_PRESET_SPLIT = {
    "md": "\n\nTheo **cài đặt** của quầy, em sẽ tách **mỗi tài liệu một hồ sơ riêng** ạ.",
    "tts": " Theo cài đặt của quầy, em sẽ tách mỗi tài liệu một hồ sơ riêng ạ.",
}

ATTACH_MODE_ASK = {
    "md": (
        "Dạ, em đã nhận **{files_count} tệp**. Công dân muốn đưa các tài liệu vào "
        "**một hồ sơ** hay **mỗi tài liệu một hồ sơ riêng** ạ?"
    ),
    "tts": (
        "Dạ, công dân muốn đính kèm tất cả tài liệu trong một hồ sơ, "
        "hay mỗi tài liệu trong một hồ sơ riêng ạ?"
    ),
}

ATTACH_MODE_SELECTED = {
    "md": "Dạ, công dân chọn **{mode}** ✓\n\nEm đang đọc và chuẩn bị tài liệu, công dân chờ chút ạ…",
    "tts": "Dạ, công dân chọn {mode}. Em đang đọc và chuẩn bị tài liệu, công dân chờ chút ạ.",
}

ATTACH_PLAN_READY = {
    "md": (
        "📎 Kế hoạch đính kèm đã xong — **{count} mục**:\n\n{plan_list}\n\n"
        "Em đang **tự đính từng tệp** vào thành phần hồ sơ trên trang, công dân chờ chút ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": "Kế hoạch đính kèm xong rồi, {count} mục. Em đang tự đính từng tệp vào hồ sơ, công dân chờ chút ạ.",
    "tts": "Kế hoạch đính kèm xong rồi ạ. Em đang tự đính từng tệp vào hồ sơ, công dân chờ chút ạ.",
}

ATTACH_PLAN_READY_SPLIT = {
    "md": (
        "📎 Kế hoạch đính kèm đã xong — **{count} tài liệu**:\n\n{plan_list}\n\n"
        "Em sẽ đưa **mỗi tài liệu vào một hồ sơ riêng** và xử lý lần lượt từng tab ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Kế hoạch đính kèm xong rồi, {count} tài liệu. "
    # "Em sẽ đưa mỗi tài liệu vào một hồ sơ riêng và xử lý lần lượt từng tab ạ."
    # ),
    "tts": "Kế hoạch đính kèm xong rồi ạ. Em sẽ đưa mỗi tài liệu vào một hồ sơ riêng và xử lý lần lượt từng tab ạ.",
}

ATTACH_PLAN_READY_SIGNATURE_SPLIT = {
    "md": (
        "📎 Kế hoạch đính kèm đã xong — **{count} hồ sơ**:\n\n{plan_list}\n\n"
        "Mỗi hồ sơ có **một giấy tờ cần chứng thực chữ ký ở STT 1**; riêng hồ sơ đầu tiên "
        "có thêm **giấy tờ tùy thân ở STT 2**. Em sẽ xử lý lần lượt từng tab ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Kế hoạch đính kèm xong rồi, {count} hồ sơ. Mỗi hồ sơ có một giấy tờ cần chứng thực "
    # "chữ ký ở mục một; hồ sơ đầu tiên có thêm giấy tờ tùy thân ở mục hai. "
    # "Em sẽ xử lý lần lượt từng tab ạ."
    # ),
    "tts": "Kế hoạch đính kèm xong rồi ạ. Mỗi hồ sơ có một giấy tờ cần chứng thực chữ ký ở mục một; hồ sơ đầu tiên có thêm giấy tờ tùy thân ở mục hai. Em sẽ xử lý lần lượt từng tab ạ.",
}

# Đòi đính kèm khi trang còn ở bước kê khai (wizard chưa sang "Thành phần hồ sơ") —
# chạy engine lúc này sẽ ra "0 tệp" vô nghĩa → dặn chuyển bước, sang đến nơi tự đính.
ATTACH_WRONG_PAGE = {
    "md": (
        "Dạ công dân đang ở bước **Kê khai thông tin** ạ. Công dân bấm nút tiếp tục của trang "
        "để chuyển sang bước **Thành phần hồ sơ** — vào đến nơi em **tự đính kèm** giấy tờ ngay ạ."
    ),
    "tts": (
        "Dạ công dân đang ở bước kê khai thông tin ạ. Công dân bấm tiếp tục để chuyển sang "
        "bước thành phần hồ sơ, vào đến nơi em tự đính kèm giấy tờ ngay ạ."
    ),
}

ATTACH_PAGE_REACHED = {
    "md": "Thấy bước **Thành phần hồ sơ** rồi ✓ Em đính kèm giấy tờ vào hồ sơ ngay ạ…",
    "tts": "Thấy bước thành phần hồ sơ rồi ạ. Em đính kèm giấy tờ vào hồ sơ ngay ạ.",
}

ATTACH_NONE = {
    "md": (
        "⚠️ Em chưa gắn được tệp nào vào hồ sơ{error_note}. "
        "Công dân kiểm tra trang đang ở bước **Thành phần hồ sơ** giúp em, rồi bấm **Đính kèm lại** ạ."
    ),
    "tts": (
        "Em chưa gắn được tệp nào vào hồ sơ ạ. Công dân kiểm tra trang đang ở bước "
        "thành phần hồ sơ giúp em, rồi bấm đính kèm lại nhé."
    ),
}

ATTACH_DONE = {
    "md": (
        "✅ Em đã đính xong **{attached} tệp** vào thành phần hồ sơ.\n\n"
        "Công dân **rà lại lần cuối** trên trang rồi bấm **Nộp hồ sơ / Gửi hồ sơ** giúp em ạ — "
        "bước nộp cuối em để công dân tự bấm cho chắc chắn."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã đính xong {attached} tệp vào hồ sơ rồi ạ. "
    # "Công dân rà lại lần cuối rồi bấm nộp hồ sơ giúp em nhé."
    # ),
    "tts": "Em đã đính xong các tệp vào hồ sơ rồi ạ. Công dân rà lại lần cuối rồi bấm nộp hồ sơ giúp em nhé.",
}

ATTACH_DONE_WITH_ERRORS = {
    "md": (
        "⚠️ Em đính được **{attached} tệp**, còn lỗi:\n\n{error_list}\n\n"
        "Công dân đính tay phần còn thiếu (nút *Chọn tệp đính kèm* trên trang) rồi bấm **Nộp hồ sơ** giúp em ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": "Em đính được {attached} tệp, còn vài mục lỗi. Công dân đính tay phần còn thiếu rồi nộp hồ sơ giúp em ạ.",
    "tts": "Em đính được một số tệp, còn vài mục lỗi. Công dân đính tay phần còn thiếu rồi nộp hồ sơ giúp em ạ.",
}

ATTACH_SUPPLEMENT_ASK = {
    "md": (
        "Dạ, em đã mở lại phiên **{session_id}** cùng toàn bộ danh sách giấy tờ đã cung cấp. "
        "Công dân có thể bấm vào từng loại giấy tờ để **xem hoặc xóa tệp** như trước ạ.\n\n"
        "Nếu muốn thêm tệp, công dân chọn **Chụp bằng điện thoại** hoặc **Scan tại quầy** "
        "bên dưới. Xong rồi bấm **{finish_action}**; {finish_detail} ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Dạ, em đã mở lại toàn bộ danh sách giấy tờ. Công dân có thể xem, xóa hoặc thêm "
    # "tệp nếu cần, rồi bấm {finish_action} ạ."
    # ),
    "tts": "Dạ, em đã mở lại toàn bộ danh sách giấy tờ. Công dân có thể xem, xóa hoặc thêm tệp nếu cần, rồi bấm nút xác nhận bên dưới ạ.",
}

ATTACH_SUPPLEMENT_SESSION_EXPIRED = {
    "md": (
        "⚠️ Phiên giấy tờ cũ đã hết hạn nên em không khôi phục được danh sách trước đó. "
        "Công dân chọn cách cung cấp giấy tờ để tải lại các tệp cần xử lý giúp em ạ."
    ),
    "tts": (
        "Phiên giấy tờ cũ đã hết hạn. Công dân chọn cách cung cấp giấy tờ để tải lại "
        "các tệp cần xử lý giúp em ạ."
    ),
}

DOCUMENT_ADJUSTMENT_WRONG_PAGE = {
    "md": (
        "Mình chưa ở trang **Kê khai thông tin** nên em chưa thể điền lại tờ khai. "
        "Em vẫn giữ nguyên danh sách giấy tờ; công dân quay lại trang Kê khai rồi bấm "
        "**Hoàn tất điều chỉnh, điền lại tờ khai** giúp em ạ."
    ),
    "tts": (
        "Mình chưa ở trang kê khai thông tin nên em chưa thể điền lại tờ khai. "
        "Công dân quay lại trang kê khai rồi bấm hoàn tất điều chỉnh giúp em ạ."
    ),
}

ATTACH_SUPPLEMENT_AFTER_SUBMIT = {
    "md": "Hồ sơ đã được **nộp thành công**, nên em không thể sửa danh sách giấy tờ của hồ sơ này nữa ạ.",
    "tts": "Hồ sơ đã nộp thành công nên em không thể sửa danh sách giấy tờ của hồ sơ này nữa ạ.",
}

ATTACH_ALL_FILES_EXIST = {
    "md": (
        "✅ Em đã kiểm tra lại danh sách giấy tờ. Các tệp còn lại đều đã có trên hồ sơ "
        "nên em không đính trùng thêm ạ.\n\n"
        "Công dân rà lại lần cuối rồi bấm **Nộp hồ sơ / Gửi hồ sơ** giúp em nhé."
    ),
    "tts": (
        "Em đã kiểm tra lại. Các tệp còn lại đều đã có trên hồ sơ nên em không đính "
        "trùng thêm ạ. Công dân rà lại rồi nộp hồ sơ giúp em nhé."
    ),
}

ATTACH_SPLIT_DONE = {
    "md": (
        "✅ Em đã đính xong **{succeeded}/{total} hồ sơ**, mỗi tài liệu nằm trong một hồ sơ riêng.\n\n"
        "Công dân rà lại từng tab rồi bấm **Nộp hồ sơ / Gửi hồ sơ** giúp em ạ — "
        "bước nộp cuối em để công dân tự bấm cho chắc chắn."
    ),
    "tts": (
        "Em đã đính xong {succeeded} trên {total} hồ sơ, mỗi tài liệu trong một hồ sơ riêng. "
        "Công dân rà lại từng tab rồi bấm nộp hồ sơ giúp em nhé."
    ),
}

ATTACH_SPLIT_DONE_WITH_ERRORS = {
    "md": (
        "⚠️ Em đính được **{succeeded}/{total} hồ sơ**, còn lỗi:\n\n{error_list}\n\n"
        "Công dân kiểm tra các tab còn thiếu và đính tay giúp em ạ."
    ),
    "tts": (
        "Em đính được {succeeded} trên {total} hồ sơ, còn một số hồ sơ lỗi. "
        "Công dân kiểm tra các tab còn thiếu giúp em ạ."
    ),
}

SCAN_PICK = {
    "md": (
        "Dạ công dân chọn **📷 Scan tại quầy** ✓\n\n"
        "Công dân **đặt giấy tờ lên máy quét** ở quầy rồi **ấn nút Scan** — scan tới đâu "
        "em **tự nhận** tới đó vào hồ sơ, công dân không phải chọn tệp ạ."
    ),
    "tts": (
        "Dạ công dân đặt giấy tờ lên máy quét rồi bấm nút Scan. "
        "Scan tới đâu thì em tự nhận giấy tờ đó vào hồ sơ ạ."
    ),
}

SCAN_PICK_ATTACH = {
    "md": (
        "Dạ công dân chọn **📷 Scan tại quầy** ✓\n\n"
        "Công dân **đặt giấy tờ lên máy quét** ở quầy rồi **ấn nút Scan**. Scan tới đâu em "
        "**tự nhận** tới đó — tất cả nhận thẳng là **Giấy tờ cần chứng thực bản sao**, "
        "không phân loại ở bước này ạ."
    ),
    "tts": (
        "Dạ công dân đặt giấy tờ lên máy quét rồi bấm nút Scan. Em tự nhận tất cả là "
        "giấy tờ cần chứng thực bản sao ạ."
    ),
}

PROFILE_ASK_PHONE = {
    "md": (
        "Dạ công dân chọn **📁 Lấy dữ liệu đã lưu** ✓\n\n"
        "Công dân đọc/nhập **số điện thoại** đã dùng để lưu hồ sơ lần trước giúp em ạ."
    ),
    "tts": "Công dân đọc số điện thoại đã dùng để lưu hồ sơ lần trước giúp em ạ.",
}

PROFILE_NOT_FOUND = {
    "md": (
        "Dạ em **chưa tìm thấy hồ sơ đã lưu** với số **{phone}** ạ. "
        "Công dân kiểm tra lại số, hoặc chọn cách khác bên dưới nhé:"
    ),
    "tts": "Em chưa tìm thấy hồ sơ đã lưu với số này ạ. Công dân kiểm tra lại số hoặc chọn cách khác nhé.",
}

PROFILE_APPLIED = {
    "md": (
        "✅ Em tìm thấy **hồ sơ đã lưu** của công dân ({count} giấy tờ) — không phải chụp lại gì cả!\n\n"
        "Em bắt đầu **đọc và điền vào form** luôn nhé, công dân chờ chút ạ…"
    ),
    "tts": "Em tìm thấy hồ sơ đã lưu của công dân rồi, không phải chụp lại gì cả. Em điền vào form luôn nhé.",
}

DONE_SUBMITTED = {
    "md": (
        "Dạ, công dân đã hoàn thành việc nộp hồ sơ lên **Cổng Dịch vụ công**. "
        "Công dân có muốn em đăng xuất tài khoản **VNeID** giúp mình luôn không ạ?\n\n"
        "Nếu chưa chọn, em sẽ tự đăng xuất sau **2 phút** để bảo vệ tài khoản."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Công dân đã hoàn thành việc nộp hồ sơ lên Cổng Dịch vụ công. Công dân có muốn "
    # "em đăng xuất tài khoản VNeID giúp mình luôn không ạ? Nếu chưa chọn, em sẽ tự "
    # "đăng xuất sau hai phút để bảo vệ tài khoản."
    # ),
    "tts": "Công dân đã hoàn thành việc nộp hồ sơ lên Cổng Dịch vụ công. Công dân có muốn em đăng xuất tài khoản vi en ai đi giúp mình luôn không ạ? Nếu chưa chọn, em sẽ tự đăng xuất sau hai phút để bảo vệ tài khoản.",
}

# Lời mời đánh giá (đọc khi hiện card đánh giá NGAY sau nộp thành công, trước 2 nút đăng xuất).
RATE_INVITE = {
    "md": (
        "Dạ, công dân đã nộp hồ sơ thành công 🎉 Trước khi kết thúc, công dân **đánh giá giúp em** "
        "hôm nay Trợ lý hỗ trợ thế nào ạ? Chỉ cần chạm một dòng, không bắt buộc."
    ),
    "tts": (
        "Dạ công dân đã nộp hồ sơ thành công. Trước khi kết thúc, công dân đánh giá giúp em hôm nay "
        "Trợ lý hỗ trợ thế nào ạ? Chỉ cần chạm một dòng, không bắt buộc."
    ),
}

PHONE_SUBSCRIBED = {
    "md": "✅ Em đã ghi nhận số **{phone}** — có tiến độ mới em nhắn công dân ngay ạ.",
    "tts": "Em đã ghi nhận số điện thoại, có tiến độ mới em nhắn công dân ngay ạ.",
}

PHONE_INVALID = {
    "md": "Dạ số **{phone}** chưa đúng định dạng ạ — công dân đọc lại 10 số bắt đầu bằng 0 giúp em nhé.",
    "tts": "Dạ số này chưa đúng, công dân đọc lại mười số bắt đầu bằng số không giúp em nhé.",
}


PROFILE_NEED_PHONE = {
    "md": "Dạ, để **lưu hồ sơ** công dân cho em xin **số điện thoại** làm chìa khoá tra cứu ạ.",
    "tts": "Để lưu hồ sơ, công dân cho em xin số điện thoại làm chìa khoá tra cứu ạ.",
}

PROFILE_SAVED = {
    "md": (
        "💾 Đã **lưu hồ sơ** theo số **{phone}** ({count} giấy tờ). "
        "Lần sau công dân chỉ cần chọn **📁 Lấy dữ liệu đã lưu** + đọc số này là xong ạ.\n\n"
        "🔒 Muốn xoá lúc nào, công dân bấm **🗑️ Xóa dữ liệu** hoặc nói \"xoá hồ sơ của tôi\"."
    ),
    "tts": "Đã lưu hồ sơ theo số điện thoại của công dân. Lần sau chỉ cần đọc số này là không phải chụp lại giấy tờ ạ.",
}

DATA_DELETED = {
    "md": "🗑️ Em đã **xoá toàn bộ** dữ liệu: hồ sơ đã lưu, ảnh giấy tờ và phiên làm việc. Cảm ơn công dân đã sử dụng ạ!",
    "tts": "Em đã xoá toàn bộ dữ liệu của công dân. Cảm ơn công dân đã sử dụng ạ.",
}

CHANGED_LOCATION = {
    "md": "Dạ, em đã chọn nơi làm thủ tục thành **{ward}, {province}** ✓",
    "tts": "Em đã chọn nơi làm thủ tục thành {ward}, {province}.",
}

CHANGED_PROCEDURE_RESET = {
    "md": "Dạ, mình đổi sang thủ tục khác nhé. Công dân chọn thủ tục bên dưới ạ:",
    "tts": "Dạ, mình đổi sang thủ tục khác. Công dân chọn thủ tục ạ.",
}

OFF_SCOPE = {
    "md": (
        "Dạ, câu này nằm ngoài phạm vi em được đào tạo ạ 🙏 "
        "Em hỗ trợ được **{count} thủ tục**: {procedures}. Công dân cần làm thủ tục nào ạ?"
    ),
    "tts": "Dạ, câu này ngoài phạm vi em hỗ trợ ạ. Công dân cần làm thủ tục nào trong danh sách ạ?",
}

FALLBACK_CLARIFY = {
    "md": "Dạ công dân nói rõ hơn giúp em với ạ — công dân muốn **{hint}** phải không ạ?",
    "tts": "Dạ công dân nói rõ hơn giúp em với ạ.",
}

# Thẻ hướng dẫn đặt giấy lên máy quét (ảnh + lời), extension DỰNG như SCAN_FEEDBACK.
# TEXT THUẦN, không thẻ HTML: extension escape trước rồi mới đổi **…** thành in đậm, nên chữ
# ở đây không chèn được markup vào trang. "alt" là mô tả ảnh cho trình đọc màn hình.
SCAN_GUIDE = {
    "heading": "🖨️ Đặt giấy tờ lên máy quét ở quầy",
    "body": "Công dân đặt giấy lên máy scan **theo hướng dẫn trong hình** rồi ấn nút **Scan** ạ.",
    "alt": "Hướng dẫn scan: đặt giấy úp mặt cần scan xuống rồi ấn nút Scan",
    "zoom": "🔍 Bấm để xem hình to",
    "note": ("Chỉ đặt **từng tờ một** — máy tự kéo giấy vào. "
             "Xong hết thì bấm **\"Đã đưa đủ\"** giúp em."),
}

# Thẻ phản hồi máy quét — extension DỰNG, không đi qua handle_turn (sự kiện scan là của máy
# quầy, không phải một lượt chat). Chữ vẫn để ở đây để bản Mông nằm cùng chỗ với lời thoại
# còn lại; /voice/config đẩy cả cụm xuống extension.
# {count} là số tệp đã nhận. "tts" đọc ở tệp ĐẦU (nói đủ hướng dẫn), "ttsMore" cho các tệp sau.
SCAN_FEEDBACK = {
    "md": ("🖨️ Em đã nhận **{count} tệp** giấy tờ từ máy quét.\n\n"
           "- Còn giấy tờ cần scan thì công dân **đặt tiếp tờ nữa** vào máy — em tự nhận ạ.\n"
           "- Đã đủ rồi thì bấm **\"Đã đưa đủ giấy tờ\"** ở dưới để em bắt đầu xử lý ạ."),
    "tts": ("Em đã nhận được một tệp giấy tờ. Nếu còn giấy tờ, công dân đặt tiếp vào máy scan, "
            "em sẽ tự nhận. Xong hết thì bấm nút Đã đưa đủ giấy tờ ạ."),
    "ttsMore": ("Em đã nhận thêm một tệp, tổng cộng {count} tệp. Còn nữa thì công dân đặt tiếp "
                "vào máy scan, đủ rồi bấm nút Đã đưa đủ giấy tờ để em thực hiện xử lý ạ."),
}

# Xác nhận đổi ngôn ngữ. LANG_OFF cố tình CHỈ có tiếng Việt: lượt này _TURN_LANG đã là "vi".
LANG_ON = {
    "md": "Dạ, em bật **chế độ tiếng Mông** rồi ạ — em sẽ đọc và nghe bằng tiếng Mông.",
    "tts": "Dạ, em bật chế độ tiếng Mông rồi ạ.",
}

LANG_OFF = {
    "md": "Dạ, em chuyển về **tiếng Việt** rồi ạ.",
    "tts": "Dạ, em chuyển về tiếng Việt rồi ạ.",
}

# Câu trả lời hỏi-tự-do và các câu trấn an. Trước đây dựng thẳng bằng f-string trong flow.py
# nên KHÔNG có bản Mông nào — quầy Lai Châu bật tiếng Mông vẫn nghe tiếng phổ thông.
PROCEDURE_IN_PROGRESS = {
    "md": ("Dạ mình đang làm **{procedure}** rồi ạ — đến bước **{step}**. "
           "Công dân cứ tiếp tục theo hướng dẫn nhé."),
    "tts": "Dạ mình đang làm {procedure} rồi ạ, công dân cứ tiếp tục theo hướng dẫn nhé.",
}

DOC_LIST_ANSWER = {
    "md": "Dạ, để làm **{procedure}** công dân cần:\n\n{documents_md}",
    "tts": "Dạ, công dân cần chuẩn bị: {documents_tts}.",
}

ANSWER_ONLY_DOCS_AND_STEPS = {
    "md": ("Dạ, về **{procedure}**: em nắm chắc nhất phần **giấy tờ cần chuẩn bị** và các bước "
           "nộp trực tuyến; chi tiết khác (lệ phí, thời hạn) công dân xem trên trang thủ tục "
           "giúp em ạ."),
    "tts": "Dạ, chi tiết này công dân xem thêm trên trang thủ tục giúp em ạ.",
}

PICK_FILES_AGAIN = {
    "md": "Dạ, công dân chọn thêm tệp trong cửa sổ vừa mở ạ.",
    "tts": "Công dân chọn thêm tệp nhé.",
}

BUSINESS_STILL_PROCESSING = {
    "md": "Dạ em vẫn đang xử lý hồ sơ hộ kinh doanh, công dân chờ em chút ạ…",
    "tts": "Dạ em vẫn đang xử lý hồ sơ hộ kinh doanh, công dân chờ em chút ạ.",
}

STILL_READING_DOCUMENTS = {
    "md": "Dạ em vẫn đang đọc giấy tờ, sắp xong rồi ạ…",
    "tts": "Dạ em vẫn đang đọc giấy tờ, sắp xong rồi ạ.",
}

# Nhãn bước hiển thị trên thanh tiến trình (progress.label) — khớp docs/03a §3.
STEP_LABELS = {
    "greet": "Chọn thủ tục",
    "confirm_procedure": "Xác nhận thủ tục",
    "choose_variant": "Chọn trường hợp",
    "guide_login": "Đăng nhập VNeID",
    "consent": "Xin phép xử lý dữ liệu",
    "ask_doc_method": "Cách cung cấp giấy tờ",
    "qr_waiting": "Quét mã QR",
    "collecting_docs": "Gửi giấy tờ",
    "owner_filling": "Điền chủ hồ sơ",
    "owner_waiting_next": "Kiểm tra chủ hồ sơ",
    "choosing_attach_mode": "Cách đính kèm",
    "filling": "Điền hồ sơ",
    "reviewing": "Rà soát",
    "attaching": "Đính kèm",
    "done": "Hoàn thành",
}

# Thứ tự bước cho progress.step (1-based).
STEP_ORDER = [
    "greet", "confirm_procedure", "choose_variant", "guide_login", "consent", "ask_doc_method",
    "qr_waiting", "collecting_docs", "choosing_attach_mode", "owner_filling", "owner_waiting_next",
    "filling", "reviewing", "attaching", "done",
]
