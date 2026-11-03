# -*- coding: utf-8 -*-
import pymysql
from config import DB_CONFIG

class Database:
    @staticmethod
    def get_connection():
        return pymysql.connect(
            host=DB_CONFIG['host'], port=DB_CONFIG['port'],
            user=DB_CONFIG['user'], password=DB_CONFIG['password'],
            database=DB_CONFIG['database'], charset=DB_CONFIG['charset'],
            cursorclass=pymysql.cursors.DictCursor
        )

    @staticmethod
    def execute_query(sql, params=None):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def execute_one(sql, params=None):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def execute_update(sql, params=None):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                conn.commit()
                return affected
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def execute_insert(sql, params=None):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def batch_insert(sql, data_list):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(sql, data_list)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
