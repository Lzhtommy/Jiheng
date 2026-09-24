package com.jiheng.controller.internal;

import com.jiheng.dto.ApiResponse;
import com.jiheng.entity.ExpertEntity;
import com.jiheng.entity.SkillEntity;
import com.jiheng.service.chat.ConversationService;
import com.jiheng.service.expert.ExpertService;
import com.jiheng.service.skill.SkillService;
import com.jiheng.service.notify.NotifyService;
import com.jiheng.service.report.ReportService;
import com.jiheng.service.world.WorldCompanyService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 服务间接口控制器（/internal/*，仅内网 + Service Token）
 *
 * @author jiheng
 */
@RestController
@RequestMapping("/internal")
public class InternalController {

    private final ExpertService expertService;
    private final SkillService skillService;
    private final ReportService reportService;
    private final NotifyService notifyService;
    private final ConversationService conversationService;
    private final WorldCompanyService worldCompanyService;

    public InternalController(ExpertService expertService, SkillService skillService, ReportService reportService,
                              NotifyService notifyService, ConversationService conversationService,
                              WorldCompanyService worldCompanyService) {
        this.expertService = expertService;
        this.skillService = skillService;
        this.reportService = reportService;
        this.notifyService = notifyService;
        this.conversationService = conversationService;
        this.worldCompanyService = worldCompanyService;
    }

    @GetMapping("/config/experts")
    public ApiResponse<List<ExpertEntity>> getExperts() {
        return ApiResponse.ok(expertService.getExpertConfig());
    }

    @GetMapping("/config/skills")
    public ApiResponse<List<SkillEntity>> getSkills(@RequestParam(required = false) Long userId) {
        return ApiResponse.ok(skillService.getOfficialCatalog());
    }

    @PostMapping("/reports")
    public ApiResponse<Map<String, Object>> archiveReport(@RequestBody Map<String, Object> body) {
        return ApiResponse.ok(Map.of("report_id", reportService.archive(body).getReportId()));
    }

    @PostMapping("/skills/{skillId}/run")
    public ApiResponse<Void> incrementSkillRun(@PathVariable Long skillId) {
        skillService.incrementRunCount(skillId);
        return ApiResponse.ok(null);
    }

    @PostMapping("/conversations/turns")
    public ApiResponse<Void> appendTurn(@RequestBody Map<String, Object> body) {
        conversationService.appendTurn(body);
        return ApiResponse.ok(null);
    }

    @PostMapping("/notifications")
    public ApiResponse<Void> createNotification(@RequestBody Map<String, Object> body) {
        notifyService.create(body);
        return ApiResponse.ok(null);
    }

    @PostMapping("/world/companies")
    public ApiResponse<Map<String, Object>> saveWorldCompany(@RequestBody Map<String, Object> body) {
        return ApiResponse.ok(worldCompanyService.save(body));
    }
}
