#Python libraries that we need to import for our bot
import json
import random
import time

from flask import Flask, request
import os
import threading

from PackageNotifier import PackageNotifier

app = Flask(__name__)
PASSWORDS = json.load(open('passwords.json'))
packageNotifier = PackageNotifier(PASSWORDS['ACCESS_TOKEN'])


# We will receive messages that Facebook sends our bot at this endpoint
@app.route("/", methods=['GET', 'POST'])
def receive_message():
    if request.method == 'GET':
        """Before allowing people to message your bot, Facebook has implemented a verify token
        that confirms all requests that your bot receives came from Facebook.""" 
        token_sent = request.args.get("hub.verify_token")
        return verify_fb_token(token_sent)
    # if the request was not get, it must be POST and we can just proceed with sending a message back to user
    else:
        # get whatever message a user sent the bot
       output = request.get_json()
       for event in output['entry']:
          messaging = event['messaging']
          for message in messaging:
            print(message)
            if message.get('message'):
                try:
                    packageNotifier.handle_message(message)
                except Exception as e:
                    print(e)

    return "Message Processed"


def verify_fb_token(token_sent):
    # take token sent by facebook and verify it matches the verify token you sent
    #if they match, allow the request, else return an error 
    if token_sent == PASSWORDS['VERIFY_TOKEN']:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


if __name__ == "__main__":
    app.run()
