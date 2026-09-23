package com.jiheng.service.report;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiheng.entity.ReportEntity;
import com.jiheng.exception.BizException;
import com.jiheng.repository.ReportMapper;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ReportService {
    private final ReportMapper reportMapper;
    private final ObjectMapper objectMapper;

    public ReportService(ReportMapper reportMapper, ObjectMapper objectMapper) {
        this.reportMapper = reportMapper;
        this.objectMapper = objectMapper;
    }

    public ReportEntity archive(Map<String, Object> data) {
        ReportEntity report = new ReportEntity();
        report.setReportId(UUID.randomUUID().toString());
        report.setUserId(Long.valueOf(String.valueOf(data.get("user_id"))));
        report.setKind(String.valueOf(data.getOrDefault("kind", "deep_research")));
        report.setTitle(String.valueOf(data.getOrDefault("title", "未命名报告")));
        report.setSummary(String.valueOf(data.getOrDefault("summary", "")));
        report.setContent(String.valueOf(data.getOrDefault("content", "")));
        report.setSourceConversationId((String) data.get("source_conversation_id"));
        report.setState("completed");
        Object refs = data.getOrDefault("refs", List.of());
        report.setRefs(toJson(refs));
        report.setRefCount(refs instanceof List<?> list ? list.size() : 0);
        report.setPages(Math.max(1, (report.getContent().length() + 1499) / 1500));
        reportMapper.insert(report);
        return report;
    }

    public List<ReportEntity> list(Long userId, String kind) {
        return reportMapper.selectList(new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<ReportEntity>()
                .eq(ReportEntity::getUserId, userId)
                .eq(kind != null && !"all".equals(kind), ReportEntity::getKind, kind)
                .orderByDesc(ReportEntity::getCreatedAt));
    }

    public ReportEntity get(Long userId, String reportId) {
        ReportEntity report = reportMapper.selectOne(new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<ReportEntity>()
                .eq(ReportEntity::getUserId, userId).eq(ReportEntity::getReportId, reportId));
        if (report == null) {
            throw new BizException("RESOURCE_NOT_FOUND", "报告不存在");
        }
        return report;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new BizException("EVENT_FORMAT_INVALID", "JSON 数据格式无效", exception);
        }
    }
}
