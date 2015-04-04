from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.db.models import Max

from hss_ranking.models import Team, Game, Conference
import scripts.scrape as scrape
import arrow
import itertools

import pandas as pd

# Create your views here.
def fetch_teams(request):
    teams = Team.objects.all()
    scrape.fetch_teams(teams)
    return HttpResponse("Done")

def test(request):
    date = arrow.utcnow()
    objs = fetch_objs_before(Team, date.datetime)
    df = load_dataframe(objs)
    before =fetch_objs_before(Team, date.replace(days=-7).datetime)

def load_dataframe(qs):
    '''
    QuerySet to dataframe
    '''

#    attrs = Team._meta.get_all_field_names()
    #XXX temporary hack until I flush and migrate the database
    attrs = [x for x in qs[0]._meta.get_all_field_names() if 'history' not in x]
    rs=[[getattr(obj, attr) for attr in attrs if 'history' not in attr] for obj in qs]
    return pd.DataFrame.from_records(rs, columns = attrs)

#def team_deltas(before, after):
    

def fetch_teams(date):
    prev = date.replace(days=-7)
    prev_set = fetch_objs_before(Team, prev.datetime)

def fetch_team(date, obj_id):
    return fetch_objs_before(Team, date.datetime, obj_id=obj_id)[0]

def fetch_objs_before(cls, date, obj_id=None):
    if obj_id:
        objs = cls.history.filter(date__lt=date, pk__in=[obj_id]).values('name').annotate(max_date=Max('date')).order_by()
    else:
        objs = cls.history.filter(date__lt=date).values('name').annotate(max_date=Max('date')).order_by()

    rs = []
    for obj in objs:
        tmp = cls.history.filter(date=obj['max_date'], name=obj['name'])
        rs.append(tmp)
    result_list = list(itertools.chain(*rs))
    return result_list

def fetch(request):
    print "Fetching"
    df = scrape.fetch_season(max_pages=0)
    return HttpResponse("Done")

def parse(request):
    print "Simulating"
    games = Game.objects.filter(simulated=False).order_by("date")
    scrape.simulate_games(games)
    return HttpResponse("Done")

def team_dash(request):
    template = loader.get_template('hss_ranking/team_dash.html')
    context = RequestContext(request, {
        'team_info': 'foo'
    })
    return HttpResponse(template.render(context))

def get_last_sunday(date):
    #Day 0 is Monday
    if date.weekday() == 6:
        return date
    else:
        date = date.replace(days= -1*date.weekday() - 1)
        return date

def get_date(request):
    date = request.GET.get('date')
    if not date:
        date = arrow.utcnow()
    else:
        date = arrow.get(date)
    return get_last_sunday(date)

def team(request, team_id):
    date = get_date(request)
    template = loader.get_template('hss_ranking/team.html')
    team = fetch_team(date, team_id)
    team_info = {}
    team_info['name'] = team.name
    rows = []
    games = Game.objects.filter(home=team, date__lt=date.datetime) 
    for game in games:
        score = "{} - {}".format(game.score_home, game.score_away)
        day = game.date.strftime('%Y-%m-%d')
        rows.append([game.id, day, game.home.name, game.away.name, score])
    games = Game.objects.filter(away=team, date__lt=date.datetime)
    for game in games:
        score = "{} - {}".format(game.score_home, game.score_away)
        day = game.date.strftime('%Y-%m-%d')
        rows.append([game.id, day, game.home.name, game.away.name, score])

    table = {}
    table['columns'] = ['Id', 'Date', 'Home', 'Away', 'Score']
    table['rows'] = rows   

    context_data = general_context()
    context_data.update({
        'table': table,
        'selected_date': date.strftime("%Y-%m-%d"),
        'endDate': arrow.utcnow().strftime("%Y-%m-%d")
     })
    #context = RequestContext(request, {
    #    'team_schedule': data,
    #    'team_info': team_info
    #})
    context = RequestContext(request, context_data)
    return HttpResponse(template.render(context))

def generate_sidebar_options():
    sidebar_data = [
      {
        "name": "Sport",
        "options": [
          {
            "name": "Men's Basketball"
          }
        ]
      },
      {
        "name": "State",
        "options": [
          {
            "name": "Michigan"
          }
        ]
      },
      {
        "name": "Division",
        "options": [
          {
            "name": "1A"
          }
        ]
      }
    ]

    sidebar_data.append(make_options(Conference.objects.all(), "Conference"))
    sidebar_data.append(make_options(Team.objects.all(), "Team"))
    return sidebar_data

def general_context():
    state = {
        "name": "Michigan",
        "id": 0
    }
    sport = {
        "name": "Men's Basketball",
        "id": 0
    }
    division = {
        "name": "1A",
        "id": 0
    }
    conference = {
        "name": "SEC",
        "id": 0
    }

    stats = get_stats()

    ret = {
        'sidebar_data': generate_sidebar_options(),
        'state': state,
        'sport': sport,
        'division': division,
        'conference': conference,
        'header_stats': get_stats()
    }
    return ret

def get_stats():
    #Placeholder stats
    stats = [
      {
        "delta": "up",
        "title": "Spread",
        "measure": "20.2",
        "delta_measure": "2.2"
      },
      {
        "delta": "null",
        "title": "Rank",
        "measure": "1",
        "delta_measure": "0.0"
      },
      {
        "delta": "up",
        "title": "Games",
        "measure": "724",
        "delta_measure": "20"
      },
      {
        "delta": "down",
        "title": "Elo",
        "measure": "1151.124",
        "delta_measure": "14.5"
      }
    ]
    return stats

def teams(request):
    template = loader.get_template('hss_ranking/teams.html')
    rows = []
    rank = 1

    teams = list(Team.objects.all())
    teams.sort(key=lambda x: x.elo, reverse=True)
    for team in teams:
        rows.append([team.id, rank, team.name, team.wins, team.loses, team.elo])
        rank += 1
    table = {}
    table['columns'] = ['Id', 'Rank', 'Name', 'Wins', 'Loses', 'Elo']
    table['rows'] = rows   

    context_data = general_context()
    context_data.update({
        'table': table,
        'endDate': '2015-03-22'
     })
    context = RequestContext(request, context_data)
    return HttpResponse(template.render(context))

def make_options(objs, name):
    ret = {
        "name": name,
        "options": []
    }
    for obj in objs:
        ret['options'].append({'name': obj.name, 'id': obj.id})
    return ret
