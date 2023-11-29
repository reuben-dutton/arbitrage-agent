# poetry run taskiq worker -w 1 src.worker.broker:broker src.tasks_example
poetry run taskiq worker -w 1 --no-configure-logging src.worker.broker:broker src.tasks_example src.tasks