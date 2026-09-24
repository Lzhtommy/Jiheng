package com.jiheng.schedule;

import com.jiheng.service.task.SchedulerService;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class JihengTaskScheduler {
    private final SchedulerService schedulerService;

    public JihengTaskScheduler(SchedulerService schedulerService) {
        this.schedulerService = schedulerService;
    }

    @Scheduled(fixedDelay = 60000)
    public void scan() {
        schedulerService.scanExpiredTasks();
    }
}
