# -*- coding: utf-8 -*-
"""高鲁棒性百度百科爬虫 - 使用Playwright作为主要方案"""
from __future__ import annotations

import time
import random
import json
from typing import Dict, Any, List, Optional

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    _HAS_PLAYWRIGHT = True
except Exception:
    _HAS_PLAYWRIGHT = False


def get_full_robust(
    keyword: str,
    retries: int = 3,
    *,
    chosen_url: Optional[str] = None,
    timeout_ms: int = 15000,
) -> Dict[str, Any]:
    """使用Playwright直接抓取百度百科（高鲁棒性版本）
    
    优势：
    1. 真实浏览器环境，不易被反爬
    2. 自动处理动态内容
    3. 可以等待页面完全加载
    4. 更接近真实用户行为
    """
    if not _HAS_PLAYWRIGHT:
        return _fallback_empty_result(keyword, chosen_url)
    
    url = chosen_url or f"https://baike.baidu.com/item/{keyword}"
    print(f"[DEBUG] baike_robust: keyword={keyword}, chosen_url={chosen_url}, final_url={url}")
    
    for attempt in range(max(1, retries)):
        try:
            result = _fetch_with_playwright(keyword, url, timeout_ms)
            
            # 检查是否获取到有效内容
            if result.get('sections') and len(result['sections']) > 0:
                return result
            
            # 如果第一次失败，增加等待时间重试
            if attempt < retries - 1:
                time.sleep(1.5 + random.uniform(0, 1))
                
        except Exception as e:
            print(f"[WARN] Playwright爬取失败 (尝试 {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(1.0 + random.uniform(0, 0.5))
    
    # 所有尝试都失败，返回空结果
    return _fallback_empty_result(keyword, chosen_url)


def _fetch_with_playwright(keyword: str, url: str, timeout_ms: int) -> Dict[str, Any]:
    """使用Playwright抓取页面"""
    with sync_playwright() as p:
        # 使用Chromium，更稳定
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',  # 隐藏自动化特征
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # 创建上下文，模拟真实浏览器（禁用缓存以避免获取到旧页面）
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            ignore_https_errors=True,
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'no-cache, no-store, must-revalidate',  # 强制禁用缓存
                'Pragma': 'no-cache',  # HTTP/1.0 缓存控制
                'Expires': '0',  # 立即过期
            }
        )
        
        page = context.new_page()
        
        # 注入脚本，隐藏webdriver特征
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        """)
        
        try:
            # 禁用页面缓存
            page.route('**/*', lambda route: route.continue_(headers={
                **route.request.headers,
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
            }))
            
            # 访问页面（强制刷新，不使用缓存）
            print(f"[DEBUG] Playwright访问URL: {url}")
            page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms, referer=None)
            
            # 随机延迟，模拟人类阅读
            time.sleep(random.uniform(0.8, 1.5))
            
            # 尝试点击展开同名词面板（如果有）
            try:
                poly_selector = 'div.J-polysemantText, div[class^="polysemantText_"]'
                if page.locator(poly_selector).count() > 0:
                    page.locator(poly_selector).first.click(timeout=2000)
                    time.sleep(0.5)
            except:
                pass
            
            # 等待主要内容加载
            try:
                page.wait_for_selector('div.J-lemma-content, div.main-content, div.lemma-summary', timeout=5000)
            except:
                pass
            
            # 滚动页面，触发懒加载
            page.evaluate("""
                () => {
                    window.scrollTo(0, document.body.scrollHeight / 3);
                }
            """)
            time.sleep(0.3)
            
            page.evaluate("""
                () => {
                    window.scrollTo(0, document.body.scrollHeight / 2);
                }
            """)
            time.sleep(0.3)
            
            # 获取页面内容
            html_content = page.content()
            
            # 提取数据
            result = _parse_html_content(page, keyword, url)
            
            # 验证返回的数据是否正确（标题应该包含关键词）
            print(f"[DEBUG] 爬取结果 - keyword: {keyword}, title: {result.get('title', 'N/A')}")
            
            # 关闭上下文和浏览器，确保完全清理
            page.close()
            context.close()
            browser.close()
            
            return result
            
        except PlaywrightTimeout as e:
            try:
                page.close()
                context.close()
            except:
                pass
            browser.close()
            raise Exception(f"页面加载超时: {e}")
        except Exception as e:
            try:
                page.close()
                context.close()
            except:
                pass
            browser.close()
            raise


def _parse_html_content(page, keyword: str, url: str) -> Dict[str, Any]:
    """从页面中提取内容（多种选择器策略）"""
    
    # 提取标题
    title = keyword
    try:
        title_elem = page.locator('dd.lemmaWgt-lemmaTitle-title h1, h1').first
        if title_elem.count() > 0:
            title = title_elem.inner_text().strip()
    except:
        pass
    
    # 提取摘要
    summary = ""
    summary_selectors = [
        'div.lemmaSummary_GJZu8',
        'div.lemmaWgt-lemmaSummary',
        'div[class*="lemma"][class*="summary"]',
        'div.J-summary',
        'meta[name="description"]',
    ]
    for selector in summary_selectors:
        try:
            if selector.startswith('meta'):
                summary = page.locator(selector).get_attribute('content') or ""
            else:
                elem = page.locator(selector).first
                if elem.count() > 0:
                    summary = elem.inner_text().strip()
            if summary:
                break
        except:
            continue
    
    # 提取信息框
    infobox = {}
    try:
        info_selectors = [
            'div.basicInfo_rZDFN',
            'div.basicInfo_i7jzb',
            'div.lemmaWgt-basicInfo',
            'div.basic-info',
        ]
        for selector in info_selectors:
            try:
                info_container = page.locator(selector).first
                if info_container.count() > 0:
                    # 提取dt-dd对
                    dts = info_container.locator('dt').all()
                    dds = info_container.locator('dd').all()
                    for dt, dd in zip(dts, dds):
                        key = dt.inner_text().strip()
                        val = dd.inner_text().strip()
                        if key:
                            infobox[key] = val
                    if infobox:
                        break
            except:
                continue
    except:
        pass
    
    # 提取章节（多种策略）
    sections = _extract_sections_multi_strategy(page)
    
    # 提取头像图片URL
    avatar_url = None
    try:
        avatar_selectors = [
            '#side div.abstractAlbum_jhNeu img',
            'div.abstractAlbum_jhNeu img',
            'div.summary-pic img',
            'div.lemma-summary img',
            '#side img',
        ]
        for selector in avatar_selectors:
            try:
                img_elem = page.locator(selector).first
                if img_elem.count() > 0:
                    avatar_url = img_elem.get_attribute('src')
                    if not avatar_url:
                        avatar_url = img_elem.get_attribute('data-src')
                    if avatar_url:
                        # 处理相对URL
                        if avatar_url.startswith('//'):
                            avatar_url = 'https:' + avatar_url
                        elif avatar_url.startswith('/'):
                            avatar_url = 'https://baike.baidu.com' + avatar_url
                        
                        # 过滤图标
                        if 'icon' not in avatar_url.lower() and 'logo' not in avatar_url.lower():
                            print(f"[INFO] 找到头像URL: {avatar_url}")
                            break
                        avatar_url = None
            except:
                continue
    except Exception as e:
        print(f"[WARN] 提取头像URL失败: {e}")
    
    result = {
        'keyword': keyword,
        'url': url,
        'title': title,
        'summary': summary,
        'infobox': infobox,
        'sections': sections,
        'catalog': [],
        'references': [],
    }
    
    if avatar_url:
        result['avatar_url'] = avatar_url
    
    return result


def _extract_sections_multi_strategy(page) -> List[Dict[str, Any]]:
    """多策略提取章节内容"""
    sections = []
    
    # 策略1: 新版结构 (J-lemma-content内的paraTitle和para)
    try:
        sections = _extract_modern_sections(page)
        if sections:
            return sections
    except Exception as e:
        print(f"[DEBUG] 策略1失败: {e}")
    
    # 策略2: 旧版结构 (lemmaWgt-lemmaSection)
    try:
        sections = _extract_legacy_sections(page)
        if sections:
            return sections
    except Exception as e:
        print(f"[DEBUG] 策略2失败: {e}")
    
    # 策略3: 通用H2+段落结构
    try:
        sections = _extract_generic_sections(page)
        if sections:
            return sections
    except Exception as e:
        print(f"[DEBUG] 策略3失败: {e}")
    
    # 策略4: 全页段落兜底
    try:
        sections = _extract_all_paragraphs(page)
        if sections:
            return sections
    except Exception as e:
        print(f"[DEBUG] 策略4失败: {e}")
    
    return []


def _extract_modern_sections(page) -> List[Dict[str, Any]]:
    """提取新版页面结构"""
    sections = []
    
    # 定位主内容区
    content_selectors = [
        'div.J-lemma-content',
        'div.mainContent_L9wKk div.J-lemma-content',
        'div[class*="mainContent"]',
    ]
    
    content_root = None
    for selector in content_selectors:
        try:
            elem = page.locator(selector).first
            if elem.count() > 0:
                content_root = elem
                break
        except:
            continue
    
    if not content_root:
        return []
    
    # 提取所有paraTitle和对应的para内容
    try:
        # 获取所有标题元素
        titles = content_root.locator('div[class*="paraTitle"], h2, h3').all()
        
        for title_elem in titles:
            title_text = title_elem.inner_text().strip()
            if not title_text or title_text in ['编辑', '目录', '播报']:
                continue
            
            # 获取该标题后的所有段落（直到下一个标题）
            paragraphs = []
            
            # 查找紧跟的段落元素
            next_elem = title_elem
            for _ in range(20):  # 最多查找20个兄弟元素
                try:
                    next_elem = page.evaluate(
                        '(elem) => elem.nextElementSibling', 
                        next_elem.element_handle()
                    )
                    if not next_elem:
                        break
                    
                    # 检查是否是下一个标题
                    class_attr = page.evaluate('(elem) => elem.className || ""', next_elem)
                    if 'paraTitle' in class_attr or next_elem.get('tagName', '').lower() in ['h2', 'h3']:
                        break
                    
                    # 检查是否是段落
                    if 'para' in class_attr or 'content' in class_attr:
                        text = page.evaluate('(elem) => elem.innerText || ""', next_elem).strip()
                        if text and len(text) > 10:
                            paragraphs.append(text)
                except:
                    break
            
            if paragraphs:
                sections.append({
                    'title': title_text,
                    'content': paragraphs
                })
    except Exception as e:
        print(f"[DEBUG] 现代结构提取失败: {e}")
    
    return sections


def _extract_legacy_sections(page) -> List[Dict[str, Any]]:
    """提取旧版页面结构"""
    sections = []
    
    try:
        section_containers = page.locator('div.lemmaWgt-lemmaSection, div.lemma-section').all()
        
        for container in section_containers:
            # 提取标题
            title = ""
            try:
                h2 = container.locator('h2').first
                if h2.count() > 0:
                    title = h2.inner_text().strip()
            except:
                pass
            
            if not title:
                continue
            
            # 提取段落
            paragraphs = []
            try:
                para_elems = container.locator('div.para, p').all()
                for para in para_elems:
                    text = para.inner_text().strip()
                    if text and len(text) > 10:
                        paragraphs.append(text)
            except:
                pass
            
            if paragraphs:
                sections.append({
                    'title': title,
                    'content': paragraphs
                })
    except Exception as e:
        print(f"[DEBUG] 旧版结构提取失败: {e}")
    
    return sections


def _extract_generic_sections(page) -> List[Dict[str, Any]]:
    """通用H2+段落提取"""
    sections = []
    current_section = None
    
    try:
        # 获取所有H2和段落元素
        all_h2 = page.locator('h2').all()
        
        for h2 in all_h2:
            title = h2.inner_text().strip()
            if not title or title in ['编辑', '目录', '播报']:
                continue
            
            # 查找该H2后的所有段落
            paragraphs = []
            try:
                # 使用JavaScript找到后续段落
                paras = page.evaluate("""
                    (h2) => {
                        const result = [];
                        let elem = h2.nextElementSibling;
                        while (elem && elem.tagName !== 'H2') {
                            if (elem.tagName === 'P' || elem.className.includes('para')) {
                                const text = elem.innerText?.trim();
                                if (text && text.length > 10) {
                                    result.push(text);
                                }
                            }
                            elem = elem.nextElementSibling;
                        }
                        return result;
                    }
                """, h2.element_handle())
                
                paragraphs = paras
            except:
                pass
            
            if paragraphs:
                sections.append({
                    'title': title,
                    'content': paragraphs
                })
    except Exception as e:
        print(f"[DEBUG] 通用结构提取失败: {e}")
    
    return sections


def _extract_all_paragraphs(page) -> List[Dict[str, Any]]:
    """兜底：提取页面所有段落"""
    try:
        # 获取所有看起来像段落的元素
        paras = page.evaluate("""
            () => {
                const elements = document.querySelectorAll('p, div.para, div[class*="para"]');
                const result = [];
                elements.forEach(elem => {
                    const text = elem.innerText?.trim();
                    if (text && text.length > 20) {
                        result.push(text);
                    }
                });
                return result;
            }
        """)
        
        if paras and len(paras) > 0:
            return [{
                'title': '正文',
                'content': paras
            }]
    except:
        pass
    
    return []


def _fallback_empty_result(keyword: str, url: Optional[str]) -> Dict[str, Any]:
    """返回空结果"""
    return {
        'keyword': keyword,
        'url': url or f"https://baike.baidu.com/item/{keyword}",
        'title': keyword,
        'summary': '',
        'infobox': {},
        'sections': [],
        'catalog': [],
        'references': [],
    }

