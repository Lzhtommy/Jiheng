package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 通知实体（notification 表）
 *
 * @author jiheng
 */
@Data
@TableName("notification")
public class NotificationEntity {

    @TableId
    private Long id;

    private String notificationId;

    private Long userId;

    private String type;

    private String title;

    private String content;

    private Boolean isRead;

    private String taskId;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}