from kik.messages import TextMessage, PictureMessage, messages_from_json,SuggestedResponseKeyboard,\
                        TextResponse, LinkMessage,StartChattingMessage, CustomAttribution

from bot import kik, access_token,FB_PAGE_TOKEN
from messengerbot import MessengerClient, attachments, templates, elements
from messengerbot import messages as fbmessages
fbmessenger = MessengerClient(access_token=FB_PAGE_TOKEN)

def dispatchMessage(context,msg_type,*args,**kwargs):
    if context['platform'] == 'KIK':
        if msg_type == 'text':
            sendKikTextMessages(*args,**kwargs)
    if context['platform'] == 'FB':
        if msg_type == 'text':
            sendFBMessage(*args,**kwargs)

def sendKikTextMessages(chat_id,from_user,msgs,suggested_responses=[]):
    send_these = []
    for msg in msgs:
        send_these.append(
            TextMessage(
            to=from_user,
            chat_id=chat_id,
            body=msg
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
    
def sendFBMessage(chat_id,from_user,msgs,suggested_responses=[]):
    # TODO: if suggested_response, create object to handle choices
    if not suggested_responses:
        for msg in msgs:
            recipient = fbmessages.Recipient(recipient_id=from_user)
            message = fbmessages.Message(text=msg)
            request = fbmessages.MessageRequest(recipient, message)
            fbmessenger.send(request)