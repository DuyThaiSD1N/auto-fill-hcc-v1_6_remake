from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "production"
    host: str = "0.0.0.0"
    port: int = 8000

    # MongoDB — cấu hình theo thành phần; docker override MONGO_HOST=host.docker.internal.
    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_username: str = ""
    mongo_password: str = ""
    mongo_auth_source: str = "admin"
    mongo_db: str = "autofill_hcc"
    # Nếu set MONGO_URI thì dùng thẳng (bỏ qua các thành phần ở trên).
    mongo_uri: str = ""

    @property
    def mongo_dsn(self) -> str:
        if self.mongo_uri:
            return self.mongo_uri
        if self.mongo_username:
            from urllib.parse import quote_plus

            cred = f"{quote_plus(self.mongo_username)}:{quote_plus(self.mongo_password)}@"
            return (f"mongodb://{cred}{self.mongo_host}:{self.mongo_port}/"
                    f"?authSource={self.mongo_auth_source}")
        return f"mongodb://{self.mongo_host}:{self.mongo_port}"

    # JWT
    jwt_access_secret: str = "change_me"
    jwt_refresh_secret: str = "change_me_too"
    jwt_alg: str = "HS256"
    jwt_access_ttl: int = 3600
    jwt_refresh_ttl: int = 2592000

    # OCR — 2 provider, chọn theo option "Có bản viết tay" (xem app/services/ocr.py).
    # raw: vnekyc Google Vision (mặc định, đính kèm + fill không viết tay).
    ocr_raw_base_url: str = "https://trolyao-hcc.vnekyc.vn"
    # vintern: Vintern-1B-v3.5 (OpenAI vision). PDF được tách trang -> ảnh rồi OCR.
    ocr_vintern_base_url: str = "https://spark-abf9.tail0f2e98.ts.net/vintern"
    ocr_model: str = "Vintern-1B-v3.5"
    ocr_timeout_ms: int = 60000
    ocr_max_tokens: int = 4096
    ocr_repetition_penalty: float = 1.1
    ocr_pdf_dpi: int = 200  # 200 cho chất lượng/độ chính xác tốt nhất với Vintern-1B (>250 model đọc sai số)
    ocr_concurrency: int = 4

    # OCR tiengnoi (vintern-v5) — batch nhiều file/1 request, server tự tách trang + xoay ảnh.
    ocr_tiengnoi_base_url: str = "https://troly-hcc.tiengnoi.vn"
    ocr_tiengnoi_api_key: str = ""
    ocr_tiengnoi_timeout_ms: int = 120000
    ocr_tiengnoi_max_tokens: int = 1500  # classify không cần dày → giảm cho nhanh
    ocr_tiengnoi_fill_max_tokens: int = 4096  # FILL cần text ĐẦY ĐỦ (nhiều trang) → cao hơn classify
    # Chuyển OCR FORM-FILL sang tiengnoi (vintern-v6) làm CHÍNH; batch lỗi/sập hoặc file rỗng
    # → fallback Gemini (per-file). Lưu ý: tiengnoi yếu đọc SỐ DÀI → sai số vẫn "thành công",
    # KHÔNG kích hoạt fallback. Tắt = về Gemini như cũ.
    ocr_by_tiengnoi: bool = False

    # Bước PHÂN LOẠI ĐÍNH KÈM (module riêng app/services/attach_classify.py) — chỉ path attach.
    # 2 MODE ĐỘC LẬP cờ RAW_BY_GEMINI: "tiengnoi" = vintern-v5 tiếng nói (lỗi→fallback vnekyc);
    # "vnekyc" (hoặc "raw") = Google Vision vnekyc THẬT (gọi thẳng ocr_raw, không bị đổi sang Gemini).
    attach_classify_ocr: str = "tiengnoi"
    attach_classify_max_pages: int = 2     # OCR tối đa N trang đầu (loại/tên luôn ở trang 1-2)
    attach_classify_char_limit: int = 800  # cắt OCR text đưa vào LLM (tiêu đề/tên ở đầu)
    attach_classify_max_tokens: int = 300  # output classify nhỏ ({"d":[{t,n}]})

    # Cache OCR text theo HASH nội dung file (collection ocr_cache, _id = "v1:<sha256 bytes>").
    # Bù cho việc OCR LẠI cùng file ở bước đính kèm sau khi đã OCR lúc fill: đọc 1 query $in cho
    # cả lô, ghi bulk chạy nền. Best-effort — lỗi cache KHÔNG được làm hỏng OCR.
    ocr_cache_enabled: bool = True
    ocr_cache_ttl_days: int = 7  # TTL tự dọn; hết hạn thì lần sau OCR lại rồi cache lại

    # Gemini OCR — provider thay thế cho raw/vintern qua cờ dưới. Thiếu GEMINI_API_KEY thì tự
    # FALLBACK về engine cũ (raw/vintern) và trace giữ nhãn cũ.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    gemini_timeout_ms: int = 120000
    gemini_max_edge: int = 2000          # cạnh dài tối đa (px) khi render — scan lớn được downscale
    gemini_jpeg_quality: int = 85        # xuất JPEG cho nhẹ payload, chữ vẫn rõ
    # HAI LỚP CỬA chống 429 mà vẫn nhanh (xem ocr_gemini._ocr_image):
    #  - gemini_concurrency: trần TỪNG hồ sơ (1 request) — để cao cho hồ sơ nhiều trang chạy nhanh.
    #  - gemini_max_inflight: trần TỔNG mỗi tiến trình worker — chặn khi đông người bung ra quá nhiều
    #    request đồng thời (N người × 16 = nổ). Mỗi trang phải qua CẢ hai cửa mới được gọi Gemini.
    gemini_concurrency: int = 16
    gemini_max_inflight: int = 24
    raw_by_gemini: bool = False          # true: mọi chỗ dùng "raw" (Google Vision) -> Gemini
    vintern_by_gemini: bool = False      # true: mọi chỗ dùng "vintern" -> Gemini

    # LLM (primary — vLLM/Qwen, OpenAI-compatible)
    llm_base_url: str = "https://spark-abf9.tail0f2e98.ts.net:8443"
    llm_model: str = "Qwen/Qwen3.6-35B-A3B"
    llm_timeout_ms: int = 60000
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1500

    # LLM fallback — OpenAI (dùng khi primary lỗi). Để trống OPENAI_API_KEY = tắt fallback.
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"

    # Bật reasoning (enable_thinking) cho agent map. Mặc định tắt cho nhanh.
    agent_reasoning: bool = False

    # Log chi tiết LLM (lỗi primary, output) để debug. Mặc định tắt.
    llm_debug: bool = False

    # Upload limits
    max_file_size_mb: int = 30
    max_total_payload_mb: int = 100

    # Storage — nơi lưu file/ảnh của mỗi request.
    storage_dir: str = "data/uploads"

    # Phiên tải ảnh qua QR: URL công khai điện thoại quét (domain BE) + TTL tự dọn phiên.
    mobile_base_url: str = "https://trolyhoso-hcc-admin.vnekyc.vn"
    upload_session_ttl_minutes: int = 30

    # CORS
    allowed_extension_ids: str = ""
    # Origin của FE trace (web). Mặc định cho dev Vite. Phân tách bằng dấu phẩy.
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def allowed_origins(self) -> list[str]:
        ids = [i.strip() for i in self.allowed_extension_ids.split(",") if i.strip()]
        return [f"chrome-extension://{i}" for i in ids]

    @property
    def frontend_origin_list(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def allow_all_extensions(self) -> bool:
        # Không cấu hình id nào → cho phép mọi extension (chỉ nên dùng ở dev).
        return not self.allowed_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
