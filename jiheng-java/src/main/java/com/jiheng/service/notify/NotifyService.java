package com.jiheng.service.notify;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.entity.NotificationEntity;
import com.jiheng.repository.NotificationMapper;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class NotifyService {
    private final NotificationMapper notificationMapper;

    public NotifyService(NotificationMapper notificationMapper) {
        this.notificationMapper = notificationMapper;
    }

    public NotificationEntity create(Map<String, Object> data) {
        NotificationEntity notification = new NotificationEntity();
        notification.setNotificationId(UUID.randomUUID().toString());
        notification.setUserId(Long.valueOf(String.valueOf(data.get("user_id"))));
        notification.setType(String.valueOf(data.getOrDefault("type", "system")));
        notification.setTitle(String.valueOf(data.getOrDefault("title", "系统通知")));
        notification.setContent(String.valueOf(data.getOrDefault("content", "")));
        notification.setTaskId((String) data.get("task_id"));
        notification.setIsRead(false);
        notificationMapper.insert(notification);
        return notification;
    }

    public List<NotificationEntity> list(Long userId) {
        return notificationMapper.selectList(new LambdaQueryWrapper<NotificationEntity>()
                .eq(NotificationEntity::getUserId, userId).orderByDesc(NotificationEntity::getCreatedAt));
    }

    public void markRead(Long userId, Long id) {
        notificationMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<NotificationEntity>()
                .eq(NotificationEntity::getId, id).eq(NotificationEntity::getUserId, userId).set(NotificationEntity::getIsRead, true));
    }
}
