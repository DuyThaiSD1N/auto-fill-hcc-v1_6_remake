from fastapi import APIRouter, Depends

from app.core.deps import require_auth
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.procedures.registry import public_list

router = APIRouter(prefix="/api/v1", tags=["procedures"])


@router.get("/procedures")
async def procedures(_: dict = Depends(require_auth)):
    return {"procedures": with_ke_khai_detect_urls(public_list())}


# Danh mục link kê khai: chỉ là URL công khai trên Cổng DVC quốc gia, KHÔNG kèm dữ liệu hồ sơ.
# Để mở (không require_auth) vì extension dựng ô "Đi đến thủ tục" ngay lúc mở panel, trước cả khi
# cán bộ đăng nhập — giữ đúng hành vi hồi danh mục còn đóng gói trong extension.
@router.get("/procedures/ke-khai-links")
async def ke_khai_links():
    return {"links": KE_KHAI_LINKS}
