from django.shortcuts import render


def index(request):
    return render(request, 'cardgame/index.html')

def play(request):
    type = request.GET.get('type')
    if type == 'default':
        context = {}
    else:
        context = {'extrascript': 'js/cardgame/' + type + '.js'}
    return render(request, 'cardgame/play.html', context)
