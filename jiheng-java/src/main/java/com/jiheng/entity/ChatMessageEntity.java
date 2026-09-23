package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 对话消息（chat_message 表）
 *
 * @author jiheng
 */
@Data
@TableName("chat_message")
public class ChatMessageEntity {

    @TableId
    private Long id;

    private String conversationId;

    private Long userId;

    private String role;

    private String content;

    private String mode;

    private String expert;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
