from django.db import models

MAX_TEAM_LENGTH = 256
MAX_CONFERENCE_LENGTH = 256
MAX_SPORT_LENGTH = 256
DEFAULT_ELO = 1200
DEFAULT_K_VAL = 25

class Conference(models.Model):
    name = models.CharField(max_length=MAX_CONFERENCE_LENGTH)

class Sport(models.Model):
    name = models.CharField(max_length=MAX_SPORT_LENGTH)

# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=MAX_TEAM_LENGTH)
    conference = models.ForeignKey(Conference)
    elo = models.FloatField(default=DEFAULT_ELO)
    k_val = models.FloatField(default=DEFAULT_K_VAL)
    wins = models.IntegerField(default=0)
    loses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    sport = models.ForeignKey(Sport)

class Game(models.Model):
    team1 = models.ForeignKey(Team, related_name='team1')
    team2 = models.ForeignKey(Team, related_name='team2')
    score1 = models.IntegerField(default=0)
    score2 = models.IntegerField(default=0)
