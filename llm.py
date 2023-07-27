import os

from dotenv import load_dotenv
from flask import Blueprint, render_template, request, jsonify
from langchain import PromptTemplate
from langchain.callbacks import get_openai_callback
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Milvus

from dao.user_quest_history import insert_user_quest_history
from docIndex import main, main_knowledge
from function_calling import search_schedule

llm_blue = Blueprint('llm', __name__)

load_dotenv(".env")
MILVUS_HOST = os.environ.get('MILVUS_HOST')
MILVUS_PORT = os.environ.get('MILVUS_PORT')
target_source_chunks = int(os.environ.get('TARGET_SOURCE_CHUNKS', 4))

# openaiLlm = OpenAI(model_name="text-davinci-003", max_tokens=1024, temperature=0.9)
openaiLlm = OpenAI(model_name="gpt-3.5-turbo", max_tokens=1024, temperature=0.9)


@llm_blue.route("/completion/<question>")
def completion(question: str) -> str:
    if question.find("班次") != -1:
        return search_schedule(question)

    res = ans(question, "IT")

    if res.find('根据已知信息无法回答该问题') != -1:
        res = openaiLlm(question)
        res = res + "\n\n" + "--来自OpenAI"
    else:
        res = res + "\n\n" + "--来自IT知识库"

    print("question:[%s], answer:[%s]" % (question, res))
    return res


@llm_blue.route("/load_local_source")
def load_local_source_to_milvus() -> str:
    main("IT")
    return 'OK'


@llm_blue.route('/training', methods=['GET', 'POST'])
def training():
    if request.method == 'POST':
        # 获取文本内容
        name = request.form.get('name')
        main_knowledge(name)
        return jsonify({'message': '训练成功！', 'knowledge': name})

    return render_template('index.html')


def load_data_to_milvus():
    # 获取并加载文档
    loader = TextLoader('D:\\bstPorject\\techplatform\\langchain-demo2\\c001.txt', encoding='utf-8')
    docs = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1024, chunk_overlap=0)
    docs = text_splitter.split_documents(docs)

    # 转换为向量嵌入并保存到向量存储中
    # OpenAI(model_name="gpt-3.5-turbo", max_tokens=1024, temperature=0.9)
    embeddings = OpenAIEmbeddings()
    vector_store = Milvus.from_documents(
        docs,
        collection_name='app02',
        embedding=embeddings,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT}
    )


@llm_blue.route("/ans/<collectionName>/<question>")
def ans(question: str, collectionName: str) -> str:
    # 设置跟踪
    with get_openai_callback() as cb:
        embeddings = OpenAIEmbeddings()
        vector_store = Milvus(
            collection_name=collectionName,
            embedding_function=embeddings,
            connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT}
        )
        retriever = vector_store.as_retriever(search_kwargs={"k": target_source_chunks})

        # llm = OpenAI(model_name="gpt-3.5-turbo", max_tokens=1024, temperature=0.9)

        prompt_template = """基于以下已知信息，简洁和专业的来回答用户的问题。
                如果无法从中得到答案，请说 "根据已知信息无法回答该问题"，不允许在答案中添加编造成分，答案请使用中文。
                已知内容:
                {context}
                问题:
                {question}"""

        promptA = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        chain_type_kwargs = {"prompt": promptA}
        qa = RetrievalQA.from_chain_type(llm=openaiLlm, retriever=retriever, chain_type="stuff",
                                         chain_type_kwargs=chain_type_kwargs, return_source_documents=True)

        res = qa(question)
        answer, docs = res['result'], res['source_documents']
        # print(answer)
        # arr = [question]
        # num_tokens = num_tokens_from_messages(arr)
        #
        # arr2 = [answer]
        # num_tokens2 = num_tokens_from_messages(arr2)

        # num_tokens3 = num_tokens_from_messages(docs)
        # print("source成本:" + str(num_tokens3))
        # print("问题成本：计算token数为：" + str(num_tokens))
        # print("答案成本：计算token数为：" + str(num_tokens2))
        print("question:[%s], answer:[%s]" % (question, answer))
        print(cb)
        # print("----------------打印具体成本信息-------------")
        # print(cb.total_tokens)
        # print(cb.prompt_tokens)
        # print(cb.completion_tokens)
        # print(cb.successful_requests)
        # print(cb.total_cost)

        insert_user_quest_history(user_no='1001', request_content=question, response_content=answer,
                                total_tokens=cb.total_tokens, prompt_tokens=cb.prompt_tokens,
                                completion_tokens=cb.completion_tokens, successful_requests=cb.successful_requests,
                                total_cost=cb.total_cost)
        return answer


@llm_blue.route('/ansQ', methods=['GET', 'POST'])
def ansQ():
    if request.method == 'POST':
        # 获取文本内容
        name = request.form.get('name')
        text = request.form.get('text')
        answer = ans(text, name)
        if answer.find('根据已知信息无法回答该问题') != -1:
            answer = openaiLlm(text)
            answer = answer + "\n\n" + "-- 来自OpenAI"
        else:
            answer = answer + "\n\n" + "-- 来自" + name + "知识库"
        return jsonify({'message': answer})

    return render_template('index.html')
