package com.jiheng.exception;

import lombok.Getter;

/**
 * 业务异常基类
 *
 * @author jiheng
 */
@Getter
public class BizException extends RuntimeException {

    private final String code;

    public BizException(String code, String message) {
        super(message);
        this.code = code;
    }

    public BizException(String code, String message, Throwable cause) {
        super(message, cause);
        this.code = code;
    }
}