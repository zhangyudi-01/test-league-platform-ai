# 球队智能推荐查询接口分析

## 分析范围与来源

**目标 operation**：`GET /relations/team/recommendations`，operationId `recommend`。只分析球队智能推荐查询接口；第13轮需求中的页面查询、切换标签、勾选、匹配保存及返回操作不属于本接口行为。

| 来源 | 本次用途 | 版本/状态 |
|---|---|---|
| `球队智能推荐需求-第10轮迭代.md` | 初始推荐规则及原“最近10场”算法 | 旧基线 |
| `球队智能推荐需求-第13轮迭代.md` | 最新需求文本及算法变更 | 当前需求 |
| `球队智能推荐第13轮需求适配方案.md` | 第13轮业务口径、确认记录和测试边界 | 文件记载为已确认，作为当前业务依据 |
| `球队智能推荐查询.openapi.json` | HTTP operation、参数、响应字段和错误描述 | 算法描述与第13轮口径不一致 |
| `球队智能推荐接口查询SQL.sql` | 现有数据路径、字段映射和响应 oracle 结构 | 旧版“全局最近10场” |
| `test_team_smart_recommendation_get.py` | 当前测试脚本、预期 SQL 和测试处理函数 | 实现/测试现状，非第13轮需求预期 |

本接口目录没有提供相关表的 DDL/完整数据库设计；这里只确认 SQL 和测试代码实际使用的字段及关联，不推断未展示的数据库约束。OpenAPI 的 Cookie 示例含会话凭据和用户标识；分析只保留认证字段名，不复制其值。

## 接口调用与契约

- **请求**：GET 查询参数 `teamId`、`currentDataSource`；OpenAPI 标记二者 `required=false`，同时错误描述列出 `teamId不能为空` 和 `当前数据源不存在`。因此 required 标记不能视为业务接受缺参。Cookie 参数为可选请求头；具体登录由现有 DataBff client 负责。
- **数据源方向**：`currentDataSource=1` 表示目标 B 源为纳米、反向基准 A 源为贝泰；`currentDataSource=3` 表示目标 B 源为贝泰、反向基准 A 源为纳米。
- **source 2**：OpenAPI 明确规定 `currentDataSource=2` 时成功返回空列表；“当前数据源不存在”错误用于其他非法值。
- **错误码**：缺少 `teamId`、非法数据源、球队不存在记录为 code 2；服务异常为 code 31。文档未规定每类错误的精确 message，不把 message 文案写成确定预期。
- **成功响应**：`CommonResult` 包含 `code`、`message`、`data`；成功约定 `code=0`、`message=OK`。`data` 是候选数组，元素字段为 `sourceType`、`sourceTeamId`、`teamNameZh`、`teamShortNameZh`、`teamNameEn`、`recommendCount`、`matchStatus`、`checkStatus`、`manualTeamId`。无候选时按业务口径返回成功空数组 `[]`。
- **字段语义**：`sourceType` 为目标 B 源；只返回最高推荐次数的并列候选；已匹配候选保留并标记状态，不从候选中排除。现有 SQL 中匹配关系映射为 `matchStatus=1/checkStatus=0/manualTeamId=<id>`，未匹配映射为 `0/1/null`。OpenAPI 没有将 `manualTeamId` 标为 nullable，是 schema 完整性缺口。
- **名称与排序**：纳米名称来自其球队表；贝泰全称和简称均取 `team_name`，英文名取 `team_name_en`。需求承诺按简称正序。现有 SQL 还对同简称按源球队 ID 排序，但第13轮确认未定义此并列顺序；测试数据应避开同简称，不把次级规则写成产品要求。
- **副作用**：本接口定位为查询。现有脚本含请求前后关系记录比较，但未读取生产实现；此处只记录测试/SQL预期体现只读，不把它当作实现证明。

## 已确认业务规则

1. 先确定目标 B 源和反向 A 源；汇总数据中心球队在 A 源关联的全部源球队。
2. A 源参考比赛只从对应足球 `r_basic_data` 映射行中选择 `source_season_id IS NOT NULL` 的源赛季。该非空规则表示赛季已匹配；`relation_status` 不参与资格判断，`source_competition_id` 不增加赛季限制。A 赛季资格必须先于时间窗口筛选。
3. A 源全部关联球队的合格比赛合并后，按一个数据库当前时刻分别选取过去侧有效开赛时间 `<= NOW()`、时间倒序最近5场；未来侧有效开赛时间 `> NOW()`、时间正序最近5场。两侧分别最多5场，不互相补位，最多合计10场。所有 A 源球队是全局5+5，不是每队各取5+5。
4. 贝泰有效时间为 `COALESCE(resumetime, match_gtm8_time)`；纳米 Unix 秒时间用 `FROM_UNIXTIME(match_time)`，按数据库会话时区约定比较。两源精确到秒。
5. 对选中的 A 源比赛，以人工赛季桥接至 B 源对应足球赛季，匹配同一有效开赛时间、同一人工赛季的 B 源比赛；按 A 源球队当时主/客角色抽取 B 源同侧球队并累计。
6. 只返回最高计数的全部并列候选，按简称正序。空简称次序、同简称源球队 ID 次级排序若未被需求/用户确认，不提升为业务口径。
7. 比赛状态不作为 A 源比赛资格；选中但无 B 源同时间/赛季候选的 A 场次仍占窗口名额，不由窗口外比赛补位。

以上第13轮时间窗口和赛季资格来自需求适配方案中的确认记录；第10轮“最近10场”已被替换。

## 数据路径与数据库行为

1. 请求参数进入 `Request_Context`：`teamId` 定位人工球队，`currentDataSource` 决定 A/B 源方向；source 2 是成功空列表分支，其他非法值不进入候选计算。
2. `r_team_data` 以 `manual_team_id + source_type + sport_id=1` 取得人工球队的 A 源球队集合。
3. `r_basic_data` 以 `source_type + sport_id=1 + source_season_id IS NOT NULL` 识别 A 源已匹配赛季；源比赛的 `season_id` 与该映射行的 `source_season_id` 对应。按有效时间构造过去/未来两组窗口。
4. 选中 A 源场次通过 `manual_season_id` 找 B 源映射行，再依据 B 源 `season_id`、精确有效时间和 A 侧主客角色生成候选命中。
5. 候选命中按目标源球队计数，过滤到最高分并列；补充目标源球队名称及 `r_team_data` 匹配状态，按简称排序。
6. 当前 SQL 与脚本提供部分字段/表关系证据；旧版赛季过滤顺序、时间窗口和有效预期须在下游重算，不能直接作为第13轮 oracle。

潜在空结果包括：人工球队或 A 源关系不存在、没有已匹配 A 源赛季、没有有效 A 源比赛、选中场次没有符合时间/赛季/角色的 B 源比赛。查询结果应为空数组。

## 来源差异与实现观察

| 行为 | 最新需求/确认 | OpenAPI / SQL / 脚本现状 | 分析结论 |
|---|---|---|---|
| A 源场次选择 | 已匹配赛季内全局过去5+未来5 | OpenAPI、独立 SQL、`RECOMMENDATION_SQL` 仍为全局最近10；`BASE_MATCH_SQL` 与 `assert_recent_ten_matches()` 也按旧口径 | 旧描述/预期需要更新，不是新需求预期 |
| 赛季资格与过滤顺序 | A 源 `source_season_id` 非空；资格过滤先于时间窗口 | 旧推荐 SQL 先选 Top 10 再做赛季桥接 | 未匹配赛季可能占用窗口，属于旧实现/测试差异 |
| 当前时间和场次窗口 | 过去 `<= NOW()`、未来 `> NOW()`，分别取5 | 旧脚本使用固定/倒序 Top 10 | 需要动态时间数据；静态2036日期不能验证相对 NOW 的边界 |
| 响应协议 | 算法变化不改响应字段 | OpenAPI 未标 `manualTeamId` nullable；缺参参数标记与错误描述不完全一致 | schema 需补全/核对；不改变已确认算法 |

## 待确认问题

无阻断测试设计的业务问题。第13轮适配方案记录核心口径已确认。全局第5/6名有效时间并列的次级取舍未定义，适配方案明确建议测试数据避开，不构成本轮阻塞。

## 测试方案交接

**分析状态：ready**  
**测试方案就绪：是**  
**范围**：仅 `GET /relations/team/recommendations`；测试预期依据第13轮已确认的匹配赛季资格和 5+5 窗口。  
**主要风险**：赛季资格过滤顺序、两侧窗口不足/边界、跨 A 源球队全局取数、动态时区/有效时间、无 B 候选的窗口占位，以及候选计分/并列/字段/只读回归。  
**待更新旧现状**：OpenAPI 算法描述、`球队智能推荐接口查询SQL.sql` 和当前脚本仍写全局最近10场。  
**凭据保护**：Cookie 样例不复制；后续代码只使用测试仓库既有安全配置。

