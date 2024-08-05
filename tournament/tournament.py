import pandas as pd
from gspread_pandas import Spread
from attrs import define, field

from tournament.game import Game
from tournament.player import Player


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

        games_df = self.spread.sheet_to_df(sheet=self.games_sheet)

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

    def _update_leaderboard(self):
        """update and sort leaderboard spreadsheet"""
        df = pd.DataFrame([player.to_dict() for player in self.players])

        self.spread.df_to_sheet(
            sheet=self.leaderboard_sheet,
            df=df.sort_values(by=['Score', 'Elo'], ascending=False),
            index=False)

    def update_tournament_state(self):
        self._instantiate_player_list()
        self._instantiate_game_list()
        self._update_players()
        self._update_leaderboard()
