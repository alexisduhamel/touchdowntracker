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

        # Find previous team matchups
        prev_team_games = []
        for i in range(1, len(os.listdir('rounds/'))+1):
            round = loadRound(f'rounds/round{i}.csv')
            for game in round:
                t1 = game[0]
                t2 = game[1]
                if t1 and t2:
                    prev_team_games.append([t1, t2])

        # Ensure even number of teams, no BYE allowed
        #if len(teams) % 2 != 0:
        #    log.error('Odd number of teams, cannot pair all teams without BYE.')
        #    return []
        print("previous games")
        print(prev_team_games)
        team_pairings = dfs_team_recursive(teams, prev_team_games)

        #if not team_pairings or len(team_pairings) * 2 != len(teams):
        #    log.error('No valid team pairings found without BYE.')
        #    return []

        # For each team pairing, match individual players by rank
        player_pairings = []
        for t1, t2 in team_pairings:
            log.debug(f'Pairing teams: {t1} vs {t2}')
            if t1 == 'BYE':
                team1_sorted = ['BYE' for _ in range(team_size)]
                team2_players = [p for p in players_dict if players_dict[p].get('Team') == t2]
                team2_sorted = sorted(team2_players, key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
            elif t2 == 'BYE':
                team2_sorted = ['BYE' for _ in range(team_size)]
                team1_players = [p for p in players_dict if players_dict[p].get('Team') == t1]
                team1_sorted = sorted(team1_players, key=lambda p: stats_dict.get(p, {}).get('rank', 9999)) 
            else:
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
    for player in players:
        for game in last_round:
            stats.setdefault(player, {key: 0 for key in config['base_statistics'] + config['statistics'] + config['additional_statistics']})
            if (game[2] == player) or (game[3] == player):
                # Update points, wins, draws and losses
                p1, p2 = game[2], game[3]
                if (game[4] == '') or (game[5] == ''):
                    raise ValueError('Round still in progress - missing scores')
                t1, t2 = int(game[4]), int(game[5])
                log.debug(f'Updating W/D/L and touchdowns for player {player}')
                if (p1 == player and t1 > t2) or (p2 == player and t2 > t1):
                    stats[player]["points"] += 4
                    stats[player]["wins"]   += 1
                elif t1 == t2:
                    stats[player]["points"] += 2
                    stats[player]["draws"]  += 1
                else:
                    stats[player]["points"] += 0
                    stats[player]["losses"] += 1

                # Update touchdowns scored/conceded (always first two columns after player names)
                stats[player]["touchdown_scored"]   += t1 if p1 == player else t2
                stats[player]["touchdown_conceded"] += t2 if p1 == player else t1
                stats[player]["touchdown_diff"]     = stats[player]["touchdown_scored"] - stats[player]["touchdown_conceded"]
                
                # Get column headers from first row
                with open(f'rounds/round{round_number-1}.csv', 'r', encoding='utf-8') as f:
                    headers = next(csv.reader(f))
                
                # Update stats based on header positions
                for stat in config['statistics'] + config['additional_statistics']:
                    if stat not in config['base_statistics']: # Exclude mandatory stats
                        # Look for both statA and statB variations in headers
                        stat_a = f"{stat}A"
                        stat_b = f"{stat}B"
                        
                        if stat_a in headers and stat_b in headers:
                            idx_a = headers.index(stat_a)
                            idx_b = headers.index(stat_b)
                            # Add stat value based on whether player is A or B
                            if p1 == player:
                                log.debug(f'Updating stat {stat} for player {player} from column {idx_a}')
                                stats[player][stat] += float(game[idx_a]) if game[idx_a] else 0
                            else:
                                log.debug(f'Updating stat {stat} for player {player} from column {idx_b}')
                                stats[player][stat] += float(game[idx_b]) if game[idx_b] else 0
                        else:
                            log.warning(f'Statistic {stat} not found in headers')
    # Build sort key from indiv_tie_breakers
    from globals import _tie_break_to_stat
    sort_key_stats = []
    for tie_break in config.get('indiv_tie_breakers', []):
        if tie_break in _tie_break_to_stat:
            log.debug(f'Sorting by tie breaker: {tie_break}')
            sort_key_stats.append(_tie_break_to_stat[tie_break])
    
    # If no tie breakers defined, fall back to points and touchdown_scored
    if not sort_key_stats:
        sort_key_stats = ['points', 'touchdown_scored']
    
    # Sort by the dynamic tie breaker keys
    def sort_key(item):
        player_stats = item[1]
        return tuple(player_stats.get(stat, 0) for stat in sort_key_stats)
    
    ranked_stats = dict(sorted(stats.items(), key=sort_key, reverse=True))
    for rank, player in enumerate(ranked_stats, start=1):
        ranked_stats[player]["rank"] = rank
    return ranked_stats

def updateTeamStats(players_dict, stats_dict):
    """
    Aggregate player statistics into team statistics.
    Returns a dictionary of team stats, sorted by performance using team_tie_breakers.
    """
    team_stats = {}
    for player, pdata in players_dict.items():
        team = pdata.get('Team', None)
        if not team:
            continue
        pstats = stats_dict.get(player, {})
        if team not in team_stats:
            team_stats[team] = {key: 0 for key in config['base_statistics'] + config['statistics'] + config['additional_statistics']}
        
        # Aggregate all stats from player to team
        for stat_key in team_stats[team]:
            team_stats[team][stat_key] += pstats.get(stat_key, 0)
    
    # Build sort key from team_tie_breakers
    sort_key_stats = []
    for tie_break in config.get('team_tie_breakers', []):
        from globals import _tie_break_to_stat
        if tie_break in _tie_break_to_stat:
            log.debug(f'Sorting teams by tie breaker: {tie_break}')
            sort_key_stats.append(_tie_break_to_stat[tie_break])
    
    # If no tie breakers defined, fall back to points and touchdown_scored
    if not sort_key_stats:
        sort_key_stats = ['points', 'touchdown_scored']
    
    # Sort by the dynamic tie breaker keys
    def sort_key(item):
        team_stats_vals = item[1]
        return tuple(team_stats_vals.get(stat, 0) for stat in sort_key_stats)
    
    sorted_teams = dict(sorted(team_stats.items(), key=sort_key, reverse=True))
    for rank, team in enumerate(sorted_teams, start=1):
        sorted_teams[team]["rank"] = rank
    return sorted_teams

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
        log.info(f'Computing individual statistics...')
        stats_dict = loadStats()
        last_round = loadRound(f'rounds/round1.csv')
        stats_dict = updateStats(players_dict, stats_dict, last_round)
        saveStats(stats_dict)
        if config.get('team_size', 1) > 1:
            log.info(f'Computing team statistics...')
            team_stats = updateTeamStats(players_dict, stats_dict)
            saveTeamStats(team_stats)
    else:
        stats_dict = {}

    # Generate next round
    log.info(f'Generating round {round_number}...')
    pairings=generatePairing(round_number, players_dict, stats_dict)
    if pairings != []:
        savePairing(round_number, pairings)

