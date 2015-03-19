from django.db import models
import datetime

MAX_TEAM_LENGTH = 256
MAX_CONFERENCE_LENGTH = 256
MAX_SPORT_LENGTH = 256
DEFAULT_ELO = 1200
DEFAULT_K_VAL = 25

class Conference(models.Model):
    name = models.CharField(max_length=MAX_CONFERENCE_LENGTH)
    site_id = models.IntegerField(default=0)

class Sport(models.Model):
    name = models.CharField(max_length=MAX_SPORT_LENGTH)
    site_id = models.IntegerField(default=0)

# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=MAX_TEAM_LENGTH)
#    conference = models.ForeignKey(Conference)
    elo = models.FloatField(default=DEFAULT_ELO)
    k_val = models.FloatField(default=DEFAULT_K_VAL)
    wins = models.IntegerField(default=0)
    loses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    site_id = models.IntegerField(default=0)
#    sport = models.ForeignKey(Sport)

class Game(models.Model):
    home = models.ForeignKey(Team, related_name='team1')
    away = models.ForeignKey(Team, related_name='team2')
    score_home = models.IntegerField(default=0)
    score_away = models.IntegerField(default=0)
    simulated = models.BooleanField(default=False)
    site_id = models.IntegerField(default=0)
    date = models.DateTimeField(default=datetime.datetime.now())
