package com.jiheng;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

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
        SpringApplication.run(JihengApplication.class, args);
    }
}