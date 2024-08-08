import os, json, requests
import boto3
from aws_lambda_powertools import Logger
from langchain.embeddings import BedrockEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import BSHTMLLoader
from langchain_community.document_loaders import PyPDFLoader


DOCUMENT_TABLE = os.environ["DOCUMENT_TABLE"]
BUCKET = os.environ["BUCKET"]

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
document_table = ddb.Table(DOCUMENT_TABLE)
logger = Logger()

def retrieve_page(url):
    try:
        response = requests.get(url)
        return response.text
    except Exception as e:
        logger.exception(e)
        return None

def set_doc_status(user_id, document_id, status):
    document_table.update_item(
        Key={"userid": user_id, "documentid": document_id},
        UpdateExpression="SET docstatus = :docstatus",
        ExpressionAttributeValues={":docstatus": status},
    )

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    event_body = json.loads(event["Records"][0]["body"])
    document_id = event_body["documentid"]
    user_id = event_body["user"]
    key = event_body["key"]
    file_name_full = key.split("/")[-1]
    extension = file_name_full.split(".")[-1]

    set_doc_status(user_id, document_id, "PROCESSING")
    s3.download_file(BUCKET, key, f"/tmp/{file_name_full}")

    loader = None
    try:
        if extension == "pdf":
            loader = PyPDFLoader(f"/tmp/{file_name_full}")
        elif (extension == "json"):
            combined_html = ""
            with open(f"/tmp/{file_name_full}", "rb") as f:
                data = json.load(f)
                for item in data:
                    url = item["url"]
                    combined_html += f"SOURCE: {url}\n"
                    combined_html += retrieve_page(url)
            final = open(f"/tmp/combined.html", "w")
            final.write(combined_html)
            final.close()
            loader = BSHTMLLoader(f"/tmp/combined.html")
            s3.upload_file("/tmp/combined.html", BUCKET, f"{user_id}/{file_name_full}/content.html")
    except Exception as e:
        logger.exception(e)

    if loader is None:
        set_doc_status(user_id, document_id, "ERROR")
        return None

    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
    )

    embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v1",
        client=bedrock_runtime,
        region_name="us-east-1",
    )

    index_creator = VectorstoreIndexCreator(
        vectorstore_cls=FAISS,
        embedding=embeddings,
    )

    index_from_loader = index_creator.from_loaders([loader])
    index_from_loader.vectorstore.save_local("/tmp")

    s3.upload_file(
        "/tmp/index.faiss", BUCKET, f"{user_id}/{file_name_full}/index.faiss"
    )
    s3.upload_file("/tmp/index.pkl", BUCKET, f"{user_id}/{file_name_full}/index.pkl")

    set_doc_status(user_id, document_id, "READY")
