import 'dart:async';

import 'package:flutter/material.dart';

void main() => runApp(const JihengApp());

class JihengApp extends StatelessWidget {
  const JihengApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: '玑衡AI',
      theme: ThemeData(
        useMaterial3: true,
        fontFamily: 'PingFang SC',
        colorScheme: ColorScheme.fromSeed(seedColor: C.ink),
      ),
      home: const JihengShell(),
    );
  }
}

class C {
  static const bg = Color(0xFFE6E3DD);
  static const paper = Color(0xFFFFFFFF);
  static const ink = Color(0xFF1F2429);
  static const text = Color(0xFF1B1F24);
  static const muted = Color(0xFF767E86);
  static const faint = Color(0xFFF6F4F0);
  static const line = Color(0xFFEDEAE3);
  static const gold = Color(0xFF9C6B3C);
  static const goldSoft = Color(0xFFF3EDE4);
  static const green = Color(0xFF12805C);
}

enum PageKey { home, reports, profile, skills, reminders, notifications }

enum Stage { thinking, tool, done }

class ChatMsg {
  ChatMsg.user(this.text)
      : isUser = true,
        flow = 'generic',
        stage = Stage.done;
  ChatMsg.ai(this.flow)
      : isUser = false,
        text = '',
        stage = Stage.thinking;

  final bool isUser;
  final String text;
  final String flow;
  Stage stage;
  bool refOpen = false;
}

class Script {
  const Script({
    required this.tool,
    required this.intro,
    required this.sections,
    required this.risk,
    required this.ref,
    required this.refCount,
    this.skill = false,
    this.rows = const [],
  });

  final String tool;
  final String intro;
  final List<SectionData> sections;
  final String risk;
  final String ref;
  final int refCount;
  final bool skill;
  final List<List<String>> rows;
}

class SectionData {
  const SectionData(this.title, this.items);
  final String title;
  final List<String> items;
}

const scripts = <String, Script>{
  'innovdrug': Script(
    tool: '聚合搜索',
    intro: '我来帮您分析创新药板块今日集体大幅上涨的核心驱动因素。',
    sections: [
      SectionData('一、政策端持续释放利好',
          ['推进药品试验数据保护制度落地', '建立儿童药、罕见病药市场独占期', '培育3-5个国际竞争力生物医药产业集群']),
      SectionData('二、产业基本面持续超预期兑现',
          ['生物医药行业归母净利润同比增长 64.87%', 'License-out交易总额约1100亿美元，已达2025全年80%']),
      SectionData('三、估值与资金面共振', ['指数PE处于历史低分位', '资金从AI板块高低切换，持续增配创新药']),
    ],
    rows: [
      ['万得创新药主题指数', '+0.04%，报3789.87'],
      ['领涨个股', '康希诺、百奥泰、奥赛康'],
      ['港股创新药指数', '盘中涨幅超6%'],
    ],
    risk: '风险提示：政策仍存变数；板块短期快速上涨后需关注追高风险。',
    ref: '创新药板块今日涨跌幅、领涨个股及板块表现',
    refCount: 22,
  ),
  'midea': Script(
    tool: '聚合搜索',
    intro: '我来帮您分析美的集团近期股价走势与创8个月新高背后的原因。',
    sections: [
      SectionData('核心驱动因素',
          ['海外OBM自主品牌收入占比持续提升', '楼宇科技、机器人与自动化业务减亏明显', '分红比例维持高位，股息率具备吸引力']),
      SectionData('短期股价下跌原因', ['前期涨幅较大后获利盘兑现', '原材料价格阶段性上行压制毛利率预期']),
    ],
    rows: [
      ['最新价', '较前高回落约3.2%'],
      ['机构评级', '多数维持增持/买入'],
    ],
    risk: '风险提示：海外需求波动、原材料价格上行、行业竞争加剧。',
    ref: '美的集团股价走势及机构评级跟踪',
    refCount: 15,
  ),
  'nvidia': Script(
    tool: '聚合搜索',
    intro: '我来帮您梳理英伟达AI芯片需求最新变化及产业链影响。',
    sections: [
      SectionData('需求端持续超预期', ['下一代平台订单能见度已排至2027年', '云厂商资本开支指引持续上修']),
      SectionData('产业链跟踪', ['先进封装产能持续满载', '国产算力链受益于自主可控与算力平权预期']),
    ],
    risk: '风险提示：AI资本开支不及预期、地缘政策限制。',
    ref: '英伟达及AI算力产业链最新跟踪数据',
    refCount: 18,
  ),
  'skill1': Script(
    tool: '宏观数据解读',
    skill: true,
    intro: '已调用「宏观洞察」技能，对8000亿元新型政策性金融工具进行测算。',
    sections: [
      SectionData(
          '工具定位与资金投向', ['重点投向重大项目资本金补充、设备更新与消费基础设施', '采用母子基金结构，撬动银行配套融资']),
      SectionData('规模测算', ['预计带动配套融资1.5-2万亿元', '对四季度基建实物工作量形成支撑']),
    ],
    risk: '风险提示：政策落地节奏及具体投向细则仍需跟踪。',
    ref: '新型政策性金融工具设立方案及规模测算',
    refCount: 12,
  ),
  'skill2': Script(
    tool: '贵金属板块深度透视',
    skill: true,
    intro: '已为您调用「贵金属板块深度透视」技能，结合历史分位与均值对伦敦金银比进行分析。',
    sections: [
      SectionData('金银比历史分位',
          ['当前伦敦金银比处于近10年 78% 分位，显著高于长期均值', '历史上金银比高位回落阶段，白银相对黄金往往有超额表现']),
      SectionData('机构核心观点', ['若实际利率见顶回落，白银在工业需求与金融属性双重驱动下，补涨弹性可能优于黄金']),
    ],
    rows: [
      ['当前金银比', '约82.3'],
      ['近10年均值', '约75.6'],
      ['近10年分位', '78%'],
    ],
    risk: '风险提示：贵金属价格受美联储政策路径、地缘政治等多重因素影响，历史规律不代表未来走势。',
    ref: '伦敦金银比历史分位与均值回归分析',
    refCount: 9,
  ),
  'generic': Script(
    tool: '聚合搜索',
    intro: '收到，我正在为你查询相关信息，请稍候。',
    sections: [
      SectionData('分析结果', ['这是一个原型演示回复，真实应用中会返回结合实时行情与多源检索得到的结构化分析内容。'])
    ],
    risk: '内容由 AI 生成，请核查重要信息。',
    ref: '示例数据来源',
    refCount: 1,
  ),
};

class JihengShell extends StatefulWidget {
  const JihengShell({super.key});

  @override
  State<JihengShell> createState() => JihengShellState();
}

class JihengShellState extends State<JihengShell> {
  PageKey page = PageKey.home;
  final input = TextEditingController();
  final scroll = ScrollController();
  final List<ChatMsg> messages = [];
  final Set<String> disabledSkills = {};
  final List<String> reminders = ['每个交易日 08:00 推送盘前简报'];
  final List<String> notifications = ['创新药板块异动：已生成归因简报'];
  final List<String> activity = ['影石创新：影像硬件出海'];
  String flow = 'generic';
  String mode = '快速问答';
  String reportTab = '全部';
  String skillTab = '已开启的';
  String expert = '';
  bool drawerOpen = false;
  bool expertSheet = false;
  bool modeSelected = false;

  @override
  void dispose() {
    input.dispose();
    scroll.dispose();
    super.dispose();
  }

  void go(PageKey next) {
    setState(() {
      page = next;
      drawerOpen = false;
    });
  }

  void mutate(VoidCallback change) {
    setState(change);
  }

  void setPrompt(String text, String nextFlow) {
    setState(() {
      input.text = text;
      flow = nextFlow;
    });
  }

  void send() {
    final text = input.text.trim();
    if (text.isEmpty) {
      setState(() => expertSheet = true);
      return;
    }
    final key = scripts.containsKey(flow) ? flow : 'generic';
    final ai = ChatMsg.ai(key);
    setState(() {
      messages.add(ChatMsg.user(text));
      messages.add(ai);
      activity.insert(0, '新问答：$text');
      input.clear();
      flow = 'generic';
    });
    _scrollDown();
    Timer(const Duration(milliseconds: 700), () {
      if (!mounted) return;
      setState(() => ai.stage = Stage.tool);
      _scrollDown();
    });
    Timer(const Duration(milliseconds: 1700), () {
      if (!mounted) return;
      setState(() => ai.stage = Stage.done);
      _scrollDown();
    });
  }

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!scroll.hasClients) return;
      scroll.animateTo(scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 240), curve: Curves.easeOut);
    });
  }

  void snack(String text) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(
        content: Text(text),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(milliseconds: 1100),
      ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C.paper,
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(child: _pageBody()),
            if (drawerOpen) DrawerOverlay(state: this),
            if (expertSheet) ExpertSheet(state: this),
          ],
        ),
      ),
    );
  }

  Widget _pageBody() {
    switch (page) {
      case PageKey.home:
        return HomeView(state: this);
      case PageKey.reports:
        return ReportsView(state: this);
      case PageKey.profile:
        return ProfileView(state: this);
      case PageKey.skills:
        return SkillsView(state: this);
      case PageKey.reminders:
        return RemindersView(state: this);
      case PageKey.notifications:
        return NotificationsView(state: this);
    }
  }
}

class HomeView extends StatelessWidget {
  const HomeView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        HomeHeader(state: state),
        Expanded(
          child: ListView(
            controller: state.scroll,
            padding: const EdgeInsets.only(bottom: 8),
            children: [
              const AiGreeting(),
              if (state.messages.isEmpty) ...[
                HomeSection(
                  title: '金融专家',
                  action: '全部专家',
                  onAction: () => state.mutate(() => state.expertSheet = true),
                  child: ExpertGrid(state: state),
                ),
              ],
              for (final msg in state.messages)
                MessageBubble(message: msg, state: state),
            ],
          ),
        ),
        Composer(state: state),
      ],
    );
  }
}

class HomeHeader extends StatelessWidget {
  const HomeHeader({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              IconButton(
                  onPressed: () => state.mutate(() => state.drawerOpen = true),
                  icon: const Icon(Icons.menu_rounded)),
              IconButton(
                  onPressed: () => state.go(PageKey.notifications),
                  icon: const Icon(Icons.notifications_none_rounded)),
            ],
          ),
          const Column(children: [
            Text('玑衡AI',
                style: TextStyle(
                    fontFamily: 'serif',
                    fontWeight: FontWeight.w700,
                    letterSpacing: 2,
                    fontSize: 17)),
            Text('你的智能金融操作系统',
                style: TextStyle(
                    fontSize: 11, color: Color(0xFF8B9299), letterSpacing: 1)),
          ]),
        ],
      ),
    );
  }
}

class AiGreeting extends StatelessWidget {
  const AiGreeting({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const BrandAvatar(size: 36),
          const SizedBox(width: 10),
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: const BoxDecoration(
                color: C.faint,
                borderRadius: BorderRadius.only(
                    topRight: Radius.circular(14),
                    bottomLeft: Radius.circular(14),
                    bottomRight: Radius.circular(14)),
              ),
              child: const Text('已为你接入实时行情、研究数据与自动化金融 Agent，今天想做什么？',
                  style: TextStyle(fontSize: 14, height: 1.7)),
            ),
          ),
        ],
      ),
    );
  }
}

class HomeSection extends StatelessWidget {
  const HomeSection(
      {required this.title,
      required this.action,
      required this.child,
      this.onAction,
      super.key});
  final String title;
  final String action;
  final Widget child;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 4),
      child: Column(children: [
        Row(children: [
          Text(title,
              style: const TextStyle(
                  fontFamily: 'serif',
                  fontWeight: FontWeight.w700,
                  fontSize: 15)),
          const SizedBox(width: 8),
          Container(width: 14, height: 1, color: const Color(0xFFC8A173)),
          const Spacer(),
          InkWell(
            onTap: onAction,
            child: Text(action,
                style:
                    const TextStyle(color: Color(0xFF9C6B3C), fontSize: 12.5)),
          ),
        ]),
        const SizedBox(height: 10),
        child,
      ]),
    );
  }
}

const expertOptions = [
  ['会议专家', '会', '作为你的会议专家，全程协助处理一场会议从会前到会后的关键工作。', Color(0xFF1F2429)],
  ['个股研究专家', '股', '面向二级市场的个股研究搭档，围绕公司基本面、财报与事件。', Color(0xFF2F4A55)],
  ['行业研究专家', '行', '面向投研团队的行业研究搭档，围绕行业、子行业、产业链。', Color(0xFF3C5545)],
  ['财富管理专家', '财', '面向投资顾问和理财师的财富管理专业助手。', Color(0xFF8A6033)],
  ['研报专家', '研', '7×24小时追踪全市场研报，提炼核心观点与评级变化。', Color(0xFF4A4550)],
  ['舆情专家', '舆', '7×24小时监测个股与行业舆情，识别异动与情绪拐点。', Color(0xFF55483C)],
];

class ExpertGrid extends StatelessWidget {
  const ExpertGrid({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: expertOptions.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 9,
        mainAxisSpacing: 9,
        childAspectRatio: .86,
      ),
      itemBuilder: (context, index) {
        final e = expertOptions[index];
        final name = e[0] as String;
        final initial = e[1] as String;
        final color = e[3] as Color;
        final picked = state.expert == name;
        return InkWell(
          onTap: () => state.mutate(() {
            state.expert = name;
            state.mode = '金融专家团';
            state.modeSelected = true;
          }),
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
            decoration: BoxDecoration(
              color: picked ? const Color(0xFFFAF6EE) : const Color(0xFFFAF9F6),
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: picked ? const Color(0xFFE4D7C4) : C.line),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                CircleAvatar(
                  radius: 19,
                  backgroundColor: color,
                  child: Text(initial,
                      style: const TextStyle(
                          color: Colors.white,
                          fontFamily: 'serif',
                          fontSize: 16)),
                ),
                const SizedBox(height: 8),
                Text(name,
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontFamily: 'serif',
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                        height: 1.25)),
                if (picked)
                  const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text('已选择',
                        style: TextStyle(color: C.gold, fontSize: 10.5)),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class HomeCardData {
  const HomeCardData(this.title, this.desc, this.prompt, this.flow);
  final String title;
  final String desc;
  final String prompt;
  final String flow;
}

class HorizontalCards extends StatelessWidget {
  const HorizontalCards(
      {required this.cards, required this.state, this.wide = false, super.key});
  final List<HomeCardData> cards;
  final JihengShellState state;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: wide ? 130 : 106,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: cards.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) {
          final c = cards[i];
          return InkWell(
            onTap: () => state.setPrompt(c.prompt, c.flow),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              width: wide ? 244 : 196,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                  color: wide ? Colors.white : const Color(0xFFFAF9F6),
                  border: Border.all(color: C.line),
                  borderRadius: BorderRadius.circular(12)),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(c.title,
                        style: const TextStyle(
                            fontFamily: 'serif',
                            fontWeight: FontWeight.w700,
                            fontSize: 14.5)),
                    const SizedBox(height: 6),
                    Text(c.desc,
                        maxLines: wide ? 3 : 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 12, height: 1.6, color: C.muted)),
                  ]),
            ),
          );
        },
      ),
    );
  }
}

class MessageBubble extends StatelessWidget {
  const MessageBubble({required this.message, required this.state, super.key});
  final ChatMsg message;
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    if (message.isUser) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.fromLTRB(64, 10, 16, 10),
          padding: const EdgeInsets.all(13),
          decoration: BoxDecoration(
              color: C.ink, borderRadius: BorderRadius.circular(14)),
          child: Text(message.text,
              style: const TextStyle(
                  color: Colors.white, fontSize: 14, height: 1.6)),
        ),
      );
    }
    final script = scripts[message.flow] ?? scripts['generic']!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const BrandAvatar(size: 30),
        const SizedBox(width: 10),
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
                color: C.faint, borderRadius: BorderRadius.circular(14)),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (message.stage == Stage.thinking)
                const Row(children: [
                  SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2)),
                  SizedBox(width: 8),
                  Text('正在理解问题并拆解任务…', style: TextStyle(color: C.muted)),
                ]),
              if (message.stage != Stage.thinking) ...[
                Label(
                    text: script.skill
                        ? '技能调用 · ${script.tool}'
                        : '工具调用 · ${script.tool}'),
                const SizedBox(height: 10),
                Text(script.intro,
                    style: const TextStyle(fontSize: 14, height: 1.7)),
                if (message.stage == Stage.tool) ...[
                  const SizedBox(height: 12),
                  const LinearProgressIndicator(minHeight: 3),
                  const SizedBox(height: 8),
                  const Text('正在检索、取数、交叉验证…',
                      style: TextStyle(color: C.muted, fontSize: 12)),
                ],
              ],
              if (message.stage == Stage.done) ...[
                const SizedBox(height: 12),
                for (final section in script.sections) ...[
                  Text(section.title,
                      style: const TextStyle(
                          fontWeight: FontWeight.w700, fontSize: 14.5)),
                  const SizedBox(height: 6),
                  for (final item in section.items)
                    Padding(
                        padding: const EdgeInsets.only(bottom: 5),
                        child: Text('• $item',
                            style:
                                const TextStyle(height: 1.55, fontSize: 13.2))),
                  const SizedBox(height: 8),
                ],
                if (script.rows.isNotEmpty) DataTableLite(rows: script.rows),
                const SizedBox(height: 8),
                Text(script.risk,
                    style: const TextStyle(
                        color: C.muted, fontSize: 12.2, height: 1.55)),
                const SizedBox(height: 10),
                InkWell(
                  onTap: () =>
                      state.mutate(() => message.refOpen = !message.refOpen),
                  child: Text('引用 ${script.refCount} 条 · 点击查看来源',
                      style: const TextStyle(color: C.gold, fontSize: 12.5)),
                ),
                if (message.refOpen)
                  Container(
                    margin: const EdgeInsets.only(top: 8),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: C.line)),
                    child: Text('${script.ref}\n数据 · 2026-09-22',
                        style: const TextStyle(fontSize: 12, height: 1.55)),
                  ),
              ],
            ]),
          ),
        ),
      ]),
    );
  }
}

class Composer extends StatelessWidget {
  const Composer({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
      decoration: const BoxDecoration(
          color: Colors.white, border: Border(top: BorderSide(color: C.line))),
      child: Column(children: [
        if (!state.modeSelected)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              ModeChip(state: state, label: '快速问答'),
              ModeChip(state: state, label: '深度研究'),
              ModeChip(state: state, label: '金融专家团', expert: true),
            ]),
          )
        else
          Row(children: [
            Label(
                text: state.expert.isEmpty
                    ? state.mode
                    : '${state.mode} · ${state.expert}'),
            const Spacer(),
            TextButton(
                onPressed: () => state.mutate(() => state.modeSelected = false),
                child: const Text('取消')),
          ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(
            child: TextField(
              controller: state.input,
              minLines: 1,
              maxLines: 4,
              onChanged: (_) => state.mutate(() {}),
              onSubmitted: (_) => state.send(),
              decoration: InputDecoration(
                hintText: state.mode == '深度研究'
                    ? '对复杂问题进行多轮检索与推理，产出深度研究报告'
                    : '针对各类信息查询和简单问题，提供快速回答与响应',
                filled: true,
                fillColor: C.faint,
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(18),
                    borderSide: BorderSide.none),
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              ),
            ),
          ),
          const SizedBox(width: 8),
          InkWell(
            onTap: state.send,
            borderRadius: BorderRadius.circular(999),
            child: Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: state.input.text.trim().isEmpty ? Colors.white : C.ink,
                border: Border.all(
                    color: state.input.text.trim().isEmpty ? C.line : C.ink),
              ),
              child: Icon(
                  state.input.text.trim().isEmpty
                      ? Icons.add
                      : Icons.arrow_upward,
                  size: 18,
                  color:
                      state.input.text.trim().isEmpty ? C.muted : Colors.white),
            ),
          ),
        ]),
      ]),
    );
  }
}

class ModeChip extends StatelessWidget {
  const ModeChip(
      {required this.state,
      required this.label,
      this.expert = false,
      super.key});
  final JihengShellState state;
  final String label;
  final bool expert;

  @override
  Widget build(BuildContext context) {
    final selected = state.mode == label;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) {
          if (expert) {
            state.mutate(() => state.expertSheet = true);
          } else {
            state.mutate(() {
              state.mode = label;
              state.modeSelected = true;
            });
          }
        },
        selectedColor: C.goldSoft,
        backgroundColor: C.faint,
        labelStyle:
            TextStyle(color: selected ? C.gold : const Color(0xFF4A5259)),
      ),
    );
  }
}

class ReportsView extends StatelessWidget {
  const ReportsView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final reports = [
      [
        '本周',
        '深度研究',
        '09-22 14:20',
        '已完成',
        '创新药板块上涨驱动因素与配置窗口研究',
        '政策、业绩、BD 出海三条主线梳理，附板块估值分位与重点公司盈利预测。',
        '18 页 · 引用 22 条'
      ],
      [
        '本周',
        '公司研究',
        '09-21 09:05',
        '已完成',
        '美的集团（000333.SZ）创新高后的回调复盘',
        '海外 OBM 占比提升与 KUKA 减亏节奏跟踪，短期获利了结压力测算。',
        '12 页 · 引用 15 条'
      ],
      [
        '本周',
        '晨报',
        '09-20 07:30',
        '已发送',
        '9月20日 玑衡晨报：算力链订单兑现节奏',
        'CoWoS 满载、液冷订单放量，关注中报业绩兑现与国产替代节奏。',
        '6 页 · 引用 9 条'
      ],
      [
        '更早',
        '宏观研究',
        '09-12 16:40',
        '已完成',
        '8000亿元新型政策性金融工具规模测算',
        '母子基金结构下的杠杆撬动测算，四季度基建投资拉动弹性推演。',
        '15 页 · 引用 12 条'
      ],
      [
        '更早',
        '大宗商品',
        '09-05 11:12',
        '草稿',
        '伦敦金银比历史分位与均值回归分析',
        '金银比 82.3 处近十年 78% 分位，白银补涨弹性情景分析。',
        '9 页 · 引用 9 条'
      ],
    ].where((r) => state.reportTab == '全部' || r[1] == state.reportTab).toList();
    return SubPage(
      title: '我的报告',
      state: state,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(
            spacing: 8,
            children: ['全部', '深度研究', '公司研究', '晨报']
                .map((t) => ChoiceChip(
                    label: Text(t),
                    selected: state.reportTab == t,
                    onSelected: (_) => state.mutate(() => state.reportTab = t)))
                .toList()),
        const SizedBox(height: 14),
        for (final r in reports)
          CardTile(
              title: r[4],
              subtitle: '${r[1]} · ${r[2]} · ${r[3]}\n${r[5]}\n${r[6]}',
              trailing: '导出',
              onTap: () => state.snack('已打开报告详情 · mock')),
      ]),
    );
  }
}

class SkillsView extends StatelessWidget {
  const SkillsView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final official = [
      ['有色板块深度透视', '有色金属板块深度分析，采用通用框架+品种插件模型。'],
      ['贵金属板块深度透视', '用于黄金、白银、铂、钯的行情快评、日报、走势复盘。'],
      ['期货主力行为分析', '基于交易所公开的期货公司席位数据分析主力行为。'],
      ['基金涨跌解读', '帮助客户看懂某只基金或ETF在一段时间内为什么上涨或下跌。'],
      ['期货资金流向监测', '基于国内商品期货品种持仓额变化，监测全市场与板块资金流。'],
      ['期权波动率洞察', '期权波动率数据诊断与市场扫描技能，分析 IV 估值。'],
      ['期权定价计算器', '期权与结构化期权产品理论定价技能。'],
      ['机构持仓透视', '查看巴菲特、桥水、易方达等顶级机构最新买了什么。'],
      ['期货盘中异动归因', '用于商品期货盘中异动归因与市场扫描。'],
    ];
    final mine = [
      ['组合周度复盘', '按持仓权重拆解本周组合收益来源，输出归因表与调仓建议。'],
      ['客户晨会纪要', '把晨会语音转写整理成结构化纪要，自动提取观点与待办。'],
      ['行业景气打分卡', '按自定义指标体系给跟踪行业打分，生成景气趋势对比表。'],
    ];
    final rows = state.skillTab == '我创建的'
        ? mine
        : state.skillTab == '官方技能'
            ? official
            : [...official, ...mine]
                .where((r) => !state.disabledSkills.contains(r[0]))
                .toList();
    return SubPage(
      title: '技能广场',
      state: state,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(
            spacing: 8,
            children: ['已开启的', '我创建的', '官方技能']
                .map((t) => ChoiceChip(
                    label: Text(t),
                    selected: state.skillTab == t,
                    onSelected: (_) => state.mutate(() => state.skillTab = t)))
                .toList()),
        const SizedBox(height: 10),
        Text(
            state.skillTab == '我创建的'
                ? '${rows.length} 个自建技能'
                : state.skillTab == '官方技能'
                    ? '${rows.length} / 36 个官方技能'
                    : '${rows.length} 个技能已开启',
            style: const TextStyle(color: C.muted)),
        const SizedBox(height: 12),
        for (final r in rows)
          CardTile(
            title: r[0],
            subtitle: r[1],
            trailing: state.disabledSkills.contains(r[0]) ? '已关' : '已开',
            onTap: () => state.mutate(() => state.disabledSkills.contains(r[0])
                ? state.disabledSkills.remove(r[0])
                : state.disabledSkills.add(r[0])),
          ),
      ]),
    );
  }
}

class RemindersView extends StatelessWidget {
  const RemindersView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    return SubPage(
      title: '定时与提醒',
      state: state,
      action: IconButton(
        onPressed: () => state.mutate(() {
          state.reminders.insert(0, '每周一 08:30 自动重跑高研发低估值筛选');
          state.snack('已新增提醒');
        }),
        icon: const Icon(Icons.add),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Text('定时任务',
            style: TextStyle(
                fontFamily: 'serif',
                fontWeight: FontWeight.w700,
                fontSize: 17)),
        const Text('管理你的自动化任务',
            style: TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 24),
        const Center(child: Text('暂无定时任务', style: TextStyle(color: C.muted))),
        const SizedBox(height: 6),
        const Center(
            child: Text('创建后可在这里查看和管理自动执行的任务',
                style: TextStyle(color: Color(0xFFADB4BA), fontSize: 12.5))),
        const SizedBox(height: 30),
        const Divider(height: 28),
        const Text('提醒任务',
            style: TextStyle(
                fontFamily: 'serif',
                fontWeight: FontWeight.w700,
                fontSize: 17)),
        const Text('展示满足条件后自动触发的提醒任务',
            style: TextStyle(color: C.muted, fontSize: 12.5)),
        const SizedBox(height: 16),
        for (final r in state.reminders)
          CardTile(
              title: r,
              subtitle: '通过对话自动创建提醒订阅任务，满足条件后会在这里展示',
              trailing: '开启',
              onTap: () => state.snack('提醒状态已切换 · mock'))
      ]),
    );
  }
}

class NotificationsView extends StatelessWidget {
  const NotificationsView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    return SubPage(
      title: '通知中心',
      state: state,
      child: Column(children: [
        for (final n in state.notifications)
          CardTile(
              title: n,
              subtitle: '任务记录 · 刚刚',
              trailing: '查看',
              onTap: () => state.go(PageKey.reports)),
        for (final a in state.activity.take(5))
          CardTile(
              title: a,
              subtitle: '本次会话动态',
              trailing: '›',
              onTap: () => state.go(PageKey.home)),
      ]),
    );
  }
}

class ProfileView extends StatelessWidget {
  const ProfileView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    return SubPage(
      title: '个人中心',
      state: state,
      child: Column(children: [
        const Row(children: [
          CircleAvatar(
              radius: 26,
              backgroundColor: C.ink,
              child: Text('陈', style: TextStyle(color: Color(0xFFD8B483)))),
          SizedBox(width: 12),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('USER_6450',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
            Text('机构版 · 研究部', style: TextStyle(color: C.muted, fontSize: 12)),
          ]),
        ]),
        const SizedBox(height: 20),
        const Row(children: [
          Expanded(child: StatBox(value: '24', label: '生成报告')),
          SizedBox(width: 10),
          Expanded(child: StatBox(value: '9', label: '启用技能')),
          SizedBox(width: 10),
          Expanded(child: StatBox(value: '146', label: '使用天数')),
        ]),
        const SizedBox(height: 18),
        for (final row in [
          '账号与安全 · 已绑定手机',
          '订阅与积分 · 机构版 · 8,420 分',
          '数据权限 · 行情 / 研报 / 财报',
          '消息通知 · 已开启',
          '偏好设置 · 简体中文',
          '关于玑衡AI · v2.4.1'
        ])
          CardTile(
              title: row,
              subtitle: '点击设置',
              trailing: '›',
              onTap: () => state.snack('$row · mock')),
      ]),
    );
  }
}

class SubPage extends StatelessWidget {
  const SubPage(
      {required this.title,
      required this.state,
      required this.child,
      this.action,
      super.key});
  final String title;
  final JihengShellState state;
  final Widget child;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(8, 4, 12, 8),
        child: Row(children: [
          IconButton(
              onPressed: () => state.go(PageKey.home),
              icon: const Icon(Icons.chevron_left)),
          Expanded(
              child: Text(title,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 17))),
          SizedBox(width: 44, child: action),
        ]),
      ),
      Expanded(
          child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), child: child)),
    ]);
  }
}

class DrawerOverlay extends StatelessWidget {
  const DrawerOverlay({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final items = [
      ['新建对话', PageKey.home, Icons.chat_bubble_outline],
      ['我的报告', PageKey.reports, Icons.description_outlined],
      ['技能广场', PageKey.skills, Icons.auto_awesome],
      ['定时与提醒', PageKey.reminders, Icons.schedule],
    ];
    return Stack(children: [
      Positioned.fill(
          child: GestureDetector(
              onTap: () => state.mutate(() => state.drawerOpen = false),
              child: Container(color: const Color(0x55000000)))),
      Align(
        alignment: Alignment.centerLeft,
        child: Container(
          width: MediaQuery.of(context).size.width * .82,
          height: double.infinity,
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(20, 54, 20, 18),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('玑衡AI',
                style: TextStyle(
                    fontFamily: 'serif',
                    fontWeight: FontWeight.w700,
                    fontSize: 22)),
            const SizedBox(height: 24),
            for (final item in items)
              ListTile(
                  leading: Icon(item[2] as IconData),
                  title: Text(item[0] as String),
                  onTap: () => state.go(item[1] as PageKey)),
            const Divider(),
            const Text('最近对话', style: TextStyle(color: C.muted)),
            TextButton(
                onPressed: () => state.go(PageKey.home),
                child: const Text('金融AI助手自我介绍')),
            TextButton(
                onPressed: () {
                  state.setPrompt('做一份宁德时代三季报前瞻', 'generic');
                  state.go(PageKey.home);
                },
                child: const Text('做一份宁德时代三季报前瞻…')),
            const Spacer(),
            ListTile(
              leading: const CircleAvatar(
                  backgroundColor: C.ink,
                  child: Text('用', style: TextStyle(color: Color(0xFFD8B483)))),
              title: const Text('USER_6450'),
              subtitle: const Text('机构版 · 研究部'),
              onTap: () => state.go(PageKey.profile),
            ),
          ]),
        ),
      ),
    ]);
  }
}

class ExpertSheet extends StatelessWidget {
  const ExpertSheet({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final experts = [
      ['会议专家', '会', '全程协助处理会前到会后的关键工作'],
      ['个股研究专家', '股', '围绕公司基本面、财报与事件进行研究'],
      ['行业研究专家', '行', '围绕行业、子行业、产业链环节分析'],
      ['财富管理专家', '财', '覆盖客户洞察、产品匹配与沟通话术'],
      ['研报专家', '研', '追踪全市场研报，提炼核心观点'],
      ['舆情专家', '舆', '监测个股与行业舆情，识别情绪拐点'],
    ];
    return Stack(children: [
      Positioned.fill(
          child: GestureDetector(
              onTap: () => state.mutate(() => state.expertSheet = false),
              child: Container(color: const Color(0x55000000)))),
      Align(
        alignment: Alignment.bottomCenter,
        child: Container(
          constraints: const BoxConstraints(maxHeight: 560),
          decoration: const BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 12, 8),
              child: Row(children: [
                const Text('选择金融专家',
                    style:
                        TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
                const Spacer(),
                IconButton(
                    onPressed: () =>
                        state.mutate(() => state.expertSheet = false),
                    icon: const Icon(Icons.close)),
              ]),
            ),
            Expanded(
              child: ListView(
                children: experts
                    .map((e) => ListTile(
                          leading: CircleAvatar(
                              backgroundColor: C.ink,
                              child: Text(e[1],
                                  style: const TextStyle(
                                      color: Color(0xFFD8B483)))),
                          title: Text(e[0]),
                          subtitle: Text(e[2]),
                          trailing: state.expert == e[0]
                              ? const Icon(Icons.check, color: C.green)
                              : null,
                          onTap: () => state.mutate(() {
                            state.expert = e[0];
                            state.mode = '金融专家团';
                            state.modeSelected = true;
                            state.expertSheet = false;
                          }),
                        ))
                    .toList(),
              ),
            ),
          ]),
        ),
      ),
    ]);
  }
}

class BrandAvatar extends StatelessWidget {
  const BrandAvatar({required this.size, super.key});
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: const BoxDecoration(shape: BoxShape.circle, color: C.ink),
      child: Text('玑',
          style: TextStyle(
              color: const Color(0xFFD8B483),
              fontFamily: 'serif',
              fontSize: size * .45)),
    );
  }
}

class Label extends StatelessWidget {
  const Label({required this.text, super.key});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
          color: C.goldSoft, borderRadius: BorderRadius.circular(3)),
      child: Text(text,
          style: const TextStyle(
              fontSize: 11, color: C.gold, fontWeight: FontWeight.w600)),
    );
  }
}

class DataTableLite extends StatelessWidget {
  const DataTableLite({required this.rows, super.key});
  final List<List<String>> rows;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: C.line)),
      child: Column(
          children: rows
              .map((r) => Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    child: Row(children: [
                      Expanded(
                          child: Text(r[0],
                              style: const TextStyle(
                                  fontSize: 12, color: C.muted))),
                      Expanded(
                          child: Text(r[1],
                              textAlign: TextAlign.right,
                              style: const TextStyle(fontSize: 12))),
                    ]),
                  ))
              .toList()),
    );
  }
}

class CardTile extends StatelessWidget {
  const CardTile(
      {required this.title,
      required this.subtitle,
      required this.trailing,
      this.onTap,
      super.key});
  final String title;
  final String subtitle;
  final String trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: C.line)),
      child: ListTile(
          onTap: onTap,
          title: Text(title,
              style:
                  const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
          subtitle:
              Text(subtitle, maxLines: 2, overflow: TextOverflow.ellipsis),
          trailing: Text(trailing, style: const TextStyle(color: C.gold))),
    );
  }
}

class StatBox extends StatelessWidget {
  const StatBox({required this.value, required this.label, super.key});
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14),
      decoration: BoxDecoration(
          color: C.faint, borderRadius: BorderRadius.circular(12)),
      child: Column(children: [
        Text(value,
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 20)),
        Text(label, style: const TextStyle(color: C.muted, fontSize: 12)),
      ]),
    );
  }
}
