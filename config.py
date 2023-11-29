# backend details
RABBITMQ_URL = "amqp://guest:guest@localhost:5672"
REDIS_URL = "redis://localhost"


# rate limiting
GLOBAL_RATE_LIMIT = 100  # requests per second (amortized)
DOMAIN_RATE_LIMIT = 0.5  # requests per second (amortized)
GLOBAL_CONCURRENCY_LIMIT = 10  # number of concurrent requests globally
DOMAIN_CONCURRENCY_LIMIT = 2  # number of concurrent requests per domain
MAX_RETRIES_PER_REQUEST = 1  # number of retries maximum per request


# database details
USING_DATABASE = True

DATABASE_HOST = "localhost"
DATABASE_PORT = "5432"
DATABASE_USER = "postgres"
DATABASE_PASS = "postgres"
DATABASE_DRIVER = "postgresql+psycopg2"
DATABASE_NAME = "arbitrage-agent"  # change this (per project)
TEST_DATABASE_NAME = "test-database"
DATABASE_CONNECT_STRING = f"{DATABASE_DRIVER}://{DATABASE_USER}:{DATABASE_PASS}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"  # noqa
TEST_DATABASE_CONNECT_STRING = f"{DATABASE_DRIVER}://{DATABASE_USER}:{DATABASE_PASS}@{DATABASE_HOST}:{DATABASE_PORT}/{TEST_DATABASE_NAME}"  # noqa


# client details

REQUEST_CACHE_LOCATION = ".request_cache"
