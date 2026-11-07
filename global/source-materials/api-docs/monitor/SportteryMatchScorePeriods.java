package com.league.client.sporttery.monitor;

/** 篮球各节比分；足球的 periods 固定为 null。 */
public record SportteryMatchScorePeriods(
        String part1,
        String part2,
        String part3,
        String part4) {
}
