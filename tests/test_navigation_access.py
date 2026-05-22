from navigation import (
    ADMIN_MENU_OPTIONS,
    EVALUATOR_MENU_OPTIONS,
    REPORT_MENU,
    menu_options_for_user,
    user_can_access_menu,
)


def test_admin_has_full_navigation():
    user = {"role": "admin"}

    assert menu_options_for_user(user) == list(ADMIN_MENU_OPTIONS)
    assert user_can_access_menu(user, REPORT_MENU)


def test_evaluator_has_limited_navigation():
    user = {"role": "avaliador"}

    assert menu_options_for_user(user) == list(EVALUATOR_MENU_OPTIONS)
    assert not user_can_access_menu(user, "1. Funcionários")
    assert not user_can_access_menu(user, "2. Usuários")
    assert not user_can_access_menu(user, REPORT_MENU)


def test_unknown_role_does_not_receive_admin_pages():
    user = {"role": "desconhecido"}

    assert menu_options_for_user(user) == list(EVALUATOR_MENU_OPTIONS)
    assert not user_can_access_menu(user, REPORT_MENU)
