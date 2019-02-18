' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post
from apis import Page,APIValueError,APIResourceNotFoundError

from models import User, Comment, Blog, next_id
from config import configs

COOKIE_NAME = 'awesession'
_COOKIE_KEY =  configs.session.secret

def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

def get_page_index(page_str):
	p=1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p
def user2cookie(user,max_age):
	'''
	用户生成cookie字符串
	'''
	#通过这个方式构建cookie字符串：id-到期时间-sha1
	expires = str(int(time.time() + max_age))
	s = '%s-%s-%s-%s' %(user.id,user.passwd,expires,_COOKIE_KEY)
	L = [user.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

def text2html(text):
	lines =map(lambda s: '<p>%s</p>' %s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt'),filter(lambda s:s.strip() != '',text.split('\n')))
	return ''.join(lines)
#解密COOKIE
async def cookie2user(cookie_str):
	'''
	如果cookie有效，则解析cookie并加载用户。
	'''
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) !=3:
			return None
		uid,expires,sha1 = L
		if int(expires) < time.time():
			return None
		user = await User.find(uid)
		if user is None:
			return None
		s = '%s-%s-%s-%s' %(uid,user.passwd,expires,_COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		return user
	except Exception as e:
		logging.exception(e)
		return None

#前端页面：

@get('/')#首页
async def index(*,page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return{
		'__template__': 'blogs.html',
        'page':page,
		'blogs': blogs
	}

@get('/blog/{id}')#日志详情页
async def get_blog(id):
	blog = await Blog.find(id)
	comments = await Comment.findAll('blog_id=?',[id],orderBy='created_at desc')
	for c in comments:
		c.html_content = text2html(c.content)
	blog.html_content = markdown2.markdown(blog.content)
	return {
		'__template__': 'blog.html',
		'blog': blog,
		'comments': comments
	}
    
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@get('/register')#注册页面
def register():
	return {
		'__template__':'register.html'
	}
	
@get('/signin')#登录页面
def signin():
	return {
		'__template__': 'signin.html'
	}
	
@post('/api/authenticate')#登录认证
async def authenticate(*,email,passwd):
	if not email:
		raise APIValueError('email','Invalid email')
	if not passwd:
		raise APIValueError('passwd','Invalid password')
	users = await User.findAll('email=?',[email])
	if len(users) == 0:
		raise APIValueError('email','邮箱不存在.')
	user = users[0]
	#检验密码
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd','Invalid password')
	#验证通过，设置COOKIE
	r = web.Response()
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user,ensure_ascii=False).encode('utf-8')
	return r

@get('/signout')#用户注销页
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME,'-deleted-',max_age=0,httponly=True)
	logging.info('user signed out.')
	return r
    
@get('/manage/blogs/create')#创建日志页
def manage_create_blog():
	return {
		'__template__': 'manage_blog_edit.html',
		'id': '',
		'action': '/api/blogs'
	}

@get('/manage/blogs/edit')#修改日志页
def manage_edit_blog(*,id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' %id
    }
 
@get('/manage/comments')#管理评论列表页
def manage_comments(*,page='1'):
    return {
        '__template__':'manage_comments.html',
        'page_index':get_page_index(page)
    }
	
@get('/manage/blogs')#管理日志列表页
def manage_blogs(*,page='1'):
	return {
		'__template__': 'manage_blogs.html',
		'page_index': get_page_index(page)
	}

@get('/manage/users')#用户列表页
def manage_users(*,page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index':get_page_index(page)
    }

#后端API：
@get('/api/blogs')
async def api_blogs(*,page='1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	p = Page(num,page_index)
	if num == 0:
		return dict(page=p, blog=())
	blogs = await Blog.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
	return dict(page=p,blogs=blogs)
    
@get('/api/blogs/{id}')#获取日志
async def api_get_blog(*,id):
	blog = await Blog.find(id)
	return blog
    
@post('/api/blogs')#创建日志
async def api_create_blog(request,*,name,summary,content):
	check_admin(request)
	if not name or not name.strip():
		raise APIValueError('name','name不能为空')
	if not summary or not summary.strip():
		raise APIValueError('summary','摘要不能为空')
	if not content or not content.strip():
		raise APIValueError('content','内容不能为空')
	blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
	await blog.save()
	return blog
    
@post('/api/blogs/{id}')#修改日志
async def api_update_blog(id,request,*,name,summary,content):
    check_admin(request)
    blog = await Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name','标题不能为空')
    if not summary or not summary.strip():
        raise APIValueError('summary','摘要不能为空')
    if not centent or not centent.strip():
        raise APIValueError('centent','内容不能为空')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog
    
@post('/api/blogs/{id}/comments')#创建评论
async def api_create_comment(id,request,*,content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('请先登录')
    if not content or not content.strip():
        raise APIValueError('内容')
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('日志')
    comment = Comment(blog_id=blog.id,user_id=user.id,user_name=user.name,user_image=user.image,content=content.strip())
    await comment.save()
    return comment
    
    
@get('/api/comments')#获取评论
async def api_comments(*,page='1'):
    page_index = get_page_index(page)
    num = await Comment.findNumber('count(id)')
    p = Page(num,page_index)
    if num == 0:
        return dict(page=p,comments=())
    comments = await Comment.findAll(orderBY='created_at desc',limit=(p.offset,p.limit))
    return dict(page=p,comments=comments)
    
@post('/api/comments/{id}/delete')#删除评论
async def api_delete_comments(id,request):
    check_admin(request)
    c = await Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('评论')
    await c.remove()
    return dict(id=id)
    
@post('/api/users')#创建新用户
async def api_register_user(*,email,name,passwd):
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('eamil')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users = await User.findAll('email=?',[email])
	if len(users) > 0:
		raise APIValueError('注册：失败','该邮箱已经在使用中')
	uid = next_id()
	sha1_passwd = '%s:%s' %(uid,passwd)
	user = User(id=uid,name=name.strip(),email=email,passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),image='http://www.gravatar.com/avatar/%s?dd=mm&s=120' %hashlib.md5(email.encode('utf-8')).hexdigest(),admin=True)
	await user.save()
	#制作会话cookie
	r = web.Response()
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user,ensure_ascii=False).encode('utf-8')
	return r
	
@get('/api/users')#获取新用户
async def api_get_users(*,page='1'):
    page_index = get_page_index(page)
    num = await User.findNumber('count(id)')
    p = Page(num,page_index)
    if num == 0:
        return dict(page=p,users=())
    users = await User.findAll(orderBY='created_at desc',limit=(p.offset,p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p,users=users)
 
@post('/api/blogs/{id}/delete')#删除日志
async def api_delete_blog(request,*,id):
    check_admin(request)
    blog = await Blog.find(id)
    await blog.remove()
    return dict(id=id)




    