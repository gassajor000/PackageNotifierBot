"""
    created by Jordan Gassaway, 9/23/2020
    TestPackageNotifier: unit tests for package notifier class
"""
import datetime
import re
import unittest
from unittest import mock

import psycopg2

from PNBDatabase import PNBDatabase, User, Package


class MockDB(mock.Mock):
    """Mock for PNBDatabase"""
    users = {}
    packages = {}

    def addUser(self, user:User):
        self.users[user.PFID] = user
        self._addUser(user)

    def getUser(self, PFID):
        u =  self.users.get(PFID)
        self._getUser(PFID)
        return u

    def getAllUsers(self):
        self._getAllUsers()
        return self.users.values()

    def getAllAdmins(self):
        self._getAllAdmins()
        admins = filter(lambda u: u.group == User.Group.ADMIN, self.users.values())
        return list(admins)

    def getUserByName(self, name):
        self._getUserByName(name)
        users = filter(lambda u: u.name.lower() == name, self.users.values())
        return next(users)

    def removeUser(self, user:User):
        self._removeUser(user)
        self.users.pop(user.PFID)

    def addPackage(self, package:Package):
        self._addPackage(package)
        self.packages[package.id] = package

    def getPackage(self, id):
        self._getPackage(id)
        return self.packages.get(id)

    def getUncollectedPackages(self):
        self._getUncollectedPackages()
        packages = filter(lambda p: not p.collected, self.packages.values())
        return list(packages)

    def claimPackage(self, package:Package):
        self._claimPackage(package)
        self.packages[package.id].collected = True

    def reset(self):
        self.reset_mock()
        self.users = {}
        self.packages = {}

    def load(self, users=None, packages=None):
        if users:
            for user in users:
                self.users[user.PFID] = user

        if packages:
            for package in packages:
                self.packages[package.id] = package


class MockRequestResult(mock.Mock):
    URL_REGEX = re.compile('(/)([0-9]*)(\?)')

    @classmethod
    def setUsers(cls, users):
        cls.users = users

    def __init__(self, url, *args, **kwargs):
        super(MockRequestResult, self).__init__(*args, **kwargs)
        self.url = url
        match = self.URL_REGEX.search(url)
        self.pfid = match.group(2) if match else None

    def json(self):
        user = self.users.get(self.pfid)
        if user:
            first_name, last_name = user.name.split(' ')
            return {'first_name': first_name, 'last_name': last_name}

        return {'first_name': 'Unknown', 'last_name': 'Unknown'}

class MockRequestLib(mock.Mock):
    def get(self, url):
        self._get(url)
        return MockRequestResult(url)

class FakeMessage(dict):
    """Stand in for a new facebook message"""
    def __init__(self, sender: User, msg):
        super(FakeMessage, self).__init__()
        self['sender'] = {'id': sender.PFID}
        self['message'] = {'text': msg}

class FakeEmail():
    def __init__(self, body, code):
        self.code = code
        self.body = body

    @classmethod
    def from_package(cls, package):
        return FakeEmail('New package pickup code\n{}'.format(package.code), str(package.code))



MOCK_DB = MockDB(name='mock db')
MOCK_BOT = mock.Mock(name='mock bot')
MOCK_PNBDATABASE_LIB = mock.MagicMock(return_value=MOCK_DB, name='mock db lib')
MOCK_PYMESSENGER_LIB = mock.MagicMock(return_value=MOCK_BOT, name='mock pymessenger lib')
MOCK_REQUESTS_LIB = MockRequestLib()

modules = {'PNBDatabase': mock.MagicMock(PNBDatabase=MOCK_PNBDATABASE_LIB, User=User, Package=Package),
           'requests': MOCK_REQUESTS_LIB,
           'pymessenger.bot': mock.MagicMock(Bot=MOCK_PYMESSENGER_LIB)}

with mock.patch.dict('sys.modules', modules):
    from PackageNotifier import PackageNotifier


class TestPackageNotifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_user1 = User.newAdmin('101', 'Reginald Hargreaves')
        cls.test_user2 = User.newUser('102', 'Vanya Hargreaves')
        cls.test_user3 = User.newUser('103', 'Luther Hargreaves')
        cls.test_user4 = User.newAdmin('104', 'Allison Hargreaves')

        cls.globals = [MOCK_DB, MOCK_BOT, MOCK_PNBDATABASE_LIB, MOCK_PYMESSENGER_LIB]

        users = {
            '101': cls.test_user1,
            '102': cls.test_user2,
            '103': cls.test_user3,
            '104': cls.test_user4,
        }
        MockRequestResult.setUsers(users)


    def setUp(self):
        # reset db
        MOCK_DB.reset()
        users = [self.test_user1, self.test_user2, self.test_user3]

        today = datetime.date.today()
        self.test_package1 = Package.newPackage(1234, today)
        self.test_package2 = Package.newPackage(5678, today)
        self.test_package3 = Package.newPackage(9012, today)
        self.test_package4 = Package.newPackage(3456, today)
        self.test_package2.collected = True
        packages = [self.test_package1, self.test_package2, self.test_package3]
        
        MOCK_DB.load(users, packages)
        MOCK_BOT.reset_mock()
        MOCK_REQUESTS_LIB.reset_mock()
        MOCK_PNBDATABASE_LIB.reset_mock()
        MOCK_PYMESSENGER_LIB.reset_mock()


    def testInit(self):
        """PackageNotifier correctly initialized database & Bot"""
        pn = PackageNotifier('test_auth_token')

        MOCK_PNBDATABASE_LIB.assert_called_once_with('pnb_test')
        MOCK_DB.login.assert_called_once_with('test_pnb', 'secret_pwd')
        MOCK_PYMESSENGER_LIB.assert_called_once_with('test_auth_token')

    def testAddUserCmd(self):
        """PackageNotifier successfully ads a new user or admin"""
        pn = PackageNotifier('test_auth_token')

        # Add a user
        msg = FakeMessage(self.test_user4, 'hedwig')
        pn.handle_message(msg)
        self.assertEqual(MOCK_DB._addUser.call_count, 1)
        self.assertIn(self.test_user4.PFID, MOCK_DB.users, "User was not added to the user table")
        user = MOCK_DB.users.get(self.test_user4.PFID)
        self.assertEqual(self.test_user4.PFID, user.PFID, "Wrong PFID was added")
        self.assertEqual(User.Group.USER, user.group, "User was added to the wrong group")

        MOCK_DB.reset()

        # add an admin
        msg = FakeMessage(self.test_user4, 'errol')
        pn.handle_message(msg)
        self.assertEqual(MOCK_DB._addUser.call_count, 1)
        self.assertIn(self.test_user4.PFID, MOCK_DB.users, "Admin was not added to the user table")
        user = MOCK_DB.users.get(self.test_user4.PFID)
        self.assertEqual(self.test_user4.PFID, user.PFID, "Wrong PFID was added")
        self.assertEqual(User.Group.ADMIN, user.group, "User was added to the wrong group")

    def testHelpCmd(self):
        """Help command returns help text. Help text for users does not include admin commands."""
        pn = PackageNotifier('test_auth_token')

        user_cmds = ['list packages', 'claim package', 'unsubscribe', 'help']
        admin_cmds = user_cmds + ['list users', 'remove user']

        # Query Help
        msg = FakeMessage(self.test_user1, 'help')
        pn.handle_message(msg)
        MOCK_BOT.send_text_message.assert_called_once_with(self.test_user1.PFID, pn.HELP_TEXT_ADMIN)

        # check for admin commands
        for cmd in admin_cmds:
            self.assertIn(cmd, pn.HELP_TEXT_ADMIN, "Admin help missing {} cmd!".format(cmd))

        MOCK_BOT.reset_mock()

        msg = FakeMessage(self.test_user2, 'help')
        pn.handle_message(msg)
        MOCK_BOT.send_text_message.assert_called_once_with(self.test_user2.PFID, pn.HELP_TEXT)

        # Make sure admin cmds aren't in the non admin msg
        self.assertNotIn('list users', pn.HELP_TEXT)
        self.assertNotIn('remove user', pn.HELP_TEXT)

        for cmd in user_cmds:
            self.assertIn(cmd, pn.HELP_TEXT, "User help missing {} cmd!".format(cmd))

    def testListPackagesCmd(self):
        """list packages will list all unclaimed packages"""
        pn = PackageNotifier('test_auth_token')

        # Add a user
        msg = FakeMessage(self.test_user1, 'list packages')
        pn.handle_message(msg)
        self.assertEqual(MOCK_BOT.send_text_message.call_count, 2, "Incorrect number of packages returned!")

        pk_msgs_args = MOCK_BOT.send_text_message.call_args_list
        for pkg in [self.test_package1, self.test_package3]:
            # check msg was sent with package info
            self.assertTrue(any([pk_msg_arg[0][1] == str(pkg) for pk_msg_arg in pk_msgs_args]))

    def testClaimPackageCmd(self):
        """claim package will mark the package as collected"""
        pn = PackageNotifier('test_auth_token')

        # Claim a package
        msg = FakeMessage(self.test_user1, 'claim package {:d}'.format(self.test_package1.id))
        pn.handle_message(msg)
        self.assertEqual(MOCK_BOT.send_text_message.call_count, 1, "System did not send a response")
        MOCK_DB._claimPackage.assert_called_once_with(self.test_package1)
        self.assertTrue(self.test_package1.collected, "Package was not marked as collected")

    def testUnsubscribeCmd(self):
        """unsubscribe removes the user from the system"""
        pn = PackageNotifier('test_auth_token')

        # Unsubscribe
        msg = FakeMessage(self.test_user1, 'unsubscribe')
        pn.handle_message(msg)
        self.assertEqual(MOCK_BOT.send_text_message.call_count, 1, "System did not send a response")
        MOCK_DB._removeUser.assert_called_once_with(self.test_user1)

    def testRemoveUserCmd(self):
        """remove user removes a user from the system. Cannot be called by non-admin."""
        pn = PackageNotifier('test_auth_token')

        # Try removing user with User privileges
        msg = FakeMessage(self.test_user2, 'remove user Luther Hargreaves')
        pn.handle_message(msg)
        self.assertEqual(MOCK_BOT.send_text_message.call_count, 1, "System did not send a response")
        MOCK_DB._removeUser.assert_not_called()

        MOCK_BOT.reset_mock()

        msg = FakeMessage(self.test_user1, 'remove user Luther Hargreaves')
        pn.handle_message(msg)
        self.assertEqual(MOCK_BOT.send_text_message.call_count, 1, "System did not send a response")
        MOCK_DB._removeUser.assert_called_once_with(self.test_user3)

    def testListUsersCmd(self):
        """list users lists all active users. Cannot be called by non-admin."""
        pn = PackageNotifier('test_auth_token')

        # List users w/ user privileges
        msg = FakeMessage(self.test_user2, 'list users')
        pn.handle_message(msg)
        self.assertEqual(MOCK_BOT.send_text_message.call_count, 1)
        self.assertEqual(MOCK_BOT.send_text_message.call_args[0][1], pn.UNKNOWN_CMD_TEXT)

        MOCK_BOT.reset_mock()
        msg = FakeMessage(self.test_user1, 'list users')
        pn.handle_message(msg)
        self.assertEqual(MOCK_BOT.send_text_message.call_count, 1 , "Incorrect number of messages sent!")

        users = MOCK_BOT.send_text_message.call_args[0][1].split('\n')
        users.pop(0)    # remove header
        self.assertEqual(len(users), 3 , "Incorrect number of users listed!")
        for user in [self.test_user1, self.test_user2, self.test_user3]:
            # check msg was sent with user info
            self.assertTrue(any([user_msg == str(user) for user_msg in users]), "User {} not found!".format(user.name))

    def testHandleEmail(self):
        """handle_email adds the new package to the db and messages all active users."""
        pn = PackageNotifier('test_auth_token')

        # Different possible email formats
        emails = [
            FakeEmail.from_package(self.test_package4),
            FakeEmail('blah blah blah pickup code\n5678\n', '5678'),
            FakeEmail('blah blah blah Pickup Code\r\n656558 lorem ipsum', '656558'),
            FakeEmail('blah blah blah Pickup Code    99999999', '99999999'),
        ]
        for email in emails:
            MOCK_BOT.reset_mock()
            pn.handle_email(email)

            self.assertEqual(MOCK_BOT.send_text_message.call_count, 3, "Incorrect number of messages sent out!")
            self.assertIn(email.code, MOCK_BOT.send_text_message.call_args[0][1], "Message did not contain pickup code!")

        # Handle bad email no pickup code)
        bad_email = FakeEmail('blah blah blah no code', '99999999')
        MOCK_BOT.reset_mock()
        pn.handle_email(bad_email)

        self.assertEqual(MOCK_BOT.send_text_message.call_count, 1, "Incorrect number of messages sent out!")
        self.assertIn("no pickup code", MOCK_BOT.send_text_message.call_args[0][1].lower(), "Message did not indicate an error")

    def testGetUserName(self):
        """when creating a new user, PackageNotifier correctly queries the Facebook API for the full name"""
        pn = PackageNotifier('test_auth_token')

        # Add a user
        msg = FakeMessage(self.test_user4, 'hedwig')
        pn.handle_message(msg)
        MOCK_REQUESTS_LIB._get.assert_called_once_with(
            "https://graph.facebook.com/{}?fields=first_name,last_name&access_token={}".format(self.test_user4.PFID,
                                                                                               'test_auth_token'))
        self.assertEqual(self.test_user4.name, MOCK_DB.users.get(self.test_user4.PFID).name)

        MOCK_REQUESTS_LIB.reset_mock()
        MOCK_DB.reset()

        # add an admin
        msg = FakeMessage(self.test_user4, 'errol')
        pn.handle_message(msg)
        MOCK_REQUESTS_LIB._get.assert_called_once_with(
            "https://graph.facebook.com/{}?fields=first_name,last_name&access_token={}".format(self.test_user4.PFID,
                                                                                               'test_auth_token'))
        self.assertEqual(self.test_user4.name, MOCK_DB.users.get(self.test_user4.PFID).name)

    def testUnknownUser(self):
        """No commands work if a user is not registered"""
        pn = PackageNotifier('test_auth_token')

        cmds = ['list users', 'list packages', 'claim package 2',
                'remove user Luther Hargreaves', 'unsubscribe', 'help']

        for cmd in cmds:
            MOCK_BOT.reset_mock()
            msg = FakeMessage(self.test_user4, cmd)
            pn.handle_message(msg)

            MOCK_BOT.send_text_message.assert_called_once_with(self.test_user4.PFID, pn.HELP_TEXT_UNVERIFIED)

