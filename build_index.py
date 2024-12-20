import json
import re
from collections import defaultdict
from hdfs import InsecureClient

# HDFS 配置
HDFS_HOST = 'http://192.168.100.133:9870'
HDFS_INPUT_PATH = '/user/kangning/input.json'
HDFS_OUTPUT_PATH = '/user/kangning/inverted_index.json'
client = InsecureClient(HDFS_HOST, user='kangning', timeout=600)  # 设置超时时间为600秒

# 从HDFS读取输入文件
with client.read(HDFS_INPUT_PATH, encoding='utf-8') as reader:
    articles = json.load(reader)

# 初始化倒排索引
inverted_index = defaultdict(list)

# 构建倒排索引
for article in articles:
    article_id = article.get('uuid', '')
    title = article.get('title', '')
    author = article.get('author', '')
    print(article_id)
    article_data = {
        'uuid': article_id,
        'title': title,
        'author': author
    }

    # 提取单词
    words = re.findall(r'\w+', f"{title} {author}".lower())

    for word in words:
        inverted_index[word].append(article_data)

# 将倒排索引保存到HDFS
with client.write(HDFS_OUTPUT_PATH, encoding='utf-8') as writer:
    json.dump(inverted_index, writer, ensure_ascii=False, indent=4)

print("倒排索引构建完成，并已保存到 HDFS 中。")

