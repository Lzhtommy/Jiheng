package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 埋点事件实体（event_log 表）
 *
 * @author jiheng
 */
@Data
@TableName("event_log")
public class EventEntity {

    @TableId
    private Long id;

    private Long userId;

    private String event;

    private LocalDateTime timestamp;

    private String props;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}