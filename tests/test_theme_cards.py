from theme import render_status_cards


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
