import numpy as np

import cvxpy as cp

from tournament.player import Player


def calculate_cost_matrix(players: list[Player], rematch_cost: float, within_fed_cost: float,
                          experience_cost: float, elo_cost: float, **kwargs) -> np.ndarray:
    """"apply cost function to each pairwise player pairing returning a symmetric cost matrix"""

    n = len(players)

    cost_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            # difference in experience
            experience_delta = experience_cost * np.abs(players[i].animal.value - players[j].animal.value)
            # difference in player scores
            score_delta = np.abs(players[i].score - players[j].score)
            # penalize rematches
            rematch_penalty = rematch_cost * players[i].match_count(players[j].name)
            # penalize intra-federation match
            federation_penalty = within_fed_cost * float(
                players[i].federation == players[j].federation)
            # fractional elo difference to break ties
            elo_difference = elo_cost * np.abs(players[i].elo - players[j].elo)

            # sum up costs
            cost = experience_delta + score_delta + rematch_penalty + federation_penalty + elo_difference
            cost_matrix[i, j] = cost
            cost_matrix[j, i] = cost  # symmetry

    return cost_matrix


def round_pairings(players: list[Player], solver=cp.GLPK_MI, **kwargs) -> np.ndarray:
    """use mixed integer linear programming to solve for optimal round pairings"""

    n = len(players)

    cost_matrix = calculate_cost_matrix(players, **kwargs)

    # pairing matrix
    x = cp.Variable((n, n), boolean=True)

    # objective function
    objective = cp.Minimize(cp.sum(cp.multiply(cost_matrix, x)))

    # constraints
    constraints = []

    for i in range(n):
        # each player should be paired with exactly one other player
        constraints.append(cp.sum(x[i, :]) == 1)
        constraints.append(cp.sum(x[:, i]) == 1)

        # no player should be paired with themselves
        constraints.append(x[i, i] == 0)

        # symmetry constraint: a vs b is the same as b vs a
        for j in range(i + 1, n):
            constraints.append(x[i, j] == x[j, i])

    # minimize objective function subject to constraints
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=solver)

    # Get the optimal pairing
    pairing_matrix = np.array(x.value, dtype=int)

    return pairing_matrix


def player_pairs_from_matrix(pairing_matrix: np.ndarray, players: list[Player]) -> list[list]:
    """extract player pairs from pairing matrix"""
    player_pairs = []
    matched_players = set()

    for i in range(len(players)):
        if i not in matched_players:
            j = np.argmax(pairing_matrix[i])
            player_pairs.append([players[i], players[j]])

            matched_players.update([i, j])

    return player_pairs
