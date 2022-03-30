import sqlite3
conn = sqlite3.connect('api.db')


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class AssignedTasks:
    def __init__(self):
        self.conn = conn
        self.cur = conn.cursor()
        self.name_table = "AssignedTasks"
        self.cur.execute("""CREATE TABLE IF NOT EXISTS {}( id INT Primary KEY , title TEXT, created_at TEXT,
                    full_name TEXT, creator text, url TEXT, id_milestone INT);""".format(self.name_table))
        self.conn.commit()

    def save(self, id_task, title, created_at, full_name, name, url, milestone_title):
        self.cur.execute("""Insert INTO {}(id, title, created_at, full_name, name, url, milestone_title) VALUES 
        ({}, {}, {}, {}, {}, {}, {})""".format(self.name_table, id_task, title, created_at, full_name,
                                               name, url, milestone_title))
        self.conn.commit()

    def get_all(self):
        self.cur.execute("Select * From {}".format(self.name_table))
        return self.cur.fetchall()


class Users:
    def __init__(self):
        self.conn = conn
        self.cur = self.conn.cursor()
        self.name_table = "Users"
        self.cur.execute("""CREATE TABLE IF NOT EXISTS {}( id INT INCREMENT Primary KEY , full_name TEXT, login TEXT,
                    token TEXT, avatar_url text);""".format(self.name_table))
        self.conn.commit()

    def save(self, full_name, login, token, avatar_url):
        self.cur.execute(
            "Insert INTO {}(full_name, login, token, avatar_url) VALUES ({}, {}, {}, {})"
            .format(self.name_table, full_name, login, token, avatar_url))
        self.conn.commit()

    def get_all(self):
        self.cur.execute("Select * From {}".format(self.name_table))
        return self.cur.fetchall()


class Notifications:
    def __init__(self):
        self.conn = conn
        self.cur = conn.cursor()
        conn.row_factory = dict_factory
        self.name_table = "Notifications"
        self.cur.execute("""Create table IF NOT EXISTS {}
                    (id INT INCREMENT PRIMARY KEY, message TEXT, user_login TEXT, full_name TEXT, created_time TEXT,
                     url TEXT)""".format(self.name_table))
        self.conn.commit()

    def save(self, message, user_login, full_name, created_time, url):
        self.cur.execute("Insert INTO {}(message, user_login, full_name, created_time, url) VALUES ({}, {}, {}, {}, {})"
                         .format(self.name_table, message, user_login, full_name, created_time, url))
        self.conn.commit()

    def get_all(self):
        self.cur.execute("Select * From {}".format(self.name_table))
        return self.cur.fetchall()