package com.jiheng.controller.world;

import com.jiheng.dto.ApiResponse;
import com.jiheng.service.world.WorldCompanyService;
import com.jiheng.util.TraceContext;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/world")
public class WorldController {
    private final WorldCompanyService worldCompanyService;
    private final TraceContext traceContext;

    public WorldController(WorldCompanyService worldCompanyService, TraceContext traceContext) {
        this.worldCompanyService = worldCompanyService;
        this.traceContext = traceContext;
    }

    @GetMapping("/companies")
    public ApiResponse<List<Map<String, Object>>> listCompanies() {
        return ApiResponse.ok(worldCompanyService.listForUser(traceContext.getUserId()));
    }
}
