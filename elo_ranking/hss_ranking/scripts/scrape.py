import BeautifulSoup
import requests
import time
import re
import arrow
from skills.elo import EloCalculator, EloGameInfo, EloRating
from skills import Match

import pandas as pd

K_VAL = 25

def get_pages(text):
    page_rgx = "Page [0-9]+ of ([0-9]+)"
    m = re.search(page_rgx, text)
    if m:
        return int(m.group(1)) + 1
    return 0

def get_teams(string):
    return string.replace('@', '').split('\t')

def simulate_season(df):
    calculator = EloCalculator()
    games = df['TEAMS'].unique()
    team_elos = {}
    for game in games:
        teams = get_teams(game)
        for team in teams:
            team_elos[team] = EloRating(1200, K_VAL)

    for index,row in df.iterrows():
        simulate_game(calculator, row, team_elos)

    columns = ('team', 'elo', 'kfactor')
    data = [(k, v.mean, v.k_factor) for k,v in team_elos.iteritems()]
    team_df = pd.DataFrame(data, columns=columns)

    return team_df

def simulate_game(calculator, row, teams):
    team1, team2 = get_teams(row['TEAMS'])
    score1, score2 = row['SCORE'].split('\t')
    #Game not recorded
    if '--' in score1 or '--' in score2:
        print "No scores"
        return

    team1_id = hash(team1)
    team2_id = hash(team2)
    team1_elo = teams.get(team1)
    team2_elo = teams.get(team2)
    if not team1_elo or not team2_elo:
        print "Couldn't match game"
        print row
        return

    if int(score1) > int(score2):
        rank = [1, 2]
    elif int(score1) == int(score2):
        rank = [1, 1]
    else:
        rank = [2, 1]

    game_info = EloGameInfo(1200, 25)
    team_info = Match(
      [ 
        {1: team1_elo},
        {2: team2_elo}
      ],
      rank)

    new_ratings = calculator.new_ratings(team_info, game_info)
    teams[team1] = (new_ratings.rating_by_id(1))
    teams[team2] = (new_ratings.rating_by_id(2))

def get_page_count():
    url = "http://highschoolsports.mlive.com/sprockets/game_search_results/?config=3853&season=2327&sport=200&page={}".format(1)
    req = requests.get(url)
    page = BeautifulSoup.BeautifulSoup(req.text)
    pages = page.find('span', {'class': 'page-of'})
    num_pages = get_pages(pages.text)
    return num_pages

def parse_season(max_pages=None):

    headings = None
    data_rows = []
    num_pages = get_page_count()
    for page_num in range(1,num_pages):
        if max_pages and page_num > max_pages:
            break
        print "Fetching page {}".format(page_num)
        url = "http://highschoolsports.mlive.com/sprockets/game_search_results/?config=3853&season=2327&sport=200&page={}".format(page_num)
        req = requests.get(url)
        time.sleep(1)
        page = BeautifulSoup.BeautifulSoup(req.text)
        table = page.find("div", {"class": "stats-table scores"})
        for row in table.findAll('tr'):
            if row.find('th'):
                if not headings:
                    headings = []
                    cols = row.findAll('th')
                    for col in cols:
                        headings.append(col.text)
            else:
                cols = row.findAll('td')
                content = []
                for col in cols:
                    divs = col.findAll('div')
                    if not divs:
                        #Some rows are just text
                        text = col.text
                    else:
                        text = "\t".join([div.text for div in divs])
                    content.append(text)
                data_rows.append(tuple(content))
    
    games_df = pd.DataFrame(data_rows, columns=headings)
    teams_df = simulate_season(games_df) 
    teams_df = teams_df.sort(columns='elo', ascending=False)
    return teams_df

pass
    
