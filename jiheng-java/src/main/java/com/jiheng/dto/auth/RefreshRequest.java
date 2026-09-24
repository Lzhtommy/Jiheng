package com.jiheng.dto.auth;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * Token 刷新请求
 *
 * @author jiheng
 */
@Data
public class RefreshRequest {

    @NotBlank(message = "refresh_token 不能为空")
    private String refreshToken;
}