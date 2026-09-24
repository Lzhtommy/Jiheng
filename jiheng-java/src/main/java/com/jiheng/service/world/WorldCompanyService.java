package com.jiheng.service.world;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jiheng.entity.WorldCompanyEntity;
import com.jiheng.exception.BizException;
import com.jiheng.repository.WorldCompanyMapper;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
public class WorldCompanyService {
    private final WorldCompanyMapper worldCompanyMapper;
    private final ObjectMapper objectMapper;

    public WorldCompanyService(WorldCompanyMapper worldCompanyMapper, ObjectMapper objectMapper) {
        this.worldCompanyMapper = worldCompanyMapper;
        this.objectMapper = objectMapper;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> save(Map<String, Object> body) {
        Long userId = Long.valueOf(String.valueOf(body.get("user_id")));
        Object scenarioObj = body.get("scenario");
        if (!(scenarioObj instanceof Map<?, ?> scenario)) {
            throw new BizException("INVALID_REQUEST", "scenario 字段缺失或格式错误");
        }
        Object companyObj = scenario.get("company");
        if (!(companyObj instanceof Map<?, ?> company)) {
            throw new BizException("INVALID_REQUEST", "scenario.company 字段缺失或格式错误");
        }
        String companyId = String.valueOf(company.get("id"));

        WorldCompanyEntity entity = worldCompanyMapper.selectOne(new LambdaQueryWrapper<WorldCompanyEntity>()
                .eq(WorldCompanyEntity::getUserId, userId)
                .eq(WorldCompanyEntity::getCompanyId, companyId));
        boolean isNew = entity == null;
        if (isNew) {
            entity = new WorldCompanyEntity();
            entity.setUserId(userId);
            entity.setCompanyId(companyId);
        }
        entity.setName(String.valueOf(company.get("name")));
        entity.setCode(company.get("code") == null ? "" : String.valueOf(company.get("code")));
        entity.setTag(company.get("tag") == null ? "" : String.valueOf(company.get("tag")));
        entity.setKind(String.valueOf(company.get("kind")));
        entity.setScenarioJson(toJson(scenario));

        if (isNew) {
            worldCompanyMapper.insert(entity);
        } else {
            worldCompanyMapper.updateById(entity);
        }
        return (Map<String, Object>) scenario;
    }

    public List<Map<String, Object>> listForUser(Long userId) {
        List<WorldCompanyEntity> entities = worldCompanyMapper.selectList(new LambdaQueryWrapper<WorldCompanyEntity>()
                .eq(WorldCompanyEntity::getUserId, userId)
                .orderByAsc(WorldCompanyEntity::getCreatedAt));
        return entities.stream().map(entity -> fromJson(entity.getScenarioJson())).toList();
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new BizException("EVENT_FORMAT_INVALID", "JSON 数据格式无效", exception);
        }
    }

    private Map<String, Object> fromJson(String json) {
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {
            });
        } catch (JsonProcessingException exception) {
            throw new BizException("EVENT_FORMAT_INVALID", "JSON 数据格式无效", exception);
        }
    }
}
