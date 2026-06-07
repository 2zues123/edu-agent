from __future__ import annotations

import html
import textwrap

import streamlit as st

from src.conversations import load_conversations, visible_conversations
from src.knowledge_summary import load_knowledge_summary
from src.ui.design_system import apply_design_system


VALID_VIEWS = {"home", "chat", "knowledge"}

HEBTU_LOGO_URL = "https://news.hebtu.edu.cn/resources/40/202505/7EF35EDE89AF416D9AE00B8F78239B36.png"
HEBTU_HERO_URL = "https://www.hebtu.edu.cn/resources/40/202504/1F8C477E6C6340D8A5681922161AEB74.jpg"


def first_query_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def current_view() -> str:
    view = str(first_query_value(st.query_params.get("view")) or "home")
    return view if view in VALID_VIEWS else "home"


@st.cache_data(show_spinner=False)
def cached_knowledge_summary(report_mtime: float, chunks_mtime: float, web_report_mtime: float) -> dict:
    return load_knowledge_summary()


@st.cache_data(show_spinner=False)
def cached_conversations(history_mtime: float) -> list[dict]:
    return load_conversations()


def file_mtime(path: str) -> float:
    try:
        from pathlib import Path

        return Path(path).stat().st_mtime
    except OSError:
        return 0.0


def load_home_summary() -> dict:
    return cached_knowledge_summary(
        file_mtime("data/processed/build_report.json"),
        file_mtime("data/processed/chunks.jsonl"),
        file_mtime("data/processed/web_crawl_report.json"),
    )


def load_recent_conversations() -> list[dict]:
    return cached_conversations(file_mtime(".chat_history/conversations.json"))


def render_chat_view() -> None:
    from src.chat_workspace import render_workspace_page

    render_workspace_page(configure_page=False)


def render_knowledge_view() -> None:
    from src.knowledge_page import render_knowledge_base_page

    render_knowledge_base_page()


def render_recent_conversations() -> str:
    conversations = load_recent_conversations()
    recent = [item for item in visible_conversations(conversations) if item.get("messages")][:4]
    if not recent:
        return """
<div class="hebtu-recent-item">
    <span>暂无最近对话</span>
    <small>进入智能问答后会自动记录</small>
</div>
"""

    items = []
    for conversation in recent:
        title = html.escape(conversation.get("title") or "未命名教务对话")
        updated_at = html.escape(conversation.get("updated_at") or conversation.get("created_at") or "")
        count = len(conversation.get("messages", []))
        items.append(
            f"""
<div class="hebtu-recent-item">
    <span>{title}</span>
    <small>{count} 条消息 · {updated_at}</small>
</div>
"""
        )
    return "".join(items)


def render_home() -> None:
    apply_design_system()
    summary = load_home_summary()
    recent_markup = render_recent_conversations()
    stat_items = [
        ("资料文件", summary["documents"]),
        ("知识片段", summary["chunks"]),
        ("课程大纲", summary["courses"]),
        ("官网网页", summary["web_pages"]),
        ("公开附件", summary["attachments"]),
    ]
    stat_numbers = [int(value or 0) for _, value in stat_items]
    stat_max = max(stat_numbers + [1])
    stats_markup = "".join(
        f"""
                <div class="hebtu-stat" style="--stat-width: {max(8, round((int(value or 0) / stat_max) * 100))}%;">
                    <b>{html.escape(str(value))}</b>
                    <span>{html.escape(label)}</span>
                    <i></i>
                </div>
"""
        for label, value in stat_items
    )

    home_html = f"""
<style>
html {{
    scroll-behavior: smooth;
}}
.stApp {{
    background: #f5f0e8;
}}
header[data-testid="stHeader"] {{
    display: none;
}}
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
footer {{
    display: none !important;
}}
[data-testid="stAppViewContainer"] > .main .block-container {{
    max-width: none !important;
    padding: 0 !important;
}}
.main .block-container,
.block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stElementContainer"],
.element-container {{
    max-width: none !important;
}}
.main .block-container,
.block-container,
[data-testid="stMainBlockContainer"] {{
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
}}
[data-testid="stElementContainer"],
.element-container {{
    width: 100% !important;
    margin: 0 !important;
}}
.block-container p {{
    margin: 0;
}}
.hebtu-home {{
    min-height: 100vh;
    width: 100vw;
    margin-left: calc(50% - 50vw);
    margin-right: calc(50% - 50vw);
    color: #fff;
}}
.hebtu-hero {{
    position: relative;
    min-height: 100vh;
    width: 100vw;
    overflow: hidden;
    background: #0d120f;
}}
.hebtu-hero::after {{
    content: "";
    position: absolute;
    inset: -3%;
    z-index: 0;
    background: url("{HEBTU_HERO_URL}") center / cover no-repeat;
    transform: scale(1.04);
    animation: hebtuHeroDrift 22s ease-in-out infinite alternate;
}}
.hebtu-hero::before {{
    content: "";
    position: absolute;
    inset: 0;
    z-index: 1;
    background:
        linear-gradient(180deg, rgba(7, 11, 12, 0.76) 0%, rgba(7, 11, 12, 0.30) 34%, rgba(7, 11, 12, 0.65) 100%),
        radial-gradient(circle at 12% 8%, rgba(0, 0, 0, 0.70), transparent 26%),
        linear-gradient(90deg, rgba(0,0,0,0.36), transparent 24%, transparent 76%, rgba(0,0,0,0.36)),
        linear-gradient(180deg, rgba(0,0,0,0.28), transparent 18%, transparent 78%, rgba(0,0,0,0.28));
    pointer-events: none;
}}
.hebtu-topbar,
.hebtu-mainnav,
.hebtu-center,
.hebtu-scroll {{
    position: relative;
    z-index: 2;
}}
.hebtu-mainnav {{
    z-index: 12;
}}
.hebtu-center {{
    pointer-events: none;
}}
.hebtu-scroll {{
    z-index: 4;
}}
.hebtu-topbar {{
    display: flex;
    justify-content: center;
    gap: clamp(22px, 3.1vw, 52px);
    padding: 24px 24px 10px;
    font-family: Georgia, "Times New Roman", "Microsoft YaHei", serif;
    font-size: clamp(0.82rem, 1.08vw, 1.04rem);
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    text-shadow: 0 2px 16px rgba(0,0,0,0.48);
    animation: hebtuDropIn 760ms ease-out both;
}}
.hebtu-mainnav {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: start;
    gap: 28px;
    padding: 46px clamp(28px, 4vw, 72px) 0;
    animation: hebtuFadeUp 860ms 120ms ease-out both;
}}
.hebtu-menu {{
    display: flex;
    align-items: center;
    gap: clamp(18px, 2.3vw, 38px);
    flex-wrap: wrap;
    font-family: Georgia, "Times New Roman", "Microsoft YaHei", serif;
    font-size: clamp(1.02rem, 1.42vw, 1.42rem);
    font-weight: 700;
    line-height: 1.2;
    text-shadow: 0 2px 18px rgba(0,0,0,0.52);
}}
.hebtu-menu-right {{
    justify-content: flex-end;
}}
.hebtu-topbar a,
.hebtu-menu a,
.hebtu-brand {{
    color: rgba(255,255,255,0.96) !important;
    text-decoration: none !important;
    transition: color 180ms ease, transform 180ms ease, text-shadow 180ms ease;
}}
.hebtu-topbar a:hover,
.hebtu-menu a:hover {{
    color: #fff !important;
    text-decoration: underline !important;
    text-underline-offset: 7px;
    transform: translateY(-2px);
    text-shadow: 0 0 18px rgba(255,255,255,0.55), 0 2px 18px rgba(0,0,0,0.52);
}}
.hebtu-dropdown {{
    position: relative;
    display: inline-flex;
    align-items: center;
}}
.hebtu-dropdown::before {{
    content: "";
    position: absolute;
    left: 50%;
    top: 100%;
    width: max(100%, 210px);
    height: 18px;
    transform: translateX(-50%);
}}
.hebtu-dropdown > a::after {{
    content: "";
    width: 7px;
    height: 7px;
    margin-left: 9px;
    border-right: 2px solid rgba(255,255,255,0.9);
    border-bottom: 2px solid rgba(255,255,255,0.9);
    transform: translateY(-2px) rotate(45deg);
    transition: transform 180ms ease;
}}
.hebtu-dropdown:hover > a::after,
.hebtu-dropdown:focus-within > a::after {{
    transform: translateY(2px) rotate(225deg);
}}
.hebtu-dropdown-menu {{
    position: absolute;
    top: calc(100% + 14px);
    left: 50%;
    z-index: 20;
    display: grid;
    min-width: 190px;
    padding: 8px;
    border: 1px solid rgba(255,255,255,0.26);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 18px 42px rgba(0,0,0,0.24);
    backdrop-filter: blur(16px) saturate(150%);
    -webkit-backdrop-filter: blur(16px) saturate(150%);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transform: translate(-50%, 8px);
    transition:
        opacity 180ms ease 120ms,
        transform 180ms ease 120ms,
        visibility 0s linear 300ms;
    text-shadow: none;
}}
.hebtu-dropdown:hover .hebtu-dropdown-menu,
.hebtu-dropdown:focus-within .hebtu-dropdown-menu {{
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    transform: translate(-50%, 0);
    transition-delay: 0s;
}}
.hebtu-dropdown-menu a {{
    justify-content: flex-start;
    min-height: 38px;
    padding: 0 12px;
    border-radius: 6px;
    color: #172018 !important;
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 0.9rem;
    font-weight: 750;
    letter-spacing: 0;
    white-space: nowrap;
    text-shadow: none !important;
}}
.hebtu-dropdown-menu a:hover {{
    color: #174c2b !important;
    background: #eef5ee;
    text-decoration: none !important;
    transform: none;
    text-shadow: none !important;
}}
.hebtu-brand {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    min-width: 220px;
    transform: translateY(-18px);
}}
.hebtu-brand img {{
    width: clamp(160px, 13vw, 230px);
    max-height: 96px;
    object-fit: contain;
    filter: brightness(0) invert(1) drop-shadow(0 5px 18px rgba(0,0,0,0.42));
    animation: hebtuLogoPulse 4.8s ease-in-out infinite;
}}
.hebtu-brand span {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 0.92rem;
    letter-spacing: 0.26em;
    text-transform: uppercase;
    text-shadow: 0 2px 14px rgba(0,0,0,0.5);
}}
.hebtu-center {{
    display: grid;
    place-items: center;
    min-height: 46vh;
    padding: 44px 20px 84px;
    text-align: center;
    animation: hebtuFadeUp 980ms 240ms ease-out both;
}}
.hebtu-center h1 {{
    margin: 0;
    color: #fff !important;
    font-family: Georgia, "Times New Roman", "Songti SC", "SimSun", serif;
    font-size: clamp(3.2rem, 7vw, 7.4rem) !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
    line-height: 1.04 !important;
    text-shadow: 0 4px 30px rgba(0,0,0,0.38);
}}
.hebtu-center p {{
    margin-top: 18px;
    color: rgba(255,255,255,0.92);
    font-family: "Microsoft YaHei", sans-serif;
    font-size: clamp(1rem, 1.5vw, 1.28rem);
    letter-spacing: 0.06em;
    text-shadow: 0 2px 16px rgba(0,0,0,0.4);
    animation: hebtuFadeUp 980ms 520ms ease-out both;
}}
.hebtu-scroll {{
    position: absolute;
    left: 50%;
    bottom: 54px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 9px;
    transform: translateX(-50%);
    color: #fff !important;
    font-family: "Microsoft YaHei", sans-serif;
    font-size: 1.2rem;
    font-weight: 600;
    text-decoration: none !important;
    text-shadow: 0 2px 14px rgba(0,0,0,0.5);
    animation: hebtuFloat 1.8s ease-in-out infinite;
}}
.hebtu-arrow {{
    width: 2px;
    height: 52px;
    border-radius: 999px;
    background: linear-gradient(#fff, rgba(255,255,255,0));
    position: relative;
}}
.hebtu-arrow::after {{
    content: "";
    position: absolute;
    left: 50%;
    bottom: -1px;
    width: 16px;
    height: 16px;
    border-right: 2px solid #fff;
    border-bottom: 2px solid #fff;
    transform: translateX(-50%) rotate(45deg);
}}
.hebtu-body {{
    color: #172018;
    background: linear-gradient(180deg, #f5f0e8 0%, #fff 56%);
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    scroll-margin-top: 0;
}}
.hebtu-body-inner {{
    width: min(1180px, calc(100% - 42px));
    margin: 0 auto;
    padding: 50px 0 72px;
}}
.hebtu-section-head,
.hebtu-actions,
.hebtu-dynamic,
.hebtu-stats,
.hebtu-recent {{
    will-change: opacity, transform;
}}
.hebtu-body:target .hebtu-section-head,
.hebtu-body:target .hebtu-actions,
.hebtu-body:target .hebtu-dynamic,
.hebtu-body:target .hebtu-stats,
.hebtu-body:target .hebtu-recent {{
    animation: hebtuRevealUp 760ms cubic-bezier(.2,.72,.2,1) both;
}}
.hebtu-body:target .hebtu-actions {{
    animation-delay: 100ms;
}}
.hebtu-body:target .hebtu-dynamic {{
    animation-delay: 190ms;
}}
.hebtu-body:target .hebtu-stats {{
    animation-delay: 280ms;
}}
.hebtu-body:target .hebtu-recent {{
    animation-delay: 370ms;
}}
.hebtu-section-head {{
    display: flex;
    justify-content: space-between;
    gap: 28px;
    align-items: flex-end;
    margin-bottom: 22px;
}}
.hebtu-section-head h2 {{
    margin: 0;
    color: #172018 !important;
    font-size: clamp(1.55rem, 2.8vw, 2.45rem) !important;
    font-weight: 750 !important;
    letter-spacing: 0 !important;
}}
.hebtu-section-head p {{
    max-width: 510px;
    color: #677160;
    font-size: 0.96rem;
    line-height: 1.8;
}}
.hebtu-actions {{
    display: grid;
    grid-template-columns: 1.1fr 1fr 1fr;
    gap: 16px;
}}
.hebtu-card {{
    min-height: 198px;
    padding: 25px 24px;
    border: 1px solid rgba(24, 53, 35, 0.13);
    border-radius: 8px;
    background: rgba(255,255,255,0.9);
    box-shadow: 0 18px 52px rgba(34, 45, 33, 0.08);
    transform: translateY(0);
    transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease, background 220ms ease;
}}
.hebtu-card:hover {{
    transform: translateY(-7px);
    border-color: rgba(18, 80, 46, 0.32);
    background: #fff;
    box-shadow: 0 26px 64px rgba(34, 45, 33, 0.14);
}}
.hebtu-card-primary {{
    background: linear-gradient(150deg, rgba(255,255,255,0.95), rgba(235,245,236,0.92));
    border-color: rgba(18, 80, 46, 0.23);
}}
.hebtu-card strong {{
    display: block;
    color: #152019;
    font-size: 1.18rem;
    margin-bottom: 12px;
}}
.hebtu-card p {{
    color: #687264;
    font-size: 0.9rem;
    line-height: 1.75;
    margin-bottom: 20px;
}}
.hebtu-card a {{
    display: inline-flex;
    align-items: center;
    min-height: 38px;
    padding: 0 16px;
    border-radius: 4px;
    background: #174c2b;
    color: #fff !important;
    font-size: 0.9rem;
    font-weight: 700;
    text-decoration: none !important;
    transition: transform 180ms ease, box-shadow 180ms ease, background 180ms ease;
}}
.hebtu-card a:hover {{
    transform: translateX(4px);
    box-shadow: 0 10px 26px rgba(23, 76, 43, 0.2);
}}
.hebtu-card:not(.hebtu-card-primary) a {{
    background: transparent;
    color: #174c2b !important;
    padding: 0;
}}
.hebtu-card:not(.hebtu-card-primary) a:hover {{
    box-shadow: none;
}}
.hebtu-dynamic {{
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 16px;
    margin-top: 16px;
}}
.hebtu-panel {{
    border-radius: 8px;
    border: 1px solid rgba(24, 53, 35, 0.13);
    background: #fff;
    box-shadow: 0 16px 48px rgba(34, 45, 33, 0.07);
    overflow: hidden;
}}
.hebtu-panel details {{
    border-bottom: 1px solid rgba(24, 53, 35, 0.09);
}}
.hebtu-panel details:last-child {{
    border-bottom: 0;
}}
.hebtu-panel summary {{
    cursor: pointer;
    list-style: none;
    padding: 18px 20px;
    color: #172018;
    font-weight: 750;
    transition: background 160ms ease, color 160ms ease;
}}
.hebtu-panel summary::-webkit-details-marker {{
    display: none;
}}
.hebtu-panel summary::after {{
    content: "+";
    float: right;
    color: #174c2b;
    font-size: 1.1rem;
}}
.hebtu-panel details[open] summary {{
    background: #eef5ee;
    color: #174c2b;
}}
.hebtu-panel details[open] summary::after {{
    content: "-";
}}
.hebtu-panel p {{
    padding: 0 20px 18px;
    color: #657160;
    font-size: 0.9rem;
    line-height: 1.75;
}}
.hebtu-quick {{
    display: grid;
    gap: 10px;
    align-content: start;
}}
.hebtu-chip {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 48px;
    padding: 0 16px;
    border-radius: 8px;
    border: 1px solid rgba(24, 53, 35, 0.13);
    background: rgba(255,255,255,0.9);
    color: #172018 !important;
    font-weight: 700;
    text-decoration: none !important;
    box-shadow: 0 12px 34px rgba(34, 45, 33, 0.06);
    transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
}}
.hebtu-chip::after {{
    content: "→";
    color: #174c2b;
    transition: transform 180ms ease;
}}
.hebtu-chip:hover {{
    transform: translateX(6px);
    border-color: rgba(23, 76, 43, 0.35);
    background: #fff;
}}
.hebtu-chip:hover::after {{
    transform: translateX(3px);
}}
.hebtu-software {{
    margin-top: 22px;
    scroll-margin-top: 24px;
}}
.hebtu-software-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
}}
.hebtu-software .hebtu-card {{
    min-height: 236px;
}}
.hebtu-tag-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 14px 0 20px;
}}
.hebtu-tag {{
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 0 10px;
    border-radius: 999px;
    background: #eef5ee;
    color: #174c2b;
    font-size: 0.78rem;
    font-weight: 750;
}}
.hebtu-stats {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
    margin-top: 18px;
}}
.hebtu-stat {{
    padding: 18px 16px;
    border-top: 3px solid #174c2b;
    background: #fff;
    box-shadow: 0 10px 34px rgba(34, 45, 33, 0.06);
    position: relative;
    overflow: hidden;
    transition: transform 200ms ease, box-shadow 200ms ease;
}}
.hebtu-stat:hover {{
    transform: translateY(-4px);
    box-shadow: 0 18px 48px rgba(34, 45, 33, 0.11);
}}
.hebtu-stat b {{
    display: block;
    color: #1f2e1f;
    font-size: 1.45rem;
    line-height: 1;
}}
.hebtu-stat span {{
    display: block;
    margin-top: 8px;
    color: #73806e;
    font-size: 0.82rem;
}}
.hebtu-stat i {{
    display: block;
    width: var(--stat-width);
    height: 3px;
    margin-top: 14px;
    border-radius: 999px;
    background: linear-gradient(90deg, #174c2b, #78a36d);
    animation: hebtuBarGrow 920ms ease-out both;
    transform-origin: left center;
}}
.hebtu-recent {{
    margin-top: 28px;
    border-top: 1px solid rgba(31, 46, 31, 0.13);
    padding-top: 16px;
}}
.hebtu-recent-title {{
    color: #172018;
    font-weight: 750;
    margin-bottom: 8px;
}}
.hebtu-recent-item {{
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 12px 0;
    border-bottom: 1px solid rgba(31, 46, 31, 0.09);
    transition: padding 180ms ease, background 180ms ease;
}}
.hebtu-recent-item:hover {{
    padding-left: 10px;
    padding-right: 10px;
    background: rgba(238, 245, 238, 0.65);
}}
.hebtu-recent-item span {{
    color: #172018;
    font-weight: 650;
}}
.hebtu-recent-item small {{
    color: #7d8677;
    white-space: nowrap;
}}
@media (max-width: 980px) {{
    .hebtu-topbar {{
        justify-content: flex-start;
        overflow-x: auto;
        gap: 20px;
        padding-left: 18px;
    }}
    .hebtu-mainnav {{
        grid-template-columns: 1fr;
        gap: 18px;
        padding-top: 26px;
        text-align: center;
    }}
    .hebtu-brand {{
        order: -1;
        transform: none;
        margin: 0 auto;
    }}
    .hebtu-menu,
    .hebtu-menu-right {{
        justify-content: center;
        gap: 16px 24px;
        font-size: 1rem;
    }}
    .hebtu-actions,
    .hebtu-dynamic,
    .hebtu-stats,
    .hebtu-software-grid {{
        grid-template-columns: 1fr;
    }}
    .hebtu-section-head {{
        display: block;
    }}
    .hebtu-section-head p {{
        margin-top: 10px;
    }}
}}
@media (max-width: 560px) {{
    .hebtu-hero {{
        min-height: 96vh;
        background-position: center;
    }}
    .hebtu-topbar {{
        font-size: 0.76rem;
        padding-top: 16px;
    }}
    .hebtu-menu {{
        display: flex;
        flex-direction: column;
        gap: 10px;
        font-size: 0.95rem;
    }}
    .hebtu-menu-right {{
        display: none;
    }}
    .hebtu-dropdown {{
        display: grid;
        justify-items: center;
        gap: 8px;
    }}
    .hebtu-dropdown::before {{
        display: none;
    }}
    .hebtu-dropdown-menu {{
        position: static;
        min-width: min(260px, 86vw);
        opacity: 1;
        visibility: visible;
        pointer-events: auto;
        transform: none;
        background: rgba(255,255,255,0.16);
        border-color: rgba(255,255,255,0.26);
        box-shadow: none;
    }}
    .hebtu-dropdown:hover .hebtu-dropdown-menu,
    .hebtu-dropdown:focus-within .hebtu-dropdown-menu {{
        transform: none;
    }}
    .hebtu-dropdown-menu a {{
        justify-content: center;
        color: rgba(255,255,255,0.96) !important;
    }}
    .hebtu-dropdown-menu a:hover {{
        color: #fff !important;
        background: rgba(255,255,255,0.15);
    }}
    .hebtu-brand img {{
        width: 184px;
    }}
    .hebtu-center {{
        min-height: 48vh;
        padding-top: 40px;
    }}
    .hebtu-center h1 {{
        font-size: clamp(2.9rem, 16vw, 4.6rem) !important;
    }}
    .hebtu-body-inner {{
        width: min(100% - 28px, 1180px);
        padding-top: 38px;
    }}
    .hebtu-recent-item {{
        display: block;
    }}
    .hebtu-recent-item small {{
        display: block;
        margin-top: 6px;
        white-space: normal;
    }}
}}
@keyframes hebtuHeroDrift {{
    0% {{ transform: scale(1.04) translate3d(-0.7%, -0.6%, 0); }}
    100% {{ transform: scale(1.10) translate3d(0.8%, 0.6%, 0); }}
}}
@keyframes hebtuDropIn {{
    from {{ opacity: 0; transform: translateY(-16px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes hebtuFadeUp {{
    from {{ opacity: 0; transform: translateY(24px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes hebtuFloat {{
    0%, 100% {{ transform: translateX(-50%) translateY(0); }}
    50% {{ transform: translateX(-50%) translateY(10px); }}
}}
@keyframes hebtuLogoPulse {{
    0%, 100% {{ filter: brightness(0) invert(1) drop-shadow(0 5px 18px rgba(0,0,0,0.42)); }}
    50% {{ filter: brightness(0) invert(1) drop-shadow(0 8px 26px rgba(255,255,255,0.22)); }}
}}
@keyframes hebtuBarGrow {{
    from {{ transform: scaleX(0); }}
    to {{ transform: scaleX(1); }}
}}
@keyframes hebtuRevealUp {{
    from {{ opacity: 0; transform: translateY(42px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes hebtuScrollReveal {{
    from {{ opacity: 0; transform: translateY(52px); filter: blur(6px); }}
    to {{ opacity: 1; transform: translateY(0); filter: blur(0); }}
}}
@keyframes hebtuRiseFromBottom {{
    from {{
        opacity: 0;
        transform: translateY(96px) scale(0.985);
        filter: blur(10px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }}
}}
@supports (animation-timeline: view()) {{
    .hebtu-section-head,
    .hebtu-actions,
    .hebtu-dynamic,
    .hebtu-stats,
    .hebtu-recent {{
        opacity: 0;
        transform: translateY(52px);
        animation-name: hebtuScrollReveal;
        animation-duration: auto;
        animation-fill-mode: both;
        animation-timing-function: cubic-bezier(.2,.72,.2,1);
        animation-timeline: view();
        animation-range: entry 8% cover 34%;
    }}
    .hebtu-actions {{
        animation-range: entry 12% cover 38%;
    }}
    .hebtu-dynamic {{
        animation-range: entry 14% cover 40%;
    }}
    .hebtu-stats {{
        animation-range: entry 16% cover 42%;
    }}
    .hebtu-recent {{
        animation-range: entry 18% cover 44%;
    }}
    .hebtu-card,
    .hebtu-panel,
    .hebtu-chip,
    .hebtu-stat,
    .hebtu-recent-item {{
        opacity: 0;
        transform: translateY(96px) scale(0.985);
        filter: blur(10px);
        animation-name: hebtuRiseFromBottom;
        animation-duration: auto;
        animation-fill-mode: both;
        animation-timing-function: cubic-bezier(.16,.84,.22,1);
        animation-timeline: view();
        animation-range: entry 0% cover 30%;
    }}
    .hebtu-card:nth-child(2),
    .hebtu-chip:nth-child(2),
    .hebtu-stat:nth-child(2),
    .hebtu-recent-item:nth-child(2) {{
        animation-range: entry 4% cover 34%;
    }}
    .hebtu-card:nth-child(3),
    .hebtu-chip:nth-child(3),
    .hebtu-stat:nth-child(3),
    .hebtu-recent-item:nth-child(3) {{
        animation-range: entry 8% cover 38%;
    }}
    .hebtu-stat:nth-child(4) {{
        animation-range: entry 12% cover 42%;
    }}
    .hebtu-stat:nth-child(5) {{
        animation-range: entry 16% cover 46%;
    }}
}}
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation: none !important;
        transition: none !important;
        opacity: 1 !important;
        transform: none !important;
        filter: none !important;
    }}
}}
</style>
<main class="hebtu-home">
    <section class="hebtu-hero">
        <div class="hebtu-topbar" aria-label="系统快捷入口">
            <a href="/?view=home" target="_self">首页</a>
            <a href="/?view=chat" target="_self">高校对话系统</a>
            <a href="/?view=knowledge" target="_self">知识库</a>
            <a href="#hebtu-system">系统概览</a>
            <a href="#hebtu-recent">最近对话</a>
        </div>
        <div class="hebtu-mainnav" aria-label="主导航">
            <div class="hebtu-menu">
                <a href="#hebtu-system">关于系统</a>
                <a href="/?view=chat" target="_self">课程咨询</a>
                <div class="hebtu-dropdown">
                    <a href="#software-overview">软件学院专栏</a>
                    <div class="hebtu-dropdown-menu" aria-label="软件学院专栏栏目">
                        <a href="#software-overview">学院学习概览</a>
                        <a href="#software-code">代码辅助学习</a>
                        <a href="#software-resources">课程相关资源</a>
                    </div>
                </div>
                <a href="/?view=chat" target="_self">教务问答</a>
            </div>
            <a class="hebtu-brand" href="/?view=home" target="_self" aria-label="河北师范大学教务智能体">
                <img src="{HEBTU_LOGO_URL}" alt="河北师范大学 logo">
                <span>Hebei Normal University</span>
            </a>
            <div class="hebtu-menu hebtu-menu-right">
                <a href="/?view=chat" target="_self">智能问答</a>
                <a href="/?view=knowledge" target="_self">知识库</a>
                <a href="#hebtu-data">数据概览</a>
                <a href="#hebtu-recent">最近对话</a>
            </div>
        </div>
        <div class="hebtu-center">
            <div>
                <h1>高校教务<br>对话系统</h1>
                <p>Education with Heart &amp; Soul</p>
            </div>
        </div>
        <a class="hebtu-scroll" href="#hebtu-system">
            <span>探索</span>
            <i class="hebtu-arrow"></i>
        </a>
    </section>
    <section id="hebtu-system" class="hebtu-body">
        <div class="hebtu-body-inner">
            <div class="hebtu-section-head">
                <h2>高校教务教学智能体</h2>
                <p>保留原有系统能力：教务问答、培养方案查询、课程资料检索、知识库溯源，并把软件学院学习场景放到首页入口。</p>
            </div>
            <div class="hebtu-actions">
                <article class="hebtu-card hebtu-card-primary">
                    <strong>高校对话系统</strong>
                    <p>进入原有智能问答工作台，继续使用课程、学分、培养方案和教务流程咨询能力。</p>
                    <a href="/?view=chat" target="_self">进入智能问答</a>
                </article>
                <article class="hebtu-card">
                    <strong>知识库资料</strong>
                    <p>查看当前已入库的课程大纲、培养方案、官网页面和公开附件。</p>
                    <a href="/?view=knowledge" target="_self">查看知识库 →</a>
                </article>
                <article class="hebtu-card">
                    <strong>系统概览</strong>
                    <p>首屏采用河北师范大学校徽与校园风光图，视觉参考给定页面，但入口只保留本系统真实功能。</p>
                    <a href="#hebtu-data">查看数据概览 →</a>
                </article>
            </div>
            <div class="hebtu-dynamic">
                <div class="hebtu-panel">
                    <details open>
                        <summary>课程与学分</summary>
                        <p>机器学习、科学计算、经典模型等课程可在智能问答中查询学分、周次、方向归属和课程依据。</p>
                    </details>
                    <details>
                        <summary>软件学院专栏</summary>
                        <p>聚合软件工程学习路径、代码辅助学习和课程相关资源，保留培养方案与课程矩阵的查询能力。</p>
                    </details>
                    <details>
                        <summary>资料溯源</summary>
                        <p>回答会关联本地文档、官网页面和公开附件，便于回到知识库核对原始依据。</p>
                    </details>
                </div>
                <div class="hebtu-quick">
                    <a class="hebtu-chip" href="/?view=chat" target="_self">查询课程学分</a>
                    <a class="hebtu-chip" href="#software-overview">进入软件学院专栏</a>
                    <a class="hebtu-chip" href="/?view=knowledge" target="_self">核对知识来源</a>
                </div>
            </div>
            <div class="hebtu-software" aria-label="软件学院专栏">
                <div class="hebtu-section-head">
                    <h2>软件学院专栏</h2>
                    <p>围绕软件工程课程、实践能力和代码学习，把学院资料、智能问答和知识库入口收束到同一处。</p>
                </div>
                <div class="hebtu-software-grid">
                    <article id="software-overview" class="hebtu-card hebtu-card-primary">
                        <strong>学院学习概览</strong>
                        <p>以程序设计、数据结构、机器学习、软件工程实践为主线，串联专业课程、项目训练和毕业要求。</p>
                        <div class="hebtu-tag-row">
                            <span class="hebtu-tag">软件工程</span>
                            <span class="hebtu-tag">AI 方向</span>
                            <span class="hebtu-tag">项目实践</span>
                        </div>
                        <a href="/?view=chat" target="_self">咨询学习路径</a>
                    </article>
                    <article id="software-code" class="hebtu-card">
                        <strong>代码辅助学习</strong>
                        <p>第一版采用静态代码阅读方式，支持解释代码、定位错误、优化思路和生成练习，不在系统内运行用户代码。</p>
                        <div class="hebtu-tag-row">
                            <span class="hebtu-tag">解释代码</span>
                            <span class="hebtu-tag">定位 Bug</span>
                            <span class="hebtu-tag">练习生成</span>
                        </div>
                        <a href="/?view=chat" target="_self">进入代码问答</a>
                    </article>
                    <article id="software-resources" class="hebtu-card">
                        <strong>课程相关资源</strong>
                        <p>查看课程大纲、培养方案、软件学院官网页面和公开附件，回答中的资料依据也可回到知识库核对。</p>
                        <div class="hebtu-tag-row">
                            <span class="hebtu-tag">课程大纲</span>
                            <span class="hebtu-tag">培养方案</span>
                            <span class="hebtu-tag">学院官网</span>
                        </div>
                        <a href="/?view=knowledge" target="_self">查看课程资料</a>
                    </article>
                </div>
            </div>
            <div id="hebtu-data" class="hebtu-stats">
{stats_markup}
            </div>
            <div id="hebtu-recent" class="hebtu-recent">
                <div class="hebtu-recent-title">最近对话</div>
                {recent_markup}
            </div>
        </div>
    </section>
</main>
"""
    st.html(textwrap.dedent(home_html).strip())


def main() -> None:
    st.set_page_config(
        page_title="河北师范大学教务智能体",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    view = current_view()
    if view == "chat":
        render_chat_view()
    elif view == "knowledge":
        render_knowledge_view()
    else:
        render_home()


if __name__ == "__main__":
    main()
