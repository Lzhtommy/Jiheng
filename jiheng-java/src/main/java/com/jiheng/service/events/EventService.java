package com.jiheng.service.events;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiheng.entity.EventEntity;
import com.jiheng.exception.BizException;
import com.jiheng.repository.EventMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class EventService {
    private final EventMapper eventMapper;
    private final ObjectMapper objectMapper;

    public EventService(EventMapper eventMapper, ObjectMapper objectMapper) {
        this.eventMapper = eventMapper;
        this.objectMapper = objectMapper;
    }

    public void batchInsert(Long userId, List<Map<String, Object>> events) {
        for (Map<String, Object> event : events) {
            Object props = event.getOrDefault("props", Map.of());
            if (event.get("event") == null || event.get("timestamp") == null || props.toString().contains("content")) {
                throw new BizException("EVENT_FORMAT_INVALID", "埋点格式无效");
            }
            try {
                EventEntity entity = new EventEntity();
                entity.setUserId(userId);
                entity.setEvent(String.valueOf(event.get("event")));
                entity.setTimestamp(LocalDateTime.parse(String.valueOf(event.get("timestamp"))));
                entity.setProps(objectMapper.writeValueAsString(props));
                eventMapper.insert(entity);
            } catch (Exception exception) {
                throw new BizException("EVENT_FORMAT_INVALID", "埋点格式无效", exception);
            }
        }
    }
}
