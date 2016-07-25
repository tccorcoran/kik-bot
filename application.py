import os
import requests
import random
from functools import wraps
import base64

from flask import request, Response
from kik.messages import TextMessage, PictureMessage, messages_from_json,SuggestedResponseKeyboard,\
                        TextResponse, LinkMessage,StartChattingMessage, CustomAttribution
from wit import Wit

from bot import app as application
from bot import kik, access_token
import canned_responses
from wit_helpers import say,merge,error, storeContext, retrieveContext
from platform_specifics import dispatchMessage

ENV_TYPE = os.environ.get('ENV_TYPE')
VERBOSE = False 
SHOW_THIS_MANY = 3 # How many pictures to show at once

if ENV_TYPE == 'DEV':
    application.debug = True
    VERBOSE = True


def debug_info(func):
    @wraps(func)
    def tmp(*args, **kwargs):
        if VERBOSE:

            print "Entering:",func.__name__
        return func(*args, **kwargs)
    return tmp

@debug_info
def showFitRoomResults(chat_id,from_user,context):
    """ Sends picture messages through kik using results from Fitroom
    args: chat_id
          from_user
          responseFromAPI:  json from fitroom
    returns:
          responseFromAPI: removed dead image links
    """

    responseFromAPI = context['image_query_result'] 
        # clean up resuts, lots of duplicates in results....
    result_image_urls = [value['imageUrl'] for value in responseFromAPI['images']]

    
    image_query_result_index = int(context['image_query_result_index'])
    i=0
    if image_query_result_index+SHOW_THIS_MANY >= len(result_image_urls):
        say(chat_id,context,"Well, maybe not. Gosh, you're hard to please :/ Try sending me back a pic of something I've showed you already to keep looking.")
        return responseFromAPI
    urls=[]
    titles=[]
    for an_image in result_image_urls[image_query_result_index:]:
        if i >= SHOW_THIS_MANY:
            break
        # some images are blank, they have exactly 5086 or 3084 bytes. This hack
        # skips any images that size. Hacky fix until they fix it on the backend.
        is_blank =requests.head(an_image, headers={'Accept-Encoding': 'identity'})
        if is_blank.headers['content-length'] in ('5086', '3084'):
            responseFromAPI['images'].pop(i)
            continue
        
        urls.append(an_image)
        titles.append(responseFromAPI['images'][i]['title'])
#        print an_image, responseFromAPI['images'][i]['pageUrl']
        i +=1
    dispatchMessage(context,'image',chat_id,from_user,urls,suggested_responses=titles)
    
    context['image_query_result_index'] = i + image_query_result_index # remember which results we've showed
    context['image_query_result'] = responseFromAPI
    storeContext(chat_id,from_user,context,action='showFitroomResults')
    if context['platform'] == 'KIK':
        selectAnImageMsg(chat_id,context)
        return responseFromAPI

@debug_info
def getFitroomResults(chat_id,context):
    """ Call fitroom search api with url of image to search for
        then send results
    """
    image_url = context['user_img_url']
    chat_id = context['chat_id']
    from_user = context['from_user']
    
    # NOTE: this donwloads the image anytime the user is on Facebook
    # really we only need to download if the user sent us the picture (we don't need to download images from textseach results or other preloaded queries)
    if context['platform'] == 'FB':
        img2 = requests.get(image_url).content
        img64 = base64.b64encode(img2)
        api_url = "http://mongodb-dev.us-west-1.elasticbeanstalk.com/api/B64Search/"
        payload = {"DataString": 'data:image/jpeg;base64,'+img64}
    elif context['platform'] == 'KIK':
        api_url = "http://mongodb-dev.us-west-1.elasticbeanstalk.com/api/UrlSearch/"
        payload = {'url':image_url}
        
    r = requests.post(api_url,json=payload)
    responseFromAPI = r.json()


    if r.status_code != 200:
        # Something went wrong with fitroom API!
        say(chat_id,context,canned_responses.error_message()+"Ouch, that hurt my brain. You almost blew my circuts!")
        return Response(status=500)

    # Show the fitroom results, and clean out the bad images from the json
    context['image_query_result_index'] = 0
    context['image_query_result'] = responseFromAPI
    showFitRoomResults(chat_id,from_user,context)
    return Response(status=200)
        
@debug_info
def getShopStyleResults(chat_id,context):
    """
    Run a text search against shopstyle api
    similar in function to getFitroomResults
    """
    from_user = context['from_user']
    context = retrieveContext(chat_id,from_user)
    if 'search_keywords' not in context:
        say(chat_id,context,canned_responses.error_message()+'text_search')
        return Response(Status=200)
    search_keywords = '+'.join(context['search_keywords'].split())
    API_URL = 'http://api.shopstyle.com/api/v2/products?pid=uid7984-31606272-0&format=json&fts={0}&offset=0&limit=10'.format(search_keywords)
    r = requests.get(API_URL)
    api_json = r.json()
    context['text_query_result'] = api_json
    context['text_query_result_index'] = 0
    showShopStyleResults(chat_id,from_user,context)


    return Response(status=200)

@debug_info    
def showShopStyleResults(chat_id,from_user,context):
    api_json = context['text_query_result']
    result_image_urls = [value['image']['sizes']['IPhone']['url'] for value in api_json['products']]
    
    text_query_result_index = int(context['text_query_result_index'])
    i = 0
    if text_query_result_index+SHOW_THIS_MANY >= len(result_image_urls):
        message = "Well, maybe not. Gosh, you're hard to please :/ Try sending me back a pic of something I've showed you already to keep looking."
        sendSuggestedResponseHowTo(chat_id,from_user,message,context)
        return api_json
    urls=[]
    titles=[]
    for an_image in result_image_urls[text_query_result_index:]:
        if i >= SHOW_THIS_MANY:
            break
        title = api_json['products'][i]['brandedName']
        urls.append(an_image)
        titles.append(title)
        if context['platform'] == 'KIK':
            picture_message = PictureMessage(to=from_user, chat_id=chat_id, pic_url=an_image)
            picture_message.attribution = CustomAttribution(name=title)
            kik.send_messages([picture_message])

        i +=1
    if context['platform'] == 'FB':
        dispatchMessage(context,'image',chat_id,from_user,urls,suggested_responses=titles)
    context['text_query_result_index'] = i + text_query_result_index # remember which results we've showed
    context['text_query_result'] = api_json
    storeContext(chat_id,from_user,context,action='showShopStyleResults')
    if context['platform'] == 'KIK':
        selectAnImageMsg(chat_id,context)
        return api_json


@debug_info
def selectAnImageMsg(chat_id,context):
    from_user = context['from_user']
    
    responses = [TextResponse('Digging the first one'),
                   TextResponse('Like the second'),
                   TextResponse("Let's go with the third"),
                   TextResponse('See more like this'),
                   TextResponse('New search')]
    if context['search_type'] == 'image':
        responses.append(TextResponse('See results on the GoFindFashion website'))
    select_an_image_msg = TextMessage(
        to=from_user,
        chat_id=chat_id,
        body=canned_responses.show_outfits()
        )
    select_an_image_msg.keyboards.append(
        SuggestedResponseKeyboard(
                responses=responses
                )
        )   
    kik.send_messages([select_an_image_msg])

@debug_info    
def doSearchEncounter(chat_id,context):
    """
    This fn is used to run through a search encounter
    The user has either sent a pic to search with or used a
    text query by typing 'find me a xxxx', in that case Wit calls doTextSearchEncounter
    which inturn calls doSearchEncounter. doSearchEncounter is called directly when a user sends a pic
    """
    search_type = context['search_type']
    say(chat_id,context,canned_responses.lookup())
    if search_type == 'image':
        getFitroomResults(chat_id,context)
    elif search_type == 'text':
        getShopStyleResults(chat_id,context)

@debug_info    
def searchAgain(chat_id,context):
    """
    User has selected a picture she likes and would like to run a visual search agaist
    this picture. This fn collects the url of the liked picture and sends it to doSearchEncounter
    """
    from_user = context['from_user']
    prev_context = retrieveContext(chat_id,from_user)
    print prev_context.keys()
    if 'image_query_result' not in prev_context and 'text_query_result' not in prev_context:
        say(chat_id,context,canned_responses.error_message())
        return Response(status=200)
    elif  'selected_outfit' not in prev_context:
        say(chat_id,context,canned_responses.error_message())
        return Response(status=200)
    else:
        i = int(prev_context['selected_outfit'])-1
        if prev_context['search_type'] == 'image':
            i = i+ int(prev_context['image_query_result_index'])- SHOW_THIS_MANY 
            user_img_url = prev_context['image_query_result']['images'][i]['imageUrl']
        elif prev_context['search_type'] == 'text':
            i = i+ int(prev_context['text_query_result_index'])- SHOW_THIS_MANY 
            user_img_url = prev_context['text_query_result']['products'][i]['image']['sizes']['Best']['url']
        prev_context['user_img_url'] = user_img_url
        prev_context['search_type'] = 'image'
        storeContext(chat_id,from_user,prev_context,action='searchAgain')
        doSearchEncounter(chat_id, prev_context)
    return Response(status=200)

@debug_info
def buyThis(chat_id,context):
    """
    User has selected a picture she likes, and would like to visit the
    store webpage
    """
    from_user = context['from_user']
    prev_context = retrieveContext(chat_id,from_user)
    if 'image_query_result' not in prev_context and 'text_query_result' not in prev_context:
        say(chat_id,context,canned_responses.error_message()+'query results issue')
    elif  'selected_outfit' not in prev_context:
        say(chat_id,context,canned_responses.error_message()+'selection issuse')
    else:
        i = int(prev_context['selected_outfit'])-1
        if prev_context['search_type'] == 'image':
            i = int(prev_context['image_query_result_index'])-SHOW_THIS_MANY+i
            link = prev_context['image_query_result']['images'][i]['pageUrl']
            title =  prev_context['image_query_result']['images'][i]['title']
            img_url = prev_context['image_query_result']['images'][i]['imageUrl']
            # using a text message to send fitroom results because Kik breaks out links by putting a trailing "/"
            link_message = TextMessage(to=from_user,chat_id=chat_id,body=link)
#            link_message = LinkMessage(to=from_user,chat_id=chat_id,url=link,title=title)
        elif prev_context['search_type'] == 'text':
            
            i = int(prev_context['text_query_result_index'])-SHOW_THIS_MANY+i
            img_url = prev_context['text_query_result']['products'][i]['image']['sizes']['IPhone']['url']
            link = prev_context['text_query_result']['products'][i]['clickUrl']
            title = prev_context['text_query_result']['products'][i]['brandedName']
            link_message = LinkMessage(to=from_user,chat_id=chat_id,url=link,title=title)
        if context['platform'] == 'KIK':
            here = TextMessage(to=from_user,chat_id=chat_id,body="Here ya go:")
            tip = TextMessage(to=from_user,chat_id=chat_id,body="Remember you can search again anytime by sending me a pic ;)")
            tip.keyboards.append(
                SuggestedResponseKeyboard(
                    responses=[TextResponse('See more results'),
                            TextResponse('Search with this pic'),
                            TextResponse('New search')]
            ))
            kik.send_messages([here,link_message,tip])
        elif context['platform'] == 'FB':
            dispatchMessage(context,'link',chat_id,from_user,[link],suggested_responses=[title],extras=[img_url])

@debug_info        
def searchOrbuy(chat_id,context):
    """
    User has selected a picture she likes;
    Present the user with the option to visit the store webpage or search again using the selected picture
    """
    from_user = context['from_user']
    if context['platform'] == 'FB':
        buyThis(chat_id,context)
    else:
        suggested_responses = ['Go to store','Search with this pic','See more results']
        dispatchMessage(context,'text',chat_id,from_user,[canned_responses.like_it()],suggested_responses=suggested_responses)




@debug_info
def doTextSearchEncounter(chat_id,context):
    """
    User has sent a message like 'find me a red sundress'
    this fn is called by Wit when it thinks a phrase has a text_search intention
    """
    from_user = context['from_user']
    context = retrieveContext(chat_id,from_user)
    context['search_type'] = 'text'
    storeContext(chat_id,from_user,context,action='doTextSearchEncounter')
    doSearchEncounter(chat_id,context)

@debug_info
def seeMoreResults(chat_id,context):
    from_user = context['from_user']
    context = retrieveContext(chat_id,from_user)
    say(chat_id,context,canned_responses.see_more())
    if context['search_type'] == 'image':
        showFitRoomResults(chat_id,from_user,context)
    else:
        showShopStyleResults(chat_id,from_user,context)


@debug_info       
def seeResultsOnWebsite(chat_id,context):
    from_user = context['from_user']
    img_url = context['user_img_url']
    msg = LinkMessage(to=from_user,chat_id=chat_id,url='http://gofindfashion.com?'+img_url,title="Go Find Fashion Seach Engine")
    msg.keyboards.append(
            SuggestedResponseKeyboard(
                responses=[TextResponse('See more results'),
                        TextResponse('Search with this pic'),
                        TextResponse('New search')]
        ))
    kik.send_messages([msg])

@debug_info
def sayHi(chat_id,context):
    from_user = context['from_user']
    sendSuggestedResponseHowTo(chat_id,from_user,canned_responses.hello(),context)

@debug_info
def sendWelcomeMessage(chat_id,context):
    """
    These messages are sent once when a user first contacts Anna; they're only
    ever sent once
    """
    from_user = context['from_user']
    msgs = ["Hey, I'm Anna FashionBot and I'm your personal stylist bot!",
            "I can help you find new dresses. Let's get started!",
            "Send a pic of a woman's dress you want to find or just describe it.",
            "Let me show you :)"
            ]
    suggested_responses = ['Show me now!']
    dispatchMessage(context,'text',chat_id,from_user,msgs,suggested_responses=suggested_responses)

@debug_info
def sendHowTo(chat_id,context):
    from_user = context['from_user']
    example_img = 'https://s-media-cache-ak0.pinimg.com/236x/49/d3/bf/49d3bf2bb0d88aa79c5fb7b41195e48c.jpg'

    dispatchMessage(context,'text',chat_id,from_user,['First, find a picture of the dress. Make sure the dress is the only thing in the picture. Like this:'])
    dispatchMessage(context,'image',chat_id,from_user,[example_img],suggested_responses=['example pic'])
    dispatchMessage(context,'text',chat_id,from_user,["Then I'll try to find similar dresses from my virtual racks. Like these:"])

    context['user_img_url'] = example_img
    context['search_type'] = 'image'
    getFitroomResults(chat_id,context)

@debug_info
def showExample(chat_id,context):
    """Anna's choice
    """
    from_user = context['from_user']
    examples = ['https://67.media.tumblr.com/1ac999c8b7993df3a1d933f1f26ed9aa/tumblr_o9mckr1dNV1ra7lgpo1_500.jpg',
                'https://66.media.tumblr.com/8d49c01c751ad772082497cd1a81fe77/tumblr_o9mbu5xJGu1ugb53eo1_1280.jpg',
                'https://66.media.tumblr.com/64fbda3655c3788b30144ed84df56af1/tumblr_o9mfsoQ2gD1tjge28o1_1280.jpg',
                'https://67.media.tumblr.com/da191961868fb3f521263aee6a70daca/tumblr_nzc6fbNNub1sh1xn8o1_400.jpg',
                'http://66.media.tumblr.com/346111ed3cad276b1a3f5630a173a8fe/tumblr_o5znu2zfj91r5wynfo1_500.jpg',
                'https://65.media.tumblr.com/dc403c140ce960644f55039ac63b8228/tumblr_o996wwm4RX1qc04t7o1_500.jpg']
    example_img =  random.choice(examples)
    context['user_img_url'] = example_img
    context['search_type'] = 'image'
    dispatchMessage(context,'image',chat_id,from_user,[example_img],suggested_responses=['Example pic'])
    dispatchMessage(context,'text',chat_id,from_user,["Let's start with something like this ^^"])
    getFitroomResults(chat_id,context)

@debug_info   
def newSearch(chat_id,context):
    from_user = context['from_user']
    dispatchMessage(context,'text',chat_id,from_user,
                    ["Send me a pic with only the dress you're looking for, OR type in what you're looking for, OR pick \"Anna's Choice\" for a suprise ;)"],
                    suggested_responses=["Anna's Choice"])


def sendSuggestedResponseHowTo(chat_id,from_user,message,context):
    dispatchMessage(context,'text',chat_id,from_user,[message],suggested_responses=['Show me how'])
        
# Actions wit knows about and can call
# must have the template: function(chat_id,context)
actions = {
    'say': say,
    'merge': merge,
    'error': error,
    'fitroom-lookup': getFitroomResults,
    'searchAgain': searchAgain,
    'buyThis': buyThis,
    'searchOrbuy': searchOrbuy,
    'doTextSearchEncounter': doTextSearchEncounter,
    'seeMoreResults':seeMoreResults,
    'sayHi': sayHi,
    'sendWelcomeMessage': sendWelcomeMessage
}

client = Wit(access_token, actions) # Invoke wit

def selectActionFromText(chat_id,from_user,message,context):
    if chat_id is None:
        chat_id = from_user
    if message == 'Go to store':
        buyThis(chat_id,context)
    elif message == 'Search with this pic':
        searchAgain(chat_id,context)
    elif message == 'See more results':
        seeMoreResults(chat_id, context)
    elif message == "See results on the GoFindFashion website":
        seeResultsOnWebsite(chat_id,context)
    elif message in ("Show me now!", "Show me how"):
        sendHowTo(chat_id,context)
    elif message  == 'New search':
        newSearch(chat_id,context)
    elif message == "Anna's Choice":
        showExample(chat_id, context)
    elif message == "Welcome":
        sendWelcomeMessage(chat_id,context)
    else:
        print message
        client.run_actions(chat_id, message, context)

@application.route('/', methods=['POST'])
def index_kik():
    """
    Main entry point for Kik POSTing to us.
    Get messages in batches an iter through each message, deciding what to do
    """
    # Make sure it's Kik sending us messages
    if not kik.verify_signature(request.headers.get('X-Kik-Signature'), request.get_data()):
        return Response(status=403)
    
    messages = messages_from_json(request.json['messages'])

    for message in messages:
        context0 = {'from_user':message.from_user,'chat_id':message.chat_id}
        # Respond to mentions: we must send only one batch of messages
        if message.mention is not None: 
            say(message.chat_id,context0,"Whoah Whoah Whoah! One at a time please. Are you trying to overload my circuts?!")
            continue
        # check to see if we've seen this user before, collect their previous context
        if retrieveContext(message.chat_id,message.from_user):
            context0 = retrieveContext(message.chat_id,message.from_user)
        context0['platform'] = 'KIK'
        if isinstance(message, TextMessage):
            storeContext(message.chat_id,message.from_user,context0,msg=message.body)
            selectActionFromText(message.chat_id,message.from_user,message.body,context0)
        elif isinstance(message, PictureMessage):
            # Always do a fitroom search when we get a picture message
            context0['user_img_url'] = message.pic_url
            context0['search_type'] = 'image'
            storeContext(message.chat_id,message.from_user,context0)
            doSearchEncounter(message.chat_id, context0)
        
        elif isinstance(message, StartChattingMessage):
            # User has started a chart for the first time; this is sent only once every for each user
            sendWelcomeMessage(message.chat_id,context0)
        else:
            # don't know how to respond to other messages e.g. videos
            say(message.chat_id,context0,"I'm new here. I'll be learning as I'm going. Try sending me a pic of a dress you'd like to search for")
             
    return Response(status=200) # If we return anything besides 200, Kik will try 3 more time to send the message


@application.route('/facebook', methods=['POST','GET'])
def index_fb():
#    return Response(status=200)
    chat_id = None
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == 'AnnaFashionBot':
            return Response(request.args.get('hub.challenge'),status=200)
    elif request.method == 'POST':
        output = request.json
        entires = output['entry']
        for entry in entires:
            for msg_obj in entry['messaging']:
                from_user = msg_obj['sender']['id']
                chat_id = from_user
                context0 = {'from_user':from_user,'chat_id':chat_id}
                if retrieveContext(chat_id,from_user):
                    context0 = retrieveContext(chat_id,from_user)
                context0['platform'] = 'FB'
                print msg_obj
                if msg_obj.get('message') and msg_obj['message'].get('attachments'):
                    img_url = msg_obj['message'].get('attachments')[0]['payload']['url']
                    context0['user_img_url'] = img_url
                    context0['search_type'] = 'image'
                    storeContext(chat_id,from_user,context0)
                    doSearchEncounter(chat_id, context0)
                elif msg_obj.get('message') and msg_obj['message'].get('text'):
                    msg = msg_obj['message']['text']
                    storeContext(chat_id,from_user,context0,msg=msg)
                    selectActionFromText(chat_id,from_user, msg,context0)
                elif  msg_obj.get('postback')and msg_obj['postback'].get('payload'):
                    msg = msg_obj['postback'].get('payload')
                    storeContext(chat_id,from_user,context0,msg=msg)
                    print msg
                    selectActionFromText(chat_id,from_user, msg,context0)
                else:
                    continue

        return Response(status=200)
    return Response(status=200)

if __name__ == "__main__":
    application.run()

