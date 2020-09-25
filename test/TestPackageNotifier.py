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

    def __init__(self):
        super(MockDB, self).__init__(spec=PNBDatabase)

    def addUser(self, user:User):
        self.users[user.PFID] = user
        super(MockDB, self).addUser(user)

    def getUser(self, PFID):
        u =  self.users.get(PFID)
        super(MockDB, self).getUser(PFID)
        return u

    def getAllUsers(self):
        super(MockDB, self).getAllUsers()
        return self.users.values()

    def getAllAdmins(self):
        super(MockDB, self).getAllAdmins()
        admins = filter(lambda u: u.group == User.Group.ADMIN, self.users.values())
        return list(admins)

    def getUserByName(self, name):
        super(MockDB, self).getUserByName()
        users = filter(lambda u: u.name == name, self.users.values())
        return next(users)

    def removeUser(self, user:User):
        super(MockDB, self).removeUser(user)
        self.users.pop(user.PFID)

    def addPackage(self, package:Package):
        super(MockDB, self).addPackage(package)
        self.packages[package.id] = package

    def getPackage(self, id):
        super(MockDB, self).getPackage(id)
        return self.packages.get(id)

    def claimPackage(self, package:Package):
        super(MockDB, self).claimPackage(package)
        self.packages[package.package.id].collected = True

    def reset(self):
        super(MockDB, self).reset()
        self.users = {}
        self.packages = {}

    def load(self, users=None, packages=None):
        if users:
            for user in users:
                self.users[user.PFID] = user

        if packages:
            for package in packages:
                self.packages[package.id] = package

MOCK_DB = MockDB()
MOCK_BOT = mock.Mock()

modules = {'PNBDatabase.PNBDatabase': mock.MagicMock(return_value=MOCK_DB),
           'requests': mock.Mock(),
           'pymessenger.bot.Bot': mock.MagicMock(return_value=MOCK_BOT)}

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


    def setUp(self):
        # reset db
        MOCK_DB.reset()
        users = [self.test_user1, self.test_user2, self.test_user3]
        packages = [self.test_package1, self.test_package2, self.test_package3]
        MOCK_DB.load(users, packages)


    def testInit(self):
        """PackageNotifier correctly initialized database & Bot"""

    def testAddUserCmd(self):
        """PackageNotifier successfully ads a new user or admin"""

    def testUnknownUser(self):
        """No commands work if a user is not registered"""

    def testHelpCmd(self):
        """Help command returns help text. Help text for users does not include admin commands."""

    def testListPackagesCmd(self):
        """list packages will list all unclaimed packages"""

    def testClaimPackageCmd(self):
        """claim package will mark the package as collected"""

    def testUnsubscribeCmd(self):
        """unsubscribe removes the user from the system"""

    def testRemoveUserCmd(self):
        """remove user removes a user from the system. Cannot be called by non-admin."""

    def testListUsersCmd(self):
        """list users lists all active users. Cannot be called by non-admin."""

    def testHandleEmail(self):
        """handle_email adds the new package to the db and messages all active users."""

    def testGetUserName(self):
        """when creating a new user, PackageNotifier correctly queries the Facebook API for the full name"""
