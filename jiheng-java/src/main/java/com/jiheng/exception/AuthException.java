package com.jiheng.exception;

/**
 * 认证异常
 *
 * @author jiheng
 */
public class AuthException extends BizException {

    public AuthException(String code, String message) {
        super(code, message);
    }
}