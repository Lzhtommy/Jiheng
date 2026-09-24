package com.jiheng.controller.report;

import com.jiheng.dto.ApiResponse;
import com.jiheng.dto.report.ReportCreateRequest;
import com.jiheng.entity.ReportEntity;
import com.jiheng.service.report.ReportService;
import com.jiheng.service.report.ExportService;
import com.jiheng.util.TraceContext;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
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
@RequestMapping("/api/v1/reports")
public class ReportController {
    private final ReportService reportService;
    private final TraceContext traceContext;
    private final ExportService exportService;

    public ReportController(ReportService reportService, TraceContext traceContext, ExportService exportService) {
        this.reportService = reportService;
        this.traceContext = traceContext;
        this.exportService = exportService;
    }

    @GetMapping
    public ApiResponse<List<ReportEntity>> list(@RequestParam(defaultValue = "all") String type) {
        return ApiResponse.ok(reportService.list(traceContext.getUserId(), type));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<ReportEntity> create(@Valid @RequestBody ReportCreateRequest request) {
        return ApiResponse.ok(reportService.createFromAnswer(traceContext.getUserId(), request));
    }

    @GetMapping("/{reportId}")
    public ApiResponse<ReportEntity> get(@PathVariable String reportId) {
        return ApiResponse.ok(reportService.get(traceContext.getUserId(), reportId));
    }

    @PostMapping("/{reportId}/export")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public ApiResponse<Map<String, String>> export(@PathVariable String reportId, @RequestBody Map<String, String> request) {
        reportService.get(traceContext.getUserId(), reportId);
        String format = request.get("format");
        if (!"pdf".equals(format) && !"word".equals(format)) {
            throw new IllegalArgumentException("format must be pdf or word");
        }
        return ApiResponse.ok(Map.of("task_id", exportService.enqueue(reportService.get(traceContext.getUserId(), reportId), format)));
    }
}
