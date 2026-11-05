"""Đo agent tra mã ngành hộ kinh doanh (chat/hkd_tro_ly/nganh_nghe.py) trên LLM thật.

    .venv/bin/python -m scripts.eval_hkd_nganh_nghe [--chi 1,5,7] [--song-song 4]

Câu mô tả tự soạn (không phải dữ liệu người dân). Mỗi ca: lời người dân → các hoạt động kỳ vọng, mỗi hoạt động là
tập mã chấp nhận được. Ca "hoi" kỳ vọng agent hỏi lại vì lời kể quá chung.
Chỉ số: chắc-đúng / chắc-SAI (phải ≈ 0) / gợi ý có đáp án / trượt / hỏi lại đúng, thời gian mỗi ca.
"""
import argparse
import asyncio
import time

from app.channels.handfree.chat.hkd_tro_ly import nganh_nghe

CASES: list[tuple[str, list[set[str]] | str, str]] = [
    ("Tôi mở quán phở bò", [{"5610"}], ""),
    ("Bán tạp hoá: gạo, mì tôm, dầu ăn, bánh kẹo, nước ngọt, bia", [{"4711"}], ""),
    ("Bán rau củ quả ở chợ", [{"4722"}], ""),
    ("Mở quán cà phê", [{"5630"}], ""),
    ("Quán trà sữa", [{"5630"}], ""),
    ("Cắt tóc, gội đầu", [{"9621"}], ""),
    ("Làm móng tay, chăm sóc da mặt", [{"9622"}], ""),
    ("Sửa xe máy", [{"9532"}], ""),
    ("Sửa chữa điện thoại di động", [{"9510"}], ""),
    ("Bán quần áo, giày dép", [{"4771"}], ""),
    ("Bán điện thoại và máy tính", [{"4740"}], ""),
    ("Nhà nghỉ cho khách thuê theo giờ, theo ngày", [{"5520", "5510"}], ""),
    ("May đo quần áo theo yêu cầu", [{"1410"}], ""),
    ("Làm bánh mì để bán", [{"1071", "5610"}], ""),  # lò bánh hay xe bánh mì kẹp — câu lưng chừng
    ("Nhà thuốc bán thuốc tây", [{"4772"}], ""),
    ("Bán xi măng, sắt thép, gạch, sơn", [{"4752"}], ""),
    ("Cây xăng bán xăng dầu cho xe máy ô tô", [{"4730"}], ""),
    ("Nuôi lợn thịt", [{"0145"}], ""),
    ("Trồng rau sạch", [{"0118"}], ""),
    ("Giặt là quần áo", [{"9610"}], ""),
    ("Chụp ảnh cưới", [{"7420"}], ""),
    ("Cho thuê ô tô tự lái", [{"7710"}], ""),
    ("Chở hàng thuê bằng xe tải", [{"4933"}], ""),
    ("Bán buôn gạo cho các đại lý", [{"4631"}], ""),
    ("Xay xát lúa gạo", [{"1061"}], ""),
    ("Kinh doanh karaoke", [{"9329"}], ""),
    ("Tiệm vàng bạc đá quý", [{"4773"}], ""),
    ("Photocopy, in ấn tài liệu cho khách", [{"8210", "1811"}], ""),
    ("Bán đồ điện gia dụng như quạt, nồi cơm điện", [{"4759"}], ""),
    ("Rửa xe máy", [{"9532"}], ""),
    ("Bán bia rượu nước giải khát", [{"4723"}], ""),
    ("Nấu cỗ đám cưới, đám giỗ theo đơn đặt", [{"5621"}], ""),
    ("Bán sách vở, văn phòng phẩm", [{"4761"}], ""),
    ("Xưởng mộc đóng tủ bàn ghế gỗ", [{"3101"}], ""),
    ("Làm cửa sắt, hàn khung sắt", [{"2511", "2592"}], ""),
    ("Bán phân bón, thuốc bảo vệ thực vật", [{"4773"}], ""),
    ("Cho thuê phòng trọ", [{"5520", "6810"}], ""),
    ("Nuôi cá trong ao", [{"0322"}], ""),
    ("Bán thịt lợn", [{"4722"}], ""),
    ("Bán xe máy", [{"4783"}], ""),
    ("Bán phụ tùng xe máy", [{"4783"}], ""),
    ("Sửa xe đạp", [{"9529"}], ""),
    ("Bán đồ chơi trẻ em", [{"4763"}], ""),
    ("Sửa chữa tivi", [{"9521"}], ""),
    ("Bán tạp hoá và sửa xe máy", [{"4711", "4719"}, {"9532"}], ""),
    ("Tôi bán cơm bình dân là chính, có bán thêm nước giải khát", [{"5610"}, {"5630", "4723"}], "5610"),
    ("Trồng rau và bán rau ngay tại vườn", [{"0118"}], ""),
    ("Tôi buôn bán", "hoi", ""),
    ("Làm dịch vụ", "hoi", ""),
    ("Bán quần áo online qua Facebook", [{"4771"}], ""),
    # Người dân nói rõ bán buôn → phải giữ mã nhóm 46 sau lượt tự kiểm.
    ("Tôi bán sỉ phân bón cho các cửa hàng vật tư nông nghiệp", [{"4679"}], ""),
    ("Lấy hàng quần áo về bán buôn lại cho các shop", [{"4641"}], ""),
]


def _grade(case, res: nganh_nghe.KetQua) -> dict:
    text, expected, main = case
    if expected == "hoi":
        ok = bool(res.hoi_lai) and not any(n.chac for n in res.nganh)
        return {"hoi": 1, "hoi_dung": int(ok)}
    out = {"dong": len(expected), "chac_dung": 0, "chac_sai": 0, "goi_y_co": 0, "truot": 0, "chinh_dung": 0}
    rows = list(res.nganh)
    for want in expected:
        hit = next((n for n in rows if set(n.ma) & want), None)
        if hit is None:
            out["truot"] += 1
            continue
        rows.remove(hit)
        if hit.chac:
            out["chac_dung" if hit.ma[0] in want else "chac_sai"] += 1
        else:
            out["goi_y_co"] += 1
    # Dòng thừa đã "chắc" (agent tự thêm hoạt động / chắc sai mã) cũng là chắc-sai.
    out["chac_sai"] += sum(1 for n in rows if n.chac)
    if main:
        out["chinh_dung"] = int(res.chinh == main)
    return out


async def _one(i: int, case, sem) -> tuple[int, dict, nganh_nghe.KetQua, float]:
    async with sem:
        t0 = time.monotonic()
        res = await nganh_nghe.tra_cuu(case[0])
        return i, _grade(case, res), res, time.monotonic() - t0


async def main(only: set[int], parallel: int) -> None:
    sem = asyncio.Semaphore(parallel)
    picked = [(i, c) for i, c in enumerate(CASES, 1) if not only or i in only]
    results = await asyncio.gather(*(_one(i, c, sem) for i, c in picked))
    total: dict[str, float] = {}
    for i, grade, res, sec in sorted(results, key=lambda x: x[0]):
        for k, v in grade.items():
            total[k] = total.get(k, 0) + v
        rows = "; ".join(f"{n.hoat_dong} → {'/'.join(n.ma) or '∅'}{' ✓' if n.chac else ' ?'}" for n in res.nganh)
        flag = "❌" if grade.get("chac_sai") or grade.get("truot") or grade.get("hoi_dung") == 0 else "  "
        steps = "→".join(s["buoc"] for s in res.steps)
        print(f"{flag}{i:>2}. {CASES[i - 1][0][:48]:<48} | {rows or '-'} | chính={res.chinh or '-'}"
              f"{' | hỏi: ' + res.hoi_lai if res.hoi_lai else ''}{' | LỖI ' + res.error if res.error else ''}"
              f" | {steps} | {sec:.1f}s")
    times = sorted(r[3] for r in results)
    print("\nTỔNG:", {k: int(v) for k, v in total.items()},
          f"| thời gian trung vị {times[len(times) // 2]:.1f}s, chậm nhất {times[-1]:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chi", default="", help="chỉ chạy các ca này, vd 1,5,7")
    ap.add_argument("--song-song", type=int, default=4)
    a = ap.parse_args()
    asyncio.run(main({int(x) for x in a.chi.split(",") if x.strip()}, a.song_song))
