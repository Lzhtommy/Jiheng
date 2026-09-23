package com.jiheng.service.profile;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.dto.profile.UserProfileDto;
import com.jiheng.dto.profile.UserStatsDto;
import com.jiheng.entity.ReportEntity;
import com.jiheng.entity.UserEntity;
import com.jiheng.exception.BizException;
import com.jiheng.repository.ReportMapper;
import com.jiheng.repository.UserMapper;
import com.jiheng.util.HashidsUtil;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;

/**
 * 用户资料与统计服务
 *
 * @author jiheng
 */
@Service
public class UserService {

    private final UserMapper userMapper;
    private final ReportMapper reportMapper;
    private final HashidsUtil hashidsUtil;

    public UserService(UserMapper userMapper, ReportMapper reportMapper, HashidsUtil hashidsUtil) {
        this.userMapper = userMapper;
        this.reportMapper = reportMapper;
        this.hashidsUtil = hashidsUtil;
    }

    public UserProfileDto getProfile(Long userId) {
        UserEntity user = userMapper.selectById(userId);
        if (user == null) {
            throw new BizException("AUTH_USER_NOT_FOUND", "用户不存在");
        }

        UserProfileDto dto = new UserProfileDto();
        dto.setUserId(hashidsUtil.encode(user.getId()));
        dto.setPhone(user.getPhone());
        dto.setDisplayName(user.getDisplayName());
        dto.setAvatar(user.getAvatar());
        dto.setPlan(user.getPlan());
        dto.setDepartment(user.getDepartment());
        dto.setPoints(user.getPoints());
        dto.setPhoneBound(user.getPhoneBound());
        dto.setLocale(user.getLocale());
        dto.setNotifyOn(user.getNotifyOn());
        dto.setStats(getStats(userId));
        return dto;
    }

    public void updateProfile(Long userId, String displayName, String avatar) {
        UserEntity user = userMapper.selectById(userId);
        if (user == null) {
            throw new BizException("AUTH_USER_NOT_FOUND", "用户不存在");
        }
        if (displayName != null) {
            user.setDisplayName(displayName);
        }
        if (avatar != null) {
            user.setAvatar(avatar);
        }
        userMapper.updateById(user);
    }

    public UserStatsDto getStats(Long userId) {
        UserStatsDto stats = new UserStatsDto();
        stats.setReportCount(reportMapper.selectCount(
                new LambdaQueryWrapper<ReportEntity>().eq(ReportEntity::getUserId, userId)));

        UserEntity user = userMapper.selectById(userId);
        if (user != null && user.getCreatedAt() != null) {
            stats.setUsageDays(Duration.between(user.getCreatedAt(), LocalDateTime.now()).toDays());
        }
        return stats;
    }
}