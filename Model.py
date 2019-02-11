'''
Models for user,blog,comment.
'''
import time,uuid
from ORM import Model,StringField,BooleanFied,FloatField,TextField
def next_id():
		return '%015d%s000' %(int(time.time()*1000),uuid.uuid4().hex)
class User(Model):
	__table__ = 'user'
	id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
	email = StringField(ddl='varchar(50)')
	password = StringField(ddl='varchar(50)')
	admin = BooleanFied()
	name = StringField(ddl='varchar(50)')
	image = StringField(ddl='varchar(50)')
	created_at = FloatField(default = time.time)
class Blog(Model):
	__table__ = 'blogs'
	id = StringField(primary_key = True,default = next_id,ddl='varchar(50)')
	user_id = StringField(ddl ='varchar(50)')
	user_image = StringField(ddl='varchar(500)')
	name = StringField(ddl='varchar(50)')
	summary = StringField(ddl='varchar(200)')
	content = TextField()
	created_at = FloatField(default = time.time)
class Comment(Model):
	__table__ = 'comment'
	id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
	blog_id = StringField(ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	user_name = StringField(ddl='varchar(50)')
	user_image = StringField(ddl = 'varchar(500)')
	content = TextField()
	created_at = FloatField(default = time.time)

