from datetime import datetime, timedelta
from enum import Enum

import pandas as pd
import pytz


MILLISECONDS_PER_SECOND = 1000
BYE_PLAYER = 'bye'
BYE_PLAYER_ELO = 0


class AnimalClass(Enum):
    """self-reported experience level"""
    KOALA = -1
    DEER = 0
    COUGAR = 1


class Outcome(Enum):
    PENDING = ''
    WHITE = 'White'
    BLACK = 'Black'
    DRAW = 'Draw'
    EXPIRED = 'Expired'


class SheetName(Enum):
    PLAYERS = 'Leaderboard'
    GAMES = 'Games'


class PlayerSheetHeader(Enum):
    PLAYER = 'Player'
    HANDLE = 'Lichess Handle'
    FEDERATION = 'Federation'
    EXPERIENCE = 'Experience'
    ELO = 'Elo'
    SCORE = 'Score'


class GamesSheetHeader(Enum):
    ROUND = 'Round'
    WHITE = 'White'
    BLACK = 'Black'
    SCORE_DELTA = 'Score Delta'
    GAMES_PLAYED = 'Games Played'
    MATCH_LINK = 'Match Link'
    OUTCOME = 'Outcome'
    EXPIRES = 'Expires'
    OPENING = 'Opening'


def white_odds(white_elo: float, black_elo: float) -> float:
    """return odds that white wins"""
    return 1 / (1 + 10 ** (-(white_elo - black_elo) / 400))


def expires_at_timestamp(days_until_expired, timezone = pytz.timezone('US/Pacific')) -> int:
    """return timestamp when game expires"""

    # last midnight local
    last_midnight = pd.Timestamp.now(timezone).normalize()

    # Calculate the expiration time
    expires_at = last_midnight + timedelta(days=days_until_expired) - timedelta(seconds=1)

    # Convert the expiration time to a timestamp in milliseconds
    epoch_secs = int(expires_at.timestamp())
    return epoch_secs * MILLISECONDS_PER_SECOND


def timestamp_to_datetime(timestamp, timezone = pytz.timezone('US/Pacific')) -> datetime:
    """convert UTC timestamp to datetime"""
    return datetime.fromtimestamp(timestamp / MILLISECONDS_PER_SECOND).astimezone(timezone)
