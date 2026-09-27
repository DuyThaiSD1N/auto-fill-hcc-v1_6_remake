import { useEffect, useRef, useState } from "react";
import { downloadTraceZip, fetchTraceFile } from "../../api";
import CopyButton from "../CopyButton";
import Icon from "../Icon";
import type { RunDetail } from "../../types";
import { EmptyState } from "../Status";
import { OcrText } from "./Parts";

/** Tệp gốc (ảnh/PDF) cạnh text OCR của đúng tệp đó. */
export default function Documents({ run }: { run: RunDetail }) {
  const files = run.trace?.attachments ?? [];
  const ocr = run.steps?.ocr ?? [];
  const [index, setIndex] = useState(0);
  const [preview, setPreview] = useState<{ url: string; mime: string } | null>(null);
  const [error, setError] = useState("");
  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!run.trace || !files.length) return undefined;
    let active = true;
    setError("");
    setPreview(null);
    fetchTraceFile(run.trace.id, index)
      .then((blob) => {
        if (!active) return;
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        urlRef.current = URL.createObjectURL(blob);
        setPreview({ url: urlRef.current, mime: blob.type });
      })
      .catch((e) => { if (active) setError(e instanceof Error ? e.message : String(e)); });
    return () => { active = false; };
  }, [run.trace, index, files.length]);

  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  const [zipState, setZipState] = useState<"idle" | "busy" | string>("idle");
  async function downloadAll() {
    if (!run.trace) return;
    setZipState("busy");
    try {
      const { blob, filename } = await downloadTraceZip(run.trace.id);
      saveBlob(blob, filename);
      setZipState("idle");
    } catch (e) {
      setZipState(e instanceof Error ? e.message : String(e));
    }
  }

  if (!files.length && !ocr.length) return <EmptyState title="Lượt này không có tệp đầu vào" />;
  const current = files[index];
  const ocrFile = ocr.find((o) => o.name === current?.name) ?? (files.length ? undefined : ocr[index]);

  return (
    <>
    {run.trace && files.length ? (
      <div className="copy-row" style={{ marginBottom: 10 }}>
        <button className="btn btn--sm" type="button" onClick={downloadAll} disabled={zipState === "busy"}>
          <Icon name="document" size={14} /> {zipState === "busy" ? "Đang nén…" : `Tải tất cả (${files.length} tệp, .zip)`}
        </button>
        {preview ? (
          <a className="btn btn--sm" href={preview.url} download={current?.name ?? "tep"}>Tải tệp đang xem</a>
        ) : null}
        {zipState !== "idle" && zipState !== "busy" ? <span className="dropped">{zipState}</span> : null}
      </div>
    ) : null}
    <div className="docs">
      <div className="panel doc-list" role="list">
        {(files.length ? files : ocr).map((f, i) => (
          <button key={i} type="button" aria-current={i === index} onClick={() => setIndex(i)}>
            <span>{f.name || `Tệp ${i + 1}`}</span>
            <small>{"role" in f && f.role ? f.role : "—"}</small>
          </button>
        ))}
      </div>
      <div className="doc-preview">
        {!run.trace ? <span className="faint">Lượt này không lưu tệp gốc.</span>
          : error ? <span className="dropped">{error}</span>
          : !preview ? <span className="faint">Đang tải tệp…</span>
          : preview.mime.startsWith("image/") ? <img src={preview.url} alt={`Tệp ${current?.name ?? ""}`} />
          : preview.mime === "application/pdf" ? <iframe src={preview.url} title={`Tệp ${current?.name ?? ""}`} />
          : <a className="btn" href={preview.url} download={current?.name ?? "tep"}>Tải tệp xuống</a>}
      </div>
      <div className="panel panel__body">
        {ocrFile ? <OcrText file={ocrFile} />
          : run.trace?.ocr_text ? (<><div className="section-title copy-row">OCR gộp (dữ liệu cũ) <CopyButton text={run.trace.ocr_text} label="Sao chép text OCR" /></div><pre className="code code--tall">{run.trace.ocr_text}</pre></>)
          : <p className="faint">Không có text OCR cho tệp này.</p>}
      </div>
    </div>
    </>
  );
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
