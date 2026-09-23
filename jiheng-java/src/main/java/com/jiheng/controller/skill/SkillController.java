package com.jiheng.controller.skill;

import com.jiheng.dto.ApiResponse;
import com.jiheng.dto.skill.SkillToggleRequest;
import com.jiheng.entity.SkillEntity;
import com.jiheng.service.skill.SkillService;
import com.jiheng.util.TraceContext;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 技能库管理控制器
 *
 * @author jiheng
 */
@RestController
@RequestMapping("/api/v1")
public class SkillController {

    private final SkillService skillService;
    private final TraceContext traceContext;

    public SkillController(SkillService skillService, TraceContext traceContext) {
        this.skillService = skillService;
        this.traceContext = traceContext;
    }

    @GetMapping("/config/skills")
    public ApiResponse<Map<String, Object>> listOfficial() {
        List<SkillEntity> skills = skillService.getOfficialCatalog();
        return ApiResponse.ok(Map.of("skills", skills, "version", skillService.getCatalogVersion()));
    }

    @PutMapping("/skills/{skillId}/enabled")
    public ApiResponse<Void> toggleEnabled(Long skillId, @Valid @RequestBody SkillToggleRequest request) {
        skillService.toggleSkill(traceContext.getUserId(), skillId, request.getEnabled());
        return ApiResponse.ok(null);
    }

    @PostMapping("/skills")
    public ApiResponse<SkillEntity> createCustom(@RequestBody Map<String, String> body) {
        SkillEntity skill = skillService.createCustomSkill(
                traceContext.getUserId(),
                body.get("name"),
                body.get("description"),
                body.get("promptTemplate"),
                body.get("toolset"));
        return ApiResponse.ok(skill);
    }

    @GetMapping("/skills/custom")
    public ApiResponse<List<SkillEntity>> listCustom() {
        return ApiResponse.ok(skillService.listCustomSkills(traceContext.getUserId()));
    }
}