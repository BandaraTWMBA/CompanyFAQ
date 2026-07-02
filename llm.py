import ollama


def ask_llm(prompt):

    response = ollama.chat(

        model="llama3.2:3b",

        options={
            "temperature":0
        },

        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ]
    )


    return response["message"]["content"]