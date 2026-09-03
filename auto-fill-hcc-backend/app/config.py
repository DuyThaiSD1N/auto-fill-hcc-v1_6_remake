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

    # OCR Tiếng Nói vintern-v12 — provider chính; batch nhiều file, tự tách PDF + xoay ảnh.
    ocr_tiengnoi_base_url: str = "https://troly-hcc.tiengnoi.vn"
    ocr_tiengnoi_api_key: str = ""
    ocr_tiengnoi_timeout_ms: int = 120000
    fallback_ocr_tiengnoi_base_url: str = ""
    fallback_ocr_tiengnoi_api_key: str = ""
    ocr_tiengnoi_max_tokens: int = 1500  # classify không cần dày → giảm cho nhanh
    ocr_tiengnoi_fill_max_tokens: int = 4096  # FILL cần text ĐẦY ĐỦ (nhiều trang) → cao hơn classify
    # Bước phân loại đính kèm vẫn dùng Tiếng Nói nhưng cắt ít trang/token để phản hồi nhanh.
    attach_classify_max_pages: int = 2     # OCR tối đa N trang đầu (loại/tên luôn ở trang 1-2)
    attach_classify_char_limit: int = 800  # cắt OCR text đưa vào LLM (tiêu đề/tên ở đầu)
    attach_classify_max_tokens: int = 300  # output classify nhỏ ({"d":[{t,n}]})

    # Cache OCR text theo HASH nội dung file (namespace v2-tiengnoi).
    # Bù cho việc OCR LẠI cùng file ở bước đính kèm sau khi đã OCR lúc fill: đọc 1 query $in cho
    # cả lô, ghi bulk chạy nền. Best-effort — lỗi cache KHÔNG được làm hỏng OCR.
    ocr_cache_enabled: bool = True
    ocr_cache_ttl_hours: int = 12  # TTL tự dọn; hết hạn thì lần sau OCR lại rồi cache lại

    # LLM (primary — vLLM/Qwen, OpenAI-compatible)
    llm_base_url: str = "https://spark-abf9.tail0f2e98.ts.net:8443"
    llm_model: str = "Qwen/Qwen3.6-35B-A3B"
    llm_timeout_ms: int = 60000
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1500

    # LLM DỰ PHÒNG cấp 1 — mirror vLLM cùng contract (OpenAI-compatible), thử TRƯỚC khi rơi
    fallback_llm_base_url: str = ""
    fallback_llm_model: str = ""

    # OPENAI_API_KEY = tắt tầng OpenAI.
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"

    # Bật reasoning (enable_thinking) cho agent map. Mặc định tắt cho nhanh.
    agent_reasoning: bool = False

    # Log chi tiết LLM (lỗi primary, output) để debug. Mặc định tắt.
    llm_debug: bool = False

    # Upload limits
    max_file_size_mb: int = 80
    max_total_payload_mb: int = 100
    # Capability riêng cho URL QR; để trống chỉ dùng JWT refresh secret làm fallback
    # tương thích deployment cũ. Production nên cấu hình secret riêng.
    upload_capability_secret: str = ""

    # Storage — nơi lưu file/ảnh của mỗi request.
    storage_dir: str = "data/uploads"

    # Batch server-to-server: API chỉ nhận/lưu hồ sơ, worker riêng mới OCR + LLM. Secret để
    # trống = khóa toàn bộ API batch; không dùng chung JWT người dùng/extension.
    batch_api_secret: str = ""
    batch_storage_dir: str = "data/batch"
    batch_worker_concurrency: int = 2
    batch_max_pending_items: int = 5000
    batch_max_attempts: int = 3
    batch_lease_seconds: int = 600
    batch_poll_seconds: float = 1.0
    batch_min_free_disk_mb: int = 1024

    # Phiên tải ảnh qua QR: URL công khai điện thoại quét (domain BE) + TTL tự dọn phiên.
    mobile_base_url: str = "https://trolyhoso-hcc-admin.vnekyc.vn"
    upload_session_ttl_minutes: int = 30
    upload_session_ttl_hours: int = 24
    review_capability_ttl_seconds: int = 3600

    # Bật dần channel Handfree sau khi staging đã qua test; Auto Fill không phụ thuộc cờ này.
    handfree_enabled: bool = False

    # Voice chỉ thuộc channel Handfree. Để trống URI/token tương ứng = tắt tính năng trên
    # /api/v1/voice/config; extension Auto Fill không dùng các cấu hình này.
    asr_grpc_uri: str = ""
    asr_grpc_token: str = ""
    asr_rate: int = 16000
    asr_silence_timeout: int = 10
    asr_speech_timeout: float = 1.8
    asr_speech_max: int = 30
    tts_ws_url: str = ""
    tts_api_key: str = ""
    tts_voice: str = "phuongnhi-north"
    tts_resample_rate: int = 16000
    tts_tempo: float = 0.95
    asr_grpc_uri_hmong: str = ""
    tts_ws_url_hmong: str = ""
    tts_voice_hmong: str = "xi"

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
