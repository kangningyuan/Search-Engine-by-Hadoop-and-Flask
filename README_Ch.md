## Search Engine by Hadoop and Flask

### 0. 说明
本项目是一个基于Hadoop和Flask框架的科技文章搜索引擎。使用Hadoop MapReduce构建倒排索引，使用Flask创建用户友好的web搜索界面，使用HDFS存储索引和数据库。

#### 0.1 目录结构

```
./
├─ app.py
├─ build_index.py
├─ input.json
├─ inverted_index.json
├─ search_index.py
├─ templates/
│  ├─ index.html
│  └─ results.html
└─ mapreduce/
   ├─ mapper.py
   ├─ reducer.py
   └─ run.sh
```

 - **input.json**  
     - 这是我们的数据库，以json的格式存储，保存了文章的ID、链接、作者、原文等信息  
     - 数据库可以通过公开数据集或者网络爬虫获取，本项目中的数据参考了开源的数据库[Webz.io News Dataset Repository](https://github.com/Webhose/free-news-datasets/tree/master)，将其中一部分关于科技类的新闻文本整合为一个input.json

 - **inverted_index.json** 
     -  这是我们根据倒排索引建立的索引文件  
 - **search_index.py** 
     -  搜索功能API，使用Python语言  
 - **app.py** 
     -  搜索引擎，借助Python以及flask库实现  
 - **templates/** 
     -  WebUI界面的模板，使用HTML语言  
 - **mapreduce/** 
     -  包含mapper.py和reducer.py，用于在数据库较大的情况下使用Mapreduce框架生成倒排索引
 - **build_index.py** 
     -  如果不想使用MapReduce建立倒排索引，可以使用build_index.py在本地机器上建立索引


### 1. 环境准备
我们的项目运行在由4台Ubuntu节点组成的Hadoop集群上（node1为主节点，node2~4为从节点）。  

**后续过程中请根据你的实际情况设置有关参数**

#### 1.1 安装 Hadoop 相关包

在 Hadoop 集群中使用 Python 进行 MapReduce 作业时，我们需要确保以下工具已安装：

1. **Hadoop**：Hadoop 集群已经安装好。
2. **Python**：确保你的环境中已经安装了 Python （例如Python 3.8）
3. **Hadoop Streaming**：Hadoop Streaming 是允许我们通过任何编程语言（包括 Python）来编写 Mapper 和 Reducer 的工具。

通常，Hadoop Streaming 已经包含在 Hadoop 的安装包中，你可以直接使用。Hadoop的安装过程较为繁琐，也不是本项目关注的重点，所有我们在此省略

#### 1.2 安装 Python 相关包
在Linux上安装Python和pip其实很简单。以下是一些基本步骤：

**更新软件包列表**：输入以下命令并按回车：
   ```bash
   sudo apt update
   ```

**安装Python**：输入以下命令并按回车：
   ```bash
   sudo apt install python3
   ```

**安装pip**：
   如果pip未安装，你可以使用以下命令安装：
   ```bash
   sudo apt install python3-pip
   ```

**安装hdfs**：如果你尚未安装 `hdfs` 包来与 HDFS 进行交互，请通过以下命令安装：

```bash
pip install hdfs
```
**验证安装**：输入以下命令来确认Python和pip是否已正确安装：
   ```bash
   python3 --version
   python3 -m pip --version
   ```


### 2. 使用 Python 和 Hadoop Streaming 构建倒排索引

#### 2.1 `mapper.py` - Mapper 程序

这个 Python 脚本将作为 Mapper，在 Hadoop 中每个节点运行。它会读取每篇文章的 JSON 数据，提取 `title`、`author`等字段，生成 `(word, article_info)` 键值对。

```python
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
```

#### 2.2 `reducer.py` - Reducer 程序

Reducer 将接收到 `(word, article_info)` 键值对，并将同一关键词的文章 ID 合并为一个集合，最终生成倒排索引。

```python
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
```

#### 2.3 确保脚本具有执行权限

在执行脚本之前，确保它们具有执行权限：

```bash
chmod +x mapper.py reducer.py
```

#### 2.4 使用 Hadoop Streaming 执行 MapReduce 作业

将 input.json 数据上传到 HDFS，并且存储在 `/user/kangning/data/` 路径下，输出结果将存储在 `/user/kangning/output/`。

1. **上传数据到 HDFS**（如果尚未上传）：

   ```bash
   hadoop fs -put /local/path/to/data /user/kangning/data
   ```

2. **运行 Hadoop Streaming 作业**：

   使用以下命令运行 MapReduce 作业：

   ```bash
   hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
       -input /user/kangning/data/input.json \
       -output /user/kangning/output \
       -mapper "python3 /path/to/mapper.py" \
       -reducer "python3 /path/to/reducer.py"
   ```

   **解释：**
   - `-input /user/kangning/data`：指定输入数据目录。
   - `-output /user/kangning/output`：指定输出结果目录。
   - `-mapper "python3 /path/to/mapper.py"`：指定 Python Mapper 脚本。
   - `-reducer "python3 /path/to/reducer.py"`：指定 Python Reducer 脚本。
   - `-D mapreduce.job.reduces=1`：设置 Reducer 的数量（通常使用一个 Reducer 来合并所有结果）。

   我们也提供了run.sh的运行脚本，你也可以在修改脚本相应信息的情况下直接：
   ```bash
   bash mapreduce/run.sh
   ```

3. **查看输出结果**：

   完成 MapReduce 作业后，你可以使用以下命令查看倒排索引结果：

   ```bash
   hadoop fs -cat /user/kangning/output/part-00000
   ```

   输出应该类似于：

   ```
    "cache": [
        {
            "uuid": "dce23adb...",
            "title": "Mastering...",
            "author": "Urfanito"
        }
    ],
    "clause": [
        {
            "uuid": "67ebc7...",
            "title": "Online Python Tutor...",
            "author": "Branding-C..."
        }
    ]
   ...
   ```

   每个单词及其对应的文章info列表将作为倒排索引保存，info列表中又包含了文章的ID、标题、作者等重点信息。

   将输出的索引另存  
   
     ```bash
   hadoop fs -cp /user/kangning/output/part-00000 /user/kangning/inverted_index.json

   ```

由于我们的输入文件不算大，所以输出的索引文件只有一个，但如果输入文件很大，可能会保存为多个part，这可能需要我们手动合并或者在后续索引中分块读取索引文件。

### 3. 使用 Flask Web 应用实现搜索功能

在 MapReduce 作业构建完倒排索引后，我们可以通过 Flask 来实现搜索功能。在此之前，需要保证数据库和索引文件都存储在HDFS上，后续功能的实现基于HDFS对数据库和索引文件的存储。

#### 3.1 search_index.py
这是搜索功能API的具体实现，根据输入的关键词，读取HDFS中的数据库和索引文件，返回包含关键词的文章信息。

```python
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
```

#### 3.2 app.py
借用flask，搭建搜索引擎的WebUI界面

```python
from flask import Flask, request, jsonify, render_template
import search_index

app = Flask(__name__)

# 首页路由
@app.route('/')
def home():
    return render_template('index.html')

# 搜索API
@app.route('/search', methods=['GET'])
def search_api():
    query = request.args.get('q')
    if query:
        result = search_index.search(query)
        return render_template('results.html', query=query, results=result)
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

#### 3.3 HTML 模板

- **`templates/index.html`**

- **`templates/results.html`**


### 4. 启动 Flask 应用

你可以启动 Flask 应用来实现前端搜索功能。

1. 确保 Flask 服务的脚本（`app.py`，`search_index.py`）以及 HTML 模板文件（`index.html` 和 `results.html`）位于合适的目录中（如开头文件结构所示）。

2. 确保相关数据库和索引文件位于HDFS上（`input.json `和`inverted_index.json`）
     - 你也可以跳过建立索引的步骤，直接将我们提供的数据库和索引上传到你的HDFS中
     ```bash
     hdfs dfs -put input.json /user/kangning/input.json
     hdfs dfs -put inverted_index.json /user/kangning/inverted_index.json
     ```

3. 通过后台运行的方式启动：

```bash
nohup python3 app.py &
```

4. 打开浏览器并访问 `http://node_IP:5000/`，你将看到一个输入框和搜索按钮，允许用户输入查询词然后得到查询结果。

5. 输入查询词（例如，`football` 或 `ea`），然后点击 "Search" 按钮。你将看到与该查询相关的文章列表。每篇文章将显示其 `title`、`author` 和可以展开的正文，点击文章标题可以直达原文链接。

### 5. 总结

我们使用Hadoop框架，主要完成了以下两大部分的工作：

1. **构建倒排索引（基于 Hadoop MapReduce）**：
   - 使用 **Hadoop Streaming** 和 **Python** 编写了 `mapper.py` 和 `reducer.py` 来处理存储在 HDFS 上的 JSON 数据，提取关键词并生成倒排索引。
   - 使用 Hadoop 的分布式计算能力将 JSON 数据中的关键词与文章 info 映射，构建倒排索引并将结果保存到 HDFS。

2. **使用 Flask 创建 Web 搜索服务（基于HDFS）**：
   - 使用 **Flask** 构建了一个简单的 Web 应用，允许用户输入查询词，然后根据倒排索引返回匹配的文章。
   - 文章的详细信息（如 `title`、`author` 正文，链接等）在搜索结果页面中展示。
