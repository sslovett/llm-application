from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from dotenv import load_dotenv
from langchain.schema import HumanMessage
from langchain.callbacks.manager import CallbackManager
from flask import Blueprint, Response, request, stream_with_context
import os
import time
import asyncio


test_blue = Blueprint('test', __name__)

# os.environ["OPENAI_API_KEY"] = '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'
# os.environ["OPENAI_API_BASE"] = 'http://43.153.41.75:9000/v1'

load_dotenv(".env")


class StreamToWeb(StreamingStdOutCallbackHandler):
    def __init__(self):
        self.tokens = []
        # 记得结束后这里置true
        self.finish = False

    def on_llm_new_token(self, token: str, **kwargs):
        self.tokens.append(token)

    def on_llm_end(self, response: any, **kwargs: any) -> None:
        self.finish = 1

    def on_llm_error(self, error: Exception, **kwargs: any) -> None:
        print(str(error))
        self.tokens.append(str(error))

    def generate_tokens(self):
        while not self.finish or self.tokens:
            if self.tokens:
                data = self.tokens.pop(0)
                yield f"data: {data}\n\n"
            else:
                pass


if __name__ == '__main__':
    # llm = ChatOpenAI(model_name="gpt-3.5-turbo",
    #                  streaming=True,
    #                  callback_manager=CallbackManager([StreamToWeb()]),
    #                  verbose=True,
    #                  temperature=0
    #                  )
    #
    # message = [HumanMessage(content="请介绍一下周杰伦")]

    llm = OpenAI(model_name="gpt-3.5-turbo",
                 streaming=True,
                 callback_manager=CallbackManager([StreamToWeb()]),
                 verbose=True,
                 temperature=0
                 )

    resp = llm("请介绍一下周杰伦")
