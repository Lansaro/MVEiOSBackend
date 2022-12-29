from database.file_cleaning_service import FileCleaningService


def main():
    FileCleaningService().cron_delete_expired()


if __name__ == '__main__':
    main()
