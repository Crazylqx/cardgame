"""qxsite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from login import views as loginViews

urlpatterns = [
    path('', loginViews.index),
    path('admin/', admin.site.urls),
    path('cardgame/', include('cardgame.urls')),
    path('login/', loginViews.login),
    path('register/', loginViews.register),
    path('logout/', loginViews.logout),
    path('findpassword/', loginViews.findpassword),
    path('confirm/', loginViews.user_confirm),
    path('captcha', include('captcha.urls')),
]
