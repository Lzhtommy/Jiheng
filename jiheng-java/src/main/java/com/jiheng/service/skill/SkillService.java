package com.jiheng.service.skill;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.dto.skill.SkillDto;
import com.jiheng.entity.SkillEntity;
import com.jiheng.entity.UserSkillEntity;
import com.jiheng.exception.BizException;
import com.jiheng.repository.SkillMapper;
import com.jiheng.repository.UserSkillMapper;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 技能库管理服务
 *
 * @author jiheng
 */
@Service
public class SkillService {

    private final SkillMapper skillMapper;
    private final UserSkillMapper userSkillMapper;

    public SkillService(SkillMapper skillMapper, UserSkillMapper userSkillMapper) {
        this.skillMapper = skillMapper;
        this.userSkillMapper = userSkillMapper;
    }

    public List<SkillEntity> getOfficialCatalog() {
        return skillMapper.selectList(
                new LambdaQueryWrapper<SkillEntity>()
                        .eq(SkillEntity::getKind, "official")
                        .orderByAsc(SkillEntity::getSortOrder));
    }

    public int getCatalogVersion() {
        return 1;
    }

    public void toggleSkill(Long userId, Long skillId, Boolean enabled) {
        SkillEntity skill = skillMapper.selectById(skillId);
        if (skill == null) {
            throw new BizException("SKILL_NOT_FOUND", "技能不存在");
        }

        UserSkillEntity userSkill = userSkillMapper.selectOne(
                new LambdaQueryWrapper<UserSkillEntity>()
                        .eq(UserSkillEntity::getUserId, userId)
                        .eq(UserSkillEntity::getSkillId, skillId));

        if (userSkill == null) {
            userSkill = new UserSkillEntity();
            userSkill.setUserId(userId);
            userSkill.setSkillId(skillId);
            userSkill.setEnabled(enabled);
            userSkillMapper.insert(userSkill);
        } else {
            userSkill.setEnabled(enabled);
            userSkillMapper.updateById(userSkill);
        }
    }

    public SkillEntity createCustomSkill(Long userId, String name, String description,
                                         String promptTemplate, String toolset) {
        SkillEntity skill = new SkillEntity();
        skill.setName(name);
        skill.setDescription(description);
        skill.setKind("custom");
        skill.setPromptTemplate(promptTemplate);
        skill.setToolset(toolset);
        skill.setCreatorId(userId);
        skill.setRunCount(0);
        return skillMapper.insert(skill) > 0 ? skill : null;
    }

    public List<SkillEntity> listCustomSkills(Long userId) {
        return skillMapper.selectList(
                new LambdaQueryWrapper<SkillEntity>()
                        .eq(SkillEntity::getKind, "custom")
                        .eq(SkillEntity::getCreatorId, userId)
                        .orderByDesc(SkillEntity::getCreatedAt));
    }

    public void incrementRunCount(Long skillId) {
        SkillEntity skill = skillMapper.selectById(skillId);
        if (skill != null) {
            skill.setRunCount(skill.getRunCount() + 1);
            skillMapper.updateById(skill);
        }
    }
}