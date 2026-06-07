from __future__ import annotations

import streamlit as st

# ── Design Tokens ─────────────────────────────────────────────
# Primary Palette
INK_DEEP   = "#1E1B4B"   # 深靛蓝 - 标题
INK_BODY   = "#1E293B"   # slate-800 - 正文
INK_MUTED  = "#64748B"   # slate-500 - 辅助文字
INK_SOFT   = "#94A3B8"   # slate-400 - 更淡的辅助文字
SURFACE    = "#F8FAFC"   # slate-50  - 页面背景
PANEL      = "#FFFFFF"   # 卡片/面板背景
BORDER     = "#E2E8F0"   # slate-200 - 边框
BORDER_SUBTLE = "#F1F5F9"  # slate-100 - 微边框

# Accent Colors
ACCENT_CORAL   = "#F97316"  # 珊瑚橙 - 强调色
ACCENT_CORAL_SOFT = "#FFF7ED"
ACCENT_EMERALD = "#059669"  # 翡翠绿 - 成功/数据
ACCENT_EMERALD_SOFT = "#ECFDF5"
ACCENT_INDIGO  = "#4F46E5"  # 靛蓝 - 链接/主按钮
ACCENT_INDIGO_SOFT = "#EEF2FF"
ACCENT_AMBER   = "#D97706"  # 琥珀 - 警告
ACCENT_AMBER_SOFT = "#FFFBEB"
ACCENT_ROSE    = "#E11D48"  # 玫红 - 风险
ACCENT_ROSE_SOFT = "#FFF1F2"

# Shadows
SHADOW_SM  = "0 1px 2px 0 rgba(0,0,0,0.05)"
SHADOW_MD  = "0 4px 12px -2px rgba(0,0,0,0.06), 0 2px 4px -2px rgba(0,0,0,0.04)"
SHADOW_LG  = "0 12px 32px -4px rgba(0,0,0,0.08), 0 4px 8px -4px rgba(0,0,0,0.04)"
SHADOW_XL  = "0 20px 48px -8px rgba(0,0,0,0.10), 0 6px 12px -6px rgba(0,0,0,0.04)"

# Radius
RADIUS_SM  = "6px"
RADIUS_MD  = "10px"
RADIUS_LG  = "14px"
RADIUS_XL  = "20px"

# Transitions
TRANS_FAST   = "150ms cubic-bezier(0.4, 0, 0.2, 1)"
TRANS_NORMAL = "300ms cubic-bezier(0.4, 0, 0.2, 1)"
TRANS_SLOW   = "500ms cubic-bezier(0.4, 0, 0.2, 1)"


# ═══════════════════════════════════════════════════════════════
#  CORE DESIGN SYSTEM CSS
# ═══════════════════════════════════════════════════════════════

DESIGN_SYSTEM_CSS = r"""
<style>
    /* ── Root & Reset ─────────────────────────────── */
    :root {
        --ink-deep: #1E1B4B;
        --ink-body: #1E293B;
        --ink-muted: #64748B;
        --ink-soft: #94A3B8;
        --surface: #F8FAFC;
        --panel: #FFFFFF;
        --border: #E2E8F0;
        --border-subtle: #F1F5F9;
        --accent-coral: #F97316;
        --accent-coral-soft: #FFF7ED;
        --accent-emerald: #059669;
        --accent-emerald-soft: #ECFDF5;
        --accent-indigo: #4F46E5;
        --accent-indigo-soft: #EEF2FF;
        --accent-amber: #D97706;
        --accent-amber-soft: #FFFBEB;
        --accent-rose: #E11D48;
        --accent-rose-soft: #FFF1F2;
        --shadow-sm: 0 1px 2px 0 rgba(0,0,0,0.05);
        --shadow-md: 0 4px 12px -2px rgba(0,0,0,0.06), 0 2px 4px -2px rgba(0,0,0,0.04);
        --shadow-lg: 0 12px 32px -4px rgba(0,0,0,0.08), 0 4px 8px -4px rgba(0,0,0,0.04);
        --shadow-xl: 0 20px 48px -8px rgba(0,0,0,0.10), 0 6px 12px -6px rgba(0,0,0,0.04);
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --radius-xl: 20px;
    }

    .stApp {
        background: var(--surface);
        color: var(--ink-body);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }

    /* Hide Streamlit branding */
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu, footer {
        display: none !important;
    }

    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }

    header[data-testid="stHeader"] {
        display: block;
        background: transparent;
        height: 2.5rem;
        pointer-events: none;
    }
    header[data-testid="stHeader"] button,
    header[data-testid="stHeader"] [role="button"] {
        pointer-events: auto;
    }

    [data-testid="stAppViewContainer"] > .main .block-container {
        max-width: 1200px;
        padding: 0.75rem 1.5rem 4rem;
    }

    /* ── Typography ──────────────────────────────── */
    h1, h2, h3, h4 {
        color: var(--ink-deep) !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    p, li { line-height: 1.7; }

    /* ── Scrollbar ───────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 999px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

    /* ═══════════════════════════════════════════════════ */
    /*  TOP NAVIGATION - Glassmorphism                    */
    /* ═══════════════════════════════════════════════════ */
    .ds-topnav {
        position: sticky;
        top: 0;
        z-index: 50;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 56px;
        margin: -0.15rem 0 1.5rem;
        padding: 8px 16px;
        background: rgba(248, 250, 252, 0.78);
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        border-bottom: 1px solid rgba(226, 232, 240, 0.7);
        border-radius: var(--radius-lg);
    }

    .ds-topnav-brand {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        color: var(--ink-deep);
        font-weight: 750;
        font-size: 1rem;
        text-decoration: none;
        letter-spacing: -0.01em;
    }
    .ds-topnav-brand:hover { text-decoration: none; color: var(--ink-deep); }

    .ds-topnav-logo {
        display: inline-grid; place-items: center;
        width: 34px; height: 34px;
        border-radius: 9px;
        background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
        color: var(--accent-indigo);
        font-size: 1.05rem;
    }

    .ds-topnav-links {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 4px;
        border-radius: var(--radius-md);
        background: rgba(255,255,255,0.85);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }

    .ds-topnav-link {
        display: inline-flex; align-items: center;
        min-height: 34px; padding: 0 14px;
        border-radius: 7px;
        color: var(--ink-muted);
        font-size: 0.875rem; font-weight: 600;
        text-decoration: none; white-space: nowrap;
        transition: all var(--TRANS_FAST);
    }
    .ds-topnav-link:hover {
        color: var(--ink-body);
        background: var(--surface);
        text-decoration: none;
    }
    .ds-topnav-link.active {
        color: var(--accent-indigo);
        background: var(--accent-indigo-soft);
    }

    /* ═══════════════════════════════════════════════════ */
    /*  HERO SECTION                                      */
    /* ═══════════════════════════════════════════════════ */
    .ds-hero {
        display: flex; justify-content: space-between; gap: 32px;
        align-items: flex-start;
        padding: 24px 0 20px;
    }
    .ds-hero-content { flex: 1; }
    .ds-hero-eyebrow {
        display: inline-flex; align-items: center; gap: 6px;
        min-height: 26px; padding: 2px 10px;
        border-radius: 999px;
        color: var(--accent-emerald);
        background: var(--accent-emerald-soft);
        border: 1px solid rgba(5, 150, 105, 0.15);
        font-size: 0.75rem; font-weight: 700;
        margin-bottom: 14px;
    }
    .ds-hero-eyebrow::before {
        content: ""; display: inline-block;
        width: 7px; height: 7px;
        border-radius: 50%;
        background: var(--accent-emerald);
        box-shadow: 0 0 6px rgba(5, 150, 105, 0.5);
    }
    .ds-hero h1 {
        font-size: clamp(2rem, 4vw, 3rem) !important;
        line-height: 1.12 !important;
        margin: 4px 0 8px !important;
        color: var(--ink-deep) !important;
    }
    .ds-hero p {
        max-width: 660px;
        color: var(--ink-muted);
        font-size: 0.95rem;
        line-height: 1.7;
        margin: 0;
    }
    .ds-hero-badges {
        display: flex; gap: 8px; flex-wrap: wrap;
        align-items: flex-start; padding-top: 4px;
    }
    .ds-badge {
        display: inline-flex; align-items: center;
        min-height: 30px; padding: 0 12px;
        border-radius: 999px;
        font-size: 0.78rem; font-weight: 650;
        white-space: nowrap;
    }
    .ds-badge-success {
        color: var(--accent-emerald);
        background: var(--accent-emerald-soft);
        border: 1px solid rgba(5, 150, 105, 0.15);
    }
    .ds-badge-muted {
        color: var(--ink-muted);
        background: var(--border-subtle);
        border: 1px solid var(--border);
    }

    /* ═══════════════════════════════════════════════════ */
    /*  PREMIUM CARDS                                     */
    /* ═══════════════════════════════════════════════════ */
    .ds-card {
        min-height: 180px;
        padding: 24px;
        border-radius: var(--radius-lg);
        background: var(--panel);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-md);
        transition: transform var(--TRANS_NORMAL), box-shadow var(--TRANS_NORMAL);
    }
    .ds-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }

    .ds-card-primary {
        border-color: rgba(79, 70, 229, 0.18);
        background: linear-gradient(150deg, #FFFFFF 0%, #EEF2FF 40%, #E8F0FE 100%);
    }

    .ds-card-kicker {
        color: var(--ink-muted);
        font-size: 0.72rem; font-weight: 750;
        letter-spacing: 0.03em; text-transform: uppercase;
        margin-bottom: 8px;
    }
    .ds-card-title {
        color: var(--ink-deep);
        font-size: 1.2rem; font-weight: 750;
        margin: 0 0 6px;
    }
    .ds-card-desc {
        color: var(--ink-muted);
        font-size: 0.88rem; line-height: 1.6;
        margin: 0 0 16px;
    }

    /* ── Primary CTA Button ─────────────────────── */
    .ds-btn-primary {
        display: inline-flex; align-items: center; justify-content: center;
        gap: 8px; min-height: 40px; padding: 0 20px;
        border-radius: var(--radius-md);
        border: 0;
        background: linear-gradient(135deg, var(--accent-indigo) 0%, #4338CA 100%);
        color: #FFFFFF;
        font-size: 0.875rem; font-weight: 650;
        text-decoration: none; white-space: nowrap;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25);
        transition: all var(--TRANS_FAST);
    }
    .ds-btn-primary:hover {
        background: linear-gradient(135deg, #4338CA 0%, #3730A3 100%);
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.35);
        transform: translateY(-1px);
        text-decoration: none; color: #FFFFFF;
    }

    .ds-btn-outline {
        display: inline-flex; align-items: center; justify-content: center;
        gap: 8px; min-height: 40px; padding: 0 20px;
        border-radius: var(--radius-md);
        border: 1.5px solid var(--border);
        background: var(--panel);
        color: var(--ink-body);
        font-size: 0.875rem; font-weight: 650;
        text-decoration: none; white-space: nowrap;
        cursor: pointer;
        transition: all var(--TRANS_FAST);
    }
    .ds-btn-outline:hover {
        border-color: var(--accent-indigo);
        color: var(--accent-indigo);
        background: var(--accent-indigo-soft);
        text-decoration: none;
    }

    /* ═══════════════════════════════════════════════════ */
    /*  METRIC CARDS                                      */
    /* ═══════════════════════════════════════════════════ */
    .ds-metric-card {
        display: flex; align-items: center; gap: 12px;
        padding: 16px;
        border-radius: var(--radius-md);
        background: var(--panel);
        border: 1px solid var(--border-subtle);
        box-shadow: var(--shadow-sm);
        transition: all var(--TRANS_NORMAL);
        cursor: default;
    }
    .ds-metric-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-1.5px);
    }
    .ds-metric-icon {
        display: inline-grid; place-items: center;
        width: 42px; height: 42px;
        border-radius: var(--radius-sm);
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    .ds-metric-icon.blue   { background: #EEF2FF; color: #4F46E5; }
    .ds-metric-icon.green  { background: #ECFDF5; color: #059669; }
    .ds-metric-icon.amber  { background: #FFFBEB; color: #D97706; }
    .ds-metric-icon.coral  { background: #FFF7ED; color: #F97316; }
    .ds-metric-icon.indigo { background: #EEF2FF; color: #6366F1; }
    .ds-metric-label {
        color: var(--ink-muted);
        font-size: 0.72rem; font-weight: 600;
        margin-bottom: 2px;
    }
    .ds-metric-value {
        color: var(--ink-deep);
        font-size: 1.35rem; font-weight: 750;
        line-height: 1.15;
    }

    /* ═══════════════════════════════════════════════════ */
    /*  SECTION HEADERS                                   */
    /* ═══════════════════════════════════════════════════ */
    .ds-section-title {
        display: flex; align-items: center; gap: 10px;
        margin: 32px 0 14px;
        color: var(--ink-deep);
        font-size: 1.05rem; font-weight: 750;
    }
    .ds-section-title::before {
        content: ""; display: inline-block;
        width: 3px; height: 18px;
        border-radius: 2px;
        background: var(--accent-indigo);
    }

    /* ═══════════════════════════════════════════════════ */
    /*  RECENT ACTIVITY LIST                              */
    /* ═══════════════════════════════════════════════════ */
    .ds-recent-list { display: grid; gap: 10px; }
    .ds-recent-item {
        display: flex; align-items: center; justify-content: space-between;
        padding: 14px 16px;
        border-radius: var(--radius-md);
        background: var(--panel);
        border: 1px solid var(--border-subtle);
        box-shadow: var(--shadow-sm);
        transition: all var(--TRANS_FAST);
    }
    .ds-recent-item:hover {
        box-shadow: var(--shadow-md);
        border-color: var(--border);
    }
    .ds-recent-left { display: flex; align-items: center; gap: 12px; }
    .ds-recent-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: var(--accent-emerald);
        flex-shrink: 0;
    }
    .ds-recent-title {
        color: var(--ink-body);
        font-size: 0.9rem; font-weight: 650;
    }
    .ds-recent-meta {
        color: var(--ink-soft);
        font-size: 0.76rem; font-weight: 500;
        white-space: nowrap;
    }

    /* ═══════════════════════════════════════════════════ */
    /*  TIMESTAMP BADGE                                   */
    /* ═══════════════════════════════════════════════════ */
    .ds-timestamp {
        display: inline-flex; align-items: center; gap: 6px;
        margin-top: 10px;
        color: var(--ink-muted);
        font-size: 0.76rem; font-weight: 500;
    }

    /* ═══════════════════════════════════════════════════ */
    /*  KNOWLEDGE BASE - HERO BANNER                      */
    /* ═══════════════════════════════════════════════════ */
    .ds-kb-hero {
        padding: 28px 32px;
        border-radius: var(--radius-lg);
        background: linear-gradient(135deg, var(--accent-indigo-soft) 0%, #FFFFFF 60%, var(--accent-emerald-soft) 100%);
        border: 1px solid rgba(226, 232, 240, 0.8);
        box-shadow: var(--shadow-md);
        margin-bottom: 24px;
    }
    .ds-kb-hero-eyebrow {
        display: inline-flex; align-items: center; gap: 6px;
        color: var(--accent-indigo);
        font-size: 0.72rem; font-weight: 750;
        letter-spacing: 0.04em; text-transform: uppercase;
        margin-bottom: 10px;
    }
    .ds-kb-hero h1 {
        margin: 0 0 6px !important;
        font-size: 1.8rem !important;
    }
    .ds-kb-hero p {
        color: var(--ink-muted);
        font-size: 0.92rem; line-height: 1.65;
        max-width: 680px;
        margin: 0;
    }
    .ds-kb-hero-footer {
        display: flex; align-items: center; gap: 12px;
        margin-top: 18px;
        flex-wrap: wrap;
    }
    .ds-kb-updated-badge {
        display: inline-flex; align-items: center; gap: 5px;
        min-height: 28px; padding: 0 10px;
        border-radius: 999px;
        color: var(--ink-muted);
        background: var(--panel);
        border: 1px solid var(--border);
        font-size: 0.74rem; font-weight: 600;
    }
    .ds-kb-updated-badge::before {
        content: "🕐"; font-size: 0.8rem;
    }

    /* ═══════════════════════════════════════════════════ */
    /*  KNOWLEDGE BASE - ACCORDION GROUPS                  */
    /* ═══════════════════════════════════════════════════ */
    .ds-accordion-group {
        margin-bottom: 16px;
    }

    .stExpander {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        background: var(--panel) !important;
        box-shadow: var(--shadow-sm) !important;
        overflow: hidden !important;
    }
    .stExpander:hover {
        border-color: rgba(79, 70, 229, 0.25) !important;
        box-shadow: var(--shadow-md) !important;
    }
    .stExpander [data-testid="stExpanderDetails"] {
        background: var(--surface);
    }

    /* KB data table inside expander */
    .ds-kb-table {
        width: 100%; border-collapse: collapse;
        font-size: 0.85rem;
    }
    .ds-kb-table th {
        text-align: left;
        padding: 10px 14px;
        background: var(--surface);
        color: var(--ink-muted);
        font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.03em; text-transform: uppercase;
        border-bottom: 2px solid var(--border-subtle);
    }
    .ds-kb-table td {
        padding: 12px 14px;
        border-bottom: 1px solid var(--border-subtle);
        color: var(--ink-body);
        vertical-align: middle;
    }
    .ds-kb-table tr:hover td { background: rgba(248, 250, 252, 0.6); }
    .ds-kb-table a {
        color: var(--accent-indigo);
        font-weight: 600; text-decoration: none;
    }
    .ds-kb-table a:hover { text-decoration: underline; }

    /* ═══════════════════════════════════════════════════ */
    /*  CHAT INTERFACE STYLES                             */
    /* ═══════════════════════════════════════════════════ */
    .chat-page {
        /* Wrapper for chat workspace */
    }

    .workspace-left-panel {
        position: sticky; top: 0.8rem;
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
        padding: 16px 14px;
        border-radius: var(--radius-lg);
        background: var(--panel);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-md);
    }

    .sidebar-brand {
        display: flex; align-items: center;
        justify-content: space-between; gap: 10px;
        margin-bottom: 12px;
        color: var(--ink-deep);
        font-size: 0.95rem; font-weight: 750;
    }
    .sidebar-brand-main {
        display: inline-flex; align-items: center; gap: 8px;
    }

    /* Sidebar metrics grid */
    .sidebar-stats {
        display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
        margin: 12px 0;
        padding: 12px;
        border-radius: var(--radius-md);
        background: var(--surface);
        border: 1px solid var(--border-subtle);
    }
    .sidebar-stat {
        padding: 6px 4px;
    }
    .sidebar-stat strong {
        display: block;
        color: var(--ink-deep);
        font-size: 1rem; line-height: 1.15;
    }
    .sidebar-stat span {
        color: var(--ink-muted);
        font-size: 0.66rem; font-weight: 650;
    }

    /* New chat button */
    .ds-newchat-btn {
        display: inline-flex; align-items: center; justify-content: center;
        gap: 6px; width: 100%;
        min-height: 38px;
        margin: 4px 0 14px;
        border-radius: var(--radius-md);
        border: 1.5px dashed var(--border);
        background: var(--panel);
        color: var(--accent-indigo);
        font-size: 0.84rem; font-weight: 650;
        cursor: pointer;
        text-decoration: none;
        transition: all var(--TRANS_FAST);
    }
    .ds-newchat-btn:hover {
        border-color: var(--accent-indigo);
        background: var(--accent-indigo-soft);
        text-decoration: none;
    }

    /* Chat message containers */
    [data-testid="stChatMessage"] {
        border-radius: var(--radius-lg) !important;
        border: 0 !important;
        background: var(--panel) !important;
        box-shadow: var(--shadow-sm) !important;
        padding: 0.8rem 1rem !important;
        margin: 0.6rem 0 !important;
        overflow-wrap: anywhere !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: var(--accent-indigo-soft) !important;
        margin-left: auto !important;
        max-width: 78% !important;
        border: 1px solid rgba(79, 70, 229, 0.12) !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        max-width: 94% !important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
        line-height: 1.7 !important;
        margin-bottom: 0.6rem !important;
    }

    /* Chat input */
    div[data-testid="stChatInput"] {
        background: rgba(248, 250, 252, 0.92) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-top: 1px solid var(--border) !important;
        padding: 14px 0 10px !important;
    }
    div[data-testid="stChatInput"] textarea {
        border-radius: var(--radius-xl) !important;
        border: 1.5px solid var(--border) !important;
        background: var(--panel) !important;
        padding: 12px 18px !important;
        font-size: 0.9rem !important;
        box-shadow: var(--shadow-md) !important;
        transition: all var(--TRANS_FAST) !important;
    }
    div[data-testid="stChatInput"] textarea:focus {
        border-color: var(--accent-indigo) !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1), var(--shadow-md) !important;
    }

    /* ── RAG Citation Accordion ─────────────────── */
    .ds-citation-tags {
        display: flex; flex-wrap: wrap; gap: 6px;
        margin: 10px 0 4px;
    }
    .ds-citation-tag {
        display: inline-flex; align-items: center; gap: 5px;
        min-height: 28px; padding: 2px 10px;
        border-radius: 999px;
        background: var(--panel);
        border: 1px solid var(--border);
        color: var(--ink-muted);
        font-size: 0.74rem; font-weight: 600;
        text-decoration: none;
        transition: all var(--TRANS_FAST);
    }
    .ds-citation-tag:hover {
        border-color: var(--accent-indigo);
        color: var(--accent-indigo);
        background: var(--accent-indigo-soft);
        text-decoration: none;
    }
    .ds-citation-tag .tag-icon {
        font-size: 0.8rem;
    }

    /* ── Answer meta chips ──────────────────────── */
    .ds-answer-meta {
        display: flex; flex-wrap: wrap; gap: 6px;
        margin: 8px 0 4px;
    }
    .ds-answer-chip {
        display: inline-flex; align-items: center;
        min-height: 24px; padding: 2px 9px;
        border-radius: 999px;
        background: var(--surface);
        border: 1px solid var(--border-subtle);
        color: var(--ink-muted);
        font-size: 0.72rem; font-weight: 600;
        line-height: 1.2;
    }

    /* ── Quick question pills ───────────────────── */
    .ds-quick-questions {
        display: flex; flex-wrap: wrap; gap: 8px;
        margin: 18px 0 6px;
    }
    .ds-quick-pill {
        display: inline-flex; align-items: center;
        min-height: 34px; padding: 0 14px;
        border-radius: 999px;
        background: var(--panel);
        border: 1px solid var(--border);
        color: var(--ink-body);
        font-size: 0.8rem; font-weight: 600;
        text-decoration: none;
        cursor: pointer;
        transition: all var(--TRANS_FAST);
        white-space: nowrap;
    }
    .ds-quick-pill:hover {
        background: var(--accent-indigo-soft);
        border-color: var(--accent-indigo);
        color: var(--accent-indigo);
        text-decoration: none;
        transform: translateY(-1px);
    }

    /* ── Conversation header ────────────────────── */
    .ds-conv-header {
        display: flex; align-items: center;
        justify-content: space-between; gap: 14px;
        min-height: 48px; margin-bottom: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border-subtle);
    }
    .ds-conv-title {
        color: var(--ink-deep);
        font-size: 1.05rem; font-weight: 750;
        letter-spacing: -0.01em;
    }
    .ds-conv-meta {
        color: var(--ink-muted);
        font-size: 0.76rem; margin-top: 2px;
    }
    .ds-conv-badge {
        display: inline-flex; align-items: center; gap: 5px;
        min-height: 28px; padding: 0 10px;
        border-radius: 999px;
        color: var(--accent-emerald);
        background: var(--accent-emerald-soft);
        border: 1px solid rgba(5, 150, 105, 0.15);
        font-size: 0.72rem; font-weight: 650;
        white-space: nowrap;
    }

    /* ── Empty state ────────────────────────────── */
    .ds-empty-state {
        display: grid; place-items: center;
        text-align: center;
        padding: 40px 20px 20px;
    }
    .ds-empty-state h2 {
        color: var(--ink-deep) !important;
        font-size: 1.5rem !important;
        margin: 0 0 8px !important;
    }
    .ds-empty-state p {
        color: var(--ink-muted);
        font-size: 0.9rem; line-height: 1.6;
        max-width: 480px; margin: 0 auto;
    }

    /* ── Starter cards grid ─────────────────────── */
    .ds-starter-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 20px 0;
    }
    .ds-starter-card {
        min-height: 130px; padding: 16px;
        border-radius: var(--radius-md);
        background: var(--panel);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        cursor: pointer;
        transition: all var(--TRANS_NORMAL);
    }
    .ds-starter-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
        border-color: var(--accent-indigo);
    }
    .ds-starter-card.green  { border-top: 3px solid var(--accent-emerald); }
    .ds-starter-card.blue   { border-top: 3px solid var(--accent-indigo); }
    .ds-starter-card.amber  { border-top: 3px solid var(--accent-amber); }
    .ds-starter-card.rose   { border-top: 3px solid var(--accent-rose); }
    .ds-starter-label {
        color: var(--ink-muted);
        font-size: 0.7rem; font-weight: 750;
        margin-bottom: 8px;
    }
    .ds-starter-title {
        color: var(--ink-deep);
        font-size: 0.9rem; font-weight: 700;
        line-height: 1.35;
        margin-bottom: 10px;
    }
    .ds-starter-meta {
        color: var(--ink-soft);
        font-size: 0.72rem; font-weight: 600;
    }

    /* ── Source text style ──────────────────────── */
    .ds-source-text {
        color: var(--ink-body);
        line-height: 1.72;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
        font-size: 0.84rem;
    }
    .ds-source-text mark {
        background: #FEF3C7;
        border-radius: 3px;
        padding: 0 3px;
    }

    /* ── Warning banner ─────────────────────────── */
    .stAlert {
        border-radius: var(--radius-md) !important;
        border: 1px solid rgba(217, 119, 6, 0.2) !important;
        background: var(--accent-amber-soft) !important;
    }

    /* ── General button overrides ───────────────── */
    .stButton > button {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
        background: var(--panel) !important;
        min-height: 40px !important;
        color: var(--ink-body) !important;
        font-weight: 600 !important;
        transition: all var(--TRANS_FAST) !important;
    }
    .stButton > button:hover {
        border-color: var(--accent-indigo) !important;
        color: var(--accent-indigo) !important;
        box-shadow: var(--shadow-md) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Popover menu ───────────────────────────── */
    div[data-testid="stPopoverBody"] {
        min-width: 168px !important;
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
        background: rgba(255, 255, 255, 0.98) !important;
        box-shadow: var(--shadow-lg) !important;
        padding: 6px !important;
    }

    /* ── Sidebar history items ──────────────────── */
    [data-testid="stSidebar"] [class*="st-key-history-"] button {
        border-radius: var(--radius-sm) !important;
        border: 0 !important;
        background: transparent !important;
        color: var(--ink-body) !important;
        box-shadow: none !important;
        transform: none !important;
    }
    [data-testid="stSidebar"] [class*="st-key-history-"] button:hover {
        background: rgba(79, 70, 229, 0.06) !important;
        box-shadow: none !important;
        transform: none !important;
    }
    [data-testid="stSidebar"] [class*="st-key-history-"].active-conversation button {
        background: var(--accent-indigo-soft) !important;
        font-weight: 650 !important;
    }

    /* ── Search panel ───────────────────────────── */
    .ds-search-box {
        display: flex; align-items: center; gap: 8px;
        margin-bottom: 14px;
    }

    /* ── Responsive breakpoints ─────────────────── */
    @media (max-width: 760px) {
        .ds-hero { flex-direction: column; }
        .ds-starter-grid { grid-template-columns: repeat(2, 1fr); }
        .ds-topnav { flex-direction: column; gap: 8px; align-items: flex-start; }
        .ds-topnav-links { width: 100%; display: grid; grid-template-columns: repeat(3, 1fr); }
        .ds-topnav-link { justify-content: center; }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { max-width: 92% !important; }
    }
</style>
"""


def apply_design_system() -> None:
    """Inject the core design system CSS into the page."""
    st.markdown(DESIGN_SYSTEM_CSS, unsafe_allow_html=True)


def inject_extra_css(extra: str) -> None:
    """Append additional page-specific CSS."""
    st.markdown(f"<style>{extra}</style>", unsafe_allow_html=True)
