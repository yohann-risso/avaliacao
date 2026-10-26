import "server-only";

import postgres from "postgres";
import { databaseUrlForRuntime } from "@/lib/database-config";
import { DATABASE_IDLE_SECONDS } from "@/lib/database-lifecycle";

const configuredDatabaseUrl = databaseUrlForRuntime(
  process.env.DATABASE_URL || process.env.APP_DATABASE_URL || process.env.SUPABASE_DB_URL,
  process.env.VERCEL === "1",
);

function missingDatabase(): never {
  throw new Error("Banco não configurado. Defina DATABASE_URL com a URL do pooler do Supabase.");
}

const globalDatabase = globalThis as typeof globalThis & {
  __avaliacaoSql?: ReturnType<typeof postgres>;
};

export const sql =
  globalDatabase.__avaliacaoSql ??
  (configuredDatabaseUrl
    ? postgres(configuredDatabaseUrl, {
        max: 1,
        prepare: false,
        ssl: "require",
        connect_timeout: 15,
        idle_timeout: DATABASE_IDLE_SECONDS,
        max_lifetime: 60,
      })
    : (missingDatabase as unknown as ReturnType<typeof postgres>));

globalDatabase.__avaliacaoSql = sql;
