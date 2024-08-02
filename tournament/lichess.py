from urllib.error import HTTPError

import chess
import chess.pgn
import io
import requests

from tournament.player import Player
from tournament.utils import timestamp_to_datetime


LICHESS_CHALLENGE = "https://lichess.org/api/challenge/open"
LICHESS_GAME_EXPORT = "https://lichess.org/game/export/"

def create_lichess_challenge(
        round_num: str,
        white_player: Player,
        black_player: Player,
        clock_secs: int,
        increment_secs: int,
        expires_at: int,
        variant: str = 'standard',
        rated: bool = True,
        api_token=None) -> str:

    headers = {"Authorization": f"Bearer {api_token}"}

    expires_at_datetime = timestamp_to_datetime(expires_at)

    data = {
        "clock.limit": clock_secs,  # in seconds
        "clock.increment": increment_secs,  # in seconds
        "variant": variant,
        "rated": rated,
        "name": f"Round: {round_num}: {white_player.name} vs. {black_player.name} (expires: {expires_at_datetime})",
        "users": f"{white_player.handle},{black_player.handle}",
        "expiresAt": expires_at}

    response = requests.post(LICHESS_CHALLENGE, headers=headers, data=data)

    if response.status_code == 200:
        game_link = response.json().get("challenge").get("url")
        return game_link
    else:
        raise ValueError("Error: " + response.text)


def get_pgn(game_id, api_token=None) -> str:
    url = f"{LICHESS_GAME_EXPORT}{game_id}?"
    headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        raise HTTPError


def get_game_result_from_pgn(pgn_data: str) -> str:
    # Use StringIO to simulate a file object
    pgn = io.StringIO(pgn_data)

    # Read the game from the PGN data
    game = chess.pgn.read_game(pgn)

    # Get the result of the game
    result = game.headers["Result"]

    if result == "1-0":
        return "White"
    elif result == "0-1":
        return "Black"
    elif result == "1/2-1/2":
        return "Draw"
    else:
        return result
