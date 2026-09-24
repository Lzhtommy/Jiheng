package com.jiheng.service.auth;

import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * Redis 会话管理服务
 *
 * @author jiheng
 */
@Service
public class SessionService {

    private static final String SESSION_KEY_PREFIX = "session:";
    private static final Duration SESSION_TTL = Duration.ofDays(7);

    private final RedisTemplate<String, Object> redisTemplate;

    public SessionService(RedisTemplate<String, Object> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void create(String jti, Long userId, String ip) {
        Map<String, Object> session = new HashMap<>();
        session.put("userId", userId);
        session.put("ip", ip);
        session.put("createdAt", System.currentTimeMillis());
        redisTemplate.opsForValue().set(SESSION_KEY_PREFIX + jti, session, SESSION_TTL);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> get(String jti) {
        Object value = redisTemplate.opsForValue().get(SESSION_KEY_PREFIX + jti);
        if (value instanceof Map) {
            return (Map<String, Object>) value;
        }
        return null;
    }

    public void renew(String jti) {
        redisTemplate.expire(SESSION_KEY_PREFIX + jti, SESSION_TTL);
    }

    public void delete(String jti) {
        redisTemplate.delete(SESSION_KEY_PREFIX + jti);
    }

    public boolean exists(String jti) {
        Boolean hasKey = redisTemplate.hasKey(SESSION_KEY_PREFIX + jti);
        return Boolean.TRUE.equals(hasKey);
    }
}