package com.jiheng.util;

import com.jiheng.config.JwtConfig;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

/**
 * JWT 工具类：签发/校验（HMAC-SHA256 对称密钥，与 Python 共享 JWT_SECRET）
 *
 * @author jiheng
 */
@Component
public class JwtUtil {

    private final JwtConfig jwtConfig;
    private final SecretKey key;

    public JwtUtil(JwtConfig jwtConfig) {
        this.jwtConfig = jwtConfig;
        this.key = Keys.hmacShaKeyFor(jwtConfig.getSecret().getBytes(StandardCharsets.UTF_8));
    }

    public String generateAccessToken(Long userId, String jti) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("user_id", userId);
        claims.put("type", "access");
        return buildToken(claims, jti, jwtConfig.getAccessTokenExpireDays() * 24 * 60 * 60 * 1000L);
    }

    public String generateRefreshToken(Long userId, String jti) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("user_id", userId);
        claims.put("type", "refresh");
        return buildToken(claims, jti, jwtConfig.getRefreshTokenExpireDays() * 24 * 60 * 60 * 1000L);
    }

    private String buildToken(Map<String, Object> claims, String jti, long expireMillis) {
        Date now = new Date();
        return Jwts.builder()
                .claims(claims)
                .id(jti)
                .issuer(jwtConfig.getIssuer())
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expireMillis))
                .signWith(key)
                .compact();
    }

    public Claims parse(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .requireIssuer(jwtConfig.getIssuer())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    public boolean isExpired(String token) {
        try {
            return parse(token).getExpiration().before(new Date());
        } catch (Exception e) {
            return true;
        }
    }

    public Long extractUserId(String token) {
        return parse(token).get("user_id", Long.class);
    }

    public String extractJti(String token) {
        return parse(token).getId();
    }

    public String extractType(String token) {
        return parse(token).get("type", String.class);
    }
}