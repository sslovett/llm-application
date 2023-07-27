# token计算

import tiktoken


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("未找到型号。使用cl100k_base编码。")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print("GPT-3.5-turbo可能会随着时间的推移而变化。返回令牌数使用gpt-3.5-turbo-0301计算")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print("gpt-4可能会随着时间的推移而变化。返回令牌数使用gpt-4-0314计算")
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        # 带有角色和名称，需要额外添加
        # <|start|>{role/name}\n{content}<|end|> 4
        tokens_per_message = 0
        # 如果有名称，则省略该角色 -1
        tokens_per_name = 0
    elif model == "gpt-4-0314":
        # 如果有，设为3
        tokens_per_message = 0
        # 如果有，设为1
        tokens_per_name = 0
    else:
        #  https://github.com/openai/openai-python/blob/main/chatml.md
        raise NotImplementedError(f"""num_tokens_from_messages() is not implemented for model {model}""")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        num_tokens += len(encoding.encode(message))
        # for key, value in message.items():
        #     num_tokens += len(encoding.encode(value))
        #     if key == "name":
        #         num_tokens += tokens_per_name
    # 携带<|start|>assistant<|message|> 设置为3
    num_tokens += 0
    return num_tokens
