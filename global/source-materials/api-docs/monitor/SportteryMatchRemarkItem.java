package com.league.client.sporttery.monitor;

import java.time.LocalDateTime;

/** 竞彩赛程监控备注；account 始终来自记录创建人。 */
public record SportteryMatchRemarkItem(
        Integer remarkId,
        Integer sportId,
        /** 竞彩官方比赛 ID，需与 sportId 一起确定比赛。 */
        Long matchId,
        /** 备注创建账号；列表据此识别备注归属。 */
        String account,
        String remark,
        /** 是否属于当前登录用户；只有此项可由当前用户编辑。 */
        Boolean isCurrentUser,
        LocalDateTime createTime,
        LocalDateTime updateTime) {
}
