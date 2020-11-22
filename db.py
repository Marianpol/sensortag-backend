import sqlite3
from sqlite3 import Error

class Database:    
    def __init__(self, dbName):
        self.dbName = dbName
        self.createDatabase()
    
    def writeReading(self, reading):
        query = """INSERT INTO readings
    (pressure, humidity, target_temp, temperature, currentdate)
        VALUES """ + reading
        
        connection = self.createConnection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(query)
            connection.commit()
        except Error as e:
            print(e)
            
        connection.close()

    def readTable(self, query):
        connection = self.createConnection()
        cursor = connection.cursor()
        result = None
        
        try:
            cursor.execute(query)
            result = cursor.fetchone()
            return result
        except Error as e:
            print(e)
            
        connection.close()

    def createConnection(self):
        connection = None
        try:
            connection = sqlite3.connect(self.dbName)
        except Error as e:
            print(e)
        
        return connection
    
    def createDatabase(self):
        TABLE_SCHEMA = """CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pressure NUMERIC,
            humidity NUMERIC,
            target_temp NUMERIC,
            temperature NUMERIC,
            currentdate DATETIME
            ) 
            """
        
        connection = self.createConnection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(TABLE_SCHEMA)
            connection.commit()
        except Error as e:
            print(e)
