import { describe, expect, it } from "vitest";

import { normalizeSectorName } from "@/lib/sectors";

describe("normalização de setor", () => {
  it("coloca a primeira letra em maiúscula", () => {
    expect(normalizeSectorName("expedição")).toBe("Expedição");
  });

  it("reutiliza a grafia existente sem diferenciar maiúsculas e minúsculas", () => {
    expect(normalizeSectorName("  OPERAÇÕES  ", ["Operações"])).toBe("Operações");
    expect(normalizeSectorName("ti", ["TI"])).toBe("TI");
  });

  it("remove espaços excedentes sem alterar o restante da grafia", () => {
    expect(normalizeSectorName("  controle   de qualidade ")).toBe("Controle de qualidade");
  });
});
