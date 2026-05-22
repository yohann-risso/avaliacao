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


def test_sidebar_navigation_uses_native_streamlit_control(monkeypatch):
    captured = {"markdowns": []}

    def fake_markdown(body, unsafe_allow_html=False):
        captured["markdowns"].append(body)
        captured["unsafe_allow_html"] = unsafe_allow_html

    def fake_radio(label, options, index=0, format_func=None, key=None, label_visibility=None):
        captured["radio"] = {
            "label": label,
            "options": options,
            "index": index,
            "labels": [format_func(option) for option in options],
            "key": key,
            "label_visibility": label_visibility,
        }
        return options[index]

    monkeypatch.setattr("theme.st.sidebar.markdown", fake_markdown)
    monkeypatch.setattr("theme.st.sidebar.radio", fake_radio)

    selected = render_sidebar_navigation(
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

    body = "".join(captured["markdowns"])
    assert captured["unsafe_allow_html"] is True
    assert selected == "2. Avaliação Semanal"
    assert captured["radio"]["label"] == "Navegação"
    assert captured["radio"]["key"] == "main_menu_nav"
    assert captured["radio"]["label_visibility"] == "collapsed"
    assert captured["radio"]["labels"] == [
        "1. Avaliações · 80% cobertura",
        "2. Relatório · 0 pendências",
    ]
    assert '<a class="kaisan-process-step' not in body
    assert 'href="?tela=' not in body
    assert "kaisan-sidebar-brand" in body
    assert "kaisan-sidebar-stats" in body
