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

    def __init__(self, PFID: str, name: str, group: Group):
        self.name = name
        self.PFID = PFID
        self.group = group

    def __str__(self):
        return '(User %s, id %s, %s)' % (self.name, self.PFID, self.group)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if not isinstance(other, User):
            return False

        if other is self:
            return True

        return self.PFID == other.PFID and self.name == other.name and self.group == other.group

    @classmethod
    def newUser(cls, PFID: str, name: str):
        return cls(PFID, name, cls.Group.USER)

    @classmethod
    def newAdmin(cls, PFID: str, name: str):
        return cls(PFID, name, cls.Group.ADMIN)

    def isAdmin(self):
        return self.group == User.Group.ADMIN


class Package:
    next_id = 0

    def __init__(self, id:int, code: int, date_received: date, collected: bool):
        self.id = id
        self.code = code
        self.date_received = date_received
        self.collected = collected

    def __str__(self):
        return '(Package #%d, code %d, received %s, collected %s)' % (self.id, self.code, self.date_received, self.collected)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if not isinstance(other, Package):
            return False

        if other is self:
            return True

        return self.id == other.id and self.code == other.code and self.date_received == other.date_received and self.collected == other.collected

    @classmethod
    def set_next_id(cls, next_id):
        cls.next_id = next_id

    @classmethod
    def newPackage(cls, code: int, date_received: date):
        id = cls.next_id
        cls.next_id += 1
        return cls(id=id, code=code, date_received=date_received, collected=False)


class PNBDatabase:
    """Manage connection to PostRegDB and provide wrapper for db operations"""
    class Config():
        def get_connect_args(self):
            raise NotImplementedError("This is an abstract class!")

    class URLConfig(Config):
        def __init__(self, url):
            self.url = url

        def get_connect_args(self):
            return (self.url, ), {'sslmode': 'require'}

    class CredentialsConfig():
        def __init__(self, db_name, user, password):
            self.password = password
            self.user = user
            self.db_name = db_name

        def get_connect_args(self):
            conn_str = "dbname={} user={} password={}".format(self.db_name, self.user,
                                                                                self.password)
            return (conn_str, ), {}

    def __init__(self, config: Config):
        self.config = config

    def login(self):
        args, kwargs = self.config.get_connect_args()
        self.conn = psycopg2.connect(*args, **kwargs)
        self.cur = self.conn.cursor()

        # This is necessary because resetting the server will reset next_id to 0, leading to duplicate package ids
        Package.set_next_id(self._get_max_package_id() + 1)

    def close(self):
        self.cur.close()
        self.conn.close()

    def addUser(self, user: User):
        self.cur.execute("INSERT INTO users (pfid, name, ugroup) VALUES (%s, %s, %s)", (user.PFID, user.name,
                                                                                        user.group.value))
        self.conn.commit()

    def getUser(self, PFID: int):
        self.cur.execute("SELECT * FROM users WHERE pfid = %s", (PFID, ))
        user = self.cur.fetchone()
        if user is None:
            return None
        else:
            return User(user[0], user[1], User.Group(user[2]))

    def getAllUsers(self):
        self.cur.execute("SELECT * FROM users")
        user = self.cur.fetchone()
        users = []
        while user is not None:
            users.append(User(user[0], user[1], User.Group(user[2])))
            user = self.cur.fetchone()

        return users

    def getAllAdmins(self):
        self.cur.execute("SELECT * FROM users WHERE ugroup=%s", (User.Group.ADMIN.value, ))
        user = self.cur.fetchone()
        users = []
        while user is not None:
            users.append(User(user[0], user[1], User.Group(user[2])))
            user = self.cur.fetchone()

        return users

    def getUserByName(self, name: str):
        self.cur.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(%s)", (name, ))
        user = self.cur.fetchone()
        if user is None:
            return None
        else:
            return User(user[0], user[1], User.Group(user[2]))

    def removeUser(self, user: User):
        self.cur.execute("DELETE FROM users WHERE pfid = %s", (user.PFID, ))
        self.conn.commit()

    def addPackage(self, package:Package):
        self.cur.execute("INSERT INTO packages (id, code, date_received, collected) VALUES (%s, %s, %s, %s)", (package.id, package.code, package.date_received, package.collected))
        self.conn.commit()

    def getPackage(self, id):
        self.cur.execute("SELECT * FROM packages WHERE id = %s", (id,))
        package = self.cur.fetchone()
        if package is None:
            return None
        else:
            return Package(package[0], package[1], package[2], package[3])

    def getUncollectedPackages(self):
        self.cur.execute("SELECT * FROM packages WHERE collected=False")
        package = self.cur.fetchone()
        packages = []
        while package is not None:
            packages.append(Package(package[0], package[1], package[2], package[3]))
            package = self.cur.fetchone()

        return packages

    def claimPackage(self, package: Package):
        self.cur.execute("UPDATE packages SET collected=True WHERE id=%s", (package.id,))
        self.conn.commit()

    def _get_max_package_id(self):
        """Return the largest package id in the database"""
        self.cur.execute("SELECT MAX(id) FROM packages")
        return int(self.cur.fetchone()[0])


if __name__ == '__main__':
    db = PNBDatabase('packagenotificationbot')
    db.login()
    # db.addUser(User.newAdmin('Jordan Gassaway', 1234))
    user = db.getUser(1234)
    print(user)
    db.removeUser(user)
    db.close()