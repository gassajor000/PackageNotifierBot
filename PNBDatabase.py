"""
    created by Jordan Gassaway, 9/23/2020
    PNBDatabase: Facilitates connection to the database of users and packages
"""
import enum
from datetime import date

import psycopg2


class User:
    class Group(enum.Enum):
        USER = 'user'
        ADMIN = 'admin'

        def __str__(self):
            return self.value

    def __init__(self, PFID: int, name: str, group: Group):
        self.name = name
        self.PFID = PFID
        self.group = group

    def __str__(self):
        return '(User %s, id %d, %s)' % (self.name, self.PFID, self.group)

    @classmethod
    def newUser(cls, PFID: int, name: str):
        return cls(PFID, name, cls.Group.USER)

    @classmethod
    def newAdmin(cls, PFID: int, name: str):
        return cls(PFID, name, cls.Group.ADMIN)


class Package:
    next_id = 0

    def __init__(self, id:int, code: int, date_received: date, collected: bool):
        self.id = id
        self.code = code
        self.date_received = date_received
        self.collected = collected

    def __str__(self):
        return '(Package %d, code %d, received %s, collected %s)' % (self.id, self.code, self.date_received, self.collected)

    @classmethod
    def newPackage(cls, code: int, date_received: date):
        cls.next_id += 1
        return cls(id=cls.next_id, code=code, date_received=date_received, collected=False)


class PNBDatabase:
    """Manage connection to PostRegDB and provide wrapper for db operations"""

    def __init__(self, db_name):
        self.db_name = db_name

    def login(self, user, password):
        self.conn = psycopg2.connect("dbname={} user={} password={}".format(self.db_name, user, password))
        self.cur = self.conn.cursor()

    def close(self):
        self.cur.close()
        self.conn.close()

    def addUser(self, user: User):
        self.cur.execute("INSERT INTO users (pfid, name, ugroup) VALUES (%s, %s, %s)", (user.PFID, user.name,
                                                                                        user.group.value))
        self.conn.commit()

    def getUesr(self, PFID: int):
        self.cur.execute("SELECT * FROM users WHERE pfid = %s", (PFID, ))
        user = self.cur.fetchone()
        return User(user[0], user[1], User.Group(user[2]))

    def removeUser(self, user: User):
        self.cur.execute("DELETE FROM users WHERE pfid = %s", (user.PFID, ))
        self.conn.commit()

    def addPackage(self, package:Package):
        pass

    def getPackage(self, id):
        pass

    def getUnclaimedPackages(self):
        pass

    def claimPackage(self, package: Package):
        pass


if __name__ == '__main__':
    db = PNBDatabase('packagenotificationbot')
    db.login()
    # db.addUser(User.newAdmin('Jordan Gassaway', 1234))
    user = db.getUesr(1234)
    print(user)
    db.removeUser(user)
    db.close()