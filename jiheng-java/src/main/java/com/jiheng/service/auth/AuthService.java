package com.jiheng.service.auth;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.dto.auth.LoginRequest;
import com.jiheng.dto.auth.LoginResponse;
import com.jiheng.dto.auth.SmsRequest;
import com.jiheng.entity.UserEntity;
import com.jiheng.exception.AuthException;
import com.jiheng.exception.BizException;
import com.jiheng.repository.UserMapper;
import com.jiheng.util.HashidsUtil;
import com.jiheng.util.JwtUtil;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 鉴权业务服务
 *
 * @author jiheng
 */
@Service
public class AuthService {

    private final UserMapper userMapper;
    private final JwtUtil jwtUtil;
    private final HashidsUtil hashidsUtil;
    private final SessionService sessionService;
    private final CaptchaService captchaService;

    public AuthService(UserMapper userMapper, JwtUtil jwtUtil, HashidsUtil hashidsUtil,
                       SessionService sessionService, CaptchaService captchaService) {
        this.userMapper = userMapper;
        this.jwtUtil = jwtUtil;
        this.hashidsUtil = hashidsUtil;
        this.sessionService = sessionService;
        this.captchaService = captchaService;
    }

    public LoginResponse login(LoginRequest request, String ip) {
        if (!captchaService.verifyCaptcha(request.getCaptchaId(), request.getCaptchaCode())) {
            throw new BizException("AUTH_CAPTCHA_INVALID", "图形验证码无效");
        }
        if (!captchaService.verifySmsCode(request.getPhone(), request.getSmsCode())) {
            throw new BizException("AUTH_SMS_INVALID", "短信验证码无效");
        }

        UserEntity user = userMapper.selectOne(
                new LambdaQueryWrapper<UserEntity>().eq(UserEntity::getPhone, request.getPhone()));
        if (user == null) {
            throw new BizException("AUTH_USER_NOT_FOUND", "手机号或验证码不正确");
        }
        if ("locked".equals(user.getStatus())) {
            throw new AuthException("AUTH_USER_LOCKED", "用户已锁定");
        }
        if ("frozen".equals(user.getStatus())) {
            throw new AuthException("AUTH_USER_FROZEN", "用户已冻结");
        }

        String jti = UUID.randomUUID().toString();
        String accessToken = jwtUtil.generateAccessToken(user.getId(), jti);
        String refreshToken = jwtUtil.generateRefreshToken(user.getId(), jti);

        sessionService.create(jti, user.getId(), ip);

        user.setLastLoginAt(LocalDateTime.now());
        user.setLastLoginIp(ip);
        userMapper.updateById(user);

        String userId = hashidsUtil.encode(user.getId());
        return new LoginResponse(accessToken, refreshToken, userId, 7 * 24 * 60 * 60L);
    }

    public LoginResponse refresh(String refreshToken) {
        if (jwtUtil.isExpired(refreshToken)) {
            throw new AuthException("AUTH_REFRESH_EXPIRED", "refresh_token 已过期");
        }
        if (!"refresh".equals(jwtUtil.extractType(refreshToken))) {
            throw new AuthException("AUTH_TOKEN_INVALID", "令牌类型错误");
        }

        Long userId = jwtUtil.extractUserId(refreshToken);
        String oldJti = jwtUtil.extractJti(refreshToken);
        if (!sessionService.exists(oldJti)) {
            throw new AuthException("AUTH_SESSION_INVALID", "会话已失效");
        }

        String newJti = UUID.randomUUID().toString();
        String newAccessToken = jwtUtil.generateAccessToken(userId, newJti);
        String newRefreshToken = jwtUtil.generateRefreshToken(userId, newJti);

        sessionService.delete(oldJti);
        sessionService.create(newJti, userId, null);

        String encodedUserId = hashidsUtil.encode(userId);
        return new LoginResponse(newAccessToken, newRefreshToken, encodedUserId, 7 * 24 * 60 * 60L);
    }

    public void logout(String accessToken) {
        String jti = jwtUtil.extractJti(accessToken);
        sessionService.delete(jti);
    }

    public void sendSms(SmsRequest request) {
        if (!captchaService.verifyCaptcha(request.getCaptchaId(), request.getCaptchaCode())) {
            throw new BizException("AUTH_CAPTCHA_INVALID", "图形验证码无效");
        }
        String code = captchaService.generateSmsCode(request.getPhone());
        // TODO: 接入短信网关发送验证码，此处仅生成存储
    }
}