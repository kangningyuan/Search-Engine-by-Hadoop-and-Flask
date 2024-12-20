#!/usr/bin/python3
# -*-coding:utf-8 -*
import sys
import json
from collections import defaultdict

def reducer():
    inverted_index = defaultdict(list)

    for line in sys.stdin:
        try:
            word, article_data = line.strip().split('\t', 1)
            article = json.loads(article_data)  # 解析为 JSON 对象
            article_id = article['uuid']
            title = article['title']
            author = article['author']
            inverted_index[word].append({'uuid': article_id, 'title': title, 'author': author})
        except Exception as e:
            print(f"Error processing line: {line}. Error: {e}", file=sys.stderr)

    # 输出 JSON 格式的倒排索引
    print(json.dumps(inverted_index, ensure_ascii=False, indent=4))

if __name__ == "__main__":
    reducer()

