package com.jiheng.dto.profile;

import lombok.Data;

/**
 * 用户资料 DTO
 *
 * @author jiheng
 */
@Data
public class UserProfileDto {

    private String userId;
    private String phone;
    private String displayName;
    private String avatar;
    private String plan;
    private String department;
    private Integer points;
    private Boolean phoneBound;
    private String dataScopes;
    private String locale;
    private Boolean notifyOn;
    private UserStatsDto stats;
}