// Chọn lượt để tái hiện / xem nội dung đã điền: nhập mã req, hoặc chọn trong các lượt người dân sửa gần đây (kho lưu trữ).
import { useState, type FormEvent } from "react";
import Icon from "../components/Icon";
import { EmptyState, ErrorNotice } from "../components/Status";
import { SourceTag } from "../components/Tags";
import { formatWhen } from "../format";
import { useAsync, useFacets } from "../hooks";
import { navigate } from "../router";
import { labApi, useLabAvailable } from "./api";
import { LabCrumbs, LabNotice, Unavailable } from "./parts";
import "./autotest.css";

export default function PickerPage({ target }: { target: "replay" | "fill" }) {
  const lab = useLabAvailable();
  const [edited, setEdited] = useState(true);
  const [text, setText] = useState("");
  const { procLabel } = useFacets();
  const { data, error, loading, reload } = useAsync(() => labApi.recent(edited), `recent:${edited}`);
  const title = target === "fill" ? "Nội dung trợ lý điền" : "Tái hiện lượt";
  const open = (id: string) => navigate(`/autotest/${target}/${encodeURIComponent(id.trim())}`);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (/^req_[a-z0-9]+$/i.test(text.trim())) open(text);
  }

  if (lab === false) return <><LabNotice /><LabCrumbs items={[{ label: title }]} /><Unavailable /></>;
  return (
    <>
      <LabNotice />
      <LabCrumbs items={[{ label: title }]} />
      <div className="page-head">
        <h1>{title}</h1>
        <span className="page-head__meta">
          {target === "fill"
            ? "Từng ô trợ lý điền gì, lấy từ đâu, người dân nộp gì — đáp án để dựng ca test."
            : "Dựng lại một lượt theo thời gian: công đoạn backend, hội thoại, các lần chụp form."}
        </span>
      </div>
      <form className="lab-pick" onSubmit={submit}>
        <label className="sr-only" htmlFor="lab-req">Mã hỗ trợ</label>
        <input id="lab-req" className="input" placeholder="Mã hỗ trợ req_… (extension hiện sau khi điền)" value={text}
               onChange={(e) => setText(e.target.value)} />
        <button className="btn btn--primary" type="submit" disabled={!/^req_[a-z0-9]+$/i.test(text.trim())}>
          <Icon name="search" size={14} /> Mở lượt
        </button>
      </form>

      <div className="page-head lab-pick__head">
        <h2>{edited ? "Lượt người dân sửa gần đây" : "Lượt gần đây"}</h2>
        <div className="seg">
          <button type="button" aria-pressed={edited} onClick={() => setEdited(true)}>Có ô bị sửa</button>
          <button type="button" aria-pressed={!edited} onClick={() => setEdited(false)}>Tất cả</button>
        </div>
        <span className="page-head__meta">{data ? `${data.items.length} lượt · nguồn ${data.source === "archive" ? "kho lưu trữ" : "Mongo nguồn"}` : loading ? "Đang tải…" : ""}</span>
      </div>
      {error ? <ErrorNotice message={error} onRetry={reload} /> : null}
      <div className="table-wrap" aria-busy={loading}>
        <table className="grid">
          <thead><tr><th>Thời gian</th><th>Kênh</th><th>Đơn vị</th><th>Thủ tục</th><th className="right">Ô bị sửa</th><th>Mã hỗ trợ</th></tr></thead>
          <tbody>
            {(data?.items ?? []).map((row) => {
              const when = formatWhen(row.createdAt);
              return (
                <tr key={row.requestId} onClick={() => open(row.requestId)}>
                  <td className="nowrap"><span className="cell-main num">{when.main}</span><span className="cell-sub">{when.sub}</span></td>
                  <td><SourceTag source={row.experience} /></td>
                  <td><span className="cell-main">{row.unit ?? "—"}</span></td>
                  <td><span className="cell-main" title={row.label ?? ""}>{procLabel(row.procedure, null)}</span>
                    {row.kinds?.length ? <span className="cell-sub">{row.kinds.join(", ")}</span> : null}</td>
                  <td className="num right">{row.edited ? <span className="lab-badge lab-badge--bad">{row.edited}</span> : row.edited === 0 ? "0" : "—"}</td>
                  <td className="mono">{row.requestId}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {data && !data.items.length ? <EmptyState title="Không có lượt nào" hint={edited ? "Chưa có lượt nào người dân sửa ô trong các trang gần nhất của kho." : undefined} /> : null}
      </div>
    </>
  );
}
