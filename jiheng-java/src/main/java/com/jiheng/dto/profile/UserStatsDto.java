package com.jiheng.dto.profile;

import lombok.Data;

/**
 * 用户统计 DTO
 *
 * @author jiheng
 */
@Data
public class UserStatsDto {

    private Long reportCount;
    private Long skillCount;
    private Long usageDays;
}