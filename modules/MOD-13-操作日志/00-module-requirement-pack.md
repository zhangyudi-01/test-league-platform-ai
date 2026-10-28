## 操作日志（13）

*   **PBL 索引**
    
    ✅PBL-639，13轮操作日志与系统权限扩展✅
    
*   **原型**
    

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/8oLl9aEkb5pylapY/img/46aba095-41bc-4a46-abd9-11ca1cbed5cb.png)

*   **查询条件规则**
    
    1.  操作类型逻辑同V2系统：
        
        1.  风险管理中的二级选项需要展示为球队移除/添加、赛事移除/添加；
            
    2.  操作角色：选项内容为本系统的全部角色；
        
    3.  操作账号：输入框精确查询；
        
    4.  操作时间：精确值秒；点击“重置”按钮，则将查询条件重置为默认值，不刷新查询结果；
        

*   **列表规则**
    
    1.  列表展示内容包括：操作模块、操作类型、操作结果、操作用户、操作时间、操作账号、操作角色；
        
    2.  列表默认按照操作时间的降序排序；
        
    3.  操作用户为进行该操作的账号
        
    4.  操作时间为执行完成该操作的时间，精确到年月日时分秒
        
    5.  操作结果由成功或失败组成（登录失败不记录、若是没有输入正确的账号密码导致绑定失败不记录）
        
    6.  操作账号为进行该操作的账号
        
    7.  操作角色为展示角色名称（被删除或被修改过的角色，操作记录也能够展示）
        
    8.  列表设置分页器；
        

*   **已实现操作日志**
    

| **模块** | **操作类型** | **操作说明** | **对应接口** |
| --- | --- | --- | --- |
| 登录 | 登录 | 登录成功时记录 | POST /login |
| 登出 | 登出 | 登出成功时记录 | POST /logout |
| 账号管理 | 新建 | 新建账号弹窗下的创建 | POST /manager\_account |
| 账号管理 | 删除 | 删除二次确认弹窗下的确定 | DELETE /data-backend/manager\_account |
| 账号管理 | 修改 | 修改账号页面下的保存 | PATCH /data-backend/manager\_account |
| 账号管理 | 启用 | 启用弹窗下的确定 | PATCH /data-backend/manager\_account\_enable |
| 账号管理 | 停用 | 停用弹窗下的确定 | PATCH /manager\_account\_disable |
| 账号管理 | 重置密码 | 重置密码弹窗下的确定 | PATCH /data-backend/manager\_account\_password\_reset |
| 账号管理 | 主动修改密码 | 主动修改密码弹窗下的保存 | PUT /user/change\_password |
| 账号管理 | 强制修改密码 | 强制修改密码弹窗下的保存 | PUT /user/force\_change\_password |
| 角色管理 | 新建 | 新建角色页面下的创建 | POST /data-backend/role |
| 角色管理 | 删除 | 删除二次确认弹窗下的确定 | DELETE /data-backend/role |
| 角色管理 | 修改 | 修改角色页面下的保存 | PATCH /data-backend/role |
| 赛程批次管理 | 新建奖期 | 新建奖期 | POST /data-backend/bd-game-draw |
| 赛程批次管理 | 奖期编辑 | 奖期编辑 | PATCH /data-backend/bd-game-draw |
| 赛程批次管理 | 奖期删除 | 奖期删除 | DELETE /data-backend/bd-game-draw |
| 赛程批次管理 | 导出备注 | 导出备注 | GET /report/game\_draw\_remark/\* |
| 赛程批次管理 | 新建批次 | 新建批次 | POST /data-backend/bd-batch |
| 赛程批次管理 | 批次编辑 | 批次编辑 | PATCH /data-backend/bd-batch |
| 赛程批次管理 | 调整批次序号 | 调整批次序号 | PATCH /data-backend/bd-batch/batchNo |
| 赛程批次管理 | 草稿比对 | 草稿比对 | POST /batch-diff |
| 赛程批次管理 | 草稿添加比赛 | 草稿添加比赛 | PATCH /batch-matchup-drafts/real-time/add |
| 赛程批次管理 | 开奖时间草稿批次添加比赛 | 在开奖时间草稿配置中按照批次添加比赛 | PATCH /batch-matchup-drafts/real-time/batch/add |
| 赛程批次管理 | 草稿删除比赛 | 草稿删除比赛 | PATCH /batch-matchup-drafts/real-time/delete |
| 赛程批次管理 | 草稿手动调整比赛顺序 | 草稿手动调整比赛顺序 | PATCH /batch-matchup-drafts/real-time/manual-sort-no |
| 赛程批次管理 | 草稿手动调整场次号 | 用户手动调整不同游戏的场次号 | PATCH /batch-matchup-drafts/real-time/matchup-no |
| 赛程批次管理 | 草稿其他信息更新 | 用户更新草稿的其他信息 | PATCH /batch-matchup-drafts/real-time/batch-matchup-drafts |
| 赛程批次管理 | 草稿调整开售的游戏 | 用户手动调整比赛开售的游戏 | PATCH /batch-matchup-drafts/real-time/sales |
| 赛程批次管理 | 赛程变更 | 处理赛程变更赛程变更的操作（更新至草稿、不更新、删除） |  |
| 赛程批次管理 | 草稿比对保存草稿 | 草稿比对保存 | POST /batch-diff/user-matchup-drafts |
| 赛程批次管理 | 草稿比对生成正式版 | 草稿比对生成正式版 | POST /batch-diff/matchup-formal |
| 赛程批次管理 | 导出正式赛程 | 导出正式赛程 | GET /report/matchup/4 |
| 赛程批次管理 | 删除批次 | 删除批次 | DELETE /data-backend/bd-batch |
| 赛程批次管理 | 导出初版草稿 | 导出初版草稿 | GET /report/matchup\_draft/\* |
| 赛程批次管理 | 导出公告表 | 导出公告表 | GET /report/matchup\_notice/5 |
| 赛程批次管理 | 赛程备注 | 赛程备注 | POST /data-backend/m-match-remark |
| 赛程批次管理 | 草稿保存 | 草稿保存 | POST /batch-matchup-drafts |
| 赛程批次管理 | 导入胜负比赛 | 导入胜负比赛 | POST /upload/s-match/save |
| 赛程批次管理 | 创建比赛 | 创建比赛 |  |
| 赛程批次管理 | 转移赛程 | 转移赛程 | POST /batch-matchup-drafts/transfer |
| 赛程批次管理 | 导出正式赛程（赛事详情） | 导出正式赛程 | GET /report/matchup/\* |
| 赛程批次管理 | 正式赛程作废 | 正式赛程作废 | DELETE /data-backend/batch-matchup |
| 赛程批次管理 | 提交比赛文件 | 提交比赛文件 | POST /data-backend/match\_file\_submit |
| 赛程批次管理 | 提交赛事文件 | 提交赛事文件 | POST /data-backend/league\_file\_submit |
| 赛程批次管理 | 提交球队文件 | 提交球队文件 | POST /data-backend/team\_file\_submit |
| 风险管理 | 添加球队黑名单 | 添加球队黑名单 | POST /data-backend/m-team-blacklist |
| 风险管理 | 移除球队黑名单 | 移除球队黑名单 | DELETE /data-backend/m-team-blacklist |
| 风险管理 | 添加赛事黑名单 | 添加赛事黑名单 | POST /data-backend/m-competition-blacklist |
| 风险管理 | 移除赛事黑名单 | 移除赛事黑名单 | DELETE /data-backend/m-competition-blacklist |
| 基础信息管理 | 新建赛事 | 新建赛事 | POST /data-backend/m-competition |
| 基础信息管理 | 修改赛事 | 修改赛事 | PATCH /data-backend/m-competition |
| 基础信息管理 | 匹配赛事 | 匹配赛事 | POST /data-backend/dimension/relations/competition |
| 基础信息管理 | 新建赛季 | 新建赛季 | POST /data-backend/m-season |
| 基础信息管理 | 修改赛季 | 修改赛季 | PATCH /data-backend/m-season |
| 基础信息管理 | 匹配赛季 | 匹配赛季 | POST /data-backend/dimension/relations/season |
| 基础信息管理 | 关联球队 | 关联球队 | POST /data-backend/r-season-team |
| 基础信息管理 | 新建球队 | 新建球队 | POST /data-backend/m-team |
| 基础信息管理 | 修改球队 | 修改球队 | PATCH /data-backend/m-team |
| 基础信息管理 | 球队匹配 | 球队匹配 | POST /data-backend/dimension/relations/team |
| 基础信息管理 | 球队导入 | 球队导入 | POST /upload/m-team/save |
| ✅基础信息管理✅ | ✅竞彩赛事匹配✅ | ✅竞彩赛事匹配页的匹配按钮✅ |  |
| ✅基础信息管理✅ | ✅竞彩球队匹配✅ | ✅竞彩球队匹配页的匹配按钮✅ |  |
| 比赛数据维护 | 新建比赛 | 新建比赛 | POST /data-backend/m-match |
| 比赛监控 | 填写监控记录 | 填写监控记录 | POST /data-backend/monitor |
| 比赛监控 | 赛果审核 | 赛果审核 | POST /data-backend/event-match-check |
| 比赛监控 | 赛果确认 | 赛果比对确认 | POST /data-backend/event-match-check/match-result/diff |
| 比赛监控 | 赛果确认保存 | 赛果确认保存 | POST /data-backend/event-match-check/match-result/confirm |
| 比赛监控 | 批量确认 | 赛果批量确认保存 |  |
| 比赛监控 | 赛果回退 | 赛果回退 |  |
| ✅比赛监控✅ | ✅竞彩赛程备注✅ | ✅竞彩赛程监控页备注弹窗的保存按钮✅ |  |
| 异常管理 | 监控备注 | 监控备注 | POST /data-backend/monitor/remark |
| 异常管理 | 告警核实 | 告警核实 | POST /data-backend/event-match-check |
| 异常管理 | 异常确认 | 异常确认 | POST /data-backend/event-match-check/event/confirm |
| ✅异常管理✅ | ✅修改详情✅ | ✅告警管理页修改详情弹窗的保存按钮✅ |  |
| 变更管理 | 导出公告表 | 导出公告表 | POST /report/event\_notice\_export |
| 变更管理 | 导出变更单 | 导出变更单 | GET /report/change\_matchup/6 |
| 变更管理 | 新建处理 | 新建处理 | POST /data-backend/abnormal/record |
| 变更管理 | 处理作废 | 处理作废 | POST /data-backend/abnormal/voided |
| 变更管理 | 完成确认 | 完成确认 | POST /data-backend/abnormal/completed |
| 开奖管理 | 新建开奖批次 | 新建开奖批次 | POST /data-backend/bd-batch/draw |
| 开奖管理 | 编辑开奖批次 | 编辑开奖批次 | PATCH /data-backend/bd-batch/draw |
| 开奖管理 | 删除开奖批次 | 删除开奖批次 | DELETE /data-backend/bd-batch/draw |
| 开奖管理 | 导出赛果 | 导出赛果 | GET /report/matchup\_result/7 |
| 开奖管理 | 调整批次序号 | 调整批次序号 | PATCH /data-backend/bd-batch/draw/batch-order-no |
| 开奖管理 | 开奖批次添加赛程 | 开奖列表添加赛程 | PATCH /batch-matchup-draw/real-time/add |
| 开奖管理 | 开奖批次删除赛程 | 开奖列表删除赛程 | PATCH /batch-matchup-draw/real-time/delete |
| 开奖管理 | 开奖批次更改开奖游戏 | 赛程更改开奖的游戏 | PATCH /batch-matchup-draw/real-time/draw |
| 开奖管理 | 保存批次开奖 | 保存批次开奖 | POST /batch-matchup-draw |
| 开奖管理 | 开奖时间草稿保存 | 开奖时间草稿保存 | POST /batch-matchup-drafts |
| 开奖管理 | 开奖时间草稿比对保存 | 开奖时间草稿比对保存 | POST /batch-diff/user-matchup-drafts |
| 开奖管理 | 开奖时间草稿比对生成正式版 | 开奖时间草稿比对生成正式版 | POST /batch-diff/matchup-formal |
| 开奖管理 | 提交赛果文件 | 提交赛果文件 | POST /data-backend/match\_result\_file\_submit |
| 开奖管理 | 完成审核 | 赛果批次完成审核 |  |
| 开奖管理 | 取消审核 | 赛果批次手动取消审核 |  |

