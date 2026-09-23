package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 导出任务实体（export_task 表）
 *
 * @author jiheng
 */
@Data
@TableName("export_task")
public class ExportTaskEntity {

    @TableId
    private Long id;

    private String taskId;

    private Long reportId;

    private Long userId;

    private String format;

    private String status;

    private String filePath;

    private String errorMessage;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    private LocalDateTime completedAt;
}