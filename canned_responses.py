from random import choice

def see_more():
    phrases = ['Cool. More coming your way...',
               "Here's some more...",
               "Check out these!",
               "How 'bout these?",
               "I found more here...",
               "You're in luck, my racks are deep",
               "I've got outfits for days..."]
    return choice(phrases)
def hello():
    phrases = ['Hi. Send me a pic to search for',
               "Hey, you can tell me something to look for like 'find me a green maxi dress'",
               "Heyyy, what are you looking for? ",
               "What's up? Send me a pic of an outfit you'd like to find matches of",
               "Hi! I'm Anna. I can find similar outfits if you send me a pic of one",
               "Hello, tell me what you're looking for. Like 'find a strapless party dress'",
               "Hey! My name's Anna :) I can find new styles for you. Tell me to 'find a floral sundress'",
               ]
    return choice(phrases)
def lookup():
    phrases = ['Hold up, lemme check the racks in the back...',
               "Mmmmm let's see here...I think I've seen something similar...",
               "Just a sec, lemme check on that...",
               "Great! just give me a sec to remember where I put those....",
               "I think I know where to get something similar....just a sec...",
               "I know I left something like that around here somewhere....give me a sec..."]
    return choice(phrases)

def error_message():
    phrases = ["Bleep! Blorp! Error: did not compute! Errr, something went wrong...",
        "Hold up a sec, I didn't get that....",
        "Ah Ah Ah. You Didn't say the Magic Word. Something went wrong, I can't do that right now.",
        "Ut oh...I think there's a glitch in the Matrix..something went wrong"
        ]
    return choice(phrases)

def show_outfits():
    phrases = ["I found some killer options for you. See any you like?",
             "Check these out! Can you see yourself in any of these?",
             "What do you think of these? Which one is your fav?",
             "Is this what you were looking for? Which one do you like?",
             ]
    return choice(phrases)

def like_it():
    phrases = ["That one is so kewl!",
             "That one blew my mind!",
             "If you don't want it, I'll buy it for myself!",
             "You have great taste!",
             "I'm diggin' that one too!",
             "Cute!",
             "Adorable! ;)"
             ]
    return choice(phrases)
