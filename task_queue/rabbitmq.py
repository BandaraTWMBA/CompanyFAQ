import pika
import json

def publish_task(task):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='ai_tasks')
        channel.basic_publish(
            exchange='',
            routing_key='ai_tasks',
            body=json.dumps(task)
        )
        connection.close()
        print(f"Published task: {task}")
    except Exception as e:
        print(f"Failed to publish task to RabbitMQ: {e}")
