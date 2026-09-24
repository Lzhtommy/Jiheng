package com.jiheng.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * 安全配置：Service Token + 内网接口白名单
 *
 * @author jiheng
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "security")
public class SecurityConfig {

    private String serviceToken;

    private List<String> internalWhitelist;
}