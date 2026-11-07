package com.league.client.sporttery.monitor;

import lombok.Data;

@Data
public class SportteryMatchLiveRequest {

    /**
     * 运动项目
     */
    private Integer sportId;

    /**
     * 竞彩比赛id
     */
    private Long sportteryMatchId;

    /** 可选；传入时必须与竞彩比赛关联的 s_match ID 一致。 */
    private Integer matchId;
}
