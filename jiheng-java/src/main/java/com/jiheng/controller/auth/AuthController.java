package com.jiheng.controller.auth;

import com.jiheng.dto.ApiResponse;
import com.jiheng.dto.auth.CaptchaResponse;
import com.jiheng.dto.auth.LoginRequest;
import com.jiheng.dto.auth.LoginResponse;
import com.jiheng.dto.auth.RefreshRequest;
import com.jiheng.dto.auth.SmsRequest;
import com.jiheng.service.auth.AuthService;
import com.jiheng.service.auth.CaptchaService;
import com.jiheng.util.TraceContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 鉴权控制器
 *
 * @author jiheng
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final CaptchaService captchaService;
    private final TraceContext traceContext;

    public AuthController(AuthService authService, CaptchaService captchaService, TraceContext traceContext) {
        this.authService = authService;
        this.captchaService = captchaService;
        this.traceContext = traceContext;
    }

    @GetMapping("/captcha")
    public ApiResponse<CaptchaResponse> getCaptcha() {
        String[] captcha = captchaService.generateCaptcha();
        return ApiResponse.ok(new CaptchaResponse(captcha[0], captcha[1]));
    }

    @PostMapping("/sms")
    public ApiResponse<Void> sendSms(@Valid @RequestBody SmsRequest request) {
        authService.sendSms(request);
        return ApiResponse.ok(null);
    }

    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request,
                                             HttpServletRequest httpRequest) {
        String ip = getClientIp(httpRequest);
        return ApiResponse.ok(authService.login(request, ip));
    }

    @PostMapping("/refresh")
    public ApiResponse<LoginResponse> refresh(@Valid @RequestBody RefreshRequest request) {
        return ApiResponse.ok(authService.refresh(request.getRefreshToken()));
    }

    @PostMapping("/logout")
    public ApiResponse<Void> logout(HttpServletRequest httpRequest) {
        String authHeader = httpRequest.getHeader("Authorization");
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            authService.logout(authHeader.substring(7));
        }
        return ApiResponse.ok(null);
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isBlank()) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isBlank()) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }
}