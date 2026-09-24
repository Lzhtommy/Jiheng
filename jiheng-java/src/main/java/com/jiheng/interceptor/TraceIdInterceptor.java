package com.jiheng.interceptor;

import com.jiheng.util.TraceContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.UUID;

/**
 * TraceId 拦截器：生成 trace_id + 注入 MDC
 *
 * @author jiheng
 */
@Component
public class TraceIdInterceptor implements HandlerInterceptor {

    private final TraceContext traceContext;

    public TraceIdInterceptor(TraceContext traceContext) {
        this.traceContext = traceContext;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String traceId = request.getHeader("X-Trace-Id");
        if (traceId == null || traceId.isBlank()) {
            traceId = UUID.randomUUID().toString().replace("-", "");
        }
        traceContext.setTraceId(traceId);
        response.setHeader("X-Trace-Id", traceId);
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                Object handler, Exception ex) {
        traceContext.clear();
    }
}