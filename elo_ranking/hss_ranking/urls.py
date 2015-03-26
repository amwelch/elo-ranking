from django.conf.urls import patterns, url

from hss_ranking import views

urlpatterns = patterns('',
    url(r'^scrape_schedule$', views.fetch, name='scrape_schedule'),
    url(r'^scrape_teams$', views.fetch_teams, name='scrape_team'),
    url(r'^sim$', views.parse, name='parse'),
    url(r'^$', views.teams, name='teams'),
    url(r'^test$', views.test, name='test'),
    url(r'^team/(?P<team_id>\d+)/$', views.team, name='team')
)
