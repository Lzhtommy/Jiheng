package com.jiheng.util;

import org.slf4j.MDC;
import org.springframework.stereotype.Component;

/**
 * Trace 上下文工具：ThreadLocal + MDC trace_id
 *
 * @author jiheng
 */
@Component
public class TraceContext {

    private static final String TRACE_ID_KEY = "trace_id";
    private static final String USER_ID_KEY = "user_id";

    private static final ThreadLocal<String> TRACE_ID_HOLDER = new ThreadLocal<>();
    private static final ThreadLocal<Long> USER_ID_HOLDER = new ThreadLocal<>();

    public void setTraceId(String traceId) {
        TRACE_ID_HOLDER.set(traceId);
        MDC.put(TRACE_ID_KEY, traceId);
    }

    public String getTraceId() {
        return TRACE_ID_HOLDER.get();
    }

    public void setUserId(Long userId) {
        USER_ID_HOLDER.set(userId);
        MDC.put(USER_ID_KEY, userId != null ? String.valueOf(userId) : null);
    }

    public Long getUserId() {
        return USER_ID_HOLDER.get();
    }

    public void clear() {
        TRACE_ID_HOLDER.remove();
        USER_ID_HOLDER.remove();
        MDC.remove(TRACE_ID_KEY);
        MDC.remove(USER_ID_KEY);
    }
}