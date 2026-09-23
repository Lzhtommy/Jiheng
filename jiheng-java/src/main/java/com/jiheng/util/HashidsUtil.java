package com.jiheng.util;

import org.hashids.Hashids;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Hashids 工具类：ID 编码（不暴露自增 ID）
 *
 * @author jiheng
 */
@Component
public class HashidsUtil {

    private final Hashids hashids;

    public HashidsUtil(@Value("${app.hashids.salt:jiheng-salt}") String salt,
                       @Value("${app.hashids.min-length:8}") int minLength) {
        this.hashids = new Hashids(salt, minLength);
    }

    public String encode(Long id) {
        return hashids.encode(id);
    }

    public Long decode(String hash) {
        long[] ids = hashids.decode(hash);
        if (ids == null || ids.length == 0) {
            return null;
        }
        return ids[0];
    }
}