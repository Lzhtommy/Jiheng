package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 技能实体（skill 表）
 *
 * @author jiheng
 */
@Data
@TableName("skill")
public class SkillEntity {

    @TableId
    private Long id;

    private String name;

    private String description;

    private String kind;

    private String promptTemplate;

    private String toolset;

    private Integer sortOrder;

    private Integer runCount;

    private Long creatorId;

    private LocalDateTime lastEditedAt;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}