package com.jiheng.exception;

/**
 * 权限/守卫异常
 *
 * @author jiheng
 */
public class GuardException extends BizException {

    public GuardException(String code, String message) {
        super(code, message);
    }
}