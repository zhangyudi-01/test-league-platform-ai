package com.league.client.sporttery.monitor;

import com.league.client.dto.BeitaiFootballMatchLiveDTO;

import java.time.LocalDate;
import java.time.LocalDateTime;

/** 竞彩赛程监控列表项；比赛身份始终使用竞彩官方 matchId。 */
public record SportteryMatchMonitorItem(
        /** 运动项目：1 为足球，2 为篮球，也是事件、任务和备注的隔离键。 */
        Integer sportId,
        String sportName,
        LocalDate businessDate,
        /** 竞彩官方比赛 ID；事件、备注接口使用此 ID，而非 sMatchId。 */
        Long matchId,
        /** 关联的标准化比赛 ID；未匹配时为 null。 */
        Integer sMatchId,
        Integer beitaiMatchId,
        Integer namiMatchId,
        String matchNo,
        Long leagueId,
        String leagueName,
        LocalDateTime matchTime,
        Long homeTeamId,
        String homeTeamName,
        Long awayTeamId,
        String awayTeamName,
        /** 已按竞彩官方主客顺序调整的标准化排名；无关联或无排名时为 null。 */
        String homePosition,
        String awayPosition,
        /** 原始 s_match.status_id；未关联标准比赛时为 null，展示文案由调用方字典维护。 */
        Integer matchStatus,
        /** 按开奖状态和数据有效性选出的比分；没有有效比分时为 null。 */
        SportteryMatchScore score,
        /** 竞彩来源销售状态：1 在售、2 停售、3 已开奖。 */
        Integer sellStatus,
        /** 二值开奖状态：0 未开奖、1 已开奖；展示文案由调用方字典维护。 */
        Integer drawStatus,
        Integer eventCount,
        Integer remarkCount,
        /** 最新未解除事件对应的行颜色：NONE、RED、YELLOW、ORANGE 或 GREEN。 */
        String rowColor,
        /** 最新未解除任务在数据库中的原始任务类型。 */
        String taskType,
        /** 足球比赛中且存在贝泰直播数据时返回，否则为 null。 */
        BeitaiFootballMatchLiveDTO beitaiFootballMatchLiveDTO) {
}
