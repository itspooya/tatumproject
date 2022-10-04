# Tatum project

Tatumproject is a tool to download a specific dataset from a free data provider, upload it to cloudstorage and then process
it to extract data relevant to Czecia and Prague and display it in a single HTML page.

## How to use it

There are multiple ways to use this project

1. Simplest one would be downloading whole project changing variables in docker-compose files present in each
   folder(dataprocessor,dataingestor,showdata) and then creating a service account for GCP or filling aws keys and manually
   installing docker and running them

2. Get a service account from gcp and then copy downloaded json key to deployment folder as key.json and change
   project in providers.tf in deployment with project in service account or google dashboard, Install ansible and terraform, then run following commands
   which would show ip for new created instance and generated ssh key in deployment/sshkeys and root password that you can access ip with port 80
   to see the output
    - terraform init
    - terraform plan
    - terraform apply

## CI/CD
Current version of CI/CD needs to be refactored and a better approach needs to be applied for example webhook like or not
using ansible for deployment and using pure bash for example

| Name            | ENV             | Description                                                         | Required | Default |
|-----------------|-----------------|---------------------------------------------------------------------|----------|---------|
| Project Path    | PROJECT_PATH    | Project path which you deployed, by default it's /root/tatumproject | YES      | -       |
| SSH IP          | SSH_HOST        | SSH IP of previously created instance by running terraform          | YES      | -       |
| SSH private key | SSH_PRIVATE_KEY | SSH private key of a user which has access to the server            | YES      | -       |
| SSH user        | SSH_USER        | Username of the user which has access to server(created for CI/CD)  | YES      | -       |


## Environment Values

| ENV                 | Description                                              | Required | Default                                                                                                          | Available options                                                                                                |
|---------------------|----------------------------------------------------------|----------|------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| S3_DOWNLOAD_BUCKET  | Bucket which we will upload our downloaded csv to        | YES      | tatum-data-download                                                                                              | *                                                                                                                |
| S3_ACCESS_KEY       | Access key for Amazon S3 account                         | YES      | -                                                                                                                | *                                                                                                                |
| S3_SECRET_KEY       | Secret key for Amazon S3 account                         | YES      | -                                                                                                                | *                                                                                                                |
| S3_REGION           | Region of S3 bucket                                      | YES      | us-east-1                                                                                                        | https://docs.aws.amazon.com/general/latest/gr/s3.html                                                            |
| GCS_DOWNLOAD_BUCKET | Bucket which we will upload our downloaded csv to at GCS | YES      | tatum-data-download                                                                                              | *                                                                                                                |
| GOOGLE_API_FILE     | Path in container which google credentials is located at | YES      | /etc/key.json                                                                                                    | *                                                                                                                |
| DOWNLOAD_PATH       | Path which Data ingestor downloads temporary files into  | YES      | /tmp                                                                                                             | *                                                                                                                |
| STORAGE_PROVIDER    | Storage providers comma separated                        | YES      | gcp                                                                                                              | s3,gcp                                                                                                           |
| BASE_URL            | Base url to download CSV from                            | YES      | https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/ | https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/ |
| S3_UPLOAD_BUCKET    | Bucket which processed csv(html) would be uploaded to    | YES      | tatum-data                                                                                                       | *                                                                                                                |
| GCS_UPLOAD_BUCKET   | Bucket which processed csv(html) would be uploaded to    | YES      | tatum-data                                                                                                       | *                                                                                                                |
| PROCESSED_FOLDER    | Path which Data Processor sends processed files into     | YES      | /tmp/processed                                                                                                   | *                                                                                                                |
| PORT                | Port which Flask listens to                              | NO       | 5000                                                                                                             | Any int                                                                                                          |

