"""Thử: độ chắc của Qwen (logprobs) có tách được cảnh báo TRÚNG khỏi cảnh báo NHẦM không, và mất bao lâu.

Đầu vào: thư mục chấm (nhom*.json = cờ luồng mới, ket_qua*.json = agent chấm bằng mắt) và thư mục kết quả luồng
mới (lấy v1). Hai cách đọc của Qwen (xem trich_qwen.py): A = từng trang chép ô chính, B = nguyên bộ trích xuất
đọc từ ảnh. Với mỗi ô đã chấm: Qwen đọc ra gì, chắc bao nhiêu, có khác v1 không, có đúng giấy không.

Chạy (từ auto-fill-hcc-backend):
  .venv/bin/python -m scripts.luongmoi.thu_do_chac --cham <dir> --luongmoi <dir> [--cach A B] [--bo req_x ...]
"""
from __future__ import annotations

import argparse
import asyncio
import difflib
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from scripts.luongmoi import du_lieu, trich_qwen

_TAUS = (0.5, 0.7, 0.8, 0.9, 0.95)


# ------------------------------------------------------------------ so sánh theo loại ô

def _nfc(s) -> str:
    return unicodedata.normalize("NFC", str(s or ""))


def _fold(s) -> str:
    text = unicodedata.normalize("NFD", _nfc(s)).replace("đ", "d").replace("Đ", "D")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").upper()
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", text).split())


def _tone(s) -> str:
    return " ".join(_nfc(s).upper().split())


def _digits(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


_DATE_RE = re.compile(r"(\d{1,2})\s*(?:[/.\-]|tháng)\s*(\d{1,2})\s*(?:[/.\-]|năm)\s*(\d{4})", re.I)


def _dates(s) -> list[tuple]:
    return [(int(d), int(m), int(y)) for d, m, y in _DATE_RE.findall(_nfc(s))]


_ABBR = (("UBND", "UY BAN NHAN DAN"), ("TAND", "TOA AN NHAN DAN"), ("TP ", "THANH PHO "), ("CSQLHC", "CANH SAT QUAN LY HANH CHINH"))


def _text_key(s) -> str:
    text = _fold(s)
    for short, full in _ABBR:
        text = text.replace(short, full)
    return text


def kind(field: str) -> str | None:
    if re.search(r"NoiCuTru|Address|Purpose|LaBanThan|TinhTrang|Period|_\d$", field):
        return None
    tail = field.split("_", 1)[-1]
    if re.search(r"HoTen|Name$", tail):
        return "ten"
    if re.search(r"NgaySinh|DoB|NgayCap|IdDate|Date", tail):
        return "ngay"
    if re.search(r"SoDinhDanh|IdNumber", tail):
        return "so"
    if "Number" in tail:
        return "so_giay"
    return "chu"


def same(k: str, a, b) -> bool:
    if k == "ten":
        return _tone(a) == _tone(b)
    if k == "ngay":
        da, db = _dates(a), _dates(b)
        return da[:1] == db[:1] if da and db else _tone(a) == _tone(b)
    if k == "so":
        return bool(_digits(a)) and _digits(a) == _digits(b)
    if k == "so_giay":
        return re.sub(r"\s", "", _nfc(a).upper()) == re.sub(r"\s", "", _nfc(b).upper())
    ka, kb = _text_key(a), _text_key(b)
    return bool(ka and kb) and (ka in kb or kb in ka or difflib.SequenceMatcher(None, ka, kb).ratio() >= 0.85)


def in_truth(k: str, q, truth) -> bool:
    """Giá trị Qwen có khớp chữ trên giấy (theo ghi chép của người chấm) không — gần đúng."""
    truth = json.dumps(truth, ensure_ascii=False) if isinstance(truth, (dict, list)) else str(truth or "")
    if k == "ten":
        return bool(_tone(q)) and _tone(q) in _tone(truth)
    if k == "ngay":
        dq = _dates(q)
        return bool(dq) and dq[0] in _dates(truth)
    if k == "so":
        return bool(_digits(q)) and _digits(q) in re.findall(r"\d{6,}", truth)
    if k == "so_giay":
        return re.sub(r"\s", "", _nfc(q).upper()) in re.sub(r"\s", "", _nfc(truth).upper())
    return same("chu", q, truth) or _text_key(q) in _text_key(truth)


# ------------------------------------------------------------------ cách A: ghép ô v1 ↔ giá trị Qwen chép theo giấy

def _docs(pages: list[dict]) -> list[dict]:
    docs = []
    for page in pages:
        by_doc: dict[int, dict] = defaultdict(dict)
        for v in page["values"]:
            path = v["path"]
            if len(path) >= 3 and path[0] == "giay" and isinstance(path[1], int):
                by_doc[path[1]][tuple(path[2:])] = (v["value"], v["p"], v["weak"])
        for k in sorted(by_doc):
            vals = by_doc[k]
            docs.append({"loai": (vals.get(("loai",)) or ("",))[0], "tep": page["tep"], "trang": page["trang"], "vals": vals})
    return docs


_TK_YC = {"HoTen": "ho_ten", "NgaySinh": "ngay_sinh", "SoDinhDanh": "so_giay_to", "NgayCapGiayTo": "ngay_cap",
          "NoiCapGiayTo": "noi_cap", "QuanHe": "quan_he"}
_TK_DC = {"HoTen": "ho_ten", "NgaySinh": "ngay_sinh", "GioiTinh": "gioi_tinh", "DanToc": "dan_toc",
          "QuocTich": "quoc_tich", "SoDinhDanh": "so_giay_to", "NgayCapGiayTo": "ngay_cap", "NoiCapGiayTo": "noi_cap"}
_CARD_FRONT = {"HoTen": "ho_ten", "SoDinhDanh": "so", "NgaySinh": "ngay_sinh", "GioiTinh": "gioi_tinh", "QuocTich": "quoc_tich"}
_CARD_BACK = {"NgayCap": "ngay_cap", "NoiCap": "noi_cap"}
_POA = {"SubjectName": "ho_ten", "SubjectDoB": "ngay_sinh", "SubjectIdNumber": "so_giay_to", "SubjectIdDate": "ngay_cap",
        "SubjectIssuer": "noi_cap"}
_CIVIL = {"DeathCert": ("khai_tu", {"Number": "so", "Date": "ngay_cap", "Agency": "co_quan_cap"}),
          "DivorceDecision": ("ly_hon", {"Number": "so", "Date": "ngay", "Agency": "co_quan"}),
          "Marriage": ("ket_hon", {"Number": "so", "Date": "ngay_dang_ky", "Agency": "co_quan"})}


def _person_score(front: dict, v1: dict, prefix: str, skip: str) -> int:
    score = 0
    name, num, dob = (front["vals"].get((k,), ("",))[0] for k in ("ho_ten", "so", "ngay_sinh"))
    if skip != "HoTen" and v1.get(prefix + "HoTen") and _fold(name) == _fold(v1[prefix + "HoTen"]):
        score += 2
    if skip != "SoDinhDanh" and v1.get(prefix + "SoDinhDanh"):
        a, b = _digits(num), _digits(v1[prefix + "SoDinhDanh"])
        score += 2 if a and a == b else (1 if len(a) == len(b) == 12 and sum(x == y for x, y in zip(a, b)) >= 9 else 0)
    if skip != "NgaySinh" and v1.get(prefix + "NgaySinh") and _dates(dob)[:1] == _dates(v1[prefix + "NgaySinh"])[:1] != []:
        score += 1
    return score


def _back_of(front: dict, backs: list[dict]) -> dict | None:
    num = _digits(front["vals"].get(("so",), ("",))[0])
    for back in backs:
        mrz = "".join(str(back["vals"].get(("mrz", i), ("",))[0]) for i in range(3))
        if num and (num in mrz or num[-9:] in mrz):
            return back
    same_file = [b for b in backs if b["tep"] == front["tep"]]
    if len(same_file) == 1:
        return same_file[0]
    return backs[0] if len(backs) == 1 else None


def _pick(cands: list[tuple], k: str, v1_value) -> tuple | None:
    """Nhiều giấy cùng loại → lấy bản khớp v1 nhất (giống cách code sẽ hỏi: có giấy nào ủng hộ v1 không)."""
    cands = [c for c in cands if c and c[0] not in (None, "")]
    if not cands:
        return None
    return max(cands, key=lambda c: (same(k, v1_value, c[0]),
                                     difflib.SequenceMatcher(None, _fold(c[0]), _fold(v1_value)).ratio()))


def qwen_a(field: str, docs: list[dict], v1: dict) -> tuple | None:
    """Giá trị Qwen (cách A) cho một ô v1 → (giá trị, p, chữ yếu, nguồn) hoặc None khi không ghép được."""
    k = kind(field)
    prefix, tail = field.split("_", 1)
    of = lambda loai: [d for d in docs if d["loai"] == loai]  # noqa: E731
    label = lambda d, key: (*d["vals"][key], f"{d['loai']} tệp {d['tep'] + 1} trang {d['trang'] + 1}")  # noqa: E731
    cands: list[tuple] = []
    if prefix == "ToKhaiYeuCau" and tail in _TK_YC:
        cands = [label(d, ("nguoi_yeu_cau", _TK_YC[tail])) for d in of("to_khai") if ("nguoi_yeu_cau", _TK_YC[tail]) in d["vals"]]
    elif prefix == "ToKhai" and tail in _TK_DC:
        cands = [label(d, ("nguoi_duoc_cap", _TK_DC[tail])) for d in of("to_khai") if ("nguoi_duoc_cap", _TK_DC[tail]) in d["vals"]]
    elif prefix in ("NguoiDuocCap", "NguoiYeuCau") and (tail in _CARD_FRONT or tail in _CARD_BACK):
        fronts = of("the_mat_truoc")
        if not fronts:
            return None
        front = max(fronts, key=lambda d: _person_score(d, v1, prefix + "_", tail))
        if tail in _CARD_FRONT:
            key = (_CARD_FRONT[tail],)
            return label(front, key) if key in front["vals"] else None
        back = _back_of(front, of("the_mat_sau"))
        key = (_CARD_BACK[tail],)
        return label(back, key) if back and key in back["vals"] else None
    elif prefix == "PoA" and tail in _POA:
        cands = [label(d, ("ben_uy_quyen", _POA[tail])) for d in of("uy_quyen") if ("ben_uy_quyen", _POA[tail]) in d["vals"]]
    elif prefix in _CIVIL and tail in _CIVIL[prefix][1]:
        loai, keys = _CIVIL[prefix]
        cands = [label(d, (keys[tail],)) for d in of(loai) if (keys[tail],) in d["vals"]]
    elif prefix == "Marriage" and tail == "SpouseName":
        subject = _fold(v1.get("NguoiDuocCap_HoTen") or v1.get("ToKhai_HoTen") or "")
        cands = [label(d, (who, "ho_ten")) for d in of("ket_hon") for who in ("chong", "vo")
                 if (who, "ho_ten") in d["vals"] and _fold(d["vals"][(who, "ho_ten")][0]) != subject]
    elif field == "GiayToKhac_DanToc":
        cands = [label(d, ("dan_toc",)) for d in of("cu_tru") if ("dan_toc",) in d["vals"]]
    return _pick(cands, k, v1.get(field))


def qwen_b(field: str, res: dict) -> tuple | None:
    for v in res.get("values") or []:
        if v["path"] == ["fields", field]:
            return v["value"], v["p"], v["weak"], "nguyên bộ trích xuất"
    return None


# ------------------------------------------------------------------ MRZ mặt sau thẻ (chữ số kiểm tra ICAO 9303)

def _check_digit(s: str) -> str:
    val = lambda c: int(c) if c.isdigit() else (0 if c == "<" else ord(c) - 55)  # noqa: E731
    return str(sum(val(c) * w for c, w in zip(s, [7, 3, 1] * 20)) % 10)


def mrz_facts(docs: list[dict]) -> list[dict]:
    """Mỗi mặt sau thẻ có MRZ đúng chữ số kiểm tra → {so9, so12, ngay_sinh} chắc chắn."""
    out = []
    for back in (d for d in docs if d["loai"] == "the_mat_sau"):
        l1, l2 = (re.sub(r"\s", "", str(back["vals"].get(("mrz", i), ("",))[0])).upper() for i in range(2))
        if len(l1) < 15 or len(l2) < 7:
            continue
        fact = {}
        if _check_digit(l1[5:14]) == l1[14]:
            fact["so9"] = l1[5:14]
            full = re.search(r"\d{12}", l1[15:])
            fact["so12"] = full.group(0) if full else None
        if _check_digit(l2[0:6]) == l2[6] and l2[:6].isdigit():
            yy, mm, dd = int(l2[0:2]), int(l2[2:4]), int(l2[4:6])
            century = None
            if fact.get("so12"):
                century = {"0": 1900, "1": 1900, "2": 2000, "3": 2000}.get(fact["so12"][3])
            fact["ngay_sinh"] = (dd, mm, (century or (1900 if yy > 30 else 2000)) + yy)
        if fact:
            out.append(fact)
    return out


def mrz_verdict(field: str, v1_value, v1: dict, facts: list[dict]) -> str | None:
    """MRZ của đúng người (khớp ≥9 chữ số định danh) nói v1 đúng hay sai; None = không áp được."""
    prefix = field.split("_", 1)[0] + "_"
    num = _digits(v1.get(prefix + "SoDinhDanh") or v1.get(prefix + "SubjectIdNumber") or "")
    if field.endswith(("SoDinhDanh", "IdNumber")):
        cand = [f for f in facts if f.get("so9") and sum(a == b for a, b in zip(num[-9:], f["so9"])) >= 7]
        # 9 chữ số cuối trùng chưa đủ: sai ở 3 chữ số đầu (mã tỉnh) chỉ lộ ra khi so cả 12 số ở phần tuỳ chọn.
        return None if not cand else ("đúng" if any((f.get("so12") or f["so9"]) == (num if f.get("so12") else num[-9:])
                                                   for f in cand) else "sai")
    if field.endswith(("NgaySinh", "DoB")):
        cand = [f for f in facts if f.get("ngay_sinh") and f.get("so9") and f["so9"] == num[-9:]]
        return None if not cand else ("đúng" if _dates(v1_value)[:1] == [cand[0]["ngay_sinh"]] else "sai")
    return None


# ------------------------------------------------------------------ chạy

def load_rows(cham: Path, bo: set[str]) -> list[dict]:
    flags = {}
    for f in sorted(cham.glob("nhom*.json")):
        for rid, items in json.loads(f.read_text(encoding="utf-8")).items():
            for it in items:
                flags[(rid, it["stt"])] = it
    rows = []
    for f in sorted(cham.glob("ket_qua*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            flag = flags.get((r["request_id"], r["stt"]))
            if flag and r["request_id"] not in bo:
                rows.append({"rid": r["request_id"], "stt": r["stt"], "field": r["field"], "flag": r["flag"],
                             "v1": flag["v1"], "ket_luan": r["ket_luan"], "tren_giay": r.get("tren_giay"),
                             "do_chac_cham": r.get("do_chac"), "co_tu_code": flag.get("de_xuat") is None
                             or str(flag.get("chot") or "").startswith("code") or "HNG" in str(flag.get("ly_do_agent") or "")})
    return rows


def _v1(luongmoi: Path, rid: str) -> dict:
    llm = json.loads((luongmoi / f"{rid}_l1.json").read_text(encoding="utf-8"))["output1"]["llm"]
    return {f["name"]: f["value"] for f in llm} if isinstance(llm, list) else llm


def evaluate(rows: list[dict], key: str) -> list[str]:
    """Bảng: luật gắn cờ × ngưỡng → số trúng/nhầm còn bị gắn cờ."""
    trung = [r for r in rows if r["ket_luan"] == "trung"]
    nham = [r for r in rows if r["ket_luan"] == "nham"]
    lines = [f"  ô ghép được: trúng {sum(1 for r in trung if r[key])}/{len(trung)} · nhầm {sum(1 for r in nham if r[key])}/{len(nham)}"]

    def count(pred):
        a, b = sum(1 for r in trung if r[key] and pred(r[key])), sum(1 for r in nham if r[key] and pred(r[key]))
        return f"trúng {a:>2}/{len(trung)} · nhầm {b:>2}/{len(nham)} · độ chính xác {a / (a + b):.0%}" if a + b else "0 cờ"

    lines.append(f"  R1 khác v1                       : {count(lambda q: not q['giong'])}")
    for tau in _TAUS:
        lines.append(f"  R2 khác HOẶC p<{tau:<4}              : {count(lambda q, t=tau: not q['giong'] or q['p'] < t)}")
    for tau in _TAUS:
        lines.append(f"  R3 khác VÀ p≥{tau:<4} (đỏ)           : {count(lambda q, t=tau: not q['giong'] and q['p'] >= t)}")
    fix = [r for r in trung if r[key] and not r[key]["giong"] and r[key]["dung_giay"]]
    lines.append(f"  trúng mà Qwen đọc ĐÚNG giấy (sửa được): {len(fix)}/{len(trung)} · p: {sorted(r[key]['p'] for r in fix)}")
    wrong_sure = [r for r in nham if r[key] and not r[key]["giong"]]
    lines.append(f"  nhầm mà Qwen vẫn khác v1: {len(wrong_sure)} · p: {sorted(r[key]['p'] for r in wrong_sure)}")
    diff_t = [r for r in trung if r[key] and not r[key]["giong"]]
    lines.append(f"  trúng mà Qwen khác v1: {len(diff_t)} · p: {sorted(r[key]['p'] for r in diff_t)}")
    same_t = [r for r in trung if r[key] and r[key]["giong"]]
    lines.append(f"  trúng mà Qwen GIỐNG v1 (cùng sai): {len(same_t)} · p: {sorted(r[key]['p'] for r in same_t)}")
    return lines


async def main() -> None:
    ap = argparse.ArgumentParser(description="Thử độ chắc Qwen trên các cờ đã chấm")
    ap.add_argument("--cham", required=True, help="thư mục nhom*.json + ket_qua*.json")
    ap.add_argument("--luongmoi", required=True, help="thư mục kết quả luồng mới (<rid>_l1.json)")
    ap.add_argument("--cach", nargs="*", default=["A", "B"])
    ap.add_argument("--bo", nargs="*", default=[], help="mã hồ sơ bỏ (trùng)")
    ap.add_argument("--flag", default="canh_bao", help="canh_bao | sua | all")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--moi", action="store_true", help="bỏ cache, gọi Qwen lại")
    args = ap.parse_args()

    rows = [r for r in load_rows(Path(args.cham), set(args.bo)) if args.flag == "all" or r["flag"] == args.flag]
    rids = sorted({r["rid"] for r in rows})
    luongmoi = Path(args.luongmoi)
    cases = {rid: du_lieu.load(rid) for rid in rids}
    v1s = {rid: _v1(luongmoi, rid) for rid in rids}
    sem = asyncio.Semaphore(args.concurrency)
    res_a, res_b = {}, {}

    async def run(rid, fn, store):
        async with sem:
            try:
                store[rid] = await fn(cases[rid], refresh=args.moi)
            except Exception as exc:  # noqa: BLE001 — lỗi từng hồ sơ không dừng cả lượt
                store[rid] = {"error": str(exc)}

    # Chạy lần lượt từng cách để thời gian đo không bị cách kia chen tải.
    if "A" in args.cach:
        await asyncio.gather(*(run(rid, trich_qwen.trich_ho_so, res_a) for rid in rids))
    if "B" in args.cach:
        await asyncio.gather(*(run(rid, trich_qwen.trich_nguyen_con, res_b) for rid in rids))

    docs = {rid: _docs(res_a[rid]["trang"]) for rid in rids if rid in res_a and "trang" in res_a[rid]}
    for r in rows:
        k, v1 = kind(r["field"]), v1s[r["rid"]]
        for key, q in (("A", qwen_a(r["field"], docs[r["rid"]], v1) if k and r["rid"] in docs else None),
                       ("B", qwen_b(r["field"], res_b[r["rid"]]) if k and r["rid"] in res_b else None)):
            r[key] = None if not q else {"q": q[0], "p": q[1], "weak": q[2], "nguon": q[3],
                                         "giong": same(k, r["v1"], q[0]), "dung_giay": in_truth(k, q[0], r["tren_giay"])}
        r["mrz"] = mrz_verdict(r["field"], r["v1"], v1, mrz_facts(docs.get(r["rid"], []))) if k else None

    lines = [f"# Thử độ chắc Qwen — {len(rows)} cờ '{args.flag}' / {len(rids)} hồ sơ",
             f"  trúng {sum(r['ket_luan'] == 'trung' for r in rows)} · nhầm {sum(r['ket_luan'] == 'nham' for r in rows)}"
             f" · ô không so được (địa chỉ/mục đích/khoảng thời gian): {sum(kind(r['field']) is None for r in rows)}"]
    for key in args.cach:
        lines += ["", f"## Cách {key}"] + evaluate([r for r in rows if kind(r["field"])], key)
    mrz = Counter((r["ket_luan"], r["mrz"]) for r in rows if r["mrz"])
    lines += ["", f"## MRZ (chữ số kiểm tra hợp lệ): {dict(mrz)}"]

    # Thời gian: cách A (các trang song song) / cách B (một lượt) / OCR Qwen toàn văn của luồng cũ.
    lines += ["", "## Thời gian mỗi hồ sơ (giây)"]
    full = []
    for rid in rids:
        cache = cases[rid]["dir"] / "ocr_qwen_cache.json"
        if cache.is_file():
            full.append(json.loads(cache.read_text(encoding="utf-8")).get("_wall_s") or 0)
    series = {"OCR Qwen toàn văn (luồng cũ)": full}
    if res_a:
        series["A trích ô chính từng trang"] = [res_a[r]["wall_s"] for r in rids if res_a[r].get("wall_s") and not res_a[r].get("cached")]
        toks = [p["out_tokens"] for r in rids for p in res_a[r].get("trang", []) if p.get("out_tokens")]
        lines.append(f"  A: {len(toks)} trang, token ra/trang trung vị {statistics.median(toks) if toks else '-'}")
    if res_b:
        series["B nguyên bộ trích xuất"] = [res_b[r]["ms"] / 1000 for r in rids if res_b[r].get("ms") and not res_b[r].get("cached")]
        ins = [res_b[r]["in_tokens"] for r in rids if res_b[r].get("in_tokens")]
        lines.append(f"  B: token vào trung vị {statistics.median(ins) if ins else '-'}")
    for name, xs in series.items():
        xs = sorted(xs)
        if xs:
            lines.append(f"  {name:32}: trung vị {statistics.median(xs):.1f} · p90 {xs[int(len(xs) * 0.9) - 1]:.1f} · max {xs[-1]:.1f}  (n={len(xs)})")
    errors = [f"{k} {rid}: {v['error']}" for k, store in (("A", res_a), ("B", res_b)) for rid, v in store.items() if v.get("error")]
    if errors:
        lines += ["", "## Lỗi"] + [f"  {e}" for e in errors]

    out_dir = du_lieu.out_root() / "_luongmoi" / (datetime.now().strftime("%Y%m%d_%H%M%S") + "_dochac")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chi_tiet.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    text = "\n".join(lines)
    (out_dir / "tong_hop.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\n→ {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
