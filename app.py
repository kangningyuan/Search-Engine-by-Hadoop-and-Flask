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

