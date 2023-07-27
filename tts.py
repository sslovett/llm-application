import edge_tts
import asyncio
from flask import Blueprint
import random

llm_blue = Blueprint('tts', __name__)

async def communicate(text: str) -> str:
    voice = 'zh-CN-YunxiNeural'  # 语音
    output = 'voice/' + str(random.randint(1, 5)) + ".mp3"  # 输出文件
    rate = '-4%'  # 语速
    volume = '+0%'  # 语量
    tts = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
    await tts.save(output)
    return output


@llm_blue.route("/get/<text>")
def get(text: str) -> str:
    return communicate(text)

if __name__ == '__main__':
    asyncio.run(communicate("新时代以来，以习近平同志为主要代表的中国共产党人，"
                            "坚持把马克思主义基本原理同中国具体实际相结合、同中华优秀传统文化相结合，"
                            "科学回答中国之问、世界之问、人民之问、时代之问，"
                            "在伟大实践中创立了习近平新时代中国特色社会主义思想。"))
