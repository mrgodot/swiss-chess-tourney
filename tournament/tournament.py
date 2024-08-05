from random import shuffle

import pandas as pd
from gspread_pandas import Spread
from attrs import define, field

from tournament.game import Game
from tournament.lichess import create_lichess_challenge
from tournament.player import Player
from tournament.utils import PlayerSheetHeader, expires_at_timestamp, timestamp_to_datetime, Outcome, elo_odds


@define
class Tournament:
    name: str
    spread: Spread
    leaderboard_sheet: str
    games_sheet: str
    initial_elo: int = field(default=1500)
    players: list[Player] = field(factory=list, init=False)
    games: list[Game] = field(factory=list, init=False)
    next_round: int = field(default=None, init=False)

    def get_player(self, name: str) -> Player:
        """return Player from list of players"""
        if name == 'bye':
            return Player.bye_player()

        for player in self.players:
            if player.name == name:
                return player
        else:
            raise ValueError(f"{name} not found!")

    def _instantiate_player_list(self):
        """instantiate list of Players from Google spreadsheet"""
        self.players = []

        players_df = self.spread.sheet_to_df(sheet=self.leaderboard_sheet)

        for name, series in players_df.iterrows():
            self.players.append(Player.from_series(series, self.initial_elo))

    def _instantiate_game_list(self):
        """instantiate list of Games from Google spreadsheet"""
        self.games = []

        games_df = self.spread.sheet_to_df(sheet=self.games_sheet, index=0)

        for round_num, series in games_df.iterrows():
            self.games.append(Game.from_series(series))
            self.next_round = round_num + 1

    def _update_players(self):
        """update player elo based on historical record"""
        for game in self.games:
            if game.outcome is None:
                continue

            white_player = self.get_player(game.white)
            black_player = self.get_player(game.black)

            white_elo = white_player.elo
            black_elo = black_player.elo

            white_player.update(game, black_elo)
            black_player.update(game, white_elo)

    def update_leaderboard_sheet(self):
        """update and sort leaderboard spreadsheet"""
        df = pd.DataFrame([player.to_dict() for player in self.players])

        self.spread.df_to_sheet(
            df=df.sort_values(by=[PlayerSheetHeader.SCORE.value, PlayerSheetHeader.ELO.value], ascending=False),
            index=False,
            sheet=self.leaderboard_sheet)

    def update_games_sheet(self):
        """update and sort leaderboard spreadsheet"""
        df = pd.DataFrame([game.to_dict() for game in self.games])

        self.spread.df_to_sheet(
            df,
            index=False,
            sheet=self.games_sheet)

    def update_tournament_state(self):
        self._instantiate_player_list()
        self._instantiate_game_list()
        self._update_players()
        self.update_leaderboard_sheet()

    def create_game(self, round_num: int, players: list[Player], lichess_api_token: str,
                    days_until_expired: int = 7, testing: bool = False, **kwargs) -> Game:
        """create a Game between the two `players`. Use kwargs to pass additional params to `create_lichess_challenge"""

        # randomize side if not bye
        if not players[1].is_bye:
            shuffle(players)

        expires_at = expires_at_timestamp(days_until_expired)

        if testing:
            game_link = '<testing: url here>'
        else:
            game_link = create_lichess_challenge(
                round_num=round_num,
                white_player=players[0],
                black_player=players[1],
                api_token=lichess_api_token,
                expires_at=expires_at,
                **kwargs)

        game = Game(
            round_num=round_num,
            white=players[0].name,
            black=players[1].name,
            score_delta=players[0].score - players[1].score,
            games_played=players[0].match_count(players[1].name),
            match_link=game_link,
            outcome=Outcome.EXPIRED if players[1].is_bye else Outcome.PENDING,
            expires=timestamp_to_datetime(expires_at))

        # add game to tournament
        self.games.append(game)

        return game

    def white_odds(self, game: Game) -> float:
        """odds of white winning"""
        return elo_odds(self.get_player(game.white).elo, self.get_player(game.black).elo)
