import os
import boto3
from botocore.config import Config
from google.cloud import storage


def s3_client_builder(access_key, secret_key, region) -> object:
    """
    This method use imported values from import_env_var function and creates s3 connection
    :param access_key: access key for s3
    :param secret_key: secret key for s3
    :param region: region for s3
    :return: s3_client to use with s3
    :rtype: object
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


class ShowData:
    """
    This class aims to have show data as one class for using in other projects or calling it from Flask
    """

    def __init__(self):
        """
        Load ENVs at class initialization
        """
        self._load_env()

    def _set_google_api(self):
        """
        This function sets the GOOGLE_APPLICATION_CREDENTIALS as env
        :return: None
        """
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_api_file

    def _load_env(self):
        """
        Function to load ENVs
        :return: None
        """
        self.s3_bucket_name = os.getenv('S3_BUCKET_NAME')
        self.s3_region = os.getenv('S3_REGION')
        self.s3_access_key = os.getenv('S3_ACCESS_KEY')
        self.s3_secret_key = os.getenv('S3_SECRET_KEY')
        self.gcs_bucket_name = os.getenv('GCS_UPLOAD_BUCKET')
        self.google_api_file = os.getenv('GOOGLE_API_FILE')
        self.storage_provider = os.getenv('STORAGE_PROVIDER')

    def _update_from_s3(self):
        """
        This function downloads the latest processed html into static files in order to be served from Flask(AWS S3)
        :return: None
        """
        s3_client = s3_client_builder(self.s3_access_key, self.s3_secret_key, self.s3_region)
        # if static folder doesn't exist create it
        if not os.path.isdir('static'):
            os.mkdir('static')
        download_path = os.path.join(os.getcwd(), 'static/index.html')
        s3_client.download_file(self.s3_bucket_name, 'index.html', download_path)

    def _update_from_gcs(self):
        """
        This function downloads the latest processed html into static files in order to be served from Flask(GCS)
        :return: None
        """
        client = storage.Client()
        bucket = client.get_bucket(self.gcs_bucket_name)
        blob = bucket.get_blob('index.html')
        if not os.path.isdir('static'):
            os.mkdir('static')
        download_path = os.path.join(os.getcwd(), 'static/index.html')
        blob.download_to_filename(download_path)

    def update_data(self):
        """
        Class initiator
        :return: None
        """
        for provider in self.storage_provider.split(','):
            if provider == 's3':
                self._update_from_s3()
            elif provider == 'gcp':
                self._set_google_api()
                self._update_from_gcs()
            else:
                print('Invalid storage provider')
