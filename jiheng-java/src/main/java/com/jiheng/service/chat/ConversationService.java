package com.jiheng.service.chat;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.entity.ChatMessageEntity;
import com.jiheng.entity.ConversationEntity;
import com.jiheng.repository.ChatMessageMapper;
import com.jiheng.repository.ConversationMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 历史对话：会话列表、消息读取、一轮问答的落库
 *
 * @author jiheng
 */
@Service
public class ConversationService {
    private static final int TITLE_LIMIT = 40;

    private final ConversationMapper conversationMapper;
    private final ChatMessageMapper chatMessageMapper;

    public ConversationService(ConversationMapper conversationMapper, ChatMessageMapper chatMessageMapper) {
        this.conversationMapper = conversationMapper;
        this.chatMessageMapper = chatMessageMapper;
    }

    public List<ConversationEntity> list(Long userId) {
        return conversationMapper.selectList(new LambdaQueryWrapper<ConversationEntity>()
                .eq(ConversationEntity::getUserId, userId)
                .isNull(ConversationEntity::getDeletedAt)
                .orderByDesc(ConversationEntity::getUpdatedAt));
    }

    public List<ChatMessageEntity> messages(Long userId, String conversationId) {
        requireOwned(userId, conversationId);
        return chatMessageMapper.selectList(new LambdaQueryWrapper<ChatMessageEntity>()
                .eq(ChatMessageEntity::getConversationId, conversationId)
                .orderByAsc(ChatMessageEntity::getId));
    }

    public void delete(Long userId, String conversationId) {
        ConversationEntity conversation = requireOwned(userId, conversationId);
        conversation.setDeletedAt(LocalDateTime.now());
        conversationMapper.updateById(conversation);
    }

    /**
     * 记录一轮问答。会话不存在时创建，标题取用户第一条提问。
     */
    public void appendTurn(Map<String, Object> data) {
        String conversationId = String.valueOf(data.get("conversation_id"));
        Long userId = Long.valueOf(String.valueOf(data.get("user_id")));
        String question = String.valueOf(data.getOrDefault("question", ""));
        String answer = String.valueOf(data.getOrDefault("answer", ""));
        String mode = (String) data.get("mode");
        String expert = (String) data.get("expert");

        ConversationEntity conversation = conversationMapper.selectOne(new LambdaQueryWrapper<ConversationEntity>()
                .eq(ConversationEntity::getConversationId, conversationId));
        if (conversation == null) {
            conversation = new ConversationEntity();
            conversation.setConversationId(conversationId);
            conversation.setConversationUuid(UUID.randomUUID().toString());
            conversation.setUserId(userId);
            conversation.setTitle(question.length() > TITLE_LIMIT ? question.substring(0, TITLE_LIMIT) : question);
            conversation.setStatus("active");
            conversation.setMode(mode);
            conversation.setExpert(expert);
            conversationMapper.insert(conversation);
        } else if (!userId.equals(conversation.getUserId())) {
            throw new IllegalArgumentException("会话不属于该用户");
        }

        insertMessage(conversationId, userId, "user", question, mode, expert);
        insertMessage(conversationId, userId, "assistant", answer, mode, expert);
        conversation.setUpdatedAt(LocalDateTime.now());
        conversationMapper.updateById(conversation);
    }

    private void insertMessage(String conversationId, Long userId, String role, String content,
                               String mode, String expert) {
        ChatMessageEntity message = new ChatMessageEntity();
        message.setConversationId(conversationId);
        message.setUserId(userId);
        message.setRole(role);
        message.setContent(content);
        message.setMode(mode);
        message.setExpert(expert);
        chatMessageMapper.insert(message);
    }

    private ConversationEntity requireOwned(Long userId, String conversationId) {
        ConversationEntity conversation = conversationMapper.selectOne(new LambdaQueryWrapper<ConversationEntity>()
                .eq(ConversationEntity::getConversationId, conversationId)
                .eq(ConversationEntity::getUserId, userId)
                .isNull(ConversationEntity::getDeletedAt));
        if (conversation == null) {
            throw new IllegalArgumentException("会话不存在");
        }
        return conversation;
    }
}
