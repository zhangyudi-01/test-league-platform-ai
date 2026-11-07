from pathlib import Path

import pytest

from common.data import DB_CONN, Excel
from settings import TEST_DATA_DIR


@pytest.fixture(scope='session', autouse=True)
def init_manager_data():
    """初始化球队数据

    注：m_team_blacklist 已有 137 条预加载数据，不调用 init_team_blacklist 重新加载
    （原 Excel 中的 zyy球队* 系列在 m_team 表中不存在，加载会 KeyError）。
    """
    # init_team()
    yield
    # del_team()


@pytest.fixture(scope='module')
def team_smart_recommendation_data():
    """插入并清理球队智能推荐查询的共享基础数据。"""
    excel = Excel(
        Path(TEST_DATA_DIR, 'init', '球队智能推荐查询基础数据.xlsx'))
    base_data = {
        sheet: excel.get_asdict(sheet, begin=3)
        for sheet in excel.file.ws_names
    }
    created_ids = {sheet: [] for sheet in base_data}
    original_time_zone = DB_CONN.get_one('SELECT @@session.time_zone')

    try:
        DB_CONN.execute("SET SESSION time_zone = '+08:00'")
        for sheet, rows in base_data.items():
            primary_key = next(iter(rows[0]))
            for row in rows:
                DB_CONN.insert(sheet, row)
                created_ids[sheet].append(row[primary_key])
        yield base_data
    finally:
        try:
            for sheet in reversed(base_data):
                ids = created_ids[sheet]
                if ids:
                    primary_key = next(iter(base_data[sheet][0]))
                    deleted = DB_CONN.delete(sheet, {primary_key: ids})
                    assert deleted == len(ids), (
                        f'{sheet} 清理数量错误，'
                        f'预期 {len(ids)}，实际 {deleted}')
        finally:
            DB_CONN.execute(
                'SET SESSION time_zone = %s', [original_time_zone])
