import requests
from flask import request, Response
from kik import KikError
from kik.messages import TextMessage, PictureMessage, messages_from_json,SuggestedResponseKeyboard,\
                        TextResponse, LinkMessage,StartChattingMessage, CustomAttribution
from wit import Wit

from bot import app as application
from bot import kik, access_token
import canned_responses
from wit_helpers import say,merge,error, storeContext, retrieveContext

application.debug = True
SHOW_THIS_MANY = 3 # How many pictures to show at once

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
    for an_image in result_image_urls[image_query_result_index:]:
        if i >= SHOW_THIS_MANY:
            break
        # some images are blank, they have exactly 5086 bytes. This hack
        # skips any images that size. Hacky fix until they fix it on the backend.
        is_blank =requests.head(an_image, headers={'Accept-Encoding': 'identity'})
        if is_blank.headers['content-length'] == '5086':
            responseFromAPI['images'].pop(i)
            continue
        
        picture_message = PictureMessage(to=from_user, chat_id=chat_id, pic_url=an_image)
        picture_message.attribution = CustomAttribution(name=responseFromAPI['images'][i]['title'])
        try:
            kik.send_messages([picture_message])
        except KikError:
            # Remove image results that give 404
            responseFromAPI['images'].pop(i)
            continue
        print an_image, responseFromAPI['images'][i]['pageUrl']
        i +=1
        
    context['image_query_result_index'] = i + image_query_result_index # remember which results we've showed
    context['image_query_result'] = responseFromAPI
    storeContext(chat_id,from_user,context)
    selectAnImageMsg(chat_id,context)
    return responseFromAPI

def getFitroomResults(chat_id,context):
    """ Call fitroom search api with url of image to search for
        then send results
    """
    image_url = context['user_img_url']
    chat_id = context['chat_id']
    from_user = context['from_user']

#   CALL Fitroom API
    try:
        r = requests.get('https://fitroom-api.herokuapp.com/api/images?type=women&key=1234&imageURL=' + image_url)
        responseFromAPI = r.json()
    except:
        say(chat_id,context,canned_responses.error_message())
        say(chat_id,context,"Try sending the pic again")
        return Response(status=500)
    
    if r.status_code != 200:
        # Something went wrong with fitroom API!
        say(chat_id,context,canned_responses.error_message()+"Ouch, that hurt my brain. You almost blew my circuts!")
        return Response(status=500)

    # Show the fitroom results, and clean out the bad images from the json
    context['image_query_result_index'] = 0
    context['image_query_result'] = responseFromAPI
    showFitRoomResults(chat_id,from_user,context)
    return Response(status=200)
        

def selectAnImageMsg(chat_id,context):
    from_user = context['from_user']
    
    responses = [TextResponse('Digging the first one'),
                   TextResponse('Like the second'),
                   TextResponse("Let's go with the third"),
                   TextResponse('See more like this')]
    if context['search_type'] == 'image':
        responses.append(TextResponse('See results on gofindfashion.com'))
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
    
def doSearchEncounter(chat_id,context):
    """
    This fn is used to run through a search encounter
    The user has either sent a pic to search with or used a
    text query by typing 'find me a xxxx', in that case Wit calls doTextSearchEncounter
    which inturn calls doSearchEncounter. doSearchEncounter is called directly when a user sends a pic
    """
    from_user = context['from_user']
    search_type = context['search_type']
    kik.send_messages([TextMessage(to=from_user, chat_id=chat_id, body=canned_responses.lookup())])
    if search_type == 'image':
        status = getFitroomResults(chat_id,context)
    elif search_type == 'text':
       status = getShopStyleResults(chat_id,context)
    if status.status_code !=200:
        return Response(status=200)
    
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
        storeContext(chat_id,from_user,prev_context)
        doSearchEncounter(chat_id, prev_context)
    return Response(status=200)

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
            # using a text message to send fitroom results because Kik breaks out links by putting a trailing /
            link_message = TextMessage(to=from_user,chat_id=chat_id,body=link)
#            link_message = LinkMessage(to=from_user,chat_id=chat_id,url=link,title=title)
        elif prev_context['search_type'] == 'text':
            i = int(prev_context['text_query_result_index'])-SHOW_THIS_MANY+i
            link = prev_context['text_query_result']['products'][i]['clickUrl']
            title = prev_context['text_query_result']['products'][i]['brandedName']
            link_message = LinkMessage(to=from_user,chat_id=chat_id,url=link,title=title)
        tip = TextMessage(to=from_user,chat_id=chat_id,body="Remember you can search again anytime by sending me a pic ;) or type 'more' to keep shopping")
        here = TextMessage(to=from_user,chat_id=chat_id,body="Here ya go:")
        kik.send_messages([here,link_message,tip])
        
def searchOrbuy(chat_id,context):
    """
    User has selected a picture she likes;
    Present the user with the option to visit the store webpage or search again using the selected picture
    """
    from_user = context['from_user']
    search_or_buy = TextMessage(
        to=from_user,
        chat_id=chat_id,
        body=canned_responses.like_it()
        )
    search_or_buy.keyboards.append(
        SuggestedResponseKeyboard(
                responses=[TextResponse('Go to store'),
                        TextResponse('Search again using that pic'),
                        TextResponse('See more of these results')]
                )
        )   
    kik.send_messages([search_or_buy])
    
def showShopStyleResults(chat_id,from_user,context):
    api_json = context['text_query_result']
    result_image_urls = [value['image']['sizes']['IPhone']['url'] for value in api_json['products']]
    
    text_query_result_index = int(context['text_query_result_index'])
    i = 0
    if text_query_result_index+SHOW_THIS_MANY >= len(result_image_urls):
        say(chat_id,context,"Well, maybe not. Gosh, you're hard to please :/ Try sending me back a pic of something I've showed you already to keep looking.")
        return api_json
    for an_image in result_image_urls[text_query_result_index:]:
        if i >= SHOW_THIS_MANY:
            break
        picture_message = PictureMessage(to=from_user, chat_id=chat_id, pic_url=an_image)
        picture_message.attribution = CustomAttribution(name=api_json['products'][i]['brandedName'])
        try:
            kik.send_messages([picture_message])
        except KikError:
            api_json['products'].pop(i)
            continue
        i +=1
        
    context['text_query_result_index'] = i + text_query_result_index # remember which results we've showed
    context['text_query_result'] = api_json
    storeContext(chat_id,from_user,context)
    selectAnImageMsg(chat_id,context)

    return api_json

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

def doTextSearchEncounter(chat_id,context):
    """
    User has sent a message like 'find me a red sundress'
    this fn is called by Wit when it thinks a phrase has a text_search intention
    """
    from_user = context['from_user']
    context = retrieveContext(chat_id,from_user)
    context['search_type'] = 'text'
    storeContext(chat_id,from_user,context)
    doSearchEncounter(chat_id,context)

def seeMoreResults(chat_id,context):
    from_user = context['from_user']
    context = retrieveContext(chat_id,from_user)
    say(chat_id,context,canned_responses.see_more())
    if context['search_type'] == 'image':
        showFitRoomResults(chat_id,from_user,context)
    else:
        showShopStyleResults(chat_id,from_user,context)
        
def seeResultsOnWebsite(chat_id,context):
    from_user = context['from_user']
    msg = LinkMessage(to=from_user,chat_id=chat_id,url='http://gofindfashion.com',title="Go Find Fashion Seach Engine")
    kik.send_messages([msg])
def sayHi(chat_id,context):
    say(chat_id,context,canned_responses.hello())


def sendWelcomeMessage(chat_id,context):
    """
    These messages are sent once when a user first contacts Anna; they're only
    ever sent once
    """
    from_user = context['from_user']
    msgs = ["Hey, I'm AnnaFashionBot and I'm your personal stylist bot!",
            "I can help you find a new outfit. Let's get started!",
            "Send a pic of a dress you want to find or just describe it."
            ]
    send_these = []
    for msg in msgs:
        send_these.append(
            TextMessage(
            to=from_user,
            chat_id=chat_id,
            body=msg
            ))
        
    show_me = TextMessage(
        to=from_user,
        chat_id=chat_id,
        body="Let me show you"
        )
    show_me.keyboards.append(
        SuggestedResponseKeyboard(
                responses=[TextResponse('Show me now!')]
                )
        )   
    send_these.append(show_me)
    kik.send_messages(send_these)
    

    
    
def sendHowTo(chat_id,context):
    from_user = context['from_user']
    example_img = 'https://s-media-cache-ak0.pinimg.com/236x/49/d3/bf/49d3bf2bb0d88aa79c5fb7b41195e48c.jpg'
    send_these = [TextMessage(
                    to=from_user,chat_id=chat_id,body='First, find a picture of the dress. Make sure the dress is the only thing in the picture. Like this:'
                    )
                 ]
    send_these.append(
        PictureMessage(
            to=from_user,
            chat_id=chat_id,
            pic_url=example_img
        )
    )
    send_these.append(TextMessage(
                    to=from_user,chat_id=chat_id,body="After you send us the image, I'll show you simiar dresess. Like this:"
                    )
                     )
    kik.send_messages(send_these)
    context['user_img_url'] = example_img
    context['search_type'] = 'image'
    getFitroomResults(chat_id,context)
    
    
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
    
@application.route('/', methods=['POST'])
def index():
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
        if isinstance(message, TextMessage):
            storeContext(message.chat_id,message.from_user,context0)
            if message.body == 'Go to store':
                buyThis(message.chat_id,context0)
            elif message.body == 'Search again using that pic':
                searchAgain(message.chat_id,context0)
            elif message.body in ('See more of these results', 'These all suck'):
                seeMoreResults(message.chat_id, context0)
            elif message.body == "See results on gofindfashion.com":
                seeResultsOnWebsite(message.chat_id,context0)
            elif message.body == "Show me now!":
                sendHowTo(message.chat_id,context0)
            else:
                client.run_actions(message.chat_id, message.body, context0)
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
            say(message.chat_id,context0,"I'm new here. I'll be learning as I'm going. Try sending me a pic")
             
    return Response(status=200) # If we return anything besides 200, Kik will try 3 more time to send the message


if __name__ == "__main__":
    application.run()

