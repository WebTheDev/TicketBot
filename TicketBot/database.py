import sqlite3
from config import databaseName

class TicketData():

    def connect():
        con = sqlite3.connect(f"./{databaseName}")
        return con

    def cursor(connection):
        cur = connection.cursor()
        return cur

    def createlayout(connection, cursor):
        cursor.execute("CREATE TABLE TicketData(ChannelID, AuthorID, Claimed, TimeCreated, Type, Status, MessageID)")
        connection.commit()
        TicketData.verifylayout(cursor)

    def verifylayout(cursor):
        res = cursor.execute("SELECT name FROM sqlite_master WHERE name='TicketData'")
        if res.fetchone() is None:
            return False
        else:
            return True

    def add(connection, cursor, ChannelID, AuthorID, TimeCreated, Type, Status, MessageID):
        cursor.execute(f"""
        INSERT INTO TicketData VALUES
             ('{ChannelID}', '{AuthorID}', 'No', '{TimeCreated}', '{Type}', '{Status}', '{MessageID}')
        """)
        connection.commit()

    def getall(cursor, list):
        for rows in cursor.execute("SELECT * FROM TicketData ORDER BY ChannelID"):
            list.append(rows)
        return list


    def find(cursor, ChannelID):
        for row in cursor.execute("SELECT * FROM TicketData ORDER BY ChannelID"):
            if row[0] == f"{ChannelID}":
                return row
            else:
                pass
        return None

    def edit(connection, cursor, row, Claimed, Status):
        TicketData.delete(connection, cursor, row[0])
        cursor.execute(f"INSERT INTO TicketData VALUES ('{row[0]}', '{row[1]}', '{Claimed}', '{row[3]}', '{row[4]}', '{Status}', '{row[6]}')")
        connection.commit()

    def delete(connection, cursor, ChannelID):
        try:
            sql_update_query = ("""DELETE from TicketData where ChannelID = ?""")
            cursor.execute(sql_update_query, (str(ChannelID),))
            connection.commit()
        except Exception as e:
            print(e)
        
    def close(connection):
        connection.close()