package com.jiheng.service.report;

import com.jiheng.entity.ExportTaskEntity;
import com.jiheng.entity.ReportEntity;
import com.jiheng.repository.ExportTaskMapper;
import com.jiheng.service.notify.NotifyService;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import java.util.concurrent.Executor;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

@Service
public class ExportService {
    private final ExportTaskMapper exportTaskMapper;
    private final NotifyService notifyService;
    private final Executor exportExecutor;

    public ExportService(ExportTaskMapper exportTaskMapper, NotifyService notifyService,
                         @Qualifier("exportExecutor") Executor exportExecutor) {
        this.exportTaskMapper = exportTaskMapper;
        this.notifyService = notifyService;
        this.exportExecutor = exportExecutor;
    }

    public String enqueue(ReportEntity report, String format) {
        ExportTaskEntity task = new ExportTaskEntity();
        task.setTaskId(UUID.randomUUID().toString());
        task.setReportId(report.getId());
        task.setUserId(report.getUserId());
        task.setFormat(format);
        task.setStatus("pending");
        exportTaskMapper.insert(task);
        exportExecutor.execute(() -> render(task, report));
        return task.getTaskId();
    }

    private void render(ExportTaskEntity task, ReportEntity report) {
        try {
            task.setStatus("processing");
            exportTaskMapper.updateById(task);
            Path directory = Path.of("data", "exports");
            Files.createDirectories(directory);
            Path output = directory.resolve(task.getTaskId() + "." + task.getFormat());
            // The exported artifact is markdown-compatible until a PDF/Word renderer is configured.
            Files.writeString(output, "# " + report.getTitle() + "\n\n" + report.getContent());
            task.setStatus("completed");
            task.setFilePath(output.toString());
            task.setCompletedAt(LocalDateTime.now());
            exportTaskMapper.updateById(task);
            notifyService.create(Map.of("user_id", report.getUserId(), "type", "export_completed",
                    "title", "报告导出完成", "content", report.getTitle()));
        } catch (Exception exception) {
            task.setStatus("failed");
            task.setErrorMessage(exception.getMessage());
            task.setCompletedAt(LocalDateTime.now());
            exportTaskMapper.updateById(task);
            notifyService.create(Map.of("user_id", report.getUserId(), "type", "export_failed",
                    "title", "报告导出失败", "content", report.getTitle()));
        }
    }
}
