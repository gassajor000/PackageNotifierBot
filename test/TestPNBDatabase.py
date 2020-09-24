"""
    created by Jordan Gassaway, 9/23/2020
    TestPNBDatabase: unit tests for pnb database
"""
import datetime

import psycopg2
import unittest

from PNBDatabase import PNBDatabase, User, Package


class TestPNBDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = PNBDatabase('pnb_test')
        cls.db.login('test_pnb', 'secret_pwd')

        cls.conn = psycopg2.connect("dbname={} user={} password={}".format('pnb_test', 'tester', 'tester'))
        cls.cur = cls.conn.cursor()

    def setUp(self):
        # Drop and recreate tables
        self.cur.execute('DROP TABLE IF EXISTS users, packages;')
        self.cur.execute('CREATE TABLE users (pfid integer PRIMARY KEY, name varchar(40) NOT NULL, ugroup varchar(10) NOT NULL)')
        self.cur.execute('CREATE TABLE packages (id integer PRIMARY KEY, code integer NOT NULL, date_received date NOT NULL, collected bool)')
        self.cur.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON users, packages TO test_pnb')

        # Prefill with some data
        self.test_user1 = User(100, 'Harold Jenkins', User.Group.USER)
        self.test_user2 = User(101, 'Stevie Wonder', User.Group.ADMIN)

        self.cur.execute('INSERT INTO users (pfid, name, ugroup) VALUES (%s, %s, %s)', (self.test_user1.PFID,
                                                                                        self.test_user1.name,
                                                                                        self.test_user1.group.value))
        self.cur.execute('INSERT INTO users (pfid, name, ugroup) VALUES (%s, %s, %s)', (self.test_user2.PFID,
                                                                                        self.test_user2.name,
                                                                                        self.test_user2.group.value))
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        self.test_package1 = Package(200, 1234, today, False)
        self.test_package2 = Package(201, 5555, yesterday, True)

        self.cur.execute('INSERT INTO packages (id, code, date_received, collected) VALUES (%s, %s, %s, %s)', (self.test_package1.id,
                                                                                                         self.test_package1.code,
                                                                                                         self.test_package1.date_received,
                                                                                                         self.test_package1.collected))
        self.cur.execute('INSERT INTO packages (id, code, date_received, collected) VALUES (%s, %s, %s, %s)', (self.test_package2.id,
                                                                                                         self.test_package2.code,
                                                                                                         self.test_package2.date_received,
                                                                                                         self.test_package2.collected))

        self.conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.cur.close()
        cls.conn.close()

    def testAddUser(self):
        """addUser adds a user to the Users group"""
        user = User.newUser(102, 'Reginald Hargreaves')
        self.db.addUser(user)

        self.cur.execute('SELECT * FROM users WHERE pfid=%s', (user.PFID,))
        pfid, name, group = self.cur.fetchone()

        self.assertEqual(user.PFID, pfid, "PFIDs are not equal!")
        self.assertEqual(user.name, name, "Names are not equal!")
        self.assertEqual(user.group.value, group, "Groups are not equal!")

    def testAddAdmin(self):
        """addUser adds a user to the Admins group"""
        user = User.newAdmin(103, 'Dave')
        self.db.addUser(user)

        self.cur.execute('SELECT * FROM users WHERE pfid=%s', (user.PFID,))
        pfid, name, group = self.cur.fetchone()

        self.assertEqual(user.PFID, pfid, "PFIDs are not equal!")
        self.assertEqual(user.name, name, "Names are not equal!")
        self.assertEqual(user.group.value, group, "Groups are not equal!")

    def testGetUser(self):
        """getUser retrieves a user from the database"""
        user = self.db.getUesr(self.test_user1.PFID)

        self.assertEqual(self.test_user1.PFID, user.PFID,"PFIDs are not equal!")
        self.assertEqual(self.test_user1.name, user.name, "Names are not equal!")
        self.assertEqual(self.test_user1.group, user.group, "Groups are not equal!")

        user = self.db.getUesr(self.test_user2.PFID)

        self.assertEqual(self.test_user2.PFID, user.PFID,"PFIDs are not equal!")
        self.assertEqual(self.test_user2.name, user.name, "Names are not equal!")
        self.assertEqual(self.test_user2.group, user.group, "Groups are not equal!")

    def testRemoveUser(self):
        """removeUser removes a user from the database"""
        self.db.removeUser(self.test_user1)

        self.cur.execute('SELECT * FROM users WHERE pfid=%s', (self.test_user1.PFID,))
        user = self.cur.fetchone()

        self.assertIsNone(user)

    def testGetPackage(self):
        """getPackage retrieves a package with the specified id"""
        package = self.db.getPackage(self.test_package1.id)

        self.assertEqual(self.test_package1.id, package.id, "ids are not equal!")
        self.assertEqual(self.test_package1.code, package.code, "Codes are not equal!")
        self.assertEqual(self.test_package1.date_received, package.date_received, "Dates are not equal!")
        self.assertEqual(self.test_package1.collected, package.collected, "Collected Status are not equal!")

        package = self.db.getPackage(self.test_package2.id)

        self.assertEqual(self.test_package2.id, package.id, "ids are not equal!")
        self.assertEqual(self.test_package2.code, package.code, "Codes are not equal!")
        self.assertEqual(self.test_package2.date_received, package.date_received, "Dates are not equal!")
        self.assertEqual(self.test_package2.collected, package.collected, "Collected Status are not equal!")

    def testAddPackage(self):
        """addPackage adds a package to the database"""
        package = Package.newPackage(9876, date_received=datetime.date.today())
        self.db.addPackage(package)

        self.cur.execute('SELECT * FROM packages WHERE id=%s', (package.id,))
        id, code, date_received, collected = self.cur.fetchone()

        self.assertEqual(package.id, id, "ids are not equal!")
        self.assertEqual(package.code, code, "Codes are not equal!")
        self.assertEqual(package.date_received, date_received, "Dates are not equal!")
        self.assertEqual(package.collected, collected, "Collected Status are not equal!")

    def testGetUncollected(self):
        """getUncollectedPackages returned all uncollected packages"""
        package = Package.newPackage(5643, datetime.date.today())
        self.cur.execute('INSERT INTO packages (id, code, date_received, collected) VALUES (%s, %s, %s, %s)',
                         (package.id,
                          package.code,
                          package.date_received,
                          package.collected))
        self.conn.commit()

        uncollected = self.db.getUncollectedPackages()

        self.assertLessEqual(len(uncollected), 2, "Returned extra packages!")
        self.assertIn(package, uncollected, "Missing package {}!".format(package.id))
        self.assertIn(self.test_package1, uncollected, "Missing package {}!".format(self.test_package1.id))


    def testClaimPackage(self):
        """claimPackage sets the collected attribute to True"""
        self.db.claimPackage(self.test_package1)

        self.cur.execute('SELECT * FROM packages WHERE id=%s', (self.test_package1.id,))
        id, code, date_received, collected = self.cur.fetchone()

        self.assertEqual(self.test_package1.id, id, "ids are not equal!")
        self.assertEqual(self.test_package1.code, code, "Codes are not equal!")
        self.assertEqual(self.test_package1.date_received, date_received, "Dates are not equal!")
        self.assertEqual(True, collected, "Collected Status not set to True!")

