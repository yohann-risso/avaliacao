import { afterEach, describe, expect, it, vi } from "vitest";

const callbacks = vi.hoisted(() => [] as Array<() => Promise<void>>);
vi.mock("next/server", () => ({ after: (callback: () => Promise<void>) => callbacks.push(callback) }));

import { DATABASE_IDLE_SECONDS, maintainDatabaseLifecycle } from "@/lib/database-lifecycle";

describe("ciclo de vida da conexão na Vercel", () => {
  afterEach(() => {
    callbacks.length = 0;
    vi.useRealTimers();
    vi.unstubAllEnvs();
  });

  it("mantém a função ativa após a resposta até passar o timeout ocioso", async () => {
    vi.stubEnv("VERCEL", "1");
    vi.useFakeTimers();
    maintainDatabaseLifecycle();
    expect(callbacks).toHaveLength(1);
    let finished = false;
    const completion = callbacks[0]().then(() => { finished = true; });
    await vi.advanceTimersByTimeAsync(DATABASE_IDLE_SECONDS * 1000);
    expect(finished).toBe(false);
    await vi.advanceTimersByTimeAsync(500);
    await completion;
    expect(finished).toBe(true);
  });

  it("não agenda tarefas de plataforma na execução local", () => {
    vi.stubEnv("VERCEL", "");
    maintainDatabaseLifecycle();
    expect(callbacks).toHaveLength(0);
  });
});
