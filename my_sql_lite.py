import sqlite3
conn = sqlite3.connect('api.db', check_same_thread=False)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


conn.row_factory = dict_factory


def change_conn(new_con):
    global conn
    conn = sqlite3.connect(new_con)


class AssignedTasks:
    def __init__(self):

        self.conn = conn
        self.cur = self.conn.cursor()
        self.name_table = "AssignedTasks"
        self.cur.execute("""CREATE TABLE IF NOT EXISTS {}( id INT PRIMARY KEY ,title TEXT, created_at TEXT,
                    full_name TEXT, creator TEXT, url TEXT, milestone_title TEXT);""".format(self.name_table))
        self.conn.commit()

    def save(self, task_id, title, created_time, full_name, creator, url, milestone_title):
        self.cur.execute("""INSERT INTO {}(id, title, created_at, full_name, creator, url, milestone_title) VALUES 
        ({}, {}, {}, {}, {}, {}, {})""".format(self.name_table, task_id, title, created_time, full_name,
                                               creator, url, milestone_title))
        self.conn.commit()

    def get_all(self):
        self.cur.execute("SELECT * FROM {}".format(self.name_table))
        return self.cur.fetchall()

    def clear(self):
        self.cur.execute("DELETE FROM {}".format(self.name_table))
        self.conn.commit()

    def delete_by_id(self, task_id):
        self.cur.execute("DELETE FROM {} WHERE id = {}".format(self.name_table, task_id))
        self.conn.commit()

class Users:
    def __init__(self):
        self.conn = conn
        self.cur = self.conn.cursor()
        self.name_table = "Users"
        self.cur.execute("""CREATE TABLE IF NOT EXISTS {}( id INTEGER PRIMARY KEY, token TEXT, server TEXT, delay INT,
                         full_name TEXT, login TEXT, avatar_url TEXT);""".format(self.name_table))
        if self.get() is None:
            self.save("null", "null", "null", "null", "null", 45)
        self.conn.commit()

    def save(self, full_name, login, token, avatar_url, server, delay):
        self.cur.execute(
            "INSERT INTO {}(full_name, login, token, avatar_url, server, delay) VALUES ({}, {}, {}, {}, {}, {})"
            .format(self.name_table, full_name, login, token, avatar_url, server, delay))
        self.conn.commit()

    def get(self):
        self.cur.execute("SELECT * FROM {}".format(self.name_table))
        return self.cur.fetchone()

    def update(self, update_dict):
        sql_command = "UPDATE {} SET ".format(self.name_table)
        for key in update_dict:
            sql_command += "{} = {}, ".format(key, update_dict[key])
        sql_command = sql_command[0:len(sql_command) - 2]
        self.cur.execute(sql_command)
        self.conn.commit()

    def clear(self):
        self.cur.execute("DELETE FROM {}".format(self.name_table))
        self.conn.commit()


class Notifications:
    def __init__(self):
        self.conn = conn
        self.cur = self.conn.cursor()
        self.name_table = "Notifications"
        self.cur.execute("""CREATE TABLE IF NOT EXISTS {}
                    (id INTEGER PRIMARY KEY, message TEXT, user_login TEXT, full_name TEXT, created_time TEXT,
                     url TEXT, user_avatar_name TEXT, state TEXT, title TEXT)""".format(self.name_table))
        self.conn.commit()

    def save(self, id_notification, message, user_login, full_name, created_time, url, user_avatar_name, state, title):
        self.cur.execute("INSERT INTO {}(id, message, user_login, full_name, created_time, url,"
                         " user_avatar_name, state, title) VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {})"
                         .format(self.name_table, id_notification, message, user_login,
                                 full_name, created_time, url, user_avatar_name, state, title))
        self.conn.commit()

    def get_all(self):
        self.cur.execute("SELECT * FROM {}".format(self.name_table))
        return self.cur.fetchall()

    def clear(self):
        self.cur.execute("DELETE FROM {}".format(self.name_table))
        self.conn.commit()
