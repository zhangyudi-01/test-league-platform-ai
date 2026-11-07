
import uuid

from common.account import get_totp_code
from common.api import API, ApiError
from common.data import DB_CONN
from settings import DATA_BFF_URL


class DataBff(API):
    base_url = f'{DATA_BFF_URL}/api'

    name = '管理端接口'
    username = None
    password = None

    def login(self, username='zhangyudi', password='Vegas2.0'):
        # username='dev1', password='f4sFS4%3'
        # username='test3', password='Vegas2.0'
        # username='wjycs', password='Vegas2.0'
        if self.username == username and self.password == password:
            self.check_login(username, password)
            return
        two_factor_bind_status, token_id = DB_CONN.get_first(
            """SELECT
            ta.two_factor_bind_status ,
            ta.token_id
        FROM
            toto_account ta
        WHERE
            ta.account = %s
            and ta.is_deleted = 0""", (username, ))
        if two_factor_bind_status == 0 or not token_id:
            token_id = uuid.uuid4().hex
            DB_CONN.update('toto_account', {
                'token_id': token_id,
                'two_factor_bind_status': 1
            }, {
                'account': username,
                'is_deleted': 0
            })
        code = get_totp_code(token_id)
        response = self.request('/login',
                                'POST',300, {
                                    "username": username,
                                    "password": password,
                                    'code': code
                                },
                                content_type='multipart/form-data').json()
        assert response[
            'code'] == 0, f'登录失败，用户名{username}，密码{password}，令牌{code}，返回内容：{response}'
        self.username = username
        self.password = password

    def logout(self):
        response = self.request('/logout', 'POST', {}).json()
        assert response['code'] == 0, '登出失败'
        self.username = None
        self.password = None

    def check_login(self, username, password):
        """检查接口是否登录，如果未登录，则登录

        Args:
            username (str): 用户名
            password (str): 密码
        """
        self.request('/operation/modules', 'GET', {})
        code = self.actual_result.get('code')
        if code == 1002:
            self.username = None
            self.password = None
            self.login(username, password)
        elif code != 0:
            self.username = None
            self.password = None
            raise ApiError(code, f'/operation/modules,{self.actual_result}')
