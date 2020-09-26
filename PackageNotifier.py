"""
    created by Jordan Gassaway, 9/23/2020
    PackageNotifier: Top Level class for business logic portion of package notifier app
"""
import datetime
import re

import requests
from pymessenger.bot import Bot

from PNBDatabase import PNBDatabase, User, Package


class PackageNotifier:
    class Config():
        def __init__(self, auth_token, db_config: PNBDatabase.Config, user_passphrase, admin_passphrase):
            self.admin_passphrase = admin_passphrase
            self.user_passphrase = user_passphrase
            self.db_config = db_config
            self.auth_token = auth_token

    HELP_TEXT = """Package Notifier Bot supports the following commands
    * list packages - list all uncollected packages
    * help - show this help menu
    * claim package [id] - mark the specified package as collected
    * unsubscribe - stop receiving package notifications and remove yourself from the system"""
    HELP_TEXT_ADMIN = HELP_TEXT + """
    * remove user [name] - remove a user from the service
    * list users - list all users"""
    HELP_TEXT_UNVERIFIED = """To subscribe to Package Notifier Bot, please respond with the correct password."""
    UNKNOWN_CMD_TEXT = """Sorry I don't know how to help with that. Type help for a list of commands."""

    NEW_PACKAGE_NOTIFICATION_TEXT = """New package received (Package #{:d}) 
Pickup code {} 
Respond with 'claim package {:d}' to mark as collected"""

    FB_PROFILE_INFO_URL = "https://graph.facebook.com/{}?fields={}&access_token={}"

    PACKAGE_CODE_RE = re.compile('([pP]ickup [cC]ode)\\s*([0-9]+)')

    def __init__(self, config: Config):
        self.config = config
        self.db = PNBDatabase(config.db_config)
        self.db.login()

        self.bot = Bot(config.auth_token)

    def handle_message(self, message):
        """Handle a new message sent from messenger"""
        # Facebook Messenger ID for user so we know where to send response back to
        sender_pfid = message['sender']['id']
        user = self.db.getUser(sender_pfid)

        text = message['message'].get('text').lower()
        print("New message {} {!r}".format(text, text))
        print("Passphrases {} {!r} {} {!r}".format(self.config.user_passphrase, self.config.user_passphrase,
                                                    self.config.admin_passphrase, self.config.admin_passphrase))
        if text:
            # process menu command
            if text == self.config.user_passphrase and user is None:
                # add user to database
                sender_name = self.get_user_name(sender_pfid)
                self.db.addUser(User.newUser(sender_pfid, sender_name))

                # respond
                self.bot.send_text_message(sender_pfid, 'New User added')

            elif text == self.config.admin_passphrase and user is None:
                # add admin to database
                sender_name = self.get_user_name(sender_pfid)
                self.db.addUser(User.newAdmin(sender_pfid, sender_name))

                # respond
                self.bot.send_text_message(sender_pfid, 'New Admin added')

            elif user is not None:
                self.handle_cmd(text, user)
            else:
                self.bot.send_text_message(sender_pfid, self.HELP_TEXT_UNVERIFIED)

        # if user sends us a GIF, photo,video, or any other non-text item
        if message['message'].get('attachments'):
            # Don't care?
            self.bot.send_text_message(sender_pfid, self.UNKNOWN_CMD_TEXT)

    def handle_cmd(self, cmd: str, sender: User):
        if cmd == 'help':
            self.bot.send_text_message(sender.PFID, self.HELP_TEXT_ADMIN if sender.isAdmin() else self.HELP_TEXT)

        elif cmd == 'list packages':
            packages = self.db.getUncollectedPackages()
            if len(packages) == 0:
                self.bot.send_text_message(sender.PFID, "There are no unclaimed packages")
                return

            for package in packages:
                self.bot.send_text_message(sender.PFID, str(package))

        elif cmd.startswith('claim package'):
            package_id = int(cmd.split(' ')[2])
            package = self.db.getPackage(package_id)

            if package is None:
                self.bot.send_text_message(sender.PFID, "No package found with ID: {}".format(package_id))
                return

            self.db.claimPackage(package)
            self.bot.send_text_message(sender.PFID, "Package marked as collected")

        elif cmd == 'unsubscribe':
            self.db.removeUser(sender)
            self.bot.send_text_message(sender.PFID, 'You have been unsubscribed from this service')

        elif cmd.startswith('remove user') and sender.isAdmin():
            user_name = cmd[12:]
            user = self.db.getUserByName(user_name)

            if user is None:
                self.bot.send_text_message(sender.PFID, "No user found with name: {}".format(user_name))
                return

            self.db.removeUser(user)
            self.bot.send_text_message(sender.PFID, "{} removed from service".format(user.name))

        elif cmd == 'list users' and sender.isAdmin():
            users = self.db.getAllUsers()
            msg = 'Users:\n' + '\n'.join([str(u) for u in users])

            self.bot.send_text_message(sender.PFID, msg)

        else:
            # Send Error response
            self.bot.send_text_message(sender.PFID, self.UNKNOWN_CMD_TEXT)

    def handle_email(self, email):
        """Handle a new email fetched from the server"""
        # get code from email
        match = self.PACKAGE_CODE_RE.search(email.body)
        if not match:
            msg = "Error: No pickup code found for email {}".format(email.body)
            print(msg)
            admins = self.db.getAllAdmins()
            for admin in admins:
                self.bot.send_text_message(admin.PFID, msg)
            return

        code = int(match.group(2))

        # add package to db
        package = Package.newPackage(code, datetime.date.today())
        self.db.addPackage(package)

        # notify users
        users = self.db.getAllUsers()
        msg = self.NEW_PACKAGE_NOTIFICATION_TEXT.format(package.id, package.code, package.id)

        for user in users:
            self.bot.send_text_message(user.PFID, msg)

    def get_user_name(self, pfid):
        data = requests.get(self.FB_PROFILE_INFO_URL.format(pfid, 'first_name,last_name', self.config.auth_token)).json()
        return data['first_name'] + ' ' + data['last_name']

