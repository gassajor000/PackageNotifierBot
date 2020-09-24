"""
    created by Jordan Gassaway, 9/23/2020
    PackageNotifier: Top Level class for business logic portion of package notifier app
"""
from pymessenger.bot import Bot
from PNBDatabase import PNBDatabase, User, Package


class PackageNotifier:
    HELP_TEXT = """Package Notifier Bot supports the following commands
    * list packages - list all uncollected packages
    * help - show help text"""
    HELP_TEXT_UNVERIFIED = """To subscribe to package notifier bot, please respond with the correct password."""

    def __init__(self, auth_token):
        self.db = PNBDatabase('pnb_test')
        self.db.login('test_pnb', 'secret_pwd')

        self.bot = Bot(auth_token)

    def handle_message(self, message):
        """Handle a new message sent from messenger"""
        # Facebook Messenger ID for user so we know where to send response back to
        sender_pfid = message['sender']['id']
        sender_name = 'Joe user'        # TODO get real name from server
        text = message['message'].get('text').lower()
        if text:
            # process menu command
            if text == 'hedwig':
                # add user to database
                self.db.addUser(User.newUser(sender_pfid, sender_name))

                # respond
                self.bot.send_text_message(sender_pfid, 'New User Added')
            elif text == 'list packages':
                packages = self.db.getUncollectedPackages()
                for package in packages:
                    self.bot.send_text_message(sender_pfid, str(package))
            elif text == 'help':
                self.bot.send_text_message(sender_pfid, self.HELP_TEXT)
            else:
                # Send Error response
                self.bot.send_text_message(sender_pfid, 'Sorry I don\'t know how to help with that')

        # if user sends us a GIF, photo,video, or any other non-text item
        if message['message'].get('attachments'):
            # Don't care?
            pass

    def handle_email(self, email):
        """Handle a new email fetched from the server"""

