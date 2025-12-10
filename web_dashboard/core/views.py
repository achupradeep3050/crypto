from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings

@login_required
def home(request):
    return render(request, 'core/home.html')

@login_required
def mean_reversion(request):
    context = {'api_url': 'http://localhost:8001'}
    return render(request, 'core/mean_reversion.html', context)

@login_required
def tma(request):
    context = {'api_url': 'http://localhost:8001'}
    return render(request, 'core/tma.html', context)
