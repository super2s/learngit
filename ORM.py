import asyncio,logging
import aiomysql
def log(sql,args=()):
	logging.info('SQL:%s' %sql)
async def create_pool(loop,**kw):#自动提交事务
	logging.info('create database connection pool..')
	global __pool
	__pool = await aiomysql.create_pool(
		host = kw.get('host','localhost'),#本地主机（host=主机）
		port = kw.get('port',3306),#端口
		user = kw['user'],#用户
		db = kw['db'],
		charset = kw.get('charset','utf8'),#字符集
		autocommit =kw.get('autocommit',True),#自动提交
		maxsize = kw.get('maxsize',10),
		minsize = kw.get('minsize',1),
		loop = loop
	)
async def select(sql,args,size=None):#定义选择函数
	log(sql,args)
	global __pool
	with (await __pool) as conn:
		cur = await conn.cursor(aiomysql.DictCursor)#创建光标
		await cur.execute(sql.replace('?','%s'),args or())#执行查询
		if size:
			rs = await cur.fetchmany(size)
		else:
			rs = await cur.fetchall()
		await cur.close()
		logging.info('rows returned: %s' % len(re))
		return rs
async def execute(sql,args):#定义执行
	log(sql)
	async with __pool.get() as conn:
		if not autocommit:
			await conn.begin()
		try:
			async with conn.cursor(aiomysql.DictCursor) as cur:
				await cur.execute(sql.replace('?','%s'),args)
			if not autocommit:
				await conn.commit()
		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise#出错后引发异常
		return affected#受影响
def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return ','.join(L)
class Field(object):
	def __init__(self,name,column_type,primary_key,default):
		self.name = name 
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default
	def __str__(self):
		return '<%s,%s:%s>' %(self.__class__.__name__,self.column_type,self.name)
class StringField(Field):#字符串字段
	def __init__(self,name=None,primary_key = False,default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)
class BooleanField(Field):
	def __init__(self,name=None,default=False):
		super().__init__(name,'boolean',False,default)
class IntegerField(Field):
	def __init__(self,name=None,primary_key=False,default=0.0):
		super().__init__(name,'text',False,default)
class ModelMetaclass(type):
	def __new__(cls,name,bases,attrs):
		if name =='Model':
			return type.__new__(cls,name,bases,attrs)#排除模块类本身
		#获取table名称
		tableName = attrs.get('__table__',None) or name 
		logging.info('found model:%s (table:%s)' %(name,tableName))
		#获取所有的字段和主键名:
		mappings = dict()
		fields = []
		primaryKey = None
		for k,v in attrs.items():
			if isintance(v,Field):
				logging.info('found mappings:%s ==>%s' %(k,v))
			if v.primary_key:
				#找到主键:
				if primaryKey:
					raise RuntimeError('Duplicate primary key for field:%s' %k)
				primaryKey = key
			else:
				fields.append(k)
		if not primaryKey:
			raise RuntimeError('Primary key not found')#没有发现主键
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f:'`%s`' % f,fieldds))#逃脱的字段
		attrs['__mappings__'] = mappings #保存属性和列的映射关系
		attrs['__table__'] = tableName
		attrs['__primary_key__']  = primaryKey #主键属性名
		attrs['__fields__'] = fields#除主键外的属性名
		#构造默认的选择，插入，更新，和删除语句：
		attrs['__select__']='select `%s`,%s from `%s` '%(primaryKey,','.join(escaped_fields),tableName)
		attrs['__insert__'] ='insert into `%s`(%s,`%s`) values(%s)' %(tableName,','.join(escaped_fields),primaryKey,create_args_string(len(escaped_fields)+1))
		attrs['__update__'] = 'update`%s` set %s where `%s`=?' %(tableName,','.join(map(lambda f:'`%s`=?' %(mappings.get(f).name or f),fields)),primarKey)
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' %(tableName,primaryKey)
		return type.__new__(cls,name,bases,attrs)
class Model(dict):
	def __init__(self,**kw):
		super(Model,self).__init__(**kw)
	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model'object has no attribute '%s'" %key)
	def __setattr__(self,key,value):
		self[key] = value
	def getValue(self,key):
		return getattr(self,key,None)
	def getValueOrDefault(self,key):
		value = getattr(self,key,None)
		if value is None:
			field = self.__mappings__[key]
			if field,default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s:%s' %(key,str(value)))
				setattr(self,key,value)
		return value
	@classmethod
	async def findAll(cls,where=None,args=None,**kw):
		' find object by where clause.'#通过where句子查找对象
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy',None)#orderby排序依据
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit',None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit,int):
				sql.append('?')
				args.extend(limit)
			elif isinstance(limit,tuple) and len(limit) == 2:
				sql.append('?,?')
				argss.extend(limit)
			else:
				raise ValueError('Invalid limit value:%s' %str(limit))#无效限制值
		rs = await select(' '.join(sql),args)
		return [cls(**r) for r in rs]
	@classmethod
	async def findNumber(cls,selectField,where=None,args=None):
		'find number by select and where'#通过选择和位置查找数字
		sql = ['select %s _num_ from `%s` %(selectField,cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql),args,1)
		if len(rs) ==0:
			return None
		return rs[0]['_num_']	
	@classmethod
	async def find(cla,pk):
		'find object by primary key.'
		re = await select('%s where `%s`=?' %(cls.__select__,cls.__primary_key__),[pk],1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])
		
	async def save(self):
		args = list(map(self.getValueOrDefault,self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = await execute(self.__insert__,args)
		if rows !=1:
			logging.warn('failed to insert record: affected rows:%s' %rows)#无法插入记录:受影响的行是
	async def updata(self):
		args = list(map(self.getValue,self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = await execute(self.__update__,args)
		if rows != 1:
			logging.warn('failed to updata by primary key : affected rows:%s' %rows)#无法按主键更新
	async def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = await execute(self.__delete__,args)
		if rows  !=1:
			logging.warn('failed to remove by primary key:affected rows:%s'%rows)#无法通过主键删除

		