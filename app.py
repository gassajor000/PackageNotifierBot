#Python libraries that we need to import for our bot
import json
import traceback

from flask import Flask, request
import os
import threading

from PackageNotifier import PackageNotifier
from PNBDatabase import PNBDatabase

from check_email import poll_emails_periodically

DEV_MODE = False


class AppConfig():
    def __init__(self, auth_token, verify_token, db_config: PNBDatabase.Config, user_passphrase, admin_passphrase):
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

        return AppConfig(os.environ.get('AUTH_TOKEN'), os.environ.get('VERIFY_TOKEN'), db_config,
                         os.environ.get('USER_PASSPHRASE'), os.environ.get('ADMIN_PASSPHRASE'))

    @classmethod
    def from_file(cls, file):
        data = json.load(open(file))
        db_config = PNBDatabase.CredentialsConfig(data['DB_NAME'], data['DB_USER'], data['DB_PASSWORD'])
        return AppConfig(data['AUTH_TOKEN'], data['VERIFY_TOKEN'], db_config, data['USER_PASSPHRASE'],
                         data['ADMIN_PASSPHRASE'])


if DEV_MODE:
    config = AppConfig.from_file('passwords.json')
else:   # PROD MODE
    config = AppConfig.from_env_variables()

app = Flask(__name__)
packageNotifier = PackageNotifier(config.to_pn_config())


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

class Email():
    def __init__(self, title, body):
        self.body = body
        self.title = title


@app.route("/email", methods=['POST'])
def receive_email():
    output = request.get_json()
    if 'title' not in output or 'body' not in output:
        print('Bad email object {}'.format(output))
        return "Message Processed"

    packageNotifier.handle_email(Email(output['title'], output['body']))

    return "Message Processed"


def verify_fb_token(token_sent):
    # take token sent by facebook and verify it matches the verify token you sent
    # if they match, allow the request, else return an error
    if token_sent == config.verify_token:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


if __name__ == "__main__":
    imap_thread = threading.Thread(target=poll_emails_periodically, args=[20])
    imap_thread.start()

    app.run()
