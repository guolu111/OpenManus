#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek思考经验包检索工具
用法:
    python search.py --keyword "任务拆解"
    python search.py --category "需求分析"
    python search.py --random 5
    python search.py --stats
"""

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

# 知识库目录
KB_DIR = Path(__file__).parent
EXPERIENCE_TXT = KB_DIR / "DeepSeek思考经验包.txt"
EXPERIENCE_JSON = KB_DIR / "DeepSeek思考经验包.json"

# 分类列表
CATEGORIES = ["需求分析", "任务拆解", "决策判断", "错误处理", "回复组织", "其他"]


def load_experiences():
    """加载思考经验，返回分类后的列表"""
    experiences = {cat: [] for cat in CATEGORIES}
    
    if not EXPERIENCE_TXT.exists():
        print(f"错误: 找不到 {EXPERIENCE_TXT}")
        return experiences
    
    with open(EXPERIENCE_TXT, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 按分类分割
    current_cat = None
    current_item = []
    
    for line in content.split("\n"):
        # 检测分类标题
        cat_match = re.match(r"## 【(.+?)】", line)
        if cat_match:
            # 保存上一个分类的最后一个item
            if current_cat and current_item:
                experiences[current_cat].append("\n".join(current_item))
            current_cat = cat_match.group(1)
            if current_cat not in experiences:
                experiences[current_cat] = []
            current_item = []
            continue
        
        # 检测新示例
        if line.startswith("--- 示例"):
            if current_cat and current_item:
                experiences[current_cat].append("\n".join(current_item))
            current_item = [line]
            continue
        
        # 普通内容
        if current_cat:
            current_item.append(line)
    
    # 保存最后一个item
    if current_cat and current_item:
        experiences[current_cat].append("\n".join(current_item))
    
    return experiences


def search_by_keyword(experiences, keyword, max_results=5):
    """按关键词搜索"""
    results = []
    keyword_lower = keyword.lower()
    
    for cat, items in experiences.items():
        for item in items:
            if keyword_lower in item.lower():
                # 提取关键词上下文
                lines = item.split("\n")
                title = lines[0] if lines else "无标题"
                results.append({
                    "category": cat,
                    "title": title,
                    "content": item[:2000]  # 限制长度
                })
                if len(results) >= max_results:
                    return results
    
    return results


def search_by_category(experiences, category, max_results=5):
    """按分类查询"""
    if category not in experiences:
        print(f"错误: 找不到分类 '{category}'")
        print(f"可用分类: {', '.join(experiences.keys())}")
        return []
    
    items = experiences[category]
    if not items:
        print(f"分类 '{category}' 暂无内容")
        return []
    
    # 随机抽取
    selected = random.sample(items, min(max_results, len(items)))
    results = []
    for item in selected:
        lines = item.split("\n")
        title = lines[0] if lines else "无标题"
        results.append({
            "category": category,
            "title": title,
            "content": item[:2000]
        })
    
    return results


def random_samples(experiences, count=5):
    """随机抽取示例"""
    all_items = []
    for cat, items in experiences.items():
        for item in items:
            all_items.append((cat, item))
    
    if not all_items:
        return []
    
    selected = random.sample(all_items, min(count, len(all_items)))
    results = []
    for cat, item in selected:
        lines = item.split("\n")
        title = lines[0] if lines else "无标题"
        results.append({
            "category": cat,
            "title": title,
            "content": item[:2000]
        })
    
    return results


def show_stats(experiences):
    """显示统计信息"""
    print("=" * 60)
    print("DeepSeek思考经验包统计")
    print("=" * 60)
    
    total = 0
    for cat, items in experiences.items():
        count = len(items)
        total += count
        print(f"  {cat}: {count} 条")
    
    print("-" * 60)
    print(f"  总计: {total} 条")
    print("=" * 60)
    
    # 文件大小
    print("\n文件大小:")
    for f in KB_DIR.glob("*"):
        if f.is_file():
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  {f.name}: {size_mb:.2f} MB")


def print_result(result, index):
    """打印单个搜索结果"""
    print(f"\n{'=' * 60}")
    print(f"【结果 {index}】分类: {result['category']}")
    print(f"标题: {result['title']}")
    print("-" * 60)
    print(result['content'])
    if len(result['content']) >= 2000:
        print("... (内容已截断，完整内容请查看源文件)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="DeepSeek思考经验包检索工具")
    parser.add_argument("--keyword", "-k", help="按关键词搜索")
    parser.add_argument("--category", "-c", help=f"按分类查询，可选: {', '.join(CATEGORIES)}")
    parser.add_argument("--random", "-r", type=int, default=5, help="随机抽取示例数量")
    parser.add_argument("--stats", "-s", action="store_true", help="显示统计信息")
    parser.add_argument("--max", "-m", type=int, default=5, help="最大结果数")
    
    args = parser.parse_args()
    
    # 加载经验
    print("正在加载思考经验包...")
    experiences = load_experiences()
    
    if args.stats:
        show_stats(experiences)
        return
    
    if args.keyword:
        print(f"\n正在搜索关键词: {args.keyword}")
        results = search_by_keyword(experiences, args.keyword, args.max)
    elif args.category:
        print(f"\n正在查询分类: {args.category}")
        results = search_by_category(experiences, args.category, args.max)
    else:
        print(f"\n随机抽取 {args.random} 条示例")
        results = random_samples(experiences, args.random)
    
    if not results:
        print("未找到匹配的结果")
        return
    
    print(f"\n找到 {len(results)} 条结果:")
    for i, result in enumerate(results, 1):
        print_result(result, i)


if __name__ == "__main__":
    main()
