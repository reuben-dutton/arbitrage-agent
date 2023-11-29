import config


# https://stackoverflow.com/questions/58660378/how-use-pytest-to-unit-test-sqlalchemy-orm-classes
def pytest_addoption(parser):
    parser.addoption('--dburl',
                     action='store',
                     default=config.TEST_DATABASE_CONNECT_STRING,
                     help='url of the database to use for tests')
