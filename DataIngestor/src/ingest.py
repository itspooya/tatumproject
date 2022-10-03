import sys
import threading
from datetime import datetime, timedelta

from google.cloud import storage
import requests
from requests.exceptions import RequestException
import shutil
import re
import boto3
from botocore.config import Config
from boto3.s3.transfer import TransferConfig
import os


class ProgressPercentage(object):
    """
    This class is used to track the progress of the upload to S3
    """

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()


def download(url, download_path=None, file_name_string=None):
    """
    Download a file from a url and save it to a specified path
    :param url: url to download from
    :param download_path: path to save the file to
    :param file_name_string: string to use as the file name(overrides the file name in the url, currently not used in
    the code but can be used in the future)
    :return: file name(with path) of the downloaded file
    """
    try:
        if download_path is not None:
            # Check if the download path exists
            if not os.path.exists(download_path):
                # If not, create it
                os.makedirs(download_path)
        with requests.get(url, stream=True) as r:
            # Get the file name from the url if not provided
            # Header Content-Disposition is used to get the file name
            if "Content-Disposition" in r.headers.keys():
                file_name_string = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
            else:
                # If the file name is not provided and Content-Disposition is absent, use the last part of the url
                file_name_string = url.split("/")[-1]
            with open(f"{file_name_string}", "wb") as f:
                shutil.copyfileobj(r.raw, f)
    except RequestException as e:
        print(e)
    return file_name_string


def s3_client_builder(access_key, secret_key, region):
    """
    This method use imported values from import_env_var function and creates s3 connection
    :param access_key: access key for s3
    :param secret_key: secret key for s3
    :param region: region for s3
    :return: s3_client to use with s3
    """
    # Region is set to eu-west-1 by default
    client_config = Config(
        region_name=region,
        retries=dict(
            max_attempts=20
        )
    )
    ACCESS_KEY = access_key
    SECRET_KEY = secret_key
    session = boto3.session.Session()
    s3_client = session.client(
        service_name='s3',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=client_config,
    )
    return s3_client


def upload_to_s3(file_name, bucket, access_key, secret_key, region="eu-west-1", object_name=None):
    s3 = s3_client_builder(access_key, secret_key, region)
    # If the bucket does not exist, create it
    s3.create_bucket(Bucket=bucket)
    if object_name is None:
        object_name = file_name
    transfer_config = TransferConfig(
        multipart_threshold=1024 * 25,
        max_concurrency=16,
        multipart_chunksize=1024 * 25,
        use_threads=True
    )
    try:
        s3.upload_file(file_name, bucket, object_name, Config=transfer_config,
                       Callback=ProgressPercentage(file_name))
    except Exception as e:
        print(e)
        exit(1)


def upload_to_gcs(file_name, bucket_name, object_name=None):
    """
    Upload a file to a bucket in Google Cloud Storage
    :param file_name: file to upload
    :param bucket_name: bucket to upload to
    :param object_name: object name to use in the bucket, optional
    :return: None
    """
    # Check if application default credentials are set
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is None:
        print("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
        exit(1)
    storage_client = storage.Client()
    # list buckets to check if the bucket exists
    buckets = list(storage_client.list_buckets())
    # If the bucket does not exist, create it
    if bucket_name not in [bucket.name for bucket in buckets]:
        bucket = storage_client.create_bucket(bucket_name)
    else:
        bucket = storage_client.get_bucket(bucket_name)
    if object_name is None:
        object_name = file_name
    blob = bucket.blob(object_name)
    blob.upload_from_filename(file_name)
    print(f"File {file_name} uploaded to {bucket_name}.")


class DataIngestor:
    def __init__(self):
        self._load_env()

    def _load_env(self):
        self.s3_bucket_name = os.environ.get('S3_DOWNLOAD_BUCKET')
        self.s3_access_key = os.environ.get('S3_ACCESS_KEY')
        self.s3_secret_key = os.environ.get('S3_SECRET_KEY')
        self.s3_region = os.environ.get('S3_REGION')
        self.gcs_bucket_name = os.environ.get('GCS_DOWNLOAD_BUCKET')
        self.google_api_file = os.environ.get('GOOGLE_API_FILE')
        self.download_path = os.environ.get('DOWNLOAD_PATH')
        self.storage_provider = os.environ.get('STORAGE_PROVIDER')

    def _set_google_api(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_api_file

    def download(self):
        # Check if the download path is provided
        if self.download_path is not None:
            file_name = download(self.url, self.download_path)
            return file_name
        else:
            file_name = download(self.url)
            return file_name

    def upload_file(self, file_name):
        # get providers list from env
        providers = self.storage_provider.split(',')
        for provider in providers:
            if provider == 's3':
                upload_to_s3(file_name, self.s3_bucket_name, self.s3_access_key, self.s3_secret_key,
                             self.s3_region)

            elif provider == 'gcp':
                self._set_google_api()
                # upload to gcp
                upload_to_gcs(file_name, self.gcs_bucket_name)

    @property
    def url(self):
        base_url = os.getenv('BASE_URL')
        today = datetime.today().strftime('%m-%d-%Y')
        url = f"{base_url}/{today}.csv"
        # Check if the url is valid
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return url
            else:
                yesterday = (datetime.today() - timedelta(days=1)).strftime('%m-%d-%Y')
                url = f"{base_url}/{yesterday}.csv"
                # Check if the url is valid
                try:
                    r = requests.get(url)
                    if r.status_code == 200:
                        return url
                    else:
                        print("No data found")
                except Exception as e:
                    print(e)
                    exit(1)
        except Exception as e:
            print(e)
            exit(1)
        return url
