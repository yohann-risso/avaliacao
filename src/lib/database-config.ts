export function databaseUrlForRuntime(value: string | undefined, serverless: boolean): string | undefined {
  if (!value || !serverless) return value;
  const url = new URL(value);
  // Supavisor session mode reserves a backend for every serverless instance.
  // Keep the same project and credentials, using transaction pooling on Vercel.
  if (url.hostname.endsWith(".pooler.supabase.com") && (!url.port || url.port === "5432")) {
    url.port = "6543";
    return url.toString();
  }
  return value;
}
