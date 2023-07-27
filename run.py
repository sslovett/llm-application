# coding:utf-8‘
import os
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_bootstrap import Bootstrap
from llm import llm_blue
from weixin import wx_blue, refresh_access_token
from test1.stream_print import test_blue, StreamToWeb
from dotenv import load_dotenv
from function_calling  import search_schedule
import asyncio

app = Flask(__name__)
bootstrap = Bootstrap(app)
# 将各模块蓝图注册到app中
app.register_blueprint(llm_blue, url_prefix='/llm')
app.register_blueprint(wx_blue, url_prefix='/wx')
app.register_blueprint(test_blue, url_prefix='/test')

load_dotenv(".env")
KNOWLEDGE_FOLDER = os.environ.get('KNOWLEDGE_FOLDER')


@app.route("/")
def root():
    return render_template('index.html')

@app.route("/test")
def test():
    return render_template('print_stream.html')

@app.route("/print_stream")
def print_stream():
    question = request.args.get('question')
    ans = search_schedule(question)

    return Response(stream_with_context(ans), content_type='text/event-stream')


@app.route('/upload', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 获取文本内容
        text = request.form.get('name')
        # 获取文件内容
        file = request.files.get('file')
        if file:
            # 保存文件到服务器
            # file.save(file.filename)
            # file_path = file.filename
            filename = file.filename
            file.save(os.path.join(KNOWLEDGE_FOLDER,text, filename))
            file_path = os.path.join(KNOWLEDGE_FOLDER,text, filename)
        else:
            file_path = None

        # 处理文本和文件内容（这里仅作示例）
        # 在实际应用中，你可以根据需求对文本和文件进行进一步处理或保存到数据库

        return jsonify({'message': '提交成功！', 'fileServicePath': file_path})

    return render_template('index.html')


if __name__ == '__main__':
    # 刷新accessToken
    refresh_access_token()
    app.run(host="0.0.0.0", port=8080)
