## Search Engine by Hadoop and Flask

### 0. Introduction
This project is a technology article search engine based on Hadoop and Flask framework. Using Hadoop MapReduce to build inverted index, Flask to create a user-friendly web search interface, and HDFS to store index and database.

#### 0.1 Directory Structure

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
  - This is our database stored in JSON format, containing information such as article ID, link, author, and the original text.  
  - The database can be obtained through public datasets or web scraping. In this project, we referenced the open-source [Webz.io News Dataset Repository](https://github.com/Webhose/free-news-datasets/tree/master), integrating a portion of technology-related news articles into one `input.json` file.

- **inverted_index.json** 
  - This is our index file built based on the inverted index.

- **search_index.py** 
  - The search functionality API, implemented in Python.

- **app.py** 
  - The search engine, implemented using Python and the Flask library.

- **templates/** 
  - Templates for the Web UI interface, using HTML.

- **mapreduce/** 
  - Contains `mapper.py` and `reducer.py`, used to generate the inverted index when dealing with a large database using the MapReduce framework.

- **build_index.py** 
  - When you don't want to use MapReduce to build an inverted index, use build_index.py to build the index on your local machine 



### 1. Environment Setup
Our project runs on a Hadoop cluster consisting of four Ubuntu nodes (node1 as the master and node2~4 as the slaves).

**Be sure to set the parameters according to your own situation**

#### 1.1 Installing Hadoop-Related Packages

When using Python for MapReduce jobs in a Hadoop cluster, we need to ensure the following tools are installed:

1. **Hadoop**: Hadoop cluster is already installed.
2. **Python**: Ensure Python is installed in your environment (e.g., Python 3.8).
3. **Hadoop Streaming**: Hadoop Streaming allows us to write Mappers and Reducers in any programming language, including Python.

Usually, Hadoop Streaming is included in the Hadoop installation package, so you can use it directly. The installation process of Hadoop is complex and not the focus of this project, so it is omitted here.

#### 1.2 Installing Python Packages
Installing Python and pip on Linux is quite simple. Here are some basic steps:

**Update the package list**: Enter the following command and press Enter:
```bash
sudo apt update
```

**Install Python**: Enter the following command and press Enter:
```bash
sudo apt install python3
```

**Install pip**:
If pip is not installed, you can install it using the following command:
```bash
sudo apt install python3-pip
```

**Install hdfs**: If you have not installed the `hdfs` package to interact with HDFS, install it using the following command:
```bash
pip install hdfs
```

**Verify the installation**: Enter the following commands to confirm Python and pip are installed correctly:
```bash
python3 --version
python3 -m pip --version
```


### 2. Building Inverted Index with Python and Hadoop Streaming

#### 2.1 `mapper.py` - Mapper Program
This Python script will act as the Mapper, running on each node in the Hadoop cluster. It will read the JSON data of each article, extract fields such as `title` and `author`, and generate `(word, article_info)` key-value pairs.


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

#### 2.2 `reducer.py` - Reducer Program
The Reducer will receive `(word, article_info)` key-value pairs and merge the article IDs of the same keyword into a collection, ultimately generating the inverted index.

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

#### 2.3 Ensure Scripts Have Execute Permissions
Before executing the scripts, ensure they have execute permissions:

```bash
chmod +x mapper.py reducer.py
```

#### 2.4 Running MapReduce Jobs with Hadoop Streaming

Upload the `input.json` data to HDFS and store it in the `/user/kangning/data/` path. The output results will be stored in `/user/kangning/output/`.

1. **Upload data to HDFS** (if not uploaded yet):

   ```bash
   hadoop fs -put /local/path/to/data /user/kangning/data
   ```

2. **Run Hadoop Streaming Job**:

   Use the following command to run the MapReduce job:

   ```bash
   hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
       -input /user/kangning/data/input.json \
       -output /user/kangning/output \
       -mapper "python3 /path/to/mapper.py" \
       -reducer "python3 /path/to/reducer.py"
   ```

   **Explanation:**
   - `-input /user/kangning/data`: Specifies the input data directory.
   - `-output /user/kangning/output`: Specifies the output result directory.
   - `-mapper "python3 /path/to/mapper.py"`: Specifies the Python Mapper script.
   - `-reducer "python3 /path/to/reducer.py"`: Specifies the Python Reducer script.
   - `-D mapreduce.job.reduces=1`: Sets the number of Reducers (usually use one Reducer to merge all results).

   We also provide a `run.sh` script, which you can run directly after modifying the script information:
   ```bash
   bash mapreduce/run.sh
   ```

3. **View Output Results**:

   After completing the MapReduce job, you can view the inverted index results using the following command:

   ```bash
   hadoop fs -cat /user/kangning/output/part-00000
   ```

   The output should look like this:

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

   Each word and its corresponding article info list will be saved as an inverted index, with the info list containing key details such as the article ID, title, and author.

   Save the output index:
   ```bash
   hadoop fs -cp /user/kangning/output/part-00000 /user/kangning/inverted_index.json
   ```

Since our input file is not large, the output index file is only one part. However, if the input file is large, it might be saved as multiple parts, which may require manual merging or reading index files in chunks in subsequent indexing.


### 3. Implementing Search Functionality Using Flask Web Application

After constructing the inverted index with the MapReduce job, we can implement the search functionality using Flask. Ensure the database and index files are stored in HDFS, as the subsequent implementation relies on HDFS for storing these files.

#### 3.1 search_index.py
This is the implementation of the search functionality API. Based on the input keywords, it reads the database and index files in HDFS and returns the article information containing the keywords.

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
Using Flask, build the Web UI interface for the search engine.
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

#### 3.3 HTML Templates

- **`templates/index.html`**

- **`templates/results.html`**


### 4. Start the Flask Application

You can start the Flask application to implement the frontend search functionality.

1. Ensure the Flask service scripts (`app.py`, `search_index.py`) and HTML template files (`index.html` and `results.html`) are in the appropriate directories (as shown in the directory structure at the beginning).

2. Ensure the relevant database and index files are in HDFS (`input.json` and `inverted_index.json`).
   - You can skip the indexing step and directly upload the provided database and index to your HDFS.
   ```bash
   hdfs dfs -put input.json /user/kangning/input.json
   hdfs dfs -put inverted_index.json /user/kangning/inverted_index.json
   ```

3. Start the Flask application in the background:
```bash
nohup python3 app.py &
```

4. Open a browser and visit `http://node_IP:5000/`. You will see an input box and search button, allowing users to enter query terms and get results.

5. Enter the query terms (for example, "football" or "ea"), and then click the "Search" button. You will see a list of articles related to the query. Each article will display its `title`, `author`, and a collapsible body text. Clicking on the article title will take you directly to the original link.

### 5. Summary

Using the Hadoop framework, we accomplished the following two main parts:

1. **Constructing the Inverted Index (Based on Hadoop MapReduce)**:
   - We used **Hadoop Streaming** and **Python** to write `mapper.py` and `reducer.py`, processing JSON data stored in HDFS, extracting keywords, and generating the inverted index.
   - Leveraged Hadoop's distributed computing capabilities to map keywords to article info from JSON data, built the inverted index, and saved the results in HDFS.

2. **Creating a Web Search Service Using Flask (Based on HDFS)**:
   - Built a simple Web application using **Flask** that allows users to enter query terms and return matching articles based on the inverted index.
   - Displayed detailed information about the articles (like `title`, `author`, body text, and link) on the search results page.
