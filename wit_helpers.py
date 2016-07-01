
from kik.messages import TextMessage
from models import Context
from bot import kik, db

def first_entity_value(entities, entity):
    if entity not in entities:
        return None
    val = entities[entity][0]['value']
    if not val:
        return None
    return val['value'] if isinstance(val, dict) else val

def last_entity_value(entities, entity):
    if entity not in entities:
        return None
    val = entities[entity][-1]['value']
    if not val:
        return None
    return val['value'] if isinstance(val, dict) else val

def all_entity_values(entities, entity):
    if entity not in entities:
        return None
    all_vals = [x['value'] for x in entities[entity]]
    all_vals = ' '.join(all_vals)
    if not all_vals:
        return None
    return all_vals

def storeContext(chat_id,from_user,context,msg=None,action=None):
    c = Context(chat_id,from_user,context,msg=msg,action=action)
    db.session.add(c)
    db.session.commit()
    
def retrieveContext(chat_id,from_user):
    prev_context_obj = db.session.query(Context).filter(Context.chat_id==chat_id,Context.from_user==from_user).order_by(Context.id.desc()).first()
    if prev_context_obj is not None:
        context = prev_context_obj.context
        return context
    else:
        return {}
    
def say(chat_id, context, msg):
    from_user = context['from_user']
    kik.send_messages([
        TextMessage(
            to=from_user,
            chat_id=chat_id,
            body=msg
            )])

def merge(session_id, context, entities, msg):
    from_user = context['from_user']
    context = retrieveContext(session_id, from_user)
    selection = last_entity_value(entities, 'ordinal')
    search_keywords = all_entity_values(entities, 'search_words')
    if selection:
        context['selected_outfit'] = selection
    if search_keywords:
        context['search_keywords'] = search_keywords
    storeContext(session_id,from_user,context,action='merge')
    return context

def error(session_id, context, e):
    print(str(e))
    
