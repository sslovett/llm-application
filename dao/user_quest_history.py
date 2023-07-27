from config.configDb import MyPymysqlPool


def insert_user_quest_history(user_no, request_content, response_content,
                              total_tokens, prompt_tokens,
                              completion_tokens, successful_requests,
                              total_cost):
    llm_db = MyPymysqlPool("llm_db")
    # sql = "INSERT INTO llm.user_quest_history (user_no, request_content, response_content, total_tokens, " \
    #       "prompt_tokens, completion_tokens, successful_requests, total_cost) VALUES ('%s', '%s', '%s', %s, %s, %s, %s, '%s')" % (
    #           user_no, request_content, response_content,
    #           total_tokens, prompt_tokens,
    #           completion_tokens, successful_requests,
    #           total_cost)

    sql = "INSERT INTO llm.user_quest_history (user_no, request_content, response_content, total_tokens, " \
          "prompt_tokens, completion_tokens, successful_requests, total_cost) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"

    list = [user_no, request_content, response_content,
            total_tokens, prompt_tokens,
            completion_tokens, successful_requests,
            total_cost]

    llm_db.insert(sql=sql, param=list)
    llm_db.dispose()
