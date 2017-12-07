from enum import Enum


class LoggingStrategy(Enum):

    NOTHING = 'Nothing'
    LOG4J = 'Log4j'
    STD = 'Std'


class View(Enum):

    SNAPSHOT = 'SnapShot'
    HISTORICAL = 'Historical'
