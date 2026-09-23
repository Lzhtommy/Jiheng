package com.jiheng.controller.events;

import com.jiheng.dto.ApiResponse;
import com.jiheng.service.events.EventService;
import com.jiheng.util.TraceContext;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/events")
public class EventController {
    private final EventService eventService;
    private final TraceContext traceContext;

    public EventController(EventService eventService, TraceContext traceContext) {
        this.eventService = eventService;
        this.traceContext = traceContext;
    }

    @PostMapping
    public ApiResponse<Void> batch(@RequestBody List<Map<String, Object>> events) {
        eventService.batchInsert(traceContext.getUserId(), events);
        return ApiResponse.ok(null);
    }
}
