from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.deps import require_auth
from app.dossiers.rating_card import RATING_CARD
from app.procedures.ke_khai_links import (
    KE_KHAI_LINKS,
    account_province_slug,
    link_province_slugs,
    procedure_province_slugs,
    visible_in_province,
    with_ke_khai_detect_urls,
    with_province_only,
)
from app.procedures.portal_submit import portal_submit_rules
from app.procedures.registry import public_list

router = APIRouter(prefix="/api/v1", tags=["procedures"])

_bearer = HTTPBearer(auto_error=False)


async def _optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    # Có gửi token thì token phải hợp lệ (401 để extension refresh rồi gọi lại), không gửi thì
    # coi như khách — extension bản cũ gọi trơn trước khi đăng nhập.
    if not creds or not creds.credentials:
        return None
    return await require_auth(creds)


@router.get("/procedures")
async def procedures(user: dict = Depends(require_auth)):
    # portalSubmit đi ghép ở đây thay vì đẻ endpoint riêng: popup đã gọi /procedures ngay khi
    # mở panel, và luật nhận nút nộp cũng là config theo cổng như detect/label. Extension bản
    # cũ bỏ qua khóa lạ nên không vỡ.
    # ratingCard đi cùng vì lý do y hệt: câu chữ phiếu đánh giá là config server-driven, và
    # Handfree đã dùng chính bộ này qua đường chat. Một nguồn, hai kênh.
    # Thủ tục riêng của tỉnh (provinceOnly) chỉ trả cho tài khoản đúng tỉnh — lọc ở đây nên
    # extension không thấy, không tự nhận diện được thủ tục tỉnh khác.
    listed = with_province_only(public_list(), procedure_province_slugs)
    return {
        "procedures": with_ke_khai_detect_urls(
            visible_in_province(listed, account_province_slug(user))
        ),
        "portalSubmit": portal_submit_rules(),
        "ratingCard": RATING_CARD,
    }


# Danh mục link kê khai: chỉ là URL công khai trên Cổng DVC quốc gia, KHÔNG kèm dữ liệu hồ sơ.
# Để mở (không require_auth) vì extension dựng ô "Đi đến thủ tục" ngay lúc mở panel, trước cả khi
# cán bộ đăng nhập — giữ đúng hành vi hồi danh mục còn đóng gói trong extension. Có token thì lọc
# thủ tục riêng của tỉnh theo tài khoản như /procedures; extension nạp lại sau khi đăng nhập.
@router.get("/procedures/ke-khai-links")
async def ke_khai_links(user: dict | None = Depends(_optional_user)):
    if user is None:
        return {"links": KE_KHAI_LINKS}
    by_key = {str(p.get("key") or ""): p for p in public_list()}
    links = with_province_only(KE_KHAI_LINKS, lambda link: link_province_slugs(link, by_key))
    return {"links": visible_in_province(links, account_province_slug(user))}
