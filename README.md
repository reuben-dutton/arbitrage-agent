## Async Web Scraper Project Template

This is a project template for web scrapers, built on:
 - [`taskiq`](https://taskiq-python.github.io/)
 - [`httpx`](https://www.python-httpx.org/)
 - [`sqlalchemy`](https://www.sqlalchemy.org/)

And requires a connection to the following backends (presumably on the local machine):
 - [RabbitMQ](https://www.rabbitmq.com/)
 - [Redis](https://redis.io/)

Optionally, the project can also use a database (PostgreSQL recommended), although this can be optionally turned off.

### Rate-limited AsyncClient

The template includes a `RateLimitedClient` which inherits from `httpx.AsyncClient`. It is used to ensure that requests are made politely, and can be configured with global rate limits or top-level domain specific rate limits.

The implementation of `RateLimitedClient` is inspired by (and partially copied from) [this discussion](https://github.com/encode/httpx/issues/815#issuecomment-1625374321)


### Config

Global configuration for the project is found in `config.py`.


### Testing

Use `pytest` to make and run tests.