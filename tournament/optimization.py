import numpy as np

import cvxpy as cp

from tournament.player import Player


def round_pairings(players: list[Player], rematch_cost: float, within_fed_cost: float, elo_cost: float,
                   solver=cp.GLPK_MI, **kwargs) -> list:

    n = len(players)

    # Binary variables for pairing
    x = cp.Variable((n, n), boolean=True)

    # Cost matrix
    cost_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):

            score_delta = np.abs(players[i].score - players[j].score)
            rematch_penalty = rematch_cost * players[i].match_count(players[j].name)
            federation_penalty = within_fed_cost * float(
                players[i].federation == players[j].federation)
            elo_difference = elo_cost * np.abs(players[i].elo - players[j].elo)

            cost = score_delta + rematch_penalty + federation_penalty + elo_difference
            cost_matrix[i, j] = cost
            cost_matrix[j, i] = cost  # symmetry

    # Objective function
    objective = cp.Minimize(cp.sum(cp.multiply(cost_matrix, x)))

    # Constraints
    constraints = []

    # Each player should be paired with exactly one other player
    for i in range(n):
        constraints.append(cp.sum(x[i, :]) == 1)
        constraints.append(cp.sum(x[:, i]) == 1)

    # No player should be paired with themselves
    for i in range(n):
        constraints.append(x[i, i] == 0)

    # Symmetry constraint (implicitly handled by the cost matrix symmetry)

    # Solve the problem
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=solver)

    # Get the optimal pairing
    pairing_matrix = np.array(x.value, dtype=int)

    return pairing_matrix


def player_pairs_from_matrix(pairing_matrix: np.array, players: list[Player]):
    # extract player matches from pairing matrix
    player_pairs = []
    matched_players = set()

    for i in range(len(players)):
        if i not in matched_players:
            j = np.argmax(pairing_matrix[i])
            player_pairs.append([players[i], players[j]])

            matched_players.update([i, j])