from kik.messages import TextMessage, PictureMessage, SuggestedResponseKeyboard,\
                        TextResponse, LinkMessage,StartChattingMessage, CustomAttribution

from bot import kik,FB_PAGE_TOKEN
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
    if msg_type == 'link':
        return LinkMessage(to=to,chat_id=chat_id,url=content)
    
def sendKikMessages(chat_id,from_user,msgs,suggested_responses=[],msg_type=None):
        
    send_these = []
    for msg in msgs:
        send_these.append(abstract_kik_message(
            to=from_user,
            chat_id=chat_id,
            content=msg,
            msg_type=msg_type
            ))
    if msg_type == 'text' and suggested_responses:
        text_resonses = [TextResponse(r) for r in suggested_responses]

        send_these[-1].keyboards.append(
            SuggestedResponseKeyboard(
            responses=text_resonses
            )
        )
    kik.send_messages(send_these)
    
def sendFBMessage(chat_id,from_user,msgs,suggested_responses=[],msg_type=None,extras=[]):
    # TODO: if suggested_response, create object to handle choices
    # if suggested responses > 3
    recipient = fbmessages.Recipient(recipient_id=from_user)
    if msg_type == 'text':
        if not suggested_responses:
            text_messages = msgs
        else:
            text_messages = msgs[:-1]
        for msg in text_messages:
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
    if msg_type == 'image':
        elmnts = []

        for i, url in enumerate(msgs):
            buttons = []
            buttons.append(elements.PostbackButton(
                    title="I like this one",
                    payload="I like number {}st".format(i+1)
                ))
# WEBSITE DOWN
#            buttons.append(elements.WebUrlButton( 
#                    title="See on gofind site",
#                    url="gofindfashion.com/?{}".format(url)  
#                ))
            buttons.append(elements.PostbackButton(
                    title="See more results",
                    payload="See more like this"
                ))
            title = suggested_responses[i]
            element = elements.Element(title=title[:43],image_url=url,buttons=buttons)
            elmnts.append(element)
            
        template = templates.GenericTemplate(elements=elmnts)
        attachment = attachments.TemplateAttachment(template=template)
        message = fbmessages.Message(attachment=attachment)
        request = fbmessages.MessageRequest(recipient, message)
        fbmessenger.send(request)
    if msg_type == 'link':
        

        for i, url in enumerate(msgs):

            elmnts = []
            buttons = []
            buttons.append(elements.WebUrlButton(
            title="Go to store",
            url=url
                ))
            buttons.append(elements.PostbackButton(
                    title="Search with this pic",
                    payload="Search with this pic"
                ))
            buttons.append(elements.PostbackButton(
                    title="See more results",
                    payload="See more like this"
                ))
            title = suggested_responses[i]
            element = elements.Element(title=title[:43],image_url=extras[i],buttons=buttons)
            elmnts.append(element)
            
            template = templates.GenericTemplate(elements=elmnts)
            attachment = attachments.TemplateAttachment(template=template)
            message = fbmessages.Message(attachment=attachment)
            request = fbmessages.MessageRequest(recipient, message)
            fbmessenger.send(request)
