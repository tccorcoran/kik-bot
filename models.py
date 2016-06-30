from bot import db
from sqlalchemy.dialects.postgresql import JSONB
class Context(db.Model):
    __tablename__ = 'context_logs'
    id = db.Column(db.Integer, primary_key=True)
    from_user = db.Column(db.String(20))
    chat_id = db.Column(db.String(64))
    context = db.Column(JSONB)
    msg = db.Column(db.Text())
    action = db.Column(db.String(64))
    
    def __init__(self,chat_id,from_user,context,msg=None,action=None):
        self.from_user = from_user
        self.chat_id = chat_id
        self.context = context
        self.msg = msg
        self.action = action

class TextQueryResults(db.Model):
    __tablename__ = 'text_query_results'
    id = db.Column(db.Integer, primary_key=True)
    from_user = db.Column(db.String(20))
    chat_id = db.Column(db.String(64))
    text_results  = db.Column(JSONB)
    
    def __init__(self,chat_id,from_user,text_results):
        self.from_user = from_user
        self.chat_id = chat_id
        self.text_results = text_results
    
class ImageQueryResults(db.Model):
    __tablename__ = 'image_query_results'
    id = db.Column(db.Integer, primary_key=True)
    from_user = db.Column(db.String(20))
    chat_id = db.Column(db.String(64))
    image_results  = db.Column(JSONB)
    def __init__(self,chat_id,from_user,image_results):
        self.from_user = from_user
        self.chat_id = chat_id
        self.image_results = image_results