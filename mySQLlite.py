import sqlite3
conn = sqlite3.connect('api.db')


class AssignedTasks:
    def __init__(self):
        self.conn = conn
        self.cur = conn.cursor()
        self.name_table = "AssignedTasks"
        self.cur.execute("""CREATE TABLE IF NOT EXISTS {}( id INT Primary KEY , title TEXT, created_at TEXT,
                    full_name TEXT, creator text, url TEXT, id_milestone INT);""".format(self.name_table))
        self.conn.commit()

    def save(self, id_task, title, created_at, full_name, name, url, id_milestone=''):
        self.cur.execute("""Insert INTO {}(id, title, created_at, full_name, name, url, id_milestone) VALUES 
        ({}, {}, {}, {}, {}, {}, {})""".format(self.name_table, id_task, title, created_at, full_name, name, url, id_milestone))
        self.conn.commit()


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


class Milestone:
    def __init__(self):
        self.conn = conn
        self.cur = conn.cursor()
        self.name_table = "Milestone"
        self.cur.execute("CREATE TABLE IF NOT EXISTS {}( id INT INCREMENT Primary KEY, title text);".format(self.name_table))
        self.conn.commit()

    def save(self, title):
        self.cur.execute("Insert INTO {}(title) VALUES ({})".format(self.name_table, title))
        self.conn.commit()


class Notifications:
    def __init__(self):
        self.conn = conn
        self.cur = conn.cursor()
        self.name_table = Notifications
        self.cur.execute("""Create table IF NOT EXISTS {}
                    (id INT INCREMENT PRIMARY KEY, message TEXT, user_login TEXT, full_name TEXT, created_time TEXT,
                     url TEXT)""".format(self.name_table))
        self.conn.commit()

    def save(self, message, user_login, full_name, created_time, url):
        self.cur.execute("Insert INTO {}(message, user_login, full_name, created_time, url) VALUES ({}, {}, {}, {}, {}"
                         .format(self.name_table, message, user_login, full_name, created_time, url))
        self.conn.commit()