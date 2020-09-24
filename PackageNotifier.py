"""
    created by Jordan Gassaway, 9/23/2020
    PackageNotifier: Top Level class for business logic portion of package notifier app
"""
from pymessenger.bot import Bot
from PNBDatabase import PNBDatabase, User, Package


class PackageNotifier:
    HELP_TEXT = """Package Notifier Bot supports the following commands
    * list packages - list all uncollected packages
    * help - show this help menu
    * claim package [id] - mark the specified package as collected
    * unsubscribe - stop receiving package notifications and remove yourself from the system"""
    HELP_TEXT_ADMIN = HELP_TEXT + """
    * remove user [name] - remove a user from the service"""
    HELP_TEXT_UNVERIFIED = """To subscribe to Package Notifier Bot, please respond with the correct password."""
    UNKNOWN_CMD_TEXT = """Sorry I don't know how to help with that. Type help for a list of commands."""

    def __init__(self, auth_token):
        self.db = PNBDatabase('pnb_test')
        self.db.login('test_pnb', 'secret_pwd')

        self.bot = Bot(auth_token)

    def handle_message(self, message):
        """Handle a new message sent from messenger"""
        # Facebook Messenger ID for user so we know where to send response back to
        sender_pfid = message['sender']['id']
        user = self.db.getUesr(sender_pfid)

        text = message['message'].get('text').lower()
        if text:
            # process menu command
            if text == 'hedwig' and user is None:
                # add user to database
                sender_name = 'Joe user'  # TODO get real name from server
                self.db.addUser(User.newUser(sender_pfid, sender_name))

                # respond
                self.bot.send_text_message(sender_pfid, 'New User Added')

            elif text == 'errol' and user is None:
                # add admin to database
                sender_name = 'Joe user'  # TODO get real name from server
                self.db.addUser(User.newAdmin(sender_pfid, sender_name))

                # respond
                self.bot.send_text_message(sender_pfid, 'New Admin Added')

            elif user is not None:
                self.handle_cmd(text, user)
            else:
                self.bot.send_text_message(sender_pfid, self.HELP_TEXT_UNVERIFIED)


        # if user sends us a GIF, photo,video, or any other non-text item
        if message['message'].get('attachments'):
            # Don't care?
            self.bot.send_text_message(sender_pfid, self.UNKNOWN_CMD_TEXT)

    def handle_cmd(self, cmd: str, arg: str,  sender: User):
        if cmd == 'help':
            self.bot.send_text_message(sender.PFID, self.HELP_TEXT_ADMIN if sender.isAdmin() else self.HELP_TEXT)

        elif cmd == 'list packages':
            packages = self.db.getUncollectedPackages()
            for package in packages:
                self.bot.send_text_message(sender.PFID, str(package))

        elif cmd == 'claim package':
            pass # TODO

        elif cmd == 'unsubscribe':
            self.db.removeUser(sender)
            self.bot.send_text_message(sender.PFID, 'You have been unsubscribed from this service')

        elif cmd == 'remove user' and sender.isAdmin():
            pass # TODO

        else:
            # Send Error response
            self.bot.send_text_message(sender.PFID, self.UNKNOWN_CMD_TEXT)


    def handle_email(self, email):
        """Handle a new email fetched from the server"""

