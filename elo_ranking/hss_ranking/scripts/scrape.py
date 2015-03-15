import BeautifulSoup
import requests
import time
import re
import arrow
import urllib
from skills.elo import EloCalculator, EloGameInfo, EloRating
from skills import Match

from hss_ranking.models import Game, Team, Conference

import pandas as pd

K_VAL = 25
SLEEP_TIME = 1

def get_site_id(name):
    url = "http://highschoolsports.mlive.com/find_school/?q={}".format(name.lower())
    r = requests.get(url)
    urls = r.json()
    for url in urls:
        if url.get("name").lower() == name.lower():
            return url.get("id")     

def get_team(name):
    team,exists = Team.objects.get_or_create(name=name)
    if not team.site_id:
        site_id = get_site_id(team.name)
        if site_id:
            team.site_id = site_id
        else:
            print "Could not get id for {}".format(team.name)

    team.save()
    return team

def add_game(team1, team2, score1, score2):

    #To avoid duplicates always sort by name to ensure that we don't get
    #duplicate games
    teams = [(team1, score1), (team2, score2)]
    teams.sort(key = lambda x: x[0])
    obj1, obj2 = teams
    team1, score1 = obj1
    team2, score2 = obj2

    #Lookup the teams and create them if they don't exist
    team1_obj = get_team(team1)
    team2_obj = get_team(team2)
    game,exists = Game.objects.get_or_create(
      team1=team1_obj, 
      team2=team2_obj, 
      score1=score1, 
      score2=score2
    )
    if not exists:
        game.save()
    else:
        print "New game"

def get_pages(text):
    page_rgx = "Page [0-9]+ of ([0-9]+)"
    m = re.search(page_rgx, text)
    if m:
        return int(m.group(1)) + 1
    return 0

def get_teams(string):
    return string.replace('@', '').split('\t')

def parse_games(df, team):
    for index,row in df.iterrows():
        parse_game(row, team)

def simulate_games(games):
    calculator = EloCalculator()
    games = Game.objects.all()
    for game in games:
        simulate_game(calculator, game)

def parse_game(row, team):
    try:
        team1, team2 = get_teams(row['TEAMS'])
    except KeyError:
        team1 = team.name
        team2 = row['OPPONENT'].replace('@', '')
    except ValueError:
        print "Couldn't unpack {}".format(row['TEAMS'])
        return

    #Sigh, game results can come in many interesting flavors
    for k in ['SCORE', 'RESULT']:
        try:
            pat = "([0-9]+)-([0-9]+)"
            m = re.search(pat, row[k])
            if m: 
                score1 = m.group(1)
                score2 = m.group(2)
            else:
                score1, score2 = row[k].split('\t')
        except KeyError:
            pass
        except ValueError:
            print "Couldn't unpack score {}".format(row[k])
            return

    #Game not recorded
    if '--' in score1 or '--' in score2:
        print "No scores"
        return
    add_game(team1, team2, score1, score2)

def simulate_game(calculator, game):

    if game.simulated:
        return

    team1 = game.team1
    team2 = game.team2

    if game.score1 > game.score2:
        rank = [1, 2]
        team1.wins += 1
        team2.loses += 1
    else:
        rank = [2, 1]
        team1.loses += 1
        team2.wins += 1

    game_info = EloGameInfo(1200, 25)
    team_info = Match(
      [ 
        {1: (team1.elo, team1.k_val)},
        {2: (team2.elo, team2.k_val)}
      ],
      rank)

    new_ratings = calculator.new_ratings(team_info, game_info)
    team1.elo = new_ratings.rating_by_id(1).mean
    team2.elo = new_ratings.rating_by_id(2).mean
    team1.k_val = new_ratings.rating_by_id(1).k_factor
    team2.k_val = new_ratings.rating_by_id(2).k_factor
    print "simulated {} vs {} [{} - {}]".format(team1.name, team2.name, game.score1, game.score2)   
    game.simulated=True
    team1.save()
    team2.save()
    game.save()

def get_page_count():
    url = "http://highschoolsports.mlive.com/sprockets/game_search_results/?config=3853&season=2327&sport=200&page={}".format(1)
    req = requests.get(url)
    page = BeautifulSoup.BeautifulSoup(req.text)
    pages = page.find('span', {'class': 'page-of'})
    num_pages = get_pages(pages.text)
    return num_pages

def parse_score_table(text, team):
    headings = None
    data_rows = []
    page = BeautifulSoup.BeautifulSoup(text)
    table = page.find("div", {"class": "stats-table scores"})
    if table:
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
    print "Got {} rows".format(len(data_rows))
    games_df = pd.DataFrame(data_rows, columns=headings)
    parse_games(games_df, team) 
    

def fetch_teams(teams):
    for team in teams:
        get_team(team.name)
        if not team.site_id:
            continue
        base_url = "http://highschoolsports.mlive.com/boysbasketball/schedule/"
        params="game_search_start=&game_search_end=&game_search_school_search={}&game_search_grouping=&game_search_school_search_id_holder={}"
        name = team.name.replace(' ', '+')
        name = urllib.quote_plus(name)
        params = params.format(name,team.site_id)
        url = "{}?{}".format(base_url, params)
        #Uses + for space
        req = requests.get(url)
        time.sleep(SLEEP_TIME)
        print "Updating {}".format(team.name)
        parse_score_table(req.text, team)

def fetch_season(max_pages=None):
    num_pages = get_page_count()
    for page_num in range(1,num_pages):
        if max_pages and page_num > max_pages:
            break
        print "Fetching page {}".format(page_num)
        url = "http://highschoolsports.mlive.com/sprockets/game_search_results/?config=3853&season=2327&sport=200&page={}".format(page_num)
        req = requests.get(url)
        parse_score_table(req.text, None)
        time.sleep(SLEEP_TIME)
