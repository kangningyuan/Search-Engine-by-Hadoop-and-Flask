#!/usr/bin/python3
# -*-coding:utf-8 -*
import json
import re
import sys

def extract_articles(data):
    """递归提取JSON中的文章列表"""
    articles = []
    if isinstance(data, dict):
        # 如果是字典，检查是否有文章的相关字段
        if 'uuid' in data and 'title' in data and 'author' in data:
            articles.append(data)
        else:
            # 递归处理嵌套结构
            for key, value in data.items():
                articles.extend(extract_articles(value))
    elif isinstance(data, list):
        # 如果是列表，递归处理每个元素
        for item in data:
            articles.extend(extract_articles(item))
    return articles

def mapper():
    input_data = sys.stdin.read()
    try:
        data = json.loads(input_data)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # 提取文章列表
    articles = extract_articles(data)

    # 用一个字典存储文章信息，避免重复
    article_info = {}

    for article in articles:
        article_id = article.get('uuid', '')
        title = article.get('title', '')
        author = article.get('author', '')
        
        # 将文章信息存储在字典中，避免重复输出
        if article_id not in article_info:
            article_info[article_id] = {
                'uuid': article_id,
                'title': title,
                'author': author
            }

        # 提取单词并输出单词与文章的映射
        words = re.findall(r'\w+', f"{title} {author}".lower())
        for word in words:
            # 输出格式：word <tab> article_id, title, author
            print(f"{word}\t{json.dumps(article_info[article_id])}")

if __name__ == "__main__":
    mapper()

