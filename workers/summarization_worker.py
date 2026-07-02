import pika
import json


def process(message):

    print(
        "Processing:",
        message
    )


    # Heavy AI task here

    # PDF loading

    # embeddings

    # LLM summarization



connection=pika.BlockingConnection(

pika.ConnectionParameters(
"localhost"
)

)


channel=connection.channel()


channel.queue_declare(
queue="ai_tasks"
)



def callback(
ch,
method,
properties,
body
):


    data=json.loads(body)


    process(data)


channel.basic_consume(

queue="ai_tasks",

on_message_callback=callback,

auto_ack=True

)


print(
"Worker started"
)


channel.start_consuming()