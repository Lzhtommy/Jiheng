package com.jiheng.service.auth;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.dto.auth.LoginResponse;
import com.jiheng.entity.UserEntity;
import com.jiheng.exception.AuthException;
import com.jiheng.repository.UserMapper;
import com.jiheng.util.HashidsUtil;
import com.jiheng.util.JwtUtil;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 鉴权业务服务：黑客松阶段固定使用默认账号，只签发 JWT，不维护服务端会话
 *
 * @author jiheng
 */
@Service
public class AuthService {

    private static final long EXPIRES_IN_SECONDS = 7 * 24 * 60 * 60L;

    private final UserMapper userMapper;
    private final JwtUtil jwtUtil;
    private final HashidsUtil hashidsUtil;
    private final String defaultPhone;

    public AuthService(UserMapper userMapper, JwtUtil jwtUtil, HashidsUtil hashidsUtil,
                       @Value("${app.default-phone}") String defaultPhone) {
        this.userMapper = userMapper;
        this.jwtUtil = jwtUtil;
        this.hashidsUtil = hashidsUtil;
        this.defaultPhone = defaultPhone;
    }

    public LoginResponse login(String ip) {
        UserEntity user = userMapper.selectOne(
                new LambdaQueryWrapper<UserEntity>().eq(UserEntity::getPhone, defaultPhone));
        if (user == null) {
            user = new UserEntity();
            user.setPhone(defaultPhone);
            user.setDisplayName("测试用户");
            user.setPlan("basic");
            user.setStatus("verified");
            userMapper.insert(user);
        }

        user.setLastLoginAt(LocalDateTime.now());
        user.setLastLoginIp(ip);
        userMapper.updateById(user);

        return issueTokens(user.getId());
    }

    public LoginResponse refresh(String refreshToken) {
        if (jwtUtil.isExpired(refreshToken)) {
            throw new AuthException("AUTH_REFRESH_EXPIRED", "refresh_token 已过期");
        }
        if (!"refresh".equals(jwtUtil.extractType(refreshToken))) {
            throw new AuthException("AUTH_TOKEN_INVALID", "令牌类型错误");
        }
        return issueTokens(jwtUtil.extractUserId(refreshToken));
    }

    private LoginResponse issueTokens(Long userId) {
        String jti = UUID.randomUUID().toString();
        String accessToken = jwtUtil.generateAccessToken(userId, jti);
        String refreshToken = jwtUtil.generateRefreshToken(userId, jti);
        return new LoginResponse(accessToken, refreshToken, hashidsUtil.encode(userId), EXPIRES_IN_SECONDS);
    }
}
