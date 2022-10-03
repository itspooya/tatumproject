import atexit
from src import DataIngestor
from apscheduler.schedulers.blocking import BlockingScheduler

cron = BlockingScheduler()


def main():
    """
    Main FUnction in order to use APscheduler
    :return: None
    """
    ingestor = DataIngestor()
    file_name = ingestor.download()
    ingestor.upload_file(file_name)


if __name__ == '__main__':
    main()
    cron.add_job(main, 'interval', hours=24)
    cron.start()
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: cron.shutdown(wait=False))
