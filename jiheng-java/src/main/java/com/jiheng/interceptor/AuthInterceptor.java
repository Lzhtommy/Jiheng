package com.jiheng.interceptor;

import com.jiheng.exception.AuthException;
import com.jiheng.util.JwtUtil;
import com.jiheng.util.TraceContext;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.cors.CorsUtils;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * 认证拦截器：仅校验 JWT 签名、有效期与令牌类型
 *
 * @author jiheng
 */
@Component
public class AuthInterceptor implements HandlerInterceptor {

    private static final String AUTH_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

    private final JwtUtil jwtUtil;
    private final TraceContext traceContext;

    public AuthInterceptor(JwtUtil jwtUtil, TraceContext traceContext) {
        this.jwtUtil = jwtUtil;
        this.traceContext = traceContext;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        if (CorsUtils.isPreFlightRequest(request)) {
            return true;
        }

        String authHeader = request.getHeader(AUTH_HEADER);
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            throw new AuthException("AUTH_TOKEN_MISSING", "缺少认证令牌");
        }

        Claims claims;
        try {
            claims = jwtUtil.parse(authHeader.substring(BEARER_PREFIX.length()));
        } catch (ExpiredJwtException e) {
            throw new AuthException("AUTH_TOKEN_EXPIRED", "认证令牌已过期");
        } catch (JwtException | IllegalArgumentException e) {
            throw new AuthException("AUTH_TOKEN_INVALID", "认证令牌无效");
        }
        if (!"access".equals(claims.get("type", String.class))) {
            throw new AuthException("AUTH_TOKEN_INVALID", "令牌类型错误");
        }

        traceContext.setUserId(claims.get("user_id", Long.class));
        return true;
    }
}
