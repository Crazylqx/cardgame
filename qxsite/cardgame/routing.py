from django.urls import path
from cardgame import consumers

websocket_urlpatterns = [
    path('ws/cardgame/', consumers.GameConsumer),
]