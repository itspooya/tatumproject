import atexit
from src import DataProcessor
from apscheduler.schedulers.blocking import BlockingScheduler
from time import sleep

cron = BlockingScheduler()


def main():
    processor = DataProcessor()
    processor.runit()


if __name__ == '__main__':
    # Running for the first time requires a delay to allow downloading the file
    sleep(100)
    main()
    cron.add_job(main, 'interval', hours=24)
    cron.start()
    atexit.register(lambda: cron.shutdown(wait=False))

