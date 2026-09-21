"""Lời thoại TIẾNG MÔNG (Hmong Trắng, chữ RPA) — bật khi conv["lang"] == "hmong".

⚠️ BẢN NHÁP MÁY DỊCH — cần người bản ngữ tiếng Mông (Lai Châu) soát lại trước khi
triển khai rộng. Thuật ngữ lấy theo mockup (mockup/Mookup full màn.html):
  pej xeem = công dân · qhov chaw ua ntaub ntawv = nơi làm thủ tục · xeev = tỉnh ·
  zos = xã/phường · daim npav = thẻ · ntaus/hais lus = gõ/nói · cuv npe = đăng ký ·
  daim ntawv theej = bản sao · thaij duab = chụp ảnh · xov tooj = điện thoại.

Cách dùng (flow._fmt): mỗi mục CÙNG TÊN với script_vi; khi bật tiếng Mông thì
  - display_md = bản Việt + dòng Mông *in nghiêng* (song ngữ như mockup),
  - tts       = ĐỌC bản Mông thay bản Việt (thiếu mục nào fallback đọc tiếng Việt).
Quy ước:
  - "md" 1 ĐOẠN NGẮN (không xuống dòng kép) — flow bọc *nghiêng* nguyên đoạn.
  - {placeholder} chỉ dùng đúng tên có trong bản Việt tương ứng. Placeholder chứa
    sẵn text tiếng Việt ({doc_list_tts}, {intro_tts}, {missing_note}…) KHÔNG đưa vào
    bản Mông — nói chung chung "theo danh sách trên màn hình" để TTS không trộn 2 thứ tiếng.
"""

# ── Tên thủ tục tiếng Mông — hiện thành dòng nghiêng dưới tên tiếng Việt trên thẻ
# service_list (mockup: "Đăng ký Kết hôn" / *Cuv npe Yuav txiv...*). Key = registry key.
PROCEDURE_HMONG = {
    "ket-hon": "Cuv npe yuav txiv yuav poj niam",
    "khai-sinh-dang-ky": "Cuv npe yug me nyuam (txuas ntxiv)",
    "trich-luc-ks": "Daim ntawv theej hộ tịch",
    "xac-nhan-tinh-trang-hon-nhan": "Ntawv lees paub tsis tau muaj txij nkawm",
    "khai-sinh-dang-ky-lai": "Cuv npe yug me nyuam dua tshiab",
    "khai-tu": "Cuv npe tuag",
    "dang-ky-kinh-doanh": "Cuv npe tsim lag luam tsev neeg",
    "dang-ky-giam-ho": "Cuv npe saib xyuas tus neeg",
    "ket-hon-nuoc-ngoai": "Cuv npe yuav txiv/poj niam nrog neeg txawv teb chaws",
    "dang-ky-lai-ket-hon": "Cuv npe yuav txiv yuav poj niam dua tshiab",
    "khai-tu-dang-ky-lai": "Cuv npe tuag dua tshiab",
    "dang-ky-nhan-cha-me-con": "Cuv npe lees txiv, niam, me nyuam",
    "chung-thuc-ban-sao": "Lees paub daim ntawv theej",
    "chung-thuc-chu-ky": "Lees paub kos npe",
    # BẢN NHÁP chờ anh Dư soát (thủ tục Bộ NN&MT — cấp/cấp lại giấy phép đánh bắt cá).
    "cap-giay-phep-khai-thac-thuy-san": "Ntawv tso cai nuv ntses (muab tshiab / muab dua)",
    # BẢN NHÁP chờ anh Dư soát (Bộ GD&ĐT — bản sao văn bằng/chứng chỉ từ sổ gốc).
    "cap-ban-sao-van-bang-so-goc": "Daim ntawv theej ntawv pov thawj kawm ntawv",
    # BẢN NHÁP chờ anh Dư soát (Bộ Xây dựng — thuê/thuê mua nhà ở xã hội).
    "cho-thue-thue-mua-nha-o-xa-hoi": "Cuv npe xauj / xauj yuav tsev nyob pab pej xeem",
    # BẢN NHÁP chờ anh Dư soát (thay đổi nội dung đăng ký hộ kinh doanh).
    "dang-ky-thay-doi-noi-dung-ho-kinh-doanh": "Hloov lub ntsiab lus lag luam tsev neeg",
    # BẢN NHÁP chờ anh Dư soát (Bắc Ninh — đăng ký biện pháp bảo đảm bằng QSDĐ/thế chấp đất).
    "dang-ky-bien-phap-bao-dam-bac-ninh": "Cuv npe siv daim av ua puav pheej (Bắc Ninh)",
    # BẢN NHÁP chờ anh Dư soát (Bắc Ninh — xóa đăng ký biện pháp bảo đảm/giải chấp đất).
    "xoa-dang-ky-bien-phap-bao-dam-bac-ninh": "Rho npe siv daim av ua puav pheej (Bắc Ninh)",
}

# Nhãn card "Nơi làm thủ tục" (mockup: Qhov chaw ua ntaub ntawv / Xeev / Zos / Tus neeg ua).
# subject_options theo key executionSubject trong registry.
LOCATION_CARD_HMONG = {
    "title": "Qhov chaw ua ntaub ntawv",
    "province": "Xeev/Lub nroog",
    "ward": "Zos/Moos",
    "subject": "Tus neeg ua",
    "subject_options": {
        "self": "Ua rau tus kheej",
        "authorized_person": "Lwm tus muab cai",
        "enterprise_authorized": "Lag luam muab cai",
        "other_person": "Ua pab lwm tus",
        "organization_representative": "Sawv cev koom haum",
    },
}

# ── Nhãn CHIP (nút bấm dưới câu chat) — key = nhãn tiếng Việt NGUYÊN VĂN trong flow.py
# (gồm cả emoji). flow._localize_reply gắn labelHmong; FE hiện dòng nghiêng dưới nhãn Việt.
# Test đối chiếu source flow.py đảm bảo không bỏ sót nhãn nào.
CHIP_HMONG = {
    "Đúng rồi": "Yog lawm",
    "Chọn thủ tục khác": "Xaiv lwm yam",
    "🆕 Làm thủ tục khác": "Ua lwm yam",
    "Có, hãy đăng xuất": "Yog, tawm mus",
    "Không, nộp thêm hồ sơ": "Tsis, xa ntxiv",
    "✅ Xem lại và đồng ý": "Saib dua thiab pom zoo",
    "📁 Chọn thêm tệp từ máy": "Xaiv ntxiv file",
    "📎 Đính kèm giấy tờ ▶": "Muab ntaub ntawv tso",
    "📎 Đính kèm trong 1 hồ sơ": "Tso rau ib phau",
    "🗂️ Đính kèm nhiều hồ sơ": "Tso rau ntau phau",
    "📱 Chụp lại giấy tờ": "Thaij dua",
    "📱 Mở lại màn hình điện thoại": "Qhib dua xov tooj",
    "📱 Đổi sang chụp điện thoại": "Hloov mus thaij xov tooj",
    "🖨️ Đổi sang Scan tại quầy": "Hloov mus scan",
    "🔁 Thử lại": "Ua dua",
    "🔁 Thử lập kế hoạch lại": "Npaj dua",
    "🔁 Thử tạo hồ sơ lại": "Tsim phau dua",
    "🔁 Điền lại thông tin chủ hồ sơ": "Sau dua tus tswv",
    "🔁 Điền lại": "Sau dua",
    "🔁 Điền lại thông tin": "Sau dua cov ntaub ntawv",
    "🔁 Đính kèm lại": "Muab tso dua",
    "🗂️ Điều chỉnh giấy tờ": "Kho cov ntaub ntawv",
    "🗑️ Xóa dữ liệu": "Rho tawm",
    # Nhãn động (không nằm trong literal "label": ... của flow):
    "Kiểm tra lại trang hiện tại": "Xyuas dua nplooj no",
    "✅ Đã đưa đủ giấy tờ, xử lý đi": "Muab txaus lawm, ua mus",
    "✅ Đã đưa đủ giấy tờ, điền chủ hồ sơ đi": "Muab txaus lawm, sau tus tswv",
    "✅ Đã đưa đủ giấy tờ, điền tờ khai đi": "Muab txaus lawm, sau daim foos",
    "✅ Đã đưa đủ giấy tờ, đính kèm đi": "Muab txaus lawm, muab tso",
    "✅ Hoàn tất điều chỉnh, điền lại tờ khai": "Kho tiav lawm, sau daim foos dua",
    "✅ Hoàn tất điều chỉnh, đính kèm lại": "Kho tiav lawm, muab tso dua",
}

# ── Card CONSENT (xin phép xử lý dữ liệu) — bản Mông chỉ HỖ TRỢ HIỂU, bản tiếng Việt
# vẫn là bản pháp lý chính (Luật 91/2025/QH15); toàn văn Điều 4 giữ nguyên tiếng Việt.
# Khung card dùng chung 2 chế độ (điền / đính kèm):
CONSENT_UI_HMONG = {
    "title": "Tso cai kuv nyeem ntaub ntawv thiab sau daim ntawv qhia ua ntej",
    "docs_title": "Cov ntaub ntawv kuv yuav nyeem",
    "select_all": "Xaiv tag nrho",
    "legal_title": "Cai thiab luag hauj lwm ntawm tus tswv ntaub ntawv",
    "ver_note": "Qhov pom zoo raug sau tseg; pej xeem thim rov tau txhua lub sij hawm.",
}

# Nội dung theo chế độ ĐIỀN (cùng tên key với CONSENT_CARD_TEXT bản Việt):
CONSENT_CARD_HMONG = {
    "intro_md": (
        "Thaum pej xeem nias Pom zoo lawm, kuv li nyeem, muab thiab siv cov ntaub ntawv "
        "hauv qab no, sau kiag rau ntawm cov chaw nplooj ntawv qhib."
    ),
    "scope_md": (
        "Kuv tsuas nyeem cov ntaub ntawv uas pej xeem muab rau yam no xwb. "
        "Pej xeem xyuas thiab kho tau tag nrho ua ntej xa."
    ),
    "purpose_md": (
        "Lub hom phiaj: nyeem ntawv ntawm duab (OCR), kho kom raug, piv tus tswv ntaub ntawv, "
        "sau kiag daim foos thiab npaj cov file tso. Cov ntaub ntawv tsuas xa mus rau "
        "Cổng Dịch vụ công raws yam pej xeem thov xwb; cov ua tiav raug khaws hauv "
        "hệ thống los saib xyuas rov qab."
    ),
    "checks": [
        "Kuv nyeem thiab nkag siab lawm; kuv pom zoo cia Tus pab pej xeem nyeem, siv thiab "
        "sau kiag cov ntaub ntawv rau daim foos.",
        "Kuv lees tias kuv ris feem rau qhov tseeb thiab raug cai ntawm cov ntaub ntawv no.",
    ],
    "accept_label": "Pom zoo thiab sau kiag",
    "decline_label": "Tsis pom zoo · Sau tus kheej",
}

# Nội dung theo chế độ ĐÍNH KÈM (cùng tên key với CONSENT_ATTACH_CARD_TEXT bản Việt):
CONSENT_ATTACH_CARD_HMONG = {
    "intro_md": (
        "Thaum pej xeem nias Pom zoo xwb, kuv thiaj txais cov file pej xeem muab "
        "thiab muab tso rau phau ntaub ntawv ntawm Cổng Dịch vụ công."
    ),
    "scope_md": (
        "Yam no tsuas siv ib hom ntaub ntawv, tsis faib. Pej xeem xa tau ntau daim; "
        "tag nrho nyob hauv tib phau."
    ),
    "purpose_md": (
        "Lub hom phiaj: khaws ib pliag cov file hauv phiên thiab muab tso kiag rau "
        "Cổng Dịch vụ công raws pej xeem qhov thov; tsis nyeem los sau daim foos."
    ),
    "checks": [
        "Kuv nyeem thiab nkag siab lawm; kuv pom zoo cia Tus pab pej xeem txais, khaws ib pliag "
        "thiab muab tso kiag cov file kuv muab.",
        "Kuv lees tias kuv ris feem rau qhov tseeb thiab raug cai ntawm cov ntaub ntawv no.",
    ],
    "accept_label": "Pom zoo thiab muab tso kiag",
    "decline_label": "Tsis pom zoo · Muab tso tus kheej",
}

# Card "chọn cách cung cấp giấy tờ" — theo key option (qr/scan/profile).
DOC_OPTION_HMONG = {
    "qr": {"title": "Thaij duab ntawm xov tooj (luam QR)",
           "desc": "Luam QR, thaij los yog xaiv duab ntawm xov tooj"},
    "scan": {"title": "Scan ntawm chaw ua hauj lwm",
             "desc": "Muab ntaub ntawv tso rau lub tshuab scan"},
    "profile": {"title": "Siv cov khaws tseg",
                "desc": "Ua dhau lawm, tsis tas muab dua"},
}

# Nhãn bước trên thanh tiến độ — cùng key STEP_LABELS của script_vi.
STEP_LABELS_HMONG = {
    "greet": "Xaiv ntaub ntawv",
    "confirm_procedure": "Lees paub",
    "guide_login": "Nkag VNeID",
    "consent": "Tso cai siv ntaub ntawv",
    "ask_doc_method": "Xaiv kev muab",
    "qr_waiting": "Luam QR",
    "collecting_docs": "Xa ntaub ntawv",
    "owner_filling": "Sau tus tswv",
    "owner_waiting_next": "Xyuas tus tswv",
    "choosing_attach_mode": "Xaiv kev tso",
    "filling": "Sau phau ntawv",
    "reviewing": "Xyuas dua",
    "attaching": "Muab tso",
    "done": "Tiav lawm",
}

# Tên giấy tờ trong checklist phiên tải lên — theo SLOT KEY của registry.requiredDocs
# (dùng chung mọi thủ tục; thuật ngữ hành chính giữ tiếng Việt như mockup "theej Hộ tịch").
DOC_SLOT_HMONG = {
    "cccd": "Daim npav CCCD",
    "cccd_nam": "CCCD tus txiv (bên nam)",
    "cccd_nu": "CCCD tus poj niam (bên nữ)",
    "cccd_cha": "CCCD leej txiv",
    "cccd_me": "CCCD leej niam",
    "to_khai": "Daim ntawv qhia",
    "khac": "Lwm yam ntaub ntawv",
    "ho_tich": "Ntawv hộ tịch qub",
    "bao_tu": "Ntawv báo tử",
    "uy_quyen": "Ntawv ủy quyền",
    "ket_hon_cha_me": "Ntawv kết hôn niam txiv",
    "giay_de_nghi": "Ntawv thov",
    "chung_sinh": "Ntawv chứng sinh",
    "chung_minh_tthn": "Ntawv pov thawj hôn nhân",
    "bien_ban": "Biên bản",
}

GREET = {
    "md": (
        "Nyob zoo pej xeem! Kuv yog Tus pab pej xeem, pab ua cov ntaub ntawv hauv nom tswv. "
        "Pej xeem xyuas qhov chaw ua ntaub ntawv hauv qab no ces xaiv cov ntaub ntawv xav ua — "
        "nias rau daim ntawv los yog ntaus/hais lub npe."
    ),
    "tts": (
        "Nyob zoo pej xeem, kuv yog tus pab pej xeem. "
        "Pej xeem xaiv cov ntaub ntawv xav ua, nias rau daim ntawv los yog hais lub npe."
    ),
}

GREET_RETURNING = {
    "md": "Pej xeem tseem ua {procedure} tsis tau tiav. Pej xeem xav ua ntxiv los yog ua lwm yam?",
    "tts": "Pej xeem tseem ua tsis tau tiav. Pej xeem xav ua ntxiv los yog ua lwm yam?",
}

CONFIRM_PROCEDURE = {
    "md": "Pej xeem xav ua {procedure} ntawm {ward}, {province}, puas yog?",
    "tts": "Pej xeem xav ua {procedure} ntawm {ward} {province}, puas yog?",
}

PROCEDURE_NOT_RECOGNIZED = {
    "md": "Kuv tsis paub yam pej xeem xav ua. Pej xeem nias xaiv hauv qab no los yog hais dua lub npe.",
    "tts": "Kuv tsis paub yam pej xeem xav ua. Pej xeem xaiv hauv qab no los yog hais dua lub npe.",
}

GUIDE_LOGIN = {
    "md": (
        "Kuv tab tom coj pej xeem mus rau nplooj ntawv. Yog nplooj ntawv nug kev nkag, "
        "pej xeem qhib app VNeID hauv xov tooj, xaiv Quét QR, ces luam tus QR ntawm npo. "
        "Nkag tau lawm kuv qhia ntxiv."
    ),
    "tts": (
        "Pej xeem qhib app VNeID hauv xov tooj, xaiv luam QR, ces luam tus QR ntawm npo kom nkag tau. "
        "Nkag tau lawm kuv qhia ntxiv."
    ),
}

GUIDE_AGENCY_SELECT = {
    "md": (
        "Kuv tab tom qhib nplooj ntawv {procedure}. Kuv yuav xaiv qhov chaw ua "
        "({ward}, {province}) thiab nias Nộp trực tuyến pab pej xeem."
    ),
    "tts": "Kuv yuav xaiv qhov chaw ua {ward} {province} thiab xa online pab pej xeem.",
}

AGENCY_MANUAL_GUIDE = {
    "md": (
        "Pej xeem xaiv qhov chaw ua (xeev/zos) ntawm nplooj ntawv ces nias mus ntxiv. "
        "Txog kauj ruam sau ntawv kuv qhia ntxiv tam sim."
    ),
    "tts": "Pej xeem xaiv xeev thiab zos ntawm nplooj ntawv ces nias mus ntxiv. Txog kauj ruam sau ntawv kuv qhia ntxiv.",
}

AGENCY_AUTOFILL_GUIDE = {
    "md": (
        "Kuv xaiv qhov chaw ua pab pej xeem raws qhov chaw nyob {ward}, {province}. "
        "Tiav lawm pej xeem nias Chuyển bước tiếp theo."
    ),
    "tts": "Kuv xaiv qhov chaw ua pab pej xeem raws qhov chaw nyob. Tiav lawm pej xeem nias mus kauj ruam tom ntej.",
}

QR_LOGIN_GUIDE = {
    "md": (
        "Kuv xaiv qhov chaw {ward}, {province} tiav thiab qhib kauj ruam nkag lawm. "
        "Pej xeem qhib app VNeID hauv xov tooj, xaiv Quét QR, luam tus QR ntawm npo kom nkag. "
        "Tiav lawm kuv qhia ntxiv."
    ),
    "tts": (
        "Pej xeem qhib app VNeID, xaiv luam QR, ces luam tus QR ntawm npo kom nkag tau. "
        "Tiav lawm kuv qhia ntxiv."
    ),
}

VNEID_LOGIN_CODE_GUIDE = {
    "md": "Pej xeem ntaus tus lej lees paub raws npo, ces nias Xác nhận mus ntxiv.",
    "tts": "Pej xeem ntaus tus lej lees paub raws npo, ces nias lees paub mus ntxiv.",
}

VNEID_DATA_SHARING_GUIDE = {
    "md": (
        "Pej xeem kos lub thawv lees paub, nias Xác nhận chia sẻ, "
        "ces ntaus 6 tus lej passcode ntawm app VNeID mus ntxiv."
    ),
    "tts": (
        "Pej xeem kos lub thawv lees paub, nias lees paub sib qhia, "
        "ces ntaus rau tus lej passcode ntawm app VNeID."
    ),
}

VNEID_PASSCODE_GUIDE = {
    "md": "Pej xeem ntaus 6 tus lej passcode VNeID rau npo, ces nias Xác nhận mus ntxiv.",
    "tts": "Pej xeem ntaus rau tus lej passcode VNeID, ces nias lees paub mus ntxiv.",
}

WAIT_LOGIN_REMIND = {
    "md": (
        "Kuv tos pej xeem nkag VNeID — qhib app ces luam QR. "
        "Yog nkag tau lawm tab sis kuv tsis pom, pej xeem nias lub pob hauv qab."
    ),
    "tts": "Kuv tos pej xeem nkag. Yog nkag tau lawm, pej xeem nias lub pob ntawm npo.",
}

LOGIN_STILL_REQUIRED = {
    "md": "Nplooj ntawv tseem nyob kauj ruam nkag VNeID. Pej xeem nkag kom tiav; nkag tau lawm kuv paub tam sim.",
    "tts": "Nplooj ntawv tseem nyob kauj ruam nkag. Pej xeem nkag kom tiav, kuv yuav paub tam sim.",
}

PORTAL_NOT_READY = {
    "md": "Nplooj ntawv tseem tsis tau txog qhov ua ntaub ntawv. Pej xeem ua raws cov kauj ruam; txog lawm kuv paub tam sim.",
    "tts": "Nplooj ntawv tseem tsis tau txog. Pej xeem ua mus ntxiv, txog lawm kuv paub tam sim.",
}

WAIT_PORTAL_REMIND = {
    "md": "Kuv tos nplooj ntawv hloov mus rau kauj ruam sau ntawv. Yog pom daim foos lawm tab sis kuv tsis pom, nias lub pob hauv qab.",
    "tts": "Kuv tos nplooj ntawv hloov mus rau kauj ruam sau ntawv. Yog pom lawm, pej xeem nias lub pob ntawm npo.",
}

WAIT_ATTACH_PORTAL_REMIND = {
    "md": "Kuv tos nplooj ntawv hloov mus rau Thành phần hồ sơ. Yog pom lawm tab sis kuv tsis pom, nias lub pob hauv qab.",
    "tts": "Kuv tos nplooj ntawv hloov mus. Yog pom lawm, pej xeem nias lub pob ntawm npo.",
}

AGENCY_SELECT_FAILED = {
    "md": "Kuv xaiv tsis tau qhov chaw. Pej xeem xaiv {ward}, {province} kiag ces nias Đồng ý.",
    "tts": "Kuv xaiv tsis tau. Pej xeem xaiv kiag ces nias pom zoo.",
}

GUIDE_LOGIN_NO_URL = {
    "md": "Kuv tsis muaj txoj kev mus rau nplooj ntawv {procedure}. Pej xeem qhib nplooj ntawv ntawm cổng dịch vụ công; kuv pom lawm yuav pab ntxiv.",
    "tts": "Pej xeem qhib nplooj ntawv ntawm cổng dịch vụ công, kuv pom lawm yuav pab ntxiv.",
}

ASK_DOC_METHOD = {
    "md": (
        "Ua {procedure} pej xeem npaj cov ntaub ntawv raws daim ntawv teev saum npo. "
        "Pej xeem xav muab ntaub ntawv li cas? Xaiv ib txoj hauv qab no:"
    ),
    "tts": (
        "Pej xeem npaj cov ntaub ntawv raws daim ntawv teev saum npo. "
        "Pej xeem xav muab li cas? Thaij duab ntawm xov tooj los yog scan ntawm chaw?"
    ),
}

INTRO_FORM_REACHED = {"md": "Txog nplooj sau ntawv lawm.", "tts": "Txog nplooj sau ntawv lawm."}
INTRO_OWNER_REACHED = {"md": "Txog kauj ruam tus tswv ntaub ntawv lawm.", "tts": "Txog kauj ruam tus tswv ntaub ntawv lawm."}
INTRO_ATTACH_REACHED = {"md": "Txog kauj ruam Thành phần hồ sơ lawm.", "tts": "Txog kauj ruam muab ntaub ntawv tso lawm."}

OWNER_INFO_GUIDE = {
    "md": (
        "Pej xeem sau tus tswv ntaub ntawv (xov tooj, email, chaw nyob) ces nias mus ntxiv "
        "kom mus kauj ruam sau ntawv. Txog lawm kuv qhia ntxiv tam sim."
    ),
    "tts": "Pej xeem sau xov tooj, email, chaw nyob, ces nias mus ntxiv. Txog lawm kuv qhia ntxiv.",
}

OWNER_INFO_ATTACH_GUIDE = {
    "md": (
        "Pej xeem sau tus tswv ntaub ntawv (xov tooj, email, chaw nyob) ces nias mus ntxiv. "
        "Nplooj ntawv yuav mus rau Thành phần hồ sơ, kuv qhia muab ntaub ntawv tso tam sim."
    ),
    "tts": "Pej xeem sau xov tooj, email, chaw nyob ces nias mus ntxiv. Kuv qhia muab ntaub ntawv tso tam sim.",
}

DOCS_COMPLETE_OWNER = {
    "md": "Kuv txais tau {files_count} daim lawm, tab tom nrhiav tus tswv ntaub ntawv…",
    "tts": "Kuv txais tau ntaub ntawv lawm, tab tom nrhiav tus tswv ntaub ntawv.",
}
OWNER_PROCESSING = {
    "md": "Kuv tab tom piv lub npe thiab tus lej ntawm tus tswv ntaub ntawv, tos ib pliag…",
    "tts": "Kuv tab tom piv tus tswv ntaub ntawv, tos ib pliag.",
}
OWNER_FIELDS_READY = {
    "md": "Kuv pom tus tswv ntaub ntawv lawm thiab nrhiav tau {count} qhov. Kuv sau rau nplooj ntawv tam sim.",
    "tts": "Kuv pom tus tswv ntaub ntawv lawm, kuv sau rau tam sim.",
}
OWNER_FIELDS_UNMATCHED = {
    "md": "Cov ntaub ntawv tsis muaj qhov phim tus tswv ntaub ntawv. Pej xeem sau cov thawv tseem khoob.",
    "tts": "Cov ntaub ntawv tsis muaj qhov phim. Pej xeem sau cov thawv tseem khoob.",
}
OWNER_FIELDS_EMPTY = {
    "md": "Kuv tsis paub meej tus tswv ntaub ntawv, kuv tsis sau. Pej xeem sau ntxiv ces nias mus kauj ruam tom ntej.",
    "tts": "Kuv tsis paub meej tus tswv, kuv tsis sau. Pej xeem sau ntxiv ces nias mus kauj ruam tom ntej.",
}
OWNER_PIPELINE_ERROR = {
    "md": "Kuv nyeem tsis tau tus tswv ntaub ntawv. Pej xeem sau qhov tseem khoob ces nias mus kauj ruam tom ntej.",
    "tts": "Kuv nyeem tsis tau. Pej xeem sau qhov tseem khoob ces nias mus kauj ruam tom ntej.",
}
OWNER_FILL_DONE = {
    "md": "Kuv sau tiav lawm. Pej xeem xyuas ces nias mus kauj ruam tom ntej.",
    "tts": "Kuv sau tiav lawm. Pej xeem xyuas ces nias mus kauj ruam tom ntej.",
}
OWNER_FILL_NOT_APPLIED = {
    "md": "Kuv nyeem tau lawm tab sis nplooj ntawv tsis txais. Pej xeem nyob nplooj no thiab xaiv sau dua tus tswv ntaub ntawv.",
    "tts": "Nplooj ntawv tsis txais. Pej xeem nyob nplooj no thiab xaiv sau dua.",
}
MAIN_FORM_PROCESSING = {
    "md": "Tam sim no kuv yuav sau daim foos pab pej xeem.",
    "tts": "Tam sim no kuv yuav sau daim foos pab pej xeem.",
}
WAIT_ATTACHMENT_PAGE = {
    "md": "Xyuas tiav lawm, pej xeem hloov mus Thành phần hồ sơ; nplooj qhib kuv muab ntaub ntawv tso tam sim.",
    "tts": " Xyuas tiav lawm pej xeem hloov mus rau qhov muab ntaub ntawv tso. Nplooj qhib kuv ua tam sim.",
}
REVIEW_ATTACHMENT_ACTION = {
    "md": "Xyuas tiav lawm, pej xeem hloov mus Thành phần hồ sơ, ces nias Đính kèm giấy tờ hauv Tus pab kom kuv ua.",
    "tts": " Xyuas tiav lawm pej xeem hloov mus, ces nias lub pob muab ntaub ntawv tso kom kuv ua.",
}

CONSENT_INTRO = {
    "md": (
        "Ua ntej txais thiab nyeem ntaub ntawv, kuv xav tau pej xeem tso cai siv cov ntaub ntawv. "
        "Pej xeem nyeem daim npav hauv qab, kos 2 lub thawv, ces nias Đồng ý. "
        "Tsis pom zoo ces xaiv Tự nhập — kuv yuav tsis nyeem."
    ),
    "tts": (
        "Ua ntej txais thiab nyeem ntaub ntawv, kuv xav tau pej xeem tso cai. "
        "Pej xeem nyeem daim npav, kos ob lub thawv, ces nias pom zoo. "
        "Tsis pom zoo ces xaiv sau kiag, kuv yuav tsis nyeem."
    ),
}

CONSENT_ATTACH_INTRO = {
    "md": (
        "Ua ntej txais thiab muab ntaub ntawv tso, kuv xav tau pej xeem tso cai siv cov ntaub ntawv. "
        "Pej xeem nyeem daim npav hauv qab, kos 2 lub thawv, ces nias Đồng ý."
    ),
    "tts": "Ua ntej txais ntaub ntawv, kuv xav tau pej xeem tso cai. Pej xeem nyeem daim npav, kos ob lub thawv, ces nias pom zoo.",
}

CONSENT_ACCEPTED = {
    "md": "Kuv khaws pej xeem qhov pom zoo lawm.",
    "tts": "Kuv khaws pej xeem qhov pom zoo lawm.",
}

CONSENT_DECLINED = {
    "md": (
        "Kuv hwm pej xeem qhov txiav txim. Kuv yuav tsis nyeem tsis siv ib daim ntawv twg. "
        "Pej xeem sau daim foos kiag; thaum twg xav tau kuv pab, nias Xem lại và đồng ý."
    ),
    "tts": "Kuv hwm pej xeem qhov txiav txim, kuv yuav tsis nyeem ib daim twg. Xav tau kuv pab, nias saib dua thiab pom zoo.",
}

CONSENT_RESHOW = {
    "md": "Pej xeem nyeem dua daim ntawv tso cai hauv qab ces lees paub.",
    "tts": "Pej xeem nyeem dua daim ntawv tso cai ces lees paub.",
}

CONSENT_REMIND = {
    "md": "Pej xeem lees paub daim npav tso cai saum toj — pom zoo ces kos 2 lub thawv ces nias Đồng ý, tsis pom zoo ces xaiv Tự nhập.",
    "tts": "Pej xeem lees paub daim npav tso cai. Pom zoo ces kos ob lub thawv ces nias pom zoo, tsis pom zoo ces xaiv sau kiag.",
}

QR_WAITING = {
    "md": "Pej xeem qhib lub koob thaij duab ntawm xov tooj, luam tus QR hauv qab — xov tooj yuav qhib nplooj thaij duab ntaub ntawv.",
    "tts": "Pej xeem qhib lub koob thaij duab ntawm xov tooj, luam tus QR ntawm npo kom xa duab tau.",
}

MOBILE_CONNECTED = {
    "md": (
        "Xov tooj txuas tau lawm. Pej xeem thaij ib daim zuj zus raws daim ntawv teev "
        "(CCCD thaij ob sab), los yog xaiv duab muaj lawm — kuv paub thiab qhia tam sim."
    ),
    "tts": "Xov tooj txuas tau lawm. Pej xeem thaij ib daim zuj zus, daim CCCD thaij ob sab. Kuv txais tau kuv qhia tam sim.",
}

MOBILE_CONNECTED_ATTACH = {
    "md": "Xov tooj txuas tau lawm. Pej xeem thaij los yog xaiv tag nrho cov ntaub ntawv, tiav ces nias Gửi tất cả ntawm xov tooj.",
    "tts": "Xov tooj txuas tau lawm. Pej xeem thaij los yog xaiv tag nrho, tiav ces nias xa tag nrho.",
}

DOCS_COMPLETE_NEXT_STEP = {
    "md": "Kuv txais tau {files_count} daim lawm. Kuv tab tom nyeem thiab npaj sau rau daim foos — li ib nrab feeb, tos kuv ib pliag…",
    "tts": "Kuv txais tau ntaub ntawv lawm. Kuv tab tom nyeem thiab npaj sau rau daim foos, tos kuv ib pliag.",
}

ATTACH_MODE_PRESET_SPLIT = {
    "md": "\n\nRaws li **Cài đặt**, kuv yuav faib **ib daim ib phau** ntaub ntawv.",
    "tts": " Raws li Cài đặt, kuv yuav faib ib daim ib phau ntaub ntawv.",
}

WAIT_ATTACHMENT_SAME_PAGE = {
    "md": ("\n\nTam sim no kuv hloov mus rau **Thành phần hồ sơ** ces muab ntaub ntawv "
           "tso rau phau ntaub ntawv — pej xeem tos ib pliag."),
    "tts": " Tam sim no kuv hloov mus rau Thành phần hồ sơ ces muab ntaub ntawv tso. Pej xeem tos ib pliag.",
}

DOCS_COMPLETE_ATTACH = {
    "md": "Kuv txais tau {files_count} daim lawm. Kuv tab tom npaj muab tag nrho tso rau tib phau ntaub ntawv, tos ib pliag…",
    "tts": "Kuv txais tau ntaub ntawv lawm. Kuv npaj muab tso rau tib phau, tos ib pliag.",
}

DOCS_TARGET_UNKNOWN = {
    "md": "Kuv tsis paub pej xeem nyob kauj ruam twg. Cov ntawv txais lawm tseem nyob; pej xeem nyob nplooj yog ces nias dua lub pob hauv qab.",
    "tts": "Kuv tsis paub pej xeem nyob kauj ruam twg. Pej xeem nyob nplooj yog ces nias dua lub pob.",
}

DOCS_FORCED_MISSING = {
    "md": "Pej xeem xa {files_count} daim. Kuv nyeem thiab sau qhov muaj; tshuav dab tsi kuv nug dua. Tab tom ua, tos ib pliag…",
    "tts": "Kuv nyeem thiab sau qhov muaj, tshuav dab tsi kuv nug dua. Tos ib pliag.",
}

BUSINESS_PREPARING = {
    "md": "Kuv nkag lub vev đăng ký hộ kinh doanh lawm. Kuv yuav mus nplooj sau ntawv tam sim; pej xeem tos, tsis tas ua dab tsi.",
    "tts": "Kuv yuav mus nplooj sau ntawv tam sim, pej xeem tos ib pliag, tsis tas ua dab tsi.",
}

BUSINESS_DOCS_COMPLETE = {
    "md": "Kuv txais tau {files_count} daim lawm. Kuv tab tom nyeem thiab npaj 8 pawg ntaub ntawv, tos ib pliag…",
    "tts": "Kuv txais tau ntaub ntawv lawm, tab tom npaj yim pawg, tos ib pliag.",
}

BUSINESS_READY = {
    "md": "Kuv nyeem tiav lawm. Kuv yuav sau thiab khaws 8 pawg ib pawg zuj zus, ces muab ntaub ntawv tso. Thaum ua, pej xeem tsis txhob kov nplooj ntawv.",
    "tts": "Kuv yuav sau thiab khaws yim pawg ib pawg zuj zus. Thaum ua pej xeem tsis txhob kov nplooj ntawv.",
}

BUSINESS_DONE = {
    "md": "Kuv sau tiav {filled_pages}/{total_pages} pawg thiab tso {attached} daim lawm. Pej xeem xyuas ces nias Nộp hồ sơ ntawm nplooj ntawv.",
    "tts": "Kuv sau tiav thiab tso ntaub ntawv lawm. Pej xeem xyuas ces nias xa ntaub ntawv.",
}

BUSINESS_STOPPED = {
    "md": "Kuv nres qhov ua kiag lawm raws pej xeem hais. Cov khaws ntawm cổng tseem nyob.",
    "tts": "Kuv nres lawm. Cov khaws tseem nyob.",
}

BUSINESS_FAILED_PROGRESS = {
    "md": "Qhov ua kiag nres ntawm ib kauj ruam. Cov khaws tseem nyob. Pej xeem nias Thử lại kom kuv ua dua.",
    "tts": "Qhov ua kiag nres lawm. Pej xeem nias ua dua kom kuv ua ntxiv.",
}

BUSINESS_FAILED = {
    "md": "Qhov sau kiag nres ntawm ib kauj ruam. Ntaub ntawv tseem nyob. Pej xeem nias Thử lại kom kuv ua ntxiv.",
    "tts": "Qhov sau kiag nres lawm. Pej xeem nias ua dua kom kuv ua ntxiv.",
}

FILL_READY = {
    "md": (
        "Tiav lawm! Kuv nyeem tau {count} qhov thiab tab tom sau rau daim foos sab laug. "
        "Pej xeem xyuas — thawv daj yog kuv teeb, thawv liab yog tseem tshuav."
    ),
    "tts": "Kuv nyeem tau lawm thiab tab tom sau rau daim foos. Pej xeem xyuas, thawv daj yog kuv teeb, thawv liab yog tshuav.",
}

FILL_REPORT_REVIEW = {
    "md": "Kuv sau tau {filled} lub thawv. Pej xeem xyuas dua ces kho kiag lub twg tsis yog.",
    "tts": "Kuv sau tiav lawm. Pej xeem xyuas dua ces kho lub twg tsis yog.",
}

PIPELINE_ERROR = {
    "md": "Kuv nyeem ntaub ntawv tsis tau. Pej xeem nias ua dua, los yog thaij duab kom pom meej dua.",
    "tts": "Kuv nyeem tsis tau. Pej xeem nias ua dua los yog thaij dua kom meej.",
}

ATTACH_PIPELINE_ERROR = {
    "md": "Kuv npaj muab ntaub ntawv tso tsis tau. Cov ntawv tseem nyob; pej xeem nias ua dua.",
    "tts": "Kuv npaj tsis tau. Cov ntawv tseem nyob, pej xeem nias ua dua.",
}

ATTACH_PLANNING = {
    "md": "Kuv tab tom npaj txoj kev muab ntaub ntawv tso, tos ib pliag…",
    "tts": "Kuv tab tom npaj, tos ib pliag.",
}

ATTACH_RUNNING = {
    "md": "Kuv tab tom muab ntaub ntawv tso rau phau ntaub ntawv. Pej xeem tos kuv ua tiav.",
    "tts": "Kuv tab tom muab ntaub ntawv tso. Pej xeem tos kuv ua tiav.",
}

ATTACH_REQUEST_ON_DECLARATION = {
    "md": "Tseem nyob nplooj sau ntawv. Pej xeem xyuas daim foos ces hloov mus Thành phần hồ sơ; mus txog kuv muab tso kiag.",
    "tts": "Tseem nyob nplooj sau ntawv. Pej xeem xyuas ces hloov mus, txog lawm kuv muab tso kiag.",
}

ATTACH_REQUEST_UNKNOWN = {
    "md": "Kuv tsis nkag siab. Pej xeem hais luv luv, piv txwv: muab ntaub ntawv tso.",
    "tts": "Kuv tsis nkag siab. Pej xeem hais luv luv, piv txwv muab ntaub ntawv tso.",
}

ATTACH_MODE_ASK = {
    "md": "Kuv txais tau {files_count} daim. Pej xeem xav muab tag nrho rau ib phau, los yog ib daim ib phau?",
    "tts": "Pej xeem xav muab tag nrho rau ib phau, los yog ib daim ib phau?",
}

ATTACH_MODE_SELECTED = {
    "md": "Pej xeem xaiv lawm. Kuv tab tom nyeem thiab npaj, tos ib pliag…",
    "tts": "Kuv tab tom nyeem thiab npaj, tos ib pliag.",
}

ATTACH_PLAN_READY = {
    "md": "Txoj kev npaj tiav lawm — {count} qhov. Kuv tab tom muab ib daim zuj zus tso rau, tos ib pliag…",
    "tts": "Npaj tiav lawm. Kuv tab tom muab tso, tos ib pliag.",
}

ATTACH_PLAN_READY_SPLIT = {
    "md": "Txoj kev npaj tiav lawm — {count} daim. Kuv yuav muab ib daim ib phau thiab ua ib lub tab zuj zus…",
    "tts": "Npaj tiav lawm. Kuv muab ib daim ib phau, ua ib lub tab zuj zus.",
}

ATTACH_PLAN_READY_SIGNATURE_SPLIT = {
    "md": "Txoj kev npaj tiav lawm — {count} phau. Ib phau muaj ib daim ntawv ntawm STT 1; phau thib ib muaj ntxiv daim npav tus kheej ntawm STT 2.",
    "tts": "Npaj tiav lawm. Kuv ua ib phau zuj zus.",
}

ATTACH_WRONG_PAGE = {
    "md": "Pej xeem tseem nyob kauj ruam sau ntawv. Nias mus ntxiv kom mus Thành phần hồ sơ — txog lawm kuv muab ntaub ntawv tso kiag.",
    "tts": "Pej xeem nias mus ntxiv kom mus rau qhov muab ntaub ntawv tso. Txog lawm kuv ua kiag.",
}

ATTACH_PAGE_REACHED = {
    "md": "Pom kauj ruam Thành phần hồ sơ lawm. Kuv muab ntaub ntawv tso tam sim…",
    "tts": "Pom lawm. Kuv muab ntaub ntawv tso tam sim.",
}

ATTACH_NONE = {
    "md": "Kuv muab tsis tau ib daim twg. Pej xeem xyuas nplooj nyob Thành phần hồ sơ, ces nias muab tso dua.",
    "tts": "Kuv muab tsis tau. Pej xeem xyuas nplooj ces nias muab tso dua.",
}

SAME_PAGE_TWO_STEP_SUMMARY = {
    "md": ("\n\n📋 **Nhập đơn đăng ký** — sau tau {filled} lub thawv ✓ · "
           "**Tải thành phần hồ sơ** — muab tau {attached} daim ✓"),
    "tts": " Kuv sau tau cov thawv ntawm daim foos, thiab muab tau cov daim ntaub ntawv tso.",
}

ATTACH_DONE = {
    "md": "Kuv muab {attached} daim tso tiav lawm. Pej xeem xyuas zaum kawg ces nias Nộp hồ sơ — kauj ruam xa kuv cia pej xeem nias.",
    "tts": "Kuv muab tso tiav lawm. Pej xeem xyuas zaum kawg ces nias xa ntaub ntawv.",
}

ATTACH_DONE_WITH_ERRORS = {
    "md": "Kuv muab tau {attached} daim, tshuav qee daim tsis tau. Pej xeem muab kiag qhov tshuav ces nias Nộp hồ sơ.",
    "tts": "Kuv muab tau ib txhia, tshuav qee daim. Pej xeem muab kiag qhov tshuav ces xa ntaub ntawv.",
}

ATTACH_SUPPLEMENT_ASK = {
    "md": (
        "Kuv qhib dua session **{session_id}** thiab tag nrho cov ntaub ntawv qub lawm. "
        "Pej xeem saib, rho tawm los yog ntxiv file tshiab tau, ces nias kho tiav."
    ),
    "tts": "Kuv qhib dua cov ntaub ntawv lawm. Pej xeem saib, rho tawm los yog ntxiv file tshiab tau.",
}

DOCUMENT_ADJUSTMENT_WRONG_PAGE = {
    "md": "Nplooj no tsis yog Kê khai thông tin. Rov mus nplooj kê khai ces nias kho tiav.",
    "tts": "Rov mus nplooj kê khai ces nias kho tiav.",
}

ATTACH_SUPPLEMENT_SESSION_EXPIRED = {
    "md": "Session ntaub ntawv qub tas lawm. Pej xeem xaiv txoj kev xa thiab muab file dua.",
    "tts": "Session qub tas lawm. Pej xeem xaiv txoj kev xa file dua.",
}

ATTACH_SUPPLEMENT_AFTER_SUBMIT = {
    "md": "Cov ntaub ntawv twb xa tiav lawm, kuv hloov daim ntawv hauv phau no tsis tau lawm.",
    "tts": "Cov ntaub ntawv twb xa tiav lawm, hloov tsis tau lawm.",
}

ATTACH_ALL_FILES_EXIST = {
    "md": "Kuv xyuas tag lawm. Cov file tseem tshuav twb nyob hauv phau lawm, kuv tsis muab rov ntxiv.",
    "tts": "Cov file twb nyob hauv phau lawm, kuv tsis muab rov ntxiv.",
}

ATTACH_SPLIT_DONE = {
    "md": "Kuv muab tiav {succeeded}/{total} phau, ib daim ib phau. Pej xeem xyuas ib lub tab zuj zus ces nias Nộp hồ sơ.",
    "tts": "Kuv muab tiav lawm, ib daim ib phau. Pej xeem xyuas ib lub tab zuj zus ces xa ntaub ntawv.",
}

ATTACH_SPLIT_DONE_WITH_ERRORS = {
    "md": "Kuv muab tau {succeeded}/{total} phau, tshuav qee phau tsis tau. Pej xeem xyuas cov tab tshuav ces muab kiag.",
    "tts": "Tshuav qee phau tsis tau. Pej xeem xyuas cov tab tshuav ces muab kiag.",
}

SCAN_PICK = {
    "md": (
        "Pej xeem muab ntaub ntawv tso rau lub maiv scan (los sis muab cov duab twb muaj/PDF "
        "hauv maiv teev), li xaiv chaw qhib file ntawm qhov chaw qhib — xaiv ntau daim ib zaug "
        "los tau, kuv paub thiab faib tsheej yam."
    ),
    "tts": "Pej xeem muab ntaub ntawv tso rau lub maiv scan los sis xaiv file hauv maiv teev. Xaiv ntau daim ib zaug los tau, kuv paub thiab faib tsheej yam.",
}

# Nối vào cuối SCAN_PICK (xem vi.SCAN_AUTO_RUN_NOTE). Trích ĐÚNG nhãn chip tiếng Mông
# "Muab txaus lawm, ua mus" để công dân dò ra nút trên màn hình.
SCAN_AUTO_RUN_NOTE = {
    "md": " Muab tag lawm, pej xeem nias **\"Muab txaus lawm, ua mus\"** hauv qab kom kuv pib ua.",
    "tts": " Muab tag lawm ces pej xeem nias lub pob Muab txaus lawm ua mus, kuv pib ua kiag.",
}

SCAN_PICK_ATTACH = {
    "md": (
        "Pej xeem muab ntaub ntawv tso rau lub tshuab scan los yog xaiv duab/PDF hauv computer. "
        "Xaiv ntau daim ib zaug los tau; tag nrho suav ua ntaub ntawv theej, tsis faib."
    ),
    "tts": "Pej xeem xaiv ib daim los ntau daim hauv computer.",
}

DONE_SUBMITTED = {
    "md": (
        "Pej xeem xa ntaub ntawv rau Cổng Dịch vụ công tiav lawm. "
        "Pej xeem puas xav kom kuv thoob khiav (đăng xuất) VNeID? Tsis xaiv, 2 feeb kuv thoob khiav kiag kom tiv thaiv account."
    ),
    "tts": "Xa tiav lawm. Pej xeem puas xav kom kuv thoob khiav VNeID? Tsis xaiv, ob feeb kuv thoob khiav kiag.",
}

PHONE_SUBSCRIBED = {
    "md": "Kuv khaws tus lej {phone} lawm — muaj xov tshiab kuv hu tam sim.",
    "tts": "Kuv khaws tus lej lawm, muaj xov tshiab kuv hu tam sim.",
}

PHONE_INVALID = {
    "md": "Tus lej {phone} tsis yog. Pej xeem hais dua 10 tus lej pib ntawm 0.",
    "tts": "Tus lej tsis yog. Pej xeem hais dua kaum tus lej pib ntawm xoom.",
}

DATA_DELETED = {
    "md": "Kuv rho tawm tag nrho pej xeem cov ntaub ntawv lawm. Ua tsaug uas siv!",
    "tts": "Kuv rho tawm tag nrho lawm. Ua tsaug uas siv.",
}

CHANGED_LOCATION = {
    "md": "Kuv hloov qhov chaw ua ntaub ntawv mus {ward}, {province} lawm.",
    "tts": "Kuv hloov qhov chaw ua mus {ward} {province} lawm.",
}

CHANGED_PROCEDURE_RESET = {
    "md": "Hloov mus ua lwm yam. Pej xeem xaiv cov ntaub ntawv hauv qab no:",
    "tts": "Hloov mus ua lwm yam. Pej xeem xaiv hauv qab no.",
}

OFF_SCOPE = {
    "md": "Lo lus no dhau kuv qhov paub lawm. Pej xeem xav ua yam twg hauv daim ntawv teev?",
    "tts": "Lo lus no dhau kuv qhov paub. Pej xeem xav ua yam twg hauv daim ntawv teev?",
}

FALLBACK_CLARIFY = {
    "md": "Pej xeem hais meej me ntsis — pej xeem xav {hint}, puas yog?",
    "tts": "Pej xeem hais meej me ntsis.",
}

# BẢN NHÁP chờ anh Dư soát. Hiện thành dòng nghiêng ngay dưới từng dòng tiếng Việt của thẻ.
# Nút chốt giấy tờ gọi đúng nhãn Mông trong CHIP_HMONG để công dân dò khớp chữ trên nút thật.
SCAN_GUIDE = {
    "heading": "Muab ntaub ntawv tso rau lub maiv scan",
    "body": ("Pej xeem muab ntawv tso rau lub maiv scan raws li daim duab qhia, ces nias "
             "lub pob **Scan**."),
    "alt": "Qhia scan: muab sab ntawv yuav scan tso rau hauv qab ces nias lub pob Scan.",
    "zoom": "🔍 Nias saib daim duab",
    "note": ("Muab **ib daim ib zaug** xwb — lub maiv txais kiag. Muab tag lawm ces nias "
             "**\"Muab txaus lawm, ua mus\"**."),
}

# BẢN NHÁP chờ anh Dư soát. "md" phải là MỘT đoạn (không gạch đầu dòng, không xuống dòng
# kép): extension bọc *nghiêng* nguyên đoạn như khối Mông của câu chat, mà markdown không
# in nghiêng qua nhiều dòng. Emoji để ở dòng Việt phía trên, không lặp lại.
SCAN_FEEDBACK = {
    "md": ("Kuv txais tau {count} daim ntawm lub maiv scan. Tseem muaj ntaub ntawv ces pej xeem "
           "muab ib daim ntxiv rau lub maiv, kuv txais kiag. Txaus lawm ces nias "
           "\"Muab txaus lawm, ua mus\" hauv qab kom kuv pib ua."),
    "tts": ("Kuv txais tau ib daim lawm. Tseem muaj ntaub ntawv ces pej xeem muab ntxiv rau lub "
            "maiv scan, kuv txais kiag. Txaus lawm ces nias lub pob Muab txaus lawm ua mus."),
    "ttsMore": ("Kuv txais tau ib daim ntxiv, tag nrho {count} daim. Tseem muaj ces muab ntxiv rau "
                "lub maiv scan; txaus lawm ces nias lub pob Muab txaus lawm ua mus kom kuv pib ua."),
}

# Không có LANG_OFF: chuyển VỀ tiếng Việt thì câu xác nhận phải bằng tiếng Việt.
LANG_ON = {
    "md": "Kuv qhib hais lus Hmoob lawm — kuv yuav hais thiab mloog lus Hmoob.",
    "tts": "Kuv qhib hais lus Hmoob lawm. Kuv yuav hais thiab mloog lus Hmoob.",
}

# Tên thủ tục và tên giấy tờ GIỮ NGUYÊN tiếng Việt: đó là chữ in trên giấy và trên cổng,
# công dân phải đối chiếu được. Chỉ phần dẫn dắt dịch sang tiếng Mông.
# KHÔNG nhắc lại {step}: nhãn bước có hai bản (STEP_LABELS / STEP_LABELS_HMONG) nhưng _fmt
# format md Việt và md Mông bằng CÙNG một bộ kwargs, nên nhét vào là một trong hai bản sai
# ngôn ngữ. Thanh tiến độ phía trên đã hiện cả hai bản rồi.
PROCEDURE_IN_PROGRESS = {
    "md": "Peb tab tom ua {procedure} lawm. Pej xeem ua raws kuv qhia mus ntxiv.",
    "tts": "Peb tab tom ua {procedure} lawm. Pej xeem ua raws kuv qhia mus ntxiv.",
}

# {documents_md}/{documents_tts} là tên giấy tờ tiếng Việt lấy từ registry — theo quy ước đầu
# file KHÔNG nhét vào bản Mông (đọc bằng giọng Mông thì công dân nghe không ra). Khối tiếng
# Việt ngay phía trên đã liệt kê đủ, bản Mông chỉ trỏ lên đó.
DOC_LIST_ANSWER = {
    "md": "Ua {procedure} pej xeem npaj cov ntaub ntawv teev saum npo.",
    "tts": "Pej xeem npaj cov ntaub ntawv teev saum npo.",
}

ANSWER_ONLY_DOCS_AND_STEPS = {
    "md": ("Txog {procedure}: kuv paub cov ntaub ntawv npaj thiab cov kauj ruam xa ntaub ntawv. "
           "Lwm yam pej xeem saib hauv nplooj ntawv."),
    "tts": "Lwm yam pej xeem saib hauv nplooj ntawv.",
}

PICK_FILES_AGAIN = {
    "md": "Kuv qhib qhov xaiv ntaub ntawv lawm. Pej xeem xaiv ntaub ntawv ntxiv.",
    "tts": "Kuv qhib qhov xaiv ntaub ntawv lawm. Pej xeem xaiv ntxiv.",
}

BUSINESS_STILL_PROCESSING = {
    "md": "Kuv tab tom ua phau ntaub ntawv lag luam, tos ib pliag…",
    "tts": "Kuv tab tom ua phau ntaub ntawv lag luam, tos ib pliag.",
}

STILL_READING_DOCUMENTS = {
    "md": "Kuv tab tom nyeem ntaub ntawv, yuav tas lawm, tos ib pliag…",
    "tts": "Kuv tab tom nyeem ntaub ntawv, yuav tas lawm, tos ib pliag.",
}

# ── BẢN NHÁP chờ anh Dư soát ────────────────────────────────────────────────────────────
# Các template flow.py đang gọi qua _fmt nhưng trước đây thiếu twin → _fmt rơi về tiếng Việt
# và đọc bằng giọng Việt giữa phiên tiếng Mông.
#
# {options_md}/{options_tts}/{error} chứa sẵn chữ tiếng Việt lấy từ registry và từ cổng, nên
# theo quy ước đầu file KHÔNG nhét vào bản Mông — chỉ trỏ "nyob saum npo" (trên màn hình),
# nơi khối tiếng Việt ngay phía trên đã liệt kê đầy đủ. Nhãn nút của cổng (Đồng ý, Kê khai
# thông tin…) giữ nguyên tiếng Việt: công dân phải dò đúng chữ trên nút.
CHOOSE_VARIANT = {
    "md": "{procedure} txog kauj ruam xaiv qhov ua. Muaj {count} qho nyob saum npo — pej xeem xaiv ib qho.",
    "tts": "Muaj {count} qho ua. Pej xeem xaiv ib qho nyob saum npo.",
}

CHOOSE_VARIANT_REMIND = {
    "md": "Pej xeem xaiv ib qho nyob saum npo kom kuv ua tau ntxiv.",
    "tts": "Pej xeem xaiv ib qho nyob saum npo kom kuv ua tau ntxiv.",
}

VARIANT_DIALOG_AUTOFILL_GUIDE = {
    "md": "Kuv xaiv qhov {variant_label} ces nias Đồng ý kom mus rau nplooj sau ntawv.",
    "tts": "Kuv xaiv qhov {variant_label} ces nias Đồng ý kom mus rau nplooj sau ntawv.",
}

GUIDE_AGENCY_SELECT_PROVINCE = {
    "md": ("Kuv tab tom qhib nplooj ntawv {procedure}. Kuv yuav xaiv xeev {province}, "
           "nias Đồng ý ces xaiv {agency} kom xa tau ntaub ntawv."),
    "tts": ("Kuv tab tom qhib nplooj ntawv. Kuv yuav xaiv xeev {province} ces xaiv {agency} "
            "kom xa tau ntaub ntawv."),
}

MAE_AGENCY_AUTOFILL_GUIDE = {
    "md": ("Kuv xaiv xeev {province} thiab {agency}, kuv xaiv qhov {variant_label} ces nias "
           "Đồng ý và tiếp tục kom mus rau nplooj sau ntawv."),
    "tts": ("Kuv xaiv xeev {province} thiab {agency}, xaiv qhov {variant_label} ces nias "
            "Đồng ý và tiếp tục kom mus rau nplooj sau ntawv."),
}

MAE_AGENCY_FAILED = {
    "md": ("Kuv xaiv tsis tau ntawm nplooj ntawv. Pej xeem xaiv: Xeev {province}, ces Sở/Ban ngành "
           "xaiv {agency}, ces qhov {variant_label}, ces nias Đồng ý và tiếp tục."),
    "tts": ("Kuv xaiv tsis tau. Pej xeem xaiv xeev {province}, xaiv {agency}, xaiv qhov "
            "{variant_label}, ces nias Đồng ý và tiếp tục."),
}

PROCEDURE_PROVINCE_LOCKED = {
    "md": ("{procedure} tsuas ua tau nyob {provinces} xwb. Pej xeem nyob lwm xeev, ua tsis tau "
           "yam no. Pej xeem xaiv lwm yam hauv qab no."),
    "tts": ("{procedure} tsuas ua tau nyob {provinces} xwb. Pej xeem nyob lwm xeev, ua tsis tau "
            "yam no. Pej xeem xaiv lwm yam hauv qab no."),
}

RATE_INVITE = {
    "md": ("Pej xeem xa tau ntaub ntawv lawm. Ua ntej tas, pej xeem qhia kuv hnub no kuv pab "
           "zoo li cas? Nias ib qho xwb, tsis yuam."),
    "tts": ("Pej xeem xa tau ntaub ntawv lawm. Ua ntej tas, pej xeem qhia kuv hnub no kuv pab "
            "zoo li cas? Nias ib qho xwb, tsis yuam."),
}

REFILL_ALREADY_RUNNING = {
    "md": "Kuv tab tom sau dua cov ntaub ntawv lawm. Pej xeem tos ib pliag.",
    "tts": "Kuv tab tom sau dua cov ntaub ntawv lawm. Pej xeem tos ib pliag.",
}

REFILL_PROCESSING = {
    "md": ("Kuv tab tom nyeem dua ntaub ntawv thiab sau dua daim foos. Pej xeem nyob hauv nplooj "
           "no, tos ib pliag…"),
    "tts": ("Kuv tab tom nyeem dua ntaub ntawv thiab sau dua daim foos. Pej xeem nyob hauv nplooj "
            "no, tos ib pliag."),
}

REFILL_WRONG_PAGE = {
    "md": ("Nplooj ntawv tsis yog nplooj Kê khai thông tin. Pej xeem rov mus rau nplooj Kê khai "
           "ces nias Điền lại thông tin."),
    "tts": ("Nplooj ntawv tsis yog nplooj Kê khai thông tin. Pej xeem rov mus rau nplooj Kê khai "
            "ces nias Điền lại thông tin."),
}
