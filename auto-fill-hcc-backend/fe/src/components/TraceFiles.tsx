import { useEffect, useRef, useState } from "react";
import { fetchTraceArchive, fetchTraceFile } from "../api";
import type { Attachment } from "../types";

interface Preview {
  index: number;
  name: string;
  type: string;
  url: string;
}

// Danh sách file đính kèm + xem trước ngay (ảnh/PDF), tải blob kèm Authorization.
// Dùng chung cho drawer xem nhanh và trang chi tiết đầy đủ.
export default function TraceFiles({
  traceId,
  attachments,
  archiveName,
}: {
  traceId: string;
  attachments: Attachment[];
  archiveName?: string; // tên file .zip khi tải tất cả (không kèm đuôi)
}) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loadingIdx, setLoadingIdx] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const urlRef = useRef<string | null>(null);

  async function downloadAll() {
    setError("");
    setDownloading(true);
    try {
      const blob = await fetchTraceArchive(traceId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${archiveName || "tai-lieu"}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được tài liệu");
    } finally {
      setDownloading(false);
    }
  }

  // Thu hồi object URL cũ khi đổi file / rời component (tránh rò bộ nhớ).
  function revoke() {
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
  }
  useEffect(() => revoke, []);

  async function open(f: Attachment, i: number) {
    if (preview?.index === i) {
      // Bấm lại file đang xem -> đóng.
      revoke();
      setPreview(null);
      return;
    }
    setError("");
    setLoadingIdx(i);
    try {
      const blob = await fetchTraceFile(traceId, i);
      revoke();
      const url = URL.createObjectURL(blob);
      urlRef.current = url;
      setPreview({ index: i, name: f.name, type: blob.type, url });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xem được file");
      setPreview(null);
    } finally {
      setLoadingIdx(null);
    }
  }

  return (
    <section>
      <div className="files-head">
        <h3>File đính kèm ({attachments.length})</h3>
        {attachments.length > 0 && (
          <button className="ghost sm" onClick={downloadAll} disabled={downloading}>
            {downloading ? "Đang nén…" : "⬇ Tải tất cả"}
          </button>
        )}
      </div>
      {attachments.length > 0 ? (
        <ul className="files">
          {attachments.map((f, i) => (
            <li key={i}>
              <button
                type="button"
                className={`linklike${preview?.index === i ? " active" : ""}`}
                onClick={() => open(f, i)}
              >
                <span className="mono">{f.name}</span>
              </button>
              {f.role && <span className="muted"> · {f.role}</span>}
              {loadingIdx === i && <span className="muted"> · đang tải…</span>}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">(không có)</p>
      )}

      {error && <div className="error">{error}</div>}

      {preview && (
        <div className="file-preview">
          <div className="file-preview-head">
            <span className="mono">{preview.name}</span>
            <a href={preview.url} target="_blank" rel="noreferrer" className="ghost">
              Mở tab mới
            </a>
          </div>
          {preview.type.startsWith("image/") ? (
            <img src={preview.url} alt={preview.name} />
          ) : preview.type === "application/pdf" ? (
            <iframe src={preview.url} title={preview.name} />
          ) : (
            <a href={preview.url} download={preview.name}>
              Tải xuống {preview.name}
            </a>
          )}
        </div>
      )}
    </section>
  );
}
