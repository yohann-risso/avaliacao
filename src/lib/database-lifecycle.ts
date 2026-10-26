import { cache } from "react";
import { after } from "next/server";

export const DATABASE_IDLE_SECONDS = 5;

// postgres.js relies on an idle timer to close sockets. Keep Vercel running
// until that timer fires, otherwise suspension can leave a stale socket behind.
// Run after the response, so this does not delay rendering or redirects.
export const maintainDatabaseLifecycle = cache(() => {
  if (process.env.VERCEL !== "1") return;
  after(() => new Promise<void>((resolve) => {
    setTimeout(resolve, DATABASE_IDLE_SECONDS * 1000 + 500);
  }));
});
