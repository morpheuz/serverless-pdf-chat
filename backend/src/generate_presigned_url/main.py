import os, json, requests
import boto3
import shortuuid

from aws_lambda_powertools import Logger
from googlesearch import search
from urllib.parse import urlparse
from botocore.config import Config

BUCKET = os.environ["BUCKET"]
REGION = os.environ["REGION"]


s3 = boto3.client(
    "s3",
    endpoint_url=f"https://s3.{REGION}.amazonaws.com",
    config=Config(
        s3={"addressing_style": "virtual"}, region_name=REGION, signature_version="s3v4"
    ),
)
logger = Logger()

def s3_key_exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except:
        return False

def retrieve_search(search_query):
    result = []
    for url in search(search_query, num_results=5):
        result.append({"url": url})
    return result

def create_key(user_id, file_name, content_type):
    extension = "txt"
    if content_type == "application/pdf":
        extension = "pdf"
    elif content_type == "application/json":
        extension = "json"
        file_name = file_name.replace(" ", "_")[0:20]

    exists = s3_key_exists(BUCKET, f"{user_id}/{file_name}.{extension}/{file_name}.{extension}")
    if exists:
        suffix = shortuuid.ShortUUID().random(length=4)
        file_name = f"{file_name}-{suffix}"

    key = f"{user_id}/{file_name}.{extension}/{file_name}.{extension}"
    return key

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    file_name_full = event["queryStringParameters"]["file_name"]

    file_name = ""
    content = ""
    exists = False
    content_type = "application/json"

    result = urlparse(file_name_full)
    if (result.netloc):
        # query url
        domain = f"{result.netloc}"
        file_name = domain.replace(".", "_")
        content = json.dumps([{"url": file_name_full}])
    elif result.scheme == "search":
        # perform a search
        file_name = f"S_{file_name_full.split('SEARCH:')[1].replace(' ', '_')}"
        print("<><> file_name: ", file_name, "<><>")
        content = json.dumps(retrieve_search(file_name_full))
    elif result.path.split(".pdf")[0]:
        # this is a pdf file
        content_type = "application/pdf"
        file_name = file_name_full.split(".pdf")[0]

    logger.info(
        {
            "user_id": user_id,
            "file_name_full": file_name_full,
            "file_name": file_name,
        }
    )

    key_file = create_key(user_id, file_name, content_type)

    presigned_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": BUCKET,
            "Key": key_file,
            "ContentType": content_type,
        },
        ExpiresIn=300,
        HttpMethod="PUT",
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps({
            "presignedurl": presigned_url,
            "type": content_type,
            "content": content,
        }),
    }
