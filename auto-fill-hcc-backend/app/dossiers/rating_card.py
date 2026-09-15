"""Nội dung phiếu đánh giá trải nghiệm — NGUỒN DUY NHẤT cho cả hai kênh.

Vì sao đặt ở `app/dossiers` chứ không ở `channels/handfree`: phiếu đánh giá gắn vào HỒ SƠ
(`dossiers.rating`), không gắn vào cuộc hội thoại. Handfree đẩy card qua chat, Auto Fill nạp
qua `GET /api/v1/procedures` — hai đường khác nhau nhưng phải cùng một câu chữ, nếu không hai
kênh sẽ hỏi khác nhau rồi cộng chung vào một con số.

Để nguyên trong `script_vi.py` thì `app/dossiers` phải import ngược vào channel — sai chiều
phụ thuộc (shared không được biết tới channel).

Server-driven: extension chỉ dựng UI từ dữ liệu này, KHÔNG chép cứng nhãn nào. Sửa câu chữ hay
thêm/bớt lý do = sửa file này rồi deploy, không phải phát hành lại extension.
"""

RATING_CARD = {
    "title": "Hôm nay Trợ lý hỗ trợ công dân thế nào ạ?",
    "subtitle": "Công dân chạm vào một dòng bên dưới. Không phải viết gì cả.",
    # value cao = hài lòng hơn; FE hiện mặt cười theo value.
    "scale": [
        {"value": 5, "label": "Rất hài lòng"},
        {"value": 4, "label": "Hài lòng"},
        {"value": 3, "label": "Bình thường"},
        {"value": 2, "label": "Chưa hài lòng"},
        {"value": 1, "label": "Không hài lòng"},
    ],
    "goodThreshold": 4,  # >= ngưỡng này hỏi "điều gì thuận tiện"; dưới ngưỡng hỏi "cần cải thiện"
    "reasonPromptGood": "Điều gì công dân thấy thuận tiện nhất?",
    "reasonPromptBad": "Điều gì cần cải thiện ạ?",
    "reasonsGood": [
        "Không phải tự điền giấy tờ", "Được hướng dẫn từng bước", "Nói được, không cần gõ",
        "Làm nhanh hơn trước", "Không phải đi lại nhiều lần",
    ],
    "reasonsBad": [
        "Thao tác còn khó", "Máy đọc sai thông tin", "Phải chờ lâu",
        "Nghe hướng dẫn chưa rõ", "Cần người hỗ trợ thêm",
    ],
    "reasonHint": "Chọn một hoặc nhiều dòng. Không chọn cũng được ạ.",
    "voiceHint": "Hoặc bấm vào đây rồi NÓI ý kiến",
    "notePlaceholder": "Ý kiến của công dân (nếu có)…",
    "skipLabel": "Bỏ qua phần đánh giá",
    "submitLabel": "Gửi đánh giá",
    "privacy": "Không bắt buộc · không ghi tên công dân · không ảnh hưởng đến việc giải quyết hồ sơ",
    # Hiện NGAY TRONG card sau khi gửi/bỏ qua (không đẻ bong bóng cảm ơn riêng).
    "thanks": "Cảm ơn công dân đã đánh giá! 🌸",
    "thanksSub": "Ý kiến của công dân đã được ghi nhận.",
}


def level_label(level) -> str:
    """Nhãn của mức hài lòng; "" nếu không khớp mức nào (bỏ qua đánh giá)."""
    for item in RATING_CARD["scale"]:
        if item["value"] == level:
            return item["label"]
    return ""
