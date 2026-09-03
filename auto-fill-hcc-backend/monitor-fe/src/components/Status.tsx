import Icon from "./Icon";

export function Spinner({ label = "Đang tải" }: { label?: string }) {
  return <span className="spinner" role="status"><span className="spinner__ring" />{label}</span>;
}

export function PageLoading({ label }: { label: string }) {
  return (
    <main id="main-content" className="page-loading">
      <span className="page-loading__document"><Icon name="document" size={28} /></span>
      <span className="page-loading__bar"><span /></span>
      <p>{label}</p>
    </main>
  );
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="notice notice--error" role="alert">
      <div>
        <strong>Không tải được dữ liệu</strong>
        <p>{message}</p>
      </div>
      {onRetry ? (
        <button className="button button--secondary" type="button" onClick={onRetry}>
          <Icon name="refresh" /> Thử lại
        </button>
      ) : null}
    </div>
  );
}
