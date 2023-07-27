import threading

from langchain.tools import BaseTool
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.tools import format_tool_to_openai_function
from langchain.agents import AgentType, initialize_agent
from langchain.callbacks.manager import CallbackManager
from pydantic import BaseModel, Field
from typing import Optional, Type
from datetime import date
from test1.stream_print import StreamToWeb
import requests
import json
import os


class ScheduleCheckInput(BaseModel):
    drv_date: str = Field(..., description="日期，请格式化为yyyy-mm-dd，日期当天从%s开始计算" % date.today())
    start_name: str = Field(..., description="起点")
    target_name: str = Field(..., description="终点")


class BusTool(BaseTool):
    name = "query_bus_by_date"
    description = "根据日期查询起止点的班次信息"

    def _run(self, drv_date, start_name, target_name):
        start_no_dic = {"成都": "cbcz"}
        url = "https://innerapiv2.scqcp.cn/ticket"
        data = {"pubRequest": {
                        "encryType": "0",
                        "version": "3.0",
                        "token": "678910",
                        "method": "getSchedule"
                    },
                "body": {
                    "startNo": "%s",
                    "startType": "2",
                    "targetNo": "%s",
                    "targetType": "0",
                    "drvTime": "%s",
                    "isCache": "1"}
                }
        json_data = json.dumps(data) % (start_no_dic[start_name], target_name, drv_date)
        # print(json_data)
        response = requests.post(url, data=json_data.encode("utf-8"))
        return response.json().get("body").get("data")

    def _arun(self):
        raise NotImplementedError("This tool does not support async1")

    args_schema: Optional[Type[BaseModel]] = ScheduleCheckInput


def search_schedule(query: str) -> str:
    stream_to_web = StreamToWeb()
    llm = ChatOpenAI(temperature=0,
                     model="gpt-3.5-turbo-0613",
                     callback_manager=CallbackManager([stream_to_web]),
                     streaming=True
                     )
    bus_tools = [BusTool()]
    open_ai_agent = initialize_agent(bus_tools,
                                     llm,
                                     agent=AgentType.OPENAI_FUNCTIONS,
                                     verbose=True)
    chain_thread = threading.Thread(target=process_query,
                                    kwargs={"question": query,
                                            "open_ai_agent": open_ai_agent})
    chain_thread.start()
    resp = stream_to_web.generate_tokens()
    return resp


def process_query(question, open_ai_agent):
    open_ai_agent.run(question)


if __name__ == '__main__':
    search_schedule("请帮我查询13号成都到绵阳的班次信息")

