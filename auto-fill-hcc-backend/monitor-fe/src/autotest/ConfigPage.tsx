// Cấu hình ghi (chỉ đọc, đợt 1): mỗi lượt đang được ghi gì, ở đâu, giữ bao lâu; phần nào chưa ghi (đợt 2 — cần sửa
// extension + backend). Kèm nguồn dữ liệu của dịch vụ agent và nhật ký truy cập.
import { ErrorNotice, PageLoading } from "../components/Status";
import { formatWhen } from "../format";
import { useAsync } from "../hooks";
import { onLinkClick } from "../router";
import { labApi, useLabAvailable } from "./api";
import { LabCrumbs, LabNotice, Section, Unavailable } from "./parts";
import "./autotest.css";

type Item = { name: string; detail: string; on: boolean; must?: boolean };

const GROUPS: { title: string; sub: string; items: Item[] }[] = [
  {
    title: "1. Nhật ký luồng",
    sub: "Màn Tái hiện lượt dựng dòng thời gian từ các nguồn dưới, theo mốc giờ.",
    items: [
      { name: "Công đoạn backend", detail: "trace_steps: từng span (nhận tệp, OCR, gọi mô hình, mapper), thời gian, lỗi", on: true },
      { name: "Kết quả OCR từng tệp", detail: "Văn bản, số trang, cache; OCR lưu theo sha256 của tệp", on: true },
      { name: "Lần gọi mô hình", detail: "Mục đích, model, độ trễ, token, câu trả lời thô (dùng để phát lại khi chạy ca test)", on: true },
      { name: "Lượt bấm nộp trên cổng", detail: "dossiers.submit_events: lúc bấm, tên miền cổng", on: true },
      { name: "Thao tác trên extension", detail: "Mở trợ lý, bấm nút, chuyển bước, đóng / mở lại phiên — chưa ghi (đợt 2)", on: false },
      { name: "Lỗi, cảnh báo, quá thời gian chờ ở extension", detail: "Kèm trạng thái extension lúc lỗi — chưa ghi (đợt 2)", on: false },
    ],
  },
  {
    title: "2. Hội thoại người dân – trợ lý",
    sub: "conversations.history của kênh handfree.",
    items: [
      { name: "Tin nhắn hai chiều", detail: "Ai nói, lúc nào, văn bản; Mongo backend giữ 24 giờ, sau đó chỉ còn bản kho lưu trữ", on: true },
      { name: "Văn bản nhận dạng giọng nói", detail: "Câu cuối cùng (nguồn tin nhắn); độ tin cậy và các phương án khác chưa ghi", on: true },
      { name: "Âm thanh gốc của người dân", detail: "Không ghi. Chỉ nên bật cho đơn vị thử nghiệm khi người dân đồng ý", on: false },
      { name: "Thời điểm đọc và nghe", detail: "Lúc trợ lý bắt đầu / dừng đọc, lúc mic mở — chưa ghi (đợt 2)", on: false },
    ],
  },
  {
    title: "3. Ảnh chụp form",
    sub: "Extension (form-snapshot/tracker.js, dùng chung 2 extension) gửi về backend, backend chuyển thẳng sang kho.",
    items: [
      { name: "Sau khi extension điền", detail: "Bản gốc để biết trợ lý đã điền gì trước khi người dân chạm vào (fill)", on: true, must: true },
      { name: "Mỗi khi người dân sửa ô", detail: "Gộp các thay đổi trong 3 giây thành một bản, chỉ gửi khi giá trị khác bản trước (edit)", on: true },
      { name: "Khi rời bước kê khai / bấm nộp", detail: "Bản cuối là đáp án khi dùng lượt làm ca test (step)", on: true, must: true },
      { name: "Giá trị từng ô", detail: "Kho dựng bảng be → fill → final và chấm từng ô (Người dùng sửa / Lượt bị sửa)", on: true },
      { name: "HTML vùng tờ khai", detail: "Để dựng lại đúng giao diện tờ khai lúc đó, kể cả khi cổng đã đổi — chưa ghi (đợt 2)", on: false },
      { name: "Khi trang báo lỗi dữ liệu / định kỳ 30 giây", detail: "Chưa ghi (đợt 2)", on: false },
    ],
  },
  {
    title: "4. Bảo vệ dữ liệu của người dân",
    sub: "Gói ghi chứa giấy tờ thật. Ca test chỉ dùng bản đã thay dữ liệu cá nhân.",
    items: [
      { name: "Che số giấy tờ khi hiển thị", detail: "Số ≥ 9 chữ số hiện dạng 024199•••147 trên mọi màn Auto test; nút “Hiện đủ số” chỉ có tác dụng trên trang đang mở", on: true },
      { name: "Thay dữ liệu cá nhân khi tạo ca test", detail: "Họ tên → tên giả, số giấy tờ / SĐT → số giả cùng độ dài, số nhà / thôn → mẫu; giữ đơn vị hành chính và ngày tháng; thay giống nhau trong OCR, câu trả lời mô hình và đáp án; còn sót chuỗi thật thì không lưu ca", on: true, must: true },
      { name: "Ghi nhật ký mỗi lần mở, tái hiện, tải gói, tạo / xoá ca", detail: "Ai, lúc nào, lượt nào — bảng cuối trang", on: true, must: true },
      { name: "Thời hạn lưu", detail: "Backend production xoá tệp gốc, OCR, kết quả điền khoảng 30 phút sau lượt cuối (chỉ còn trong kho); ca test để trong auto-test-hcc/runs/_lab, không commit", on: true },
    ],
  },
];

const VAULT_MAP: [string, string][] = [
  ["Lượt xử lý", "Tái hiện lượt (công đoạn backend, OCR, lần gọi mô hình), Gói ghi thô"],
  ["Hội thoại handfree", "Tái hiện lượt › hội thoại"],
  ["“Có ảnh chụp form”", "Mốc S1–Sn trên dòng thời gian, bảng Ảnh chụp form"],
  ["Người dùng sửa, Lượt bị sửa", "Nội dung trợ lý điền (bảng từng ô), đáp án của ca test, danh sách chọn lượt"],
  ["Tệp lẻ của lượt", "Tab Tệp (văn bản OCR; tệp gốc không tải từ đây)"],
  ["Nhật ký tải ảnh, Phiên tải ảnh", "Chưa dùng"],
];

export default function ConfigPage() {
  const lab = useLabAvailable();
  const { data, error, loading, reload } = useAsync(() => labApi.config(), "lab-config");
  if (lab === false) return <><LabNotice /><LabCrumbs items={[{ label: "Cấu hình ghi" }]} /><Unavailable /></>;
  if (loading && !data) return <><LabNotice /><PageLoading label="Đang tải cấu hình…" /></>;
  return (
    <>
      <LabNotice />
      <LabCrumbs items={[{ label: "Cấu hình ghi" }]} />
      <div className="page-head">
        <h1>Cấu hình ghi</h1>
        <span className="page-head__meta">
          Mỗi lượt xử lý đang được ghi những phần dưới đây, đủ để tái hiện lượt và dùng lượt làm ca test. Bật / tắt từng phần ghi theo
          đơn vị là đợt 2 (cần sửa extension và backend); trang này chỉ hiện hiện trạng.
        </span>
      </div>
      {error ? <ErrorNotice message={error} onRetry={reload} /> : null}

      {data ? (
        <div className="kpis">
          <div className="kpi"><span>Mongo nguồn</span><b className="lab-kpi-text">{data.source.mongo}</b><small>dịch vụ agent đọc lượt ở đây trước</small></div>
          <div className="kpi"><span>Kho lưu trữ</span><b className="lab-kpi-text">{data.source.archive ? "Đã nối" : "Chưa nối"}</b><small>{data.source.archive ? "lượt production đã dọn + ảnh chụp form" : "khai AUTOTEST_ARCHIVE_* trong server.env"}</small></div>
          <div className="kpi"><span>Ca test từ lượt thật</span><b>{data.lab.cases}</b><small>{data.lab.suites} bộ · <a href="/autotest/suites" onClick={(e) => onLinkClick(e, "/autotest/suites")}>xem bộ ca</a></small></div>
          <div className="kpi"><span>Lần chạy</span><b>{data.lab.runs}</b><small><a href="/autotest/runs" onClick={(e) => onLinkClick(e, "/autotest/runs")}>xem lần chạy</a></small></div>
          <div className="kpi"><span>Cây backend để chạy ca</span><b className="lab-kpi-text">{data.targets.filter((t) => t.ok).length}</b>
            <small>{data.targets.map((t) => `${t.key === "dev" ? "đang phát triển" : "production"}${t.tag || t.commit ? ` ${t.tag ?? t.commit}` : ""}${t.dirty ? "+" : ""}`).join(" · ")}</small></div>
        </div>
      ) : null}

      <div className="lab-config">
        {GROUPS.map((g) => (
          <Section key={g.title} title={g.title} sub={g.sub}>
            <ul className="lab-items">
              {g.items.map((item) => (
                <li key={item.name} className={item.on ? "is-on" : "is-off"}>
                  <span className={`lab-switch${item.on ? " is-on" : ""}`} aria-label={item.on ? "Đang ghi" : "Chưa ghi"} />
                  <div><b>{item.name}</b>{item.must ? <span className="lab-badge lab-badge--muted">Bắt buộc</span> : null}<p>{item.detail}</p></div>
                </li>
              ))}
            </ul>
          </Section>
        ))}
      </div>

      <Section title="Khớp với loại dữ liệu đang có trong kho" sub="Auto test đọc lại đúng các loại kho đang nhận, không có gói ghi riêng">
        <div className="table-wrap">
          <table className="grid"><thead><tr><th>Đang có trong kho</th><th>Dùng ở</th></tr></thead>
            <tbody>{VAULT_MAP.map(([a, b]) => <tr key={a}><td>{a}</td><td>{b}</td></tr>)}</tbody>
          </table>
        </div>
      </Section>

      <Section title="Nhật ký truy cập gần đây" sub="Mỗi lần mở tái hiện, tải gói ghi, tạo / xoá ca, chạy bộ ca">
        {data?.access.length ? (
          <div className="table-wrap">
            <table className="grid">
              <thead><tr><th>Lúc</th><th>Tài khoản</th><th>Việc</th><th>Lượt / ca</th></tr></thead>
              <tbody>
                {data.access.map((a, i) => {
                  const when = formatWhen(a.at);
                  return (
                    <tr key={i}>
                      <td className="nowrap"><span className="cell-main num">{when.main}</span><span className="cell-sub">{when.sub}</span></td>
                      <td>{a.user ?? "—"}</td>
                      <td>{a.action}</td>
                      <td className="mono">{[a.requestId, a.caseId, a.run ? `#${a.run}` : null].filter(Boolean).join(" · ") || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : <p className="faint">Chưa có lượt truy cập nào.</p>}
      </Section>
    </>
  );
}
