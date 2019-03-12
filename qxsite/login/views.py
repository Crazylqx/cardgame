from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import EmailMultiAlternatives
from login import models, forms
import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from qxsite.settings import USER_TTL

def get_online_user_id(session):
    id = session.get('user_id', None)
    if id == None:
        session.flush()
    else:
        state = cache.get('user.' + str(id))
        if state == None:
            session.flush()
        else:
           return id
    return None

def get_online_user(session):
    id = get_online_user_id(session)
    if id:
        try:
            user = models.User.objects.get(id = id)
            return user
        except ObjectDoesNotExist:
            session.flush()
    return None


def index(request):
    user = get_online_user(request.session)
    if user:
        name = user.name
        return render(request, 'index.html', {'name': name})
    else:
        return render(request, 'index.html')

def login(request):
    if request.method == "POST":
        login_form = forms.UserForm(request.POST)
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            try:
                user = models.User.objects.get(name = username)
                if not user.confirmed:
                    if confirm_out_of_date(user):
                        user.delete()
                    else:
                        message = "该用户还未通过邮件确认！"
                        return render(request, 'login/login.html', {'message': message, 'login_form': login_form})
                elif(check_password(password, user.password)):
                    request.session['user_id'] = user.id
                    user_key = 'user.' + str(user.id)
                    user_cache = cache.get(user_key)
                    if user_cache == None:
                        user_cache = {
                            'name': user.name,
                            'gender': user.gender,
                        }
                    cache.set('user.' + str(user.id), user_cache, timeout = USER_TTL)
                    next = request.GET.get('next', None)
                    if next:
                        return redirect(next)
                    return redirect('/')
            except:
                pass
            message = '用户名或密码错误'
        else:
            message = '请检查所填写的内容'
        return render(request, 'login/login.html', {'message': message, 'login_form': login_form})
    else:
        # GET
        if get_online_user_id(request.session):
            next = request.GET.get('next', None)
            if next:
                return redirect(next)
            return redirect('/')
        login_form = forms.UserForm()
        next = request.GET.get('next', None)
        return render(request, 'login/login.html', {'login_form': login_form, 'next': next})

def register(request):
    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        if register_form.is_valid():
            username = register_form.cleaned_data['username']
            true_name = register_form.cleaned_data['true_name'].strip()
            password = register_form.cleaned_data['password']
            password2 = register_form.cleaned_data['password2']
            email = register_form.cleaned_data['email']
            sex = register_form.cleaned_data['sex']
            if password != password2:  # 判断两次密码是否相同
                message = '两次输入的密码不同！'
            else:
                message = check_reg(username, true_name, password)
                if(message == None):
                    # 建立新用户
                    user = models.User()
                    user.name = username
                    user.true_name = true_name
                    user.password = make_password(password)
                    user.email = email
                    user.gender = sex
                    # 发送确认邮件
                    code = make_confirm_code(user)
                    user.confirm_code = code
                    user.save()
                    send_confirm_email(email, user.id, code)
                    return render(request, 'login/confirm.html', {'message': '请前往注册邮箱确认'})
        else:
            message = '请检查所填写的内容'
        return render(request, 'login/register.html', {'message': message, 'register_form': register_form})
    register_form = forms.RegisterForm()
    return render(request, 'login/register.html', {'register_form': register_form})

def make_confirm_code(user):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    code = make_password(user.name + now)
    return code

def send_confirm_email(email, uid, code):
    subject = '来自李权熹个人网站的注册确认邮件'
    url = 'http://{}/confirm/?uid={}&code={}'.format(settings.MY_HOST, uid, code)
    text_content = '''
                    您好，欢迎您在李权熹的个人网站进行注册。请访问{}完成注册确认。此链接有效期为{}天。
                    '''.format(url, settings.CONFIRM_DAYS)
    html_content = '''
                    <p>您好，欢迎您在李权熹的个人网站进行注册。</p>
                    <p>请点击<a href="{}" target=blank>这个链接</a>完成注册确认。</p>
                    <p>此链接有效期为{}天。</p>
                    '''.format(url, settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def check_reg(username, true_name, email):
    same_name_user = models.User.objects.filter(name=username)
    if same_name_user:
        u = same_name_user[0]
        if confirm_out_of_date(u):
            u.delete()
        else:
            return '用户已存在'
    if len(true_name) == 0:
        return '姓名不能为空'
    same_email_user = models.User.objects.filter(email=email)
    if same_email_user:
        return '该邮箱地址已被注册'
    return None

def logout(request):
    id = get_online_user_id(request.session)
    if id:
        request.session.flush()
        cache.delete('user.' + str(id))
    return redirect('/')

def findpassword(request):
    return render(request, 'login/findpassword.html/')

def user_confirm(request):
    uid = request.GET.get('uid', None)
    code = request.GET.get('code', None)
    try:
        user = models.User.objects.get(id=uid)
        if confirm_out_of_date(user):
            user.delete()
            message = '您的邮件已经过期！请重新注册!'
        elif user.confirmed == False and user.confirm_code == code:
            user.confirmed = True
            user.save()
            message = '感谢确认，请使用账户登录！'
        else:
            message = '无效的确认请求！'
    except:
        message = '无效的确认请求！'
    return render(request, 'login/confirm.html', {'message': message})

def confirm_out_of_date(user):
    return (not user.confirmed) and user.registerTime + datetime.timedelta(settings.CONFIRM_DAYS) < datetime.datetime.now()