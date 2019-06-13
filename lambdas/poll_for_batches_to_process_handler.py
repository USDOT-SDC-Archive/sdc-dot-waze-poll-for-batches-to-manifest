import boto3
import json
import os
from common.logger_utility import *
from common.constants import *

client = boto3.client('sns', region_name='us-east-1')


class SqsHandler:

    def __init__(self):
        pass

    def publish_message_to_sns(self, message):
        """
        Publishes a message to Amazon's Simple Notification Service
        :param message: dict
        """

        response = client.publish(
            TargetArn=os.environ['BATCH_NOTIFICATION_SNS'],
            Message=json.dumps({'default': json.dumps(message)}),
            MessageStructure='json'
        )

    def poll_for_batches(self, event, context):
        """
        gets the messages from the data persistence queue to start the persistence in Redshift
        :param event: a dictionary, or a list of a dictionary, that contains information on a batch
        :param context:
        :return:
        """
        try:

            sqs = boto3.resource('sqs', region_name='us-east-1')
            is_historical = event["is_historical"] == "true"
            persist_sqs = os.environ["manifest_sqs"]
            if is_historical:
                persist_sqs = os.environ["manifest_historical_sqs"]
            queue = sqs.get_queue_by_name(QueueName=persist_sqs)
            data = dict()
            data["is_historical"] = str(is_historical).lower()
            data["batch_id"] = ""

            # if no batch id assigned, gather batch_id, queueUrl, and receiptHandle from the messages in the queue.
            if 'BatchId' not in event:
                for message in queue.receive_messages():
                    jsonBody = json.loads(message.body)
                    data["batch_id"] = jsonBody["BatchId"]
                    data["queueUrl"] = message.queue_url
                    data["receiptHandle"] = message.receipt_handle
                    LoggerUtility.logInfo("Batch {} retrieved for processing".format(jsonBody["BatchId"]))
                    break

            # Otherwise, only assign the BatchId from the event.
            else:
                data["batch_id"] = event['BatchId']

            if data["batch_id"]:
                self.publish_message_to_sns({"BatchId": data["batch_id"], "Status": "Manifest generation started"})
            return data

        except Exception as e:
            LoggerUtility.logError("Error polling for batches")
            raise e
    
    def get_batches(self, event, context):
        """
        Executes poll_for_batches
        :param event: a dictionary, or a list of a dictionary, that contains information on a batch
        :param context:
        :return:
        """
        return self.poll_for_batches(event, context)
