from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('mean-reversion/', views.mean_reversion, name='mean_reversion'),
    path('tma/', views.tma, name='tma'),
]
