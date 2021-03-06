#!usr/bin/python
# -*- coding:utf-8 -*-

from captcha.models import CaptchaStore
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_protect 
from django.views.decorators.http import require_http_methods
from firebase import firebase
from main.models import User, Comment

FIREBASE_USERNAME = getattr(settings, 'FIREBASE_USERNAME')
FIREBASE_REPO_URL = getattr(settings, 'FIREBASE_REPO_URL')
FIREBASE_API_SECRET = getattr(settings, 'FIREBASE_API_SECRET')

# Firebase configuration 
authentication = firebase.FirebaseAuthentication(FIREBASE_API_SECRET, FIREBASE_USERNAME, True, True)
firebase_obj = firebase.FirebaseApplication(FIREBASE_REPO_URL, authentication)


@csrf_protect
@require_http_methods(['POST'])
def create_comment(request):

    if all(x in request.POST for x in ['nickname', 'content', 'captcha_key', 'captcha_value']):
        
        # Human validation by captcha form
        captcha_key = request.POST['captcha_key']
        captcha_value = request.POST['captcha_value']
        
        try:
            captcha = CaptchaStore.objects.get(challenge=captcha_value, hashkey=captcha_key)
            captcha.delete()
        except:
            return JsonResponse({'state': 'fail', 'msg': 'Captcha input is not valid'})
        
        comment = Comment(nickname=request.POST['nickname'], content=request.POST['content'])
        comment.save()
        
        update_firebase_database('/comment', 'last_comment_id', comment.id)
        
        return JsonResponse({'state': 'success', 'msg': 'Succeed to create comment', 'comment_id': comment.id})
        
    else:
        return HttpResponse(status=400)


@require_http_methods(['GET'])
def get_comments(request):

    if all(x in request.GET for x in ['first_comment_id', 'last_comment_id']):
        
        first_comment_id = int(request.GET['first_comment_id'])
        last_comment_id = int(request.GET['last_comment_id'])
        
        # Set maximum number of comments per request
        if last_comment_id - 100 > first_comment_id:
            first_comment_id = last_comment_id - 100
        
        comments = list(Comment.objects.filter(id__gte=first_comment_id, id__lte=last_comment_id, is_deleted=False).values())
        
        return JsonResponse({'comments': comments})
        
    else:
        return HttpResponse(status=400)


@require_http_methods(['GET'])
def get_random_spoken_comments(request):

    comments = list(Comment.objects.filter(is_spoken=True, is_deleted=False).order_by('?')[:5].values())
    return JsonResponse({'comments': comments})


@require_http_methods(['GET'])
def search_comment(request):

    if all(x in request.GET for x in ['category', 'keyword']):
        
        category = request.GET['category']
        keyword = request.GET['keyword']
        
        if 'spoken' in request.GET:
            comments = Comment.objects.filter(is_spoken=True, is_deleted=False)
        else:
            comments = Comment.objects.filter(is_deleted=False)
        
        if category == 'id':
            try:
                comments = comments.filter(id=int(keyword))
            except:
                return HttpResponse(status=400)
        elif category == 'nickname':
            comments = comments.filter(nickname__contains=keyword, is_deleted=False)
        elif category == 'content':
            comments = comments.filter(content__contains=keyword, is_deleted=False)
        else:
            return HttpResponse(status=400)
        
        if 'last_comment_id' in request.GET:
            comments = comments.filter(id__lt=int(request.GET['last_comment_id']))
        
        comments = list(comments[:10].values())
        return JsonResponse({'comments': comments})
        
    else:
        return HttpResponse(status=400)


def update_firebase_database(permalink, key, value):
    """
    Update Firebase database
    """
    firebase_obj.put(permalink, key, value)
    return None
