from src import DataIngestor

if __name__ == '__main__':
    data_ingestor = DataIngestor()
    file_name = data_ingestor.download()
    data_ingestor.upload_file(file_name)


