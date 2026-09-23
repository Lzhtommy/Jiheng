-- V3__seed_experts.sql
-- 6 个专家种子数据

INSERT INTO expert (id, expert_id, name, initial, avatar_bg, description, system_prompt_ref, toolset, sort_order, config_version) VALUES
(1, 'expert_meeting', '会议专家', '会', '#4a90d9', '专注会议纪要、电话会、路演等会议场景的信息提取与结构化整理', 'prompts/expert_meeting.txt', '["search","research"]', 1, 1),
(2, 'expert_stock_research', '个股研究专家', '股', '#50c878', '专注个股深度研究，覆盖基本面、估值、催化剂与风险分析', 'prompts/expert_stock_research.txt', '["search","quote","research"]', 2, 1),
(3, 'expert_industry_research', '行业研究专家', '行', '#f5a623', '专注行业景气度、竞争格局、产业链与投资逻辑分析', 'prompts/expert_industry_research.txt', '["search","quote","research"]', 3, 1),
(4, 'expert_wealth_management', '财富管理专家', '财', '#9b59b6', '专注产品解读、资产配置、客户服务与财富规划场景', 'prompts/expert_wealth_management.txt', '["search","quote","research"]', 4, 1),
(5, 'expert_research_report', '研报专家', '研', '#e74c3c', '专注研报撰写、财报分析、会议纪要与深度报告生成', 'prompts/expert_research_report.txt', '["search","quote","research"]', 5, 1),
(6, 'expert_sentiment', '舆情专家', '舆', '#3498db', '专注舆情监测、新闻情感分析与事件影响评估', 'prompts/expert_sentiment.txt', '["search","news"]', 6, 1);