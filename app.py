#Python libraries that we need to import for our bot
import json
import random
import time
import traceback

from flask import Flask, request
import os
import threading
import easyimap

from PackageNotifier import PackageNotifier

PASSWORDS = json.load(open('passwords.json'))
app = Flask(__name__)
packageNotifier = PackageNotifier(PASSWORDS['ACCESS_TOKEN'])
imap = easyimap.connect(PASSWORDS['EMAIL_HOST'], PASSWORDS['EMAIL_ACCOUNT'], PASSWORDS['EMAIL_PASSWORD'])


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
                       traceback.print_exc()

    return "Message Processed"


def verify_fb_token(token_sent):
    # take token sent by facebook and verify it matches the verify token you sent
    #if they match, allow the request, else return an error 
    if token_sent == PASSWORDS['VERIFY_TOKEN']:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


def check_for_emails():
    while True:
        try:
            new_mail = imap.unseen()

            if new_mail:
                for email in new_mail:
                    if 'package to pick up' in email.title:
                        packageNotifier.handle_email(email)

            else:
                # print('no new emails')
                pass
            time.sleep(20)
        except:
            traceback.print_exc()

if __name__ == "__main__":
    # app.run()
    check_for_emails()
