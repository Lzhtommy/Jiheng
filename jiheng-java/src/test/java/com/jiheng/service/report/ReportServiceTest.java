package com.jiheng.service.report;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiheng.dto.report.ReportCreateRequest;
import com.jiheng.entity.ReportEntity;
import com.jiheng.repository.ReportMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class ReportServiceTest {

    @Test
    void createsReportFromAnswerForAuthenticatedUser() throws Exception {
        ReportMapper mapper = mock(ReportMapper.class);
        ReportService service = new ReportService(mapper, new ObjectMapper());
        ReportCreateRequest request = new ReportCreateRequest();
        request.setQuestion("  近三年财报表现如何？  ");
        request.setContent("# 核心结论\n营收持续增长。\n" + "x".repeat(1500));
        request.setRefs(List.of(Map.of("title", "公司年报", "url", "https://example.com/report")));
        request.setSourceConversationId("conversation-1");

        ReportEntity report = service.createFromAnswer(42L, request);

        assertEquals(42L, report.getUserId());
        assertEquals("chat_answer", report.getKind());
        assertEquals("近三年财报表现如何？", report.getTitle());
        assertEquals("核心结论", report.getSummary());
        assertEquals(1, report.getRefCount());
        assertEquals(2, report.getPages());
        assertEquals("conversation-1", report.getSourceConversationId());
        assertEquals("completed", report.getState());
        assertEquals("公司年报", new ObjectMapper().readTree(report.getRefs()).get(0).get("title").asText());
        assertNotNull(report.getReportId());
        verify(mapper).insert(report);
    }

    @Test
    void createsReportWithEmptyReferences() {
        ReportMapper mapper = mock(ReportMapper.class);
        ReportService service = new ReportService(mapper, new ObjectMapper());
        ReportCreateRequest request = new ReportCreateRequest();
        request.setQuestion("问题");
        request.setContent("回答");
        request.setRefs(null);

        ReportEntity report = service.createFromAnswer(7L, request);

        assertEquals("[]", report.getRefs());
        assertEquals(0, report.getRefCount());
        assertEquals(1, report.getPages());
    }
}
