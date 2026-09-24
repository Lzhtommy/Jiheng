package com.jiheng.dto.skill;

import lombok.Data;

/**
 * 技能 DTO
 *
 * @author jiheng
 */
@Data
public class SkillDto {

    private Long id;
    private String name;
    private String description;
    private String kind;
    private Boolean enabled;
    private Integer runCount;
    private String lastEditedAt;
}