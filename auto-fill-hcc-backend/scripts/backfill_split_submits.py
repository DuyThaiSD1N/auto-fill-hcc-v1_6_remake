"""TÁI TẠO lần nộp bị đếm thiếu của hồ sơ CHỨNG THỰC tách đa tab (kênh Handfree).

Áp cho cả 3 thủ tục có chế độ tách: bản sao, chữ ký, chữ ký người dịch (CTV). Số hồ sơ của
một lượt đa tab: bản sao/CTV = số tệp; CHỮ KÝ = số tệp TRỪ giấy tờ tùy thân (CCCD chỉ đi kèm
hồ sơ đầu, không thành hồ sơ riêng) — sao y quy tắc thống kê để hai bên khớp nhau.

Vì sao cần: chứng thực bản sao chế độ ĐA TAB tách mỗi tài liệu thành một hồ sơ riêng trên một
tab riêng, công dân nộp ở TỪNG tab. Handfree trước bản sửa chỉ ghi được lần nộp ở tab GỐC (tab có
sidebar) — cú bấm "Nộp" ở tab tách bị extension bỏ. Hệ quả: nộp 4 hồ sơ, `dossiers` chỉ ghi 1.

Cách tái tạo (theo yêu cầu): số lần nộp phải bằng số tệp của lượt đính kèm đa tab. Thiếu bao
nhiêu thì nhân bản đúng sự kiện nộp đã có — GIỮ NGUYÊN thời điểm và mã hồ sơ — cho đủ.
  Ví dụ: đính kèm "(đa tab) 4 tệp", đang có 1 lần nộp (16:00, mã 144725)
         → thêm 3 lần nộp y hệt (16:00, mã 144725) → đủ 4.

CHỈ đụng hồ sơ thoả TẤT CẢ:
  1. experience = handfree — bản Auto-fill popup đã đếm đúng từ trước; thêm vào đó là BỊA.
  2. procedure  ∈ {chung-thuc-ban-sao, chung-thuc-chu-ky, chung-thuc-chu-ky-nguoi-dich-ctv}.
  3. ĐÃ có ít nhất 1 lần nộp — chưa nộp lần nào thì không có gì để nhân bản, và cũng không
     biết công dân có nộp thật hay không.
  4. Có trace đính kèm split=true (đa tab), status=done.
  5. Số lần nộp hiện tại < số hồ sơ của lượt đa tab đó.

Hồ sơ MƠ HỒ (nhiều lượt đa tab với số tệp KHÁC nhau) KHÔNG tự sửa — liệt kê riêng để xem tay,
trừ khi thêm --gom-mo-ho (khi đó lấy lượt đa tab MỚI NHẤT).

An toàn:
  - Mặc định CHẠY THỬ, không ghi gì. Phải thêm --apply mới ghi.
  - Sự kiện tái tạo mang cờ `reconstructed: true` — màn quản trị KHÔNG hiện cờ này (chỉ hiện
    giờ + mã) nên nhìn y như thật, nhưng vẫn lọc/gỡ lại được bằng --revert.
  - Ghi có điều kiện `submit_count` không đổi từ lúc đọc → chạy 2 lần song song hay có lần nộp
    thật chen vào giữa cũng không cộng dồn sai.
  - Chạy lại nhiều lần an toàn: hồ sơ đã đủ thì tự bỏ qua.

MẶC ĐỊNH CHỈ CHỨNG THỰC BẢN SAO. Hai thủ tục kia phải gọi đích danh (--thu-tuc chu-ky / ctv /
tat-ca). Trước đây mặc định là cả 3: chạy thử có cờ mà lúc --apply quên cờ là ghi lan sang chữ
ký/CTV — mà quy tắc đếm chữ ký (trừ giấy tờ tùy thân) lệch với bản sao, sai là số liệu sai thật.

Chạy trên server (thư mục backend):
  python -m scripts.backfill_split_submits                       # chạy thử bản sao, in bảng
  python -m scripts.backfill_split_submits --apply               # ghi thật (bản sao)
  python -m scripts.backfill_split_submits --ho-so <id>          # chỉ 1 hồ sơ
  python -m scripts.backfill_split_submits --thu-tuc chu-ky      # chỉ chứng thực chữ ký
  python -m scripts.backfill_split_submits --thu-tuc tat-ca      # cả 3 thủ tục
  python -m scripts.backfill_split_submits --tu 2026-09-01 --den 2026-09-18
  python -m scripts.backfill_split_submits --revert --apply      # gỡ sự kiện tái tạo (theo --thu-tuc)
"""
import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient  # noqa: E402

from app.config import settings  # noqa: E402

# Ba thủ tục chứng thực đều có chế độ tách đa tab trên Handfree → cùng dính lỗi chỉ đếm tab gốc.
PROCEDURES = ("chung-thuc-ban-sao", "chung-thuc-chu-ky", "chung-thuc-chu-ky-nguoi-dich-ctv")
SHORT = {"chung-thuc-ban-sao": "bản sao", "chung-thuc-chu-ky": "chữ ký",
         "chung-thuc-chu-ky-nguoi-dich-ctv": "CTV"}
EXPERIENCE = "handfree"
# Chữ ký: giấy tờ tùy thân chỉ đi kèm hồ sơ ĐẦU (STT2), KHÔNG thành hồ sơ riêng → không tính vào
# số hồ sơ. Sao y NGUYÊN quy tắc thống kê (app/traces/repo.py::legacy_split_count) để số lần nộp
# sau khi bổ sung khớp đúng số hồ sơ dashboard đang đếm.
IDENTITY_RE = re.compile(
    r"cccd|căn\s*cước|can\s*cuoc|chứng\s*minh|chung\s*minh|"
    r"hộ\s*chiếu|ho\s*chieu|passport|giấy\s*tờ\s*tùy\s*thân",
    re.IGNORECASE,
)
# Khớp app/dossiers/repo.py::_MAX_SUBMIT_EVENTS — mảng sự kiện được cắt giữ 50 bản cuối.
MAX_SUBMIT_EVENTS = 50
VN = timezone(timedelta(hours=7))


def _fmt(dt) -> str:
    if not isinstance(dt, datetime):
        return "—"
    aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(VN).strftime("%H:%M %d/%m/%Y")


def _parse_day(value: str | None, *, end: bool = False) -> datetime | None:
    """Ngày theo giờ VIỆT NAM → mốc UTC naive (Mongo lưu naive UTC)."""
    if not value:
        return None
    day = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=VN)
    if end:
        day += timedelta(days=1)
    return day.astimezone(timezone.utc).replace(tzinfo=None)


def _split_traces(db, dossier_id: str) -> list[dict]:
    """Các lượt đính kèm ĐA TAB đã chạy xong của hồ sơ, cũ → mới."""
    return list(db.traces.find(
        {"dossier_id": dossier_id, "kind": "attach", "split": True, "status": "done"},
        {"attachments": 1, "created_at": 1},
    ).sort("created_at", 1))


def dossier_count(trace: dict, procedure: str) -> int:
    """Số hồ sơ mà một lượt đa tab tạo ra trên cổng.

    Bản sao / CTV: mỗi tệp một hồ sơ. Chữ ký: bỏ giấy tờ tùy thân (chỉ kèm hồ sơ đầu). Tối
    thiểu 1 — giống thống kê.
    """
    items = trace.get("attachments") or []
    if procedure == "chung-thuc-chu-ky":
        items = [
            a for a in items
            if not IDENTITY_RE.search(f"{a.get('name') or ''} {a.get('role') or ''}")
        ]
    return max(1, len(items)) if trace.get("attachments") else 0


def _template_event(doc: dict) -> dict | None:
    """Sự kiện nộp để nhân bản: sự kiện THẬT cuối cùng trong nhật ký.

    Hồ sơ cũ có thể có submit_count mà mảng rỗng (ghi trước khi có mảng) → dựng lại từ các
    trường rút gọn ở cấp hồ sơ — cùng một dữ liệu nên giờ và mã vẫn y nguyên.
    """
    real = [e for e in (doc.get("submit_events") or []) if not e.get("reconstructed")]
    if real:
        last = real[-1]
        event = {"at": last.get("at")}
        if last.get("host"):
            event["host"] = last["host"]
        if last.get("ref"):
            event["ref"] = last["ref"]
        return event if event["at"] else None
    if doc.get("submit_clicked_at"):
        event = {"at": doc["submit_clicked_at"]}
        if doc.get("portal_host"):
            event["host"] = doc["portal_host"]
        if doc.get("portal_dossier_ref"):
            event["ref"] = doc["portal_dossier_ref"]
        return event
    return None


def plan_backfill(db, *, dossier_id=None, date_from=None, date_to=None, take_ambiguous=False,
                  procedures=PROCEDURES):
    """Trả (cần_sửa, mơ_hồ): mỗi mục là dict mô tả hồ sơ + số lần nộp cần thêm."""
    query: dict = {
        "experience": EXPERIENCE,
        "procedure": {"$in": list(procedures)},
        "submit_count": {"$gte": 1},
    }
    if dossier_id:
        query["_id"] = dossier_id
    if date_from or date_to:
        rng: dict = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lt"] = date_to
        query["started_at"] = rng

    todo, ambiguous = [], []
    for doc in db.dossiers.find(query):
        traces = _split_traces(db, doc["_id"])
        if not traces:
            continue  # không có lượt đa tab → gộp 1 hồ sơ, 1 lần nộp là đúng
        procedure = doc.get("procedure") or ""
        counts = [dossier_count(t, procedure) for t in traces]
        latest = traces[-1]
        expected = counts[-1]
        current = int(doc.get("submit_count") or 0)
        if expected <= current:
            continue  # đã đủ (hoặc thừa do bấm hụt rồi bấm lại) → không đụng
        row = {
            "id": doc["_id"],
            "procedure": procedure,
            "ward": doc.get("ward") or "",
            "name": doc.get("name") or doc.get("username") or "",
            "current": current,
            "expected": expected,
            "missing": expected - current,
            "attach_at": latest.get("created_at"),
            "split_counts": counts,
            "template": _template_event(doc),
        }
        # Nhiều lượt đa tab mà số tệp KHÁC nhau → không chắc hồ sơ thật có bao nhiêu.
        if len(set(counts)) > 1 and not take_ambiguous:
            ambiguous.append(row)
            continue
        if not row["template"]:
            ambiguous.append({**row, "reason": "không có sự kiện nộp để nhân bản"})
            continue
        todo.append(row)
    return todo, ambiguous


def apply_backfill(db, rows: list[dict]) -> int:
    done = 0
    for row in rows:
        clones = [{**row["template"], "reconstructed": True} for _ in range(row["missing"])]
        # Điều kiện submit_count KHÔNG ĐỔI kể từ lúc đọc: có lần nộp thật chen vào giữa hay
        # chạy 2 lần song song thì update không khớp → bỏ qua, không cộng dồn sai.
        res = db.dossiers.update_one(
            {"_id": row["id"], "submit_count": row["current"]},
            {
                "$inc": {"submit_count": row["missing"]},
                "$push": {"submit_events": {"$each": clones, "$slice": -MAX_SUBMIT_EVENTS}},
                "$set": {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None)},
            },
        )
        if res.modified_count:
            done += 1
        else:
            print(f"  ! bỏ qua {row['id']}: số lần nộp đã đổi trong lúc chạy — chạy lại để tính lại")
    return done


def revert_backfill(db, *, dossier_id=None, write=False, procedures=PROCEDURES) -> int:
    """Gỡ sự kiện tái tạo và trừ lại submit_count tương ứng — CHỈ trong các thủ tục được chọn,
    để gỡ đợt bản sao không kéo theo đợt chữ ký đã chạy riêng trước đó."""
    query: dict = {"submit_events.reconstructed": True, "procedure": {"$in": list(procedures)}}
    if dossier_id:
        query["_id"] = dossier_id
    n = 0
    for doc in db.dossiers.find(query, {"submit_events": 1, "submit_count": 1}):
        extra = sum(1 for e in doc.get("submit_events") or [] if e.get("reconstructed"))
        print(f"  {doc['_id']}: gỡ {extra} lần nộp tái tạo "
              f"({doc.get('submit_count')} → {int(doc.get('submit_count') or 0) - extra})")
        if write and extra:
            db.dossiers.update_one(
                {"_id": doc["_id"]},
                {"$pull": {"submit_events": {"reconstructed": True}},
                 "$inc": {"submit_count": -extra}},
            )
        n += 1
    return n


def _print_rows(title: str, rows: list[dict]) -> None:
    print(f"\n{title} ({len(rows)} hồ sơ)")
    if not rows:
        return
    print(f"  {'Mã hồ sơ':<26} {'Thủ tục':<9} {'Phường':<22} {'Đính kèm đa tab':<18} {'Nộp':>4} {'Cần':>4} {'Thêm':>5}  Nhân bản từ")
    for r in rows:
        tpl = r.get("template") or {}
        src = f"{_fmt(tpl.get('at'))} · mã {tpl.get('ref') or '—'}" if tpl else r.get("reason", "—")
        note = f"  [các lượt: {r['split_counts']}]" if len(set(r["split_counts"])) > 1 else ""
        print(f"  {str(r['id']):<26} {SHORT.get(r.get('procedure'), r.get('procedure') or ''):<9} "
              f"{r['ward'][:22]:<22} {_fmt(r['attach_at']):<18} "
              f"{r['current']:>4} {r['expected']:>4} {r['missing']:>5}  {src}{note}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Tái tạo lần nộp bị đếm thiếu của chứng thực bản sao đa tab.")
    ap.add_argument("--apply", action="store_true", help="GHI thật (mặc định chỉ chạy thử)")
    ap.add_argument("--revert", action="store_true", help="gỡ toàn bộ sự kiện đã tái tạo")
    ap.add_argument("--ho-so", dest="dossier_id", help="chỉ xử lý 1 hồ sơ")
    ap.add_argument("--tu", help="lọc hồ sơ BẮT ĐẦU từ ngày (YYYY-MM-DD, giờ VN)")
    ap.add_argument("--den", help="lọc hồ sơ BẮT ĐẦU đến hết ngày (YYYY-MM-DD, giờ VN)")
    ap.add_argument("--thu-tuc", choices=["ban-sao", "chu-ky", "ctv", "tat-ca"], default="ban-sao",
                    help="loại chứng thực cần xử lý (mặc định: CHỈ bản sao)")
    ap.add_argument("--gom-mo-ho", action="store_true",
                    help="sửa cả hồ sơ mơ hồ (nhiều lượt đa tab số tệp khác nhau) theo lượt MỚI NHẤT")
    args = ap.parse_args()

    client = MongoClient(settings.mongo_dsn)
    db = client[settings.mongo_db]
    mode = "GHI THẬT" if args.apply else "CHẠY THỬ (không ghi)"
    procedures = PROCEDURES if args.thu_tuc == "tat-ca" else (
        {"ban-sao": "chung-thuc-ban-sao", "chu-ky": "chung-thuc-chu-ky",
         "ctv": "chung-thuc-chu-ky-nguoi-dich-ctv"}[args.thu_tuc],
    )
    print(f"Thủ tục: {', '.join(SHORT[p] for p in procedures)}")

    if args.revert:
        print(f"== GỠ sự kiện tái tạo — {mode} ==")
        n = revert_backfill(db, dossier_id=args.dossier_id, write=args.apply, procedures=procedures)
        print(f"\n{'Đã gỡ' if args.apply else 'Sẽ gỡ'} ở {n} hồ sơ.")
        return

    todo, ambiguous = plan_backfill(
        db, dossier_id=args.dossier_id,
        date_from=_parse_day(args.tu), date_to=_parse_day(args.den, end=True),
        take_ambiguous=args.gom_mo_ho,
        procedures=procedures,
    )
    print(f"== Tái tạo lần nộp chứng thực đa tab — {mode} ==")
    _print_rows("CẦN BỔ SUNG", todo)
    _print_rows("MƠ HỒ — BỎ QUA, CẦN XEM TAY", ambiguous)
    total_add = sum(r["missing"] for r in todo)
    print(f"\nTổng: {len(todo)} hồ sơ, thêm {total_add} lần nộp.")

    if not args.apply:
        print("→ Chưa ghi gì. Xem bảng trên rồi chạy lại với --apply để ghi.")
        return
    done = apply_backfill(db, todo)
    print(f"→ Đã ghi {done}/{len(todo)} hồ sơ.")


if __name__ == "__main__":
    main()
