package com.jiheng.controller.expert;

import com.jiheng.dto.ApiResponse;
import com.jiheng.entity.ExpertEntity;
import com.jiheng.service.expert.ExpertService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 专家配置下发控制器
 *
 * @author jiheng
 */
@RestController
@RequestMapping("/api/v1/config/experts")
public class ExpertController {

    private final ExpertService expertService;

    public ExpertController(ExpertService expertService) {
        this.expertService = expertService;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> listExperts() {
        List<ExpertEntity> experts = expertService.getExpertConfig();
        return ApiResponse.ok(Map.of("experts", experts, "version", expertService.getConfigVersion()));
    }
}