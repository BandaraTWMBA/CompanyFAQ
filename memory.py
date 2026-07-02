from collections import deque


chat_history = deque(maxlen=10)



def add_message(role, content):

    chat_history.append(
        {
            "role": role,
            "content": content
        }
    )



def get_history():

    history = ""

    for item in chat_history:

        history += (
            f"{item['role']}: "
            f"{item['content']}\n"
        )


    return history