package com.jiheng.service.expert;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.jiheng.entity.ExpertEntity;
import com.jiheng.repository.ExpertMapper;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 专家配置下发服务
 *
 * @author jiheng
 */
@Service
public class ExpertService {

    private final ExpertMapper expertMapper;

    public ExpertService(ExpertMapper expertMapper) {
        this.expertMapper = expertMapper;
    }

    public List<ExpertEntity> getExpertConfig() {
        return expertMapper.selectList(
                new LambdaQueryWrapper<ExpertEntity>().orderByAsc(ExpertEntity::getSortOrder));
    }

    public int getConfigVersion() {
        return 1;
    }
}