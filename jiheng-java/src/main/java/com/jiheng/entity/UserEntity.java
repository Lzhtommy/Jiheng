package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户实体（user_account 表）
 *
 * @author jiheng
 */
@Data
@TableName("user_account")
public class UserEntity {

    @TableId
    private Long id;

    private String phone;

    private String passwordHash;

    private String displayName;

    private String avatar;

    private String plan;

    private String department;

    private Integer points;

    private Boolean phoneBound;

    private String dataScopes;

    private String locale;

    private Boolean notifyOn;

    private String status;

    private LocalDateTime lastLoginAt;

    private String lastLoginIp;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @Version
    private Integer version;
}