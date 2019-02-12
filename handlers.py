' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id

@get('/')
async def index(request):
	summary = '这是我的第一个网站'
	blogs =[
		Blog(id='1', name='python新手',summary=summary,created_at=time.time()-300),
		Blog(id='2', name='super余的',summary=summary,created_at=time.time()-5000),
		Blog(id='3', name='测试日志',summary=summary,created_at=time.time()-200000)
	]
	return{
		'__template__': 'blogs.html',
		'blogs': blogs
	}