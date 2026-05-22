import base64
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import quote

import streamlit as st


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    logo_path = Path("assets/logo.png")
    if not logo_path.exists():
        return ""

    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_page_header(title: str, subtitle: str, icon: str = "", kicker: str = "", meta: list[str] | None = None):
    logo_uri = _logo_data_uri()
    logo_html = f'<img src="{logo_uri}" alt="Kaisan" />' if logo_uri else '<span>Kaisan</span>'
    icon_html = f'<span class="kaisan-page-icon">{escape(str(icon))}</span>' if icon else ""
    kicker_html = f'<div class="kaisan-page-kicker">{escape(str(kicker))}</div>' if kicker else ""
    meta_items = "".join(f"<span>{escape(str(item))}</span>" for item in (meta or []) if str(item).strip())
    meta_html = f'<div class="kaisan-page-meta">{meta_items}</div>' if meta_items else ""

    st.markdown(
        f"""
        <section class="kaisan-page-hero">
          <div class="kaisan-logo-card">{logo_html}</div>
          <div class="kaisan-page-copy">
            {kicker_html}
            <h1>{icon_html}{escape(str(title))}</h1>
            <p>{escape(str(subtitle))}</p>
          </div>
          {meta_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str = "", kicker: str = ""):
    kicker_html = f'<span class="kaisan-section-kicker">{escape(str(kicker))}</span>' if kicker else ""
    subtitle_html = f"<p>{escape(str(subtitle))}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="kaisan-section-heading">
          <div>
            {kicker_html}
            <h2>{escape(str(title))}</h2>
            {subtitle_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_divider():
    st.markdown('<div class="kaisan-divider"></div>', unsafe_allow_html=True)


def mark_operation_status(title: str, detail: str = "", tone: str = "success"):
    st.session_state["kaisan_operation_status"] = {
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "tone": str(tone or "success").strip(),
        "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


def render_status_notice(title: str, detail: str = "", tone: str = "info", meta: str = ""):
    tone = str(tone or "info").strip().lower()
    if tone not in {"info", "success", "warning", "danger"}:
        tone = "info"

    detail_html = f"<p>{escape(str(detail))}</p>" if detail else ""
    meta_html = f"<small>{escape(str(meta))}</small>" if meta else ""
    st.markdown(
        f"""
        <div class="kaisan-notice kaisan-notice-{tone}">
          <div>
            <strong>{escape(str(title))}</strong>
            {detail_html}
          </div>
          {meta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_operation_status():
    status = st.session_state.get("kaisan_operation_status")
    if not status:
        return
    render_status_notice(
        status.get("title", "Operação concluída"),
        status.get("detail", ""),
        status.get("tone", "success"),
        f"Atualizado em {status.get('time', '')}",
    )


def render_status_cards(cards: list[dict]):
    items = []
    for card in cards:
        tone = str(card.get("tone", "info") or "info").lower()
        if tone not in {"info", "success", "warning", "danger", "neutral", "violet"}:
            tone = "info"
        title = escape(str(card.get("title", "")))
        value = escape(str(card.get("value", "")))
        detail = escape(str(card.get("detail", "")))
        items.append(
            f'<div class="kaisan-status-card kaisan-status-{tone}">'
            f"<span>{title}</span>"
            f"<strong>{value}</strong>"
            f"<small>{detail}</small>"
            "</div>"
        )

    st.markdown(
        f'<div class="kaisan-status-grid">{"".join(items)}</div>',
        unsafe_allow_html=True,
    )


def render_status_chip(label: str, tone: str = "info") -> str:
    tone = str(tone or "info").lower()
    if tone not in {"info", "success", "warning", "danger", "neutral", "violet"}:
        tone = "info"
    return f'<span class="kaisan-chip kaisan-chip-{tone}">{escape(str(label))}</span>'


def render_stage_grid(stages: list[dict]):
    items = []
    for stage in stages:
        tone = str(stage.get("tone", "info") or "info").lower()
        if tone not in {"info", "success", "warning", "danger", "neutral", "violet"}:
            tone = "info"
        status = escape(str(stage.get("status", "")))
        title = escape(str(stage.get("title", "")))
        detail = escape(str(stage.get("detail", "")))
        items.append(
            f'<div class="kaisan-stage-tile kaisan-stage-{tone}">'
            f'{render_status_chip(status, tone) if status else ""}'
            f"<strong>{title}</strong>"
            f"<small>{detail}</small>"
            "</div>"
        )

    st.markdown(
        f'<div class="kaisan-stage-grid">{"".join(items)}</div>',
        unsafe_allow_html=True,
    )


def render_focus_strip(title: str, detail: str, items: list[dict | str] | None = None, tone: str = "warning"):
    tone = str(tone or "warning").lower()
    if tone not in {"info", "success", "warning", "danger", "neutral"}:
        tone = "warning"

    chips = []
    for item in items or []:
        if isinstance(item, dict):
            label = item.get("label", "")
            chip_tone = item.get("tone", tone)
        else:
            label = str(item)
            chip_tone = tone
        if str(label).strip():
            chips.append(render_status_chip(str(label), str(chip_tone)))

    st.markdown(
        f"""
        <section class="kaisan-focus-strip kaisan-focus-{tone}">
          <div>
            <span>Foco operacional</span>
            <strong>{escape(str(title))}</strong>
            <p>{escape(str(detail))}</p>
          </div>
          <div class="kaisan-focus-chips">{"".join(chips)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_progress_panel(
    title: str,
    value: str,
    detail: str = "",
    progress: float = 0.0,
    tone: str = "info",
    meta: str = "",
):
    tone = str(tone or "info").lower()
    if tone not in {"info", "success", "warning", "danger", "neutral"}:
        tone = "info"
    try:
        progress_value = max(0.0, min(100.0, float(progress)))
    except Exception:
        progress_value = 0.0

    meta_html = render_status_chip(meta, tone) if str(meta or "").strip() else ""
    detail_html = f"<p>{escape(str(detail))}</p>" if detail else ""
    st.markdown(
        f"""
        <section class="kaisan-progress-panel kaisan-progress-{tone}">
          <div>
            <span>{escape(str(title))}</span>
            <strong>{escape(str(value))}</strong>
            {detail_html}
            <div class="kaisan-progress-track" aria-hidden="true">
              <div style="width:{progress_value:.1f}%"></div>
            </div>
          </div>
          {meta_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_intro_html(
    month_label: str,
    subtitle: str = "Operação estoque e expedição",
) -> str:
    logo_uri = _logo_data_uri()
    logo_html = f'<img src="{logo_uri}" alt="Kaisan" />' if logo_uri else '<span>K</span>'

    return (
        '<div class="kaisan-sidebar-brand">'
        f'<div class="kaisan-sidebar-logo">{logo_html}</div>'
        '<div>'
        '<strong>Avaliação &<br>Bonificação</strong>'
        f'<small>{escape(str(subtitle))}</small>'
        '</div>'
        '</div>'
        '<div class="kaisan-sidebar-month">'
        '<small>Competência ativa</small>'
        f'<strong>{escape(str(month_label))}</strong>'
        '</div>'
    )


def _sidebar_stats_html(stats: list[dict] | None = None) -> str:
    stat_items = []
    for stat in stats or []:
        label = escape(str(stat.get("label", "")))
        value = escape(str(stat.get("value", "")))
        if label or value:
            stat_items.append(f"<div><span>{label}</span><strong>{value}</strong></div>")

    return f'<div class="kaisan-sidebar-stats">{"".join(stat_items)}</div>' if stat_items else ""


def _sidebar_step_html(
    steps: list[dict],
    query_key: str = "tela",
    clickable: bool = False,
) -> str:
    step_items = []
    for index, step in enumerate(steps, start=1):
        tone = str(step.get("tone", "neutral") or "neutral").lower()
        if tone not in {"info", "success", "warning", "danger", "neutral"}:
            tone = "neutral"
        active = " is-active" if step.get("active") else ""
        title = escape(str(step.get("title", "")))
        detail = escape(str(step.get("detail", "")))
        content = (
            f'<span class="kaisan-step-number">{index}</span>'
            f'<span class="kaisan-step-copy"><strong>{title}</strong><small>{detail}</small></span>'
            f'<span class="kaisan-step-dot kaisan-dot-{tone}"></span>'
        )
        if clickable:
            option = str(step.get("option", step.get("title", "")))
            aria_current = ' aria-current="page"' if step.get("active") else ""
            step_items.append(
                f'<a class="kaisan-process-step kaisan-nav-step{active}" href="?{escape(query_key)}={quote(option)}"'
                f' target="_self"{aria_current}>{content}</a>'
            )
        else:
            step_items.append(f'<div class="kaisan-process-step{active}">{content}</div>')

    return f'<nav class="kaisan-process-list" aria-label="Navegação do processo">{"".join(step_items)}</nav>'


def render_sidebar_process(
    month_label: str,
    steps: list[dict],
    stats: list[dict] | None = None,
    subtitle: str = "Operação estoque e expedição",
):
    html = _sidebar_intro_html(month_label, subtitle)
    html += _sidebar_step_html(steps, clickable=False)
    html += _sidebar_stats_html(stats)
    st.sidebar.markdown(html, unsafe_allow_html=True)


def render_sidebar_navigation(
    month_label: str,
    steps: list[dict],
    stats: list[dict] | None = None,
    subtitle: str = "Operação estoque e expedição",
    query_key: str = "tela",
    key: str = "main_menu_nav",
) -> str | None:
    html = _sidebar_intro_html(month_label, subtitle)
    st.sidebar.markdown(html, unsafe_allow_html=True)

    options = [str(step.get("option", step.get("title", ""))) for step in steps]
    options = [option for option in options if option]
    if not options:
        st.sidebar.markdown(_sidebar_stats_html(stats), unsafe_allow_html=True)
        return None

    active_option = next(
        (
            str(step.get("option", step.get("title", "")))
            for step in steps
            if step.get("active")
        ),
        options[0],
    )
    active_index = options.index(active_option) if active_option in options else 0
    labels = {}
    for index, step in enumerate(steps, start=1):
        option = str(step.get("option", step.get("title", "")))
        title = str(step.get("title", option))
        detail = str(step.get("detail", "") or "").strip()
        labels[option] = f"{index}. {title}" + (f" · {detail}" if detail else "")

    selected = st.sidebar.radio(
        "Navegação",
        options,
        index=active_index,
        format_func=lambda option: labels.get(option, str(option)),
        key=key,
        label_visibility="collapsed",
    )
    st.sidebar.markdown(_sidebar_stats_html(stats), unsafe_allow_html=True)
    return selected


def apply_kaisan_admin_theme():
    st.markdown(
        """
        <style>
        :root {
          --kaisan-ink: #12263a;
          --kaisan-muted: #5f7386;
          --kaisan-soft: #8a9aaa;
          --kaisan-navy: #173452;
          --kaisan-navy-deep: #0b182a;
          --kaisan-blue: #347da5;
          --kaisan-blue-soft: #d9e9f2;
          --kaisan-green: #177864;
          --kaisan-green-soft: #e5f4ef;
          --kaisan-amber: #cb8a19;
          --kaisan-amber-soft: #fff2dc;
          --kaisan-red: #b04557;
          --kaisan-red-soft: #fae9ec;
          --kaisan-bg: #edf3f7;
          --kaisan-bg-alt: #e8f0f6;
          --kaisan-surface: #ffffff;
          --kaisan-surface-soft: #f9fcff;
          --kaisan-line: rgba(23, 52, 82, 0.12);
          --kaisan-line-strong: rgba(23, 52, 82, 0.22);
          --kaisan-shadow: 0 14px 30px rgba(16, 38, 60, 0.10);
          --kaisan-shadow-soft: 0 8px 18px rgba(16, 38, 60, 0.07);
          --kaisan-radius: 8px;
          --kaisan-radius-sm: 8px;
          --kaisan-page-bg: linear-gradient(180deg, #f6f9fc 0%, #edf3f7 48%, #e8f0f6 100%);
        }

        html,
        body,
        [data-testid="stAppViewContainer"] {
          color: var(--kaisan-ink);
          background: var(--kaisan-page-bg);
          font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
          accent-color: var(--kaisan-blue);
        }

        [data-testid="stHeader"] {
          background: transparent;
        }

        [data-testid="block-container"] {
          max-width: 1240px;
          padding-top: 1.35rem;
          padding-bottom: 3rem;
        }

        [data-testid="stHeading"] a,
        [data-testid="stHeading"] button,
        [data-testid="stHeaderActionElements"] {
          display: none !important;
        }

        h1, h2, h3,
        [data-testid="stMetricValue"] {
          color: var(--kaisan-ink);
          font-family: "Space Grotesk", "Segoe UI", sans-serif;
          letter-spacing: 0;
        }

        .kaisan-page-hero {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto;
          align-items: center;
          gap: 1rem;
          margin: 0 0 0.85rem;
          padding: 0.1rem 0 0.72rem;
          border-bottom: 1px solid var(--kaisan-line-strong);
        }

        .kaisan-logo-card {
          width: 54px;
          height: 54px;
          display: grid;
          place-items: center;
          overflow: hidden;
          border: 1px solid rgba(23, 52, 82, 0.08);
          border-radius: 8px;
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        .kaisan-logo-card img {
          width: 70%;
          height: auto;
          object-fit: contain;
        }

        .kaisan-page-copy {
          min-width: 0;
        }

        .kaisan-page-kicker,
        .kaisan-section-kicker {
          display: inline-block;
          color: var(--kaisan-blue);
          font-size: 0.72rem;
          font-weight: 800;
          letter-spacing: 0.14em;
          text-transform: uppercase;
        }

        .kaisan-page-copy h1 {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 0.72rem;
          margin: 0.1rem 0 0.38rem;
          font-size: clamp(1.55rem, 2.1vw, 2.05rem);
          line-height: 1.05;
          overflow-wrap: anywhere;
        }

        .kaisan-page-icon {
          display: inline-grid;
          place-items: center;
          width: 2rem;
          height: 2rem;
          border-radius: 8px;
          background: var(--kaisan-blue-soft);
          color: var(--kaisan-blue);
          font-size: 1.18rem;
        }

        .kaisan-page-copy p,
        .kaisan-section-heading p {
          max-width: 46rem;
          margin: 0;
          color: var(--kaisan-muted);
        }

        .kaisan-page-meta {
          display: flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          align-items: flex-end;
          gap: 0.42rem;
          min-width: 0;
          max-width: 28rem;
        }

        .kaisan-page-meta span {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          max-width: 100%;
          min-width: 0;
          padding: 0.32rem 0.58rem;
          border: 1px solid rgba(52, 125, 165, 0.18);
          border-radius: 999px;
          background: #eef6fb;
          color: #1f5d80;
          font-size: 0.76rem;
          font-weight: 800;
          line-height: 1.12;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .kaisan-section-heading {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          margin: 1.4rem 0 0.85rem;
        }

        .kaisan-section-heading h2 {
          margin: 0.05rem 0 0.2rem;
          font-size: clamp(1.35rem, 2vw, 1.85rem);
        }

        .kaisan-divider {
          height: 1px;
          margin: 1.35rem 0;
          background: var(--kaisan-line-strong);
        }

        .kaisan-status-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 0.8rem;
          margin: 0.95rem 0 1.1rem;
        }

        .kaisan-status-card {
          min-height: 112px;
          padding: 0.95rem 1rem;
          border: 1px solid var(--kaisan-line);
          border-left: 5px solid var(--kaisan-blue);
          border-radius: 8px;
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        .kaisan-status-card span {
          display: block;
          margin-bottom: 0.4rem;
          color: var(--kaisan-muted);
          font-size: 0.76rem;
          font-weight: 800;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .kaisan-status-card strong {
          display: block;
          color: var(--kaisan-ink);
          font-size: 1.35rem;
          line-height: 1.18;
          overflow-wrap: anywhere;
        }

        .kaisan-status-card small {
          display: block;
          margin-top: 0.48rem;
          color: var(--kaisan-muted) !important;
          line-height: 1.35;
        }

        .kaisan-status-info {
          border-left-color: var(--kaisan-blue);
          background: linear-gradient(180deg, #ffffff 0%, #f6fbfe 100%);
        }

        .kaisan-status-success {
          border-left-color: var(--kaisan-green);
          background: linear-gradient(180deg, #ffffff 0%, var(--kaisan-green-soft) 100%);
        }

        .kaisan-status-warning {
          border-left-color: var(--kaisan-amber);
          background: linear-gradient(180deg, #ffffff 0%, var(--kaisan-amber-soft) 100%);
        }

        .kaisan-status-danger {
          border-left-color: var(--kaisan-red);
          background: linear-gradient(180deg, #ffffff 0%, var(--kaisan-red-soft) 100%);
        }

        .kaisan-status-neutral {
          border-left-color: var(--kaisan-line-strong);
          background: var(--kaisan-surface-soft);
        }

        .kaisan-status-violet {
          border-left-color: #66579f;
          background: linear-gradient(180deg, #ffffff 0%, #f3effb 100%);
        }

        .kaisan-chip {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          max-width: 100%;
          min-height: 1.65rem;
          padding: 0.22rem 0.55rem;
          border-radius: 999px;
          font-size: 0.74rem;
          font-weight: 850;
          line-height: 1.1;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .kaisan-chip-info {
          color: var(--kaisan-blue);
          background: #e4f0f6;
        }

        .kaisan-chip-success {
          color: var(--kaisan-green);
          background: var(--kaisan-green-soft);
        }

        .kaisan-chip-warning {
          color: #8b580c;
          background: var(--kaisan-amber-soft);
        }

        .kaisan-chip-danger {
          color: var(--kaisan-red);
          background: var(--kaisan-red-soft);
        }

        .kaisan-chip-neutral {
          color: var(--kaisan-muted);
          background: #edf2f6;
        }

        .kaisan-chip-violet {
          color: #66579f;
          background: #eeeaf8;
        }

        .kaisan-stage-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 0.75rem;
          margin: 0.9rem 0 1rem;
        }

        .kaisan-stage-tile {
          min-height: 104px;
          padding: 0.88rem;
          border: 1px solid var(--kaisan-line);
          border-top: 4px solid var(--kaisan-blue);
          border-radius: var(--kaisan-radius);
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        .kaisan-stage-tile strong {
          display: block;
          margin-top: 0.48rem;
          color: var(--kaisan-ink);
          font-size: 0.98rem;
          line-height: 1.2;
          overflow-wrap: anywhere;
        }

        .kaisan-stage-tile small {
          display: block;
          margin-top: 0.35rem;
          line-height: 1.32;
        }

        .kaisan-stage-success {
          border-top-color: var(--kaisan-green);
        }

        .kaisan-stage-warning {
          border-top-color: var(--kaisan-amber);
        }

        .kaisan-stage-danger {
          border-top-color: var(--kaisan-red);
        }

        .kaisan-stage-neutral {
          border-top-color: var(--kaisan-line-strong);
        }

        .kaisan-stage-violet {
          border-top-color: #66579f;
        }

        .kaisan-focus-strip {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          align-items: center;
          gap: 1rem;
          margin: 0.95rem 0 1.1rem;
          padding: 0.9rem 1rem;
          border: 1px solid var(--kaisan-line);
          border-left: 5px solid var(--kaisan-amber);
          border-radius: var(--kaisan-radius);
          background: var(--kaisan-amber-soft);
          box-shadow: var(--kaisan-shadow-soft);
        }

        .kaisan-focus-strip span:first-child,
        .kaisan-progress-panel span:first-child {
          display: block;
          margin-bottom: 0.18rem;
          color: var(--kaisan-muted);
          font-size: 0.72rem;
          font-weight: 850;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .kaisan-focus-strip strong {
          display: block;
          color: var(--kaisan-ink);
          font-size: 1rem;
        }

        .kaisan-focus-strip p {
          margin: 0.15rem 0 0;
          color: var(--kaisan-muted);
        }

        .kaisan-focus-chips {
          display: flex;
          justify-content: flex-end;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .kaisan-focus-info {
          border-left-color: var(--kaisan-blue);
          background: #eef6fb;
        }

        .kaisan-focus-success {
          border-left-color: var(--kaisan-green);
          background: var(--kaisan-green-soft);
        }

        .kaisan-focus-danger {
          border-left-color: var(--kaisan-red);
          background: var(--kaisan-red-soft);
        }

        .kaisan-progress-panel {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 1rem;
          align-items: center;
          margin: 0.85rem 0 1rem;
          padding: 0.9rem 1rem;
          border: 1px solid #cfe8df;
          border-left: 5px solid var(--kaisan-green);
          border-radius: var(--kaisan-radius);
          background: #f3f9f7;
          box-shadow: var(--kaisan-shadow-soft);
        }

        .kaisan-progress-panel strong {
          display: block;
          color: var(--kaisan-ink);
          font-size: 1.12rem;
          line-height: 1.2;
        }

        .kaisan-progress-panel p {
          margin: 0.18rem 0 0.55rem;
          color: var(--kaisan-muted);
        }

        .kaisan-progress-track {
          width: 100%;
          height: 0.55rem;
          overflow: hidden;
          border-radius: 999px;
          background: rgba(15, 37, 64, 0.08);
        }

        .kaisan-progress-track div {
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(90deg, var(--kaisan-green), var(--kaisan-blue));
        }

        .kaisan-progress-warning {
          border-left-color: var(--kaisan-amber);
          background: #fff8ec;
        }

        .kaisan-progress-warning .kaisan-progress-track div {
          background: linear-gradient(90deg, var(--kaisan-amber), #d66b56);
        }

        .kaisan-progress-danger {
          border-left-color: var(--kaisan-red);
          background: var(--kaisan-red-soft);
        }

        .kaisan-progress-danger .kaisan-progress-track div {
          background: linear-gradient(90deg, var(--kaisan-red), #d66b56);
        }

        .kaisan-progress-neutral {
          border-left-color: var(--kaisan-line-strong);
          border-color: var(--kaisan-line);
          background: var(--kaisan-surface);
        }

        .kaisan-progress-neutral .kaisan-progress-track div {
          background: var(--kaisan-line-strong);
        }

        .kaisan-notice {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: center;
          margin: 0.8rem 0 1.1rem;
          padding: 0.82rem 1rem;
          border: 1px solid var(--kaisan-line);
          border-left: 5px solid var(--kaisan-blue);
          border-radius: 8px;
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        .kaisan-notice > div {
          min-width: 0;
        }

        .kaisan-notice strong {
          display: block;
          color: var(--kaisan-ink);
          font-size: 0.98rem;
        }

        .kaisan-notice p {
          margin: 0.15rem 0 0;
          color: var(--kaisan-muted);
        }

        .kaisan-notice small {
          flex: 0 0 auto;
          color: var(--kaisan-muted) !important;
        }

        .kaisan-notice-success {
          border-left-color: var(--kaisan-green);
          background: var(--kaisan-green-soft);
        }

        .kaisan-notice-warning {
          border-left-color: var(--kaisan-amber);
          background: var(--kaisan-amber-soft);
        }

        .kaisan-notice-danger {
          border-left-color: var(--kaisan-red);
          background: var(--kaisan-red-soft);
        }

        h2 {
          font-size: clamp(1.8rem, 2.4vw, 2.55rem);
          line-height: 1.08;
        }

        h3 {
          font-size: clamp(1.28rem, 1.8vw, 1.65rem);
        }

        p, label, .stCaption, [data-testid="stMarkdownContainer"] {
          color: var(--kaisan-ink);
        }

        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] *,
        [data-testid="stForm"] label,
        [data-testid="stForm"] label *,
        [data-baseweb="checkbox"] *,
        [data-baseweb="radio"] * {
          color: var(--kaisan-ink) !important;
        }

        [data-testid="stCaptionContainer"],
        .stCaption,
        small {
          color: var(--kaisan-muted) !important;
        }

        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, #173452 0%, #0b182a 100%);
          border-right: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: 10px 0 24px rgba(11, 24, 42, 0.16);
          overflow-x: hidden;
        }

        [data-testid="stSidebar"],
        [data-testid="stSidebar"] * {
          box-sizing: border-box;
        }

        [data-testid="stSidebar"] * {
          color: rgba(244, 251, 255, 0.92) !important;
        }

        [data-testid="stSidebar"] > div,
        [data-testid="stSidebar"] section {
          max-width: 100%;
          overflow-x: hidden;
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] small {
          color: rgba(227, 237, 246, 0.68) !important;
        }

        [data-testid="stSidebar"] hr {
          border-color: rgba(255, 255, 255, 0.12);
        }

        .kaisan-sidebar-brand {
          display: flex;
          align-items: center;
          gap: 0.72rem;
          margin: 0.2rem 0 1.2rem;
        }

        .kaisan-sidebar-brand > div:last-child {
          min-width: 0;
        }

        .kaisan-sidebar-brand strong {
          display: block;
          color: #ffffff !important;
          font-size: 1.05rem;
          line-height: 1.08;
        }

        .kaisan-sidebar-brand small {
          display: block;
          margin-top: 0.3rem;
        }

        .kaisan-sidebar-logo {
          flex: 0 0 auto;
          width: 42px;
          height: 42px;
          display: grid;
          place-items: center;
          overflow: hidden;
          border-radius: 8px;
          background: #ffffff;
        }

        .kaisan-sidebar-logo img {
          width: 74%;
          height: auto;
          object-fit: contain;
        }

        .kaisan-sidebar-month {
          display: grid;
          gap: 0.22rem;
          margin: 0 0 1rem;
          padding: 0.82rem;
          border: 1px solid rgba(255, 255, 255, 0.13);
          border-radius: var(--kaisan-radius);
          background: rgba(255, 255, 255, 0.07);
        }

        .kaisan-sidebar-month strong {
          color: #ffffff !important;
          font-size: 1rem;
        }

        .kaisan-process-list {
          display: grid;
          gap: 0.55rem;
          margin: 1rem 0;
        }

        .kaisan-process-step {
          display: grid;
          grid-template-columns: 1.8rem minmax(0, 1fr) auto;
          gap: 0.6rem;
          align-items: center;
          padding: 0.62rem;
          border: 1px solid transparent;
          border-radius: var(--kaisan-radius);
          background: rgba(255, 255, 255, 0.05);
          text-decoration: none !important;
        }

        .kaisan-nav-step {
          cursor: pointer;
          transition: background 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
        }

        .kaisan-nav-step:hover {
          border-color: rgba(255, 255, 255, 0.14);
          background: rgba(255, 255, 255, 0.1);
        }

        .kaisan-nav-step:focus-visible {
          outline: 2px solid rgba(255, 255, 255, 0.72);
          outline-offset: 2px;
        }

        .kaisan-nav-step:visited,
        .kaisan-nav-step:hover,
        .kaisan-nav-step:focus {
          color: rgba(244, 251, 255, 0.92) !important;
          text-decoration: none !important;
        }

        .kaisan-process-step.is-active {
          background: rgba(52, 125, 165, 0.31);
          box-shadow: inset 3px 0 0 #ffffff, inset 0 0 0 1px rgba(255, 255, 255, 0.12);
        }

        .kaisan-step-number {
          width: 1.8rem;
          height: 1.8rem;
          display: grid;
          place-items: center;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.12);
          color: #ffffff !important;
          font-weight: 850;
          font-size: 0.78rem;
        }

        .kaisan-step-copy {
          min-width: 0;
        }

        .kaisan-step-copy strong {
          display: block;
          color: #ffffff !important;
          font-size: 0.9rem;
          line-height: 1.12;
        }

        .kaisan-step-copy small {
          display: block;
          margin-top: 0.18rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .kaisan-step-dot {
          width: 0.62rem;
          height: 0.62rem;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.38);
        }

        .kaisan-dot-success {
          background: var(--kaisan-green);
        }

        .kaisan-dot-warning {
          background: var(--kaisan-amber);
        }

        .kaisan-dot-danger {
          background: var(--kaisan-red);
        }

        .kaisan-dot-info {
          background: #7bc4e8;
        }

        .kaisan-sidebar-stats {
          display: grid;
          gap: 0.55rem;
          margin-top: 1.2rem;
          padding-top: 1rem;
          border-top: 1px solid rgba(255, 255, 255, 0.13);
        }

        .kaisan-sidebar-stats div {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.8rem;
          font-size: 0.86rem;
        }

        .kaisan-sidebar-stats strong {
          flex: 0 0 auto;
          color: #ffffff !important;
          font-size: 0.9rem;
        }

        .kaisan-sidebar-stats span {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        [data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stButton"]),
        [data-testid="stSidebar"] [data-testid="stButton"],
        [data-testid="stSidebar"] .stButton,
        [data-testid="stSidebar"] .stButton > button,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
          width: 100% !important;
        }

        [data-testid="stSidebar"] .stButton > button,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
          min-height: 2.35rem;
          justify-content: center;
          background: #ffffff !important;
          color: var(--kaisan-navy) !important;
        }

        [data-testid="stSidebar"] [data-testid="stButton"] button *,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] * {
          color: var(--kaisan-navy) !important;
        }

        [data-testid="stSidebar"] [role="radiogroup"] {
          gap: 0.35rem;
        }

        [data-testid="stSidebar"] [role="radio"] {
          padding: 0.34rem 0.5rem;
          border-radius: var(--kaisan-radius-sm);
        }

        [data-testid="stSidebar"] [role="radio"]:has(input:checked) {
          background: rgba(52, 125, 165, 0.28);
          box-shadow: inset 3px 0 0 #ffffff, inset 0 0 0 1px rgba(255, 255, 255, 0.14);
        }

        [data-testid="stSidebar"] [data-baseweb="radio"] {
          width: 100%;
          padding: 0.34rem 0.5rem;
          border-radius: var(--kaisan-radius-sm);
        }

        [data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked) {
          background: rgba(52, 125, 165, 0.28);
          box-shadow: inset 3px 0 0 #ffffff, inset 0 0 0 1px rgba(255, 255, 255, 0.14);
        }

        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) {
          min-height: 126px;
          padding: 1rem 1.08rem;
          border: 1px solid var(--kaisan-line);
          border-radius: var(--kaisan-radius);
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) {
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(255, 255, 255, 0.14);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }

        [data-testid="stMetric"] {
          min-height: 92px;
        }

        [data-testid="stMetricLabel"] {
          color: var(--kaisan-muted);
          font-size: 0.72rem;
          font-weight: 800;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        [data-testid="stMetricValue"] {
          color: var(--kaisan-ink);
          font-size: clamp(1.55rem, 2.2vw, 2.05rem);
          font-weight: 700;
        }

        div[data-testid="stAlert"] {
          border: 1px solid rgba(52, 125, 165, 0.16);
          border-radius: var(--kaisan-radius-sm);
          background: var(--kaisan-surface-soft);
        }

        div[data-testid="stAlert"] * {
          color: var(--kaisan-ink) !important;
        }

        div[data-testid="stExpander"] {
          overflow: hidden;
          border: 1px solid var(--kaisan-line) !important;
          border-radius: var(--kaisan-radius) !important;
          background: var(--kaisan-surface) !important;
          box-shadow: var(--kaisan-shadow-soft);
        }

        div[data-testid="stExpander"] details > summary {
          padding: 0.8rem 1rem;
          background: var(--kaisan-surface-soft);
          font-weight: 700;
        }

        .stTabs [data-baseweb="tab-list"] {
          gap: 0.25rem;
          max-width: 100%;
          overflow-x: auto;
          overflow-y: hidden;
          flex-wrap: nowrap;
          border-bottom: 1px solid var(--kaisan-line);
          scrollbar-width: thin;
        }

        .stTabs [data-baseweb="tab"] {
          flex: 0 0 auto;
          height: 2.65rem;
          padding: 0 0.95rem;
          border: 1px solid transparent;
          border-radius: 8px 8px 0 0;
          color: var(--kaisan-muted);
          font-weight: 700;
          white-space: nowrap;
        }

        .stTabs [aria-selected="true"] {
          color: var(--kaisan-navy) !important;
          background: var(--kaisan-surface);
          border-color: var(--kaisan-line);
          border-bottom-color: transparent;
        }

        .stTabs [data-baseweb="tab-highlight"] {
          background-color: var(--kaisan-blue) !important;
        }

        input[type="checkbox"],
        input[type="radio"],
        input[type="range"] {
          accent-color: var(--kaisan-blue) !important;
        }

        [data-testid="stSegmentedControl"] button[aria-pressed="true"],
        [data-testid="stSegmentedControl"] button[kind="secondary"],
        button[kind="segmented_controlActive"] {
          border-color: rgba(52, 125, 165, 0.44) !important;
          color: var(--kaisan-navy) !important;
          background: rgba(217, 233, 242, 0.72) !important;
          box-shadow: inset 0 -2px 0 var(--kaisan-blue) !important;
        }

        button[kind="segmented_control"] {
          color: var(--kaisan-ink) !important;
        }

        [data-baseweb="slider"] [role="slider"] {
          background-color: var(--kaisan-blue) !important;
          border-color: #ffffff !important;
          box-shadow: 0 5px 14px rgba(52, 125, 165, 0.24) !important;
        }

        div[data-testid="stSlider"] {
          max-width: 100%;
          overflow: hidden;
        }

        div[data-testid="stSlider"] [data-baseweb="slider"] {
          max-width: 100%;
          padding-inline: 0.12rem;
        }

        [data-baseweb="slider"] > div > div:first-child {
          background-image: linear-gradient(
            to right,
            var(--kaisan-blue) 0%,
            var(--kaisan-blue) 100%,
            rgba(151, 166, 195, 0.25) 100%,
            rgba(151, 166, 195, 0.25) 100%
          ) !important;
        }

        [data-baseweb="slider"] [aria-valuenow] {
          color: var(--kaisan-blue) !important;
        }

        [data-baseweb="slider"] div[style*="right"] {
          color: var(--kaisan-blue) !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stBaseButton-secondary"],
        [data-testid="stBaseButton-primary"] {
          width: 100%;
          min-height: 2.45rem;
          border-radius: var(--kaisan-radius-sm);
          border: 1px solid var(--kaisan-line-strong);
          background: var(--kaisan-surface);
          color: var(--kaisan-navy);
          font-weight: 800;
          line-height: 1.16;
          white-space: normal;
          text-align: center;
          box-shadow: 0 8px 20px rgba(16, 38, 60, 0.06);
          transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stBaseButton-secondary"]:hover {
          transform: translateY(-1px);
          border-color: rgba(52, 125, 165, 0.42);
          box-shadow: var(--kaisan-shadow-soft);
        }

        [data-testid="stBaseButton-primary"] {
          border-color: transparent;
          background: var(--kaisan-blue);
          color: #ffffff;
        }

        [data-testid="stBaseButton-primary"]:hover {
          background: #2b6f95;
          color: #ffffff;
        }

        input,
        textarea,
        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] {
          border-radius: var(--kaisan-radius-sm) !important;
          border-color: rgba(23, 52, 82, 0.14) !important;
          background: var(--kaisan-surface) !important;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.74);
        }

        input::placeholder,
        textarea::placeholder {
          color: var(--kaisan-soft) !important;
          opacity: 1 !important;
        }

        [data-baseweb="select"] span,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {
          color: var(--kaisan-ink) !important;
        }

        input:focus,
        textarea:focus {
          border-color: rgba(52, 125, 165, 0.55) !important;
          box-shadow: 0 0 0 0.2rem rgba(41, 127, 168, 0.14) !important;
        }

        [data-testid="stDataFrame"] {
          max-width: 100%;
          overflow: auto;
          border: 1px solid var(--kaisan-line);
          border-radius: var(--kaisan-radius);
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        [data-testid="stDataEditor"] {
          max-width: 100%;
          overflow: auto;
          border: 1px solid var(--kaisan-line);
          border-radius: var(--kaisan-radius);
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        [data-testid="stForm"] {
          padding: 1.05rem 1.1rem;
          border: 1px solid var(--kaisan-line);
          border-radius: var(--kaisan-radius);
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        [data-testid="stProgress"] > div {
          height: 0.72rem;
          border-radius: 999px;
          background: rgba(15, 37, 64, 0.08);
        }

        [data-testid="stProgress"] [role="progressbar"] > div {
          background: linear-gradient(90deg, var(--kaisan-blue), var(--kaisan-green));
        }

        a {
          color: var(--kaisan-blue);
          text-decoration-color: rgba(52, 125, 165, 0.36);
          text-underline-offset: 0.18em;
        }

        a:hover {
          color: var(--kaisan-navy);
        }

        button:focus-visible,
        input:focus-visible,
        textarea:focus-visible,
        [role="button"]:focus-visible,
        [role="tab"]:focus-visible {
          outline: 3px solid rgba(52, 125, 165, 0.24) !important;
          outline-offset: 2px !important;
        }

        @media (max-width: 768px) {
          [data-testid="block-container"] {
            padding-top: 0.85rem;
            padding-left: 0.82rem;
            padding-right: 0.82rem;
          }

          .kaisan-page-hero {
            grid-template-columns: auto minmax(0, 1fr);
            align-items: center;
            gap: 0.62rem;
            margin-top: 0;
            margin-bottom: 0.7rem;
            padding-bottom: 0.62rem;
          }

          .kaisan-logo-card {
            width: 44px;
            height: 44px;
          }

          .kaisan-page-copy h1 {
            gap: 0.42rem;
            margin-bottom: 0.18rem;
            font-size: 1.42rem;
            line-height: 1.12;
          }

          .kaisan-page-icon {
            width: 1.62rem;
            height: 1.62rem;
            font-size: 0.96rem;
          }

          .kaisan-page-copy p,
          .kaisan-section-heading p {
            font-size: 0.88rem;
            line-height: 1.32;
          }

          .kaisan-page-meta {
            grid-column: 1 / -1;
            justify-content: flex-start;
            align-items: stretch;
            min-width: 0;
          }

          .kaisan-page-meta span {
            padding: 0.26rem 0.5rem;
            font-size: 0.72rem;
          }

          h2 {
            font-size: 1.45rem;
          }

          .kaisan-section-heading {
            margin: 1rem 0 0.65rem;
          }

          .kaisan-section-heading h2 {
            font-size: 1.32rem;
          }

          .kaisan-status-card {
            min-height: auto;
            padding: 0.78rem 0.85rem;
          }

          [data-testid="stForm"] {
            padding: 0.85rem;
          }

          .stTabs [data-baseweb="tab"] {
            height: 2.35rem;
            padding: 0 0.65rem;
            font-size: 0.86rem;
          }

          .stButton > button,
          .stDownloadButton > button,
          [data-testid="stBaseButton-secondary"],
          [data-testid="stBaseButton-primary"] {
            min-height: 2.28rem;
          }

          [data-testid="stSidebar"] {
            max-width: 100vw;
            overflow-x: hidden;
          }

          div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) {
            min-height: auto;
          }

          .kaisan-focus-strip,
          .kaisan-progress-panel,
          .kaisan-notice {
            grid-template-columns: 1fr;
            align-items: stretch;
          }

          .kaisan-notice {
            display: grid;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
