package com.jiheng.dto.skill;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 技能开关请求
 *
 * @author jiheng
 */
@Data
public class SkillToggleRequest {

    @NotNull(message = "enabled 不能为空")
    private Boolean enabled;
}