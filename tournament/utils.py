from datetime import datetime, timedelta
from enum import Enum

import pytz


MILLISECONDS_PER_SECOND = 1000


class Outcome(Enum):
    white = 'White'
    black = 'Black'
    draw = 'Draw'
    expired = 'Expired'


def elo_odds(white_elo: float, black_elo: float) -> float:
    """return odds that white wins"""
    return 1 / (1 + 10 ** (-(white_elo - black_elo) / 400))


def expires_at_timestamp(days_until_expired) -> int:
    """return timestamp when game expires"""

    # last midnight in epoch seconds
    last_utc_midnight = datetime.now(pytz.UTC).replace(
        hour=0, minute=0, second=0, microsecond=0)

    # Calculate the expiration time (e.g. 7 days from now at midnight UTC)
    expires_at_utc = last_utc_midnight + timedelta(days=days_until_expired)

    # Convert the expiration time to a timestamp in milliseconds
    return int(expires_at_utc.timestamp() * MILLISECONDS_PER_SECOND)


def timestamp_to_datetime(timestamp) -> datetime:
    """convert UTC timestamp to datetime"""
    return datetime.fromtimestamp(timestamp / MILLISECONDS_PER_SECOND)
