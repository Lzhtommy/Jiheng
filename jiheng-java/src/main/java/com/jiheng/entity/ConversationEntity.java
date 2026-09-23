package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 会话实体（conversation 表，Python 回写，用于报告关联）
 *
 * @author jiheng
 */
@Data
@TableName("conversation")
public class ConversationEntity {

    @TableId
    private Long id;

    private String conversationId;

    private String conversationUuid;

    private Long userId;

    private String agentId;

    private String title;

    private String status;

    private String mode;

    private String expert;

    private LocalDateTime deletedAt;

    private Long serverId;

    private LocalDateTime syncedAt;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}