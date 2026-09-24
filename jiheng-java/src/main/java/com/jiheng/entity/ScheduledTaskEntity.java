package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 定时任务实体（scheduled_task 表）
 *
 * @author jiheng
 */
@Data
@TableName("scheduled_task")
public class ScheduledTaskEntity {

    @TableId
    private Long id;

    private String taskId;

    private Long userId;

    private String type;

    private String cron;

    private String conditionExpr;

    private String payload;

    private LocalDateTime nextRunAt;

    private String lastResult;

    private LocalDateTime lastTriggerAt;

    private String status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}