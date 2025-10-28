# touchdowntracker.py

import os
import random
import csv
import yaml
import logging as log
from pathlib import Path
import argparse
import sys

version = 0.1
with open('config/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Global argparse setup
parser = argparse.ArgumentParser(description='Touchdown Tracker')
parser.add_argument('--loglevel', type=str, default='INFO', help='Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
args = parser.parse_args()

def loadPlayers(filepath='config/players.csv'):
    """
    Load player data from a CSV file into a dictionary.
    Each player is keyed by name, with their attributes as values.
    """
    players = {}
    teams = {}
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f'{filepath} not found.')

    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        header = next(reader)
        has_team = 'Team' in header

        for row in reader:
            if len(row) < len(header):
                continue  # skip malformed lines
            player_data = dict(zip(header, row))
            name = player_data.get('Player', row[0])
            players[name] = player_data

            if has_team:
                team_name = player_data.get('Team')
                if not team_name:  # enforce every player has a team
                    raise ValueError(f"Player '{name}' has no team assigned.")
                teams.setdefault(team_name, []).append(name)

    # If we have teams, validate team sizes
    if has_team and teams:
        team_sizes = {team: len(roster) for team, roster in teams.items()}
        unique_sizes = set(team_sizes.values())
        if len(unique_sizes) > 1:
            mismatch = ", ".join(f"{t}: {s}" for t, s in team_sizes.items())
            raise ValueError(f"Inconsistent team sizes detected -> {mismatch}")
        config['team_size'] = unique_sizes.pop()
        config['teams'] = teams

    return players
    
def loadStats(filepath='stats/statistics.csv'):
    """
    Load player statistics from a CSV file into a dictionary.
    If the file does not exist, create it with the appropriate header.
    """
    stats = {}
    path = Path(filepath)
    if not path.exists():
        # Create file with header
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Player', 'Rank', 'Points', 'Touchdowns', 'Wins', 'Draws', 'Losses'])
        return stats
    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader) # skip first line
        for row in reader:
            if len(row) < 7:
                continue # skip malformed lines
            name = row[0]
            rank = int(row[1])
            points = int(row[2])
            touchdowns = int(row[3])
            wins = int(row[4])
            draws = int(row[5])
            losses = int(row[6])
            stats[name] = {
                "rank": rank,
                "points": points,
                "touchdowns": touchdowns,
                "wins": wins,
                "draws": draws,
                "losses": losses
            }
    return stats

def loadRound(filepath='rounds/round1.csv'):
    """
    Load a round's results from a CSV file.
    Returns a list of match results for the round.
    """
    round = []
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f'{filepath} not found')
    team_size = int(config.get('team_size', 1))
    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader) # skip first line
        for row in reader:
            if team_size > 1:
                if len(row) < 6:
                    continue # skip malformed lines
                round.append([row[2], row[3], row[4], row[5]]) # PlayerA, PlayerB, TouchdownA, TouchdownB
            else:
                if len(row) < 4:
                    continue # skip malformed lines
                round.append([row[0], row[1], row[2], row[3]])
    return round

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

        # Pair teams so that no BYE is assigned and no repeat matches
        def team_pairing_dfs(teams, prev_games, pairings=[]):
            if len(pairings) * 2 == len(teams):
                return pairings
            used = set()
            for t1, t2 in pairings:
                used.add(t1)
                used.add(t2)
            remaining = [t for t in teams if t not in used]
            if not remaining:
                return pairings
            t1 = remaining[0]
            for i in range(1, len(remaining)):
                t2 = remaining[i]
                if [t1, t2] not in prev_games and [t2, t1] not in prev_games:
                    result = team_pairing_dfs(teams, prev_games, pairings + [(t1, t2)])
                    if result:
                        return result
            return []

        team_pairings = team_pairing_dfs(sorted_teams, prev_team_games)

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
            stats.setdefault(player, {"rank": 0, "points": 0, "touchdowns": 0, "wins": 0, "draws": 0, "losses": 0})
            if (game[0] == player) or (game[1] == player):
                p1, p2 = game[0], game[1]
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

                stats[player]["touchdowns"] += t1 if p1 == player else t2
                break
    ranked_stats = dict(sorted(stats.items(), key=lambda x: (x[1]["points"], x[1]["touchdowns"]), reverse=True))
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

def savePairing(round_number, pairing):
    """
    Save the pairings for a round to a CSV file.
    Handles both team and individual formats.
    """
    filepath = f'rounds/round{round_number}.csv'
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Need access to players_dict for team info
    from inspect import currentframe
    frame = currentframe()
    players_dict = frame.f_back.f_locals.get('players_dict', {})
    team_size = int(config.get('team_size', 1))

    with open(path, mode='w', encoding='utf-8', newline="") as file:
        writer = csv.writer(file)
        if team_size > 1:
            writer.writerow(['TeamA', 'TeamB', 'PlayerA', 'PlayerB', 'TouchdownA', 'TouchdownB'])
            for game in pairing:
                pA, pB = game[0], game[1]
                teamA = players_dict.get(pA, {}).get('Team', '') if pA != 'BYE' else 'BYE'
                teamB = players_dict.get(pB, {}).get('Team', '') if pB != 'BYE' else 'BYE'
                writer.writerow([teamA, teamB, pA, pB, '', ''])
        else:
            writer.writerow(['PlayerA', 'PlayerB', 'TouchdownA', 'TouchdownB'])
            for game in pairing:
                writer.writerow([game[0], game[1], '', ''])
    log.info(f'{path} saved.')

def saveStats(stats, filepath='stats/statistics.csv'):
    """
    Save player statistics to a CSV file.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, mode='w', encoding='utf-8', newline="") as file:
        writer = csv.writer(file)
        writer.writerow(['Player', 'Rank', 'Points', 'Touchdowns', 'Wins', 'Draws', 'Losses'])
        for player in stats:
            s = stats[player]
            writer.writerow([
                player,
                s.get('rank', 0),
                s.get('points', 0),
                s.get('touchdowns', 0),
                s.get('wins', 0),
                s.get('draws', 0),
                s.get('losses', 0)
            ])
    log.info(f'{filepath} saved.')

def saveTeamStats(team_stats, filepath='stats/team_statistics.csv'):
    """
    Save team statistics to a CSV file.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, mode='w', encoding='utf-8', newline="") as file:
        writer = csv.writer(file)
        writer.writerow(['Team', 'Points', 'Touchdowns', 'Wins', 'Draws', 'Losses', 'Players'])
        for team, stats in team_stats.items():
            writer.writerow([
                team,
                stats.get('points', 0),
                stats.get('wins', 0),
                stats.get('draws', 0),
                stats.get('losses', 0),
                stats.get('touchdowns', 0)
            ])
    log.info(f'{filepath} saved.')

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

