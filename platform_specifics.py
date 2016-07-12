from kik.messages import TextMessage, PictureMessage, messages_from_json,SuggestedResponseKeyboard,\
                        TextResponse, LinkMessage,StartChattingMessage, CustomAttribution

from bot import kik, access_token,FB_PAGE_TOKEN
from messengerbot import MessengerClient, attachments, templates, elements
from messengerbot import messages as fbmessages
fbmessenger = MessengerClient(access_token=FB_PAGE_TOKEN)

def dispatchMessage(context,msg_type,*args,**kwargs):
    kwargs['msg_type'] = msg_type
    if context['platform'] == 'KIK':
        sendKikMessages(*args,**kwargs)
    if context['platform'] == 'FB':
        sendFBMessage(*args,**kwargs)

def abstract_kik_message(to,chat_id,content,msg_type):
    if msg_type == 'text':
        return TextMessage(to=to,chat_id=chat_id,body=content)
    if msg_type == 'image':
        return PictureMessage(to=to,chat_id=chat_id,pic_url=content)
    
def sendKikMessages(chat_id,from_user,msgs,suggested_responses=[],msg_type=None):
        
    send_these = []
    for msg in msgs:
        send_these.append(abstract_kik_message(
            to=from_user,
            chat_id=chat_id,
            content=msg,
            msg_type=msg_type
            ))
    if suggested_responses:
        text_resonses = [TextResponse(r) for r in suggested_responses]
        for sr in suggested_responses:
            send_these[-1].keyboards.append(
                SuggestedResponseKeyboard(
                responses=text_resonses
                )
            )
    kik.send_messages(send_these)
    
def sendFBMessage(chat_id,from_user,msgs,suggested_responses=[],msg_type=None):
    # TODO: if suggested_response, create object to handle choices
    # if suggested responses > 3
    recipient = fbmessages.Recipient(recipient_id=from_user)
    if not suggested_responses:
        text_messages = msgs
    else:
        text_messages = msgs[:-1]
    for msg in text_messages:
        recipient = fbmessages.Recipient(recipient_id=from_user)
        message = fbmessages.Message(text=msg)
        request = fbmessages.MessageRequest(recipient, message)
        fbmessenger.send(request)
        
    if suggested_responses:
        buttons = []
        for suggested_response in suggested_responses:
            
            buttons.append(elements.PostbackButton(
                title=suggested_response,
                payload=suggested_response
            ))
            
        template = templates.ButtonTemplate(
            text=msgs[-1],
            buttons=buttons
        )
        attachment = attachments.TemplateAttachment(template=template)
        message = fbmessages.Message(attachment=attachment)
        request = fbmessages.MessageRequest(recipient, message)
        fbmessenger.send(request)