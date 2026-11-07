package com.league.client.sporttery.monitor;

/** 保存当前用户监控备注的请求；账号和备注类型由服务端决定。 */
public record SportteryMatchRemarkRequest(
        /** 运动项目：1 为足球，2 为篮球。 */
        Integer sportId,
        /** 竞彩官方比赛 ID。 */
        Long matchId,
        /** 备注内容；账号与备注类型不由客户端指定。 */
        String remark) {
}
