package com.jiheng.config;

import com.jiheng.interceptor.AuthInterceptor;
import com.jiheng.interceptor.InternalTokenInterceptor;
import com.jiheng.interceptor.TraceIdInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web MVC 配置：CORS + 拦截器注册
 *
 * @author jiheng
 */
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    private final TraceIdInterceptor traceIdInterceptor;
    private final AuthInterceptor authInterceptor;
    private final InternalTokenInterceptor internalTokenInterceptor;

    public WebMvcConfig(TraceIdInterceptor traceIdInterceptor,
                        AuthInterceptor authInterceptor,
                        InternalTokenInterceptor internalTokenInterceptor) {
        this.traceIdInterceptor = traceIdInterceptor;
        this.authInterceptor = authInterceptor;
        this.internalTokenInterceptor = internalTokenInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(traceIdInterceptor)
                .addPathPatterns("/**");

        registry.addInterceptor(internalTokenInterceptor)
                .addPathPatterns("/internal/**");

        registry.addInterceptor(authInterceptor)
                .addPathPatterns("/api/**")
                .excludePathPatterns(
                        "/api/v1/auth/login",
                        "/api/v1/auth/register",
                        "/api/v1/auth/captcha",
                        "/api/v1/auth/sms",
                        "/api/v1/auth/refresh",
                        "/api/v1/auth/logout"
                );
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }
}