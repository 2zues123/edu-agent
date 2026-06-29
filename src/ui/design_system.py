from __future__ import annotations

import streamlit as st


DESIGN_SYSTEM_CSS = r"""
<style>
    :root {
        --ink: #17324A;
        --ink-secondary: #586A79;
        --ink-muted: #6D7A86;
        --ink-ghost: #9BA6AD;
        --surface: #F7F1E6;
        --surface-deep: #EFE2C8;
        --surface-soft: #FFF9EF;
        --surface-card: #FFF9EF;
        --border: #E3D8C7;
        --border-light: #ECE2D3;
        --accent: #168C8C;
        --accent-hover: #0F787A;
        --accent-soft: #DDEAE2;
        --success: #168C8C;
        --success-soft: #DDEAE2;
        --warning: #D1A050;
        --warning-soft: #F0DFC0;
        --danger: #B45842;
        --danger-soft: #EED3C6;
        --radius: 20px;
        --radius-sm: 14px;
        --radius-full: 999px;
        --shadow-sm: 0 8px 20px rgba(23, 50, 74, 0.05);
        --shadow: 0 18px 46px rgba(23, 50, 74, 0.08);
        --shadow-lg: 0 28px 70px rgba(23, 50, 74, 0.12);
    }

    .stApp {
        background:
            radial-gradient(circle at 11% 16%, rgba(199, 218, 207, 0.78) 0 118px, transparent 119px),
            radial-gradient(circle at 87% 20%, rgba(239, 223, 190, 0.86) 0 112px, transparent 113px),
            linear-gradient(180deg, var(--surface) 0%, #FBF6ED 58%, #FFFDF9 100%);
        color: var(--ink-secondary);
        font-family: "Inter", "DM Sans", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }

    [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {
        display: none !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    header[data-testid="stHeader"] {
        background: transparent;
        height: 1.5rem;
        pointer-events: none;
    }
    header[data-testid="stHeader"] button {
        pointer-events: auto;
    }
    [data-testid="stAppViewContainer"] > .main .block-container {
        max-width: 1200px;
        padding: 1.75rem 2rem 4rem;
    }

    h1, h2, h3, h4 {
        color: var(--ink) !important;
        font-weight: 750 !important;
        letter-spacing: 0 !important;
    }
    p, li {
        line-height: 1.7;
    }

    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: #D6CAB9;
        border-radius: 999px;
    }

    .ds-topnav {
        position: sticky;
        top: 10px;
        z-index: 50;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 76px;
        margin-bottom: 2rem;
        padding: 14px 18px;
        background: rgba(255, 249, 239, 0.88);
        border: 1px solid var(--border);
        border-radius: 20px;
        box-shadow: 0 1px 0 rgba(23, 50, 74, 0.04), 0 12px 30px rgba(23, 50, 74, 0.06);
        backdrop-filter: blur(18px) saturate(160%);
        -webkit-backdrop-filter: blur(18px) saturate(160%);
    }
    .ds-topnav-brand {
        display: inline-flex;
        align-items: center;
        gap: 14px;
        color: var(--ink) !important;
        font-size: 1.18rem;
        font-weight: 800;
        text-decoration: none !important;
    }
    .ds-topnav-logo {
        display: inline-grid;
        place-items: center;
        width: 42px;
        height: 42px;
        border-radius: 50%;
        background: var(--ink);
        color: #FFFFFF;
        font-size: 0.98rem;
        font-weight: 800;
        box-shadow: 0 10px 20px rgba(23, 50, 74, 0.14);
    }
    .ds-topnav-links {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .ds-topnav-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 38px;
        padding: 0 14px;
        border-radius: var(--radius-full);
        color: var(--ink-secondary) !important;
        font-size: 0.92rem;
        font-weight: 650;
        text-decoration: none !important;
        white-space: nowrap;
        transition: background 180ms ease, color 180ms ease, transform 180ms ease;
    }
    .ds-topnav-link:hover {
        color: var(--ink) !important;
        background: rgba(23, 50, 74, 0.06);
        transform: translateY(-1px);
    }
    .ds-topnav-link.active {
        color: #FFFFFF !important;
        background: var(--accent);
        box-shadow: 0 10px 22px rgba(22, 140, 140, 0.18);
    }

    .ds-hero {
        position: relative;
        overflow: hidden;
        min-height: 330px;
        margin-bottom: 28px;
        padding: clamp(34px, 5vw, 58px);
        border: 1px solid var(--border);
        border-radius: 24px;
        background: rgba(255, 249, 239, 0.76);
        box-shadow: var(--shadow);
        animation: ds-rise 520ms ease-out both;
    }
    .ds-hero::before,
    .ds-hero::after {
        content: "";
        position: absolute;
        border-radius: 50%;
        pointer-events: none;
    }
    .ds-hero::before {
        width: 230px;
        height: 230px;
        left: -58px;
        top: -78px;
        background: rgba(207, 223, 215, 0.86);
    }
    .ds-hero::after {
        width: 218px;
        height: 218px;
        right: -62px;
        top: -52px;
        background: rgba(239, 223, 190, 0.92);
    }
    .ds-hero-eyebrow,
    .ds-hero h1,
    .ds-hero p,
    .ds-hero-badges {
        position: relative;
        z-index: 1;
    }
    .ds-hero-eyebrow {
        display: inline-flex;
        align-items: center;
        min-height: 28px;
        margin-bottom: 16px;
        color: var(--accent);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.18em;
        text-transform: uppercase;
    }
    .ds-hero-eyebrow::before {
        content: "";
        display: inline-block;
        width: 10px;
        height: 10px;
        margin-right: 10px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 0 6px rgba(22, 140, 140, 0.10);
    }
    .ds-hero h1 {
        max-width: 650px;
        margin: 0 0 16px !important;
        font-size: clamp(2.3rem, 5.5vw, 4.25rem) !important;
        line-height: 1.1 !important;
    }
    .ds-hero p {
        max-width: 700px;
        margin: 0;
        color: var(--ink-secondary);
        font-size: clamp(1rem, 1.6vw, 1.25rem);
        line-height: 1.55;
    }
    .ds-hero strong {
        color: var(--ink);
    }
    .ds-hero-badges {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 20px;
    }

    .ds-badge {
        display: inline-flex;
        align-items: center;
        min-height: 32px;
        padding: 0 14px;
        border-radius: var(--radius-full);
        font-size: 0.78rem;
        font-weight: 750;
        white-space: nowrap;
    }
    .ds-badge-success {
        color: #FFFFFF;
        background: var(--accent);
        box-shadow: 0 10px 22px rgba(22, 140, 140, 0.18);
    }
    .ds-badge-muted {
        color: var(--ink);
        background: rgba(255, 249, 239, 0.8);
        border: 1px solid var(--border);
    }

    .ds-card {
        padding: 28px;
        border-radius: 20px;
        background: rgba(255, 249, 239, 0.82);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
    }
    .ds-card:hover {
        transform: translateY(-4px);
        border-color: rgba(22, 140, 140, 0.34);
        box-shadow: var(--shadow);
    }
    .ds-card-primary {
        background: linear-gradient(145deg, rgba(255, 249, 239, 0.92), rgba(221, 234, 226, 0.64));
        border-color: rgba(22, 140, 140, 0.22);
    }
    .ds-card-kicker {
        color: var(--accent);
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .ds-card-title {
        color: var(--ink);
        font-size: 1.24rem;
        font-weight: 800;
        margin: 0 0 8px;
    }
    .ds-card-desc {
        color: var(--ink-secondary);
        font-size: 0.94rem;
        line-height: 1.65;
        margin: 0 0 18px;
    }

    .ds-btn-primary,
    .stLinkButton a {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
        min-height: 42px !important;
        padding: 0 22px !important;
        border-radius: var(--radius-full) !important;
        border: 0 !important;
        background: var(--accent) !important;
        color: #FFFFFF !important;
        font-size: 0.92rem !important;
        font-weight: 760 !important;
        text-decoration: none !important;
        box-shadow: 0 10px 22px rgba(22, 140, 140, 0.18) !important;
        transition: background 180ms ease, transform 180ms ease, box-shadow 180ms ease !important;
    }
    .ds-btn-primary:hover,
    .stLinkButton a:hover {
        background: var(--accent-hover) !important;
        transform: translateY(-2px);
        box-shadow: 0 14px 28px rgba(22, 140, 140, 0.24) !important;
    }
    .ds-btn-outline {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        min-height: 42px;
        padding: 0 22px;
        border-radius: var(--radius-full);
        border: 1px solid var(--border);
        background: transparent;
        color: var(--ink);
        font-size: 0.92rem;
        font-weight: 760;
        text-decoration: none;
        transition: all 180ms ease;
    }
    .ds-btn-outline:hover {
        border-color: var(--accent);
        color: var(--accent);
        transform: translateY(-1px);
        text-decoration: none;
    }

    .ds-metric-card {
        display: flex;
        align-items: center;
        gap: 16px;
        min-height: 96px;
        padding: 18px;
        border-radius: 20px;
        background: rgba(255, 249, 239, 0.82);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
    }
    .ds-metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(22, 140, 140, 0.30);
        box-shadow: var(--shadow);
    }
    .ds-metric-icon {
        display: inline-grid;
        place-items: center;
        width: 56px;
        height: 56px;
        border-radius: 14px;
        font-size: 0;
        flex-shrink: 0;
    }
    .ds-metric-icon::after {
        content: "";
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: currentColor;
        opacity: 0.52;
    }
    .ds-metric-icon.blue { background: #DDEAE2; color: #168C8C; }
    .ds-metric-icon.green { background: #DDEAE2; color: #168C8C; }
    .ds-metric-icon.amber { background: #F0DFC0; color: #C89138; }
    .ds-metric-icon.coral { background: #EED3C6; color: #BD582F; }
    .ds-metric-icon.indigo { background: #DDEAE2; color: #17324A; }
    .ds-metric-label {
        color: var(--ink-muted);
        font-size: 0.78rem;
        font-weight: 650;
        margin-bottom: 4px;
    }
    .ds-metric-value {
        color: var(--ink);
        font-size: 1.5rem;
        font-weight: 820;
        line-height: 1.1;
    }

    .ds-section-title {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 34px 0 16px;
        color: var(--ink);
        font-size: 1.08rem;
        font-weight: 820;
    }
    .ds-section-title::before {
        content: "";
        display: inline-block;
        width: 13px;
        height: 13px;
        border-radius: 50%;
        background: var(--accent);
        box-shadow: 0 0 0 7px rgba(22, 140, 140, 0.10);
    }

    .ds-recent-list {
        display: grid;
        gap: 10px;
    }
    .ds-recent-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 18px;
        border-radius: 18px;
        background: rgba(255, 249, 239, 0.82);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        transition: transform 180ms ease, box-shadow 180ms ease;
    }
    .ds-recent-item:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow);
    }
    .ds-recent-left {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .ds-recent-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--accent);
        flex-shrink: 0;
    }
    .ds-recent-title {
        color: var(--ink);
        font-size: 0.92rem;
        font-weight: 760;
    }
    .ds-recent-meta {
        color: var(--ink-ghost);
        font-size: 0.76rem;
        font-weight: 560;
        white-space: nowrap;
    }
    .ds-timestamp {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-top: 10px;
        color: var(--ink-muted);
        font-size: 0.78rem;
        font-weight: 560;
    }

    .stButton > button {
        min-height: 42px !important;
        padding: 0 18px !important;
        border-radius: var(--radius-full) !important;
        border: 1px solid var(--border) !important;
        background: rgba(255, 249, 239, 0.88) !important;
        color: var(--ink) !important;
        font-weight: 760 !important;
        font-size: 0.9rem !important;
        transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, box-shadow 180ms ease !important;
    }
    .stButton > button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
        background: #FFFFFF !important;
        box-shadow: var(--shadow-sm) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="primary"] {
        border-color: var(--accent) !important;
        color: #FFFFFF !important;
        background: var(--accent) !important;
        box-shadow: 0 10px 22px rgba(22, 140, 140, 0.18) !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stExpander"] {
        border: 1px solid var(--border) !important;
        border-radius: 20px !important;
        background: rgba(255, 249, 239, 0.82) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover,
    [data-testid="stExpander"]:hover {
        border-color: rgba(22, 140, 140, 0.28) !important;
    }
    .stExpander [data-testid="stExpanderDetails"] {
        background: rgba(255, 249, 239, 0.68);
    }
    .stAlert {
        border-radius: 18px !important;
    }
    div[data-testid="stPopoverBody"] {
        min-width: 178px !important;
        border-radius: 18px !important;
        border: 1px solid var(--border) !important;
        background: #FFF9EF !important;
        padding: 8px !important;
        box-shadow: var(--shadow) !important;
    }

    [data-testid="stChatMessage"] {
        border-radius: 22px !important;
        border: 1px solid var(--border-light) !important;
        background: rgba(255, 249, 239, 0.84) !important;
        box-shadow: var(--shadow-sm) !important;
        padding: 0.85rem 1.05rem !important;
        margin: 0.65rem 0 !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        max-width: 78% !important;
        margin-left: auto !important;
        background: #DDEAE2 !important;
        border-color: rgba(22, 140, 140, 0.20) !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        max-width: 94% !important;
    }
    div[data-testid="stChatInput"] {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stChatInput"] > div {
        border: 1px solid rgba(22, 140, 140, 0.34) !important;
        border-radius: var(--radius-full) !important;
        background: #FFF9EF !important;
        box-shadow: var(--shadow) !important;
        outline: none !important;
        overflow: hidden !important;
        transition: border-color 180ms ease, box-shadow 180ms ease !important;
    }
    div[data-testid="stChatInput"] > div *,
    div[data-testid="stChatInput"] [data-baseweb="textarea"],
    div[data-testid="stChatInput"] [data-baseweb="base-input"],
    div[data-testid="stChatInput"] [data-baseweb="base-input"] > div {
        background: transparent !important;
        background-color: transparent !important;
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(22, 140, 140, 0.16), var(--shadow) !important;
    }
    div[data-testid="stChatInput"] textarea,
    div[data-testid="stChatInput"] textarea:focus {
        min-height: 52px !important;
        border: 0 !important;
        border-radius: 0 !important;
        background: transparent !important;
        color: var(--ink) !important;
        font-size: 0.94rem !important;
        box-shadow: none !important;
        outline: none !important;
    }

    .ds-source-text {
        color: var(--ink-secondary);
        line-height: 1.72;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
        font-size: 0.86rem;
    }
    .ds-source-text mark {
        background: #F0DFC0;
        border-radius: 4px;
        padding: 0 4px;
    }

    @keyframes ds-rise {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 760px) {
        [data-testid="stAppViewContainer"] > .main .block-container {
            padding: 1rem 1rem 3rem;
        }
        .ds-topnav {
            top: 6px;
            flex-direction: column;
            gap: 10px;
            align-items: stretch;
        }
        .ds-topnav-links {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
        }
        .ds-hero {
            min-height: 0;
            padding: 30px 22px;
        }
        .ds-hero h1 {
            font-size: clamp(2rem, 12vw, 3rem) !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            max-width: 92% !important;
        }
    }
</style>
"""


def apply_design_system() -> None:
    st.markdown(DESIGN_SYSTEM_CSS, unsafe_allow_html=True)


def inject_extra_css(extra: str) -> None:
    st.markdown(f"<style>{extra}</style>", unsafe_allow_html=True)
