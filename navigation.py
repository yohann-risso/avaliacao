ADMIN_MENU_OPTIONS = (
    "1. Funcionários",
    "2. Usuários",
    "3. Avaliação Semanal",
    "4. Monitoria Mensal",
    "5. Relatório Mensal",
)

EVALUATOR_MENU_OPTIONS = (
    "3. Avaliação Semanal",
    "4. Monitoria Mensal",
)

REPORT_MENU = "5. Relatório Mensal"


def menu_options_for_user(user: dict | None) -> list[str]:
    role = str((user or {}).get("role", "")).strip().lower()
    if role == "admin":
        return list(ADMIN_MENU_OPTIONS)
    return list(EVALUATOR_MENU_OPTIONS)


def user_can_access_menu(user: dict | None, menu: str) -> bool:
    return str(menu or "").strip() in menu_options_for_user(user)
