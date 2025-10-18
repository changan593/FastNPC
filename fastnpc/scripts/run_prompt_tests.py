# -*- coding: utf-8 -*-
"""
提示词测试运行脚本
运行所有测试用例并生成报告
"""
from __future__ import annotations

import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from fastnpc.prompt_manager import PromptManager
from fastnpc.prompt_evaluator import PromptEvaluator


async def run_all_tests():
    """运行所有激活提示词的测试"""
    print("=" * 80)
    print("提示词自动化测试")
    print("=" * 80)
    
    # 获取所有激活的提示词
    prompts = PromptManager.list_prompts(include_inactive=False)
    
    if not prompts:
        print("未找到激活的提示词")
        return
    
    print(f"\n找到 {len(prompts)} 个激活的提示词")
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for prompt in prompts:
        prompt_id = prompt['id']
        prompt_name = prompt['name']
        prompt_category = prompt['category']
        prompt_sub_category = prompt.get('sub_category', '')
        
        print(f"\n{'=' * 80}")
        print(f"测试提示词: {prompt_name}")
        print(f"类别: {prompt_category} {('/ ' + prompt_sub_category) if prompt_sub_category else ''}")
        print(f"版本: {prompt['version']}")
        print(f"{'=' * 80}")
        
        # 运行该提示词的所有测试用例
        results = await PromptEvaluator.batch_test(prompt_id)
        
        if not results:
            print("  [INFO] 没有相关测试用例")
            continue
        
        for result in results:
            total_tests += 1
            
            if 'error' in result:
                print(f"  ✗ 测试失败: {result.get('error')}")
                failed_tests += 1
                continue
            
            if 'info' in result:
                print(f"  [INFO] {result.get('info')}")
                continue
            
            test_case_name = result.get('test_case_name', 'Unknown')
            passed = result.get('passed', False)
            auto_metrics = result.get('auto_metrics', {})
            
            if passed:
                print(f"  ✓ 测试通过: {test_case_name}")
                passed_tests += 1
            else:
                print(f"  ✗ 测试失败: {test_case_name}")
                failed_tests += 1
            
            # 显示自动化指标
            if auto_metrics:
                passed_checks = auto_metrics.get('passed_checks', [])
                failed_checks = auto_metrics.get('failed_checks', [])
                pass_rate = auto_metrics.get('pass_rate', 0)
                
                print(f"    通过率: {pass_rate * 100:.1f}%")
                
                if passed_checks:
                    print(f"    通过检查: {', '.join(passed_checks)}")
                
                if failed_checks:
                    print(f"    失败检查: {', '.join(failed_checks)}")
            
            # 显示输出预览（前200字符）
            output_content = result.get('output_content', '')
            if output_content:
                preview = output_content[:200] + ('...' if len(output_content) > 200 else '')
                print(f"    输出预览: {preview}")
    
    # 总结
    print(f"\n{'=' * 80}")
    print("测试总结")
    print(f"{'=' * 80}")
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests} ({passed_tests / total_tests * 100:.1f}%)" if total_tests > 0 else "通过: 0")
    print(f"失败: {failed_tests} ({failed_tests / total_tests * 100:.1f}%)" if total_tests > 0 else "失败: 0")
    print(f"{'=' * 80}")


async def run_specific_test(prompt_id: int, test_case_id: int):
    """运行指定的测试"""
    print(f"\n运行测试: Prompt ID={prompt_id}, Test Case ID={test_case_id}")
    
    result = await PromptEvaluator.run_test_case(prompt_id, test_case_id)
    
    if 'error' in result:
        print(f"✗ 测试失败: {result['error']}")
        return
    
    print(f"\n测试用例: {result.get('test_case_name')}")
    print(f"是否通过: {'✓ 是' if result.get('passed') else '✗ 否'}")
    
    # 显示自动化指标
    auto_metrics = result.get('auto_metrics', {})
    if auto_metrics:
        print(f"\n自动化指标:")
        for key, value in auto_metrics.items():
            if key not in ['passed_checks', 'failed_checks']:
                print(f"  {key}: {value}")
        
        passed_checks = auto_metrics.get('passed_checks', [])
        failed_checks = auto_metrics.get('failed_checks', [])
        
        if passed_checks:
            print(f"\n通过的检查:")
            for check in passed_checks:
                print(f"  ✓ {check}")
        
        if failed_checks:
            print(f"\n失败的检查:")
            for check in failed_checks:
                print(f"  ✗ {check}")
    
    # 显示完整输出
    output_content = result.get('output_content', '')
    if output_content:
        print(f"\nLLM输出:")
        print("-" * 80)
        print(output_content)
        print("-" * 80)
    
    # 显示期望输出
    expected_output = result.get('expected_output', '')
    if expected_output:
        print(f"\n期望输出:")
        print(expected_output)


def main():
    """主函数"""
    if len(sys.argv) > 2:
        # 运行指定测试
        try:
            prompt_id = int(sys.argv[1])
            test_case_id = int(sys.argv[2])
            asyncio.run(run_specific_test(prompt_id, test_case_id))
        except ValueError:
            print("用法: python run_prompt_tests.py [prompt_id test_case_id]")
            return 1
    else:
        # 运行所有测试
        asyncio.run(run_all_tests())
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

