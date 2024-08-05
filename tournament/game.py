from datetime import datetime
from random import shuffle

from attrs import define, field
import pandas as pd

from tournament.lichess import create_lichess_challenge
from tournament.player import Player
from tournament.utils import Outcome, expires_at_timestamp, timestamp_to_datetime, GamesSheetHeader, BYE_PLAYER


@define
class Game:
    round_num: int = field(converter=int)
    white: str
    black: str
    score_delta: float = field(default=None)
    games_played: int = field(default=None)
    match_link: str = field(default=None)  # lichess url
    expires: datetime = field(default=None)
    outcome: Outcome = field(default=None)

    @classmethod
    def from_series(cls, series: pd.Series):
        return cls(
            round_num=series[GamesSheetHeader.ROUND.value],
            white=series[GamesSheetHeader.WHITE.value],
            black=series[GamesSheetHeader.BLACK.value],
            score_delta=series[GamesSheetHeader.SCORE_DELTA.value],
            games_played=series[GamesSheetHeader.GAMES_PLAYED.value],
            match_link=series[GamesSheetHeader.MATCH_LINK.value],
            outcome=Outcome(series[GamesSheetHeader.OUTCOME.value]))

    @classmethod
    def create(cls, round_num: str, players: tuple[Player], lichess_api_token: str,
               testing: bool = False, days_until_expired: int = 7,
               **kwargs):

        player_pair = [players[0], players[1]]

        # randomize side if not bye
        if not players[1].is_bye:
            shuffle(player_pair)

        expires_at = expires_at_timestamp(days_until_expired)
        expires_at_datetime = timestamp_to_datetime(expires_at)

        if testing:
            game_link = '<testing: url here>'
        else:
            game_link = create_lichess_challenge(
                round_num=round_num,
                white_player=player_pair[0],
                black_player=player_pair[1],
                api_token=lichess_api_token,
                **kwargs)

        return cls(
            round_num=int(round_num),
            white=player_pair[0].name,
            black=player_pair[1].name,
            score_delta=player_pair[0].score - player_pair[1].score,
            games_played=players[0].match_count(players[1].name),
            match_link=game_link,
            outcome=Outcome.WHITE if players[1].is_bye else None,
            expires=expires_at_datetime)

    @property
    def bye(self):
        return self.black == BYE_PLAYER

    def to_dict(self) -> dict:
        return {
            GamesSheetHeader.ROUND.value: self.round_num,
            GamesSheetHeader.WHITE.value: self.white,
            GamesSheetHeader.BLACK.value: self.black,
            GamesSheetHeader.SCORE_DELTA.value: self.score_delta,
            GamesSheetHeader.GAMES_PLAYED.value: self.games_played,
            GamesSheetHeader.MATCH_LINK.value: self.match_link,
            GamesSheetHeader.OUTCOME.value: self.outcome.value,
            GamesSheetHeader.EXPIRES: self.expires}

    def get_points(self, player: str) -> float:
        if self.outcome == Outcome.DRAW:
            return 0.5

        elif ((player == self.white and self.outcome == Outcome.WHITE)
              or (player == self.black and self.outcome == Outcome.BLACK)):
            return 1.0

        else:
            # losses and games that expire
            return 0.
