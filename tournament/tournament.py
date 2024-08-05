from random import shuffle

import cvxpy as cp
import numpy as np
import pandas as pd
from gspread_pandas import Spread
from attrs import define, field

from tournament.game import Game
from tournament.lichess import create_lichess_challenge
from tournament.optimization import round_pairings
from tournament.player import Player
from tournament.utils import expires_at_timestamp, timestamp_to_datetime, Outcome, elo_odds


@define
class Tournament:
    name: str
    spread: Spread
    leaderboard_sheet: str
    games_sheet: str
    initial_elo: int = field(default=1500)
    players: list[Player] = field(factory=list, init=False)
    games: list[Game] = field(factory=list, init=False)

    @property
    def next_round(self):
        if len(self.games) == 0:
            return 1
        else:
            return self.games[-1].round_num + 1

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

        # add bye player if odd
        if len(self.players) % 2 != 0:
            self.players.append(Player.bye_player())

    def _instantiate_game_list(self):
        """instantiate list of Games from Google spreadsheet"""
        self.games = []

        games_df = self.spread.sheet_to_df(sheet=self.games_sheet, index=0)

        for round_num, series in games_df.iterrows():
            self.games.append(Game.from_series(series))

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

        # sort by score and then elo
        self.players = sorted(self.players, key=lambda x: [x.score, x.elo], reverse=True)

        df = pd.DataFrame([player.to_dict() for player in self.players])

        self.spread.df_to_sheet(
            df=df,
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

        if testing or players[1].is_bye:
            game_link = ''
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
            outcome=Outcome.PENDING,
            expires=timestamp_to_datetime(expires_at))

        # add game to tournament
        self.games.append(game)

        return game

    def get_pairings(self, rematch_cost: float = 1.5, within_fed_cost: float = 0.75, elo_cost: float = 0.0001,
                     **kwargs) -> list[list[Player]]:
        """determine optimal player pairing to minimize cost function"""
        n = len(self.players)
        pairing_matrix = round_pairings(self.players, rematch_cost, within_fed_cost, elo_cost, **kwargs)

        # extract player matches from pairing matrix
        player_pairs = []
        matched_players = set()

        for i in range(n):
            if i not in matched_players:
                j = np.argmax(pairing_matrix[i])
                player_pairs.append([self.players[i], self.players[j]])

                matched_players.update([i, j])

        return player_pairs

    def create_next_round(self, lichess_api_token: str, **kwargs):
        """create games for next round"""
        round_num = self.next_round
        player_pairs = self.get_pairings()
        for players in player_pairs:
            self.create_game(
                round_num=round_num,
                players=players,
                lichess_api_token=lichess_api_token,
                **kwargs)

    def white_odds(self, game: Game) -> float:
        """odds of white winning"""
        return elo_odds(self.get_player(game.white).elo, self.get_player(game.black).elo)
