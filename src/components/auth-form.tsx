"use client";

import { useActionState } from "react";
import { createInitialAdminAction, loginAction, type AuthState } from "@/app/actions/auth";
import { SubmitButton } from "@/components/submit-button";

const initialState: AuthState = { error: "" };

export function AuthForm({ firstAccess }: { firstAccess: boolean }) {
  const action = firstAccess ? createInitialAdminAction : loginAction;
  const [state, formAction] = useActionState(action, initialState);
  return (
    <form action={formAction} className="grid">
      {state.error ? <div className="notice error">{state.error}</div> : null}
      <div className="field span-12">
        <label htmlFor="username">Usuário</label>
        <input id="username" name="username" autoComplete="username" required minLength={3} autoFocus />
      </div>
      <div className="field span-12">
        <label htmlFor="password">Senha</label>
        <input id="password" name="password" type="password" autoComplete={firstAccess ? "new-password" : "current-password"} required minLength={8} />
      </div>
      {firstAccess ? (
        <div className="field span-12">
          <label htmlFor="password_confirmation">Confirmar senha</label>
          <input id="password_confirmation" name="password_confirmation" type="password" autoComplete="new-password" required minLength={8} />
        </div>
      ) : null}
      <SubmitButton>{firstAccess ? "Criar administrador" : "Entrar"}</SubmitButton>
    </form>
  );
}
