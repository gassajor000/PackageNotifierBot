"""
    created by Jordan Gassaway, 9/23/2020
    TestPackageNotifier: unit tests for package notifier class
"""
import datetime
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
    @classmethod
    def setUsers(cls, users):
        cls.users = users

    def __init__(self, url, *args, **kwargs):
        super(MockRequestResult, self).__init__(*args, **kwargs)
        self.url = url
        self.pfid = 'something'     # TODO actually parse the URL

    def json(self):
        user = self.users.get(self.pfid)
        if user:
            first_name, last_name = user.name.split
            return {'first_name': first_name, 'last_name': last_name}

        return {'first_name': 'Unknown', 'last_name': 'Unknown'}

class MockRequestLib(mock.Mock):
    def get(self, url):
        return MockRequestResult(url)

class FakeMessage(dict):
    """Stand in for a new facebook message"""
    def __init__(self, sender: User, msg):
        super(FakeMessage, self).__init__()
        self['sender'] = {'id': sender.PFID}
        self['message'] = {'text': msg}


MOCK_DB = MockDB(name='mock db')
MOCK_BOT = mock.Mock(name='mock bot')
MOCK_PNBDATABASE_LIB = mock.MagicMock(return_value=MOCK_DB, name='mock db lib')
MOCK_PYMESSENGER_LIB = mock.MagicMock(return_value=MOCK_BOT, name='mock pymessenger lib')

modules = {'PNBDatabase': mock.MagicMock(PNBDatabase=MOCK_PNBDATABASE_LIB, User=User, Package=Package),
           'requests': MockRequestLib(),
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

        today = datetime.date.today()
        cls.test_package1 = Package.newPackage(1234, today)
        cls.test_package2 = Package.newPackage(5678, today)
        cls.test_package3 = Package.newPackage(9012, today)
        cls.test_package4 = Package.newPackage(3456, today)
        cls.test_package2.collected = True

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
        packages = [self.test_package1, self.test_package2, self.test_package3]
        MOCK_DB.load(users, packages)


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

        # Query Help
        msg = FakeMessage(self.test_user1, 'help')
        pn.handle_message(msg)
        MOCK_BOT.send_text_message.assert_called_once_with(self.test_user1.PFID, pn.HELP_TEXT_ADMIN)

        MOCK_BOT.reset_mock()

        msg = FakeMessage(self.test_user2, 'help')
        pn.handle_message(msg)
        MOCK_BOT.send_text_message.assert_called_once_with(self.test_user2.PFID, pn.HELP_TEXT)

        self.assertNotIn('list users', pn.HELP_TEXT)
        self.assertNotIn('remove user', pn.HELP_TEXT)

    def testListPackagesCmd(self):
        """list packages will list all unclaimed packages"""
        pn = PackageNotifier('test_auth_token')

        # Add a user
        msg = FakeMessage(self.test_user1, 'list packages')
        pn.handle_message(msg)
        self.assertEqual(MOCK_BOT.send_text_message.call_count, 2)
        msgs = MOCK_BOT.send_text_message.call_args

        # TODO finish this
        self.fail("Unfinished test!")

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

    def testHandleEmail(self):
        """handle_email adds the new package to the db and messages all active users."""

    def testGetUserName(self):
        """when creating a new user, PackageNotifier correctly queries the Facebook API for the full name"""

    def testUnknownUser(self):
        """No commands work if a user is not registered"""
