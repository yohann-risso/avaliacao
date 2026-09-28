export function Notice({ success, error, info }: { success?: string; error?: string; info?: string }) {
  const message = error || success || info;
  if (!message) return null;
  const tone = error ? "error" : success ? "success" : "info";
  return <div className={`notice ${tone}`}>{message}</div>;
}
