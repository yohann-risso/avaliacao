from theme import render_sidebar_navigation, render_status_cards


def test_status_cards_emit_compact_html(monkeypatch):
    captured = {}

    def fake_markdown(body, unsafe_allow_html=False):
        captured["body"] = body
        captured["unsafe_allow_html"] = unsafe_allow_html

    monkeypatch.setattr("theme.st.markdown", fake_markdown)

    render_status_cards([
        {"title": "Mês", "value": "05/2026", "detail": "Competência", "tone": "info"},
        {"title": "Origem", "value": "Novo registro", "detail": "Sem HTML cru", "tone": "neutral"},
    ])

    body = captured["body"]
    assert captured["unsafe_allow_html"] is True
    assert body.count('class="kaisan-status-card') == 2
    assert "\n            <div class=\"kaisan-status-card" not in body


def test_sidebar_navigation_emits_clickable_process_steps(monkeypatch):
    captured = {}

    def fake_markdown(body, unsafe_allow_html=False):
        captured["body"] = body
        captured["unsafe_allow_html"] = unsafe_allow_html

    monkeypatch.setattr("theme.st.sidebar.markdown", fake_markdown)

    render_sidebar_navigation(
        "maio/2026",
        [
            {
                "option": "2. Avaliação Semanal",
                "title": "Avaliações",
                "detail": "80% cobertura",
                "tone": "warning",
                "active": True,
            },
            {
                "option": "4. Relatório Mensal",
                "title": "Relatório",
                "detail": "0 pendências",
                "tone": "success",
            },
        ],
        [{"label": "Cobertura semanal", "value": "80%"}],
        query_key="tela",
    )

    body = captured["body"]
    assert captured["unsafe_allow_html"] is True
    assert '<nav class="kaisan-process-list" aria-label="Navegação do processo">' in body
    assert 'href="?tela=2.%20Avalia%C3%A7%C3%A3o%20Semanal"' in body
    assert 'aria-current="page"' in body
    assert body.index("kaisan-process-list") < body.index("kaisan-sidebar-stats")
