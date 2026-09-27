import Icon from "./Icon";

export function Spinner({ label = "Đang tải" }: { label?: string }) {
  return <span className="spinner" role="status"><span className="spinner__ring" />{label}</span>;
}

export function PageLoading({ label }: { label: string }) {
  return <div className="page-loading"><Spinner label={label} /></div>;
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="notice notice--error" role="alert">
      <Icon name="alert" />
      <div>
        <strong>Không tải được dữ liệu</strong>
        <span>{message}</span>
      </div>
      {onRetry ? <button className="btn btn--sm" type="button" onClick={onRetry}><Icon name="refresh" size={14} /> Thử lại</button> : null}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return <div className="state"><strong>{title}</strong>{hint ? <span>{hint}</span> : null}</div>;
}
