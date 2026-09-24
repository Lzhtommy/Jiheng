package com.jiheng.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 玑衡 World 公司实体（world_company 表）：AI 生成的产业链关卡
 *
 * @author jiheng
 */
@Data
@TableName("world_company")
public class WorldCompanyEntity {

    @TableId
    private Long id;

    private Long userId;

    private String companyId;

    private String name;

    private String code;

    private String tag;

    private String kind;

    private String scenarioJson;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
