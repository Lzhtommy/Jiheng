-- V6__rename_experts_to_analysts.sql
-- 展示名与职责：研究专家 → 分析师；研报专家 → 财报分析师

UPDATE expert SET name = '个股分析师', description = '专注个股深度分析，覆盖基本面、估值、催化剂与风险'
WHERE expert_id = 'expert_stock_research';

UPDATE expert SET name = '行业分析师', description = '专注行业景气度、竞争格局、产业链与投资逻辑分析'
WHERE expert_id = 'expert_industry_research';

UPDATE expert SET name = '财报分析师', initial = '报', description = '专注上市公司定期报告解读，提炼营收利润、现金流、毛利率与同比变化'
WHERE expert_id = 'expert_research_report';
