"""
    created by Jordan Gassaway, 9/26/2020
    check_email: simple script to check email and then pass it on to the web process
"""
import json
import os
import time
import traceback
from imaplib import IMAP4

import easyimap
import requests


class EmailConfig():
    def __init__(self, host, user, password, pnb_url):
        self.pnb_url = pnb_url
        self.password = password
        self.user = user
        self.host = host

    @classmethod
    def from_env_variables(cls):
        for var in ['EMAIL_HOST', 'EMAIL_USER', 'EMAIL_PASSWORD', 'APP_URL']:
            if var not in os.environ:
                raise RuntimeError("Error, environment variable {} not set!".format(var))

        return EmailConfig(os.environ.get('EMAIL_HOST'), os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASSWORD'),
                           os.environ.get('APP_URL'))

    @classmethod
    def from_file(cls, file):
        data = json.load(open(file))
        return EmailConfig(data['EMAIL_HOST'], data['EMAIL_USER'], data['EMAIL_PASSWORD'], data['APP_URL'])

DEV_MODE = False

if DEV_MODE:
    config = EmailConfig.from_file('passwords.json')
else:   # PROD MODE
    config = EmailConfig.from_env_variables()

imap = easyimap.connect(config.host, config.user, config.password)

def check_for_email():
    global imap, config
    try:
        new_mail = imap.unseen()

        if new_mail:
            for email in new_mail:
                if 'package to pick up' in email.title:
                    print(email)
                    # send a post to the web server
                    requests.post(config.pnb_url + '/email', json={'title': email.title, 'body': email.body})

        else:
            print('no new emails')

    except IMAP4.abort:
        # socket error, close & reopen socket
        traceback.print_exc()
        imap.quit()
        imap = easyimap.connect(config.host, config.user, config.password)
    except:
        traceback.print_exc()


def poll_emails_periodically(poll_period):
    while True:
        check_for_email()
        time.sleep(poll_period)

if __name__ == '__main__':
    check_for_email()
