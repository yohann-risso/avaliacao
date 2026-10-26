import { describe, expect, it } from "vitest";
import { databaseUrlForRuntime } from "@/lib/database-config";

describe("conexão serverless", () => {
  const session = "postgresql://postgres.project:secret%40encoded@aws-1-us-east-2.pooler.supabase.com:5432/postgres?sslmode=require";

  it("troca apenas a porta do pooler Supabase na Vercel", () => {
    expect(databaseUrlForRuntime(session, true)).toBe(session.replace(":5432/", ":6543/"));
  });

  it("converte também a porta padrão implícita do pooler", () => {
    expect(databaseUrlForRuntime(session.replace(":5432", ""), true)).toBe(session.replace(":5432/", ":6543/"));
  });

  it("preserva conexões locais, diretas e poolers já configurados", () => {
    expect(databaseUrlForRuntime(session, false)).toBe(session);
    const direct = "postgresql://postgres:secret@db.project.supabase.co:5432/postgres";
    expect(databaseUrlForRuntime(direct, true)).toBe(direct);
    const transaction = session.replace(":5432/", ":6543/");
    expect(databaseUrlForRuntime(transaction, true)).toBe(transaction);
    expect(databaseUrlForRuntime(undefined, true)).toBeUndefined();
  });
});
