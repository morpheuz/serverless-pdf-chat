import os, json
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger


DOCUMENT_TABLE = os.environ["DOCUMENT_TABLE"]
MEMORY_TABLE = os.environ["MEMORY_TABLE"]
BUCKET = os.environ["BUCKET"]

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")

document_table = ddb.Table(DOCUMENT_TABLE)
memory_table = ddb.Table(MEMORY_TABLE)
logger = Logger()


def remove_folder(user, file_name):
    # we need to delete the whole folder
    folder_key = f"{user}/{file_name}/"
    logger.info({"folder_key": folder_key})
    objects_to_delete = s3.list_objects_v2(Bucket=BUCKET, Prefix=folder_key)
    for obj in objects_to_delete["Contents"]:
        response = s3.delete_object(Bucket=BUCKET, Key=obj["Key"])
    return s3.delete_object(Bucket=BUCKET, Key=folder_key)

def clean_conversations(conversations):
    deleted_conversation_ids = []
    for conversation in conversations:
        conversation_id = conversation['conversationid']
        logger.info({"conversation_id": conversation_id})
        response = memory_table.delete_item(Key={"SessionId": conversation_id})
        if response:
            deleted_conversation_ids.append(conversation_id)
    return deleted_conversation_ids

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    document_id = event["pathParameters"]["documentid"]

    logger.info({"document_id": document_id})
    # retrieve document first so we can start deleting all conversations
    response = document_table.get_item(
        Key={"userid": user_id, "documentid": document_id}
    )

    # retrieved the document and its filename
    document = response["Item"]
    file_name = response["Item"]["filename"]

    # and delete the S3 folder (file and index)
    response = remove_folder(user_id, file_name)
    logger.info({"deleted folder": response})

    # clean up all conversations
    deleted_conversations = clean_conversations(document["conversations"])
    for id in deleted_conversations:
        logger.info({"deleted conversation": id})

    # finally delete the document
    response = document_table.delete_item(
        Key={"userid": user_id, "documentid": document_id}
    )
    logger.info({"deleted document": response})

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps(
            {
                "operation": "deleted_document",
                "document_id": document_id,
                "conversation_ids": deleted_conversations,
            },
            default=str,
        ),
    }
