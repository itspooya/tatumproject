import boto3
import gzip
import pandas as pd
import threading
import sys
import os
import jinja2
from botocore.config import Config
from boto3.s3.transfer import TransferConfig
from google.cloud import storage


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


# check if the file is gzipped from file content
def is_gzipped(file_name):
    with open(file_name, 'rb') as f:
        return f.read(2) == b'\x1f\x8b'


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


class DataProcessor:
    def __init__(self):
        self._load_env()

    def _set_google_api(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_api_file

    def _load_env(self):
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        self.region = os.getenv('S3_REGION')
        self.s3_download_bucket = os.getenv('S3_DOWNLOAD_BUCKET')
        self.s3_upload_bucket = os.getenv('S3_UPLOAD_BUCKET')
        self.gcs_download_bucket = os.getenv('GCS_DOWNLOAD_BUCKET')
        self.gcs_upload_bucket = os.getenv('GCS_UPLOAD_BUCKET')
        self.google_api_file = os.getenv('GOOGLE_API_FILE')
        self.download_path = os.getenv('DOWNLOAD_PATH')
        self.processed_folder = os.getenv('PROCESSED_FOLDER')
        self.storage_provider = os.getenv('STORAGE_PROVIDER')

    def runit(self):
        # check storage providers
        if "s3" in self.storage_provider:
            self.upload_to_s3()
        elif "gcp" in self.storage_provider:
            self.upload_to_gcs()
        else:
            print("No storage provider is selected, please select one of the following: s3, gcp")
            exit(1)

    @property
    def last_file_s3(self):
        """
        This method returns the last file from the bucket
        :return: last_file_s3
        """
        # get last file from s3
        s3_client = s3_client_builder(self.access_key, self.secret_key, self.region)
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=self.s3_download_bucket)
        latest_file = None
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    if latest_file is None or obj['LastModified'] > latest_file['LastModified']:
                        latest_file = obj
        if latest_file is not None:
            return latest_file['Key']
        else:
            print("No files found in bucket")
            exit(1)

    @property
    def get_last_file_from_gcs(self):
        """
        This method gets the last file from gcs
        :return: None
        """
        self._set_google_api()
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(self.gcs_download_bucket)
        blobs = bucket.list_blobs()
        latest_file = None
        for blob in blobs:
            if latest_file is None or blob.updated > latest_file.updated:
                latest_file = blob
        if latest_file is not None:
            return latest_file.name
        else:
            print("No files found in bucket")
            exit(1)

    @property
    def download_from_s3(self):
        """
        This method downloads the last file from s3
        :return: None
        """
        s3_client = s3_client_builder(self.access_key, self.secret_key, self.region)
        # Check if the download folder exists
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
        # Create s3 folder in download folder
        s3_folder = os.path.join(self.download_path, self.s3_download_bucket)
        if not os.path.exists(s3_folder):
            os.makedirs(s3_folder)
        file_path = os.path.join(s3_folder, self.last_file_s3)
        s3_client.download_file(self.s3_download_bucket, self.last_file_s3, f"{file_path}")
        return file_path

    @property
    def download_from_gcs(self):
        """
        Downloads the last file from gcs
        :return: file_path
        """
        self._set_google_api()
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(self.gcs_download_bucket)
        blob = bucket.blob(self.get_last_file_from_gcs)
        # Check if the download folder exists
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
        # create gcs folder in download folder
        gcs_folder = os.path.join(self.download_path, self.gcs_download_bucket)
        if not os.path.exists(gcs_folder):
            os.makedirs(gcs_folder)
        file_path = os.path.join(gcs_folder, self.get_last_file_from_gcs)
        blob.download_to_filename(file_path)
        return file_path

    @property
    def extract(self):
        """
        This method extracts the last file from s3
        :return: file_paths of the extracted data
        """
        file_paths = []
        providers = self.storage_provider.split(',')
        for provider in providers:
            if provider == 's3':
                file_paths.append(self.download_from_s3)
                flag = 's3'
            elif provider == 'gcp':
                file_paths.append(self.download_from_gcs)
                flag = 'gcp'
            else:
                print("No supported storage provider found")
                exit(1)
        processed_files = []
        for file_path in file_paths:
            if is_gzipped(file_path):
                df = pd.read_csv(file_path, compression='gzip')
            else:
                df = pd.read_csv(file_path)
            # get Country_Region row which matches with Czechia
            czechia_row = df.loc[df['Country_Region'] == 'Czechia']
            # convert to table
            czechia_table = czechia_row.to_html()
            # Why Jinja2? Because it's easy to use, and later we can add more variables to the template, and it will be
            # easier to maintain and even we can add some logic to the template
            template = jinja2.Template(open('src/templates/index.html.j2').read())
            # Check if the processed folder exists
            if not os.path.exists(self.processed_folder):
                os.makedirs(self.processed_folder)
            # create folder based on flag
            if flag == 's3':
                # check if processed folder exists
                processed_folder = os.path.join(self.processed_folder, "s3")
                if not os.path.exists(processed_folder):
                    os.makedirs(processed_folder)
            elif flag == 'gcp':
                processed_folder = os.path.join(self.processed_folder, "gcp")
                if not os.path.exists(processed_folder):
                    os.makedirs(processed_folder)
            processed_file_path = os.path.join(processed_folder, f"index.html")

            with open(f'{processed_file_path}', 'w') as f:
                f.write(template.render(data=czechia_table))
            processed_files.append(processed_file_path)
        return processed_files

    def upload_to_s3(self):
        """
        This method uploads the processed file to s3
        :return: None
        """
        s3_client = s3_client_builder(self.access_key, self.secret_key, self.region)
        s3_client.create_bucket(Bucket=self.s3_upload_bucket)
        transfer_config = TransferConfig(
            multipart_threshold=1024 * 25,
            max_concurrency=16,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )
        processed_file_paths = self.extract
        for processed_file_path in processed_file_paths:
            if "s3" in processed_file_path:
                try:
                    s3_client.upload_file(processed_file_path, self.s3_upload_bucket, 'index.html',
                                          Config=transfer_config, Callback=ProgressPercentage(processed_file_path))
                except Exception as e:
                    print(e)
                    exit(1)

    def upload_to_gcs(self):
        """
        This method uploads the processed file to gcs
        :return: None
        """
        # Check if application default credentials are set
        self._set_google_api()
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is None:
            print("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
            exit(1)

        storage_client = storage.Client()
        buckets = list(storage_client.list_buckets())
        if self.gcs_upload_bucket not in [bucket.name for bucket in buckets]:
            bucket = storage_client.create_bucket(self.gcs_upload_bucket)
        else:
            bucket = storage_client.get_bucket(self.gcs_upload_bucket)
        processed_file_paths = self.extract
        for processed_file_path in processed_file_paths:
            if "gcp" in processed_file_path:
                blob = bucket.blob('index.html')
                blob.upload_from_filename(processed_file_path)
                print(f"File {processed_file_path} uploaded to {self.gcs_upload_bucket}")
