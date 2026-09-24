package com.jiheng.controller.notify;

import com.jiheng.dto.ApiResponse;
import com.jiheng.entity.NotificationEntity;
import com.jiheng.service.notify.NotifyService;
import com.jiheng.util.TraceContext;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/notifications")
public class NotifyController {
    private final NotifyService notifyService;
    private final TraceContext traceContext;

    public NotifyController(NotifyService notifyService, TraceContext traceContext) {
        this.notifyService = notifyService;
        this.traceContext = traceContext;
    }

    @GetMapping
    public ApiResponse<List<NotificationEntity>> list() {
        return ApiResponse.ok(notifyService.list(traceContext.getUserId()));
    }

    @PutMapping("/{id}/read")
    public ApiResponse<Void> markRead(@PathVariable Long id) {
        notifyService.markRead(traceContext.getUserId(), id);
        return ApiResponse.ok(null);
    }
}
