"use client";

import { useFormStatus } from "react-dom";

export function SubmitButton({
  children,
  className = "button primary",
  name,
  value,
}: {
  children: React.ReactNode;
  className?: string;
  name?: string;
  value?: string | number;
}) {
  const { pending } = useFormStatus();
  return (
    <button className={className} type="submit" disabled={pending} name={name} value={value}>
      {pending ? "Processando…" : children}
    </button>
  );
}
