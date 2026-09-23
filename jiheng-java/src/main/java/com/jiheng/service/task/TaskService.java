package com.jiheng.service.task;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.entity.ScheduledTaskEntity;
import com.jiheng.exception.BizException;
import com.jiheng.repository.TaskMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class TaskService {
    private final TaskMapper taskMapper;

    public TaskService(TaskMapper taskMapper) {
        this.taskMapper = taskMapper;
    }

    public ScheduledTaskEntity create(Long userId, Map<String, Object> data) {
        String type = String.valueOf(data.get("type"));
        if (!"scheduled".equals(type) && !"reminder".equals(type)) {
            throw new BizException("CRON_INVALID", "任务类型无效");
        }
        String cron = (String) data.get("cron");
        if ("scheduled".equals(type) && (cron == null || cron.isBlank())) {
            throw new BizException("CRON_INVALID", "cron 表达式格式无效");
        }
        ScheduledTaskEntity task = new ScheduledTaskEntity();
        task.setTaskId(UUID.randomUUID().toString());
        task.setUserId(userId);
        task.setType(type);
        task.setCron(cron);
        task.setConditionExpr((String) data.get("condition"));
        task.setPayload(String.valueOf(data.getOrDefault("payload", "{}")));
        task.setStatus("active");
        task.setNextRunAt("scheduled".equals(type) ? LocalDateTime.now().plusMinutes(1) : null);
        taskMapper.insert(task);
        return task;
    }

    public List<ScheduledTaskEntity> list(Long userId, String type) {
        return taskMapper.selectList(new LambdaQueryWrapper<ScheduledTaskEntity>().eq(ScheduledTaskEntity::getUserId, userId)
                .eq(type != null, ScheduledTaskEntity::getType, type).orderByDesc(ScheduledTaskEntity::getCreatedAt));
    }

    public void delete(Long userId, String taskId) {
        taskMapper.delete(new LambdaQueryWrapper<ScheduledTaskEntity>().eq(ScheduledTaskEntity::getUserId, userId)
                .eq(ScheduledTaskEntity::getTaskId, taskId));
    }
}
