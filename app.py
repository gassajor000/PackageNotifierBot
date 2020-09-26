#Python libraries that we need to import for our bot
import json
import time
import traceback
from imaplib import IMAP4

from flask import Flask, request
import os
import threading
import easyimap

from PackageNotifier import PackageNotifier
from PNBDatabase import PNBDatabase

DEV_MODE = False


class AppConfig():
    def __init__(self, auth_token, verify_token, db_config: PNBDatabase.Config, user_passphrase, admin_passphrase,
                 email_host, email_user, email_password):
        self.email_password = email_password
        self.email_user = email_user
        self.email_host = email_host
        self.admin_passphrase = admin_passphrase
        self.user_passphrase = user_passphrase
        self.db_config = db_config
        self.verify_token = verify_token
        self.auth_token = auth_token

    def to_pn_config(self):
        return PackageNotifier.Config(self.auth_token, self.db_config, self.user_passphrase, self.admin_passphrase)

    @classmethod
    def from_env_variables(cls):
        for var in ['AUTH_TOKEN', 'USER_PASSPHRASE', 'ADMIN_PASSPHRASE',
                    'EMAIL_HOST', 'EMAIL_USER', 'EMAIL_PASSWORD']:
            if var not in os.environ:
                raise RuntimeError("Error, environment variable {} not set!".format(var))

        if 'DATABASE_URL' in os.environ:
            db_config = PNBDatabase.URLConfig(os.environ.get('DATABASE_URL'))
        elif all([var in os.environ for var in ['DB_NAME', 'DB_USER', 'DB_PASSWORD']]):
            db_config = PNBDatabase.CredentialsConfig(os.environ.get('DB_NAME'), os.environ.get('DB_USER'),
                                                   os.environ.get('DB_PASSWORD'))
        else:
            raise RuntimeError('ERROR! No database variables are set!')

        return AppConfig(os.environ.get('AUTH_TOKEN'), os.environ.get('VERIFY_TOKEN'),
                         db_config,
                         os.environ.get('USER_PASSPHRASE'), os.environ.get('ADMIN_PASSPHRASE'),
                         os.environ.get('EMAIL_HOST'), os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASSWORD'))

    @classmethod
    def from_file(cls, file):
        data = json.load(open(file))
        db_config = PNBDatabase.CredentialsConfig(data['DB_NAME'], data['DB_USER'], data['DB_PASSWORD'])
        return AppConfig(data['AUTH_TOKEN'], data['VERIFY_TOKEN'],
                         db_config,
                         data['USER_PASSPHRASE'], data['ADMIN_PASSPHRASE'],
                         data['EMAIL_HOST'], data['EMAIL_USER'], data['EMAIL_PASSWORD'])


if DEV_MODE:
    config = AppConfig.from_file('passwords.json')
else:   # PROD MODE
    config = AppConfig.from_env_variables()

app = Flask(__name__)
packageNotifier = PackageNotifier(config.to_pn_config())
imap = easyimap.connect(config.email_host, config.email_user, config.email_password)


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
                    except:
                        traceback.print_exc()

    return "Message Processed"


def verify_fb_token(token_sent):
    # take token sent by facebook and verify it matches the verify token you sent
    # if they match, allow the request, else return an error
    if token_sent == config.verify_token:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


def check_for_emails():
    global imap

    while True:
        try:
            new_mail = imap.unseen()

            if new_mail:
                for email in new_mail:
                    if 'package to pick up' in email.title:
                        print(email)
                        packageNotifier.handle_email(email)

            else:
                # print('no new emails')
                pass
            time.sleep(20)
        except IMAP4.abort:
            # socket error, close & reopen socket
            traceback.print_exc()
            imap.quit()
            imap = easyimap.connect(config.email_host, config.email_user, config.email_password)
        except:
            traceback.print_exc()


if __name__ == "__main__":
    imap_thread = threading.Thread(target=check_for_emails)
    imap_thread.start()
    app.run()
