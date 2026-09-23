package com.jiheng.service.auth;

import cn.hutool.captcha.CaptchaUtil;
import cn.hutool.captcha.LineCaptcha;
import cn.hutool.core.util.IdUtil;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Base64;
import java.util.concurrent.ThreadLocalRandom;

/**
 * 验证码服务：图形验证码 + 短信验证码
 *
 * @author jiheng
 */
@Service
public class CaptchaService {

    private static final String CAPTCHA_KEY_PREFIX = "captcha:";
    private static final String SMS_KEY_PREFIX = "sms:";
    private static final Duration CAPTCHA_TTL = Duration.ofMinutes(5);
    private static final Duration SMS_TTL = Duration.ofMinutes(5);

    private final RedisTemplate<String, Object> redisTemplate;

    public CaptchaService(RedisTemplate<String, Object> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public String[] generateCaptcha() {
        String captchaId = IdUtil.simpleUUID();
        LineCaptcha captcha = CaptchaUtil.createLineCaptcha(120, 40, 4, 30);
        String code = captcha.getCode();
        redisTemplate.opsForValue().set(CAPTCHA_KEY_PREFIX + captchaId, code, CAPTCHA_TTL);

        byte[] imageBytes = captcha.getImageBytes();
        String base64Image = "data:image/png;base64," + Base64.getEncoder().encodeToString(imageBytes);
        return new String[]{captchaId, base64Image};
    }

    public boolean verifyCaptcha(String captchaId, String captchaCode) {
        Object stored = redisTemplate.opsForValue().get(CAPTCHA_KEY_PREFIX + captchaId);
        if (stored == null) {
            return false;
        }
        redisTemplate.delete(CAPTCHA_KEY_PREFIX + captchaId);
        return stored.toString().equalsIgnoreCase(captchaCode);
    }

    public String generateSmsCode(String phone) {
        String code = String.format("%06d", ThreadLocalRandom.current().nextInt(1_000_000));
        redisTemplate.opsForValue().set(SMS_KEY_PREFIX + phone, code, SMS_TTL);
        return code;
    }

    public boolean verifySmsCode(String phone, String smsCode) {
        Object stored = redisTemplate.opsForValue().get(SMS_KEY_PREFIX + phone);
        if (stored == null) {
            return false;
        }
        redisTemplate.delete(SMS_KEY_PREFIX + phone);
        return stored.toString().equals(smsCode);
    }
}
