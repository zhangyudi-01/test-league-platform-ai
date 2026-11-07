package com.league.client.sporttery.monitor;

import java.time.LocalDateTime;

/** 竞彩比赛事件弹窗所需的最小数据项。 */
public record SportteryMatchEventItem(
        /** 数据库中的 11 位事件主键，按原值返回以保留大小写。 */
        String eventId,
        /** 事件创建时间。 */
        LocalDateTime eventTime,
        /** 事件名称。 */
        String title,
        /** 事件原因详情。 */
        String exceptionDetail) {
}
