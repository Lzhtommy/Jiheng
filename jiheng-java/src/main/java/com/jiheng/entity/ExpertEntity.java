package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 专家实体（expert 表）
 *
 * @author jiheng
 */
@Data
@TableName("expert")
public class ExpertEntity {

    @TableId
    private Long id;

    private String expertId;

    private String name;

    private String initial;

    private String avatarBg;

    private String description;

    private String systemPromptRef;

    private String toolset;

    private Integer sortOrder;

    private Integer configVersion;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}