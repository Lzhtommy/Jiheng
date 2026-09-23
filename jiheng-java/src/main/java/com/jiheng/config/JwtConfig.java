package com.jiheng.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * JWT 配置：密钥 + 过期时间
 *
 * @author jiheng
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "jwt")
public class JwtConfig {

    private String secret;

    private long accessTokenExpireDays = 7;

    private long refreshTokenExpireDays = 30;

    private String issuer = "jiheng-ai";
}