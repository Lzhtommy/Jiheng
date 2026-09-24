package com.jiheng.interceptor;

import com.jiheng.exception.AuthException;
import com.jiheng.util.JwtUtil;
import com.jiheng.util.TraceContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * 认证拦截器：JWT + Redis 会话存在性 + 用户状态
 *
 * @author jiheng
 */
@Component
public class AuthInterceptor implements HandlerInterceptor {

    private static final String AUTH_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";
    private static final String SESSION_KEY_PREFIX = "session:";

    private final JwtUtil jwtUtil;
    private final TraceContext traceContext;
    private final RedisTemplate<String, Object> redisTemplate;

    public AuthInterceptor(JwtUtil jwtUtil, TraceContext traceContext,
                           RedisTemplate<String, Object> redisTemplate) {
        this.jwtUtil = jwtUtil;
        this.traceContext = traceContext;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String authHeader = request.getHeader(AUTH_HEADER);
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            throw new AuthException("AUTH_TOKEN_MISSING", "缺少认证令牌");
        }

        String token = authHeader.substring(BEARER_PREFIX.length());
        if (jwtUtil.isExpired(token)) {
            throw new AuthException("AUTH_TOKEN_EXPIRED", "认证令牌已过期");
        }

        Long userId = jwtUtil.extractUserId(token);
        String jti = jwtUtil.extractJti(token);

        Boolean hasSession = redisTemplate.hasKey(SESSION_KEY_PREFIX + jti);
        if (Boolean.FALSE.equals(hasSession)) {
            throw new AuthException("AUTH_SESSION_INVALID", "会话已失效，请重新登录");
        }

        traceContext.setUserId(userId);
        return true;
    }
}