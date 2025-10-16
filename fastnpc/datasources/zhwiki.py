# -*- coding: utf-8 -*-
from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple, Union
import time
import re


API_URL = "https://zh.wikipedia.org/w/api.php"
VARIANT = "zh-hans"
HEADERS = {
    'User-Agent': 'FastNPC/1.0 (+https://example.com; contact@example.com) Python-requests',
    'Accept-Language': 'zh-CN,zh;q=0.9'
}


def _api_get(params: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _search_candidates(keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
    data = _api_get({'action': 'query', 'format': 'json', 'list': 'search', 'srsearch': keyword, 'srlimit': max(1, min(200, limit)), 'srprop': 'snippet|titlesnippet'})
    hits = data.get('query', {}).get('search', [])
    results: List[Dict[str, Any]] = []
    for h in hits:
        title = h.get('title') or ''
        if not title:
            continue
        results.append({'title': title, 'snippet': h.get('snippet', '')})
    return results


def _is_disambiguation(title: str) -> bool:
    data = _api_get({'action': 'query', 'format': 'json', 'prop': 'pageprops', 'ppprop': 'disambiguation', 'titles': title})
    pages = data.get('query', {}).get('pages', {})
    for _, p in pages.items():
        if 'pageprops' in p and 'disambiguation' in p.get('pageprops', {}):
            return True
    return False


def _disambig_links(title: str, limit: int = 200) -> List[Dict[str, Any]]:
    data = _api_get({'action': 'parse', 'format': 'json', 'page': title, 'prop': 'links', 'variant': VARIANT})
    links = data.get('parse', {}).get('links', [])
    results: List[Dict[str, Any]] = []
    for l in links:
        if int(l.get('ns', 0)) != 0:
            continue
        t = l.get('*') or l.get('title') or ''
        if not t:
            continue
        results.append({'title': t})
        if len(results) >= limit:
            break
    return results


def get_polysemant_options(keyword: str, limit: int = 80, *, return_route: bool = False) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], str]]:
    """返回候选标题列表；若首选为消歧义页，则附加其出链作为更多候选。"""
    route = "search"
    results = _search_candidates(keyword, limit=limit)
    try:
        if results:
            first = results[0]
            t = first.get('title') or ''
            if t and _is_disambiguation(t):
                more = _disambig_links(t, limit=200)
                # 追加，但去重
                seen = { (r.get('title') or '') for r in results }
                for m in more:
                    tt = m.get('title') or ''
                    if tt and tt not in seen:
                        results.append(m)
                        seen.add(tt)
                route = "disambig_links"
    except Exception:
        pass
    results = results[:max(1, min(200, limit))]
    return (results, route) if return_route else results


def _parse_page_html(title: str, section: Optional[str] = None) -> str:
    params = {'action': 'parse', 'format': 'json', 'page': title, 'prop': 'text', 'formatversion': 2, 'variant': VARIANT}
    if section is not None:
        params['section'] = section
    data = _api_get(params)
    html = data.get('parse', {}).get('text', '')
    return html or ''


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for sup in soup.select('sup.reference, sup[role="note"]'):
        sup.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()


def _get_extract_intro(title: str) -> str:
    data = _api_get({'action': 'parse', 'format': 'json', 'page': title, 'prop': 'text', 'section': 0, 'formatversion': 2, 'variant': VARIANT})
    html = data.get('parse', {}).get('text', '')
    return _html_to_text(html)


def _parse_sections(title: str) -> List[Dict[str, Any]]:
    data = _api_get({'action': 'parse', 'format': 'json', 'page': title, 'prop': 'sections', 'variant': VARIANT})
    secs = data.get('parse', {}).get('sections', [])
    catalog = []
    for s in secs:
        catalog.append({'index': s.get('index'), 'title': s.get('line', ''), 'anchor': s.get('anchor', ''), 'level': int(s.get('toclevel', 2))})
    return catalog


def _parse_infobox_from_html(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, 'html.parser')
    infobox: Dict[str, str] = {}
    table = soup.select_one('table.infobox')
    if not table:
        return infobox
    for tr in table.select('tr'):
        th = tr.find('th')
        td = tr.find('td')
        if th and td:
            k = th.get_text(' ', strip=True)
            v = td.get_text(' ', strip=True)
            if k:
                infobox[k] = v
    return infobox


def _parse_references_from_html(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, 'html.parser')
    refs: List[Dict[str, str]] = []
    for li in soup.select('ol.references li, div.references li'):
        txt = li.get_text(' ', strip=True)
        a = li.find('a', href=True)
        href = a['href'] if a else ''
        refs.append({'text': txt, 'url': href})
    return refs


def _choose(options: List[Dict[str, Any]], *, choice_index: Optional[int], filter_text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not options:
        return None
    if isinstance(choice_index, int) and 0 <= choice_index < len(options):
        return options[choice_index]
    if filter_text:
        ft = filter_text.strip().lower()
        for it in options:
            if ft and ft in (it.get('title') or '').lower():
                return it
    return options[0]


def _get_full_once(keyword: str, *, choice_index: Optional[int] = None, filter_text: Optional[str] = None) -> Dict[str, Any]:
    # 1) 搜索候选并选择
    title = keyword
    try:
        cand = _search_candidates(keyword, limit=80)
        chosen = _choose(cand, choice_index=choice_index, filter_text=filter_text) if cand else None
        if chosen:
            title = chosen.get('title') or keyword
        # 2) 若为消歧义页，展开二级候选
        if _is_disambiguation(title):
            sub = _disambig_links(title, limit=200)
            chosen2 = _choose(sub, choice_index=choice_index, filter_text=filter_text) if sub else None
            if chosen2:
                title = chosen2.get('title') or title
    except Exception:
        pass

    summary = _get_extract_intro(title)
    full_html = _parse_page_html(title)
    infobox = _parse_infobox_from_html(full_html)
    references = _parse_references_from_html(full_html)
    catalog = _parse_sections(title)
    sections: List[Dict[str, Any]] = []
    if catalog:
        for item in catalog:
            idx = item.get('index')
            html = _parse_page_html(title, section=idx)
            text = _html_to_text(html)
            if text:
                sections.append({'title': item.get('title', ''), 'content': [text]})
    else:
        text = _html_to_text(full_html)
        if text:
            sections.append({'title': title, 'content': [text]})

    return {
        'keyword': keyword,
        'title': title,
        'summary': summary,
        'catalog': [{'title': it.get('title', ''), 'anchor': it.get('anchor', ''), 'level': it.get('level', 2)} for it in catalog],
        'infobox': infobox,
        'sections': sections,
        'references': references,
        'source': f'https://zh.wikipedia.org/wiki/{requests.utils.quote(title)}?variant={VARIANT}'
    }


def _sections_char_count(data: Dict[str, Any]) -> int:
    total = 0
    for sec in data.get('sections', []) or []:
        for p in sec.get('content', []) or []:
            if isinstance(p, str):
                total += len(p)
    return total


def get_full(keyword: str, retries: int = 5, min_sections: int = 0, min_chars: int = 500, *, choice_index: Optional[int] = None, filter_text: Optional[str] = None) -> Dict[str, Any]:
    last: Optional[Dict[str, Any]] = None
    for attempt in range(max(1, retries)):
        try:
            data = _get_full_once(keyword, choice_index=choice_index, filter_text=filter_text)
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
        time.sleep(0.5 * (attempt + 1))
    return last or {'keyword': keyword, 'title': keyword, 'summary': '', 'catalog': [], 'infobox': {}, 'sections': [], 'references': [], 'source': ''}


