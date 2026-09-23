package com.jiheng.service.profile;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.dto.profile.UserProfileDto;
import com.jiheng.dto.profile.UserStatsDto;
import com.jiheng.entity.ReportEntity;
import com.jiheng.entity.UserEntity;
import com.jiheng.entity.UserSkillEntity;
import com.jiheng.exception.AuthException;
import com.jiheng.repository.ReportMapper;
import com.jiheng.repository.UserMapper;
import com.jiheng.repository.UserSkillMapper;
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
    private final UserSkillMapper userSkillMapper;
    private final HashidsUtil hashidsUtil;

    public UserService(UserMapper userMapper, ReportMapper reportMapper, UserSkillMapper userSkillMapper,
                       HashidsUtil hashidsUtil) {
        this.userMapper = userMapper;
        this.reportMapper = reportMapper;
        this.userSkillMapper = userSkillMapper;
        this.hashidsUtil = hashidsUtil;
    }

    public UserProfileDto getProfile(Long userId) {
        UserEntity user = requireUser(userId);

        UserProfileDto dto = new UserProfileDto();
        dto.setUserId(hashidsUtil.encode(user.getId()));
        dto.setPhone(user.getPhone());
        dto.setDisplayName(user.getDisplayName());
        dto.setAvatar(user.getAvatar());
        dto.setPlan(user.getPlan());
        dto.setDepartment(user.getDepartment());
        dto.setPoints(user.getPoints());
        dto.setPhoneBound(user.getPhoneBound());
        dto.setDataScopes(user.getDataScopes());
        dto.setLocale(user.getLocale());
        dto.setNotifyOn(user.getNotifyOn());
        dto.setStats(getStats(user));
        return dto;
    }

    public void updateProfile(Long userId, String displayName, String avatar) {
        UserEntity user = requireUser(userId);
        if (displayName != null) {
            user.setDisplayName(displayName);
        }
        if (avatar != null) {
            user.setAvatar(avatar);
        }
        userMapper.updateById(user);
    }

    private UserEntity requireUser(Long userId) {
        UserEntity user = userMapper.selectById(userId);
        if (user == null) {
            // 令牌有效但用户已不存在（如数据库重建），让前端重新登录
            throw new AuthException("AUTH_USER_NOT_FOUND", "用户不存在，请重新登录");
        }
        return user;
    }

    private UserStatsDto getStats(UserEntity user) {
        UserStatsDto stats = new UserStatsDto();
        stats.setReportCount(reportMapper.selectCount(
                new LambdaQueryWrapper<ReportEntity>().eq(ReportEntity::getUserId, user.getId())));
        stats.setSkillCount(userSkillMapper.selectCount(
                new LambdaQueryWrapper<UserSkillEntity>()
                        .eq(UserSkillEntity::getUserId, user.getId())
                        .eq(UserSkillEntity::getEnabled, true)));
        if (user.getCreatedAt() != null) {
            stats.setUsageDays(Duration.between(user.getCreatedAt(), LocalDateTime.now()).toDays());
        }
        return stats;
    }
}
