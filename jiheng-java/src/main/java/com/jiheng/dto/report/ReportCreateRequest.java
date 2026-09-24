package com.jiheng.dto.report;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class ReportCreateRequest {

    @NotBlank(message = "question 不能为空")
    @Size(max = 500, message = "question 不能超过 500 字")
    private String question;

    @NotBlank(message = "content 不能为空")
    private String content;

    private List<Map<String, Object>> refs = List.of();

    @Size(max = 50, message = "sourceConversationId 不能超过 50 字")
    private String sourceConversationId;
}
