package com.jiheng.service.auth;

import cn.hutool.captcha.CaptchaUtil;
import cn.hutool.captcha.LineCaptcha;
import cn.hutool.core.util.IdUtil;
import org.springframework.stereotype.Service;

import java.util.Base64;

/**
 * 验证码服务：仅生成图形验证码供登录页展示，不存储、不校验（黑客松默认账号登录）
 *
 * @author jiheng
 */
@Service
public class CaptchaService {

    public String[] generateCaptcha() {
        String captchaId = IdUtil.simpleUUID();
        LineCaptcha captcha = CaptchaUtil.createLineCaptcha(120, 40, 4, 30);
        byte[] imageBytes = captcha.getImageBytes();
        String base64Image = "data:image/png;base64," + Base64.getEncoder().encodeToString(imageBytes);
        return new String[]{captchaId, base64Image};
    }
}
