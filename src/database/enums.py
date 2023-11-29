from enum import Enum


class Status(Enum):
    UNKNOWN = 0
    RETRIEVED = 1
    ADDED = 2
    CHECKED = 3
    NOT_FOUND = 4
    EXPIRED = 5
