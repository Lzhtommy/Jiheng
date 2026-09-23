package com.jiheng.interceptor;

import com.jiheng.config.SecurityConfig;
import com.jiheng.exception.AuthException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * 服务间 Token 拦截器（/internal/* 接口认证）
 *
 * @author jiheng
 */
@Component
public class InternalTokenInterceptor implements HandlerInterceptor {

    private static final String SERVICE_TOKEN_HEADER = "X-Service-Token";

    private final SecurityConfig securityConfig;

    public InternalTokenInterceptor(SecurityConfig securityConfig) {
        this.securityConfig = securityConfig;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String token = request.getHeader(SERVICE_TOKEN_HEADER);
        if (token == null || !token.equals(securityConfig.getServiceToken())) {
            throw new AuthException("INTERNAL_TOKEN_INVALID", "服务间认证失败");
        }
        return true;
    }
}