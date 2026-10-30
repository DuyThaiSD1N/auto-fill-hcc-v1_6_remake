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
        "**Xin chào công dân!** Em là Trợ lý nhân dân.\n\n"
        "Công dân kiểm tra **nơi làm thủ tục**, rồi **chọn thủ tục** bên dưới (bấm thẻ hoặc nói tên) ạ."
    ),
    "tts": "Xin chào công dân, em là Trợ lý nhân dân. Công dân bấm chọn, hoặc nói tên thủ tục cần làm ạ.",
}

# Thứ tự MỚI: chọn thủ tục trước, chọn nơi sau. Màn chào không còn card chọn nơi nên câu chào
# cũng không được bảo công dân "kiểm tra nơi làm thủ tục bên dưới".
# Công dân chỉ nói "bắt đầu" (chưa nêu thủ tục) ở màn chào.
GREET_START_ONLY = {
    "md": "Dạ, công dân **chọn thủ tục** bên dưới hoặc nói tên thủ tục cần làm ạ.",
    "tts": "Dạ, công dân chọn thủ tục bên dưới hoặc nói tên thủ tục cần làm ạ.",
}
GREET_PROCEDURE_FIRST = {
    "md": (
        "**Xin chào công dân!** Em là Trợ lý nhân dân.\n\n"
        "Công dân **chọn thủ tục** bên dưới (bấm thẻ hoặc nói tên) ạ."
    ),
    "tts": "Xin chào công dân, em là Trợ lý nhân dân. Công dân bấm chọn, hoặc nói tên thủ tục cần làm ạ.",
}

# Nơi làm thủ tục giờ hiện NGAY TRONG lượt xác nhận → mời công dân soát nó trước khi đồng ý.
# Hỏi thẳng cả ba thứ trong MỘT câu (thủ tục + nơi làm + đối tượng) thay vì bảo "kiểm tra bên
# dưới": người lớn tuổi đọc câu hỏi có/không nhanh hơn là tự đối chiếu ba dòng trong card.
CONFIRM_PROCEDURE_WITH_LOCATION = {
    "md": (
        "Dạ, công dân làm **{procedure}** · tại **{place}** · **{subject}** — đúng không ạ?\n\n"
        "Đúng → bấm **Đồng ý**. Chưa đúng → chọn lại bên dưới → bấm **Đồng ý**."
    ),
    "tts": (
        # Chỉ đọc vế "đúng thì bấm Đồng ý"; vế chọn lại khi chưa đúng đã có trên màn hình, đọc thêm thì dài.
        # Thêm "Nếu": "…đúng không ạ? Đúng thì…" hai chữ "đúng" sát nhau làm giọng đọc nghe như bị lắp.
        "Dạ, công dân làm thủ tục {procedure}, tại {place}, {subject}, đúng không ạ? "
        "Nếu đúng thì bấm Đồng ý."
    ),
}

GREET_RETURNING = {
    "md": (
        "Công dân đang làm dở **{procedure}** (bước: {step_label}). "
        "**Tiếp tục** hay **làm thủ tục khác** ạ?"
    ),
    "tts": "Dạ, công dân đang làm dở thủ tục {procedure}. Làm tiếp, hay làm thủ tục khác ạ?",
}

CONFIRM_PROCEDURE = {
    "md": "Dạ, công dân làm **{procedure}** tại **{place}**, đúng không ạ?",
    "tts": "Dạ, công dân làm thủ tục {procedure}, tại {place}, đúng không ạ?",
}

PROCEDURE_NOT_RECOGNIZED = {
    "md": (
        "Dạ em chưa nhận ra thủ tục ạ. "
        "Công dân **chọn 1 trong {count} thủ tục** bên dưới, hoặc nói lại tên."
    ),
    "tts": "Dạ, em chưa nhận ra thủ tục. Công dân chọn trong danh sách, hoặc nói lại tên ạ.",
}

# Câu gõ/nói hợp với nhiều thủ tục → hỏi lại kèm nút gợi ý. options_* là tên thủ tục lấy từ registry.
PROCEDURE_UNCLEAR = {
    "md": "Dạ, công dân cần thủ tục nào ạ?\n\n{options_md}",
    "tts": "Dạ, có phải {options_tts} không ạ? Công dân bấm chọn giúp em.",
}

# Thủ tục đặc thù tỉnh (provinceOnly) mà tài khoản đang đăng nhập ở tỉnh khác → không mở được.
PROCEDURE_PROVINCE_LOCKED = {
    "md": "Dạ, **{procedure}** chỉ làm được ở **{provinces}** ạ. Công dân chọn thủ tục khác bên dưới.",
    "tts": "Dạ, thủ tục này chỉ làm được ở {provinces}. Công dân chọn thủ tục khác ạ.",
}

GUIDE_LOGIN = {
    "md": "Nếu trang hiện mã đăng nhập: mở app **VNeID** → **Quét QR** → quét mã trên màn hình ạ.",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Công dân mở app VNeID trên điện thoại chọn Quét QR, rồi quét mã trên màn hình để đăng nhập. "
    # "Đăng nhập xong em sẽ hướng dẫn tiếp ạ."
    # ),
    "tts": "Nếu trang hiện mã, công dân mở ứng dụng vi en ai đi, chọn Quét quy rờ, rồi quét mã ạ.",
}

# Máy quét / chọn tệp từ máy: công dân chủ động bấm "Đã đưa đủ" khi xong. Câu này NỐI vào SCAN_PICK.
SCAN_AUTO_RUN_NOTE = {
    "md": " Xong hết → bấm **Đã đưa đủ giấy tờ** ạ.",
    "tts": " Xong hết thì bấm Đã đưa đủ giấy tờ ạ.",
}

GUIDE_AGENCY_SELECT = {
    "md": (
        "Em đang mở **{procedure}**, tự chọn **{ward}, {province}** và bấm **Nộp trực tuyến**. "
        "Công dân chờ chút ạ."
    ),
    "tts": "Em đang mở trang và tự chọn cơ quan. Công dân chờ em chút ạ.",
}

# Thủ tục cổng Bộ NN&MT (agencyProvinceOnly): trang DVCQG chỉ cần chọn TỈNH rồi Đồng ý;
# kết quả đầu tiên "Nộp trực tuyến" chính là Sở chuyên ngành.
GUIDE_AGENCY_SELECT_PROVINCE = {
    "md": (
        "Em đang mở **{procedure}**, tự chọn **tỉnh {province}** → **{agency}** → **Nộp trực tuyến**. "
        "Công dân chờ chút ạ."
    ),
    "tts": "Em đang mở trang và tự chọn cơ quan. Công dân chờ em chút ạ.",
}

# Hỏi "Trường hợp giải quyết" (cấp mới / cấp lại) NGAY sau khi xác nhận thủ tục — lựa chọn
# này quyết định option trên cổng MAE nên phải chốt trước khi mở trang.
# Danh sách trường hợp do REGISTRY của từng thủ tục quyết định (variants.options) — dựng sẵn
# thành {options_md}/{options_tts} rồi mới nhét vào đây, nên câu này dùng chung cho mọi thủ tục
# có bước "Chọn trường hợp giải quyết", không riêng cấp mới/cấp lại.
CHOOSE_VARIANT = {
    "md": "Dạ, **{procedure}** có {count} trường hợp, công dân chọn 1 ạ:\n\n{options_md}",
    "tts": "Dạ, có {count} trường hợp: {options_tts}. Công dân chọn trường hợp nào ạ?",
}

CHOOSE_VARIANT_REMIND = {
    "md": "Dạ, công dân chọn 1 trường hợp ạ:\n\n{options_md}",
    "tts": "Dạ, công dân chọn một trường hợp: {options_tts} ạ.",
}

# Bước "Chọn trường hợp giải quyết" ở dạng HỘP THOẠI chỉ có Đơn vị thực hiện + Trường hợp giải
# quyết (cổng Bộ Xây dựng) — không có ô Tỉnh/radio Sở như trang MAE nên không nhắc tới chúng.
VARIANT_DIALOG_AUTOFILL_GUIDE = {
    "md": "Em chọn **{variant_label}** → bấm **Đồng ý** để sang trang kê khai ạ.",
    "tts": "Dạ, em chọn trường hợp {variant_label}, rồi bấm Đồng ý ạ.",
}

# Hộp thoại "Chọn trường hợp giải quyết" của cổng Bộ Xây dựng — danh sách lựa chọn ĐỌC TỪ CỔNG
# (ô Đơn vị thực hiện = nơi xử lý, ô Trường hợp giải quyết = trường hợp kèm thời gian). Chỉ hỏi
# những ô có từ 2 lựa chọn; {questions} = "nơi xử lý" / "trường hợp giải quyết" / cả hai.
CHOOSE_MAE_DIALOG = {
    "md": (
        "Dạ, thủ tục **{procedure}** cần chọn **{questions}** ạ.\n\n{options_md}\n\n"
        "Công dân chọn ở thẻ bên dưới rồi bấm **Xác nhận**, hoặc nói tên lựa chọn giúp em nhé ạ."
    ),
    "tts": (
        "Dạ, thủ tục này cần chọn {questions}. {options_tts}. Công dân chọn ở thẻ bên dưới, "
        "hoặc nói tên lựa chọn giúp em nhé ạ."
    ),
}

CHOOSE_MAE_DIALOG_REMIND = {
    "md": (
        "Dạ, công dân chọn giúp em **{questions}** ở thẻ bên dưới rồi bấm **Xác nhận** để em "
        "làm tiếp ạ."
    ),
    "tts": "Dạ, công dân chọn giúp em {questions} ở thẻ bên dưới rồi bấm xác nhận để em làm tiếp ạ.",
}

MAE_DIALOG_FAILED = {
    "md": (
        "⚠️ Em chưa chọn tự động được trên trang: *{error}*\n\n"
        "Công dân chọn tay giúp em ở hộp thoại **Chọn trường hợp giải quyết**: Đơn vị thực hiện "
        "**{agency}**, Trường hợp giải quyết **{process}**, rồi bấm **Đồng ý** ạ."
    ),
    "tts": (
        "Em chưa chọn tự động được ạ. Công dân chọn tay giúp em đơn vị thực hiện và trường hợp "
        "giải quyết ở hộp thoại trên trang, rồi bấm đồng ý ạ."
    ),
}

MAE_DIALOG_AUTOFILL_GUIDE = {
    "md": "Dạ, em chọn {choice_md} rồi ấn **Đồng ý** để sang trang kê khai nhé ạ.",
    "tts": "Dạ, em chọn {choice_tts} rồi ấn đồng ý để sang trang kê khai nhé ạ.",
}

# Trang MAE "chọn nơi và loại": bot tự điền Tỉnh + Sở + Trường hợp giải quyết rồi bấm
# "Đồng ý và tiếp tục" — câu hướng dẫn theo yêu cầu nghiệp vụ.
MAE_AGENCY_AUTOFILL_GUIDE = {
    "md": "Em chọn **tỉnh {province}** · **{agency}** · **{variant_label}** → bấm **Đồng ý và tiếp tục** ạ.",
    "tts": "Dạ, em chọn tỉnh {province}, {agency}, trường hợp {variant_label}, rồi bấm Đồng ý và tiếp tục ạ.",
}

# Hộp thoại chọn cơ quan của cổng bộ KHÔNG có ô "Trường hợp giải quyết" (vd Bộ Nội vụ: UBND tỉnh →
# Sở/Ban ngành → Sở Nội vụ). Câu của MAE nhắc tên trường hợp nên dùng lại sẽ ra câu cụt.
AGENCY_DEPT_DIALOG_AUTOFILL_GUIDE = {
    "md": "Em chọn **UBND {province}** · **{agency}** → bấm **Đồng ý và tiếp tục** ạ.",
    "tts": "Dạ, em chọn ủy ban nhân dân {province}, {agency}, rồi bấm Đồng ý và tiếp tục ạ.",
}

# Cùng hộp thoại đó nhưng thủ tục giải quyết ở CẤP XÃ (Bộ Nội vụ, người có công từ trần): chọn
# Tỉnh + Phường/Xã chứ không phải Sở, nên câu trên dùng lại sẽ đọc sai cấp cơ quan.
AGENCY_WARD_DIALOG_AUTOFILL_GUIDE = {
    "md": "Em chọn **{province}** · **{ward}** → bấm **Đồng ý và tiếp tục** ạ.",
    "tts": "Dạ, em chọn {province}, {ward}, rồi bấm Đồng ý và tiếp tục ạ.",
}

MAE_AGENCY_FAILED = {
    "md": (
        "⚠️ Em chưa tự chọn được (*{error}*).\n\n"
        "Công dân chọn tay: "
        "**Tỉnh {province}** → **Sở/Ban ngành** → **{agency}** → **{variant_label}** → bấm "
        "**Đồng ý và tiếp tục** ạ."
    ),
    "tts": (
        "Dạ, em chưa tự chọn được. "
        "Công dân chọn tỉnh {province}, {agency}, trường hợp {variant_label}, "
        "rồi bấm Đồng ý và tiếp tục ạ."
    ),
}

MAE_AGENCY_WARD_FAILED = {
    "md": (
        "⚠️ Em chưa tự chọn được (*{error}*).\n\n"
        "Công dân chọn tay: **{province}** → **Phường/Xã** → **{ward}** → bấm **Đồng ý và tiếp tục** ạ."
    ),
    "tts": (
        "Dạ, em chưa tự chọn được. "
        "Công dân chọn {province}, phường xã {ward}, rồi bấm Đồng ý và tiếp tục ạ."
    ),
}

# Liên thông: trang "Chọn cơ quan thực hiện" (Angular, KHÔNG có needsAgencySelect nên bot không
# tự chọn) → dặn người dân chọn tỉnh/xã + bấm tiếp, nói 1 lần; sang trang kê khai thì thôi.
AGENCY_MANUAL_GUIDE = {
    "md": "Công dân chọn **tỉnh, xã** trên trang → bấm **Chuyển bước tiếp theo** ạ.",
    "tts": "Công dân chọn tỉnh và xã trên trang, rồi bấm Chuyển bước tiếp theo ạ.",
}

# Trợ lý ĐIỀN HỘ bước chọn cơ quan (liên thông khai sinh): loại khai sinh, tỉnh/xã theo nơi ở,
# trường hợp khai sinh/ĐKTT, tick "Cùng địa bàn". Điền xong người dân tự bấm "Chuyển bước tiếp theo".
AGENCY_AUTOFILL_GUIDE = {
    "md": (
        "Em đang chọn **cơ quan thực hiện** theo nơi ở **{ward}, {province}**. "
        "Xong → công dân bấm **Chuyển bước tiếp theo** ạ."
    ),
    "tts": "Em đang chọn cơ quan cho công dân. Xong thì công dân bấm Chuyển bước tiếp theo ạ.",
}

# MỘT CÂU duy nhất đọc TRÊN chính trang login SSO (Hướng A): xác nhận cơ quan + dặn VNeID/Quét QR
# gộp lại (không tách 2 bong bóng). Panel còn hiện → đọc đủ → đọc xong FE thu gọn
# (action collapse_after_tts ở flow) để lộ mã QR cho công dân quét.
# Trang đăng nhập VNeID lỗi không dựng mã QR (khung QR trống).
LOGIN_QR_MISSING = {
    "md": ("⚠️ Trang VNeID chưa hiện **mã QR** ạ.\n\n"
           "Công dân bấm **Tải lại trang** bên dưới để hiện mã QR, hoặc đăng nhập bằng số định danh và mật khẩu."),
    "tts": ("Trang VNeID chưa hiện mã QR ạ. Công dân bấm tải lại trang bên dưới để hiện mã QR "
            "hoặc đăng nhập bằng số định danh và mật khẩu."),
}
# Extension cũ chưa có nút tải lại trang.
LOGIN_QR_MISSING_F5 = {
    "md": ("⚠️ Trang VNeID chưa hiện **mã QR** ạ.\n\n"
           "Công dân bấm phím **F5** để tải lại trang, hoặc đăng nhập bằng số định danh và mật khẩu."),
    "tts": ("Trang VNeID chưa hiện mã QR ạ. Công dân bấm phím F5 để tải lại trang "
            "hoặc đăng nhập bằng số định danh và mật khẩu."),
}
QR_LOGIN_GUIDE = {
    "md": (
        "✓ Đã chọn **{ward}, {province}**.\n\n"
        "Công dân mở app **VNeID** → **Quét QR** → quét mã trên màn hình ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã chọn cơ quan {ward}, {province} và mở bước đăng nhập ạ. "
    # "Công dân mở app VNeID chọn Quét QR rồi quét mã trên màn hình để đăng nhập. Xong em hướng dẫn tiếp ạ."
    # ),
    "tts": (
        "Em đã chọn cơ quan. "
        "Công dân mở ứng dụng vi en ai đi, chọn Quét quy rờ, rồi quét mã trên màn hình ạ."
    ),
}

# Các modal xác thực nối tiếp dùng chung URL SSO. Extension chỉ nhận diện trạng thái trang;
# toàn bộ lời hướng dẫn vẫn do backend quản lý.
VNEID_LOGIN_CODE_GUIDE = {
    "md": "Công dân nhập **mã xác nhận** → bấm **Xác nhận** ạ.",
    "tts": "Công dân nhập mã xác nhận, rồi bấm Xác nhận ạ.",
}

VNEID_DATA_SHARING_GUIDE = {
    "md": (
        "Công dân tích ô **“Tôi đã đọc và hiểu rõ…”** → bấm **Xác nhận chia sẻ** → nhập "
        "**passcode VNeID** (6 số) ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Công dân tích vào ô Tôi đã đọc và hiểu rõ nội dung mục đích, quyền và nghĩa vụ "
    # "của chủ thể dữ liệu, và đồng ý với các nội dung này. Sau đó bấm Xác nhận chia sẻ "
    # "rồi nhập passcode 6 số của ứng dụng VNeID để tiếp tục ạ."
    # ),
    "tts": (
        "Công dân tích ô Tôi đã đọc và hiểu rõ, bấm Xác nhận chia sẻ, "
        "rồi nhập mật mã sáu số của vi en ai đi ạ."
    ),
}

VNEID_PASSCODE_GUIDE = {
    "md": "Công dân nhập **passcode VNeID** (6 số) → bấm **Xác nhận** ạ.",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Công dân vui lòng nhập passcode VNeID gồm 6 chữ số vào màn hình, "
    # "sau đó bấm Xác nhận để tiếp tục ạ."
    # ),
    "tts": "Công dân nhập mật mã sáu số, rồi bấm Xác nhận ạ.",
}

# Người dân gõ/nói giữa lúc chờ — nhắc NGẮN theo đúng việc đang chờ, kèm nút phao.
WAIT_LOGIN_REMIND = {
    "md": (
        "Em đang chờ công dân **đăng nhập VNeID** ạ. "
        "Đã vào trang kê khai mà em chưa nhận ra → bấm nút dưới."
    ),
    "tts": "Dạ, em đang chờ công dân đăng nhập. Đã vào trang kê khai thì bấm nút bên dưới ạ.",
}

# Nút phao chỉ yêu cầu extension kiểm tra lại DOM, không phải lời xác nhận đã đăng nhập.
# Hai câu này được dùng khi chính lần kiểm tra tay cho thấy trang vẫn chưa sẵn sàng.
LOGIN_STILL_REQUIRED = {
    "md": "Trang vẫn ở bước **đăng nhập VNeID**. Công dân đăng nhập xong, em tự làm tiếp ạ.",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Trang hiện tại vẫn đang ở bước đăng nhập VNeID. Công dân hoàn tất đăng nhập "
    # "giúp em. Khi vào trang làm hồ sơ em sẽ tự nhận ra ạ."
    # ),
    "tts": "Dạ, trang vẫn ở bước đăng nhập. Công dân đăng nhập xong, em tự làm tiếp ạ.",
}

PORTAL_NOT_READY = {
    "md": "Trang **chưa vào phần làm hồ sơ**. Công dân làm tiếp trên cổng, tới nơi em tự nhận ra ạ.",
    "tts": "Dạ, trang chưa vào phần làm hồ sơ. Công dân làm tiếp trên trang ạ.",
}

WAIT_PORTAL_REMIND = {
    "md": "Em đang chờ trang sang **bước kê khai** ạ. Đã thấy tờ khai mà em chưa nhận ra → bấm nút dưới.",
    "tts": "Dạ, em đang chờ trang kê khai. Đã thấy tờ khai thì công dân bấm nút bên dưới ạ.",
}

WAIT_ATTACH_PORTAL_REMIND = {
    "md": (
        "Em đang chờ trang sang **Thành phần hồ sơ** ạ. "
        "Đã thấy bảng đính kèm mà em chưa nhận ra → bấm nút dưới."
    ),
    "tts": "Dạ, em đang chờ trang thành phần hồ sơ. Đã thấy bảng đính kèm thì công dân bấm nút bên dưới ạ.",
}

AGENCY_SELECT_FAILED = {
    "md": (
        "⚠️ Em chưa tự chọn được cơ quan (*{error}*).\n\n"
        "Công dân chọn **{ward}, {province}** → bấm **Đồng ý** ạ."
    ),
    "tts": "Dạ, em chưa tự chọn được. Công dân chọn {ward}, {province}, rồi bấm Đồng ý ạ.",
}

# Thủ tục mà trang kết quả DVCQG ra NHIỀU thẻ (Sở lẫn UBND xã cùng tiếp nhận) và thẻ đầu KHÔNG
# phải thẻ đúng. Bản trợ lý chưa biết chọn thẻ theo chữ → dặn công dân làm tay cả bước, không để
# nó bấm thẻ đầu.
AGENCY_CARD_MANUAL_GUIDE = {
    "md": (
        "Công dân chọn **{ward}, {province}** → **Đồng ý** → bấm **Nộp trực tuyến** ở thẻ có dòng "
        "**{card}** ạ.\n\n"
        "⚠️ Không bấm thẻ đầu tiên (thẻ của Sở)."
    ),
    "tts": (
        "Dạ, công dân chọn {ward}, {province}, bấm Đồng ý. "
        "Rồi bấm Nộp trực tuyến ở thẻ có dòng {card}, không bấm thẻ đầu tiên ạ."
    ),
}

# Đã chọn xong tỉnh/xã + Đồng ý nhưng không thấy thẻ đúng cơ quan để bấm "Nộp trực tuyến".
AGENCY_CARD_MISSING = {
    "md": (
        "⚠️ Em chưa thấy thẻ có dòng **{card}** ạ.\n\n"
        "Công dân tìm thẻ đó → bấm **Nộp trực tuyến**. Không bấm thẻ đầu tiên (thẻ của Sở)."
    ),
    "tts": (
        "Dạ, em chưa thấy thẻ có dòng {card}. "
        "Công dân tìm thẻ đó, bấm Nộp trực tuyến, không bấm thẻ đầu tiên ạ."
    ),
}

# Cổng DVC Bộ Công an (registry `bcaPortal`). Câu mở trang chỉ báo đang chuyển; hướng dẫn chọn cơ
# quan nói khi trang đã hiện khối "Cơ quan thực hiện".
BCA_PORTAL_OPEN = {
    "md": "Dạ, em đang mở trang **{procedure}** trên Cổng dịch vụ công Bộ Công an ạ.",
    "tts": "Dạ, em đang mở trang {procedure} ạ.",
}

# Hỏi nơi đăng ký tạm trú để chọn hộ khối "Cơ quan thực hiện" (đi kèm thẻ chọn Tỉnh → Xã, chọn xong mới có nút điền).
BCA_AGENCY_ASK = {
    "md": (
        "Dạ, công dân đăng ký tạm trú ở **tỉnh/thành phố** và **xã/phường** nào ạ?\n\n"
        "Công dân chọn **Tỉnh/Thành phố** rồi **Phường/Xã** ở thẻ bên dưới, xong bấm **Điền cơ quan thực hiện** "
        "để em chọn giúp trên trang. Chọn xong trang mới hiện các mục tiếp theo."
    ),
    "tts": (
        "Dạ, công dân chọn tỉnh, thành phố rồi xã, phường nơi đăng ký tạm trú ở bên dưới, "
        "xong bấm Điền cơ quan thực hiện giúp em ạ."
    ),
}

BCA_AGENCY_ASK_PREFILLED = {
    "md": (
        "Dạ, công dân đăng ký tạm trú ở **{ward}, {province}** phải không ạ?\n\n"
        "Nếu đúng, công dân bấm **Điền cơ quan thực hiện** là em chọn giúp trên trang. "
        "Nếu ở nơi khác, công dân chọn lại ở thẻ bên dưới nhé."
    ),
    "tts": (
        "Dạ, công dân đăng ký tạm trú ở {ward}, {province} phải không ạ? Nếu đúng, công dân bấm "
        "Điền cơ quan thực hiện là em chọn giúp trên trang."
    ),
}

BCA_AGENCY_READY = {
    "md": "Đã chọn **{ward}, {province}**. Bấm **Điền cơ quan thực hiện** để em chọn trên trang ạ.",
    "tts": "Dạ, công dân bấm Điền cơ quan thực hiện để em chọn trên trang ạ.",
}

BCA_AGENCY_REMIND = {
    "md": "Dạ, công dân chọn **Tỉnh/Thành phố** và **Phường/Xã** ở thẻ **Nơi làm thủ tục** phía trên, "
          "rồi bấm **Điền cơ quan thực hiện** giúp em ạ.",
    "tts": "Dạ, công dân chọn tỉnh và phường xã ở thẻ phía trên, rồi bấm Điền cơ quan thực hiện giúp em ạ.",
}

BCA_AGENCY_NEED_WARD = {
    "md": "Dạ, công dân chọn tiếp **xã/phường** thuộc **{province}** ạ.",
    "tts": "Dạ, công dân chọn tiếp xã, phường thuộc {province} ạ.",
}

BCA_AGENCY_FILLING = {
    "md": "Em đang chọn **{ward}, {province}** ở mục Cơ quan thực hiện ạ.",
    "tts": "Dạ, em đang chọn {ward}, {province} ạ.",
}

BCA_AGENCY_FILLED = {
    "md": "✓ Đã chọn Cơ quan thực hiện: **{ward}, {province}**.",
    "tts": "Dạ, em đã chọn xong cơ quan thực hiện ạ.",
}

BCA_AGENCY_FILL_FAILED = {
    "md": (
        "⚠️ Em chưa chọn được **{missing}** trên trang cho **{place}** ạ.\n\n"
        "Công dân chọn lại ở thẻ bên dưới, hoặc tự chọn ở mục **Cơ quan thực hiện** trên trang."
    ),
    "tts": "Dạ, em chưa chọn được trên trang. Công dân chọn lại bên dưới, hoặc tự chọn trên trang giúp em ạ.",
}

BCA_QR_LOGIN_GUIDE = {
    "md": "Công dân mở app **VNeID** → **Quét QR** → quét mã trên màn hình để đăng nhập ạ.",
    "tts": "Dạ, công dân mở ứng dụng vi en ai đi, chọn Quét quy rờ, rồi quét mã trên màn hình ạ.",
}

GUIDE_LOGIN_NO_URL = {
    "md": (
        "Dạ, em chưa có đường dẫn **{procedure}**. "
        "Công dân mở trang thủ tục trên Cổng dịch vụ công, em hỗ trợ tiếp ạ."
    ),
    "tts": "Dạ, công dân mở trang thủ tục trên Cổng dịch vụ công giúp em ạ.",
}

# Intro chỉ nêu bước trên cổng đã tới; không lặp lại trạng thái đăng nhập.
ASK_DOC_METHOD = {
    "md": (
        "{intro_md} Để làm **{procedure}**, công dân cần:\n\n"
        "{doc_list}\n\n"
        "**Công dân gửi giấy tờ bằng cách nào ạ?**"
    ),
    # Chữ liệt kê đủ giấy tờ; lời đọc chỉ trỏ xuống danh sách — đọc từng tên giấy mất gần 20 giây.
    "tts": "{intro_tts} Giấy tờ cần chuẩn bị có ở bên dưới. Công dân muốn chụp bằng điện thoại, hay quét tại quầy ạ?",
}

# Chưa nhận ra công dân chọn cách nào: hỏi lại NGẮN (danh sách giấy tờ đã ở lượt trước), thẻ 2 cách hiện lại bên dưới.
ASK_DOC_METHOD_AGAIN = {
    "md": "Dạ, công dân chọn giúp em: **📱 Chụp bằng điện thoại** hoặc **🖨️ Scan tại quầy** ạ.",
    "tts": "Dạ, công dân chọn chụp bằng điện thoại, hay quét tại quầy ạ?",
}

# Công dân chưa nghe rõ ("sao cơ", "gì cơ"…): đọc lại lời lượt trước; khung chat chỉ thêm dòng ngắn này.
REPEAT_LAST = {
    "md": "Dạ, em nhắc lại ạ.",
    "tts": "Dạ, em nhắc lại ạ. ",
}

INTRO_LOGIN_OK = {"md": "", "tts": ""}
INTRO_FORM_REACHED = {"md": "Đã vào trang kê khai ✓", "tts": "Đã vào trang kê khai."}
INTRO_OWNER_REACHED = {
    "md": "Đã vào bước Thông tin chủ hồ sơ ✓",
    "tts": "Đã vào bước thông tin chủ hồ sơ.",
}
# Quét sớm: công dân đang đứng ở trang có FORM, đưa giấy tờ ra mà không biết để làm gì thì
# tưởng đã sang bước đính kèm. Nói thẳng việc sắp làm.
INTRO_OWNER_SCAN_REACHED = {
    "md": "✓ Đã vào **Thông tin chủ hồ sơ**. Em điền phần này trước ạ.",
    "tts": "Đã vào bước chủ hồ sơ. Em điền phần này trước ạ.",
}
# Nhánh ỦY QUYỀN: trang đổi nhãn khối thành "Thông tin người nộp hồ sơ" và mọc thêm khối
# "Thông tin ủy quyền cá nhân" → nói thẳng là sẽ điền HAI khối, và vì sao.
INTRO_AUTHORIZATION_SCAN_REACHED = {
    "md": (
        "✓ Đã vào **Người nộp hồ sơ và ủy quyền**. Vì là **ủy quyền**, em điền 2 phần: "
        "**Người nộp hồ sơ** và **Thông tin ủy quyền cá nhân** ạ."
    ),
    "tts": "Đã vào bước ủy quyền. Em sẽ điền hai phần: người nộp hồ sơ và thông tin ủy quyền ạ.",
}

INTRO_ATTACH_REACHED = {
    "md": "Đã vào bước Thành phần hồ sơ ✓",
    "tts": "Đã vào bước thành phần hồ sơ.",
}

# Wizard hồ sơ cổng React (kết hôn): modal "Thông tin chung" → bước Thông tin chủ hồ sơ
# → bước Kê khai. Modal đã điền sẵn đúng cơ quan → bot bấm Xác nhận hộ LẶNG LẼ (không báo câu —
# đã bỏ CONFIRM_INFO_MODAL khỏi luồng theo yêu cầu; hành động confirm_info_modal vẫn chạy ở flow).

OWNER_INFO_GUIDE = {
    "md": "Công dân điền **Thông tin chủ hồ sơ** (SĐT, email, địa chỉ) → bấm nút tiếp tục trên trang ạ.",
    "tts": "Công dân điền số điện thoại, thư điện tử, địa chỉ, rồi bấm nút tiếp tục trên trang ạ.",
}

OWNER_INFO_ATTACH_GUIDE = {
    "md": "Công dân điền **Thông tin chủ hồ sơ** (SĐT, email, địa chỉ) → bấm nút tiếp tục trên trang ạ.",
    "tts": "Công dân điền số điện thoại, thư điện tử, địa chỉ, rồi bấm nút tiếp tục trên trang ạ.",
}

DOCS_COMPLETE_OWNER = {
    "md": "✓ Đã nhận **{files_count} tệp**. Em đang tìm thông tin chủ hồ sơ…",
    "tts": "Dạ, em đã nhận giấy tờ. Công dân chờ em chút ạ.",
}
OWNER_PROCESSING = {
    "md": "Em đang đối chiếu chủ hồ sơ, sắp xong ạ…",
    "tts": "Dạ, em đang đối chiếu, sắp xong rồi ạ.",
}
OWNER_FIELDS_READY = {
    "md": "✓ Đã xác định chủ hồ sơ, tìm thấy **{count} thông tin**. Em điền ngay ạ.",
    "tts": "Dạ, em điền thông tin chủ hồ sơ ngay ạ.",
}
OWNER_FIELDS_UNMATCHED = {
    "md": "Giấy tờ **chưa có thông tin chủ hồ sơ** ạ. Công dân điền các ô còn thiếu giúp em.",
    "tts": "Dạ, giấy tờ chưa có thông tin chủ hồ sơ. Công dân điền giúp em ạ.",
}
OWNER_FIELDS_EMPTY = {
    "md": (
        "Em chưa chắc ai là chủ hồ sơ nên **không tự điền** ạ. "
        "Công dân điền ô còn thiếu → bấm **Bước tiếp theo**."
    ),
    "tts": "Dạ, em chưa chắc chủ hồ sơ nên chưa điền. Công dân điền, rồi bấm Bước tiếp theo ạ.",
}
OWNER_PIPELINE_ERROR = {
    "md": "⚠️ Em chưa đọc được chủ hồ sơ ({error}). Công dân điền ô còn thiếu → bấm **Bước tiếp theo** ạ.",
    "tts": "Dạ, em chưa đọc được. Công dân điền, rồi bấm Bước tiếp theo ạ.",
}
OWNER_FILL_DONE = {
    "md": "✓ Đã điền **{completed}**.{missing_note}\n\nCông dân kiểm tra → bấm **Bước tiếp theo** ạ.",
    "tts": "Dạ, em đã điền {completed}.{missing_tts} Công dân kiểm tra, rồi bấm Bước tiếp theo ạ.",
}
OWNER_FILL_NOT_APPLIED = {
    "md": (
        "⚠️ Trang chưa nhận lệnh điền ({error}). "
        "Công dân giữ nguyên trang → bấm **Điền lại thông tin chủ hồ sơ** ạ."
    ),
    "tts": "Dạ, trang chưa nhận. Công dân bấm Điền lại thông tin chủ hồ sơ ạ.",
}
MAIN_FORM_PROCESSING = {
    "md": "Giờ em **điền tờ khai** giúp công dân ạ.",
    "tts": "Giờ em điền tờ khai ạ.",
}
WAIT_ATTACHMENT_PAGE = {
    "md": "\n\nKiểm tra xong → chuyển sang **Thành phần hồ sơ**, em tự đính kèm ạ.",
    "tts": " Kiểm tra xong công dân sang bước thành phần hồ sơ rồi em sẽ tự đính kèm ạ.",
}
# Cổng 2 tab cùng trang (Bắc Ninh): công dân KHÔNG phải chuyển bước — bot tự mở tab
# "Tải thành phần hồ sơ" và đính kèm ngay sau khi điền xong đơn.
WAIT_ATTACHMENT_SAME_PAGE = {
    "md": "\n\nGiờ em sang **Tải thành phần hồ sơ** và tự đính kèm, công dân chờ chút ạ…",
    "tts": " Giờ em tự đính kèm giấy tờ, công dân chờ chút ạ.",
}
# Chốt kết quả CẢ HAI bước (điền đơn + đính kèm) sau khi luồng cùng-trang chạy liền mạch.
SAME_PAGE_TWO_STEP_SUMMARY = {
    "md": "\n\n📋 **Đơn đăng ký**: {filled} ô ✓ · **Thành phần hồ sơ**: {attached} tệp ✓",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # " Tóm tắt lại: phần nhập đơn đăng ký em đã điền {filled} ô, phần thành phần hồ sơ "
    # "em đã đính kèm {attached} tệp ạ."
    # ),
    "tts": " Em đã điền đơn và đính kèm xong ạ.",
}
REFILL_PROCESSING = {
    "md": "🔁 Em đang **điền lại tờ khai**. Công dân giữ nguyên trang, chờ chút ạ…",
    "tts": "Dạ, em đang điền lại. Công dân giữ nguyên trang ạ.",
}
REFILL_ALREADY_RUNNING = {
    "md": "Em đang điền lại rồi, công dân chờ chút ạ.",
    "tts": "Dạ, em đang điền lại, công dân chờ chút ạ.",
}
REFILL_WRONG_PAGE = {
    "md": "Mình chưa ở trang **Kê khai** ạ. Công dân quay lại trang Kê khai → bấm **Điền lại thông tin**.",
    "tts": "Dạ, công dân quay lại trang kê khai, rồi bấm Điền lại thông tin ạ.",
}
# Cổng đính kèm CÙNG TRANG kê khai (samePageAttach) mà điền xong không tự đính (askBeforeAttach).
REVIEW_ATTACHMENT_SAME_PAGE = {
    "md": "\n\nKiểm tra xong → bấm **Đính kèm giấy tờ**, em đính kèm ngay ở mục **Hồ sơ đính kèm** trên trang này ạ.",
    "tts": " Kiểm tra xong, công dân bấm Đính kèm giấy tờ, em đính kèm ngay trên trang này ạ.",
}

REVIEW_ATTACHMENT_ACTION = {
    "md": "\n\nKiểm tra xong → sang **Thành phần hồ sơ** → bấm **Đính kèm giấy tờ** trong Trợ lý ạ.",
    "tts": " Kiểm tra xong, công dân sang bước thành phần hồ sơ, rồi bấm Đính kèm giấy tờ ạ.",
}

# Tờ khai điện tử mở bằng nút "Khai tờ khai" trong bảng Thành phần hồ sơ (registry declarationEforms,
# vd khai sinh kết hợp nhận cha, mẹ, con): trợ lý chỉ điền được khi công dân đã tự mở tờ khai.
EFORM_DOCS_READY = {
    "md": (
        "✓ Đã nhận **{files_count} tệp**.\n\n"
        "Thủ tục này điền tờ khai ngay ở bước **Thành phần hồ sơ**: công dân nhấn nút **Khai tờ khai** "
        "ở dòng {row} (*{label}*), đợi tờ khai mở ra rồi bấm **✍️ Điền tờ khai** để em điền ạ."
    ),
    "tts": (
        "Dạ, em đã nhận giấy tờ. Công dân nhấn nút Khai tờ khai ở dòng {row} trên cổng, "
        "tờ khai mở ra thì bấm Điền tờ khai để em điền ạ."
    ),
}
EFORM_OPEN_GUIDE = {
    "md": (
        "Thủ tục này điền tờ khai ở bước **Thành phần hồ sơ**: công dân sang bước đó, nhấn nút "
        "**Khai tờ khai** ở dòng {row} (*{label}*), đợi tờ khai mở ra rồi bấm **✍️ Điền tờ khai** ạ."
    ),
    "tts": (
        "Công dân sang bước thành phần hồ sơ, nhấn nút Khai tờ khai ở dòng {row}, "
        "tờ khai mở ra thì bấm Điền tờ khai ạ."
    ),
}
EFORM_NOT_OPEN = {
    "md": (
        "Em chưa thấy tờ khai nào đang mở. Công dân nhấn nút **Khai tờ khai** ở dòng {row} "
        "(*{label}*) trên cổng, đợi tờ khai hiện ra rồi bấm lại **✍️ Điền tờ khai** ạ."
    ),
    "tts": (
        "Em chưa thấy tờ khai đang mở. Công dân nhấn nút Khai tờ khai ở dòng {row}, "
        "tờ khai hiện ra rồi bấm lại Điền tờ khai ạ."
    ),
}
# Extension tự bấm "Khai tờ khai" (cờ supportsOpenEform): tờ khai mở ra thì điền luôn, công dân không phải bấm gì.
EFORM_OPENING = {
    "md": "Em đang mở **{label}** (dòng {row} của Thành phần hồ sơ) để điền, công dân chờ chút ạ…",
    "tts": "Dạ, em đang mở tờ khai để điền, công dân chờ chút ạ.",
}
EFORM_FILLING = {
    "md": "Em đang điền **{label}**. Công dân giữ nguyên tờ khai đang mở, chờ chút ạ…",
    "tts": "Dạ, em đang điền tờ khai. Công dân giữ nguyên tờ khai, chờ chút ạ.",
}
EFORM_NEXT = {
    "md": (
        "\n\nRà xong công dân lưu tờ khai này, rồi nhấn **Khai tờ khai** ở dòng {row} (*{label}*) "
        "và bấm **✍️ Điền tờ khai** ạ."
    ),
    "tts": " Rà xong công dân lưu tờ khai, rồi mở tờ khai ở dòng {row} và bấm Điền tờ khai ạ.",
}
EFORM_ALL_FILLED = {
    "md": (
        "\n\nĐã điền xong các tờ khai. Rà xong công dân lưu tờ khai, đóng lại rồi bấm "
        "**📎 Đính kèm giấy tờ** để em đính kèm ạ."
    ),
    "tts": " Đã điền xong các tờ khai. Công dân lưu tờ khai, đóng lại rồi bấm Đính kèm giấy tờ ạ.",
}

# ── Xin phép xử lý dữ liệu cá nhân (Luật 91/2025/QH15) — TRƯỚC khi nhận/đọc giấy tờ ──
# Intro nối mốc trang hiện tại như ASK_DOC_METHOD; không đọc lại trạng thái đăng nhập.
CONSENT_INTRO = {
    "md": (
        "{intro_md} Trước khi đọc giấy tờ, em cần **công dân cho phép xử lý dữ liệu cá nhân** ạ.\n\n"
        "- Đồng ý → tích đủ **2 ô** (nếu chưa tích sẵn) → bấm **Đồng ý và tự động điền**\n- Không đồng ý → bấm "
        "**Không đồng ý · Tự nhập** (em không đọc giấy tờ)"
    ),
    # Danh sách giấy tờ đã nằm trong thẻ xin phép → không đọc (dài, và lượt sau còn hiện lại). Bản extension
    # mới tích sẵn 2 ô nên lời đọc không bảo tích; chữ ở trên vẫn nhắc cho bản cũ.
    "tts": (
        "{intro_tts} Trước khi đọc giấy tờ, em cần công dân cho phép xử lý dữ liệu cá nhân. "
        "Em chỉ đọc các giấy tờ trên màn hình để điền tờ khai và đính kèm hồ sơ. "
        "Công dân đồng ý thì bấm Đồng ý và tự động điền ạ."
    ),
}

CONSENT_ATTACH_INTRO = {
    "md": (
        "{intro_md} Trước khi đính kèm giấy tờ, "
        "em cần **công dân cho phép xử lý dữ liệu cá nhân** ạ.\n\n"
        "Đồng ý → tích **2 ô** → bấm **Đồng ý và tự động đính kèm**."
    ),
    "tts": (
        "{intro_tts} Em cần công dân cho phép xử lý dữ liệu để đính kèm {doc_list_tts} ạ. "
        "Công dân tích hai ô, rồi bấm Đồng ý và tự động đính kèm."
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
    # Phiên bản nội dung chỉ lưu ở nhật ký đồng ý + PDF biên bản, không hiện cho công dân.
    "md": "✓ Đã ghi nhận đồng ý — mã **{log_id}**, {time}.",
    "tts": "Dạ, em đã ghi nhận.",
}

CONSENT_DECLINED = {
    "md": (
        "✓ Em sẽ **không đọc** giấy tờ nào. Công dân tự điền trên trang ạ.\n\n"
        "Cần em hỗ trợ → bấm **Xem lại và đồng ý**."
    ),
    "tts": "Dạ, em sẽ không đọc giấy tờ. Công dân tự điền trên trang ạ.",
}

CONSENT_RESHOW = {
    "md": "Dạ, công dân đọc lại và xác nhận giúp em ạ:",
    "tts": "Dạ, công dân đọc lại và xác nhận giúp em ạ.",
}

CONSENT_REMIND = {
    "md": (
        "Công dân xác nhận **thẻ xin phép** bên trên ạ:\n\n"
        "- Đồng ý → tích **2 ô** → **Đồng ý và tự động điền**\n- Không → **Không đồng ý · Tự nhập**"
    ),
    "tts": (
        "Dạ, công dân xác nhận thẻ xin phép bên trên ạ. "
        "Đồng ý thì tích hai ô, rồi bấm Đồng ý và tự động điền."
    ),
}

QR_WAITING = {
    "md": "✓ **Chụp bằng điện thoại**\n\nCông dân mở **camera điện thoại** → quét **mã QR** dưới đây ạ.",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": "Mời công dân mở camera điện thoại rồi quét mã QR trên màn hình để tải ảnh giấy tờ lên ạ.",
    "tts": "Dạ, công dân mở camera điện thoại, quét mã quy rờ trên màn hình ạ.",
}

MOBILE_CONNECTED = {
    "md": (
        "📱 ✓ Điện thoại đã kết nối.\n\n"
        "Công dân chụp lần lượt theo danh sách (**CCCD chụp 2 mặt**), hoặc chọn ảnh có sẵn ạ."
    ),
    "tts": "Dạ, điện thoại đã kết nối. Công dân chụp từng giấy tờ, căn cước chụp hai mặt ạ.",
}

MOBILE_CONNECTED_ATTACH = {
    "md": (
        "📱 ✓ Điện thoại đã kết nối.\n\n"
        "Công dân chụp/chọn tất cả **giấy tờ cần chứng thực bản sao** → bấm **Gửi tất cả** ạ."
    ),
    "tts": "Dạ, điện thoại đã kết nối. Công dân chụp hết giấy cần chứng thực, rồi bấm Gửi tất cả ạ.",
}

# Chỉ nói SỐ ĐÃ NHẬN, không "x/y" — tổng gồm slot tuỳ chọn dễ làm công dân tưởng còn thiếu.
DOCS_COMPLETE_NEXT_STEP = {
    "md": "✓ Đã nhận **{files_count} tệp**.\n\nEm đang đọc và điền tờ khai, khoảng **30 giây** ạ…",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã nhận {files_count} tệp giấy tờ. "
    # "Em đang tự đọc và chuẩn bị điền vào form bên trái, khoảng nửa phút, công dân chờ em chút nhé."
    # ),
    "tts": "Dạ, em đã nhận giấy tờ. Công dân chờ em khoảng nửa phút ạ.",
}

DOCS_COMPLETE_ATTACH = {
    "md": "✓ Đã nhận **{files_count} tệp**.\n\nEm đang đính tất cả vào **một hồ sơ**, công dân chờ chút ạ…",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã nhận {files_count} tệp giấy tờ. Em đang chuẩn bị đính tất cả tệp vào cùng một hồ sơ, "
    # "công dân chờ em chút ạ."
    # ),
    "tts": "Dạ, em đã nhận giấy tờ. Công dân chờ em chút ạ.",
}

DOCS_TARGET_UNKNOWN = {
    "md": (
        "Em chưa biết trang đang ở bước nào ạ. Giấy tờ vẫn được giữ.\n\n"
        "Công dân mở đúng trang cần làm → bấm lại nút dưới."
    ),
    "tts": "Dạ, em chưa biết trang đang ở bước nào. Công dân mở đúng trang, rồi bấm lại nút bên dưới ạ.",
}

BUSINESS_PREPARING = {
    "md": "Em đang mở trang **Thành lập mới hộ kinh doanh**. Công dân chờ chút, **chưa cần bấm gì** ạ.",
    "tts": "Em đang mở trang kê khai. Công dân chờ chút, chưa cần bấm gì ạ.",
}

# Luồng THAY ĐỔI nội dung ĐK hộ kinh doanh — bootstrap pha 1 chỉ tới màn tra cứu hộ KD.
BUSINESS_PREPARING_CHANGE = {
    "md": "Em đang mở trang **Đăng ký thay đổi hộ kinh doanh**. Công dân chờ chút, **chưa cần bấm gì** ạ.",
    "tts": "Em đang mở trang kê khai. Công dân chờ chút, chưa cần bấm gì ạ.",
}

BUSINESS_DOCS_COMPLETE_CHANGE = {
    "md": (
        "✓ Đã nhận **{files_count} tệp**.\n\n"
        "Em đang lấy **mã số hộ kinh doanh** và nội dung thay đổi, công dân chờ chút ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã nhận {files_count} tệp giấy tờ. Em đang đọc hồ sơ để lấy mã số hộ kinh doanh "
    # "và so sánh nội dung thay đổi. Công dân chờ em chút ạ."
    # ),
    "tts": "Dạ, em đã nhận giấy tờ. Công dân chờ em chút ạ.",
}

BUSINESS_READY_CHANGE = {
    "md": (
        "✓ Đã đọc xong giấy tờ. Em đang tra cứu, điền phần **cần thay đổi** và đính kèm.\n\n"
        "Công dân **chưa bấm gì** trên trang giúp em ạ."
    ),
    "tts": "Dạ, em đang tự điền. Công dân chờ, chưa bấm gì trên trang ạ.",
}

BUSINESS_DOCS_COMPLETE = {
    "md": "✓ Đã nhận **{files_count} tệp**.\n\nEm đang đọc và chuẩn bị điền, công dân chờ chút ạ…",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã nhận {files_count} tệp giấy tờ. Em đang chuẩn bị dữ liệu cho tám khối thông tin "
    # "và phân loại giấy tờ đính kèm. Công dân chờ em chút ạ."
    # ),
    "tts": "Dạ, em đã nhận giấy tờ. Công dân chờ em chút ạ.",
}

BUSINESS_READY = {
    "md": (
        "✓ Đã đọc xong giấy tờ. Em đang điền **8 khối dữ liệu** và đính kèm.\n\n"
        "Công dân **chưa bấm gì** trên trang giúp em ạ."
    ),
    "tts": "Dạ, em đang tự điền. Công dân chờ, chưa bấm gì trên trang ạ.",
}

BUSINESS_DONE = {
    "md": (
        "✓ Đã điền **{filled_pages}/{total_pages} khối** · đính **{attached} tệp**.\n\n"
        "Công dân rà lại → tự bấm **Nộp hồ sơ** ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã điền đủ {filled_pages} trên {total_pages} khối dữ liệu và đính kèm {attached} tệp. "
    # "Công dân rà soát các thông tin đã điền ở từng khối và các tệp đã đính kèm giúp em nhé ạ. "
    # "Sau khi kiểm tra xong, công dân tự bấm nộp hồ sơ trên trang giúp em."
    # ),
    "tts": "Dạ, em đã điền và đính kèm xong. Công dân xem lại, rồi tự bấm Nộp hồ sơ ạ.",
}

BUSINESS_STOPPED = {
    "md": (
        "⏹️ Đã dừng theo yêu cầu.\n\n"
        "**Tiến độ:** {fill_status}\n\n"
        "**Đính kèm:** {attachment_status}\n\n"
        "Thông tin đã lưu trên cổng vẫn được giữ."
    ),
    "tts": "Dạ, em đã dừng. {fill_status_tts}. {attachment_status_tts}. Thông tin đã lưu vẫn còn ạ.",
}

BUSINESS_FAILED_PROGRESS = {
    "md": (
        "⚠️ Tự điền đang dừng (*{error}*).\n\n"
        "**Tiến độ:** {fill_status}\n\n"
        "**Đính kèm:** {attachment_status}\n\n"
        "Thông tin đã lưu vẫn được giữ. Công dân bấm **Thử lại** ạ."
    ),
    "tts": "Dạ, việc tự điền đang dừng. {fill_status_tts}. {attachment_status_tts}. Công dân bấm Thử lại ạ.",
}

BUSINESS_FAILED = {
    "md": "⚠️ Tự điền đang dừng (*{error}*). Dữ liệu vẫn được giữ.\n\nCông dân bấm **Thử lại** ạ.",
    "tts": "Dạ, việc tự điền đang dừng. Công dân bấm Thử lại ạ.",
}

DOCS_FORCED_MISSING = {
    "md": "Dạ, em làm tiếp với **{files_count} tệp** hiện có. Thiếu gì em sẽ hỏi lại ạ…",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Dạ công dân chốt gửi với {files_count} tệp. Em vẫn đọc và điền phần có được, "
    # "thiếu thông tin nào em sẽ hỏi lại ạ. Đang xử lý công dân chờ chút nhé."
    # ),
    "tts": "Dạ, em làm tiếp với giấy tờ hiện có. Thiếu gì em sẽ hỏi lại ạ.",
}

FILL_READY = {
    "md": (
        "✓ Đã đọc **{count} thông tin**, đang điền vào tờ khai bên trái.\n\n"
        "Công dân kiểm tra lại: ô **vàng** = em điền mặc định, ô **đỏ** = còn thiếu ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã đọc được {count} trường thông tin và đang điền vào form bên trái. "
    # "Công dân nhìn sang form kiểm tra lại giúp em nhé. Ô viền vàng là em đặt mặc định, "
    # "ô viền đỏ là còn thiếu ạ."
    # ),
    "tts": "Dạ xong rồi ạ. Công dân kiểm tra thông tin tờ khai. Ô vàng là điền sẵn và ô đỏ là còn thiếu.",
}

FILL_REPORT_REVIEW = {
    "md": "Em điền được **{filled} ô** ✓{missing_note}\n\nCông dân rà lại, ô nào sai thì sửa trực tiếp ạ.",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em điền xong {filled} ô rồi ạ. Công dân rà lại trên form và sửa trực tiếp "
    # "ô nào chưa đúng giúp em ạ."
    # ),
    "tts": "Dạ em điền xong rồi. Ô nào sai công dân sửa trực tiếp ạ.",
}

PIPELINE_ERROR = {
    "md": "⚠️ Em chưa đọc được giấy tờ (*{error}*).\n\nCông dân bấm **Thử lại**, hoặc chụp lại rõ hơn ạ.",
    "tts": "Dạ, em chưa đọc được. Công dân bấm Thử lại, hoặc chụp lại rõ hơn ạ.",
}

ATTACH_PIPELINE_ERROR = {
    "md": "⚠️ Lỗi khi chuẩn bị đính kèm (*{error}*). Tệp vẫn được giữ.\n\nCông dân bấm **Thử lại** ạ.",
    "tts": "Dạ, em gặp lỗi. Công dân bấm Thử lại ạ.",
}

ATTACH_PLANNING = {
    "md": "Em đang xếp giấy tờ để đính kèm, chờ chút ạ…",
    "tts": "Dạ, công dân chờ em chút ạ.",
}

ATTACH_RUNNING = {
    "md": "Em đang đính kèm, công dân chờ chút ạ…",
    "tts": "Dạ, em đang đính kèm, công dân chờ chút ạ.",
}

ATTACH_REQUEST_ON_DECLARATION = {
    "md": (
        "Mình đang ở trang **Kê khai**. "
        "Công dân xem lại → chuyển sang **Thành phần hồ sơ**, em tự đính kèm ạ."
    ),
    "tts": "Mình đang ở trang kê khai. Công dân xem lại, rồi sang bước thành phần hồ sơ ạ.",
}

ATTACH_REQUEST_UNKNOWN = {
    "md": "Em chưa rõ ý ạ. Công dân nói ngắn gọn, ví dụ **“đính kèm giấy tờ”**.",
    "tts": "Dạ, em chưa rõ. Công dân nói ngắn gọn, ví dụ: đính kèm giấy tờ ạ.",
}

# Máy quầy đã chọn "mỗi tài liệu một hồ sơ riêng" trong Cài đặt → không hỏi giữa luồng,
# nhưng phải BÁO vì tách hồ sơ mở nhiều tab (câu này nối vào sau DOCS_COMPLETE_ATTACH).
ATTACH_MODE_PRESET_SPLIT = {
    "md": "\n\nTheo cài đặt quầy: **mỗi tài liệu một hồ sơ riêng** ạ.",
    "tts": " Theo cài đặt quầy, mỗi tài liệu một hồ sơ riêng ạ.",
}

ATTACH_MODE_ASK = {
    "md": (
        "✓ Đã nhận **{files_count} tệp**. "
        "Công dân muốn **gộp một hồ sơ** hay **mỗi tài liệu một hồ sơ** ạ?"
    ),
    "tts": "Dạ, công dân muốn gộp một hồ sơ, hay mỗi tài liệu một hồ sơ ạ?",
}

ATTACH_MODE_SELECTED = {
    "md": "✓ **{mode}**. Em đang chuẩn bị, công dân chờ chút ạ…",
    "tts": "Dạ, đã chọn {mode}. Công dân chờ em chút ạ.",
}

ATTACH_PLAN_READY = {
    "md": "📎 Đã xếp xong **{count} mục**:\n\n{plan_list}\n\nEm đang đính từng tệp, chờ chút ạ…",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": "Kế hoạch đính kèm xong rồi, {count} mục. Em đang tự đính từng tệp vào hồ sơ, công dân chờ chút ạ.",
    "tts": "Dạ, em đang đính từng tệp, công dân chờ chút ạ.",
}

ATTACH_PLAN_READY_SPLIT = {
    "md": (
        "📎 Đã xếp xong **{count} tài liệu**:\n\n"
        "{plan_list}\n\n"
        "Mỗi tài liệu **một hồ sơ riêng**, em làm lần lượt từng tab ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Kế hoạch đính kèm xong rồi, {count} tài liệu. "
    # "Em sẽ đưa mỗi tài liệu vào một hồ sơ riêng và xử lý lần lượt từng tab ạ."
    # ),
    "tts": "Dạ, mỗi tài liệu một hồ sơ riêng. Em làm lần lượt ạ.",
}

ATTACH_PLAN_READY_SIGNATURE_SPLIT = {
    "md": (
        "📎 Đã xếp xong **{count} hồ sơ**:\n\n"
        "{plan_list}\n\n"
        "Mỗi hồ sơ: **giấy cần chứng thực chữ ký** ở STT 1; "
        "hồ sơ đầu có thêm **giấy tùy thân** ở STT 2. Em làm lần lượt từng tab ạ…"
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Kế hoạch đính kèm xong rồi, {count} hồ sơ. Mỗi hồ sơ có một giấy tờ cần chứng thực "
    # "chữ ký ở mục một; hồ sơ đầu tiên có thêm giấy tờ tùy thân ở mục hai. "
    # "Em sẽ xử lý lần lượt từng tab ạ."
    # ),
    "tts": "Dạ, em đã xếp xong. Em làm lần lượt từng hồ sơ ạ.",
}

# Đòi đính kèm khi trang còn ở bước kê khai (wizard chưa sang "Thành phần hồ sơ") —
# chạy engine lúc này sẽ ra "0 tệp" vô nghĩa → dặn chuyển bước, sang đến nơi tự đính.
ATTACH_WRONG_PAGE = {
    "md": (
        "Đang ở bước **Kê khai** ạ. "
        "Công dân bấm tiếp tục trên trang để sang **Thành phần hồ sơ**, em tự đính kèm ngay."
    ),
    "tts": "Dạ, công dân bấm tiếp tục để sang bước thành phần hồ sơ ạ.",
}

ATTACH_PAGE_REACHED = {
    "md": "✓ Đã sang **Thành phần hồ sơ**. Em đính kèm ngay ạ…",
    "tts": "Dạ, em đính kèm ngay ạ.",
}

ATTACH_NONE = {
    "md": (
        "⚠️ Chưa đính được tệp nào{error_note}.\n\n"
        "Công dân kiểm tra trang đang ở **Thành phần hồ sơ** → bấm **Đính kèm lại** ạ."
    ),
    "tts": "Dạ, em chưa đính được. Công dân kiểm tra trang, rồi bấm Đính kèm lại ạ.",
}

# Kế hoạch có tệp KHÔNG xếp được vào hồ sơ nào (vd giấy tùy thân không khớp người ký của văn bản
# nào). Nói NGAY ở bước báo kế hoạch để cán bộ biết trước tệp nào sẽ không được đính.
ATTACH_PLAN_SKIPPED_NOTE = {
    "md": "\n\n⚠️ {skipped_note}",
    "tts": " Có giấy tờ em chưa xếp được, sẽ bỏ qua ạ.",
}

# Thử lại mà vẫn 0 tệp: KHÔNG mời bấm lại nữa (kế hoạch cũ được phát lại y nguyên nên kết quả y
# nguyên). Chỉ đường thoát thật: sửa giấy tờ rồi lập kế hoạch mới.
ATTACH_NONE_REPEAT = {
    "md": (
        "⚠️ Vẫn chưa đính được tệp nào{error_note}.\n\n"
        "Bấm lại cũng không đổi kết quả. "
        "Công dân bấm **🗂️ Điều chỉnh giấy tờ** để bỏ hoặc chụp lại giấy chưa đúng ạ."
    ),
    "tts": "Dạ, vẫn chưa đính được. Công dân bấm Điều chỉnh giấy tờ, chụp lại giấy chưa đúng ạ.",
}

ATTACH_DONE = {
    "md": "✓ Đã đính **{attached} tệp**.\n\nCông dân rà lại lần cuối → tự bấm **Nộp hồ sơ / Gửi hồ sơ** ạ.",
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Em đã đính xong {attached} tệp vào hồ sơ rồi ạ. "
    # "Công dân rà lại lần cuối rồi bấm nộp hồ sơ giúp em nhé."
    # ),
    "tts": "Dạ, em đính kèm xong. Công dân xem lại, rồi tự bấm Nộp hồ sơ ạ.",
}

# Cổng bắt tích ô cam kết trước khi nộp (registry submitCommitLabel = nhãn ô trên trang, vd Cổng DVC Bộ Công an).
ATTACH_DONE_COMMIT = {
    "md": (
        "✓ Đã đính **{attached} tệp**.\n\nCông dân rà lại lần cuối, rồi bấm ô **\"{commit}\"**, "
        "rồi bấm **Nộp hồ sơ** ạ."
    ),
    "tts": "Dạ, em đính kèm xong. Công dân rà lại lần cuối, rồi bấm ô {commit}, rồi bấm Nộp hồ sơ ạ.",
}

COMMIT_TICKED = {
    "md": "✓ Đã tích ô **\"{commit}\"**. Công dân bấm **Nộp hồ sơ** ạ.",
    "tts": "Dạ, em tích xong rồi. Công dân bấm Nộp hồ sơ ạ.",
}

COMMIT_TICK_FAILED = {
    "md": "Em chưa tích được ô **\"{commit}\"**. Công dân tích giúp em ô này ở cuối trang, rồi bấm **Nộp hồ sơ** ạ.",
    "tts": "Dạ, em chưa tích được. Công dân tích giúp em ô cam kết ở cuối trang, rồi bấm Nộp hồ sơ ạ.",
}

ATTACH_DONE_WITH_ERRORS = {
    "md": (
        "⚠️ Đính được **{attached} tệp**, còn lỗi:\n\n"
        "{error_list}\n\n"
        "Công dân đính tay (*Chọn tệp đính kèm*) → bấm **Nộp hồ sơ** ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": "Em đính được {attached} tệp, còn vài mục lỗi. Công dân đính tay phần còn thiếu rồi nộp hồ sơ giúp em ạ.",
    "tts": "Dạ, còn vài tệp lỗi. Công dân đính tay, rồi bấm Nộp hồ sơ ạ.",
}

ATTACH_SUPPLEMENT_ASK = {
    "md": (
        "Em đã mở lại danh sách giấy tờ. "
        "Bấm từng loại để **xem/xoá**, hoặc thêm bằng **Chụp bằng điện thoại** / **Scan tại quầy**.\n\n"
        "Xong → bấm **{finish_action}**; {finish_detail} ạ."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Dạ, em đã mở lại toàn bộ danh sách giấy tờ. Công dân có thể xem, xóa hoặc thêm "
    # "tệp nếu cần, rồi bấm {finish_action} ạ."
    # ),
    "tts": "Dạ, công dân xem, xoá hoặc thêm tệp. Xong thì bấm nút xác nhận bên dưới ạ.",
}

ATTACH_SUPPLEMENT_SESSION_EXPIRED = {
    "md": "⚠️ Danh sách giấy tờ cũ đã hết hạn. Công dân chọn cách gửi để gửi lại ạ.",
    "tts": "Dạ, danh sách cũ đã hết hạn. Công dân gửi lại giấy tờ ạ.",
}

DOCUMENT_ADJUSTMENT_WRONG_PAGE = {
    "md": (
        "Mình chưa ở trang **Kê khai** ạ. Giấy tờ vẫn được giữ.\n\n"
        "Công dân quay lại trang Kê khai → bấm **Hoàn tất điều chỉnh, điền lại tờ khai**."
    ),
    "tts": "Dạ, công dân quay lại trang kê khai, rồi bấm Hoàn tất điều chỉnh ạ.",
}

ATTACH_SUPPLEMENT_AFTER_SUBMIT = {
    "md": "Hồ sơ đã **nộp thành công**, không sửa giấy tờ được nữa ạ.",
    "tts": "Dạ, hồ sơ đã nộp, không sửa được nữa ạ.",
}

ATTACH_ALL_FILES_EXIST = {
    "md": (
        "✓ Các tệp đã có sẵn trên hồ sơ, em không đính trùng.\n\n"
        "Công dân rà lại → bấm **Nộp hồ sơ / Gửi hồ sơ** ạ."
    ),
    "tts": "Dạ, tệp đã có đủ. Công dân xem lại, rồi bấm Nộp hồ sơ ạ.",
}

ATTACH_SPLIT_DONE = {
    "md": (
        "✓ Đã đính **{succeeded}/{total} hồ sơ** (mỗi tài liệu một hồ sơ).\n\n"
        "Công dân rà từng tab → tự bấm **Nộp hồ sơ / Gửi hồ sơ** ạ."
    ),
    "tts": "Dạ, em đính xong {succeeded} trên {total} hồ sơ. Công dân xem từng hồ sơ, rồi bấm Nộp ạ.",
}

ATTACH_SPLIT_DONE_WITH_ERRORS = {
    "md": (
        "⚠️ Đính được **{succeeded}/{total} hồ sơ**, còn lỗi:\n\n"
        "{error_list}\n\n"
        "Công dân kiểm tra tab còn thiếu và đính tay ạ."
    ),
    "tts": "Dạ, em đính được {succeeded} trên {total} hồ sơ. Công dân đính tay phần còn thiếu ạ.",
}

SCAN_PICK = {
    "md": (
        "✓ **Scan tại quầy**\n\n"
        "Công dân đặt giấy lên máy quét → bấm **Scan**. Quét tờ nào em tự nhận tờ đó ạ."
    ),
    "tts": "Dạ, công dân đặt giấy lên máy, rồi bấm nút quét. Em tự nhận từng tờ ạ.",
}

# Checklist CHỈ MỘT ô (chứng thực bản sao, chữ ký người dịch): tên ô lấy từ chính checklist,
# không ghi cứng — thủ tục khác đọc "giấy tờ cần chứng thực bản sao" là nói sai thủ tục.
SCAN_PICK_ATTACH = {
    "md": (
        "✓ **Scan tại quầy**\n\n"
        "Công dân đặt giấy lên máy quét → bấm **Scan**. Tất cả nhận là **{doc_name}** ạ."
    ),
    "tts": "Dạ, công dân đặt giấy lên máy, rồi bấm nút quét. Em nhận tất cả là {doc_name} ạ.",
}

# Bước chủ hồ sơ nhận HAI loại giấy dùng vào hai việc khác nhau → ở đây trợ lý CÓ phân loại,
# không được đọc câu "tất cả nhận thẳng là giấy tờ cần chứng thực" của bước đính kèm.
SCAN_PICK_OWNER = {
    "md": (
        "✓ **Scan tại quầy**\n\n"
        "Công dân quét lần lượt **CCCD chủ hồ sơ** và **giấy tờ cần chứng thực** → bấm **Scan**. "
        "Em tự nhận và xếp loại ạ."
    ),
    "tts": "Dạ, công dân lần lượt quét căn cước chủ hồ sơ và giấy cần chứng thực. Em tự nhận và xếp loại ạ.",
}

PROFILE_ASK_PHONE = {
    "md": "✓ **Lấy dữ liệu đã lưu**\n\nCông dân đọc hoặc nhập **số điện thoại** đã lưu lần trước ạ.",
    "tts": "Dạ, công dân đọc số điện thoại đã lưu lần trước ạ.",
}

PROFILE_NOT_FOUND = {
    "md": "Em chưa tìm thấy hồ sơ với số **{phone}** ạ. Công dân kiểm tra lại số, hoặc chọn cách khác:",
    "tts": "Dạ, em chưa tìm thấy hồ sơ với số này. Công dân kiểm tra lại số ạ.",
}

PROFILE_APPLIED = {
    "md": (
        "✓ Đã tìm thấy hồ sơ đã lưu ({count} giấy tờ), không cần chụp lại.\n\n"
        "Em đang điền, công dân chờ chút ạ…"
    ),
    "tts": "Dạ, em tìm thấy hồ sơ đã lưu, không cần chụp lại. Công dân chờ em chút ạ.",
}

DONE_SUBMITTED = {
    "md": (
        "✓ Đã nộp hồ sơ lên **Cổng Dịch vụ công**.\n\n"
        "Công dân có muốn **đăng xuất VNeID** luôn không ạ? Sau **2 phút** em tự đăng xuất."
    ),
    # [TTS-TẠM 17/09/2026] đọc VNeID→"vi en ai đi", QR→"quy rờ", bỏ CON SỐ tài liệu (để thu âm/cache tiếng Mông). Gỡ mốc này + bỏ comment khối dưới là về bản cũ.
    # "tts": (
    # "Công dân đã hoàn thành việc nộp hồ sơ lên Cổng Dịch vụ công. Công dân có muốn "
    # "em đăng xuất tài khoản VNeID giúp mình luôn không ạ? Nếu chưa chọn, em sẽ tự "
    # "đăng xuất sau hai phút để bảo vệ tài khoản."
    # ),
    "tts": (
        "Dạ, công dân đã nộp xong. Có đăng xuất vi en ai đi luôn không ạ? "
        "Sau hai phút em sẽ tự đăng xuất."
    ),
}

# Lời mời đánh giá (đọc khi hiện card đánh giá NGAY sau nộp thành công, trước 2 nút đăng xuất).
RATE_INVITE = {
    "md": (
        "🎉 Nộp hồ sơ thành công!\n\n"
        "Công dân **chạm 1 dòng** để đánh giá Trợ lý hôm nay ạ (không bắt buộc)."
    ),
    "tts": "Dạ, nộp hồ sơ thành công. Công dân chạm một dòng để đánh giá giúp em ạ.",
}

PHONE_SUBSCRIBED = {
    "md": "✓ Đã lưu số **{phone}**. Có tiến độ mới em nhắn ngay ạ.",
    "tts": "Dạ, em đã lưu số. Có tiến độ em sẽ nhắn ạ.",
}

PHONE_INVALID = {
    "md": "Số **{phone}** chưa đúng ạ. Công dân đọc lại **10 số, bắt đầu bằng 0**.",
    "tts": "Dạ, số chưa đúng. Công dân đọc lại mười số, bắt đầu bằng số không ạ.",
}


PROFILE_NEED_PHONE = {
    "md": "Để **lưu hồ sơ**, công dân cho em xin **số điện thoại** ạ.",
    "tts": "Dạ, công dân cho em xin số điện thoại để lưu hồ sơ ạ.",
}

PROFILE_SAVED = {
    "md": (
        "💾 Đã lưu hồ sơ theo số **{phone}** ({count} giấy tờ).\n\n"
        "Lần sau: chọn **📁 Lấy dữ liệu đã lưu** + đọc số này.\n\n"
        "🔒 Muốn xoá: bấm **🗑️ Xóa dữ liệu**."
    ),
    "tts": "Dạ, em đã lưu hồ sơ. Lần sau công dân chỉ cần đọc số điện thoại này ạ.",
}

DATA_DELETED = {
    "md": "🗑️ Đã xoá toàn bộ dữ liệu (hồ sơ, ảnh giấy tờ, phiên). Cảm ơn công dân ạ!",
    "tts": "Dạ, em đã xoá hết dữ liệu. Cảm ơn công dân ạ.",
}

CHANGED_LOCATION = {
    "md": "✓ Đã đổi nơi làm: **{ward}, {province}**",
    "tts": "Dạ, em đã đổi sang {ward}, {province} ạ.",
}

CHANGED_PROCEDURE_RESET = {
    "md": "Dạ, công dân chọn thủ tục khác bên dưới ạ:",
    "tts": "Dạ, công dân chọn thủ tục khác ạ.",
}

OFF_SCOPE = {
    "md": (
        "Dạ, việc này em chưa hỗ trợ ạ 🙏 Em làm được **{count} thủ tục**: {procedures}.\n\n"
        "Công dân cần thủ tục nào ạ?"
    ),
    "tts": "Dạ, việc này em chưa hỗ trợ. Công dân cần làm thủ tục nào ạ?",
}

FALLBACK_CLARIFY = {
    "md": "Dạ, có phải công dân muốn **{hint}** không ạ?",
    "tts": "Dạ, có phải công dân muốn {hint} không ạ?",
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
    "md": (
        "🖨️ ✓ Đã nhận **{count} tệp**.\n\n"
        "- Còn giấy → đặt tiếp vào máy\n- Đủ rồi → bấm **Đã đưa đủ giấy tờ**"
    ),
    "tts": "Dạ, em đã nhận một tệp. Còn giấy thì quét tiếp, đủ rồi thì bấm Đã đưa đủ giấy tờ ạ.",
    "ttsMore": ("Em đã nhận thêm một tệp, tổng cộng {count} tệp. Còn nữa thì công dân đặt tiếp "
                "vào máy scan, đủ rồi bấm nút Đã đưa đủ giấy tờ để em thực hiện xử lý ạ."),
}

# Xác nhận đổi ngôn ngữ. LANG_OFF cố tình CHỈ có tiếng Việt: lượt này _TURN_LANG đã là "vi".
LANG_ON = {
    "md": "✓ Đã bật **tiếng Mông**.",
    "tts": "Dạ, em đã bật tiếng Mông ạ.",
}

LANG_OFF = {
    "md": "✓ Đã chuyển về **tiếng Việt**.",
    "tts": "Dạ, em đã chuyển về tiếng Việt ạ.",
}

# Câu trả lời hỏi-tự-do và các câu trấn an. Trước đây dựng thẳng bằng f-string trong flow.py
# nên KHÔNG có bản Mông nào — quầy Lai Châu bật tiếng Mông vẫn nghe tiếng phổ thông.
PROCEDURE_IN_PROGRESS = {
    "md": "Mình đang làm **{procedure}**, bước **{step}** ạ. Công dân cứ làm theo hướng dẫn nhé.",
    "tts": "Dạ, mình đang làm thủ tục {procedure}. Công dân cứ làm theo hướng dẫn ạ.",
}

DOC_LIST_ANSWER = {
    "md": "Dạ, để làm **{procedure}** công dân cần:\n\n{documents_md}",
    "tts": "Dạ, công dân cần: {documents_tts}.",
}

ANSWER_ONLY_DOCS_AND_STEPS = {
    "md": (
        "Dạ, em chỉ nắm phần **giấy tờ** và **các bước nộp**. "
        "Lệ phí, thời hạn công dân xem trên trang thủ tục ạ."
    ),
    "tts": "Dạ, phần này công dân xem trên trang thủ tục ạ.",
}

# Nói "chọn thêm tệp": trình duyệt chỉ mở cửa sổ chọn tệp khi BẤM thật → mời bấm nút ngay dưới câu này.
PICK_FILES_BY_HAND = {
    "md": "Cửa sổ chọn tệp chỉ mở được khi bấm tay ạ. Công dân bấm nút **📁 Chọn thêm tệp từ máy** "
          "ngay bên dưới giúp em.",
    "tts": "Cửa sổ chọn tệp chỉ mở được khi bấm tay ạ. Công dân bấm nút chọn thêm tệp từ máy ngay bên dưới giúp em.",
}
PICK_FILES_AGAIN = {
    "md": "Công dân chọn thêm tệp trong cửa sổ vừa mở ạ.",
    "tts": "Dạ, công dân chọn thêm tệp ạ.",
}

BUSINESS_STILL_PROCESSING = {
    "md": "Em vẫn đang xử lý, công dân chờ chút ạ…",
    "tts": "Dạ, em vẫn đang xử lý, công dân chờ chút ạ.",
}

STILL_READING_DOCUMENTS = {
    "md": "Em vẫn đang đọc giấy tờ, sắp xong ạ…",
    "tts": "Dạ, em sắp xong rồi ạ.",
}

# ── Dẫn từng bước wizard (guidedSteps) ────────────────────────────────────────────────────
# Công dân lớn tuổi không tìm ra nút "Bước tiếp theo" nằm cuối trang cổng → trợ lý đặt NÚT
# CHUYỂN BƯỚC ngay trong khung chat và tự bấm hộ. Nhãn bước ({attachment_step},
# {result_step}, {submit_label}) lấy từ registry để đọc ĐÚNG CHỮ đang hiện trên cổng.

GUIDED_OWNER_STEP = {
    "md": (
        "Công dân điền/sửa **Thông tin chủ hồ sơ**: ngày cấp, nơi cấp CCCD, SĐT, địa chỉ.\n\n"
        "Xong → bấm nút dưới để sang **{attachment_step}** ạ."
    ),
    "tts": "Công dân điền ngày cấp, nơi cấp căn cước, số điện thoại, địa chỉ. Xong thì bấm nút bên dưới ạ.",
}

# Chặn TRƯỚC khi bấm nút của cổng: cổng chỉ tô đỏ ô thiếu ở cuối trang, công dân không thấy.
GUIDED_OWNER_MISSING = {
    "md": "Trang còn thiếu **{missing_note}** ạ. Công dân điền nốt → bấm lại nút dưới.",
    "tts": "Dạ, còn thiếu {missing_tts}. Công dân điền nốt, rồi bấm lại nút bên dưới ạ.",
}

GUIDED_ATTACH_DONE = {
    "md": ("✓ Đã đính **{attached} tệp**.\n\n"
           "Công dân rà lại → bấm nút dưới (hoặc nói **“bước tiếp theo”**) để sang **{result_step}** ạ."),
    "tts": "Dạ, em đính kèm xong. Công dân xem lại, rồi bấm nút bên dưới để sang bước {result_step} ạ.",
}

# Bước Thông tin nhận kết quả của thủ tục KHÔNG khai cách mặc định: hiện thẻ, không chọn sẵn.
GUIDED_RESULT_CHOOSE = {
    "md": "✓ Đã vào **{result_step}**. Công dân chọn **một** cách nhận kết quả bên dưới (bấm hoặc nói tên) ạ.",
    "tts": "Dạ, đã sang bước {result_step}. Công dân chọn một cách nhận kết quả bên dưới ạ.",
}

# Công dân NÓI "sang bước tiếp theo / bước nhận kết quả" ở trang Thành phần hồ sơ → trợ lý bấm hộ
# "Bước tiếp theo" (báo cáo cú bấm đi đường guided_step_report như nút).
VOICE_NEXT_STEP = {
    "md": "Em bấm **{next_label}** sang **{result_step}** ạ…",
    "tts": "Dạ, em chuyển sang bước {result_step} ạ.",
}
# Công dân NÓI "gửi hồ sơ" ở bước Thông tin nhận kết quả: nộp hồ sơ không chạy bằng lời → nhắc tự bấm.
VOICE_SUBMIT_SELF = {
    "md": "Dạ, công dân kiểm tra lại rồi tự bấm **{submit_label}** giúp em ạ.",
    "tts": "Dạ, công dân kiểm tra lại, rồi tự bấm {submit_label} giúp em ạ.",
}

# Cổng chặn bằng toast/thông báo đỏ (vd "Vui lòng đính kèm đủ Hồ sơ bắt buộc"). Toast tự tắt
# sau vài giây và nằm ở góc màn hình — đọc lại nguyên văn cho công dân biết vì sao chưa qua bước.
GUIDED_STEP_BLOCKED = {
    "md": "⚠️ Trang báo: *{portal_message}*\n\nCông dân xử lý xong → bấm lại nút dưới ạ.",
    "tts": "Dạ, trang báo: {portal_message}. Công dân sửa xong, rồi bấm lại nút bên dưới ạ.",
}

# Dùng chung cho cả nút chuyển bước lẫn nút gửi hồ sơ → không nêu tên nút cụ thể; dùng chung cho thủ tục chỉ
# đính kèm (chứng thực: không có ô tờ khai) → không nói "ô báo đỏ".
GUIDED_STEP_STUCK = {
    "md": "⚠️ Trang chưa sang bước tiếp theo. Công dân xem lại trang giúp em, xử lý xong thì bấm lại nút dưới ạ.",
    "tts": "Dạ, trang chưa sang bước tiếp theo. Công dân xem lại trang giúp em, xong thì bấm lại nút bên dưới ạ.",
}

# Bấm sang bước từ Thành phần hồ sơ mà cổng không nháy lời nào: lý do hay gặp nhất là còn dòng giấy tờ bắt buộc
# chưa có tệp.
GUIDED_ATTACH_STEP_STUCK = {
    "md": "⚠️ Trang chưa sang bước tiếp theo. Công dân xem giúp em còn **giấy tờ bắt buộc** nào chưa đính kèm không, "
          "đính đủ rồi bấm lại nút dưới ạ.",
    "tts": "Dạ, trang chưa sang bước tiếp theo. Công dân xem còn giấy tờ bắt buộc nào chưa đính kèm không, "
           "đính đủ rồi bấm lại nút bên dưới ạ.",
}

# Bước cuối: trợ lý KHÔNG tự chọn hộ (phương thức nhận kết quả là ý muốn của công dân, chọn
# sai là phải làm lại hồ sơ) — chỉ nói kỹ từng lựa chọn và các ô đi kèm.
GUIDED_RESULT_STEP = {
    "md": (
        "✓ Đã vào **{result_step}**. Công dân chọn **1** cách nhận kết quả ạ:\n\n"
        "1. **Bản giấy có đóng dấu** — chọn thêm nơi đến lấy.\n2. "
        "**Trực tuyến** — nhận bản điện tử, không phải đến quầy.\n3. "
        "**Bưu chính công ích** — điền đơn vị bưu chính, người nhận, SĐT, địa chỉ.\n\n"
        "Chọn xong → bấm nút dưới hoặc **{submit_label}** ạ."
    ),
    "tts": (
        "Dạ, công dân chọn một cách nhận kết quả: "
        "nhận bản giấy tại quầy, nhận bản điện tử, hoặc gửi qua bưu điện. "
        "Chọn bưu điện thì điền thêm địa chỉ người nhận. Chọn xong thì bấm nút bên dưới ạ."
    ),
}

GUIDED_SUBMIT_SENT = {
    "md": "Em đã bấm **{submit_label}**, chờ trang xác nhận chút ạ…",
    "tts": "Dạ, em đã gửi hồ sơ. Công dân chờ chút ạ.",
}

# Trang đã điền đủ mọi ô bắt buộc → không bắt công dân quét giấy tờ ở bước này nữa, giấy tờ
# để sang bước Thành phần hồ sơ nhận một thể.
GUIDED_OWNER_READY = {
    "md": (
        "✓ **Thông tin chủ hồ sơ** đã đủ.\n\n"
        "Công dân đọc lại → bấm nút dưới để sang **{attachment_step}** ạ."
    ),
    "tts": "Dạ, thông tin chủ hồ sơ đã đủ. Công dân đọc lại, rồi bấm nút bên dưới ạ.",
}

# Hỏi RIÊNG thẻ căn cước: nó được quét để lấy ngày cấp/nơi cấp điền form, nhưng chưa chắc
# công dân muốn chứng thực chính thẻ đó. Các giấy còn lại mặc định là giấy đem đi chứng thực.
GUIDED_CERTIFY_ASK = {
    "md": "Có **thẻ Căn cước công dân** trong giấy tờ. Công dân có **chứng thực bản sao** thẻ này không ạ?",
    "tts": "Dạ, công dân có chứng thực luôn thẻ căn cước không ạ?",
}

# Công dân tự điền xong rồi tự bấm sang bước Thành phần hồ sơ trong lúc trợ lý còn đang chờ
# giấy tờ. Checklist của bước chủ hồ sơ hết nghĩa ở đây → phải nói đã sang bước nào.
GUIDED_DOCS_STEP_SWITCHED = {
    "md": (
        "✓ Đã sang **Thành phần hồ sơ**. Từ đây em chỉ nhận **giấy cần chứng thực**.\n\n"
        "Công dân đưa nốt giấy tờ → bấm nút dưới ạ."
    ),
    "tts": "Dạ, đã sang bước thành phần hồ sơ. Công dân đưa nốt giấy cần chứng thực, rồi bấm nút bên dưới ạ.",
}

# Thẻ căn cước đã quét ở bước trước: trợ lý KHÔNG chạy pipeline chủ hồ sơ (công dân tự điền)
# nên không có bằng chứng nào nói thẻ đó đưa ra để làm gì. Không đoán — chuyển sang giấy cần
# chứng thực cho công dân NHÌN THẤY và tự quyết; giấu tệp đi mà vẫn đính là tệ nhất.
GUIDED_IDENTITY_MOVED_NOTE = {
    "md": (
        "\n\n"
        "Thẻ **Căn cước** em xếp vào **giấy cần chứng thực**. "
        "Không cần chứng thực thì bấm vào mục đó để xoá ạ."
    ),
    "tts": " Thẻ căn cước em xếp vào giấy cần chứng thực. Không cần thì công dân xoá ạ.",
}

GUIDED_AUTHORIZATION_ATTACHED = {
    "md": "📎 ✓ Đã đính **giấy ủy quyền**.",
    "tts": "Dạ, em đã đính giấy ủy quyền ạ.",
}

GUIDED_AUTHORIZATION_ATTACH_FAILED = {
    "md": (
        "⚠️ Chưa đính được **giấy ủy quyền** ({error}).\n\n"
        "Công dân bấm **Chọn tệp đính kèm** ở dòng giấy ủy quyền ạ."
    ),
    "tts": "Dạ, em chưa đính được giấy ủy quyền. Công dân bấm Chọn tệp đính kèm ở dòng đó ạ.",
}

GUIDED_CERTIFY_YES = {
    "md": "✓ Em chứng thực cả **thẻ Căn cước** ạ.",
    "tts": "Dạ, em chứng thực cả thẻ căn cước ạ.",
}

GUIDED_CERTIFY_NO = {
    "md": "✓ Thẻ **Căn cước** chỉ dùng để điền, **không** đính vào hồ sơ ạ.",
    "tts": "Dạ, thẻ căn cước chỉ dùng để điền thông tin ạ.",
}

# Nhãn nút trong khung chat: ngắn, đọc là hiểu bấm xong đi đâu.
GUIDED_CERTIFY_YES_CTA = "✅ Có, chứng thực luôn"
GUIDED_CERTIFY_NO_CTA = "❌ Không chứng thực thẻ này"
GUIDED_OWNER_CTA = "Xong, sang bước đính kèm →"
# Trợ lý gạt sẵn công tắc "bản giấy" — cách đại đa số công dân ra quầy đang chọn. Vẫn nói rõ
# đây là ĐỀ XUẤT và đổi được trong một chạm.
GUIDED_RESULT_PICK = {
    "md": "✓ Đã vào **{result_step}**.\n\nEm đang chọn **{label}**. Muốn đổi → bấm cách khác ạ.",
    "tts": "Dạ, em chọn sẵn {label}. Muốn đổi, công dân bấm cách khác ạ.",
}

# Câu chốt đi kèm MỌI lượt chọn cách nhận kết quả — dùng qua note= của _fmt để bản Mông cũng
# nối đúng khối của nó, không lẫn Việt vào lời đọc Mông.
GUIDED_RESULT_SUBMIT_HINT = {
    "md": "\n\nKiểm tra xong → bấm **{submit_label}** để nộp ạ.",
    "tts": " Kiểm tra xong, công dân bấm {submit_label} ạ.",
}

# Cổng Bộ Y tế (guidedSteps.selfSubmit): dưới ô nhận kết quả còn ô cam đoan + Mã xác nhận — lời cam đoan
# và mã kiểm tra là việc của CHÍNH công dân, trợ lý chỉ nhắc, không tích/gõ hộ.
GUIDED_RESULT_CAPTCHA_HINT = {
    "md": ("\n\nCông dân tích ô **“Tôi chắc chắn rằng các thông tin khai báo trên là đúng sự thật…”**, "
           "nhập **Mã xác nhận** theo chữ trong ảnh bên cạnh (khó đọc thì bấm nút làm mới), "
           "rồi bấm **{submit_label}** để nộp hồ sơ ạ."),
    "tts": " Công dân tích ô cam đoan, nhập mã xác nhận theo chữ trong ảnh, rồi bấm {submit_label} để nộp hồ sơ ạ.",
}

# Nói "lưu và nộp hồ sơ / gửi hồ sơ": nộp không rút lại được → hỏi lại một lần. {label} = tên nút nộp (bỏ biểu tượng).
VOICE_SUBMIT_CONFIRM = {
    "md": "Công dân chắc chắn **nộp hồ sơ** chứ ạ? Nói **Có** hoặc bấm **{label}** để em nộp ạ.",
    "tts": "Công dân chắc chắn nộp hồ sơ chứ ạ? Công dân nói Có, hoặc bấm {label} để em nộp ạ.",
}
VOICE_SUBMIT_CANCELLED = {
    "md": "Dạ, em chưa nộp. Công dân kiểm tra lại, sẵn sàng thì nói hoặc bấm **{label}** ạ.",
    "tts": "Dạ em chưa nộp. Công dân kiểm tra lại, sẵn sàng thì nói hoặc bấm {label} ạ.",
}

GUIDED_RESULT_PICKED = {
    "md": "✓ Đã chọn **{label}**.",
    "tts": "Dạ, em đã chọn {label} ạ.",
}

# CHỈ dịch vụ bưu chính mới đòi thêm thông tin. Địa chỉ/người nhận là dữ liệu riêng của công
# dân, điền hộ mà sai là kết quả đi lạc chỗ.
GUIDED_RESULT_NEEDS_INPUT = {
    "md": "✓ Đã chọn **{label}**.\n\nCông dân **tự điền** tên, địa chỉ người nhận trên trang ạ.",
    "tts": "Dạ, em đã chọn {label}. Công dân tự điền tên và địa chỉ người nhận ạ.",
}

GUIDED_RESULT_MISSING = {
    "md": "✓ Đã chọn **{label}**.\n\nCòn thiếu **{missing_note}**, công dân điền nốt ạ.",
    "tts": "Dạ, em đã chọn {label}. Còn thiếu {missing_tts}, công dân điền nốt ạ.",
}

GUIDED_RESULT_FAILED = {
    "md": "⚠️ Em chưa gạt được **{label}**. Công dân gạt trên trang → bấm **{submit_label}** ạ.",
    "tts": "Dạ, em chưa chọn được {label}. Công dân gạt trên trang, rồi bấm {submit_label} ạ.",
}

# Cổng Bộ Y tế: cách nhận kết quả là ô chọn thả xuống, không phải công tắc. Câu chốt cam đoan/mã đi qua note=.
GUIDED_RESULT_SELECT_FAILED = {
    "md": "⚠️ Em chưa chọn được **{label}**. Công dân chọn ở ô **{result_step}** trên trang ạ.",
    "tts": "Dạ, em chưa chọn được {label}. Công dân chọn ở ô {result_step} trên trang ạ.",
}

# Cổng Bộ Y tế, "Nhận trực tiếp tại nhà qua bưu điện": cổng mọc hai ô tích (không bắt buộc) — trợ lý không tích
# hộ vì đó là đăng ký dịch vụ bưu chính có phí của công dân.
GUIDED_RESULT_HOME_POSTAL = {
    "md": ("✓ Đã chọn **{label}**.\n\nCông dân tích **Đăng ký nhận kết quả tại nhà** (muốn bưu điện đến lấy hồ "
           "sơ thì tích thêm **Đăng ký nộp hồ sơ tại nhà**). Phí bưu chính trả trực tiếp cho nhân viên bưu điện ạ."),
    "tts": ("Dạ, em đã chọn {label}. Công dân tích ô đăng ký nhận kết quả tại nhà. Phí bưu chính trả trực tiếp "
            "cho nhân viên bưu điện ạ."),
}

GUIDED_ATTACH_SPLIT_DONE = {
    "md": (
        "✓ Đã đính **{succeeded}/{total} hồ sơ**.\n\n"
        "- Tab này: bấm nút dưới để sang **{result_step}**\n- Tab khác: "
        "mở từng tab → bấm **Nộp hồ sơ / Gửi hồ sơ**"
    ),
    "tts": (
        "Dạ, em đính xong {succeeded} trên {total} hồ sơ. Hồ sơ này, công dân bấm nút bên dưới. "
        "Hồ sơ khác, công dân mở ra rồi bấm Nộp ạ."
    ),
}

GUIDED_ATTACH_CTA = "Xong, sang bước nhận kết quả →"
GUIDED_SUBMIT_CTA = "📨 Gửi hồ sơ"

# ── Tư pháp luồng mới: trang nộp MỘT TRANG của Cổng DVC quốc gia (chat/tu_phap_moi.py) ──
# Form, thành phần hồ sơ và hình thức nhận kết quả nằm cùng một trang: không có câu "chuyển
# sang bước…"; nút trong khung chat đặt đúng tên nút/ô trên trang để công dân đối chiếu.
TPM_ATTACH_CTA = "📎 Đính kèm thành phần hồ sơ"
TPM_RESULT_CTA = "📮 Chọn hình thức nhận kết quả"
TPM_SUBMIT_CTA = "💾 Lưu và nộp hồ sơ"

# Extension trên máy quầy chưa có engine cho trang mới — dẫn vào là kẹt ở trang không điền được.
TPM_UPDATE_REQUIRED = {
    "md": (
        "⚠️ Cổng đã đổi **mẫu mới** cho **{procedure}**, Trợ lý bản này chưa hỗ trợ.\n\n"
        "Cán bộ cập nhật Trợ lý rồi mở lại ạ. Trong lúc chờ, công dân có thể chọn thủ tục khác."
    ),
    "tts": "Dạ, cổng đã đổi mẫu mới, em chưa làm được thủ tục này. Nhờ cán bộ cập nhật trợ lý ạ.",
}

# Câu đuôi sau báo cáo điền (note= của FILL_REPORT_REVIEW): planner đính kèm chạy nền ngay lúc này.
TPM_FILL_NEXT = {
    "md": "\n\nEm đang xếp sẵn giấy tờ. Rà xong → bấm **Đính kèm thành phần hồ sơ** ạ.",
    "tts": " Xem xong, công dân bấm Đính kèm thành phần hồ sơ ạ.",
}

TPM_ATTACH_WAIT_PLAN = {
    "md": "Em đang xếp giấy tờ, xong là đính ngay, chờ chút ạ…",
    "tts": "Dạ, công dân chờ em chút ạ.",
}

TPM_ATTACH_DONE = {
    "md": "✓ Đã đính **{attached} tệp**.\n\nCông dân rà lại → bấm **Chọn hình thức nhận kết quả** ạ.",
    "tts": "Dạ, em đính kèm xong. Công dân xem lại, rồi bấm Chọn hình thức nhận kết quả ạ.",
}

TPM_ATTACH_ALL_EXIST = {
    "md": "✓ Các tệp đã có sẵn, em không đính trùng.\n\nCông dân bấm **Chọn hình thức nhận kết quả** ạ.",
    "tts": "Dạ, tệp đã có đủ. Công dân bấm Chọn hình thức nhận kết quả ạ.",
}

TPM_ATTACH_DONE_WITH_ERRORS = {
    "md": (
        "⚠️ Đính được **{attached} tệp**, còn lỗi:\n\n"
        "{error_list}\n\n"
        "Bấm **Đính kèm lại** để thử lần nữa, hoặc **Điều chỉnh giấy tờ** nếu tệp chưa đúng ạ."
    ),
    "tts": "Dạ, còn vài tệp lỗi. Công dân bấm Đính kèm lại, hoặc Điều chỉnh giấy tờ ạ.",
}

TPM_ATTACH_NONE = {
    "md": (
        "⚠️ Chưa đính được tệp nào{error_note}.\n\n"
        "Bấm **Đính kèm lại** để thử lần nữa, hoặc **Điều chỉnh giấy tờ** nếu tệp chưa đúng ạ."
    ),
    "tts": "Dạ, em chưa đính được. Công dân bấm Đính kèm lại, hoặc Điều chỉnh giấy tờ ạ.",
}

TPM_RESULT_PICK = {
    "md": "Em đang chọn **{label}**. Muốn đổi → bấm cách khác ạ.",
    "tts": "Dạ, em chọn sẵn {label}. Muốn đổi, công dân bấm cách khác ạ.",
}

# Câu chốt đi kèm mọi lượt chọn cách nhận (note=).
TPM_SUBMIT_HINT = {
    "md": "\n\nKiểm tra xong → bấm **Lưu và nộp hồ sơ** ạ.",
    "tts": " Kiểm tra xong, công dân bấm Lưu và nộp hồ sơ ạ.",
}

# Bưu điện trên trang một trang: FE điền khối người nhận theo NGƯỜI YÊU CẦU trên tờ khai.
TPM_RESULT_RECIPIENT_FILLED = {
    "md": ("✓ Đã chọn **{label}**.\n\nEm đã điền **{filled_note}** của người nhận theo người yêu cầu "
           "trên tờ khai, công dân kiểm tra lại ạ."),
    "tts": "Dạ, em đã chọn {label} và điền thông tin người nhận theo người yêu cầu trên tờ khai. "
           "Công dân kiểm tra lại ạ.",
}

TPM_RESULT_RECIPIENT_PARTIAL = {
    "md": ("✓ Đã chọn **{label}**.\n\nEm đã điền **{filled_note}** theo người yêu cầu trên tờ khai. "
           "Còn thiếu **{missing_note}**, công dân điền nốt ạ."),
    "tts": "Dạ, em đã chọn {label} và điền thông tin người nhận theo tờ khai. "
           "Còn thiếu {missing_tts}, công dân điền nốt ạ.",
}

TPM_RESULT_FAILED = {
    "md": (
        "⚠️ Em chưa chọn được **{label}**. "
        "Công dân chọn ở ô **Hình thức nhận kết quả** → bấm **Lưu và nộp hồ sơ** ạ."
    ),
    "tts": "Dạ, em chưa chọn được {label}. Công dân chọn trên trang, rồi bấm Lưu và nộp hồ sơ ạ.",
}

# Ô thiếu do FE đọc THẲNG trên trang (ô bắt buộc của form + khối nhận kết quả qua bưu điện).
TPM_SUBMIT_MISSING = {
    "md": (
        "⚠️ Chưa nộp, còn thiếu: **{missing_note}** (đã tô đỏ).\n\n"
        "Công dân điền nốt → bấm lại **Lưu và nộp hồ sơ** ạ."
    ),
    "tts": "Dạ, còn thiếu {missing_tts}. Công dân điền ô tô đỏ, rồi bấm lại Lưu và nộp hồ sơ ạ.",
}

TPM_SUBMIT_BLOCKED = {
    "md": "⚠️ Trang báo: *{portal_message}*\n\nCông dân xử lý xong → bấm lại **Lưu và nộp hồ sơ** ạ.",
    "tts": "Dạ, trang báo: {portal_message}. Công dân sửa xong, rồi bấm lại Lưu và nộp hồ sơ ạ.",
}

TPM_SUBMIT_STUCK = {
    "md": "⚠️ Em chưa bấm được **Lưu và nộp hồ sơ**. Công dân bấm nút đó ở cuối trang ạ.",
    "tts": "Dạ, công dân bấm nút Lưu và nộp hồ sơ ở cuối trang ạ.",
}

# ── Luồng TỰ ĐỘNG (tu_phap_moi.auto_flow): điền xong tự đính kèm, xong hiện luôn nút nộp ──
# Câu đuôi sau báo cáo điền (note= của FILL_REPORT_REVIEW). TTS ngắn: câu "đính xong" về ngay sau.
TPM_AUTO_ATTACH_WAIT = {
    "md": "\n\nChuẩn bị xong em đính kèm ngay ạ…",
    "tts": " Chuẩn bị xong em đính kèm ngay ạ.",
}

TPM_AUTO_ATTACH_DONE = {
    "md": "✓ Đã đính **{attached} tệp**.",
    "tts": "Dạ, em đính kèm xong.",
}

TPM_AUTO_ALL_EXIST = {
    "md": "✓ Các tệp đã có sẵn, em không đính trùng.",
    "tts": "Dạ, tệp đã có đủ.",
}

# Cổng chọn sẵn một cách nhận kết quả; {label} = cách mặc định khai trong registry thủ tục.
TPM_AUTO_RESULT_DEFAULT = {
    "md": (
        "\n\n"
        "Hình thức nhận kết quả đang để mặc định **{label}**; "
        "công dân muốn đổi thì bấm **Chọn hình thức nhận kết quả** rồi chọn hình thức tương ứng ạ. "
        "Rà xong → bấm **Lưu và nộp hồ sơ** ạ."
    ),
    "tts": (
        " Hình thức nhận kết quả đang để mặc định {label}; "
        "công dân muốn đổi thì bấm chọn hình thức nhận kết quả rồi chọn hình thức tương ứng ạ. "
        "Rà xong, công dân bấm Lưu và nộp hồ sơ ạ."
    ),
}

TPM_DONE_REMIND = {
    "md": "Công dân bấm nút dưới để đi tiếp ạ.",
    "tts": "Dạ, công dân bấm nút bên dưới ạ.",
}

# ── Trang nộp một trang, luồng bản 2 (extension khai supportsFlowV2; chế độ Mông giữ luồng cũ) ──
# Mỗi khung một việc: nhận tệp → thẻ tiến trình 3 bước → kết quả điền → kết quả đính kèm → kết luận. Nút đi tiếp
# (chọn hình thức nhận kết quả, nộp) chỉ hiện khi tờ khai đủ ô bắt buộc.
FLOW2_STEPS = ("Bóc tách thông tin từ giấy tờ", "Điền tờ khai", "Đính kèm giấy tờ")
FLOW2_DOCS_RECEIVED = {
    "md": "✓ Đã nhận **{files_count} tệp**.\n\nEm đang đọc giấy tờ để điền tờ khai và đính kèm, công dân chờ chút ạ…",
    "tts": "Dạ em đã nhận giấy tờ. Em đang đọc để điền tờ khai và đính kèm, công dân chờ chút ạ.",
}
FLOW2_REFILL = {
    "md": "Em đang đọc lại giấy tờ để điền lại tờ khai, công dân chờ chút ạ…",
    "tts": "Dạ em đang đọc lại giấy tờ để điền lại tờ khai, công dân chờ chút ạ.",
}
FLOW2_FILL_RESULT = {
    "md": "🟩 Em đã điền **{filled} ô** vào tờ khai.{default_md}{not_found_md}",
    "tts": "Dạ em đã điền {filled} ô vào tờ khai.{default_tts}",
}
FLOW2_FILL_DEFAULT = {
    "md": "\n\n🟨 **{count} ô** em điền mặc định (viền vàng), công dân kiểm tra lại giúp em ạ.",
    "tts": " Có {count} ô em điền mặc định, công dân kiểm tra lại giúp em ạ.",
}
FLOW2_FILL_NOT_FOUND = "\n\n⚠️ **{count} ô** chưa khớp được trên tờ khai: {labels}."
FLOW2_ATTACH_RESULT = {
    "md": "📎 Em đã đính kèm **{attached} tệp**:\n\n{plan_list}\n\nCông dân rà soát lại các tệp đã đính trên trang ạ.",
    "tts": "Dạ em đã đính kèm xong. Công dân rà soát lại các tệp đã đính trên trang ạ.",
}
FLOW2_ATTACH_ALL_EXIST = {
    "md": "📎 Các tệp đã có sẵn trên trang, em không đính trùng ạ.",
    "tts": "Dạ các tệp đã có sẵn trên trang, em không đính trùng ạ.",
}
FLOW2_ATTACH_ERRORS = {
    "md": "⚠️ Em đính được **{attached} tệp**, còn lỗi:\n\n{error_list}\n\nCông dân bấm **Đính kèm lại** để thử lần nữa ạ.",
    "tts": "Dạ còn tệp đính chưa được. Công dân bấm Đính kèm lại để em thử lần nữa ạ.",
}
FLOW2_NEED_REQUIRED = {
    "md": ("🟥 **{required} ô bắt buộc** · 🟧 **{optional} ô không bắt buộc** còn trống.\n\nTờ khai còn **{required} ô "
           "bắt buộc** chưa có thông tin. Công dân có thể tự điền thẳng vào tờ khai, hoặc bấm **Bổ sung các thông tin "
           "còn thiếu** để em hỏi và điền lần lượt từng ô cho đầy đủ ạ."),
    "tts": (" Tờ khai còn {required} ô bắt buộc chưa có thông tin. Công dân có thể tự điền thẳng vào tờ khai, hoặc bấm "
            "Bổ sung các thông tin còn thiếu để em hỏi và điền lần lượt từng ô ạ."),
}
FLOW2_OPTIONAL_ONLY = {
    "md": ("✓ Tờ khai đã đủ các ô bắt buộc, còn **{optional} ô không bắt buộc** để trống.\n\nCông dân muốn bổ sung thì "
           "bấm **Bổ sung các thông tin còn thiếu**; không thì bấm **Chọn hình thức nhận kết quả** để đổi cách nhận "
           "kết quả, hoặc **Lưu và nộp hồ sơ** ạ."),
    "tts": (" Tờ khai đã đủ các ô bắt buộc, còn {optional} ô không bắt buộc để trống. Công dân muốn bổ sung thì bấm Bổ "
            "sung các thông tin còn thiếu, không thì chọn hình thức nhận kết quả hoặc bấm Lưu và nộp hồ sơ ạ."),
}
# {done}: "điền và đính kèm đủ" | "điền đủ" (đính kèm còn lỗi thì không khẳng định đã đính đủ).
FLOW2_READY = {
    "md": ("✓ Công dân đã {done} các thông tin bắt buộc.\n\nHình thức nhận kết quả đang để **{label}**. Công dân bấm "
           "**Chọn hình thức nhận kết quả** để đổi, hoặc bấm **Lưu và nộp hồ sơ** để nộp luôn ạ."),
    "tts": (" Công dân đã {done} các thông tin bắt buộc. Hình thức nhận kết quả đang để {label}. Công dân bấm Chọn "
            "hình thức nhận kết quả để đổi, hoặc bấm Lưu và nộp hồ sơ để nộp luôn ạ."),
}
FLOW2_READY_NO_DEFAULT = {
    "md": ("✓ Công dân đã {done} các thông tin bắt buộc.\n\nCông dân bấm **Chọn hình thức nhận kết quả** rồi **Lưu và "
           "nộp hồ sơ** ạ."),
    "tts": " Công dân đã {done} các thông tin bắt buộc. Công dân bấm Chọn hình thức nhận kết quả rồi Lưu và nộp hồ sơ ạ.",
}
FLOW2_DONE_ATTACHED = "điền và đính kèm đủ"
FLOW2_DONE_FILLED = "điền đủ"
# Hỏi xong vòng bổ sung mà vẫn còn ô bắt buộc trống: chưa có nút đi tiếp.
FLOW2_REVIEW_MISSING = {
    "md": ("{lead_md}Tờ khai còn **{required} ô bắt buộc** công dân cần điền. Công dân điền thẳng vào tờ khai, hoặc bấm "
           "**Bổ sung các thông tin còn thiếu** để em hỏi lại các ô đó ạ."),
    "tts": ("{lead_tts}Tờ khai còn {required} ô bắt buộc công dân cần điền. Công dân điền thẳng vào tờ khai, hoặc bấm "
            "Bổ sung các thông tin còn thiếu để em hỏi lại ạ."),
}
# ── Tư pháp form cũ (tờ khai eForm, profile "tu-phap"), luồng bản 2: hai thẻ tiến trình (điền; đính kèm) vì giữa
# hai chặng là Xem trước → Xác nhận trên cổng ──
FLOW2_FILL_STEPS = ("Bóc tách thông tin từ giấy tờ", "Điền tờ khai")
FLOW2_ATTACH_STEPS = ("Xếp giấy tờ vào thành phần hồ sơ", "Đính kèm giấy tờ")
# Sang Kê khai, điền tờ khai bằng giấy tờ đã nhận ở bước chủ hồ sơ (không nhận tệp mới).
FLOW2_MAIN_FORM = {
    "md": "✓ Đã sang **Kê khai thông tin**.\n\nEm đang đọc giấy tờ để điền tờ khai, công dân chờ chút ạ…",
    "tts": "Dạ đã sang bước kê khai thông tin. Em đang đọc giấy tờ để điền tờ khai, công dân chờ chút ạ.",
}
FLOW2_DOCS_RECEIVED_FILL = {
    "md": "✓ Đã nhận **{files_count} tệp**.\n\nEm đang đọc giấy tờ để điền tờ khai, công dân chờ chút ạ…",
    "tts": "Dạ em đã nhận giấy tờ. Em đang đọc để điền tờ khai, công dân chờ chút ạ.",
}
# Tờ khai đủ ô bắt buộc → bước kế tiếp là Xem trước (cổng chặn Xem trước khi còn ô bắt buộc trống).
FLOW2_PREVIEW_READY = {
    "md": ("✓ Tờ khai đã đủ các ô bắt buộc{optional_md}.\n\n{optional_hint_md}Công dân rà lại rồi bấm **Xem trước tờ "
           "khai** để em mở bản xem trước và xác nhận ạ."),
    "tts": (" Tờ khai đã đủ các ô bắt buộc{optional_tts}. {optional_hint_tts}Công dân rà lại rồi bấm Xem trước tờ khai "
            "để em mở bản xem trước và xác nhận ạ."),
}
FLOW2_OPTIONAL_LEFT = ", còn **{optional} ô không bắt buộc** để trống"
FLOW2_OPTIONAL_LEFT_TTS = ", còn {optional} ô không bắt buộc để trống"
FLOW2_OPTIONAL_HINT = {
    "md": "Công dân cần bổ sung thông tin còn thiếu thì bấm **Bổ sung các thông tin còn thiếu** để em hỏi từng ô. ",
    "tts": "Công dân cần bổ sung thông tin còn thiếu thì bấm Bổ sung các thông tin còn thiếu để em hỏi từng ô. ",
}
# ── Cổng liên thông (form Angular, chat/lien_thong.py): 6 bước, mỗi bước có nút + lệnh nói "bước tiếp theo".
# Chỉ bản tiếng Việt: luồng tắt ở chế độ Mông. ──
LT_STEP_NAMES = {2: "Kê khai", 3: "Xem lại các tờ khai chi tiết", 4: "Đính kèm thành phần hồ sơ",
                 5: "Lựa chọn hình thức nhận kết quả"}
LT_AGENCY_CHIP = "▶ Sang bước Kê khai"
LT_REVIEW_CHIP = "📄 Xem lại tờ khai ▶"
LT_ATTACH_CHIP = "📎 Sang bước đính kèm ▶"
LT_RESULT_CHIP = "📬 Chọn cách nhận kết quả ▶"
LT_BACK_CHIP = "✏️ Quay lại sửa tờ khai"
LT_RETRY_CHIP = "🔁 Thử chuyển bước lại"
LT_SUBMIT_CHIP = "📨 Nộp hồ sơ"
LT_AGENCY_FILLING = {
    "md": ("Em đang chọn **cơ quan thực hiện** theo nơi ở **{ward}, {province}**. Công dân rà lại rồi bấm "
           "**Sang bước Kê khai** hoặc nói **“bước tiếp theo”** ạ."),
    "tts": ("Em đang chọn cơ quan thực hiện cho công dân. Công dân rà lại rồi bấm Sang bước Kê khai, hoặc nói bước "
            "tiếp theo ạ."),
}
LT_MOVING = {
    "md": "Dạ em chuyển sang bước **{step}** ạ.",
    "tts": "Dạ em chuyển sang bước {step} ạ.",
}
LT_MOVING_BACK = {
    "md": "Dạ em quay lại bước **Kê khai** để công dân sửa tờ khai ạ.",
    "tts": "Dạ em quay lại bước Kê khai để công dân sửa tờ khai ạ.",
}
# Đủ ô bắt buộc ở Kê khai (cùng khoá với FLOW2_PREVIEW_READY: field_review._ready dùng chung bộ tham số).
LT_FILL_READY = {
    "md": ("✓ Tờ khai đã đủ các ô bắt buộc{optional_md}.\n\n{optional_hint_md}Công dân rà lại rồi bấm **Xem lại tờ "
           "khai** hoặc nói **“bước tiếp theo”** để sang bước xem lại các tờ khai chi tiết ạ."),
    "tts": (" Tờ khai đã đủ các ô bắt buộc{optional_tts}. {optional_hint_tts}Công dân rà lại rồi bấm Xem lại tờ khai, "
            "hoặc nói bước tiếp theo để sang bước xem lại các tờ khai chi tiết ạ."),
}
# Thủ tục liên thông chưa có vòng bổ sung ô (hoặc báo cáo điền không kèm số ô).
LT_FILL_NEXT = {
    "md": ("Công dân rà lại tờ khai, ô nào sai thì sửa thẳng trên trang, xong bấm **Xem lại tờ khai** hoặc nói "
           "**“bước tiếp theo”** ạ."),
    "tts": "Công dân rà lại tờ khai, xong bấm Xem lại tờ khai, hoặc nói bước tiếp theo ạ.",
}
LT_OPTIONAL_PHASE = {
    "md": ("✓ Đã đủ các ô bắt buộc. Em hỏi tiếp **{optional} ô không bắt buộc**; công dân muốn đi tiếp luôn thì bấm "
           "**Xem lại tờ khai** ạ."),
    "tts": ("Dạ đã đủ các ô bắt buộc. Em hỏi tiếp các ô không bắt buộc, công dân muốn đi tiếp luôn thì bấm Xem lại tờ "
            "khai ạ. "),
}
LT_PROCEED_STEP = "cổng chưa cho sang bước xem lại tờ khai"
LT_BLOCKED = {
    "md": "⚠️ Cổng chưa cho sang bước **{step}**{message}. Công dân xem lại trang rồi thử lại ạ.",
    "tts": "Dạ cổng chưa cho sang bước {step}. Công dân xem lại trang rồi thử lại ạ.",
}
LT_BLOCKED_FORM = {
    "md": ("⚠️ Cổng chưa cho sang bước xem lại{message}: tờ khai còn **{required} ô bắt buộc** trống (ô tô đỏ trên "
           "trang).\n\nCông dân bấm **Bổ sung các thông tin còn thiếu** để em hỏi từng ô, hoặc tự điền rồi bấm **Xem "
           "lại tờ khai** ạ."),
    "tts": ("Dạ cổng chưa cho sang bước xem lại, tờ khai còn {required} ô bắt buộc trống. Công dân bấm Bổ sung các "
            "thông tin còn thiếu để em hỏi từng ô, hoặc tự điền rồi bấm Xem lại tờ khai ạ."),
}
LT_REVIEW_STEP = {
    "md": ("📄 Đây là bước **Xem lại các tờ khai chi tiết**: cổng đã tạo các tờ khai ở các thẻ phía trên trang (khai "
           "sinh, thay đổi thông tin cư trú, BHYT…).\n\nCông dân bấm từng thẻ để rà lại; thấy sai thì bấm **Quay lại "
           "sửa tờ khai**, đúng hết thì bấm **Sang bước đính kèm** hoặc nói **“bước tiếp theo”** ạ."),
    "tts": ("Đây là bước xem lại các tờ khai chi tiết. Công dân bấm từng thẻ phía trên trang để rà lại, thấy sai thì "
            "bấm Quay lại sửa tờ khai, đúng hết thì bấm Sang bước đính kèm, hoặc nói bước tiếp theo ạ."),
}
LT_BACK_TO_FORM = {
    "md": ("✏️ Đã quay lại bước **Kê khai**. Công dân sửa xong thì bấm **Xem lại tờ khai** hoặc nói **“bước tiếp "
           "theo”** ạ."),
    "tts": "Đã quay lại bước Kê khai. Công dân sửa xong thì bấm Xem lại tờ khai, hoặc nói bước tiếp theo ạ.",
}
LT_ATTACH_NEXT = {
    "md": ("Tiếp theo là **Lựa chọn hình thức nhận kết quả**, công dân bấm nút dưới hoặc nói **“bước tiếp "
           "theo”** ạ."),
    "tts": " Tiếp theo là bước lựa chọn hình thức nhận kết quả, công dân bấm nút bên dưới hoặc nói bước tiếp theo ạ.",
}
LT_RESULT_READING = {
    "md": "📬 Đây là bước **Lựa chọn hình thức nhận kết quả**. Em đang đọc cách nhận của từng giấy tờ ạ…",
    "tts": "Đây là bước lựa chọn hình thức nhận kết quả. Em đang đọc cách nhận của từng giấy tờ ạ.",
}
LT_RESULT_SUMMARY = {
    "md": ("📬 **Cách nhận kết quả** đang chọn:\n\n{lines_md}\n\nMuốn đổi giấy nào thì bấm lựa chọn ở dòng của giấy "
           "đó bên dưới ạ."),
    "tts": "Cách nhận kết quả đang chọn: {lines_tts}. Muốn đổi giấy nào thì bấm lựa chọn ở dòng của giấy đó ạ.",
}
# Cổng chỉ có MỘT ô cách nhận kết quả (luồng 4 bước iGate các bộ): không nói "giấy nào", không lặp tên ô.
LT_RESULT_SUMMARY_ONE = {
    "md": "📬 **Cách nhận kết quả** đang chọn: **{value}**{place}.\n\nMuốn đổi thì bấm lựa chọn khác bên dưới ạ.",
    "tts": "Cách nhận kết quả đang chọn: {value}. Muốn đổi thì bấm lựa chọn khác bên dưới ạ.",
}
LT_RESULT_LINE = "- **{label}**: {value}{place}"
LT_RESULT_PLACE = " — tại {place}"
LT_RESULT_FIXED = " _(cổng đặt sẵn)_"
LT_RESULT_EMPTY = "chưa chọn"
LT_RESULT_CHANGED = {
    "md": "✓ Đã đổi **{label}** sang **{value}**.",
    "tts": "Dạ em đã đổi {label} sang {value}.",
}
LT_RESULT_FILL_HINT = {
    "md": "\n\n✍️ Công dân tự điền thêm ở mục **{label}** trên trang: **{fields}** ạ.",
    "tts": " Công dân tự điền thêm ở mục {label} trên trang các ô {fields} ạ.",
}
LT_RESULT_FAILED = {
    "md": "⚠️ Em chưa đổi được **{label}** sang **{value}**, công dân chọn tay ở ô đó trên trang giúp em ạ.",
    "tts": "Dạ em chưa đổi được {label}, công dân chọn tay ở ô đó trên trang giúp em ạ.",
}
LT_RESULT_UNREAD = {
    "md": "⚠️ Em chưa đọc được các ô cách nhận kết quả trên trang, công dân chọn tay giúp em ạ.",
    "tts": "Dạ em chưa đọc được các ô cách nhận kết quả, công dân chọn tay giúp em ạ.",
}
LT_SUBMIT_GUIDE = {
    "md": ("Cuối cùng công dân tích ô **Tôi cam đoan…**, nhập **mã kiểm tra** (chữ trong ảnh) rồi bấm **Hoàn thành** "
           "trên trang, hoặc bấm nút **Nộp hồ sơ** bên dưới để em bấm giúp ạ."),
    "tts": (" Cuối cùng công dân tích ô Tôi cam đoan, nhập mã kiểm tra trong ảnh, rồi bấm Hoàn thành trên trang, hoặc "
            "bấm nút Nộp hồ sơ để em bấm giúp ạ."),
}
LT_SUBMIT_MISSING = {
    "md": "Công dân còn thiếu: **{missing}**. Làm xong rồi bấm **Nộp hồ sơ** lại ạ.",
    "tts": "Công dân còn thiếu {missing}. Làm xong rồi bấm Nộp hồ sơ lại ạ.",
}
LT_MISSING_CAM_DOAN = "tích ô Tôi cam đoan"
LT_MISSING_CAPTCHA = "nhập mã kiểm tra"
LT_SUBMITTING = {
    "md": "Dạ em bấm **Hoàn thành** để nộp hồ sơ ạ.",
    "tts": "Dạ em bấm Hoàn thành để nộp hồ sơ ạ.",
}
LT_SUBMIT_FAILED = {
    "md": ("⚠️ Hồ sơ **chưa nộp được**{message}.\n\nCông dân kiểm tra lại (mã kiểm tra hay bị sai, bấm biểu tượng "
           "làm mới cạnh ảnh để lấy mã khác) rồi bấm **Nộp hồ sơ** lại ạ."),
    "tts": ("Dạ hồ sơ chưa nộp được. Công dân kiểm tra lại mã kiểm tra, nếu cần bấm làm mới để lấy mã khác, rồi bấm "
            "Nộp hồ sơ lại ạ."),
}
# ── Cổng Bộ Xây dựng (dvc.moc.gov.vn, wizard 4 bước, chat/bxd): mỗi bước có nút + lệnh nói "bước tiếp theo".
# Chỉ bản tiếng Việt: luồng tắt ở chế độ Mông. Thẻ cách nhận kết quả dùng chung câu LT_RESULT_*. ──
BXD_STEP_NAMES = {2: "Thành phần hồ sơ", 3: "Hình thức nhận kết quả"}
BXD_ATTACH_CHIP = "📎 Sang Thành phần hồ sơ ▶"
BXD_RESULT_CHIP = "📬 Sang hình thức nhận kết quả ▶"
BXD_RETRY_CHIP = "🔁 Thử chuyển bước lại"
BXD_SUBMIT_CHIP = "📨 Nộp hồ sơ"
BXD_MOVING = {
    "md": "Dạ em bấm **Tiếp tục** để sang **{step}** ạ.",
    "tts": "Dạ em bấm Tiếp tục để sang bước {step} ạ.",
}
# Đủ ô bắt buộc ở Thông tin hồ sơ (cùng khoá với FLOW2_PREVIEW_READY: field_review._ready dùng chung bộ tham số).
BXD_FILL_READY = {
    "md": ("✓ Tờ khai đã đủ các ô bắt buộc{optional_md}.\n\n{optional_hint_md}Công dân rà lại rồi bấm **Sang Thành "
           "phần hồ sơ** hoặc nói **“bước tiếp theo”** để em bấm Tiếp tục ạ."),
    "tts": (" Tờ khai đã đủ các ô bắt buộc{optional_tts}. {optional_hint_tts}Công dân rà lại rồi bấm Sang Thành phần "
            "hồ sơ, hoặc nói bước tiếp theo để em bấm Tiếp tục ạ."),
}
BXD_FILL_NEXT = {
    "md": ("Công dân rà lại tờ khai, ô nào sai thì sửa thẳng trên trang, xong bấm **Sang Thành phần hồ sơ** hoặc nói "
           "**“bước tiếp theo”** ạ."),
    "tts": "Công dân rà lại tờ khai, xong bấm Sang Thành phần hồ sơ, hoặc nói bước tiếp theo ạ.",
}
BXD_OPTIONAL_PHASE = {
    "md": ("✓ Đã đủ các ô bắt buộc. Em hỏi tiếp **{optional} ô không bắt buộc**; công dân muốn đi tiếp luôn thì bấm "
           "**Sang Thành phần hồ sơ** ạ."),
    "tts": ("Dạ đã đủ các ô bắt buộc. Em hỏi tiếp các ô không bắt buộc, công dân muốn đi tiếp luôn thì bấm Sang Thành "
            "phần hồ sơ ạ. "),
}
BXD_PROCEED_STEP = "cổng chưa cho sang Thành phần hồ sơ"
BXD_BLOCKED = {
    "md": "⚠️ Cổng chưa cho sang **{step}**{message}. Công dân xem lại trang rồi thử lại ạ.",
    "tts": "Dạ cổng chưa cho sang bước {step}. Công dân xem lại trang rồi thử lại ạ.",
}
BXD_BLOCKED_FORM = {
    "md": ("⚠️ Cổng chưa cho sang Thành phần hồ sơ{message}: tờ khai còn **{required} ô bắt buộc** trống (ô tô đỏ trên "
           "trang).\n\nCông dân bấm **Bổ sung các thông tin còn thiếu** để em hỏi từng ô, hoặc tự điền rồi bấm **Sang "
           "Thành phần hồ sơ** ạ."),
    "tts": ("Dạ cổng chưa cho sang Thành phần hồ sơ, tờ khai còn {required} ô bắt buộc trống. Công dân bấm Bổ sung các "
            "thông tin còn thiếu để em hỏi từng ô, hoặc tự điền rồi bấm Sang Thành phần hồ sơ ạ."),
}
BXD_BACK_TO_FORM = {
    "md": ("✏️ Đã quay lại **Thông tin hồ sơ**. Công dân sửa xong thì bấm **Sang Thành phần hồ sơ** hoặc nói **“bước "
           "tiếp theo”** ạ."),
    "tts": "Đã quay lại bước Thông tin hồ sơ. Công dân sửa xong thì bấm Sang Thành phần hồ sơ, hoặc nói bước tiếp theo ạ.",
}
BXD_ATTACH_NEXT = {
    "md": "Tiếp theo là **Hình thức nhận kết quả**, công dân bấm nút dưới hoặc nói **“bước tiếp theo”** ạ.",
    "tts": " Tiếp theo là bước hình thức nhận kết quả, công dân bấm nút bên dưới hoặc nói bước tiếp theo ạ.",
}
BXD_RESULT_READING = {
    "md": "📬 Đây là bước **Hình thức nhận kết quả**. Em đang đọc các cách nhận trên trang ạ…",
    "tts": "Đây là bước hình thức nhận kết quả. Em đang đọc các cách nhận trên trang ạ.",
}
BXD_SUBMIT_GUIDE = {
    "md": ("Cuối cùng công dân tích ô **Tôi chắc chắn…**, nhập **mã xác nhận** (chữ trong ảnh) rồi bấm **Nộp hồ sơ** "
           "trên trang, hoặc bấm nút **Nộp hồ sơ** bên dưới để em bấm giúp ạ."),
    "tts": (" Cuối cùng công dân tích ô Tôi chắc chắn, nhập mã xác nhận trong ảnh, rồi bấm Nộp hồ sơ trên trang, hoặc "
            "bấm nút Nộp hồ sơ để em bấm giúp ạ."),
}
BXD_MISSING_CAM_DOAN = "tích ô Tôi chắc chắn…"
BXD_MISSING_CAPTCHA = "nhập mã xác nhận"
BXD_SUBMIT_MISSING = {
    "md": "Công dân còn thiếu: **{missing}**. Làm xong rồi bấm **Nộp hồ sơ** lại ạ.",
    "tts": "Công dân còn thiếu {missing}. Làm xong rồi bấm Nộp hồ sơ lại ạ.",
}
BXD_SUBMITTING = {
    "md": "Dạ em bấm **Nộp hồ sơ** trên trang ạ.",
    "tts": "Dạ em bấm Nộp hồ sơ trên trang ạ.",
}
BXD_SUBMIT_FAILED = {
    "md": ("⚠️ Hồ sơ **chưa nộp được**{message}.\n\nCông dân kiểm tra lại (mã xác nhận hay bị sai, bấm nút làm mới "
           "cạnh ảnh để lấy mã khác) rồi bấm **Nộp hồ sơ** lại ạ."),
    "tts": ("Dạ hồ sơ chưa nộp được. Công dân kiểm tra lại mã xác nhận, nếu cần bấm làm mới để lấy mã khác, rồi bấm "
            "Nộp hồ sơ lại ạ."),
}
# ── Cổng Bắc Ninh (Liferay, 4 tab cùng trang, chat/bac_ninh.py): câu hỏi điền người ủy quyền ở tab Chọn cơ quan tiếp
# nhận, nút + lệnh nói "bước tiếp theo" chuyển tab, nơi nhận kết quả, nút Nộp hồ sơ. Chỉ bản tiếng Việt: luồng tắt ở
# chế độ Mông. Thẻ nơi nhận kết quả dùng chung khuôn result_methods. ──
BN_TAB_LABELS = {1: "Chọn cơ quan tiếp nhận", 2: "Nhập đơn đăng ký", 3: "Tải thành phần hồ sơ",
                 4: "Thông tin đăng ký nhận kết quả"}
# Nút đi tiếp theo tab ĐÍCH - 1 (tab 2 / 3 / 4).
BN_NEXT_CHIPS = {1: "📝 Sang Nhập đơn đăng ký ▶", 2: "📎 Sang Thành phần hồ sơ ▶",
                 3: "📬 Sang Thông tin đăng ký nhận kết quả ▶"}
BN_WHO_DEFAULT = "người ủy quyền"
BN_NEXT_DESC = "đi tiếp, sang bước / phần tiếp theo, qua {step}, ok được rồi đi tiếp"
BN_AUTHORIZED_YES_CHIP = "✍️ Điền thông tin {who}"
BN_AUTHORIZED_NO_CHIP = "➡️ Không điền, sang {step}"
BN_AUTHORIZED_YES_DESC = "có, có điền, điền đi, có {who}, có giấy ủy quyền / giấy giới thiệu"
BN_AUTHORIZED_NO_DESC = "không, không điền, không cần, không có ủy quyền, bỏ qua, sang {step} luôn"
BN_RETRY_CHIP = "🔁 Thử chuyển lại"
BN_SUBMIT_CHIP = "📨 Nộp hồ sơ"
BN_ATTACH_RETRY_CHIP = "🔁 Đính kèm lại"
BN_ATTACH_RETRYING = {
    "md": "Dạ em đính kèm lại các tệp chưa lên trang ạ…",
    "tts": "Dạ em đính kèm lại các tệp chưa lên trang ạ.",
}
BN_AGENCY_ASK = {
    "md": ("Đây là phần **Chọn cơ quan tiếp nhận**. Công dân nộp hồ sơ tại **cơ quan nào** ạ?\n\nCông dân **nói tên chi "
           "nhánh** (tên địa danh là được), bấm gợi ý bên dưới nếu có, hoặc chọn thẳng ở ô **Cơ quan tiếp nhận, giải quyết "
           "hồ sơ** trên trang."),
    "tts": ("Đây là phần chọn cơ quan tiếp nhận. Công dân nộp hồ sơ tại cơ quan nào ạ? Công dân nói tên chi nhánh, hoặc "
            "chọn thẳng trên trang."),
}
BN_AGENCY_SELECTED = {
    "md": "✓ Đã chọn cơ quan tiếp nhận: **{agency}**.\n\n",
    "tts": "Dạ đã chọn cơ quan tiếp nhận {agency}. ",
}
BN_AGENCY_FAILED = {
    "md": ("⚠️ Em chưa chọn được cơ quan này trên trang. Công dân chọn thẳng ở ô **Cơ quan tiếp nhận, giải quyết hồ "
           "sơ** giúp em ạ."),
    "tts": "Dạ em chưa chọn được cơ quan này. Công dân chọn thẳng trên trang giúp em ạ.",
}
BN_AGENCY_UNREAD = {
    "md": ("⚠️ Em chưa đọc được danh sách cơ quan tiếp nhận. Công dân chọn ở ô **Cơ quan tiếp nhận, giải quyết hồ sơ** "
           "trên trang, chọn xong em hỏi tiếp ạ."),
    "tts": "Dạ em chưa đọc được danh sách cơ quan tiếp nhận. Công dân chọn trên trang, chọn xong em hỏi tiếp ạ.",
}
BN_AUTHORIZED_ASK = {
    "md": "Công dân có điền **thông tin {who}** (khối *Thông tin trong trường hợp được ủy quyền*) không ạ?",
    "tts": "Công dân có điền thông tin {who} không ạ?",
}
BN_PART_AUTHORIZED = "khối thông tin người ủy quyền"
BN_PART_ACCOUNT = "thông tin tài khoản"
BN_ACCOUNT_INTRO = {
    "md": ("🪪 Trước khi vào thủ tục, công dân cần **hoàn thiện thông tin tài khoản** trên cổng Bắc Ninh. Em xin phép và "
           "nhận **đủ giấy tờ của thủ tục một lần** (có căn cước của chủ tài khoản) — em điền tài khoản trước, sang thủ "
           "tục em điền luôn, không hỏi lại giấy tờ."),
    "tts": ("Trước khi vào thủ tục, công dân cần hoàn thiện thông tin tài khoản. Em xin phép và nhận đủ giấy tờ của thủ "
            "tục một lần, em điền tài khoản trước, sang thủ tục em điền luôn ạ. "),
}
BN_ACCOUNT_SAVE_CHIP = "💾 Lưu và sang bước tiếp theo"
BN_ACCOUNT_SAVE_DESC = "lưu, lưu lại, lưu thông tin tài khoản, sang bước tiếp theo, đi tiếp"
BN_ACCOUNT_SAVING = {
    "md": "Dạ em bấm **Lưu** thông tin tài khoản trên trang ạ.",
    "tts": "Dạ em bấm Lưu thông tin tài khoản ạ.",
}
BN_ACCOUNT_SAVED = {
    "md": "✓ Đã lưu thông tin tài khoản. Cổng đang chuyển sang trang thủ tục, công dân chờ chút ạ…",
    "tts": "Dạ đã lưu thông tin tài khoản. Cổng đang chuyển sang trang thủ tục, công dân chờ chút ạ.",
}
BN_ACCOUNT_SAVE_FAILED = {
    "md": ("⚠️ Cổng chưa cho lưu: *{message}*.\n\nCông dân bấm **Bổ sung các thông tin còn thiếu** để em hỏi từng ô, hoặc "
           "sửa trên trang rồi bấm **Lưu và sang bước tiếp theo** lại ạ."),
    "tts": ("Dạ cổng chưa cho lưu. Công dân bấm Bổ sung các thông tin còn thiếu để em hỏi từng ô, hoặc sửa trên trang rồi "
            "bấm Lưu lại ạ."),
}
BN_ACCOUNT_STILL_HERE = "trang vẫn đang ở bước hoàn thiện thông tin tài khoản"
BN_FILL_FROM_DOCS = {
    "md": "📝 Em điền luôn từ giấy tờ công dân đã đưa ở bước tài khoản, công dân chờ chút ạ…",
    "tts": "Dạ em điền luôn từ giấy tờ công dân đã đưa, công dân chờ chút ạ.",
}
BN_PART_FORM = "đơn đăng ký"
BN_FILL_RESULT = {
    "md": "🟩 Em đã điền **{filled} ô** vào {part}.{not_found_md}",
    "tts": "Dạ em đã điền {filled} ô vào {part}.",
}
BN_FILL_NOT_FOUND = "\n\n⚠️ **{count} ô** chưa khớp được trên trang."
# Cùng khoá với FLOW2_PREVIEW_READY: field_review._ready dùng chung bộ tham số.
BN_FILL_READY = {
    "md": ("✓ Em đã điền xong phần này{optional_md}.\n\n{optional_hint_md}Công dân rà lại rồi bấm nút đi tiếp bên "
           "dưới hoặc nói **“bước tiếp theo”** ạ."),
    "tts": (" Em đã điền xong phần này{optional_tts}. {optional_hint_tts}Công dân rà lại rồi bấm nút đi tiếp bên dưới, "
            "hoặc nói bước tiếp theo ạ."),
}
BN_FILL_NEXT = {
    "md": "Công dân rà lại, ô nào sai thì sửa thẳng trên trang, xong bấm nút đi tiếp hoặc nói **“bước tiếp theo”** ạ.",
    "tts": " Công dân rà lại, xong bấm nút đi tiếp, hoặc nói bước tiếp theo ạ.",
}
BN_OPTIONAL_PHASE = {
    "md": ("Em hỏi lần lượt **{optional} ô còn trống**; ô nào không có thì công dân nói **“bỏ qua”**, muốn đi tiếp "
           "luôn thì bấm nút đi tiếp ạ."),
    "tts": ("Dạ em hỏi lần lượt các ô còn trống, ô nào không có thì công dân nói bỏ qua, muốn đi tiếp luôn thì bấm nút "
            "đi tiếp ạ. "),
}
BN_MOVING = {
    "md": "Dạ em chuyển sang **{step}** ạ.",
    "tts": "Dạ em chuyển sang phần {step} ạ.",
}
BN_TAB_BLOCKED = {
    "md": "⚠️ Em chưa chuyển được sang **{step}**. Công dân bấm thẳng tab **{step}** trên trang hoặc bấm thử lại ạ.",
    "tts": "Dạ em chưa chuyển được sang phần {step}. Công dân bấm thẳng tab đó trên trang, hoặc bấm thử lại ạ.",
}
BN_FORM_FILLING = {
    "md": "📝 Đã sang **Nhập đơn đăng ký**. Em điền đơn luôn từ giấy tờ công dân đã đưa ạ.",
    "tts": "Đã sang phần nhập đơn đăng ký. Em điền đơn luôn từ giấy tờ công dân đã đưa ạ. ",
}
BN_BACK_TO_TAB = {
    "md": "✏️ Đã quay lại **{step}**. Công dân sửa xong thì bấm nút đi tiếp hoặc nói **“bước tiếp theo”** ạ.",
    "tts": "Đã quay lại phần {step}. Công dân sửa xong thì bấm nút đi tiếp, hoặc nói bước tiếp theo ạ.",
}
BN_ATTACHING = {
    "md": "📎 Đã sang **Tải thành phần hồ sơ**. Em đang xếp giấy tờ vào từng thành phần, công dân chờ chút ạ…",
    "tts": "Đã sang phần tải thành phần hồ sơ. Em đang xếp giấy tờ vào từng thành phần, công dân chờ chút ạ.",
}
BN_ATTACHED_ALREADY = {
    "md": "📎 Giấy tờ đã đính ở **Tải thành phần hồ sơ**. Công dân bấm nút dưới hoặc nói **“bước tiếp theo”** ạ.",
    "tts": "Dạ giấy tờ đã đính rồi. Công dân bấm nút bên dưới, hoặc nói bước tiếp theo ạ.",
}
BN_ATTACH_NEXT = {
    "md": "Tiếp theo là **Thông tin đăng ký nhận kết quả**, công dân bấm nút dưới hoặc nói **“bước tiếp theo”** ạ.",
    "tts": " Tiếp theo là phần thông tin đăng ký nhận kết quả, công dân bấm nút bên dưới hoặc nói bước tiếp theo ạ.",
}
BN_RESULT_READING = {
    "md": "📬 Đây là **Thông tin đăng ký nhận kết quả**. Em đang đọc nơi nhận kết quả trên trang ạ…",
    "tts": "Đây là phần thông tin đăng ký nhận kết quả. Em đang đọc nơi nhận kết quả trên trang ạ.",
}
BN_RESULT_SUMMARY = {
    "md": ("Nơi nhận kết quả đang là **{label}**. Công dân chọn nơi khác ở thẻ dưới nếu muốn, xong bấm **Nộp hồ sơ** "
           "để em bấm Nộp hồ sơ trên trang ạ."),
    "tts": (" Nơi nhận kết quả đang là {label}. Công dân chọn nơi khác nếu muốn, xong bấm Nộp hồ sơ để em nộp giúp "
            "ạ."),
}
BN_POINT_ASK = {
    "md": ("Nhận kết quả **Tại nơi nộp hồ sơ**: công dân chọn **điểm tiếp nhận** muốn đến nhận kết quả ở thẻ dưới (nói "
           "tên điểm hoặc chọn thẳng trên trang), xong bấm **Nộp hồ sơ** ạ."),
    "tts": ("Nhận kết quả tại nơi nộp hồ sơ, công dân chọn điểm tiếp nhận muốn đến nhận kết quả, nói tên điểm hoặc chọn "
            "trên trang, xong bấm Nộp hồ sơ ạ."),
}
BN_POSTAL_STEP = "gửi hồ sơ / nhận kết quả qua bưu chính công ích"
BN_POSTAL_STEP_CHIP = "📬 Chọn gửi / nhận kết quả qua bưu điện ▶"
BN_TWO_TAB_ATTACH_NEXT = {
    "md": ("Tiếp theo là **gửi hồ sơ / nhận kết quả qua bưu chính công ích** (ở phần Chọn cơ quan tiếp nhận), công dân "
           "bấm nút dưới hoặc nói **“bước tiếp theo”** ạ."),
    "tts": " Tiếp theo là phần gửi hồ sơ và nhận kết quả qua bưu chính, công dân bấm nút bên dưới hoặc nói bước tiếp theo ạ.",
}
BN_POSTAL_READING = {
    "md": "📬 Đây là phần **gửi hồ sơ và nhận kết quả qua bưu chính công ích**. Em đang đọc trên trang ạ…",
    "tts": "Đây là phần gửi hồ sơ và nhận kết quả qua bưu chính. Em đang đọc trên trang ạ.",
}
BN_POSTAL_BOTH_CHIP = "Cả hai"
BN_POSTAL_BOTH_DESC = "cả hai, gửi hồ sơ và nhận kết quả đều qua bưu điện"
BN_POSTAL_ASK = {
    "md": ("Công dân muốn **gửi hồ sơ** qua bưu điện, **nhận kết quả** qua bưu điện, hay **cả hai** ạ? Công dân chọn ở "
           "nút dưới hoặc nói giúp em."),
    "tts": "Công dân muốn gửi hồ sơ qua bưu điện, nhận kết quả qua bưu điện, hay cả hai ạ?",
}
BN_POSTAL_DONE = {
    "md": ("✓ Đã chọn **{labels}**. Công dân điền thông tin ở khối tương ứng trên trang (họ tên, số điện thoại, tỉnh, "
           "phường/xã, địa chỉ liên hệ) rồi bấm **Nộp hồ sơ** ạ."),
    "tts": ("Dạ đã chọn {labels}. Công dân điền họ tên, số điện thoại, tỉnh, phường xã và địa chỉ liên hệ trên trang, "
            "rồi bấm Nộp hồ sơ ạ."),
}
BN_POSTAL_MISSING = {
    "md": ("⚠️ Công dân chưa chọn **gửi hồ sơ** hay **nhận kết quả** qua bưu điện. Công dân chọn ở nút dưới, điền thông "
           "tin trên trang rồi bấm **Nộp hồ sơ** lại ạ."),
    "tts": ("Dạ công dân chưa chọn gửi hồ sơ hay nhận kết quả qua bưu điện. Công dân chọn xong, điền thông tin rồi bấm "
            "Nộp hồ sơ lại ạ."),
}
BN_POSTAL_FAILED = {
    "md": ("⚠️ Em chưa tích được trên trang. Công dân tích thẳng ô **Gửi hồ sơ qua bưu điện** / **Nhận kết quả qua bưu "
           "điện** giúp em ạ."),
    "tts": "Dạ em chưa tích được trên trang. Công dân tích thẳng ô gửi hồ sơ hoặc nhận kết quả qua bưu điện giúp em ạ.",
}
BN_POINT_MISSING = {
    "md": ("⚠️ Công dân chưa chọn **điểm tiếp nhận** để nhận kết quả. Công dân chọn ở thẻ dưới hoặc trên trang rồi bấm "
           "**Nộp hồ sơ** lại ạ."),
    "tts": "Dạ công dân chưa chọn điểm tiếp nhận để nhận kết quả. Công dân chọn xong rồi bấm Nộp hồ sơ lại ạ.",
}
BN_RESULT_UNREAD = {
    "md": "⚠️ Em chưa đọc được nơi nhận kết quả trên trang. Công dân chọn tay trên trang rồi bấm **Nộp hồ sơ** ạ.",
    "tts": "Dạ em chưa đọc được nơi nhận kết quả. Công dân chọn tay trên trang rồi bấm Nộp hồ sơ ạ.",
}
BN_RESULT_CHANGED = {
    "md": "✓ Đã chọn nhận kết quả **{label}**. ",
    "tts": "Dạ đã chọn nhận kết quả {label}. ",
}
BN_RESULT_ADDRESS_HINT = {
    "md": " Công dân điền **địa chỉ nhận** (họ tên, số điện thoại, tỉnh, xã, địa chỉ) ngay trên trang rồi bấm **Nộp hồ sơ** ạ.",
    "tts": " Công dân điền địa chỉ nhận ngay trên trang rồi bấm Nộp hồ sơ ạ.",
}
BN_RESULT_FAILED = {
    "md": "⚠️ Em chưa chọn được **{label}**. Công dân bấm chọn thẳng trên trang giúp em ạ.",
    "tts": "Dạ em chưa chọn được {label}. Công dân bấm chọn thẳng trên trang giúp em ạ.",
}
BN_SUBMITTING = {
    "md": "Dạ em bấm **Nộp hồ sơ** trên trang ạ.",
    "tts": "Dạ em bấm Nộp hồ sơ trên trang ạ.",
}
BN_SUBMIT_SENT = {
    "md": "📨 Em đã bấm **Nộp hồ sơ**. Công dân chờ cổng chuyển sang trang hồ sơ đã nộp ạ.",
    "tts": "Dạ em đã bấm Nộp hồ sơ. Công dân chờ cổng chuyển sang trang hồ sơ đã nộp ạ.",
}
BN_SUBMIT_FAILED = {
    "md": "⚠️ Hồ sơ **chưa nộp được**{message}.\n\nCông dân xem lại các phần trên trang rồi bấm **Nộp hồ sơ** lại ạ.",
    "tts": "Dạ hồ sơ chưa nộp được. Công dân xem lại các phần trên trang rồi bấm Nộp hồ sơ lại ạ.",
}
FLOW2_NEXT_RESULT_STEP = {
    "md": "Tiếp theo là **{result_step}**, công dân bấm nút dưới hoặc nói **“bước tiếp theo”** ạ.",
    "tts": " Tiếp theo là bước {result_step}, công dân bấm nút bên dưới hoặc nói bước tiếp theo ạ.",
}
FLOW2_NEXT_SUBMIT = {
    "md": "Công dân rà lại lần cuối rồi tự bấm **Nộp hồ sơ / Gửi hồ sơ** trên trang ạ.",
    "tts": " Công dân rà lại lần cuối rồi tự bấm nộp hồ sơ trên trang ạ.",
}
FLOW2_REVIEW_DONE_LEAD = ("✓ Em đã hỏi hết các ô còn trống. ", "Dạ em đã hỏi hết các ô còn trống. ")
FLOW2_REVIEW_STOP_LEAD = ("Dạ, em dừng hỏi. ", "Dạ em dừng hỏi. ")

# Nhãn bước hiển thị trên thanh tiến trình (progress.label) — khớp docs/03a §3.
STEP_LABELS = {
    "greet": "Chọn thủ tục",
    "confirm_procedure": "Xác nhận thủ tục",
    "choose_variant": "Chọn trường hợp",
    "guide_login": "Đăng nhập VNeID",
    "choose_mae_dialog": "Chọn nơi xử lý, trường hợp",
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

BCA_AGENCY_STEP_LABEL = "Chọn cơ quan thực hiện"

# Thứ tự bước cho progress.step (1-based).
STEP_ORDER = [
    "greet", "confirm_procedure", "choose_variant", "guide_login", "choose_mae_dialog", "consent",
    "ask_doc_method", "qr_waiting", "collecting_docs", "choosing_attach_mode", "owner_filling",
    "owner_waiting_next", "filling", "reviewing", "attaching", "done",
]


# ── Giọng nói toàn trình ─────────────────────────────────────────────────────────────────────
# Nhãn cho các nút TRÊN CARD khi đưa vào danh sách "nút đang hiện" của bộ phân loại (chip thì dùng
# chính nhãn chip). Chỉ dành cho LLM + câu "nói được gì", không hiển thị thành nút.
VOICE_CONSENT_AGREE = "Đồng ý cho xử lý dữ liệu và tự động điền"
VOICE_CONSENT_DECLINE = "Không đồng ý, tự nhập"
VOICE_DOC_OPTION = {
    "qr": "Chụp giấy tờ bằng điện thoại (quét mã QR)",
    "scan": "Scan tại quầy hoặc chọn tệp có sẵn trong máy",
}

OWNER_RESEND_DOCS_CTA = "📷 Gửi lại giấy tờ"

# Câu gõ/nói không ra việc gì ở bước đang làm. options_* là nhãn các nút đang hiện.
VOICE_NOT_UNDERSTOOD = {
    "md": "Em chưa hiểu ý ạ. Công dân nói lại ngắn gọn, hoặc bấm nút trên màn hình.",
    "tts": "Dạ, em chưa hiểu. Công dân nói lại ngắn gọn, hoặc bấm nút trên màn hình ạ.",
}
VOICE_NOT_UNDERSTOOD_OPTIONS = {
    "md": "Em chưa hiểu ý ạ. Ở bước này công dân có thể nói: {options_md}.",
    "tts": "Dạ, em chưa hiểu. Công dân có thể nói: {options_tts}.",
}

# Sửa nơi làm bằng lời: tên xã nghe được khớp nhiều xã / không trọn tên. options_* là tên xã.
PLACE_WARD_UNCLEAR = {
    "md": "Dạ, phường/xã nào ạ?\n\n{options_md}",
    "tts": "Dạ, có phải {options_tts} không ạ? Công dân bấm chọn, hoặc nói lại tên xã.",
}
PLACE_NOT_HEARD = {
    "md": "Dạ em chưa nghe rõ ạ. Công dân nói lại **tên phường/xã** hoặc **làm cho ai**, hoặc chọn bên dưới.",
    "tts": "Dạ, em chưa nghe rõ. Công dân nói lại tên phường xã, hoặc làm thủ tục cho ai ạ.",
}

# ── Bổ sung ô còn trống ngay trên tờ khai eForm (chat/field_review) ──
# Chỉ chạy ở chế độ tiếng Việt: nhãn ô lấy NGUYÊN VĂN từ tờ khai nên chưa có bản Mông.
# Lời đọc KHÔNG ngắt dấu phẩy thành mẩu quá ngắn (TTS dễ đọc vấp); *_tts của nhãn đã bỏ dấu phẩy và "/".
# Mỗi bong bóng một thông tin: kết quả ô trước / lời mở đầu / câu hỏi ô kế tiếp hiện riêng.
FR_CHIP = "📝 Bổ sung các thông tin còn thiếu"
FR_SKIP_CHIP = "⏭️ Bỏ qua ô này"
FR_STOP_CHIP = "⏹️ Dừng bổ sung"
FR_BACK_CHIP = "↩️ Sửa ô vừa điền"
FR_RELOAD_CHIP = "🔄 Tải lại danh sách xã"
# Bước Thông tin chủ hồ sơ đã đủ ô bắt buộc (cổng đổ sẵn từ tài khoản): chưa xin giấy tờ ở đây, sang Kê khai trước.
FR_OWNER_CTA = "Xong, sang bước điền tờ khai →"
# Bước cuối của Kê khai: trợ lý bấm "Xem trước" rồi "Xác nhận" trên cổng thay công dân.
FR_PREVIEW_CHIP = "👁 Xem trước tờ khai"
FR_CONFIRM_CTA = "Xác nhận, sang Thành phần hồ sơ →"
FR_PREVIEW_CLOSE_CHIP = "✏️ Sửa lại tờ khai"
# Vòng hỏi (luồng bản 2) hỏi ô bắt buộc trước; hết ô bắt buộc, sang ô không bắt buộc → báo một lần + nút đi tiếp.
FR_OPTIONAL_PHASE_LEGACY = {
    "md": ("✓ Đã đủ các ô bắt buộc. Em hỏi tiếp **{optional} ô không bắt buộc**; công dân muốn xem luôn thì bấm "
           "**Xem trước tờ khai** ạ."),
    "tts": ("Dạ đã đủ các ô bắt buộc. Em hỏi tiếp các ô không bắt buộc, công dân muốn xem luôn thì bấm Xem trước tờ "
            "khai ạ. "),
}
FR_OPTIONAL_PHASE_SINGLE = {
    "md": ("✓ Đã đủ các ô bắt buộc. Em hỏi tiếp **{optional} ô không bắt buộc**; công dân muốn đi tiếp luôn thì bấm "
           "**Chọn hình thức nhận kết quả** hoặc **Lưu và nộp hồ sơ** ạ."),
    "tts": ("Dạ đã đủ các ô bắt buộc. Em hỏi tiếp các ô không bắt buộc, công dân muốn đi tiếp luôn thì bấm Chọn hình "
            "thức nhận kết quả hoặc Lưu và nộp hồ sơ ạ. "),
}
# Giữa vòng hỏi công dân đòi xem trước / sang bước tiếp mà còn ô bắt buộc trống → báo rồi hỏi tiếp ô đang dở.
FR_PROCEED_BLOCKED = {
    "md": ("Tờ khai còn **{required} ô bắt buộc** chưa có thông tin nên {step_md} ạ. Em hỏi tiếp ô **{label}** nhé, "
           "công dân không biết thì nói **bỏ qua**, hoặc nói **dừng** để tự điền trên tờ khai."),
    "tts": ("Dạ tờ khai còn {required} ô bắt buộc chưa có thông tin nên {step_md} ạ. Em hỏi tiếp ô {label_tts} nhé, "
            "công dân không biết thì nói bỏ qua, hoặc nói dừng để tự điền trên tờ khai."),
}
FR_PROCEED_STEP_LEGACY = "cổng chưa cho xem trước"
FR_PROCEED_STEP_SINGLE = "chưa sang bước nhận kết quả được"
FR_PREVIEW_OPENING = {
    "md": "Dạ em bấm **Xem trước** để mở tờ khai ạ.",
    "tts": "Dạ em bấm Xem trước để mở tờ khai ạ.",
}
FR_PREVIEW_OPEN = {
    "md": ("👁 Tờ khai đang mở để công dân xem lại.\n\nĐúng hết rồi thì bấm **Xác nhận, sang Thành phần hồ sơ**, "
           "qua trang đó em tự đính kèm ạ. Cần sửa thì bấm **Sửa lại tờ khai**."),
    "tts": ("Tờ khai đang mở để công dân xem lại. Đúng hết rồi thì công dân bấm xác nhận để sang thành phần hồ sơ "
            "và em sẽ tự đính kèm. Cần sửa thì công dân bấm sửa lại tờ khai ạ."),
}
FR_PREVIEW_MISSING = {
    "md": ("⚠️ Cổng chưa cho xem trước vì còn **{count} ô bắt buộc** chưa điền (ô đỏ trên tờ khai).\n\n"
           "Công dân bấm **Bổ sung các thông tin còn thiếu** để em hỏi từng ô ạ."),
    "tts": ("Cổng chưa cho xem trước vì còn {count} ô bắt buộc chưa điền. "
            "Công dân bấm bổ sung các thông tin còn thiếu để em hỏi từng ô ạ."),
}
FR_PREVIEW_FAILED = {
    "md": "⚠️ Em chưa mở được bản xem trước{message}. Công dân bấm thử lại hoặc bấm **Xem trước** ngay trên trang giúp em.",
    "tts": "Em chưa mở được bản xem trước. Công dân bấm thử lại hoặc bấm Xem trước ngay trên trang giúp em ạ.",
}
FR_CONFIRMING = {
    "md": "Dạ em bấm **Xác nhận** để sang **Thành phần hồ sơ** ạ.",
    "tts": "Dạ em bấm xác nhận để sang thành phần hồ sơ ạ.",
}
FR_CONFIRM_FAILED = {
    "md": "⚠️ Trang chưa chuyển sang Thành phần hồ sơ{message}. Công dân bấm thử lại giúp em ạ.",
    "tts": "Trang chưa chuyển sang thành phần hồ sơ. Công dân bấm thử lại giúp em ạ.",
}
FR_PREVIEW_CLOSED = {
    "md": "Dạ em đã đóng bản xem trước. Công dân sửa trực tiếp trên tờ khai{review_md}, xong bấm **Xem trước tờ khai** ạ.",
    "tts": "Dạ em đã đóng bản xem trước. Công dân sửa trực tiếp trên tờ khai{review_tts}, rồi bấm xem trước tờ khai ạ.",
}
# Tờ khai còn ô trống: sửa xong bản xem trước vẫn quay lại được vòng hỏi từng ô.
FR_PREVIEW_CLOSED_REVIEW = {
    "md": " hoặc bấm **Bổ sung các thông tin còn thiếu** để em hỏi từng ô",
    "tts": " hoặc bấm bổ sung các thông tin còn thiếu để em hỏi từng ô",
}
FR_OWNER_READY = {
    "md": ("✓ **Thông tin chủ hồ sơ** đã đủ.\n\nCông dân đọc và sửa lại nếu cần, sau đó bấm **\"Bước tiếp theo\"** "
           "hoặc bấm nút bên dưới để sang **Kê khai thông tin** ạ."),
    "tts": ("Dạ thông tin chủ hồ sơ đã đủ. Công dân đọc và sửa lại nếu cần rồi bấm Bước tiếp theo "
            "hoặc bấm nút bên dưới để sang bước kê khai thông tin ạ."),
}
# Nối sau OWNER_FILL_DONE (note=) khi bước chủ hồ sơ có nút sang Kê khai.
FR_OWNER_FILLED_NOTE = {
    "md": "\n\nHoặc bấm nút bên dưới, em chuyển sang **Kê khai thông tin** giúp ạ.",
    "tts": " Hoặc bấm nút bên dưới để em chuyển sang bước kê khai thông tin ạ.",
}
FR_OWNER_BLOCKED = {
    "md": "⚠️ Trang chưa cho sang bước kê khai{message}.\n\nCông dân kiểm tra các ô có dấu ***** rồi bấm lại nút dưới ạ.",
    "tts": "Dạ trang chưa cho sang bước kê khai. Công dân kiểm tra các ô có dấu sao rồi bấm lại nút bên dưới ạ.",
}
# Câu khi dữ liệu điền về (thay FILL_READY): màu ô là xanh / cam / đỏ, không còn ô vàng.
FR_FILL_READY = {
    "md": "✓ Đã đọc **{count} thông tin**, đang điền vào tờ khai bên trái.",
    "tts": "Dạ em đã đọc xong giấy tờ và đang điền vào tờ khai. Công dân chờ em một chút ạ.",
}
# Bong bóng riêng sau báo cáo điền khi tờ khai còn ô trống.
FR_FILL_STATS = {
    "md": ("🟩 **{filled}** ô đã điền · 🟧 **{optional}** ô không bắt buộc còn trống · 🟥 **{required}** ô bắt buộc "
           "còn trống\n\nCòn **{empty} ô trống** → bấm **Bổ sung các thông tin còn thiếu** để em hỏi từng ô ạ."),
    "tts": " Trên tờ khai còn {empty} ô trống. Công dân bấm nút Bổ sung các thông tin còn thiếu để em hỏi lần lượt từng ô ạ.",
}
# Trang nộp một trang (tư pháp mới): điền xong là tự đính kèm → báo số ô trước, mời bổ sung khi đính xong.
FR_FILL_STATS_WAIT = {
    "md": ("🟩 **{filled}** ô đã điền · 🟧 **{optional}** ô không bắt buộc còn trống · 🟥 **{required}** ô bắt buộc "
           "còn trống\n\nĐính kèm xong em mời công dân bổ sung các ô trống ạ."),
    "tts": " Trên tờ khai còn {empty} ô trống, đính kèm xong em sẽ mời công dân bổ sung ạ.",
}
FR_OFFER_AFTER_ATTACH = {
    "md": ("📝 Tờ khai còn **{empty} ô trống** ({required} ô bắt buộc) → bấm **Bổ sung các thông tin còn thiếu** để "
           "em hỏi từng ô ạ."),
    "tts": " Tờ khai còn {empty} ô trống, công dân bấm Bổ sung các thông tin còn thiếu để em hỏi từng ô ạ.",
}
FR_START = {
    "md": "Em hỏi lần lượt từng ô còn trống từ trên xuống ạ. Ô nào không có thông tin thì công dân nói **bỏ qua**.",
    "tts": "Em sẽ hỏi lần lượt từng ô còn trống. Ô nào không có thông tin thì công dân nói bỏ qua ạ. ",
}
# Câu hỏi ô kế tiếp. head_*: dòng mở đầu FR_HEAD (hoặc FR_HEAD_NO_PART cho ô không thuộc phần nào trên tờ khai).
FR_ASK = {
    "md": "{head_md}📝 {badge}Ô **{label}**{current_md}\n\nCông dân nói hoặc gõ giúp em ạ.",
    "tts": "{head_tts}Công dân nói hoặc gõ giúp em ạ.",
}
# lead: "Đầu tiên là" (ô đầu của vòng) / "Tiếp theo đến" (các ô sau).
# Dấu phẩy sau tên phần: tên phần dài nối thẳng vào "ô …" nghe liền một cụm, khó tách phần với ô.
FR_HEAD = {"md": "{lead} phần **{where}**\n\n", "tts": "{lead} phần {where_tts}, ô {label_tts}. "}
FR_HEAD_NO_PART = {"md": "{lead}:\n\n", "tts": "{lead} ô {label_tts}. "}
# Quay lại sửa một ô: bong bóng trên đã nói "Quay lại ô … để sửa" → không nhắc lại phần / tên ô.
FR_HEAD_BACK = {"md": "", "tts": ""}
FR_LEAD_FIRST = "Đầu tiên là"
FR_LEAD_NEXT = "Tiếp theo đến"
FR_CURRENT_MD = "\n\nĐang điền: **{value}**"
# Ô ít lựa chọn (≤ 6): đọc luôn các lựa chọn và hiện nút bấm chọn. choices_* là nhãn NGUYÊN VĂN trên tờ khai.
FR_ASK_CHOICES = {
    "md": ("{head_md}📝 {badge}Ô **{label}**{current_md}\n\n{choices_md}\n\n"
           "Công dân bấm chọn bên dưới, hoặc nói / gõ giúp em ạ."),
    "tts": ("{head_tts}Công dân chọn {choices_tts} ạ. "
            "Công dân bấm chọn bên dưới hoặc nói hoặc gõ giúp em."),
}
# Ô Quốc gia / Quốc tịch (danh sách cả trăm nước): hỏi Việt Nam hay nước khác.
FR_ASK_COUNTRY = {
    "md": "{head_md}📝 {badge}Ô **{label}**{current_md}\n\nCông dân nói hoặc gõ tên nước giúp em ạ.",
    "tts": "{head_tts}Công dân nói hoặc gõ tên nước giúp em ạ.",
}
# Ô Xã: Tỉnh đã có nhưng cổng không nạp danh sách xã (extension đã tự chọn lại tỉnh mà vẫn rỗng).
FR_ASK_WARDS_FAILED = {
    "md": ("{head_md}📝 {badge}Ô **{label}**\n\n⚠️ Cổng chưa tải được danh sách xã của **{province}**. "
           "Công dân bấm **Tải lại danh sách xã** hoặc bỏ qua ô này ạ."),
    "tts": ("{head_tts}Cổng chưa tải được danh sách xã của {province_tts}. "
            "Công dân bấm tải lại danh sách xã hoặc bỏ qua ô này giúp em."),
}
FR_APPLIED = {
    "md": "✓ Đã điền **{label}** · *{where}*: {value}",
    # Chữ đã ghi tên ô + giá trị; đọc lại cả phần lẫn ô trước câu hỏi ô kế tiếp thì quá dài.
    "tts": "Dạ em đã điền xong. ",
}
FR_APPLIED_NO_PART = {
    "md": "✓ Đã điền **{label}**: {value}",
    "tts": "Dạ em đã điền xong. ",
}
# Ô Đề nghị cấp bản sao: nói kèm số bản thì chọn Có rồi điền luôn ô số lượng (hiện sau khi chọn Có).
FR_COPY_COUNT_HINT = {
    "md": "\n\nCần bản sao thì nói luôn số bản, vd **\"có, 2 bản\"** ạ.",
    "tts": " Cần bản sao thì công dân nói luôn số bản, ví dụ có, hai bản ạ.",
}
FR_COPY_VALUE = "{choice}, {count} bản"
# Ô tích có lựa chọn "Khác" kèm ô ghi chữ: ô ghi chữ chỉ hiện sau khi tích nên phải nghe luôn phần cụ thể.
FR_OTHER_TEXT_HINT = {
    "md": "\n\nNếu là **{option}** thì công dân nói rõ luôn cụ thể là gì giúp em ạ.",
    "tts": " Nếu là {option_tts} thì công dân nói rõ luôn cụ thể là gì giúp em ạ.",
}
FR_OTHER_VALUE = "{choice}: {text}"
FR_COPY_COUNT_FAILED = {
    "md": "✓ Đã điền **{label}**: {choice} · ⚠️ chưa điền được số lượng bản sao, em sẽ hỏi lại ô số lượng ạ.",
    "tts": "Dạ em đã chọn {choice} nhưng chưa điền được số lượng bản sao, em sẽ hỏi lại ô số lượng ạ. ",
}
FR_APPLY_FAILED = {
    "md": "⚠️ Em chưa điền được ô **{label}**, công dân điền tay trên trang giúp em.",
    "tts": "Em chưa điền được ô {label_tts} nên công dân điền tay trên trang giúp em. ",
}
FR_SKIPPED = {
    "md": "↷ Bỏ qua ô **{label}**.",
    "tts": "Dạ em bỏ qua ô {label_tts}. ",
}
FR_BACK = {
    "md": "↩️ Quay lại ô **{label}** để sửa.",
    "tts": "Dạ em quay lại ô {label_tts} để công dân sửa. ",
}
FR_NO_BACK = {
    "md": "Chưa có ô nào vừa điền để sửa ạ.",
    "tts": "Dạ hiện chưa có ô nào vừa điền để sửa. ",
}
FR_UNCLEAR = {
    "md": "Em chưa nghe rõ ạ. Công dân nói lại **{label}**{hint} giúp em.",
    "tts": "Dạ em chưa nghe rõ. Công dân nói lại ô {label_tts} giúp em ạ.",
}
# Ô số (điện thoại, số định danh, số giấy tờ): nghe được dãy số nhưng thiếu / thừa chữ số.
FR_DIGITS_SHORT = {
    "md": "Em nghe được **{count} số** ({heard}), ô **{label}** cần đủ **{need} số** ạ. Công dân đọc lại chậm "
          "từng số giúp em.",
    "tts": "Dạ em mới nghe được {count} số, ô {label_tts} cần đủ {need} số. Công dân đọc lại chậm từng số giúp em ạ.",
}
# Ô số điện thoại: đọc đủ số chữ số nhưng không bắt đầu bằng số 0 → sai dạng, không phải thiếu số.
FR_PHONE_FORMAT = {
    "md": "Em nghe được **{heard}**, nhưng **{label}** phải **bắt đầu bằng số 0** ạ. Công dân đọc lại cả số, bắt đầu "
          "từ số 0 giúp em.",
    "tts": "Dạ em nghe được số này, nhưng {label_tts} phải bắt đầu bằng số không. Công dân đọc lại cả số, bắt đầu từ số "
           "không giúp em ạ.",
}
FR_DATE_HINT = " (đủ ngày, tháng, năm, vd 12/04/1978)"
FR_YEAR_HINT = " (ngày, tháng, năm, hoặc chỉ năm, vd 1978)"
FR_PARTIAL_DATE_HINT = " (ngày tháng năm, tháng năm, hoặc chỉ năm, vd 05/03/1978, 03/1978 hoặc 1978)"
FR_OPTION_HINT = " (đúng một lựa chọn trong danh sách của ô)"
# Hết ô trống / công dân dừng. missing_note: còn ô bắt buộc chưa có thông tin.
FR_DONE = {
    "md": ("✓ Em đã hỏi hết các ô còn trống.{missing_note}\n\nCông dân kiểm tra lại tờ khai, sau đó bấm **Xem trước** để xem trước tờ khai đã điền, nếu đúng rồi thì "
           "bấm **Xác nhận** để chuyển sang **Thành phần hồ sơ**, qua trang đó em tự đính kèm ạ."),
    "tts": ("Dạ em đã hỏi xong các ô còn trống. Công dân kiểm tra lại tờ khai rồi bấm Xem trước để xem tờ khai đã điền. "
            "Nếu đúng rồi thì công dân bấm Xác nhận để chuyển sang thành phần hồ sơ và em sẽ tự đính kèm ạ."),
}
FR_STOPPED = {
    "md": ("Dạ, em dừng hỏi các ô còn lại.{missing_note}\n\nCông dân kiểm tra lại tờ khai, sau đó bấm **Xem trước** để xem trước tờ khai đã điền, nếu đúng rồi thì "
           "bấm **Xác nhận** để chuyển sang **Thành phần hồ sơ**, qua trang đó em tự đính kèm ạ."),
    "tts": ("Dạ em dừng hỏi các ô còn lại. Công dân kiểm tra lại tờ khai rồi bấm Xem trước để xem tờ khai đã điền. "
            "Nếu đúng rồi thì công dân bấm Xác nhận để chuyển sang thành phần hồ sơ và em sẽ tự đính kèm ạ."),
}
FR_DONE_SINGLE_PAGE = {
    "md": ("✓ Em đã hỏi hết các ô còn trống.{missing_note}\n\nCông dân kiểm tra lại tờ khai, sau đó bấm **Chọn hình "
           "thức nhận kết quả** để chọn cách nhận kết quả rồi **Lưu và nộp hồ sơ** ạ."),
    "tts": ("Dạ em đã hỏi xong các ô còn trống. Công dân kiểm tra lại tờ khai, sau đó bấm Chọn hình thức nhận kết quả "
            "rồi Lưu và nộp hồ sơ ạ."),
}
FR_STOPPED_SINGLE_PAGE = {
    "md": ("Dạ, em dừng hỏi các ô còn lại.{missing_note}\n\nCông dân kiểm tra lại tờ khai, sau đó bấm **Chọn hình "
           "thức nhận kết quả** để chọn cách nhận kết quả rồi **Lưu và nộp hồ sơ** ạ."),
    "tts": ("Dạ em dừng hỏi các ô còn lại. Công dân kiểm tra lại tờ khai, sau đó bấm Chọn hình thức nhận kết quả "
            "rồi Lưu và nộp hồ sơ ạ."),
}
FR_MISSING_NOTE = " Còn **{count} ô bắt buộc** chưa có thông tin."

# ── Hỏi bổ sung ô còn trống ở bước Thông tin chủ hồ sơ (chat/owner_review.py) ──────────────────────────────
# Chỉ bật ở tiếng Việt (chế độ Mông giữ câu "công dân tự điền" cũ) nên chưa có twin bên script_mong.
OR_FILLED = {"md": "✓ Đã điền **{completed}** từ giấy tờ.", "tts": "Dạ, em đã điền {completed}. "}
OR_START = {
    "md": "Còn **{count} thông tin** giấy tờ không ghi, em hỏi nhanh ạ. Không có thì công dân nói **bỏ qua**.",
    "tts": "Còn {count} thông tin giấy tờ không ghi, em hỏi nhanh ạ. ",
}
OR_QUESTIONS = {
    "issueDate": {"md": "**Ngày cấp** căn cước là ngày nào ạ?", "tts": "Ngày cấp căn cước là ngày nào ạ?"},
    "issuePlace": {"md": "**Nơi cấp** căn cước là cơ quan nào ạ?", "tts": "Nơi cấp căn cước là cơ quan nào ạ?"},
    "phoneNumber": {"md": "**Số điện thoại** của công dân là số nào ạ?",
                    "tts": "Số điện thoại của công dân là số nào ạ?"},
    "detailedAddress": {"md": "**Địa chỉ chi tiết** (số nhà, đường, thôn/tổ…) của công dân là gì ạ?",
                        "tts": "Địa chỉ chi tiết của công dân là gì ạ?"},
}
OR_ASK = {"md": "📝 {question_md}\n\nCông dân nói hoặc gõ giúp em ạ.", "tts": "{question_tts} Công dân nói hoặc gõ giúp em."}
# Nhãn ngắn trên nút, cùng thứ tự với ISSUE_PLACE_OPTIONS (owner_info/schema.py) — nút gửi số thứ tự, không gửi chữ.
OR_ISSUE_PLACE_CHIPS = (
    "Cục CS ĐKQL cư trú và DLQG về dân cư",
    "Cục CS QLHC về TTXH",
    "Bộ Công an",
    "Cục Quản lý xuất nhập cảnh",
)
OR_STOP_CHIP = "⏹️ Để công dân tự điền trên trang"
OR_APPLYING = {"md": "✓ **{label}**: {value}", "tts": "Dạ, em điền {label}. "}
OR_ISSUE_PLACE_DERIVED = {
    "md": "\n\n✓ **Nơi cấp** theo ngày cấp: {place} — sai thì công dân sửa trên trang giúp em.",
    "tts": "Nơi cấp em điền theo ngày cấp, sai thì công dân sửa trên trang giúp em. ",
}
OR_COMPLETE = {"md": "✓ **Thông tin chủ hồ sơ** đã đủ.", "tts": "Dạ, thông tin chủ hồ sơ đã đủ."}
OR_LEFT = {
    "md": "Còn thiếu **{missing}**, công dân tự điền trên trang giúp em.",
    "tts": "Dạ, còn thiếu {missing}, công dân tự điền trên trang giúp em.",
}
OR_NEXT_HINT = {
    "md": "\n\nCông dân đọc lại, còn sửa gì cứ sửa trên trang → bấm nút dưới để sang **{attachment_step}** ạ.",
    "tts": " Công dân đọc lại, còn sửa gì cứ sửa, rồi bấm nút bên dưới ạ.",
}
# Thủ tục tư pháp form cũ: bước sau chủ hồ sơ là Kê khai (tên bước đúng chữ trên cổng).
OR_DECLARATION_STEP = "Kê khai thông tin"
OR_SAVE_CHIP = "💾 Lưu vào Thông tin định danh của công dân"
OR_SAVED = {
    "md": "✓ Đã lưu vào **Thông tin định danh** của công dân — lần sau cổng tự điền sẵn.\n\nBấm nút dưới để sang bước tiếp ạ.",
    "tts": "Dạ, em đã lưu vào thông tin định danh của công dân. Bấm nút bên dưới để sang bước tiếp ạ.",
}
OR_SAVE_FAILED = {
    "md": ("⚠️ Em chưa lưu được ({error}). Công dân tick ô **Lưu thông tin mới sửa đổi…** trên trang rồi bấm "
           "**Xác nhận** giúp em, hoặc bỏ qua và bấm nút dưới ạ."),
    "tts": "Dạ, em chưa lưu được. Công dân tự tick ô lưu thông tin trên trang rồi bấm xác nhận, hoặc bấm nút bên dưới ạ.",
}
