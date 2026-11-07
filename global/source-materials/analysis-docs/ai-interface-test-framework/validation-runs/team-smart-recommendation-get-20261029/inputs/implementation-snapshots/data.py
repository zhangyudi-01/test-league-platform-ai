"""
数据相关方法
"""
import json
import logging
import random
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

import allure
import pylightxl as xl
import pymysql
import redis
from json_tools import diff
from pymysql import FIELD_TYPE, converters
from pymysql.constants import CLIENT
from redis.sentinel import Sentinel

from settings import (DATA_COMPUTATION_REDIS_CONFIG, DB_HOST, DB_NAME,
                      DB_PASSWORD, DB_PORT, DB_USER, TMP_DIR)

# --- pylightxl 兼容性补丁 ---
# 部分 xlsx 文件将 xmlns:r 声明在 <sheet> 元素上而非根 <workbook> 元素，
# 导致 pylightxl 无法获取 r 命名空间、rId 为 None 而抛出 TypeError。
# 此补丁在原始函数失败时，使用硬编码命名空间重新解析 workbook.xml。
import pylightxl.pylightxl as _px

_orig_readxl_get_workbook = _px.readxl_get_workbook


def _patched_readxl_get_workbook(fn):
    try:
        return _orig_readxl_get_workbook(fn)
    except TypeError:
        import zipfile
        import xml.etree.ElementTree as etree
        import re as _re
        _R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        _M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        _ns = {'default': _M, 'r': _R}
        rv = {'ws': {}, 'nr': {}}
        with zipfile.ZipFile(fn, 'r') as _z:
            with _z.open('xl/workbook.xml', 'r') as _f:
                _root = etree.parse(_f).getroot()
        _wbrels = _px.readxl_get_workbookxmlrels(fn)
        for _tag in _root.findall('./default:sheets/default:sheet', _ns):
            _name = _tag.get('name')
            _rId = _tag.get('{' + _R + '}id') or _tag.get('id')
            _sid = int(_re.sub('[^0-9]', '', _rId))
            rv['ws'][_name] = {'ws': _name, 'rId': _rId, 'order': _sid,
                               'fn_ws': _wbrels[_rId]}
        for _tag in _root.findall('./default:definedNames/default:definedName', _ns):
            _name = _tag.get('name')
            _addr = (_tag.text or '').replace('$', '')
            try:
                _ws, _cell = _addr.split('!')
                _ws = _ws.replace("'", "")
            except ValueError:
                continue
            rv['nr'][_name] = {'nr': _name, 'ws': _ws, 'address': _cell}
        return rv


_px.readxl_get_workbook = _patched_readxl_get_workbook

# --- pylightxl inlineStr 兼容性补丁 ---
# 部分 xlsx 文件使用 inlineStr 格式存储字符串（<is><t>文本</t></is>），
# pylightxl 原生不支持此格式，导致单元格值为空。
# 此补丁扩展 readxl_scrape 以支持 inlineStr。
_orig_readxl_scrape = _px.readxl_scrape


def _patched_readxl_scrape(fn, fn_ws, sharedString, styles, comments):
    data = _orig_readxl_scrape(fn, fn_ws, sharedString, styles, comments)
    # Check if any cells have empty values - if so, try inlineStr parsing
    import zipfile
    import xml.etree.ElementTree as etree
    _M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    _ns = {'default': _M}
    with zipfile.ZipFile(fn, 'r') as f_zip:
        with f_zip.open('xl/' + fn_ws, 'r') as file:
            root = etree.parse(file).getroot()
    for tag_cell in root.findall('./default:sheetData/default:row/default:c', _ns):
        cell_address = tag_cell.get('r')
        cell_type = tag_cell.get('t')
        if cell_type == 'inlineStr' and cell_address not in data:
            tag_is = tag_cell.find('./default:is/default:t', _ns)
            if tag_is is not None and tag_is.text:
                data[cell_address] = {'v': tag_is.text, 'f': '', 's': '', 'c': ''}
    return data


_px.readxl_scrape = _patched_readxl_scrape

DB_TABLE = Literal[
    "batch_diff_record",
    "batch_matchup",
    "batch_matchup_diff",
    "batch_matchup_draft",
    "batch_operation",
    "d_batch",
    "d_batch_matchup_result",
    "d_change_record",
    "d_data_source",
    "d_game_draw",
    "d_game_draw_match_monitor",
    "d_match_check",
    "d_match_event",
    "game_draw",
    "m_competition",
    "m_season",
    "m_team",
    "matchup",
    "nami_basketball_match",
    "nami_football_category",
    "nami_football_competition",
    "nami_football_competition_rule",
    "nami_football_country",
    "nami_football_match",
    "nami_football_season",
    "nami_football_stage",
    "nami_football_team",
    "nami_football_venue",
    "s_category",
    "s_competition",
    "s_competition_bak",
    "s_country",
    "s_country_bak",
    "s_event",
    "s_match",
    "s_match_bak",
    "s_season",
    "s_season_bak",
    "s_stage",
    "s_team",
    "s_team_bak",
    "s_venue",
    "toto_account",
    "toto_account_role",
    "toto_config",
    "toto_dict",
    "toto_err",
    "toto_operation_record",
    "toto_permission",
    "toto_role",
    "toto_role_permission",
    "toto_system",
    "tx_competition",
    "tx_match",
    "tx_team",
]


def get_random_str(length=16):
    """
    生成一个指定长度的随机字符串
    """
    ascii_letters = '0123456789abcdefghigklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' * \
        ((length//62)+1)
    str_list = random.sample(ascii_letters, length)
    random_str = ''.join(str_list)
    return random_str


class Select:
    """构造子查询
    """

    def __init__(self,
                 table: DB_TABLE,
                 column: str,
                 query_dict: dict = None) -> None:
        """构造子查询

        Args:
            table (str): 表名
            column (str): 列名
            query_dict (dict, optional): 查询条件. Defaults to None.
        """
        self.sql, self.args = DB.sql_args_query(f'select `{column}`', table,
                                                query_dict)


class DB:
    '''
    数据库类
    '''
    sql = None

    def __init__(self,
                 host: str = DB_HOST,
                 port: int = int(DB_PORT),
                 user: str = DB_USER,
                 password: str = DB_PASSWORD,
                 database: str = DB_NAME) -> None:
        """数据库类. 类方法中query_dict参数说明参考DB._sql_where方法

        Args:
            host (str, optional): 数据库IP.
            port (int, optional): 端口号. 
            user (str, optional): 用户名. 
            password (str, optional): 密码. 
            database (str, optional): 库名. 

        """
        conv = converters.conversions
        conv[FIELD_TYPE.DATE] = str  # convert dates to strings
        conv[FIELD_TYPE.TIMESTAMP] = str  # convert dates to strings
        conv[FIELD_TYPE.TIME] = str  # convert dates to strings
        conv[FIELD_TYPE.DATETIME] = str  # convert dates to strings
        self.conv = conv
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.database = database
        self._connect()

    def _connect(self):
        conn_time = 0
        while conn_time < 3:
            try:
                self.conn = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    charset='utf8mb4',
                    autocommit=True,
                    client_flag=CLIENT.MULTI_STATEMENTS,
                    conv=self.conv,
                    init_command="SET SESSION group_concat_max_len=10240")
                return
            except Exception as e:
                conn_time += 1
                print(f'数据库连接失败:{e}，20秒后，第{conn_time}次重试')
                # 20秒后重试
                time.sleep(20)
        else:
            logging.error('数据库连接失败，退出测试')
            exit()

    def _check_connection(self):
        try:
            self.conn.ping(False)
            return
        except Exception as e:
            print(f'数据库连接失败:{e}，重新连接。')
            self._connect()

    def get_asdict(self, sql: str, args=None) -> list[dict]:
        """以字典形式返回查询结果

        Args:
            sql (str): 查询语句
            args (tuple,list,dict): 参数化，用法同：https://pymysql.readthedocs.io/en/latest/modules/cursors.html#pymysql.cursors.Cursor.execute
        Returns:
            list: 列表中每一项为字典，格式
        """
        self._check_connection()
        dict_cursor = self.conn.cursor(cursor=pymysql.cursors.SSDictCursor)
        try:
            dict_cursor.execute(sql, args=args)
            # 获取所有记录列表
            self.sql = dict_cursor._executed
            result = dict_cursor.fetchall()
        except pymysql.err.ProgrammingError as e:
            print(f'查询语句：{dict_cursor.mogrify(sql, args)}')
            raise e
        finally:
            dict_cursor.close()
        return result
    
    def get_asdict_args_dict(self, sql: str, args=None) -> list[dict]:
        """以字典形式返回查询结果（支持字典参数格式）
        
        Args:
            sql (str): SQL查询语句，必须使用字典格式的参数化查询
            args (dict, optional): 字典格式的查询参数，键对应SQL中的命名参数
            
        Returns: 
            list[dict]: 返回字典列表，每个字典对应一行数据，键为列名
            
        Raises:
            pymysql.err.ProgrammingError: 当SQL语句有语法错误时抛出
        """
        self._check_connection()
        dict_cursor = self.conn.cursor(cursor=pymysql.cursors.SSDictCursor)
        try:
            dict_cursor.execute(sql, args=args)
            # 获取所有记录列表
            self.sql = dict_cursor._executed
            result = dict_cursor.fetchall()
        except pymysql.err.ProgrammingError as e:
            print(f'查询语句：{dict_cursor.mogrify(sql, args)}')
            raise e
        finally:
            dict_cursor.close()
        return result

    def get_aslist(self, sql: str, args=None) -> list[tuple]:
        """以列表形式返回查询结果

        Args:
            sql (str): 查询语句
            args (tuple,list,dict): 参数化，用法同：https://pymysql.readthedocs.io/en/latest/modules/cursors.html#pymysql.cursors.Cursor.execute
        Returns:
            list[tuple]: 返回结果，内容格式为tuple
        """
        self._check_connection()
        cursor = self.conn.cursor(cursor=pymysql.cursors.SSCursor)
        try:
            cursor.execute(sql, args)
            self.sql = cursor._executed
            # 获取所有记录列表
            result = cursor.fetchall()
        except pymysql.err.ProgrammingError as e:
            print(f'查询语句：{cursor.mogrify(sql, args)}')
            raise e
        finally:
            cursor.close()
        return result

    def execute(self, sql: str, args=None) -> int:
        """执行sql

        Args:
            sql (str): 查询语句
            args (_type_, optional): 查询参数. Defaults to None.

        Returns:
            int: 受影响的行数
        """
        self._check_connection()
        cursor = self.conn.cursor()
        try:
            result = cursor.execute(sql, args=args)
            self.sql = cursor._executed
            self.lastrowid = cursor.lastrowid
        except pymysql.err.ProgrammingError as e:
            print(f'查询语句：{cursor.mogrify(sql, args)}')
            raise e
        finally:
            cursor.close()
        return result

    def executemany(self, sql: str, data: list | tuple) -> int | None:
        """根据data，执行多遍sql

        Args:
            sql (str): 查询语句
            data (list | tuple): 参数内容，例[[1,2],[3,4]]，第一遍执行使用[1,2]，第二遍执行使用[3,4]

        Returns:
            int| None: 受影响的行数
        """
        self._check_connection()
        cursor = self.conn.cursor()
        result = cursor.executemany(sql, data)
        self.sql = cursor._executed
        self.lastrowid = cursor.lastrowid
        cursor.close()
        return result

    def get_first(self, sql: str, sql_args: list = None) -> tuple:
        """返回第一条查询结果

        Args:
            sql (str): 查询语句
            sql_args (list, optional): 查询参数. Defaults to None.

        Returns:
            tuple: 第一条查询结果
        """
        cursor = self.conn.cursor()
        cursor.execute(sql, sql_args)
        self.sql = cursor._executed
        result = cursor.fetchone()
        cursor.close()
        return result

    def get_one(self, sql: str, sql_args: list = None):
        """返回一个具体值

        Args:
            sql (str): 查询语句
            sql_args (list, optional): 查询参数. Defaults to None.

        Returns:
            any: 返回查询结果第一条第一列的内容
        """
        result = self.get_first(sql, sql_args)
        try:
            if result is not None:
                return result[0]
            else:
                return None
        except Exception as e:
            print(f'查询语句：{sql},参数：{sql_args}')
            raise e

    def get_max(self, table: DB_TABLE, column: str, query_dict: dict = {}):
        """返回指定表字段最大值

        Args:
            table (DB_TABLE): 表名
            column (str): 字段名
            query_dict (dict, optional): 条件，值为str时为等于，值为list时为in. Defaults to {}.
        """
        sql, sql_args = self.sql_args_query(f'select max({column})', table,
                                            query_dict)
        return self.get_one(sql, sql_args)

    def get_in_list(self,
                    table: DB_TABLE,
                    column: str,
                    query_dict: dict = {},
                    orderby: Literal['ASC', 'DESC'] = None,
                    size: int = None,
                    page: int = None) -> list:
        """返回指定列的值列表

        Args:
            table (DB_TABLE): 指定表
            column (str): 指定字段
            query_dict (dict, optional): 条件，值为str时为等于，值为list时为in. Defaults to {}.
            orderby (Literal['ASC', 'DESC'], optional): 升序或降序，排序字段为入参column. Defaults to None，不排序.
            size (int, optional): 返回个数. Defaults to None.
            page (int, optional): 按照size分页，返回指定页的内容. Defaults to None.
        Returns:
            list: 指定列的值列表
        """
        if orderby and orderby.upper() in ['ASC', 'DESC']:
            orderby = f'{column} {orderby}'
        sql, sql_args = self.sql_args_query(f'select DISTINCT {column}', table,
                                            query_dict, orderby, size, page)
        tmp_list = self.get_aslist(sql, sql_args)
        return [t[0] for t in tmp_list]

    @staticmethod
    def _sql_where(query_dict: dict[str, int | list | str | Select] = {}):
        """生成sql的where语句部分

        Args:
            query_dict (dict[str, int  |  list  |  str | Select], optional): 参数字典. Defaults to {}.key可以由'列名__后缀'组成，
                后缀：
                'contains'表示包含;
                'startswith'表示以value开头;
                'endswith'表示以value结束;
                'lt'表示小于;
                'lte'表示小于等于;
                'gt'表示大于;
                'gte'表示大于等于;
                'between'表示介于, value为list或tuple, 长度为2;
                'isnull'表示为空;
                'not'表示不等于或not in。

        Raises:
            KeyError: key的后缀错误
        """
        if not query_dict:
            return '', None
        sql_args = []
        sql = ' where '
        query_list = []
        for key, value in query_dict.items():
            args_flag = True
            if '__' in key:
                key, suffix = key.split('__')
            else:
                suffix = None
            if type(value) in (list, tuple, set):
                if len(value) == 0:
                    if suffix is None:
                        query_list.append(f'`{key}`!=`{key}`')
                    args_flag = False
                else:
                    if suffix == 'not':
                        query_list.append(f'`{key}` not in %s')
                    elif suffix == 'between':
                        query_list.append(f'`{key}` between %s and %s')
                        args_flag = False
                        sql_args.extend(value)
                    elif suffix is None:
                        query_list.append(f'`{key}` in %s')
                    else:
                        raise KeyError(f'{key}后缀{suffix}错误')
            elif type(value) == Select:
                if suffix == 'not':
                    query_list.append(f'`{key}` not in ({value.sql})')
                else:
                    query_list.append(f'`{key}` in ({value.sql})')
                args_flag = False
                if value.args:
                    sql_args.extend(value.args)
            else:
                match suffix:
                    case None:
                        if value is None:
                            query_list.append(f'`{key}` is NULL')
                            args_flag = False
                        else:
                            query_list.append(f'`{key}`=%s')
                    case 'contains':
                        query_list.append(f"`{key}` like CONCAT('%%',%s,'%%')")
                    case 'startswith':
                        query_list.append(f"`{key}` like CONCAT(%s,'%%')")
                    case 'endswith':
                        query_list.append(f"`{key}` like CONCAT('%%',%s)")
                    case 'lt':
                        query_list.append(f"`{key}`<%s")
                    case 'lte':
                        query_list.append(f"`{key}`<=%s")
                    case 'gt':
                        query_list.append(f"`{key}`>%s")
                    case 'gte':
                        query_list.append(f"`{key}`>=%s")
                    case 'isnull':
                        query_list.append(f'`{key}` is NULL')
                        args_flag = False
                    case 'not':
                        if value is None:
                            query_list.append(f'`{key}` is not NULL')
                            args_flag = False
                        else:
                            query_list.append(f'`{key}`!=%s')
                    case _:
                        raise KeyError(f'{key}后缀{suffix}错误')
            if args_flag:
                sql_args.append(value)
        sql += ' and '.join(query_list)
        return sql, sql_args

    @staticmethod
    def sql_args_query(action: str,
                       table: DB_TABLE,
                       query_dict: dict[str, int | list | str] = {},
                       orderby: str = '',
                       size: int = None,
                       page: int = None):
        """根据字典构造查询语句

        Args:
            action (str): sql的动作，例：'select draw_id'
            table (str): 表名
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法
            orderby (str, optional): 排序条件. Defaults to ''.
            size (int, optional): 每页大小. Defaults to None.
            page (int, optional): 页数. Defaults to None.

        Returns:
            sql, sql_args: 查询语句，参数列表
        """
        sql = f'{action} from `{table}`'
        sql_where, sql_args = DB._sql_where(query_dict)
        sql += sql_where
        if orderby:
            sql += f' order by {orderby}'
        if size:
            if page:
                sql += f' limit {(page-1)*size},{size}'
            else:
                sql += f' limit {size}'
        return sql, sql_args

    def _update_exec(self,
                     action: str,
                     table: DB_TABLE,
                     update_dict: dict[str, str | int] | list[dict],
                     query_dict: dict = {}) -> int | None:
        """执行update或replace

        Args:
            action (str): 动作
            table (str): 表名
            update_dict (dict[str, str  |  int] | list[dict]): description_
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法

        Returns:
            int | None: 受影响的行数
        """
        sql = f'{action} `{table}` set '
        sql_args = []
        update_list = []
        if isinstance(update_dict, list):
            for key, value in update_dict[0].items():
                update_list.append(f'`{key}`=%s')
            for ud in update_dict:
                sql_args.append(tuple(ud.values()))
        else:
            for key, value in update_dict.items():
                update_list.append(f'`{key}`=%s')
                sql_args.append(value)
        sql += ','.join(update_list)
        if query_dict:
            sql_where, args_where = DB._sql_where(query_dict)
            sql += sql_where
            if isinstance(update_dict, list):
                for arg in sql_args:
                    arg.extend(args_where)
            else:
                sql_args.extend(args_where)
        if isinstance(update_dict, list):
            result = self.executemany(sql, sql_args)
        else:
            result = self.execute(sql, sql_args)
        return result

    def update(self, table: DB_TABLE, update_dict: dict,
               query_dict: dict) -> int | None:
        """执行update命令

        Args:
            table (DB_TABLE): 表名
            update_dict (dict): 更新字典
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法

        Returns:
            int| None: 受影响的行数
        """
        result = self._update_exec('update', table, update_dict, query_dict)
        return result

    def replace_into(self, table: DB_TABLE,
                     update_dict: dict[str, str | int] | list[dict]):
        """执行replace into命令，入参说明参考update方法"""
        result = self._update_exec('replace into', table, update_dict)
        return result

    def insert(self, table: DB_TABLE,
               update_dict: dict[str, str | int] | list[dict]):
        """执行insert into命令，入参说明参考update方法"""
        result = self._update_exec('insert into', table, update_dict)
        return result

    def delete(self, table: DB_TABLE, query_dict: dict):
        """删除数据

        Args:
            table (str): 表名
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法
        """
        sql, sql_args = self.sql_args_query('delete', table, query_dict)
        result = self.execute(sql, sql_args)
        return result

    def count(self,
              table: DB_TABLE,
              query_dict: dict,
              column: str = '*') -> int:
        """获取数量

        Args:
            table (str): 表名
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法
            column (str): count的列名，默认为*
        Returns:
            int: 符合条件的数量
        """
        sql, sql_args = self.sql_args_query(f'select count({column})', table,
                                            query_dict)
        return self.get_one(sql, sql_args)

    def exec_file(self, filepath: str | Path):
        """执行sql文件

        Args:
            filepath (str | Path): 文件路径

        """
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_file = f.read()
        cursor = self.conn.cursor()
        cursor.execute(sql_file)
        self.sql = cursor._executed
        cursor.close()

    def recovery_from_data(self,
                           table: DB_TABLE,
                           data_list: list[dict] | list[list],
                           col_list: list | tuple = None):
        """恢复数据，数据中必须有主键或唯一索引

        Args:
            table (DB_TABLE): 要恢复的表名
            data_list (list[dict], list[list]): 需要恢复的数据，每条数据为字典或列表形式，字典key：列名
            col_list (list, tuple): 更新数据对应的列名，只有data_list为list[list]时使用，不写则全部列，需要注意顺序
        """
        if isinstance(data_list[0], dict):
            col_list = [f'`{col}`' for col in data_list[0].keys()]
            values = [
                tuple(value for value in data.values()) for data in data_list
            ]
        else:
            values = data_list
            if col_list:
                col_list = [f'`{col}`' for col in col_list]
        colstr = f"({','.join(col_list)})" if col_list else ''
        sql = f'replace into `{table}`{colstr} values({",".join(["%s"]*len(values[0]))})'
        self.executemany(sql, values)

    def recovery_from_table(self,
                            table: DB_TABLE,
                            query_dict: dict = None,
                            table_bak: str = None):
        """从table_bak中恢复数据到表table中

        Args:
            table (DB_TABLE): 想要恢复的表
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法
            table_bak (str, optional): 备份表名，默认为table后面加_bak
        """
        if not table_bak:
            table_bak = f'{table}_bak'
        if self.get_one('SHOW TABLES LIKE %s', [table_bak]) is None:
            print(f'不存在备份表{table_bak}')
            return
        sql, sqlargs = self.sql_args_query(f'replace into `{table}` select *',
                                           table_bak, query_dict)
        self.execute(sql, sqlargs)

    def backup_to_table(self,
                        table: DB_TABLE,
                        query_dict: dict = None,
                        table_bak: str = None):
        """备份表table数据，到新表table_bak中，存在则更新

        Args:
            table (DB_TABLE): 要备份的表
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法
            table_bak (str): 备份表名，默认为table后面加_bak
        """
        if not table_bak:
            table_bak = f'{table}_bak'
        create_ddl = self.get_first(f'show CREATE table {table}')[1].split(
            'ENGINE',
            1)[0].replace(f'CREATE TABLE `{table}`',
                          f'CREATE TABLE IF NOT EXISTS `{table_bak}`', 1)
        self.execute(create_ddl)
        sql, sqlargs = self.sql_args_query(
            f'replace into `{table_bak}` select *', table, query_dict)
        self.execute(sql, sqlargs)

    def backup_to_file(self,
                       bak_file: Path,
                       table: DB_TABLE,
                       query_dict: dict = None):
        """备份表table数据成replace语句，到文件bak_file中

        Args:
            bak_file (Path): 备份文件的Path对象
            table (DB_TABLE): 要备份的表
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法
        """
        bak_file.parent.mkdir(parents=True, exist_ok=True)
        cols_list = [
            c[0] for c in self.get_aslist(
                'select COLUMN_NAME from information_schema.columns where TABLE_NAME=%s and TABLE_SCHEMA=%s',
                [table, DB_NAME])
        ]
        sql, sqlargs = self.sql_args_query('select *', table, query_dict)
        data_to_bak = self.get_aslist(sql, sqlargs)
        cols = ','.join(cols_list)
        sql = ''
        for data in data_to_bak:
            sql += f'replace into {table} ({cols}) values {data};'
        sql = sql.replace(', None', ', NULL').replace('Decimal(', '(')
        with open(bak_file, 'w', encoding='utf8') as f:
            f.write(sql)
        allure.attach.file(bak_file,
                           name=bak_file.name,
                           extension=bak_file.suffix.removeprefix('.'))

    def drop_partition(self, table: DB_TABLE, names: list, prefix: str = 'p'):
        """删除分区

        Args:
            table (DB_TABLE): 表名
            names (list): PARTITION_NAME除去前缀的列表
            prefix (str, optional): PARTITION_NAME的前缀，默认为p
        """
        p_names = [f'{prefix}{name}' for name in names]
        p_list = self.get_aslist(
            """select t.PARTITION_NAME
            from INFORMATION_SCHEMA.`PARTITIONS` t
            where t.TABLE_SCHEMA =%s
            and t.TABLE_NAME=%s and t.PARTITION_NAME in %s""",
            [DB_NAME, table, p_names])
        pn_list = [pn[0] for pn in p_list]
        sql = ''
        for name in p_names:
            if name in pn_list:
                sql += f'alter table {table} drop PARTITION {name};'
        self.execute(sql)

    def add_partition(self, table: DB_TABLE, names: list, prefix: str = 'p'):
        """创建分区

        Args:
            table (DB_TABLE): 表名
            names (list): PARTITION_NAME除去前缀的列表
            prefix (str, optional): PARTITION_NAME的前缀，默认为p
        """
        p_names = [f'{prefix}{name}' for name in names]
        p_list = self.get_aslist(
            """select t.PARTITION_NAME
            from INFORMATION_SCHEMA.`PARTITIONS` t
            where t.TABLE_SCHEMA =%s
            and t.TABLE_NAME=%s and t.PARTITION_NAME in %s""",
            [DB_NAME, table, p_names])
        pn_list = [pn[0] for pn in p_list]
        sql = ''
        for name in p_names:
            if name not in pn_list:
                sql += f'alter table {table} add partition (partition {name} values in ({name[1:]}));'
        if sql:
            self.execute(sql)

    def snapshot(self, table_name: str, query_dict: dict):
        """记录表快照，快照表名为原表名+__snapshot

        Args:
            table_name (str): 表名
            query_dict (dict, optional): 参数字典. 说明参考DB._sql_where方法
        """
        snapshot_table = f'{table_name}__snapshot'
        if not self.get_one(
                'SELECT COUNT(*) from information_schema.tables  WHERE table_schema = DATABASE() and TABLE_NAME = %s',
            [snapshot_table]):
            info_dict = self.get_aslist(f"DESCRIBE {table_name}")
            col_list = [f'{i[0]} {i[1]}' for i in info_dict]
            col_list.append(
                'snapshot__time datetime not null default current_timestamp')
            create_sql = f"""CREATE TABLE IF NOT EXISTS {snapshot_table} ({','.join(col_list)})"""
            self.execute(create_sql)
        sql_where, sql_args = self._sql_where(query_dict)
        self.execute(
            f"INSERT INTO {snapshot_table} SELECT *,now() FROM {table_name} {sql_where}",
            sql_args)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, trace):
        self.close()


class Excel:

    def __init__(self, filepath: str | Path):
        """excel文件，支持xlsx、xlsm

        Args:
            filepath (str | Path): 文件完整，支持str和pathlib.Path类型
        """
        self.file = xl.readxl(filepath)

    def __sheet(self, sheetname: str = None):
        """获取工作表对象

        Args:
            sheetname (str, optional): 工作表名称，不写默认第一个. Defaults to None.

        Returns:
            Worksheet: 工作表对象
        """
        if not sheetname:
            sheetname = self.file.ws_names[0]
        return self.file.ws(sheetname)

    @staticmethod
    def __convert(type_: str, value):
        """根据type转换value的数据类型，返回转换后的结果

        Args:
            type_ (str): 允许的数据类型有：str、int、float、json、list等
            value (str): 需要转换的值
        """
        converted = value
        if value == 'null':
            converted = None
        elif type_ in ('str', 'int', 'float'):
            if value != '':
                converted = eval(f'{type_}(value)')
        elif type_ == 'json':
            if value:
                converted = json.loads(value)
            else:
                converted = {}
        elif type_ in ('list', 'timerange'):
            if value != '':
                converted = str(value).split(',')
            else:
                converted = []
        elif type_ == 'list|int':
            if value != '':
                converted = [int(v) for v in str(value).split(',')]
            else:
                converted = []
        elif type_ == 'list|float':
            if value != '':
                converted = [float(v) for v in str(value).split(',')]
            else:
                converted = []
        elif type_ == 'time':
            if value:
                converted = value.replace('/', '-')
        elif type_ == 'date':
            if value:
                value = value.split(' ')[0]
                converted = value.replace('/', '-')
        return converted

    def __get_data(self,
                   return_type,
                   sheetname: str = None,
                   keyrow: int = 1,
                   begin: int = 2,
                   end: int = None) -> list:
        if return_type == 'dict' and not keyrow:
            raise ValueError('以字典形式返回数据时，必须要指定标题行keyrow')
        ws = self.__sheet(sheetname)
        result = []
        max_row = ws.maxrow
        if begin < 1:
            begin = 1
        if begin > max_row:
            begin = max_row
        if not end or end > max_row:
            end = max_row
        elif end < begin:
            end = begin
        if keyrow:
            if begin <= keyrow:
                begin = keyrow + 1
            titlelist = ws.row(keyrow)
            keylist = []
            typelist = []
            for t in titlelist:
                t = t.strip()
                if not t:
                    break
                key_type = t.split('|', 1)
                key = key_type[0]
                if len(key_type) == 2:
                    type_ = key_type[1]
                else:
                    type_ = 'str'
                keylist.append(key)
                typelist.append(type_)
        for r in range(begin, end + 1):
            valuelist = ws.row(r)
            if all(item == '' for item in valuelist):
                break
            try:
                if return_type == 'dict':
                    row_value = {}
                    for i, key in enumerate(keylist):
                        row_value[key] = self.__convert(
                            typelist[i], valuelist[i])
                elif keyrow:
                    row_value = [
                        self.__convert(typelist[i], valuelist[i])
                        for i in range(len(typelist))
                    ]
                else:
                    row_value = valuelist
                result.append(row_value)
            except Exception:
                raise ValueError(
                    f'工作表：{sheetname}，第{r}行数据有误，类型：{typelist[i]}，值：{valuelist[i]}'
                )
        return result

    def get_asdict(self,
                   sheetname: str = None,
                   keyrow: int = 1,
                   begin: int = 2,
                   end: int = None) -> list[dict]:
        """以字典列表的形式返回数据，字典的key为标题，要求每一列的第一个单元格不能为空。

        Args:
            sheetname (str, optional): 工作表名，不写默认第一个. Defaults to None.
            keyrow (int, optional): 标题行. Defaults to 1.
                标题中可以写明数据类型，以“|”间隔，获取数据时会自动转为对应类型，默认为str.
                允许的数据类型有：str、int、float、json、list、time、timerange,其中，list、timerange要求数据以英文逗号间隔，time要求数据为时间格式，获取时会
                自动转为%Y-%m-%d %H:%M:%S格式字符串。

                标题内容举例：

                    1. 标题1|json，表示该列数据类型为json字符串，获取数据时，该列数据将自动转为python object;
                    2. 比赛项目|list，单元格内容为：足球,篮球，获取该数据为：'比赛项目':['足球','篮球'];
            begin (int, optional): 数据开始行，行号从1开始。 Defaults to 2.
            end (int, optional): 数据结束行，行号从1开始。 Defaults to None. None时为最大行


        Returns:
            list: 一个列表，其中元素为字典
        """
        return self.__get_data('dict',
                               sheetname=sheetname,
                               keyrow=keyrow,
                               begin=begin,
                               end=end)

    def get_aslist(self,
                   sheetname: str = None,
                   keyrow: int = 1,
                   begin: int = 2,
                   end: int = None) -> list[list]:
        """以列表列表的形式返回数据，字典的key为标题，要求每一列的第一个单元格不能为空。

        Args:
            sheetname (str, optional): _工作表名，不写默认第一个. Defaults to None.
            keyrow (int, optional): 标题行. Defaults to 1.如果没有标题，则写None，数据不会处理格式。
                标题中可以写明数据类型，以“|”间隔，获取数据时会自动转为对应类型，默认为str.
                允许的数据类型有：str、int、float、json、list、time、timerange,其中，list、timerange要求数据以英文逗号间隔，time要求数据为时间格式，获取时会
                自动转为%Y-%m-%d %H:%M:%S格式字符串。

                标题内容举例：

                    1. 标题1|json，表示该列数据类型为json字符串，获取数据时，该列数据将自动转为python object;
                    2. 比赛项目|list，单元格内容为：足球,篮球，获取该数据为：['足球','篮球'];
            begin (int, optional): 数据开始行，行号从1开始。 Defaults to 2.
            end (int, optional): 数据结束行，行号从1开始。 Defaults to None. None时为最大行


        Returns:
            list: 一个列表，其中元素为列表
        """
        return self.__get_data('list',
                               sheetname=sheetname,
                               keyrow=keyrow,
                               begin=begin,
                               end=end)


class Redis:

    def __init__(self,
                 address: str = None,
                 sentinel_address: str = None,
                 master_name: str = None,
                 password: str = None,
                 db: int = 0):
        """初始化Redis连接,支持哨兵模式,使用client属性获取redis连接对象.

        Args:
            address (str, optional): ip:port, redis地址, 一般模式下必填. Defaults to None.
            sentinel_address (str, optional): ip1:port1,ip2:port2,ip3:port3,sentinel地址. Defaults to None.
            master_name (str, optional): master名称,sentinel模式下必填. Defaults to None.
            password (str, optional): 密码. Defaults to None.
            db (int, optional): db. Defaults to 0.
        """
        if not address and not sentinel_address:
            raise ValueError('address和sentinel_address不能同时为空')
        if address and sentinel_address:
            raise ValueError('address和sentinel_address不能同时存在')
        if sentinel_address and not master_name:
            raise ValueError('master_name在sentinel模式下必填')
        if address:
            if ':' not in address:
                host = address
                port = 6379
            else:
                host, port = address.split(':')
            self.client = redis.Redis(host=host,
                                      port=int(port),
                                      password=password,
                                      db=db,
                                      decode_responses=True)
        else:
            sentinel = Sentinel(
                [(ip, port) for ip, port in
                 [i.split(':') for i in sentinel_address.split(',')]],
                socket_timeout=5)
            self.client = sentinel.master_for(master_name,
                                              password=password,
                                              db=db,
                                              decode_responses=True)


DATA_COMPUTATION_REDIS = Redis(**DATA_COMPUTATION_REDIS_CONFIG)


def create_excel(
    worksheet: str,
    data: list | tuple,
    path: Path = Path(TMP_DIR, 'tmp123.xlsx')) -> Path:
    """生成单工作表excel文件

    Args:
        worksheet(str): 工作表名
        data(list | tuple): 数据，可迭代对象即可，每一项为行数据的迭代。例如((1, 2), (3, 4))，则第一行为1、2，第二行为3、4
        path(Path, optional): 想要生成Excel文件的Path. Defaults to Path(TMP_DIR, 'tmp123.xlsx').

    Returns:
        Path: Excel文件的Path对象
    """
    path.unlink(True)
    excel_data = xl.Database()
    excel_data.add_ws(worksheet)
    for row_id, row_data in enumerate(data, start=1):
        for col_id, v in enumerate(row_data, start=1):
            excel_data.ws(worksheet).update_index(row_id, col_id, v)
    xl.writexl(excel_data, path)
    return path


class MetaDict(TypedDict):
    '''返回分页结构'''
    totalElements: int
    totalPages: int


class ReviewResponse(TypedDict):
    warnList: list[str]
    data: dict


class ResponseDict(TypedDict):
    '''返回内容结构'''
    code: int
    message: str
    data: list | dict | None | ReviewResponse
    meta: NotRequired[MetaDict]


class CaseDict(TypedDict):
    """用例结构"""
    接口名: str
    路径: str
    测试内容: str
    处理数据: str
    请求方式: str
    是否登录: Literal['是', '否', '']
    用户名: NotRequired[str]
    密码: NotRequired[str]
    参数: dict
    预期: ResponseDict
    描述: NotRequired[str]
    内容类型: str
    跳过: NotRequired[str]
    HTTP_STATUS_CODE: NotRequired[int]


def api_test_data(filepath: str | Path) -> list[CaseDict]:
    """返回接口测试用例。

    Args:
            filepath(str, Path): 用例文件地址，模板见/data/template/接口测试用例.xlsx
    Returns:
            list: 一个CaseDict列表，每个元素为一条用例.
    """
    # 用例列表
    case_list = []
    test_data = Excel(filepath)
    # 接口列表
    api_list = test_data.get_asdict('接口路径')
    for a in api_list:
        # a接口用例列表读取数据
        try:
            tmplist = test_data.get_asdict(a['接口名'])
            try:
                paramlist = test_data.get_asdict(f"{a['接口名']}-参数")
            except UserWarning:
                paramlist = None
            try:
                expectlist = test_data.get_asdict(f"{a['接口名']}-预期")
            except UserWarning:
                expectlist = None
            # 整合用例
            for i, t in enumerate(tmplist):
                t.update(a)
                try:
                    t['参数'] = paramlist[i]
                except Exception:
                    pass
                try:
                    t['预期'] = expectlist[i]
                except Exception:
                    pass
        except Exception as e:
            tmplist = []
            print(f"{filepath}接口{a['接口名']}用例读取失败")
            raise e
        case_list += tmplist
    return case_list


DB_CONN = DB()


def set_occupation(key: str,
                   user: str,
                   value: str = None,
                   timeout_m: int = 20):
    """设置占用，最多20分钟

    Args:
        key(Str): 关键字
        user(Str): 占用用户
        value(Str): 值，设置占用内容
        timeout_m(int): 占用超时分钟，判断上一个占用已存在的时间，超过该分钟则认为上一个占用失效
    """
    print(f'设置占用，更新tmp_use表，增加{key}占用，用户为{user}，值为{value}')
    DB_CONN.execute(
        """CREATE TABLE IF NOT EXISTS `tmp_use`(`use_key`  VARCHAR(20) NOT NULL,
   `use_user` VARCHAR(20),
   `use_value` VARCHAR(40),
   `use_date` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
   PRIMARY KEY(`use_key`)
)COMMENT = '临时使用'""")
    while DB_CONN.get_one(
            """select use_date
                                from tmp_use
                                where use_key = %s
                                and use_user != %s
                                and TIMESTAMPDIFF(MINUTE, use_date, NOW()) < %s""",
        [key, user, timeout_m]):
        print(f'{key}操作被占用，10秒后重新查询，或到tmp_use表中将{key}对应的use_user设为NULL')
        time.sleep(10)

    DB_CONN.replace_into('tmp_use', {
        'use_key': key,
        'use_user': user,
        'use_value': value
    })


def clear_occupation(key: str | list | tuple):
    """清除占用

    Args:
        key(str, list, tuple): 关键字或关键字列表
    """
    DB_CONN.delete('tmp_use', {'use_key': key})


def clear_table_bak(table_list: list | Literal['__all__'], exclude: list = []):
    """清空以_bak结尾的备份表，只能在整个测试运行之前执行

    Args:
        table_list(list, str): 要删除的表列表，必须以_bak结尾，'__all__'表示所有.
        exclude(list, optional): 排除表名列表. Defaults to[].
    """
    print(f'删除备份表{table_list}{f"，排除{exclude}" if exclude else ""}')
    if table_list != '__all__':
        if (not isinstance(table_list, list)) or len(table_list) == 0:
            raise TypeError('table_list要求类型为非空list')
        table_bak_list = set(table_list)
    else:
        table_bak_list = set(
            [v[0] for v in DB_CONN.get_aslist("show tables like '%_bak'")])

    table_bak_list -= set(exclude)
    if table_bak_list:
        DB_CONN.execute(f"drop table IF EXISTS {','.join(table_bak_list)}")


def clear_table_snapshot():
    """清空以__snapshot结尾的表，只能在整个测试运行之前执行"""
    print('删除快照表')
    table_list = [
        v[0] for v in DB_CONN.get_aslist("show tables like '%__snapshot'")
    ]
    # 排除业务快照表（nami_football_standing_snapshot 等），避免被误删
    _SKIP_TABLES = {'nami_football_standing_snapshot','beitai_football_standing_snapshot'}
    table_list = [t for t in table_list if t not in _SKIP_TABLES]
    if table_list:
        DB_CONN.execute(f"drop table IF EXISTS {','.join(table_list)}")


class JsonEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, (Path, datetime, set)):
            return str(obj)
        elif isinstance(obj, Decimal):
            return f"Decimal('{obj}')"
        try:
            return json.JSONEncoder.default(self, obj)
        except:
            return str(obj)


def json_dumps(obj: list | dict,
               ensure_ascii=False,
               indent=2,
               cls=JsonEncoder):
    """json序列化"""
    return json.dumps(obj,
                      ensure_ascii=ensure_ascii,
                      indent=indent,
                      cls=cls,
                      skipkeys=True)


def _compare_equal_list(equal_list: list | tuple, index=0):
    try:
        diff_list = diff(equal_list[index][0], equal_list[index][1])
        if diff_list != []:
            raise AssertionError(f'''{equal_list[index][2]}数据错误：
与预期差异，prev为预期值：
{json_dumps(diff_list)}
实际结果为：
{json_dumps(equal_list[index][1])}''')
    finally:
        index += 1
        if index < len(equal_list):
            _compare_equal_list(equal_list, index)


def _compare_not_equal_list(not_equal_list: list | tuple, index=0):
    try:
        assert not_equal_list[index][0] != not_equal_list[index][
            1], f'{not_equal_list[index][2]}数据错误：两值相同,{not_equal_list[index][0]}'
    finally:
        index += 1
        if index < len(not_equal_list):
            _compare_not_equal_list(not_equal_list, index)


def compare_result(equal_list: list | tuple = None,
                   not_equal_list: list | tuple = None):
    """比较equal_list中所有数据对是否一致, not_equal_list中所有数据是否不一致，列表中字典的key必须为str类型

    Args:
        equal_list(list | tuple, optional): 一个预期一致的列表，每个子项为一个列表，包含预期、实际、比较内容。例：[[预期1, 实际1, 比较内容1], [预期2, 实际2, 比较内容2], ……]. Defaults to None.
        not_equal_list(list | tuple, optional): 一个预期不一致的列表，每个子项为一个列表，包含预期、实际、比较内容。例：[[预期1, 实际1, 比较内容1], [预期2, 实际2, 比较内容2], ……]. Defaults to None.
    """
    try:
        if equal_list:
            _compare_equal_list(equal_list)
    finally:
        if not_equal_list:
            _compare_not_equal_list(not_equal_list)
            
def are_times_equal(time_str1, time_str2, format_str="%H:%M:%S"):
    try:
        time1 = datetime.strptime(time_str1, format_str)
        time2 = datetime.strptime(time_str2, format_str)
        return time1 == time2
    except ValueError:
        # 如果格式不正确，可以抛出异常或者返回False
        return False

def timestrf(dt: datetime, format='%Y-%m-%d %H:%M:%S') -> str:
    """调整时间格式

    Args:
        dt (datetime): 日期时间
        format: 日期时间格式
    Returns:
        str: format格式字符串
    """
    try:
        result = dt.strftime(format)
    except Exception:
        result = dt
    return result

def compare_json_dicts(dict1, dict2):
    """调整字典排序

    Args:
        dict1: 字典1
        dict2: 字典2
    Returns:
        list: 数组格式
    """
    data=[]
    # 将字典的键排序
    for index,i in enumerate(dict1):
        sorted_dict1 = {k: dict1[index][k] for k in sorted(dict1[index])}
        sorted_dict2 = {k: dict2[index][k] for k in sorted(dict2[index])}
        if sorted_dict1 != sorted_dict2:
            data.append(i)
    return data
    

if __name__ == '__main__':
    pass
