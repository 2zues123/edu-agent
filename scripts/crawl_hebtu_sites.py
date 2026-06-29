#!/usr/bin/env python3
"""Crawl public Hebei Normal University pages into the local knowledge base."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import shutil
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib import robotparser
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


CORE_SEED_URLS = [
    "https://www.hebtu.edu.cn/",
    "https://news.hebtu.edu.cn/",
    "https://software.hebtu.edu.cn/",
    "https://software.hebtu.edu.cn/a/xygk/xyjj/index.html",
    "https://software.hebtu.edu.cn/a/xygk/xyry/index.html",
    "https://software.hebtu.edu.cn/a/xygk/xyld/index.html",
    "https://software.hebtu.edu.cn/a/xygk/xybs/index.html",
    "https://software.hebtu.edu.cn/a/xygk/cydh/index.html",
    "https://software.hebtu.edu.cn/a/lxwm/index.html",
    "https://jwc.hebtu.edu.cn/",
]

DISCOVERY_SEED_URLS = [
    "https://software.hebtu.edu.cn/a/tzgg/index.html",
    "https://software.hebtu.edu.cn/a/jyjx/zypy/index.html",
    "https://software.hebtu.edu.cn/a/2025/05/30/E6381C289BF948A4A53049CC6AF4687D.html",
    "https://jwc.hebtu.edu.cn/a/2026/04/09/E55718F3AAD24D219FB44A3B64892DB7.html",
    "https://jwc.hebtu.edu.cn/a/2026/03/05/C2E58230C5944480912C3E62C0E52B8E.html",
    # Additional detail pages
    "https://jwc.hebtu.edu.cn/a/xlxx/index.html",     # 校历 / academic calendar
    "https://jwc.hebtu.edu.cn/a/xkxx/index.html",     # 选课信息 / course selection
    "https://jwc.hebtu.edu.cn/a/2026/06/01/326BAD4DC64948B0A64BC2B65E86223C.html",
]
SEED_URLS = CORE_SEED_URLS + DISCOVERY_SEED_URLS
ALLOWED_NETLOCS = {
    "www.hebtu.edu.cn",
    "news.hebtu.edu.cn",
    "software.hebtu.edu.cn",
    "jwc.hebtu.edu.cn",
}
EXCLUDED_NETLOCS = {
    "jwgl.hebtu.edu.cn",
    "hebtux.fanya.chaoxing.com",
    "hbsdkcsz.mh.chaoxing.com",
    "www.zhihuishu.com",
    "www.chsi.com.cn",
    "zsjyc.hebtu.edu.cn",
}
ATTACHMENT_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}
SKIP_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".mp4",
    ".mp3",
    ".zip",
    ".rar",
    ".7z",
}
DEFAULT_USER_AGENT = "edu-agent-hebtu-crawler/1.0 (+local academic knowledge indexing)"


@dataclass
class CrawledPage:
    url: str
    title: str
    site: str
    path: str
    content_hash: str
    text_chars: int
    published_at: str = ""


@dataclass
class DownloadedAttachment:
    url: str
    site: str
    path: str
    content_hash: str
    bytes: int
    title: str = ""


def sha1_text(value: str, length: int = 16) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def sha1_bytes(value: bytes, length: int = 16) -> str:
    return hashlib.sha1(value).hexdigest()[:length]


def safe_site_name(netloc: str) -> str:
    return netloc.replace(".", "_")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "spm", "from"))
        and key.lower() not in {"page", "pageno", "curpage", "p", "pn", "pageid", "pageindex"}
    ]
    query = urlencode(sorted(query_items), doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def suffix_for_url(url: str) -> str:
    path = urlparse(url).path.lower()
    return Path(path).suffix


def is_allowed_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() in EXCLUDED_NETLOCS:
        return False
    return parsed.netloc.lower() in ALLOWED_NETLOCS


def looks_like_attachment(url: str) -> bool:
    if suffix_for_url(url) in ATTACHMENT_SUFFIXES:
        return True
    # AndaCMS download portal URLs (jwc attachments use /dynamic/download.jsp?id=...)
    if "/dynamic/download.jsp" in url and "id=" in url:
        return True
    return False


def should_skip_url(url: str) -> bool:
    suffix = suffix_for_url(url)
    if suffix in ATTACHMENT_SUFFIXES:
        return False
    return suffix in SKIP_SUFFIXES


def ensure_output_dirs(raw_web_dir: Path, attachment_dir: Path, processed_dir: Path) -> None:
    raw_web_dir.mkdir(parents=True, exist_ok=True)
    attachment_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)


def clean_output_dirs(raw_web_dir: Path, attachment_dir: Path) -> None:
    for path in [raw_web_dir, attachment_dir]:
        if path.exists():
            shutil.rmtree(path)


def build_session(user_agent: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return session


def load_robot_parsers(session: requests.Session, timeout: int, user_agent: str) -> dict[str, robotparser.RobotFileParser]:
    parsers: dict[str, robotparser.RobotFileParser] = {}
    for netloc in ALLOWED_NETLOCS:
        robots_url = f"https://{netloc}/robots.txt"
        parser = robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = session.get(robots_url, timeout=timeout)
            if response.ok:
                parser.parse(response.text.splitlines())
            else:
                parser.parse([])
        except requests.RequestException:
            parser.parse([])
        parsers[netloc] = parser
        time.sleep(0.2)
    return parsers


def can_fetch(
    url: str,
    parsers: dict[str, robotparser.RobotFileParser],
    user_agent: str,
    ignore_robots: bool,
) -> bool:
    if ignore_robots:
        return True
    parser = parsers.get(urlparse(url).netloc.lower())
    return True if parser is None else parser.can_fetch(user_agent, url)


def fetch_with_retries(
    session: requests.Session,
    url: str,
    *,
    timeout: int,
    retries: int,
) -> requests.Response:
    last_error: requests.RequestException | None = None
    for attempt in range(retries + 1):
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1 + attempt)
    assert last_error is not None
    raise last_error


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_published_at(soup: BeautifulSoup, text: str) -> str:
    for selector in ["meta[name='pubdate']", "meta[name='publishdate']", "meta[property='article:published_time']"]:
        tag = soup.select_one(selector)
        if tag and tag.get("content"):
            return str(tag["content"])[:19]
    match = re.search(r"(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return ""


def html_to_markdown_text(soup_element) -> str:
    """Convert BS4 element to plain text, preserving structure from tables/lists."""
    for table in soup_element.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            table.replace_with("\n" + "\n".join(rows) + "\n")

    for li in soup_element.find_all("li"):
        text = li.get_text(" ", strip=True)
        if text:
            li.replace_with(f"- {text}\n")

    for dl in soup_element.find_all("dl"):
        lines = []
        for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
            key = dt.get_text(" ", strip=True)
            val = dd.get_text(" ", strip=True)
            if key and val:
                lines.append(f"**{key}**: {val}")
        if lines:
            dl.replace_with("\n".join(lines) + "\n")

    text = soup_element.get_text("\n", strip=True)
    return clean_text(text)


def extract_page(response: requests.Response, url: str) -> tuple[str, str, str, list[str], list[tuple[str, str]]]:
    if not response.encoding or response.encoding.lower() in {"iso-8859-1", "latin-1"}:
        response.encoding = response.apparent_encoding or "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    for selector in ["script", "style", "noscript", "iframe", "video", "audio"]:
        for tag in soup.select(selector):
            tag.decompose()

    title_tag = soup.find("title")
    h1_tag = soup.find("h1")
    title = clean_text(h1_tag.get_text(" ", strip=True) if h1_tag else "")
    if not title and title_tag:
        title = clean_text(title_tag.get_text(" ", strip=True))
    if not title:
        title = urlparse(url).path.strip("/") or urlparse(url).netloc

    main = soup.find("article") or soup.find("main")
    if main is None:
        candidates = soup.select(
            ".con_con, .TRS_Editor, .article_content, .news_content, "
            ".Custom_UnionStyle, .text_content, .nr-content, .wp_articlecontent, "
            ".content, .article, .news, .main, .con, .detail, #content, #main"
        )
        main = max(candidates, key=lambda item: len(item.get_text(" ", strip=True)), default=soup.body or soup)
    text = html_to_markdown_text(main)
    published_at = extract_published_at(soup, text)

    # Discover attachment links within the main content area
    discovered_attachments: list[tuple[str, str]] = []
    if main is not None:
        for anchor in main.find_all("a", href=True):
            href = str(anchor["href"]).strip()
            joined = normalize_url(urljoin(url, href))
            if looks_like_attachment(joined):
                link_text = clean_text(anchor.get_text(" ", strip=True))
                discovered_attachments.append((joined, link_text))

    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        joined = normalize_url(urljoin(url, str(anchor["href"]).strip()))
        if is_allowed_url(joined) and not should_skip_url(joined):
            links.append(joined)
    return title, text, published_at, links, discovered_attachments


def markdown_document(title: str, text: str, *, url: str, site: str, published_at: str) -> str:
    metadata = {
        "title": title.replace("\n", " "),
        "category": "web",
        "source_url": url,
        "site": site,
        "published_at": published_at,
    }
    front_matter = "\n".join(f"{key}: {value}" for key, value in metadata.items())
    return f"---\n{front_matter}\n---\n\n# {title}\n\n{text}\n"


def write_text_document(
    raw_web_dir: Path,
    *,
    site: str,
    url: str,
    title: str,
    text: str,
    published_at: str,
) -> CrawledPage:
    content_hash = sha1_text(text)
    site_dir = raw_web_dir / safe_site_name(site)
    site_dir.mkdir(parents=True, exist_ok=True)
    path = site_dir / f"{content_hash}.md"
    path.write_text(
        markdown_document(title, text, url=url, site=site, published_at=published_at),
        encoding="utf-8",
    )
    return CrawledPage(
        url=url,
        title=title,
        site=site,
        path=str(path),
        content_hash=content_hash,
        text_chars=len(text),
        published_at=published_at,
    )


def write_attachment(
    attachment_dir: Path,
    *,
    response: requests.Response,
    url: str,
    title: str,
) -> DownloadedAttachment:
    site = urlparse(url).netloc.lower()
    content = response.content
    content_hash = sha1_bytes(content)
    suffix = suffix_for_url(url)
    if not suffix:
        guessed = mimetypes.guess_extension(response.headers.get("Content-Type", "").split(";")[0].strip())
        suffix = guessed or ".bin"
    site_dir = attachment_dir / safe_site_name(site)
    site_dir.mkdir(parents=True, exist_ok=True)
    path = site_dir / f"{content_hash}{suffix}"
    path.write_bytes(content)
    metadata = {
        "title": title or Path(urlparse(url).path).stem or content_hash,
        "category": "web",
        "source_url": url,
        "site": site,
        "published_at": "",
    }
    path.with_suffix(path.suffix + ".meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return DownloadedAttachment(
        url=url,
        site=site,
        path=str(path),
        content_hash=content_hash,
        bytes=len(content),
        title=metadata["title"],
    )


def site_counts_within_budget(site_counts: dict[str, int], url: str, max_pages_per_site: int) -> bool:
    if max_pages_per_site <= 0:
        return True
    site = urlparse(url).netloc.lower()
    return site_counts[site] < max_pages_per_site


def enqueue_links(queue: deque[str], seen: set[str], links: Iterable[str]) -> None:
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        queue.append(link)


def seed_counts_by_site(urls: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for url in urls:
        counts[urlparse(url).netloc.lower()] += 1
    return dict(counts)


def validate_clean_run(args: argparse.Namespace) -> None:
    if not args.clean_output or args.allow_incomplete_seed_coverage or args.max_pages_per_site <= 0:
        return

    too_low = {
        site: count
        for site, count in seed_counts_by_site(CORE_SEED_URLS).items()
        if args.max_pages_per_site < count
    }
    if not too_low:
        return

    details = ", ".join(f"{site} needs at least {count}" for site, count in sorted(too_low.items()))
    raise RuntimeError(
        "Refusing to clean and rebuild with an incomplete page budget. "
        f"Core seed coverage would be lost: {details}. "
        "Increase --max-pages-per-site, use --max-pages-per-site 0 for no per-site limit, "
        "or pass --allow-incomplete-seed-coverage for a disposable test run."
    )


def _url_priority(url: str) -> bool:
    """Return True if the URL looks like a detail/article page (crawl first)."""
    path = urlparse(url).path.lower()
    if re.search(r"/a/\d{4}/\d{2}/\d{2}/[a-f0-9]+\.html$", path):
        return True
    if "/dynamic/content.jsp" in path:
        return True
    return False


def crawl(args: argparse.Namespace) -> int:
    if args.dry_run:
        print("Seeds:")
        for seed in SEED_URLS:
            print(f"- {seed}")
        print(f"Allowed domains: {', '.join(sorted(ALLOWED_NETLOCS))}")
        print(f"Excluded domains: {', '.join(sorted(EXCLUDED_NETLOCS))}")
        page_limit = "unlimited" if args.max_pages_per_site <= 0 else str(args.max_pages_per_site)
        total_limit = "unlimited" if args.max_total_pages <= 0 else str(args.max_total_pages)
        print(f"Max pages per site: {page_limit}")
        print(f"Max total pages: {total_limit}")
        print(f"Core seed counts: {seed_counts_by_site(CORE_SEED_URLS)}")
        print(f"Attachments: {', '.join(sorted(ATTACHMENT_SUFFIXES))}")
        return 0

    validate_clean_run(args)

    if args.clean_output:
        clean_output_dirs(args.raw_web_dir, args.attachment_dir)
    ensure_output_dirs(args.raw_web_dir, args.attachment_dir, args.processed_dir)
    session = build_session(args.user_agent)
    robots = load_robot_parsers(session, args.timeout, args.user_agent)

    # Priority queues: high = detail pages first, low = listing/nav pages
    queue_high: deque[str] = deque()
    queue_low: deque[str] = deque()
    for url in SEED_URLS:
        normalized = normalize_url(url)
        if _url_priority(normalized):
            queue_high.append(normalized)
        else:
            queue_low.append(normalized)
    seen: set[str] = set(queue_high) | set(queue_low)
    content_hashes: set[str] = set()
    site_counts: dict[str, int] = defaultdict(int)
    pages: list[CrawledPage] = []
    attachments: list[DownloadedAttachment] = []
    skipped: list[dict] = []
    failed: list[dict] = []

    def _pop_url() -> str | None:
        """Pop from high-priority queue first, then low."""
        if queue_high:
            return queue_high.popleft()
        if queue_low:
            return queue_low.popleft()
        return None

    def _enqueue_links(links: Iterable[str]) -> None:
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            if _url_priority(link):
                queue_high.append(link)
            else:
                queue_low.append(link)

    while True:
        url = _pop_url()
        if url is None:
            break

        # Global budget check
        if args.max_total_pages > 0 and len(pages) >= args.max_total_pages:
            skipped.append({"url": url, "reason": "global page budget reached"})
            continue

        site = urlparse(url).netloc.lower()
        if not site_counts_within_budget(site_counts, url, args.max_pages_per_site):
            skipped.append({"url": url, "reason": "site page budget reached"})
            continue
        if not can_fetch(url, robots, args.user_agent, args.ignore_robots):
            skipped.append({"url": url, "reason": "robots.txt disallow"})
            continue

        try:
            response = fetch_with_retries(session, url, timeout=args.timeout, retries=args.retries)
            final_url = normalize_url(response.url)
            if not is_allowed_url(final_url):
                skipped.append({"url": url, "reason": f"redirected outside scope: {final_url}"})
                continue
            content_type = response.headers.get("Content-Type", "").lower()
            if looks_like_attachment(final_url):
                if args.download_attachments:
                    attachments.append(write_attachment(args.attachment_dir, response=response, url=final_url, title=""))
                continue
            if "html" not in content_type and "xml" not in content_type and not response.text.strip().startswith("<"):
                skipped.append({"url": final_url, "reason": f"unsupported content type: {content_type}"})
                continue

            title, text, published_at, links, discovered_attachments = extract_page(response, final_url)

            # Download any discovered attachments (jwc notices embed content in files)
            for att_url, att_title in discovered_attachments:
                if args.download_attachments:
                    try:
                        att_response = fetch_with_retries(session, att_url, timeout=args.timeout, retries=1)
                        attachments.append(write_attachment(
                            args.attachment_dir, response=att_response, url=att_url, title=att_title))
                        time.sleep(args.delay * 0.5)
                    except Exception:
                        pass

            if len(text) < args.min_text_chars:
                skipped.append({"url": final_url, "reason": f"text too short: {len(text)}"})
                _enqueue_links(links)
                continue

            content_hash = sha1_text(text)
            if content_hash not in content_hashes:
                content_hashes.add(content_hash)
                pages.append(
                    write_text_document(
                        args.raw_web_dir,
                        site=site,
                        url=final_url,
                        title=title,
                        text=text,
                        published_at=published_at,
                    )
                )
                site_counts[site] += 1
            _enqueue_links(links)
            time.sleep(args.delay)
        except Exception as exc:
            failed.append({"url": url, "error": str(exc)})

    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "pages": [asdict(page) for page in pages],
        "attachments": [asdict(attachment) for attachment in attachments],
    }
    report = {
        "built_at": manifest["built_at"],
        "seed_urls": SEED_URLS,
        "core_seed_urls": CORE_SEED_URLS,
        "allowed_netlocs": sorted(ALLOWED_NETLOCS),
        "excluded_netlocs": sorted(EXCLUDED_NETLOCS),
        "max_pages_per_site": args.max_pages_per_site,
        "page_count": len(pages),
        "attachment_count": len(attachments),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "site_counts": dict(site_counts),
        "skipped": skipped[:500],
        "failed": failed,
    }
    args.manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    args.report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Pages: {len(pages)}")
    print(f"Attachments: {len(attachments)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failed: {len(failed)}")
    print(f"Manifest: {args.manifest_file}")
    print(f"Report: {args.report_file}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-web-dir", type=Path, default=Path("data/raw/web"))
    parser.add_argument("--attachment-dir", type=Path, default=Path("data/raw/web_attachments"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--manifest-file", type=Path, default=Path("data/processed/web_crawl_manifest.json"))
    parser.add_argument("--report-file", type=Path, default=Path("data/processed/web_crawl_report.json"))
    parser.add_argument(
        "--max-pages-per-site",
        type=int,
        default=150,
        help="Maximum saved HTML pages per allowed site. Use 0 for no per-site limit.",
    )
    parser.add_argument(
        "--max-total-pages",
        type=int,
        default=600,
        help="Maximum total saved pages across all sites. Use 0 for no limit.",
    )
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--min-text-chars", type=int, default=80)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean-output", action="store_true")
    parser.add_argument(
        "--allow-incomplete-seed-coverage",
        action="store_true",
        help="Allow --clean-output with a page budget smaller than the core seed pages. Use only for disposable tests.",
    )
    parser.add_argument("--ignore-robots", action="store_true")
    parser.add_argument("--no-download-attachments", dest="download_attachments", action="store_false")
    parser.set_defaults(download_attachments=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(crawl(parse_args()))
