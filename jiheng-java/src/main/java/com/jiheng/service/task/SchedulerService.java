package com.jiheng.service.task;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.entity.ScheduledTaskEntity;
import com.jiheng.repository.TaskMapper;
import com.jiheng.service.notify.NotifyService;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class SchedulerService {
    private final TaskMapper taskMapper;
    private final NotifyService notifyService;

    public SchedulerService(TaskMapper taskMapper, NotifyService notifyService) {
        this.taskMapper = taskMapper;
        this.notifyService = notifyService;
    }

    public void scanExpiredTasks() {
        List<ScheduledTaskEntity> tasks = taskMapper.selectList(new LambdaQueryWrapper<ScheduledTaskEntity>()
                .eq(ScheduledTaskEntity::getStatus, "active").eq(ScheduledTaskEntity::getType, "scheduled")
                .le(ScheduledTaskEntity::getNextRunAt, LocalDateTime.now()));
        for (ScheduledTaskEntity task : tasks) {
            execute(task);
        }
    }

    private void execute(ScheduledTaskEntity task) {
        task.setLastTriggerAt(LocalDateTime.now());
        task.setLastResult("accepted");
        task.setNextRunAt(LocalDateTime.now().plusMinutes(1));
        taskMapper.updateById(task);
        notifyService.create(Map.of("user_id", task.getUserId(), "type", "task_result",
                "title", "定时任务已执行", "content", task.getTaskId(), "task_id", task.getTaskId()));
    }
}
