package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 报告实体（report 表）
 *
 * @author jiheng
 */
@Data
@TableName("report")
public class ReportEntity {

    @TableId
    private Long id;

    private String reportId;

    private Long userId;

    private String kind;

    private String title;

    private String summary;

    private String content;

    private String state;

    private Integer pages;

    private Integer refCount;

    private String refs;

    private String sourceConversationId;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}