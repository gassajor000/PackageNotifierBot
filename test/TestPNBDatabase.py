"""
    created by Jordan Gassaway, 9/23/2020
    TestPNBDatabase: unit tests for pnb database
"""
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
        self.cur.execute('DROP TABLE IF EXISTS users;')
        self.cur.execute('CREATE TABLE users (pfid integer PRIMARY KEY, name varchar(40) NOT NULL, ugroup varchar(10) NOT NULL)')
        self.cur.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON users TO test_pnb')

        # Prefill with some data
        self.test_user1 = User(100, 'Harold Jenkins', User.Group.USER)
        self.test_user2 = User(101, 'Stevie Wonder', User.Group.ADMIN)

        self.cur.execute('INSERT INTO users (pfid, name, ugroup) VALUES (%s, %s, %s)', (self.test_user1.PFID,
                                                                                        self.test_user1.name,
                                                                                        self.test_user1.group.value))
        self.cur.execute('INSERT INTO users (pfid, name, ugroup) VALUES (%s, %s, %s)', (self.test_user2.PFID,
                                                                                        self.test_user2.name,
                                                                                        self.test_user2.group.value))
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
