package com.jiheng.controller.chat;

import com.jiheng.dto.ApiResponse;
import com.jiheng.entity.ChatMessageEntity;
import com.jiheng.entity.ConversationEntity;
import com.jiheng.service.chat.ConversationService;
import com.jiheng.util.TraceContext;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 历史对话
 *
 * @author jiheng
 */
@RestController
@RequestMapping("/api/v1/conversations")
public class ConversationController {
    private final ConversationService conversationService;
    private final TraceContext traceContext;

    public ConversationController(ConversationService conversationService, TraceContext traceContext) {
        this.conversationService = conversationService;
        this.traceContext = traceContext;
    }

    @GetMapping
    public ApiResponse<List<ConversationEntity>> list() {
        return ApiResponse.ok(conversationService.list(traceContext.getUserId()));
    }

    @GetMapping("/{conversationId}/messages")
    public ApiResponse<List<ChatMessageEntity>> messages(@PathVariable String conversationId) {
        return ApiResponse.ok(conversationService.messages(traceContext.getUserId(), conversationId));
    }

    @DeleteMapping("/{conversationId}")
    public ApiResponse<Void> delete(@PathVariable String conversationId) {
        conversationService.delete(traceContext.getUserId(), conversationId);
        return ApiResponse.ok(null);
    }
}
