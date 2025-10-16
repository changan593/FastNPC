# -*- coding: utf-8 -*-
"""
命令行接口模块
"""
from __future__ import annotations

import argparse
from .core import run


def _build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(description="FastNPC 结构化：从原始输入生成结构化画像")
    parser.add_argument("--input", "-i", required=True, help="输入文件路径（如 Characters/baike_xxx.json）")
    parser.add_argument("--output", "-o", default=None, help="输出结构化JSON路径（默认与输入同目录）")
    parser.add_argument("--level", choices=["detailed", "concise"], default="detailed", help="结构化细节等级")
    parser.add_argument("--strategy", choices=["global", "mapreduce"], default="global", help="摘要/事实策略：global=整文摘要 mapreduce=分块事实")
    parser.add_argument("--export-facts", action="store_true", help="导出事实抽取结果为 facts_*.json")
    parser.add_argument("--facts-out", default=None, help="事实JSON输出路径（默认与输入同目录，facts_前缀）")
    parser.add_argument("--export-bullets", action="store_true", help="导出要点文本为 bullets_*.txt")
    parser.add_argument("--bullets-out", default=None, help="要点输出路径（默认与输入同目录，bullets_前缀）")
    parser.add_argument("--export-summary", action="store_true", help="导出全局详细摘要为 summary_*.txt（仅 global 策略适用）")
    parser.add_argument("--summary-out", default=None, help="摘要输出路径（默认与输入同目录，summary_前缀）")
    parser.add_argument("--export-md", action="store_true", help="导出 JSON → Markdown 的中间结果 md_*.md")
    parser.add_argument("--md-out", default=None, help="Markdown 输出路径（默认与输入同目录，md_前缀）")
    return parser


def main() -> None:
    """CLI 主函数"""
    parser = _build_arg_parser()
    args = parser.parse_args()
    run(
        input_path=args.input,
        output_path=args.output,
        level=args.level,
        export_facts=bool(args.export_facts),
        facts_output_path=args.facts_out,
        export_bullets=bool(args.export_bullets),
        bullets_output_path=args.bullets_out,
        strategy=args.strategy,
        export_summary=bool(args.export_summary),
        summary_output_path=args.summary_out,
        export_markdown=bool(args.export_md),
        markdown_output_path=args.md_out,
    )


if __name__ == "__main__":
    main()

