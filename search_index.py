import json
import re
from collections import defaultdict
from hdfs import InsecureClient

# HDFS 配置
HDFS_HOST = 'http://192.168.100.133:9870'
HDFS_INDEX_PATH = '/user/kangning/inverted_index.json'
HDFS_INPUT_PATH = '/user/kangning/input.json'
client = InsecureClient(HDFS_HOST, user='kangning', timeout=600)  # 设置超时时间为600秒

# 从HDFS读取倒排索引
with client.read(HDFS_INDEX_PATH, encoding='utf-8') as reader:
    inverted_index = json.load(reader)

# 从HDFS读取输入文件
with client.read(HDFS_INPUT_PATH, encoding='utf-8') as reader:
    articles = json.load(reader)

# 查询函数
def search(query):
    words = re.findall(r'\w+', query.lower())
    result = []
    for word in words:
        if word in inverted_index:
            article_list = inverted_index[word]
            for article_data in article_list:
                article_id = article_data['uuid']
                article = next((item for item in articles if item['uuid'] == article_id), None)
                if article:
                    detailed_result = {
                        'uuid': article['uuid'],
                        'title': article['title'],
                        'author': article['author'],
                        'url': article['url'],
                        'text': article['text']
                    }
                    result.append(detailed_result)
    return result

# 示例查询
if __name__ == '__main__':
    query = input("请输入搜索关键词：")
    result = search(query)
    for res in result:
        print(f"文章ID: {res['uuid']}, 标题: {res['title']}, 作者: {res['author']}, URL: {res['url']}, 全文: {res['text']}")

