package com.jiheng.dto.auth;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * 图形验证码响应
 *
 * @author jiheng
 */
@Data
@AllArgsConstructor
public class CaptchaResponse {

    private String captchaId;
    private String captchaImage;
}