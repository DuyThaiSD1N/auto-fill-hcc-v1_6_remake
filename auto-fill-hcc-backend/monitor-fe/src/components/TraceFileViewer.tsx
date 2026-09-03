import { useEffect, useRef, useState } from "react";
import { fetchTraceFile } from "../api";
import type { Attachment } from "../types";
import Icon from "./Icon";
import { Spinner } from "./Status";

interface Preview {
  index: number;
  name: string;
  mime: string;
  url: string;
}

function fileName(file: Attachment, index: number): string {
  return file.name?.trim() || `Tệp ${index + 1}`;
}

export default function TraceFileViewer({ traceId, files }: { traceId: string; files: Attachment[] }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loadingIndex, setLoadingIndex] = useState<number | null>(null);
  const [error, setError] = useState("");
  const objectUrl = useRef<string | null>(null);
  const requestSequence = useRef(0);

  function revokePreview() {
    if (objectUrl.current) {
      URL.revokeObjectURL(objectUrl.current);
      objectUrl.current = null;
    }
  }

  useEffect(() => {
    return () => {
      requestSequence.current += 1;
      revokePreview();
    };
  }, []);

  async function openFile(file: Attachment, index: number) {
    const sequence = ++requestSequence.current;
    setLoadingIndex(index);
    setError("");
    try {
      const blob = await fetchTraceFile(traceId, index);
      if (sequence !== requestSequence.current) return;
      revokePreview();
      const url = URL.createObjectURL(blob);
      objectUrl.current = url;
      setPreview({ index, name: fileName(file, index), mime: blob.type, url });
    } catch (reason) {
      if (sequence !== requestSequence.current) return;
      setError(reason instanceof Error ? reason.message : "Không tải được tệp giấy tờ.");
    } finally {
      if (sequence === requestSequence.current) setLoadingIndex(null);
    }
  }

  return (
    <section className="file-workbench" aria-label="Giấy tờ đầu vào">
      <div className="file-list-panel">
        <header className="pane-heading">
          <span className="section-index">01</span>
          <div>
            <h2>Giấy tờ đầu vào</h2>
            <p>{files.length.toLocaleString("vi-VN")} tệp trong lượt xử lý</p>
          </div>
        </header>

        {files.length ? (
          <ul className="file-list">
            {files.map((file, index) => {
              const active = preview?.index === index;
              return (
                <li key={`${file.name || "file"}-${index}`}>
                  <button
                    aria-current={active ? "true" : undefined}
                    className={`file-row${active ? " file-row--active" : ""}`}
                    onClick={() => openFile(file, index)}
                    type="button"
                  >
                    <span className="file-row__icon"><Icon name="file" /></span>
                    <span className="file-row__copy">
                      <strong>{fileName(file, index)}</strong>
                      <small>{file.role?.trim() || "Tài liệu hồ sơ"}</small>
                    </span>
                    <span className="file-row__action">
                      {loadingIndex === index ? <Spinner label="" /> : <Icon name="eye" />}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="pane-empty">
            <Icon name="file" size={24} />
            <p>Trace này không có metadata tệp đính kèm.</p>
          </div>
        )}

        {error ? <div className="inline-error" role="alert">{error}</div> : null}
      </div>

      <div className="preview-panel">
        {preview ? (
          <>
            <header className="preview-panel__head">
              <div>
                <span>Đang xem</span>
                <strong>{preview.name}</strong>
              </div>
              <a className="button button--ghost" href={preview.url} rel="noreferrer" target="_blank">
                <Icon name="external" /> Mở tab mới
              </a>
            </header>
            <div className="preview-panel__body">
              {preview.mime.startsWith("image/") ? (
                <img alt={`Bản xem trước ${preview.name}`} src={preview.url} />
              ) : preview.mime === "application/pdf" ? (
                <iframe src={preview.url} title={`Bản xem trước ${preview.name}`} />
              ) : (
                <div className="preview-unsupported">
                  <Icon name="document" size={32} />
                  <h3>Không xem trước được định dạng này</h3>
                  <a className="button button--primary" download={preview.name} href={preview.url}>Tải tệp xuống</a>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="preview-placeholder">
            <span className="preview-placeholder__target"><Icon name="eye" size={28} /></span>
            <h3>Chọn một tệp để xem</h3>
            <p>Tệp chỉ được tải khi chọn, giúp hạn chế đọc giấy tờ không cần thiết.</p>
          </div>
        )}
      </div>
    </section>
  );
}
