package com.jiheng.controller.task;

import com.jiheng.dto.ApiResponse;
import com.jiheng.entity.ScheduledTaskEntity;
import com.jiheng.service.task.TaskService;
import com.jiheng.util.TraceContext;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/tasks")
public class TaskController {
    private final TaskService taskService;
    private final TraceContext traceContext;

    public TaskController(TaskService taskService, TraceContext traceContext) {
        this.taskService = taskService;
        this.traceContext = traceContext;
    }

    @GetMapping
    public ApiResponse<List<ScheduledTaskEntity>> list(@RequestParam(required = false) String type) {
        return ApiResponse.ok(taskService.list(traceContext.getUserId(), type));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<ScheduledTaskEntity> create(@RequestBody Map<String, Object> request) {
        return ApiResponse.ok(taskService.create(traceContext.getUserId(), request));
    }

    @DeleteMapping("/{taskId}")
    public ApiResponse<Void> delete(@PathVariable String taskId) {
        taskService.delete(traceContext.getUserId(), taskId);
        return ApiResponse.ok(null);
    }
}
