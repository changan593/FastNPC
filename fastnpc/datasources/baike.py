# -*- coding: utf-8 -*-
from __future__ import annotations

import requests
from bs4 import BeautifulSoup
import re
import time
import random
import os
from typing import Optional, Dict, Any, List, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
try:
    from playwright.sync_api import sync_playwright  # 可选：用于动态点击展开同名面板
    _HAS_PLAYWRIGHT = True
except Exception:
    _HAS_PLAYWRIGHT = False
from fastnpc.config import CHAR_DIR
from urllib.parse import urlparse, parse_qs, unquote, urlunparse

# 将 Baike 全文抓取路径收敛为“modern_jlemma”单一路径
_FULL_ONLY_MODERN = True


def _debug_enabled() -> bool:
    return os.environ.get('FASTNPC_DEBUG', '').strip() not in ('', '0', 'false', 'False')


def _debug_dump(role: str, stage: str, content: bytes) -> None:
    if not _debug_enabled():
        return
    try:
        dbg_dir = os.path.join(CHAR_DIR.as_posix(), "debug")
        os.makedirs(dbg_dir, exist_ok=True)
        path = os.path.join(dbg_dir, f"baike_{role}_{stage}.html")
        with open(path, 'wb') as f:
            f.write(content)
    except Exception:
        pass


def _filter_noise(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    noise_patterns = [
        r"使用百度前必读", r"百科协议", r"隐私政策", r"京ICP", r"京公网",
        r"百度百科合作平台", r"广告服务", r"举报", r"登录", r"注册",
    ]
    for pat in noise_patterns:
        if re.search(pat, t):
            return False
    return True


def _fetch_baike_card_summary(keyword: str, session: Optional[requests.Session] = None) -> Optional[str]:
    try:
        s = session or requests.Session()
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/javascript,*/*;q=0.1',
            'Referer': 'https://baike.baidu.com/',
        })
        api_url = (
            'https://baike.baidu.com/api/openapi/BaikeLemmaCardApi?'
            f'scope=103&format=json&appid=379020&bk_key={requests.utils.quote(keyword)}&bk_length=600'
        )
        resp = s.get(api_url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        for key in ['abstract', 'desc']:
            if isinstance(data, dict) and data.get(key):
                text = str(data[key])
                text = re.sub(r'\[\d+(-\d+)?\]', '', text)
                return text.strip()
        return None
    except Exception:
        return None


# ===================== 同名候选提取（步骤一） =====================

def _make_absolute_baike_url(href: str) -> str:
    """将百科相对链接转换为可请求的绝对链接。"""
    if not href:
        return ''
    if href.startswith('//'):
        return 'https:' + href
    if href.startswith('/'):
        return 'https://baike.baidu.com' + href
    if href.startswith('http'):
        return href
    return 'https://baike.baidu.com' + ('' if href.startswith('/') else '/') + href


def _normalize_text_for_match(text: str) -> str:
    t = re.sub(r'[\s\u3000\-·:：、/\\，。；;,.（）()【】\[\]]+', '', text or '')
    return t.lower()


def _normalize_item_url(raw_url: str) -> str:
    """标准化百科 item 链接：转绝对、移除锚点与无关查询参数（fr/fromModule等）。"""
    if not raw_url:
        return ''
    abs_url = _make_absolute_baike_url(raw_url)
    try:
        parsed = urlparse(abs_url)
        if 'baike.baidu.com' not in (parsed.netloc or '') or '/item/' not in (parsed.path or ''):
            return ''
        # 去掉 fragment，并清理 fr / fromModule 等噪声参数
        query_dict = parse_qs(parsed.query or '')
        for k in list(query_dict.keys()):
            if k.lower() in {'fr', 'frommodule'}:
                query_dict.pop(k, None)
        cleaned = parsed._replace(query='', fragment='')
        return urlunparse(cleaned)
    except Exception:
        return abs_url


def _should_drop_option_text(text: str) -> bool:
    t = (text or '').strip()
    if not t:
        return True
    if t in {'百度百科', '更多', '更多 >'}:
        return True
    core = re.sub(r'[\s·\-:：、/\\，。；;,.（）()【】\[\]<>“”"\']+', '', t)
    return len(core) < 2


def _has_polysemant_hint(soup: BeautifulSoup) -> bool:
    """页面文本中是否出现“多义词/同名词条”的提示。"""
    try:
        hint = soup.find(string=lambda t: isinstance(t, str) and ('多义词' in t or '同名词条' in t))
        return bool(hint)
    except Exception:
        return False


def _extract_polysemant_options(soup: BeautifulSoup, keyword: str) -> List[Dict[str, str]]:
    """
    在百科页面中提取同名（多义）候选项。
    返回 [{'text': 标题, 'href': 绝对链接}]，保持页面顺序并去重。
    """
    options: List[Dict[str, str]] = []
    seen = set()

    def _push(text: str, url: str) -> None:
        if _should_drop_option_text(text):
            return
        norm_url = _normalize_item_url(url)
        if not norm_url:
            return
        key = (text, norm_url)
        if key in seen:
            return
        seen.add(key)
        options.append({'text': text, 'href': norm_url})

    def _accept(url: str) -> bool:
        try:
            parsed = urlparse(url)
            q = parse_qs(parsed.query)
            if 'fromModule' in q and any('inlink' in v for vs in q.values() for v in vs):
                return False
        except Exception:
            pass
        return True

    def _match_kw(text: str, url: str) -> bool:
        try:
            decoded_path = unquote(url)
        except Exception:
            decoded_path = url
        norm_kw = _normalize_text_for_match(keyword)
        return (norm_kw in _normalize_text_for_match(text)) or (norm_kw in _normalize_text_for_match(decoded_path))

    # 1) 明确的多义容器内提取（新旧结构）
    poly_containers = [
        *soup.select('div[class^="newPolysemantList_"]'),
        *soup.select('div.polysemantList'),
        *soup.select('div.polysemantList-wrapper'),
        *soup.select('div.lemmaWgt-polysemant'),
        *soup.select('ul.polysemantList-wrapper'),
    ]
    for container in poly_containers:
        anchors = container.select('a[class^="contentItemChild_"]') or container.find_all('a', href=lambda h: h and '/item/' in h)
        for a in anchors:
            href = a.get('href') or ''
            text = a.get_text(' ', strip=True)
            if not href or not text:
                continue
            url = _make_absolute_baike_url(href)
            if not _accept(url):
                continue
            # 在明确容器内可放宽匹配
            if not _match_kw(text, url):
                pass
            _push(text, url)
        if options:
            break

    # 2) 全页稳定类名/结构
    if not options:
        selectors = [
            'a[class^="contentItemChild_"]',
            'div[class^="contentItemChildren_"] a',
            'ul.polysemantList-wrapper li a',
            'div.polysemantList a',
            'div.polysemantList-wrapper a',
            'div.lemmaWgt-polysemant a',
            'ul[class*="polysemantList"] li a',
        ]
        for sel in selectors:
            for a in soup.select(sel):
                href = a.get('href') or ''
                text = a.get_text(' ', strip=True)
                if not href or not text:
                    continue
                url = _make_absolute_baike_url(href)
                if not _accept(url):
                    continue
                # 全页抓取保持严格
                if not _match_kw(text, url):
                    continue
                _push(text, url)
            if options:
                break

    # 3) 提示文本附近的局部范围
    if not options:
        tip_node = soup.find(string=lambda t: isinstance(t, str) and ('多义词' in t or '同名词条' in t))
        tip_container = tip_node.parent if hasattr(tip_node, 'parent') else None
        candidates = []
        if tip_container:
            candidates.append(tip_container)
            if tip_container.parent:
                candidates.append(tip_container.parent)
            if tip_container.parent and tip_container.parent.parent:
                candidates.append(tip_container.parent.parent)
        for node in candidates:
            for a in node.find_all('a'):
                href = a.get('href') or ''
                text = a.get_text(' ', strip=True)
                if not text or '/item/' not in href:
                    continue
                url = _make_absolute_baike_url(href)
                if not _accept(url):
                    continue
                if not _match_kw(text, url):
                    continue
                _push(text, url)
            if options:
                break

    return options


def _extract_keyword_item_links_from_page(soup: BeautifulSoup, keyword: str) -> List[Dict[str, str]]:
    """兜底：全页查找标题或 URL 含关键词的 /item/ 链接（排除 inlink）。"""
    results: List[Dict[str, str]] = []
    seen = set()
    for a in soup.find_all('a', href=lambda h: h and '/item/' in h):
        href = a.get('href') or ''
        text = a.get_text(' ', strip=True)
        if not href or not text:
            continue
        url = _make_absolute_baike_url(href)
        try:
            parsed = urlparse(url)
            q = parse_qs(parsed.query)
            if 'fromModule' in q and any('inlink' in v for vs in q.values() for v in vs):
                continue
        except Exception:
            pass
        try:
            decoded_path = unquote(url)
        except Exception:
            decoded_path = url
        if (_normalize_text_for_match(keyword) not in _normalize_text_for_match(text)) and \
           (_normalize_text_for_match(keyword) not in _normalize_text_for_match(decoded_path)):
            continue
        norm_url = _normalize_item_url(url)
        if _should_drop_option_text(text) or not norm_url:
            continue
        key = (text, norm_url)
        if key in seen:
            continue
        seen.add(key)
        results.append({'text': text, 'href': norm_url})
        if len(results) >= 100:
            break
    return results


def _extract_options_from_search(keyword: str, session: requests.Session, limit: int = 60, relaxed: bool = False) -> List[Dict[str, str]]:
    """回退：进入百科搜索页，抓取与关键字同名/相关的条目列表。"""
    results: List[Dict[str, str]] = []
    try:
        search_url = f"https://baike.baidu.com/search?word={requests.utils.quote(keyword)}"
        resp = session.get(search_url, timeout=10)
        if not (200 <= resp.status_code < 300):
            return results
        s = BeautifulSoup(resp.content, 'html.parser')
        container = s.select_one('div.search-list') or s
        anchors = container.find_all('a', href=lambda h: h and '/item/' in h)
        seen = set()
        for a in anchors:
            text = a.get_text(' ', strip=True)
            href = a.get('href') or ''
            if not text or not href:
                continue
            url = _make_absolute_baike_url(href)
            try:
                parsed = urlparse(url)
                q = parse_qs(parsed.query)
                if 'fromModule' in q and any('inlink' in v for vs in q.values() for v in vs):
                    continue
            except Exception:
                pass
            if not relaxed:
                try:
                    decoded_path = unquote(url)
                except Exception:
                    decoded_path = url
                if (_normalize_text_for_match(keyword) not in _normalize_text_for_match(text)) and \
                   (_normalize_text_for_match(keyword) not in _normalize_text_for_match(decoded_path)):
                    continue
            norm_url = _normalize_item_url(url)
            if _should_drop_option_text(text) or not norm_url:
                continue
            key = (text, norm_url)
            if key in seen:
                continue
            seen.add(key)
            results.append({'text': text, 'href': norm_url})
            if len(results) >= limit:
                break
        return results
    except Exception:
        return results


def _extract_options_from_baidu_web(keyword: str, session: requests.Session, limit: int = 60, *, relaxed: bool = True) -> List[Dict[str, str]]:
    """兜底加强：使用 Baidu Web 搜索(site:baike.baidu.com) 提取 /item/ 链接。

    relaxed=True 时，放宽“标题/URL 必含关键词”的限制，以提升在风控页面或
    结果标题被截断/替换时的召回率。
    """
    results: List[Dict[str, str]] = []
    try:
        q = f"site:baike.baidu.com {keyword}"
        search_url = f"https://www.baidu.com/s?wd={requests.utils.quote(q)}"
        resp = session.get(search_url, timeout=10)
        if not (200 <= resp.status_code < 300):
            return results
        s = BeautifulSoup(resp.content, 'html.parser')
        seen = set()
        for a in s.find_all('a', href=True):
            href = a.get('href') or ''
            text = a.get_text(' ', strip=True)
            if 'baidu.com' not in href:
                continue
            url = href
            try:
                if href.startswith('http') and 'baidu.com' in href:
                    r2 = session.get(href, timeout=6, allow_redirects=True)
                    if 200 <= r2.status_code < 400:
                        url = r2.url
            except Exception:
                pass
            if 'baike.baidu.com' not in url or '/item/' not in url:
                continue
            try:
                parsed = urlparse(url)
                qd = parse_qs(parsed.query)
                if 'fromModule' in qd and any('inlink' in v for vs in qd.values() for v in vs):
                    continue
            except Exception:
                pass
            if not relaxed:
                try:
                    decoded_path = unquote(url)
                except Exception:
                    decoded_path = url
                norm_kw = _normalize_text_for_match(keyword)
                if (norm_kw not in _normalize_text_for_match(text)) and (norm_kw not in _normalize_text_for_match(decoded_path)):
                    continue
            norm_url = _normalize_item_url(url)
            if _should_drop_option_text(text) or not norm_url:
                continue
            key = (text or decoded_path, norm_url)
            if key in seen:
                continue
            seen.add(key)
            results.append({'text': text or decoded_path, 'href': norm_url})
            if len(results) >= limit:
                break
        return results
    except Exception:
        return results


def _extract_options_dynamic_with_playwright(keyword: str, timeout_ms: int = 12000) -> List[Dict[str, str]]:
    """使用无头浏览器点击“同名/多义”面板后抓取候选（与 Test 样例一致的选择器）。"""
    results: List[Dict[str, str]] = []
    if not _HAS_PLAYWRIGHT:
        return results
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
            url = f"https://baike.baidu.com/item/{requests.utils.quote(keyword)}"
            page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            try:
                # 点击“展开同名词”面板
                loc = page.locator('div.J-polysemantText, div[class^="polysemantText_"]')
                if loc.count() > 0:
                    loc.first.click(timeout=2000)
                else:
                    icon = page.locator('#lemmaDesc div.J-polysemantText svg, svg.polysemantIcon_VoaS3')
                    if icon.count() > 0:
                        icon.first.click(timeout=2000)
            except Exception:
                pass
            try:
                # 等待新面板出现（包含你提供的结构）
                page.wait_for_selector('div[class^="newPolysemantList_"], #newPolysemantList, #content', timeout=4000)
            except Exception:
                pass
            page.wait_for_timeout(400)
            # 覆盖更多可能位置的 a 链接
            selector_union = ' , '.join([
                'div[class^=\"newPolysemantList_\"] a[href*=\"/item/\"]',
                '#newPolysemantList a[href*=\"/item/\"]',
                '#content a[href*=\"/item/\"]',
                'div[class^=\"contentItemChildren_\"] a[href*=\"/item/\"]',
                'a[class^=\"contentItemChild_\"]',
            ])
            anchors = page.locator(selector_union)
            count = min(200, anchors.count())
            seen = set()
            for i in range(count):
                try:
                    a = anchors.nth(i)
                    href = a.get_attribute('href') or ''
                    text = (a.inner_text() or '').strip()
                    if not href or not text:
                        continue
                    abs_url = _normalize_item_url(href)
                    if _should_drop_option_text(text) or not abs_url:
                        continue
                    key = (text, abs_url)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({'text': text, 'href': abs_url})
                except Exception:
                    continue
            
            # 如果没有找到同名词选项，提取当前页面信息作为唯一选项
            if not results:
                try:
                    print(f"[INFO] 没有找到同名词面板，提取当前页面信息作为选项")
                    
                    # 提取标题
                    title = keyword  # 默认使用关键词
                    try:
                        title_elem = page.locator('dd.lemmaWgt-lemmaTitle-title h1, h1').first
                        if title_elem.count() > 0:
                            title = title_elem.inner_text().strip()
                            print(f"[INFO] 提取到标题: {title}")
                    except Exception as e:
                        print(f"[DEBUG] 提取标题失败: {e}")
                    
                    # 获取当前URL
                    current_url = page.url
                    print(f"[INFO] 当前URL: {current_url}")
                    
                    # 提取简介
                    summary = ""
                    summary_selectors = [
                        'div.lemmaSummary_GJZu8',
                        'div.lemmaWgt-lemmaSummary',
                        'div[class*="lemma"][class*="summary"]',
                        'div.J-summary',
                    ]
                    for selector in summary_selectors:
                        try:
                            elem = page.locator(selector).first
                            if elem.count() > 0:
                                summary = elem.inner_text().strip()
                                if summary:
                                    print(f"[INFO] 提取到简介 (长度: {len(summary)})")
                                    break
                        except Exception:
                            continue
                    
                    # 如果上述都没找到，尝试meta description
                    if not summary:
                        try:
                            meta = page.locator('meta[name="description"]').first
                            if meta.count() > 0:
                                summary = meta.get_attribute('content') or ""
                                if summary:
                                    print(f"[INFO] 从meta标签提取到简介 (长度: {len(summary)})")
                        except Exception:
                            pass
                    
                    # 构建返回项
                    if title and current_url:
                        normalized_url = _normalize_item_url(current_url)
                        if normalized_url:
                            results.append({
                                'text': title,
                                'href': normalized_url,
                                'snippet': summary[:200] if summary else ""  # 限制长度
                            })
                            print(f"[INFO] 已添加当前页面作为选项: {title}")
                except Exception as e:
                    print(f"[DEBUG] 提取当前页面信息失败: {e}")
            
            browser.close()
        return results
    except Exception:
        return results


def get_polysemant_options(
    keyword: str,
    limit: int = 120,
    *,
    strict: bool = True,
    return_route: bool = False,
) -> Union[List[Dict[str, str]], Tuple[List[Dict[str, str]], str]]:
    """仅使用 Playwright 点击“展开同名词”面板后提取候选。

    - 若 Playwright 不可用，直接返回空列表并给出 route 标识。
    - 保留 strict/return_route 参数以兼容旧签名，strict 无实际作用。
    """
    if not _HAS_PLAYWRIGHT:
        return ([], 'playwright_unavailable') if return_route else []
    try:
        items = _extract_options_dynamic_with_playwright(keyword)
        items = items[:max(1, min(limit, 200))]
        return (items, 'playwright_panel') if return_route else items
    except Exception:
        return ([], 'playwright_error') if return_route else []

def _get_full_once(
    keyword: str,
    *,
    choice_index: Optional[int] = None,
    filter_text: Optional[str] = None,
    chosen_url: Optional[str] = None,
    prefer_amp: bool = True,
    race_pc: bool = True,
    request_timeout: float = 8.0,
    connect_timeout: float = 6.0,
) -> Dict[str, Any]:
    url = chosen_url or f"https://baike.baidu.com/item/{requests.utils.quote(keyword)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Referer': 'https://baike.baidu.com/',
        'Upgrade-Insecure-Requests': '1',
    }
    session = requests.Session()
    session.headers.update(headers)
    timeout_tup = (connect_timeout, request_timeout)
    _ = session.get('https://www.baidu.com/', timeout=timeout_tup)
    time.sleep(random.uniform(0.2, 0.6))
    _ = session.get('https://baike.baidu.com/', timeout=timeout_tup)
    time.sleep(random.uniform(0.3, 0.8))

    # AMP 优先并发：并行请求 AMP 版本，先返回可用内容
    amp_future = None
    if race_pc:
        try:
            executor = ThreadPoolExecutor(max_workers=1)
            amp_future = executor.submit(_fetch_amp_sections, url)
        except Exception:
            amp_future = None

    resp = session.get(url, timeout=timeout_tup, allow_redirects=True)
    _debug_dump(keyword, 'pc_initial', resp.content)
    if resp.status_code == 403:
        card_summary = _fetch_baike_card_summary(keyword, session)
        search_url = f"https://baike.baidu.com/search?word={requests.utils.quote(keyword)}"
        resp_search = session.get(search_url, timeout=timeout_tup)
        if resp_search.status_code == 200:
            soup_search = BeautifulSoup(resp_search.content, 'html.parser')
            link_tag = soup_search.find('a', href=lambda h: h and '/item/' in h)
            if link_tag and link_tag.get('href'):
                fallback_url = link_tag['href']
                if fallback_url.startswith('//'):
                    fallback_url = 'https:' + fallback_url
                elif fallback_url.startswith('/'):
                    fallback_url = 'https://baike.baidu.com' + fallback_url
                resp = session.get(fallback_url, timeout=timeout_tup, allow_redirects=True)
                time.sleep(random.uniform(0.2, 0.6))
        if not (200 <= resp.status_code < 300):
            return {
                'keyword': keyword,
                'url': url,
                'title': keyword,
                'summary': card_summary or '',
                'infobox': {},
                'sections': [],
                'references': []
            }

    if not (200 <= resp.status_code < 300):
        resp.raise_for_status()

    # 若 AMP 优先并且 AMP 已快速返回可用章节，则直接采用 AMP 结果
    if prefer_amp and amp_future is not None:
        try:
            amp = amp_future.result(timeout=0.9)
            if isinstance(amp, dict) and amp.get('sections'):
                return {
                    'keyword': keyword,
                    'url': url,
                    'title': keyword,
                    'summary': str(amp.get('summary') or ''),
                    'infobox': {},
                    'sections': amp.get('sections') or [],
                    'catalog': [],
                    'references': [],
                }
        except Exception:
            pass

    soup = BeautifulSoup(resp.content, 'html.parser')
    current_url = resp.url if hasattr(resp, 'url') else url

    # 同名候选：若提供了选择参数，则尝试解析候选并切换到指定义项
    def _choose_from_options(options: List[Dict[str, str]], *, choice_index: Optional[int], filter_text: Optional[str]) -> Optional[Dict[str, str]]:
        if not options:
            return None
        if isinstance(choice_index, int) and 0 <= choice_index < len(options):
            return options[choice_index]
        if filter_text:
            ft = filter_text.strip().lower()
            for item in options:
                if ft and ft in (item.get('text') or '').lower():
                    return item
        return None

    chosen_item: Optional[Dict[str, str]] = None
    if (choice_index is not None) or (filter_text is not None):
        # 先尝试直接从当前页结构中提取
        options = _extract_polysemant_options(soup, keyword)
        if not options:
            # 辅助：全页含关键词的 /item/ 链接
            options = _extract_keyword_item_links_from_page(soup, keyword)
        if not options and _has_polysemant_hint(soup):
            # 进一步：百科搜索与站内 Web 搜索兜底
            options = _extract_options_from_search(keyword, session, limit=60, relaxed=True)
        if not options:
            options = _extract_options_from_baidu_web(keyword, session, limit=60)
        if options:
            chosen_item = _choose_from_options(options, choice_index=choice_index, filter_text=filter_text)
            if chosen_item and chosen_item.get('href'):
                try:
                    resp2 = session.get(chosen_item['href'], timeout=timeout_tup, allow_redirects=True)
                    if 200 <= resp2.status_code < 300:
                        soup = BeautifulSoup(resp2.content, 'html.parser')
                        current_url = resp2.url if hasattr(resp2, 'url') else chosen_item['href']
                        _debug_dump(keyword, 'pc_poly_choice', resp2.content)
                except Exception:
                    pass

    poly_link = soup.select_one('ul.polysemantList-wrapper a, div.polysemantList a')
    if poly_link and poly_link.get('href'):
        fallback_url = poly_link['href']
        if fallback_url.startswith('//'):
            fallback_url = 'https:' + fallback_url
        elif fallback_url.startswith('/'):
            fallback_url = 'https://baike.baidu.com' + fallback_url
        resp2 = session.get(fallback_url, timeout=timeout_tup, allow_redirects=True)
        if 200 <= resp2.status_code < 300:
            soup = BeautifulSoup(resp2.content, 'html.parser')
            current_url = resp2.url if hasattr(resp2, 'url') else fallback_url
            _debug_dump(keyword, 'pc_poly', resp2.content)

    title = ''
    summary = ''
    infobox: Dict[str, str] = {}
    sections: List[Dict[str, Any]] = []

    def _span_text_concat(node) -> str:
        """从新版结构的段落节点中聚合文本：
        - 只收集 span[data-text="true"] 或 class 含 text_ 的文本片段
        - 忽略脚注/上标（class 含 J-supWrap 或 supWrap_）
        - 清理多余空白与脚注编号
        """
        parts: List[str] = []
        for sp in node.find_all(['span'], recursive=True):
            classes = (sp.get('class') or [])
            if any('J-supWrap' in c or c.startswith('supWrap_') for c in classes):
                continue
            if sp.get('data-text') == 'true' or any('text_' in c for c in classes):
                t = sp.get_text(' ', strip=True)
                if t:
                    parts.append(t)
        text = ' '.join(parts).strip()
        try:
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\[\d+(?:-\d+)?\]', '', text)
        except Exception:
            pass
        return text

    def parse_core(curr_soup: BeautifulSoup) -> None:
        nonlocal title, summary, infobox, sections
        # 标题
        ttag = curr_soup.select_one('dd.lemmaWgt-lemmaTitle-title h1') or curr_soup.find('h1')
        if ttag:
            title = ttag.get_text(strip=True)
        # 摘要
        sdiv = curr_soup.find('div', class_=lambda x: x and 'lemma-summary' in x) or \
               curr_soup.select_one('div.lemmaWgt-lemmaSummary') or \
               curr_soup.select_one('div[class*="lemma"][class*="summary"]') or \
               curr_soup.select_one('div.lemmaSummary_GJZu8.J-summary')
        if sdiv:
            summary_local = re.sub(r'\[\d+(-\d+)?\]', '', sdiv.get_text(" ")).strip()
            if summary_local:
                summary = summary_local
        else:
            meta_desc = curr_soup.find('meta', attrs={'name': 'description'}) or curr_soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc and meta_desc.get('content') and not summary:
                summary = re.sub(r'\[\d+(-\d+)?\]', '', meta_desc.get('content')).strip()
        # 信息框
        infobox_container_local = (
            curr_soup.select_one('div.basic-info.cmn-clearfix') or
            curr_soup.select_one('div.lemmaWgt-basicInfo') or
            curr_soup.select_one('div.basic-info') or
            curr_soup.select_one('div.basicInfo_rZDFN.J-basic-info')
        )
        if infobox_container_local:
            blocks = infobox_container_local.select('dl.basicInfo-block')
            if blocks:
                for block in blocks:
                    for dt in block.select('dt.basicInfo-item.name'):
                        key = dt.get_text(" ", strip=True)
                        dd = dt.find_next_sibling('dd')
                        val = dd.get_text(" ", strip=True) if dd else ''
                        if key:
                            infobox[key] = re.sub(r'\[\d+(-\d+)?\]', '', val)
            else:
                dts = infobox_container_local.select('dt')
                dds = infobox_container_local.select('dd')
                for dt, dd in zip(dts, dds):
                    key = dt.get_text(" ", strip=True)
                    val = re.sub(r'\[\d+(-\d+)?\]', '', dd.get_text(" ", strip=True))
                    if key:
                        infobox[key] = val
        # 章节
        # ① 旧版容器提取（已关闭，仅保留 modern 路径）
        if not _FULL_ONLY_MODERN:
            sections_local: List[Dict[str, Any]] = []
            for node in curr_soup.select('div.lemmaWgt-lemmaSection, div.lemma-section'):
                h2 = node.find('h2')
                title_text = ''
                if h2:
                    inner = h2.select_one('.title-text')
                    title_text = inner.get_text(" ", strip=True) if inner else h2.get_text(" ", strip=True)
                paras = [p.get_text(" ", strip=True) for p in node.select('div.para, p')]
                paras = [re.sub(r'\[\d+(-\d+)?\]', '', p) for p in paras if p and _filter_noise(p)]
                if title_text and paras:
                    sections_local.append({'title': title_text, 'content': paras})
            if sections_local:
                sections = sections_local
                return

        # ② 新版结构：基于 J-lemma-content 内部的 paraTitle/para 收集
        modern_root = curr_soup.select_one('div.J-lemma-content') or \
                      curr_soup.select_one('#J-lemma-main-wrapper div.contentWrapper_kOzfN div.mainContent_L9wKk div.J-lemma-content')
        if modern_root:
            linear_sections: List[Dict[str, Any]] = []
            current: Optional[Dict[str, Any]] = None
            for node in modern_root.find_all(['div'], recursive=True):
                classes = (node.get('class') or [])
                if any('paraTitle' in c for c in classes):
                    # section title
                    h = node.find(['h2', 'h3'])
                    t_text = h.get_text(" ", strip=True) if h else node.get_text(" ", strip=True)
                    if t_text:
                        current = {'title': t_text, 'content': []}
                        linear_sections.append(current)
                    continue
                # 新版段落：data-tag="paragraph" 或类名前缀 para_/content_
                is_para_like = (node.get('data-tag') == 'paragraph') or any(
                    c.startswith('para_') or c.startswith('content_') for c in classes
                )
                if current is not None and (any('para_WuuCs' in c for c in classes) or is_para_like):
                    txt = _span_text_concat(node) or node.get_text(" ", strip=True)
                    if txt and _filter_noise(txt):
                        try:
                            txt = re.sub(r'\[\d+(-\d+)?\]', '', txt)
                        except Exception:
                            pass
                        current['content'].append(txt)
            linear_sections = [s for s in linear_sections if s.get('content')]
            if linear_sections:
                sections = linear_sections
                return

        # ③ 新版信息框 basicInfo_i7jzb
        if not infobox:
            basic = curr_soup.select_one('div.basicInfo_i7jzb')
            if basic:
                dts = basic.find_all('dt')
                dds = basic.find_all('dd')
                for dt, dd in zip(dts, dds):
                    k = dt.get_text(' ', strip=True)
                    v = dd.get_text(' ', strip=True)
                    if k and v:
                        infobox[k] = re.sub(r'\[\d+(-\d+)?\]', '', v)
            return

        # ② 目录驱动（已关闭）
        if not _FULL_ONLY_MODERN:
            linear_sections: List[Dict[str, Any]] = []
            main = curr_soup.select_one('div.main-content') or curr_soup
            current: Optional[Dict[str, Any]] = None
            for node in main.find_all(['h2', 'h3', 'p', 'div', 'ul', 'ol'], recursive=True):
                name = getattr(node, 'name', '')
                if name in ('h2', 'h3'):
                    title_text = node.get_text(" ", strip=True)
                    if title_text:
                        current = {'title': title_text, 'content': []}
                        linear_sections.append(current)
                    continue
                if name in ('p', 'div', 'ul', 'ol') and current is not None:
                    texts: List[str] = []
                    if name == 'div':
                        for p in node.select('div.para, p'):
                            txt = p.get_text(" ", strip=True)
                            if txt and _filter_noise(txt):
                                texts.append(txt)
                    else:
                        txt = node.get_text(" ", strip=True)
                        if txt and _filter_noise(txt):
                            texts.append(txt)
                    for t in texts:
                        t = re.sub(r'\[\d+(-\d+)?\]', '', t)
                        if t:
                            current['content'].append(t)
            linear_sections = [s for s in linear_sections if s.get('content')]
            if linear_sections:
                sections = linear_sections

    def _collect_plain_sections(curr_soup: BeautifulSoup) -> List[Dict[str, Any]]:
        main = curr_soup.select_one('div.J-lemma-content') or curr_soup.select_one('div.main-content') or curr_soup
        paras = [p.get_text(" ", strip=True) for p in main.select('div.para, p, div.para_WuuCs')]
        cleaned = [re.sub(r'\[\d+(-\d+)?\]', '', t) for t in paras if t and _filter_noise(t)]
        if cleaned:
            return [{'title': '正文', 'content': cleaned}]
        return []

    def _fetch_amp_sections(pc_url: str) -> Dict[str, Any]:
        try:
            amp_url = pc_url.replace('://baike.baidu.com/item/', '://baike.baidu.com/amphtml/item/')
            s2 = requests.Session()
            s2.headers.update({
                'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://baike.baidu.com/',
                'Connection': 'keep-alive',
            })
            r = s2.get(amp_url, timeout=10, allow_redirects=True)
            if not (200 <= r.status_code < 300):
                return {}
            s = BeautifulSoup(r.content, 'html.parser')
            sections_amp: List[Dict[str, Any]] = []
            for h2 in s.find_all('h2'):
                tt = h2.get_text(" ", strip=True)
                if not tt:
                    continue
                content_list: List[str] = []
                for sib in h2.next_siblings:
                    if getattr(sib, 'name', None) == 'h2':
                        break
                    if getattr(sib, 'name', None) in ['p', 'ul', 'ol', 'div']:
                        if sib.name == 'p':
                            txt = sib.get_text(" ", strip=True)
                            if txt:
                                content_list.append(txt)
                        if hasattr(sib, 'find_all'):
                            for li in sib.find_all('li'):
                                txt = li.get_text(" ", strip=True)
                                if txt:
                                    content_list.append(txt)
                        if hasattr(sib, 'select'):
                            for p in sib.select('div.para'):
                                txt = p.get_text(" ", strip=True)
                                if txt:
                                    content_list.append(txt)
                content_list = [re.sub(r'\[\d+(-\d+)?\]', '', c) for c in content_list if c and c not in ('编辑', '目录')]
                if content_list:
                    sections_amp.append({'title': tt, 'content': content_list})
            # 摘要简单取第一节前两段
            summary_amp = ''
            if sections_amp:
                summary_amp = ' '.join(sections_amp[0]['content'][:2])
            # 返回
            return {'sections': sections_amp, 'summary': summary_amp}
        except Exception:
            return {}

    # 首次解析
    parse_core(soup)
    if not sections and not _FULL_ONLY_MODERN:
        # 等待 5 秒后重试一次
        time.sleep(5.0)
        resp_retry = session.get(url, timeout=timeout_tup, allow_redirects=True)
        _debug_dump(keyword, 'pc_retry', resp_retry.content)
        if 200 <= resp_retry.status_code < 300:
            soup_retry = BeautifulSoup(resp_retry.content, 'html.parser')
            parse_core(soup_retry)
            # 若仍无章节，尝试全页段落兜底
            if not sections:
                plain = _collect_plain_sections(soup_retry)
                if plain:
                    sections = plain
        # 如仍没有摘要，则尝试卡片摘要兜底
        if not summary:
            card_summary = _fetch_baike_card_summary(keyword, session)
            if card_summary:
                summary = card_summary
    # 再次兜底：AMP 解析
    if not sections and not _FULL_ONLY_MODERN:
        amp = _fetch_amp_sections(url)
        if isinstance(amp, dict) and amp.get('sections'):
            sections = amp['sections']  # type: ignore
            if not summary and amp.get('summary'):
                summary = amp['summary']  # type: ignore
    # 搜索页回退：即便状态为 200，但页面结构特殊时，尝试搜索到首个 /item/ 具体条目
    if not sections and not _FULL_ONLY_MODERN:
        try:
            search_url = f"https://baike.baidu.com/search?word={requests.utils.quote(keyword)}"
            resp_search = session.get(search_url, timeout=timeout_tup)
            _debug_dump(keyword, 'search', resp_search.content)
            if 200 <= resp_search.status_code < 300:
                soup_search = BeautifulSoup(resp_search.content, 'html.parser')
                link_tag = soup_search.find('a', href=lambda h: h and '/item/' in h)
                if link_tag and link_tag.get('href'):
                    fallback_url = link_tag['href']
                    if fallback_url.startswith('//'):
                        fallback_url = 'https:' + fallback_url
                    elif fallback_url.startswith('/'):
                        fallback_url = 'https://baike.baidu.com' + fallback_url
                    resp_fallback = session.get(fallback_url, timeout=timeout_tup, allow_redirects=True)
                    _debug_dump(keyword, 'pc_fallback', resp_fallback.content)
                    if 200 <= resp_fallback.status_code < 300:
                        soup_fb = BeautifulSoup(resp_fallback.content, 'html.parser')
                        parse_core(soup_fb)
                        if not sections:
                            # 尝试全页段落兜底
                            plain2 = _collect_plain_sections(soup_fb)
                            if plain2:
                                sections = plain2
                        if not sections:
                            # AMP 兜底
                            amp2 = _fetch_amp_sections(fallback_url)
                            if isinstance(amp2, dict) and amp2.get('sections'):
                                sections = amp2['sections']  # type: ignore
                                if not summary and amp2.get('summary'):
                                    summary = amp2['summary']  # type: ignore
        except Exception:
            pass

    references: List[Dict[str, str]] = []
    for li in soup.select('ol.reference-list li, div.reference-list li, li.reference-item'):
        ref_text = li.get_text(" ", strip=True)
        a = li.find('a')
        ref_href = ''
        if a and a.get('href'):
            ref_href = a['href']
            if ref_href.startswith('//'):
                ref_href = 'https:' + ref_href
            elif ref_href.startswith('/'):
                ref_href = 'https://baike.baidu.com' + ref_href
        references.append({'text': ref_text, 'url': ref_href})

    # 若最终 PC 未产出章节而 AMP 分支成功，则采用 AMP 结果兜底
    if (not sections) and amp_future is not None:
        try:
            amp = amp_future.result(timeout=0.1)
            if isinstance(amp, dict) and amp.get('sections'):
                return {
                    'keyword': keyword,
                    'url': url,
                    'title': title or keyword,
                    'summary': summary or str(amp.get('summary') or ''),
                    'infobox': infobox,
                    'sections': amp.get('sections') or [],
                    'catalog': [],
                    'references': [],
                }
        except Exception:
            pass

    return {
        'keyword': keyword,
        'url': current_url,
        'title': title or keyword,
        'summary': summary,
        'infobox': infobox,
        'sections': sections,
        'catalog': [],
        'references': references,
    }


def _sections_char_count(data: Dict[str, Any]) -> int:
    total = 0
    for sec in data.get('sections', []) or []:
        for p in sec.get('content', []) or []:
            if isinstance(p, str):
                total += len(p)
    return total


def get_full(
    keyword: str,
    retries: int = 5,
    min_sections: int = 0,
    min_chars: int = 500,
    *,
    choice_index: Optional[int] = None,
    filter_text: Optional[str] = None,
    chosen_url: Optional[str] = None,
    prefer_amp: bool = True,
    race_pc: bool = True,
    request_timeout: float = 8.0,
    connect_timeout: float = 6.0,
) -> Dict[str, Any]:
    last: Optional[Dict[str, Any]] = None
    for attempt in range(max(1, retries)):
        try:
            data = _get_full_once(
                keyword,
                choice_index=choice_index,
                filter_text=filter_text,
                chosen_url=chosen_url,
                prefer_amp=prefer_amp,
                race_pc=race_pc,
                request_timeout=request_timeout,
                connect_timeout=connect_timeout,
            )
            last = data
            ok = False
            if min_chars and _sections_char_count(data) >= max(0, min_chars):
                ok = True
            elif (not min_chars) and len(data.get('sections', [])) >= max(0, min_sections):
                ok = True
            if ok:
                return data
        except Exception:
            pass
        time.sleep(0.7 * (attempt + 1))
    return last or {
        'keyword': keyword,
        'url': f"https://baike.baidu.com/item/{requests.utils.quote(keyword)}",
        'title': keyword,
        'summary': '',
        'infobox': {},
        'sections': [],
        'catalog': [],
        'references': [],
    }


