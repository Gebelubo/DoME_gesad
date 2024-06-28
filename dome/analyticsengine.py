import sqlite3

import pandas as pd

from dome.config import LIMIT_REGISTERS, DATE_KEYWORDS, ANALYTICS
from util import list_util, date_util
from datetime import datetime

import tests

class AnalyticsEngine:
    def __init__(self, AC):
        # self.__IC = IC
        self.__AC = AC
        self.__TDB = None
        
    def __executeSqlCmd(self, sqlCmd):
        if self.__TDB is None:
            self.__TDB = sqlite3.connect(self.__AC.getTransactionDB_path(), check_same_thread=False)
        result = self.__TDB.cursor().execute(sqlCmd)
        self.__TDB.commit()

        return result
    
    def __checkEntity(self, entity_name):
        sql_cmd = "SELECT name FROM sqlite_master WHERE type ='table' AND name LIKE 'managedsys_web_" + entity_name + "';"
        cursor = self.__executeSqlCmd(sql_cmd)
        resultado = cursor.fetchone()
        
        return resultado
        
    def average(self, entity, attribute):
        table, row = entity, attribute
        #date_prompt = self.date_filter(words)
        date_prompt = ""
        
        if(self.__checkEntity(table)):
            sql_cmd = "SELECT AVG(" + row + ") FROM managedsys_web_" + table + date_prompt
        elif(self.__checkEntity(table + "s")):
            sql_cmd = "SELECT AVG(" + row + ") FROM managedsys_web_" + table + "s" + date_prompt
        elif(self.__checkEntity(table[:-1])):
            sql_cmd = "SELECT AVG(" + row + ") FROM managedsys_web_" + table[:-1] + date_prompt
        else:
            return "doesn't exist"
            
        cursor = self.__executeSqlCmd(sql_cmd)
        result = cursor.fetchone()

        if result[0] == None:
            return -1

        return round(result[0], 2)
    
    def highest(self, entity, attribute):
        table, row = entity, attribute
        #date_prompt = self.date_filter(words)
        date_prompt = ""
        
        if(self.__checkEntity(table)):
            sql_cmd = "SELECT MAX(" + row + ") FROM managedsys_web_" + table + date_prompt
        elif(self.__checkEntity(table + "s")):
            sql_cmd = "SELECT MAX(" + row + ") FROM managedsys_web_" + table + "s" + date_prompt
        elif(self.__checkEntity(table[:-1])):
            sql_cmd = "SELECT MAX(" + row + ") FROM managedsys_web_" + table[:-1] + date_prompt
        else:
            return "doesn't exist"

        cursor = self.__executeSqlCmd(sql_cmd)
        result = cursor.fetchone()

        if result[0] == None:
            return -1
        
        return result[0]
    
    def lowest(self, entity, attribute):
        table, row = entity, attribute
        # date_prompt = self.date_filter(words)
        date_prompt = ""
        
        if(self.__checkEntity(table)):
            sql_cmd = "SELECT MIN(" + row + ") FROM managedsys_web_" + table + date_prompt
        elif(self.__checkEntity(table + "s")):
            sql_cmd = "SELECT MIN(" + row + ") FROM managedsys_web_" + table + "s" + date_prompt
        elif(self.__checkEntity(table[:-1])):
            sql_cmd = "SELECT MIN(" + row + ") FROM managedsys_web_" + table[:-1] + date_prompt
        else:
            return "doesn't exist"
        
        cursor = self.__executeSqlCmd(sql_cmd)
        result = cursor.fetchone()

        if result[0] == None:
            return -1

        return result[0]
    
    def sum(self, entity, attribute):
        table, row = entity, attribute
        # date_prompt = self.date_filter(words)
        date_prompt = ""
        
        if(self.__checkEntity(table)):
            sql_cmd = "SELECT SUM(" + row + ") FROM managedsys_web_" + table + date_prompt
        elif(self.__checkEntity(table + "s")):
            sql_cmd = "SELECT SUM(" + row + ") FROM managedsys_web_" + table + "s" + date_prompt
        elif(self.__checkEntity(table[:-1])):
            sql_cmd = "SELECT SUM(" + row + ") FROM managedsys_web_" + table[:-1] + date_prompt
        else:
            return "doesn't exist"
        
        cursor = self.__executeSqlCmd(sql_cmd)
        result = cursor.fetchone()

        if result[0] == None:
            return -1

        return round(result[0], 2)

    def get_object(self, entity, attribute, operation="highest"):
        #words = msg.split()  # [get, product, with, highest, price]
        table = entity
        new_user_data = dict()
        attribute_key = 0
        if operation in ANALYTICS[1]:
            attribute_key = self.highest(entity, attribute)
        elif operation in ANALYTICS[2]:
            attribute_key = self.lowest(entity, attribute)
        else:
            return None
        if (self.__checkEntity(table)):
            sql_cmd = "SELECT * from managedsys_web_" + table + " where " + attribute + " = '" + str(attribute_key) + "' "

            # ordering by the newest
            # dome_updated_at is a reserved field automatically updated by the system
            sql_cmd += " ORDER BY dome_updated_at DESC"
            # put limit to LIMIT_REGISTERS
            sql_cmd += " LIMIT " + str(LIMIT_REGISTERS)
            print(sql_cmd)
            query = self.__executeSqlCmd(sql_cmd)
            cols = [column[0] for column in query.description]
            data = query.fetchall()
            if len(data) == 0:
                return None
            # else
            results = pd.DataFrame.from_records(data=data, columns=cols, index=['id'])
            results.drop(['dome_created_at', 'dome_updated_at'], axis=1, inplace=True)
            
            return results
        else:
            return None


    def date_filter(self, words):

        index = list_util.compare_index(words, DATE_KEYWORDS)
        if index != -1:

            date = words[index+1]
            date = date_util.format(date)
            return " WHERE DATE(dome_created_at) = " + date

        elif "today" in words:

            date = datetime.now().strftime("'%Y-%m-%d'")
            return " WHERE DATE(dome_created_at) = " + date
        else:
            return ""
