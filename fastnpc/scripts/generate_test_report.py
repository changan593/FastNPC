# -*- coding: utf-8 -*-
"""
生成提示词测试报告
汇总所有测试用例和评估结果，生成HTML或Markdown报告
"""
from __future__ import annotations

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from fastnpc.api.auth.db_utils import _get_conn, _return_conn, _row_to_dict
from fastnpc.config import USE_POSTGRESQL


def generate_markdown_report(output_file: str = "prompt_test_report.md"):
    """生成Markdown格式的测试报告"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        
        # 获取所有提示词
        cur.execute("""
            SELECT id, category, sub_category, name, version, is_active
            FROM prompt_templates
            ORDER BY category, sub_category
        """)
        
        prompts = []
        for row in cur.fetchall():
            if USE_POSTGRESQL:
                prompts.append(_row_to_dict(row, cur))
            else:
                prompts.append(dict(row))
        
        # 获取所有测试用例
        cur.execute("""
            SELECT id, prompt_category, prompt_sub_category, name, description
            FROM prompt_test_cases
            ORDER BY prompt_category, prompt_sub_category
        """)
        
        test_cases = []
        for row in cur.fetchall():
            if USE_POSTGRESQL:
                test_cases.append(_row_to_dict(row, cur))
            else:
                test_cases.append(dict(row))
        
        # 获取评估统计
        cur.execute("""
            SELECT 
                pt.category,
                pt.sub_category,
                pt.name as prompt_name,
                COUNT(pe.id) as eval_count,
                AVG(CAST(pe.manual_score AS FLOAT)) as avg_score
            FROM prompt_templates pt
            LEFT JOIN prompt_evaluations pe ON pt.id = pe.prompt_template_id
            WHERE pt.is_active = 1
            GROUP BY pt.id, pt.category, pt.sub_category, pt.name
            ORDER BY pt.category, pt.sub_category
        """)
        
        eval_stats = []
        for row in cur.fetchall():
            if USE_POSTGRESQL:
                eval_stats.append(_row_to_dict(row, cur))
            else:
                eval_stats.append(dict(row))
        
        # 生成Markdown
        lines = []
        lines.append("# 提示词测试报告")
        lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("\n---\n")
        
        # 概览
        lines.append("## 📊 概览")
        lines.append(f"\n- **提示词总数**: {len(prompts)}")
        lines.append(f"- **激活提示词数**: {len([p for p in prompts if p['is_active']])}")
        lines.append(f"- **测试用例总数**: {len(test_cases)}")
        
        # 按类别统计
        categories = {}
        for prompt in prompts:
            cat = prompt['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'active': 0}
            categories[cat]['total'] += 1
            if prompt['is_active']:
                categories[cat]['active'] += 1
        
        lines.append("\n### 按类别统计\n")
        lines.append("| 类别 | 提示词总数 | 激活数 |")
        lines.append("|------|-----------|--------|")
        for cat, stats in sorted(categories.items()):
            lines.append(f"| {cat} | {stats['total']} | {stats['active']} |")
        
        # 测试用例列表
        lines.append("\n---\n")
        lines.append("## 📝 测试用例")
        
        test_by_category = {}
        for tc in test_cases:
            cat = tc['prompt_category']
            if cat not in test_by_category:
                test_by_category[cat] = []
            test_by_category[cat].append(tc)
        
        for cat in sorted(test_by_category.keys()):
            lines.append(f"\n### {cat}")
            lines.append(f"\n测试用例数: {len(test_by_category[cat])}\n")
            
            for tc in test_by_category[cat]:
                sub_cat = tc.get('prompt_sub_category', '')
                lines.append(f"#### {tc['name']}")
                if sub_cat:
                    lines.append(f"**子分类**: {sub_cat}")
                lines.append(f"**描述**: {tc['description']}")
                lines.append("")
        
        # 评估结果
        if eval_stats:
            lines.append("\n---\n")
            lines.append("## 📈 评估结果")
            lines.append("\n| 提示词 | 类别 | 评估次数 | 平均分 |")
            lines.append("|--------|------|----------|--------|")
            
            for stat in eval_stats:
                if stat['eval_count'] > 0:
                    avg_score = stat['avg_score'] if stat['avg_score'] else 'N/A'
                    if isinstance(avg_score, (int, float)):
                        avg_score = f"{avg_score:.2f}"
                    
                    sub_cat = stat.get('sub_category', '')
                    cat_display = f"{stat['category']}" + (f" / {sub_cat}" if sub_cat else "")
                    
                    lines.append(f"| {stat['prompt_name']} | {cat_display} | {stat['eval_count']} | {avg_score} |")
        
        # 写入文件
        content = '\n'.join(lines)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 测试报告已生成: {output_file}")
        print(f"  提示词总数: {len(prompts)}")
        print(f"  测试用例总数: {len(test_cases)}")
        
    finally:
        _return_conn(conn)


def main():
    """主函数"""
    output_file = sys.argv[1] if len(sys.argv) > 1 else "prompt_test_report.md"
    generate_markdown_report(output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())

