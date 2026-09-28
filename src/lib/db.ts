import "server-only";

import postgres from "postgres";

const configuredDatabaseUrl = process.env.DATABASE_URL || process.env.APP_DATABASE_URL || process.env.SUPABASE_DB_URL;

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
        idle_timeout: 20,
      })
    : (missingDatabase as unknown as ReturnType<typeof postgres>));

if (process.env.NODE_ENV !== "production") globalDatabase.__avaliacaoSql = sql;
