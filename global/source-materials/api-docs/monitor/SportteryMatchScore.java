package com.league.client.sporttery.monitor;

/** 比分视图；没有任何有效比分时由列表项将整个对象置为 null。 */
public record SportteryMatchScore(
        /** 足球半场比分；篮球固定为 null。 */
        String half,
        /** 全场比分，格式为“主队:客队”。 */
        String full,
        SportteryMatchScorePeriods periods,
        /** 比分来源：SPORTTERY 为竞彩官方赛果，S_MATCH 为标准化采集比分。 */
        String source) {
}
