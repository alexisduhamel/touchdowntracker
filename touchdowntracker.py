# touchdowntracker.py

import os
import random
import csv
import logging as log

from globals import *
from utils import *

def generatePairing(round_number, players_dict, stats_dict):
    """
    Generate Swiss pairings for the given round.
    Supports both team-based and individual pairings, avoiding repeat matchups.
    """
    log.debug(f'generatePairing called for round {round_number}')
    team_size = int(config.get('team_size', 1))
    log.debug(f'team_size: {team_size}')

    if team_size > 1:
        log.debug('Team Swiss pairing mode')
        team_stats = updateTeamStats(players_dict, stats_dict)
        teams = list(team_stats.keys())
        sorted_teams = sorted(teams, key=lambda t: (
            team_stats[t]['points'],
            team_stats[t]['wins'],
            team_stats[t]['draws'],
            team_stats[t]['touchdowns']), reverse=True)

        # Find previous team matchups
        prev_team_games = []
        for i in range(1, len(os.listdir('rounds/'))+1):
            round = loadRound(f'rounds/round{i}.csv')
            for game in round:
                t1 = players_dict.get(game[0], {}).get('Team')
                t2 = players_dict.get(game[1], {}).get('Team')
                if t1 and t2:
                    prev_team_games.append([t1, t2])

        # Ensure even number of teams, no BYE allowed
        if len(sorted_teams) % 2 != 0:
            log.error('Odd number of teams, cannot pair all teams without BYE.')
            return []

        team_pairings = dfs_team_recursive(sorted_teams, prev_team_games)

        if not team_pairings or len(team_pairings) * 2 != len(sorted_teams):
            log.error('No valid team pairings found without BYE.')
            return []

        # For each team pairing, match individual players by rank
        player_pairings = []
        for t1, t2 in team_pairings:
            log.debug(f'Pairing teams: {t1} vs {t2}')
            team1_players = [p for p in players_dict if players_dict[p].get('Team') == t1]
            team1_sorted = sorted(team1_players, key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
            team2_players = [p for p in players_dict if players_dict[p].get('Team') == t2]
            team2_sorted = sorted(team2_players, key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
            for p1, p2 in zip(team1_sorted, team2_sorted):
                log.debug(f'\tPairing players: {p1} vs {p2}')
                player_pairings.append((p1, p2))
            # If teams have unequal number of players, ignore extra players (no BYE)
        return player_pairings
    else:
        log.debug('Individual Swiss pairing mode')
        if (round_number==1): # first round
            log.debug('First round pairing')
            if stats_dict:
                log.debug('Sorting players by rank')
                sorted_players = sorted(players_dict.keys(), key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
            else:
                log.debug('No stats, shuffling players randomly')
                sorted_players = list(players_dict.keys())
                random.shuffle(sorted_players)
            pairings = []
            for i in range(0, len(sorted_players)-1, 2):
                log.debug(f'Pairing: {sorted_players[i]} vs {sorted_players[i+1]}')
                pairings.append([sorted_players[i], sorted_players[i+1]])
            if len(sorted_players) % 2 == 1:
                log.debug(f'Assigning BYE to: {sorted_players[-1]}')
                pairings.append([sorted_players[-1], 'BYE'])
            return pairings
        else:
            log.debug('Subsequent round pairing')
            prev_games = []
            last_round_file = f'rounds/round{round_number-1}.csv'
            if os.path.exists(last_round_file):
                log.debug(f'Loading last round file: {last_round_file}')
                with open(last_round_file, mode='r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    next(reader) # skip header
                    for row in reader:
                        if len(row) < 4:
                            log.error('Round still in progress')
                            return []
                        last_round.append(row)
            for i in range(1, len(os.listdir('rounds/'))+1):
                round = loadRound(f'rounds/round{i}.csv')
                for game in round:
                    prev_games.append([game[0], game[1]])
            pairings = dfs_recursive(players_dict, stats_dict, prev_games)
            return pairings

def dfs_recursive(players_dict, stats_dict, prev_games, pairings=[]):
    """
    Recursively generate valid player pairings using DFS, avoiding repeat matchups.
    Returns a list of pairings.
    """
    log.debug(f'dfs_recursive called')
    if len(pairings) * 2 >= len(players_dict):
        log.debug('All players paired, returning pairings')
        return pairings
    used = set()
    for p1, p2 in pairings:
        used.add(p1)
        used.add(p2)
    remaining = [p for p in players_dict if p not in used]
    log.debug(f'Remaining players: {remaining}')
    if len(remaining) == 1:
        log.debug(f'Only one player left: {remaining[0]}, assigning BYE')
        pairings.append((remaining[0], 'BYE'))
        return pairings
    elif not remaining:
        log.debug('No remaining players, returning pairings')
        return pairings
    # Sort remaining by rank (lowest first)
    sorted_remaining = sorted(remaining, key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
    log.debug(f'Sorted remaining players by rank: {sorted_remaining}')
    p1 = sorted_remaining[0]
    for i in range(1, len(sorted_remaining)):
        p2 = sorted_remaining[i]
        log.debug(f'Trying to pair {p1} with {p2}')
        if [p1, p2] not in prev_games and [p2, p1] not in prev_games:
            log.debug(f'Pair {p1}-{p2} not in previous games, recursing')
            result = dfs_recursive(players_dict, stats_dict, prev_games, pairings + [[p1, p2]])
            if result:
                log.debug(f'Recursion successful for pair {p1}-{p2}')
                return result
            else:
                log.debug(f'Recursion failed for pair {p1}-{p2}')
    log.debug('No valid pairings found, returning empty list')
    return []

def dfs_team_recursive(sorted_teams, prev_games, pairings=[]):
    log.debug(f'dfs_team_recursive called with pairings: {pairings}')
    if len(pairings) * 2 >= len(sorted_teams):
        log.debug('All teams paired, returning pairings')
        return pairings
    used = set()
    for t1, t2 in pairings:
        used.add(t1)
        used.add(t2)
    remaining = [t for t in sorted_teams if t not in used]
    log.debug(f'Remaining teams: {remaining}')
    if len(remaining) == 1:
        log.debug(f'Only one team left: {remaining[0]}, assigning BYE')
        pairings.append((remaining[0], 'BYE'))
        return pairings
    elif not remaining:
        log.debug('No remaining teams, returning pairings')
        return pairings
    t1 = remaining[0]
    for i in range(1, len(remaining)):
        t2 = remaining[i]
        log.debug(f'Trying to pair {t1} with {t2}')
        if [t1, t2] not in prev_games and [t2, t1] not in prev_games:
            log.debug(f'Pair {t1}-{t2} not in previous games, recursing')
            result = dfs_team_recursive(sorted_teams, prev_games, pairings + [(t1, t2)])
            if result:
                log.debug(f'Recursion successful for pair {t1}-{t2}')
                return result
            else:
                log.debug(f'Recursion failed for pair {t1}-{t2}')
    log.debug(f'No valid pairings found for {t1}, assigning BYE')
    pairings.append((t1, 'BYE'))
    return pairings

def updateStats(players, stats, last_round):
    """
    Update player statistics based on the results of the last round.
    Returns a dictionary of updated stats, sorted and ranked.
    """
    # Update points, touchdowns, wins, draws, losses
    for player in players:
        for game in last_round:
            stats.setdefault(player, {key: 0 for key in config['statistics'] + config['additional_statistics']})
            if (game[0] == player) or (game[1] == player):
                p1, p2 = game[0], game[1]
                if (game[2] == '') or (game[3] == ''):
                    raise ValueError('Round still in progress - missing scores')
                t1, t2 = int(game[2]), int(game[3])
                if (p1 == player and t1 > t2) or (p2 == player and t2 > t1):
                    stats[player]["points"] += 4
                    stats[player]["wins"] += 1
                elif t1 == t2:
                    stats[player]["points"] += 2
                    stats[player]["draws"] += 1
                else:
                    stats[player]["points"] += 0
                    stats[player]["losses"] += 1

                stats[player]["touchdown_scored"] += t1 if p1 == player else t2
                break
    ranked_stats = dict(sorted(stats.items(), key=lambda x: (x[1]["points"], x[1]["touchdown_scored"]), reverse=True))
    for rank, player in enumerate(ranked_stats, start=1):
        ranked_stats[player]["rank"] = rank
    return ranked_stats

def updateTeamStats(players_dict, stats_dict):
    """
    Aggregate player statistics into team statistics.
    Returns a dictionary of team stats, sorted by performance.
    """
    team_stats = {}
    for player, pdata in players_dict.items():
        team = pdata.get('Team', None)
        if not team:
            continue
        pstats = stats_dict.get(player, {})
        if team not in team_stats:
            team_stats[team] = {
                'points': 0,
                'touchdowns': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0
            }
        team_stats[team]['points'] += pstats.get('points', 0)
        team_stats[team]['wins'] += pstats.get('wins', 0)
        team_stats[team]['draws'] += pstats.get('draws', 0)
        team_stats[team]['losses'] += pstats.get('losses', 0)
        team_stats[team]['touchdowns'] += pstats.get('touchdowns', 0)     
    
    # Sort teams by points, wins, draws, touchdowns (descending)
    sorted_teams = sorted(
        team_stats.items(),
        key=lambda x: (
            x[1]['points'],
            x[1]['wins'],
            x[1]['draws'],
            x[1]['touchdowns']
        ),
        reverse=True
    )
    return dict(sorted_teams)

if __name__ == '__main__':

    log.basicConfig(format='%(levelname)s - %(message)s', level=args.loglevel.upper())
    log.info(f'Touchdown Tracker v{version}')
    log.debug(f'Config: {config}')

    random.seed(config['random_seed'])

    # Load players info
    players_dict = loadPlayers(filepath=config['players_file'])

    # Compute statistics
    round_number = len(os.listdir('rounds/'))+1
    log.info(f'Round number: {round_number}')
    if (round_number>1):
        log.info(f'Computing statistics...')
        stats_dict = loadStats()
        last_round = loadRound(f'rounds/round1.csv')
        stats_dict = updateStats(players_dict, stats_dict, last_round)
        saveStats(stats_dict)
        if config.get('team_size', 1) > 1:
            team_stats = updateTeamStats(players_dict, stats_dict)
            saveTeamStats(team_stats)
    else:
        stats_dict = {}

    # Generate next round
    log.info(f'Generating round {round_number}...')
    pairings=generatePairing(round_number, players_dict, stats_dict)
    if pairings != []:
        savePairing(round_number, pairings)

