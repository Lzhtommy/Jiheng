package com.jiheng;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

import java.util.TimeZone;

/**
 * 玑衡AI Java 业务服务启动类
 *
 * @author jiheng
 */
@SpringBootApplication
@MapperScan("com.jiheng.repository")
@EnableScheduling
@EnableAsync
public class JihengApplication {

    public static void main(String[] args) {
        // 表里是不带时区的 TIMESTAMP，JVM 与数据库会话必须同为北京时间，否则代码写入和列默认值会差 8 小时
        TimeZone.setDefault(TimeZone.getTimeZone("Asia/Shanghai"));
        SpringApplication.run(JihengApplication.class, args);
    }
}