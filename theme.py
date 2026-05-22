import base64
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path

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
        if tone not in {"info", "success", "warning", "danger", "neutral"}:
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
          padding-top: 1.65rem;
          padding-bottom: 3rem;
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
          margin: 0.2rem 0 1.25rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid var(--kaisan-line-strong);
        }

        .kaisan-logo-card {
          width: 76px;
          height: 76px;
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
          align-items: center;
          gap: 0.72rem;
          margin: 0.1rem 0 0.38rem;
          font-size: clamp(1.9rem, 2.5vw, 2.55rem);
          line-height: 1.05;
        }

        .kaisan-page-icon {
          display: inline-grid;
          place-items: center;
          width: 2.3rem;
          height: 2.3rem;
          border-radius: 8px;
          background: var(--kaisan-blue-soft);
          color: var(--kaisan-blue);
          font-size: 1.45rem;
        }

        .kaisan-page-copy p,
        .kaisan-section-heading p {
          max-width: 46rem;
          margin: 0;
          color: var(--kaisan-muted);
        }

        .kaisan-page-meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.45rem;
          min-width: 12rem;
        }

        .kaisan-page-meta span {
          display: inline-flex;
          justify-content: center;
          min-width: 9rem;
          padding: 0.56rem 0.82rem;
          border: 1px solid var(--kaisan-line);
          border-radius: var(--kaisan-radius-sm);
          background: var(--kaisan-surface);
          color: var(--kaisan-navy);
          font-weight: 800;
          box-shadow: var(--kaisan-shadow-soft);
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
        }

        [data-testid="stSidebar"] * {
          color: rgba(244, 251, 255, 0.92) !important;
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] small {
          color: rgba(227, 237, 246, 0.68) !important;
        }

        [data-testid="stSidebar"] hr {
          border-color: rgba(255, 255, 255, 0.12);
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
          border-bottom: 1px solid var(--kaisan-line);
        }

        .stTabs [data-baseweb="tab"] {
          height: 2.65rem;
          padding: 0 0.95rem;
          border: 1px solid transparent;
          border-radius: 8px 8px 0 0;
          color: var(--kaisan-muted);
          font-weight: 700;
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
          min-height: 2.45rem;
          border-radius: var(--kaisan-radius-sm);
          border: 1px solid var(--kaisan-line-strong);
          background: var(--kaisan-surface);
          color: var(--kaisan-navy);
          font-weight: 800;
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
          overflow: hidden;
          border: 1px solid var(--kaisan-line);
          border-radius: var(--kaisan-radius);
          background: var(--kaisan-surface);
          box-shadow: var(--kaisan-shadow-soft);
        }

        [data-testid="stDataEditor"] {
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
            padding-top: 1.25rem;
            padding-left: 1rem;
            padding-right: 1rem;
          }

          .kaisan-page-hero {
            grid-template-columns: 1fr;
            align-items: start;
            gap: 0.9rem;
            margin-top: 0;
          }

          .kaisan-logo-card {
            width: 76px;
            height: 76px;
          }

          .kaisan-page-copy h1 {
            font-size: 2.05rem;
          }

          .kaisan-page-meta {
            align-items: stretch;
            min-width: 0;
          }

          h2 {
            font-size: 1.85rem;
          }

          div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) {
            min-height: auto;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
