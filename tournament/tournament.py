from random import shuffle

import numpy as np
import pandas as pd
from gspread_pandas import Spread
from attrs import define, field

from tournament.game import Game
from tournament.lichess import create_lichess_challenge, get_game_from_id
from tournament.optimization import round_pairings, player_pairs_from_matrix
from tournament.player import Player
from tournament.utils import expires_at_timestamp, timestamp_to_datetime, Outcome, white_odds, BYE_PLAYER, GamesSheetHeader

SECONDS_PER_MIN = 60
pd.set_option('future.no_silent_downcasting', True)


@define
class Tournament:
    """
    Container for all tournament parameters and objects.
    After instantiation, load tournament state by calling tournament.update_tournament_state()
    Create a new round using tournament.create_next_round()
    """
    name: str
    spread: Spread
    leaderboard_sheet: str
    games_sheet: str
    # player pairing cost starts with abs score difference
    rematch_cost: float = 2.5  # cost to play the same player again
    within_fed_cost: float = 0.75  # cost to be paired within federation
    experience_cost: float = 1.0  # early round sorting based on difference in experience
    elo_cost: float = 0.0001  # tie-breaker based on abs elo difference
    initial_elo: int = field(default=1500)
    clock_secs: int = field(default=SECONDS_PER_MIN * 10)
    increment_secs: int = field(default=5)
    players: list[Player] = field(factory=list, init=False)
    games: list[Game] = field(factory=list, init=False)

    def __attrs_post_init__(self):
        """load tournament details"""
        self._instantiate_player_list()
        print(f"{len(self.players)} players created")
        self._instantiate_game_list()
        self._process_games()
        print(f"{len(self.games)} games processessed ({self.games_in_progress} games in progress)")

    @property
    def current_round(self):
        if len(self.games) == 0:
            return 1
        else:
            return self.games[-1].round_num
            
    @property
    def next_round(self):
        return self.current_round + 1

    @property
    def games_in_progress(self) -> int:
        """return count of games in progress"""
        return sum(game.in_progress for game in self.games)
    
    def get_player(self, name: str) -> Player:
        """return Player from list of players"""
        if name == BYE_PLAYER:
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

    def _process_games(self, **kwargs):
        """add games to players and update elo"""
        for game in self.games:
            if game.outcome != Outcome.PENDING and not game.bye:
                self.update_players(game, **kwargs)

    def reset(self):
        """reset tournament to the start of round 1"""
        self.games = []
        for player in self.players:
            player.reset(self.initial_elo)

    def update_players(self, game: Game, **kwargs):
        """add game to players and update elo"""
        white_player = self.get_player(game.white)
        black_player = self.get_player(game.black)

        white_elo = white_player.elo
        black_elo = black_player.elo

        white_player.update(game, black_elo, **kwargs)
        black_player.update(game, white_elo, **kwargs)

    def update_leaderboard_sheet(self):
        """update and sort leaderboard spreadsheet"""
        print("updating leaderboard sheet")
        # sort players by score and then elo
        self.players = sorted(self.players, key=lambda x: [x.score, x.elo], reverse=True)

        df = pd.DataFrame([player.to_dict() for player in self.players])

        self.spread.df_to_sheet(
            df=df,
            index=False,
            sheet=self.leaderboard_sheet)

    def update_games_sheet(self):
        """update and sort game spreadsheet"""
        print("updating games sheet")
        df = pd.DataFrame([game.to_dict() for game in self.games])

        def sum_value(game: Game, value: str):
            return sum([getattr(self.get_player(player), value) for player in [game.white, game.black]])

        # sort df by round, byes on bottom, highest rated matches first
        df['rank'] = [(
            game.round_num, game.bye,
            -sum_value(game, value='score'), -sum_value(game, value='elo'))
            for game in self.games]

        df = df.sort_values('rank')

        self.spread.df_to_sheet(
            df.drop(columns='rank'),
            index=False,
            sheet=self.games_sheet)

    def create_game(self, round_num: int, players: list[Player], lichess_api_token: str,
                    random_sides: bool = True, days_until_expired: int = 7, testing: bool = False,
                    **kwargs) -> Game:
        """create a Game between the two `players`. Use kwargs to pass additional params to `create_lichess_challenge"""

        # check for bye
        is_bye = any(player.is_bye for player in players)

        if is_bye:
            # ensure bye player is black
            players = sorted(players, key=lambda x: x.is_bye)
        elif random_sides:
            # randomize sides
            shuffle(players)

        expires_at = expires_at_timestamp(days_until_expired)

        if testing or is_bye:
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
            score_delta=players[0].score - players[1].score if not is_bye else 0,
            games_played=players[0].match_count(players[1].name),
            match_link=game_link,
            expires=timestamp_to_datetime(expires_at))

        # add game to tournament
        self.games.append(game)

        return game

    def get_pairings(self, bye_players: list[str] | None, **kwargs) -> list[list[Player]]:
        """determine optimal player pairing to minimize cost function"""
        # remove withdrawn
        players = [player for player in self.players if not player.withdrawn]

        if bye_players is not None:
            # remove bye_player from player list
            players = [player for player in players if player.name not in bye_players]

        if len(players) % 2 != 0:
            # player list is still odd, add a bye player
            players = players + [Player.bye_player()]

        pairing_matrix = round_pairings(
            players=players,
            rematch_cost=self.rematch_cost,
            within_fed_cost=self.within_fed_cost,
            experience_cost=self.experience_cost / self.current_round,
            elo_cost=self.elo_cost,
            **kwargs)

        player_pairs = player_pairs_from_matrix(pairing_matrix, players)

        # if bye player was provided, pair them now
        if bye_players is not None:
            for player in bye_players:
                player_pairs.append([self.get_player(player), Player.bye_player()])

        return player_pairs

    def add_current_round_openings(self, round_num: int | None = None):
        """add opening to current round sheet"""
        round_num = round_num or self.current_round
        games_df = self.spread.sheet_to_df(sheet=self.games_sheet, index=0).set_index('Round')
        games_df.index = games_df.index.astype(int)
        
        game_id_from_url = lambda x: x.split('/')[-1]
        games_df.loc[round_num, GamesSheetHeader.OPENING.value] = games_df.loc[round_num, :].apply(
            lambda x: get_game_from_id(game_id_from_url(x['Match Link'])).headers.get('Opening')
            if (
                x[GamesSheetHeader.OUTCOME.value] not in {Outcome.PENDING.value, Outcome.EXPIRED.value} 
                and x[GamesSheetHeader.MATCH_LINK.value] != '' 
                and x[GamesSheetHeader.BLACK.value] != BYE_PLAYER
            ) else '', axis=1
        ).squeeze()
        
        self.spread.df_to_sheet(
            games_df,
            index=True,
            sheet=self.games_sheet)

        # re-instantiate games to pull in openings
        self._instantiate_game_list()

    def create_next_round(self, lichess_api_token: str, bye_players: str | list[str] | None = None, **kwargs):
        """create games for next round and update leaderboard and game sheets"""
        # update leaderboard
        self.update_leaderboard_sheet()
        
        round_num = self.next_round

        if isinstance(bye_players, str):
            bye_players = [bye_players]

        player_pairs = self.get_pairings(bye_players=bye_players, **kwargs)

        for players in player_pairs:
            self.create_game(
                round_num=round_num,
                players=players,
                lichess_api_token=lichess_api_token,
                clock_secs=self.clock_secs,
                increment_secs=self.increment_secs,
                **kwargs)

        # update game sheet
        self.update_games_sheet()

    def white_odds(self, game: Game) -> float:
        """odds of white winning"""
        return white_odds(self.get_player(game.white).elo, self.get_player(game.black).elo)
