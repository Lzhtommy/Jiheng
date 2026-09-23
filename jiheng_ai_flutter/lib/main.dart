import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

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
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context).copyWith(textScaler: TextScaler.noScaling),
        child: child ?? const SizedBox.shrink(),
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
  String tool = '';
  String intro = '';
  String risk = '';
  String ref = '';
  String stageNote = '';
  int refCount = 0;
  bool skill = false;
  final List<SectionData> sections = [];
  final List<List<String>> rows = [];
}

class ApiClient {
  ApiClient();

  static const javaBase = String.fromEnvironment(
    'JIHENG_JAVA_BASE_URL',
    defaultValue: 'http://192.168.184.207',
  );
  static const agentBase = String.fromEnvironment(
    'JIHENG_AGENT_BASE_URL',
    defaultValue: 'http://192.168.184.207',
  );

  final storage = const FlutterSecureStorage();
  String? accessToken;
  String? refreshToken;
  String? userId;

  Future<void> loadTokens() async {
    try {
      accessToken = await storage
          .read(key: 'accessToken')
          .timeout(const Duration(milliseconds: 250));
      refreshToken = await storage
          .read(key: 'refreshToken')
          .timeout(const Duration(milliseconds: 250));
      userId = await storage
          .read(key: 'userId')
          .timeout(const Duration(milliseconds: 250));
    } on MissingPluginException {
      accessToken = null;
      refreshToken = null;
      userId = null;
    } on TimeoutException {
      accessToken = null;
      refreshToken = null;
      userId = null;
    }
  }

  Future<void> saveTokens(Map<String, dynamic> data) async {
    accessToken = data['accessToken']?.toString();
    refreshToken = data['refreshToken']?.toString();
    userId = data['userId']?.toString();
    try {
      if (accessToken != null) {
        await storage.write(key: 'accessToken', value: accessToken);
      }
      if (refreshToken != null) {
        await storage.write(key: 'refreshToken', value: refreshToken);
      }
      if (userId != null) {
        await storage.write(key: 'userId', value: userId);
      }
    } on MissingPluginException {
      // Widget tests and unsupported platforms can still run with in-memory auth.
    }
  }

  Future<void> clearTokens() async {
    accessToken = null;
    refreshToken = null;
    userId = null;
    try {
      await storage.deleteAll();
    } on MissingPluginException {
      // Ignore local mock storage failures.
    }
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (accessToken != null && accessToken!.isNotEmpty)
          'Authorization': 'Bearer $accessToken',
      };

  dynamic _unwrap(http.Response response) {
    final text = utf8.decode(response.bodyBytes);
    final decoded = text.isEmpty ? null : jsonDecode(text);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(decoded is Map && decoded['message'] != null
          ? decoded['message']
          : 'HTTP ${response.statusCode}');
    }
    if (decoded is Map<String, dynamic> && decoded.containsKey('data')) {
      return decoded['data'];
    }
    return decoded;
  }

  Future<dynamic> get(String path) async {
    final response =
        await http.get(Uri.parse('$javaBase$path'), headers: _headers);
    return _unwrap(response);
  }

  Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final response = await http.post(Uri.parse('$javaBase$path'),
        headers: _headers, body: jsonEncode(body));
    return _unwrap(response);
  }

  Future<dynamic> put(String path, Map<String, dynamic> body) async {
    final response = await http.put(Uri.parse('$javaBase$path'),
        headers: _headers, body: jsonEncode(body));
    return _unwrap(response);
  }

  Future<dynamic> delete(String path) async {
    final response =
        await http.delete(Uri.parse('$javaBase$path'), headers: _headers);
    return _unwrap(response);
  }

  Future<dynamic> agentPost(String path, Map<String, dynamic> body) async {
    final response = await http.post(Uri.parse('$agentBase$path'),
        headers: _headers, body: jsonEncode(body));
    if (response.statusCode == 202) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    }
    return _unwrap(response);
  }

  Stream<Map<String, dynamic>> streamChat(Map<String, dynamic> body) async* {
    final request = http.Request('POST', Uri.parse('$agentBase/chat/stream'));
    request.headers.addAll({
      ..._headers,
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
    });
    request.body = jsonEncode(body);
    final response = await request.send();
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('SSE HTTP ${response.statusCode}');
    }

    var event = 'message';
    final data = StringBuffer();
    await for (final line in response.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter())) {
      if (line.isEmpty) {
        if (data.isNotEmpty) {
          final raw = data.toString();
          final parsed = jsonDecode(raw);
          if (parsed is Map<String, dynamic>) {
            yield {'event': event, ...parsed};
          } else {
            yield {'event': event, 'data': parsed};
          }
          data.clear();
          event = 'message';
        }
        continue;
      }
      if (line.startsWith('event:')) {
        event = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        if (data.isNotEmpty) data.write('\n');
        data.write(line.substring(5).trim());
      }
    }
  }
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
  final api = ApiClient();
  PageKey page = PageKey.home;
  final input = TextEditingController();
  final scroll = ScrollController();
  final List<ChatMsg> messages = [];
  final Set<String> disabledSkills = {
    '有色板块深度透视',
    '贵金属板块深度透视',
    '期货主力行为分析',
    '基金涨跌解读',
    '期货资金流向监测',
    '期权波动率洞察',
  };
  final List<String> reminders = [];
  final List<String> notifications = [];
  final List<String> activity = ['影石创新：影像硬件出海'];
  String flow = 'generic';
  String mode = '快速问答';
  String reportTab = '全部';
  String skillTab = '已开启的';
  String skillQuery = '';
  String expert = '';
  String selectedExpertId = '';
  String? apiError;
  Map<String, dynamic>? profile;
  List<Map<String, dynamic>> apiExperts = [];
  List<Map<String, dynamic>> apiSkills = [];
  List<Map<String, dynamic>> customSkills = [];
  final List<Map<String, dynamic>> localCustomSkills = [];
  List<Map<String, dynamic>> apiReports = [];
  List<Map<String, dynamic>> apiNotifications = [];
  List<Map<String, dynamic>> apiTasks = [];
  final List<Map<String, dynamic>> localTasks = [];
  final Set<String> favorites = {};
  bool drawerOpen = false;
  bool expertSheet = false;
  bool modeSelected = false;
  bool authReady = false;
  bool isLoggedIn = false;
  bool loadingData = false;
  bool sending = false;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  @override
  void dispose() {
    input.dispose();
    scroll.dispose();
    super.dispose();
  }

  Future<void> _bootstrap() async {
    await api.loadTokens();
    if (!mounted) return;
    setState(() {
      isLoggedIn = api.accessToken != null && api.accessToken!.isNotEmpty;
      authReady = true;
    });
    if (isLoggedIn) {
      await loadRemoteData();
    }
  }

  Future<void> login({
    required String phone,
    required String smsCode,
    required String captchaCode,
    required String captchaId,
  }) async {
    final data = await api.post('/api/v1/auth/login', {
      'phone': phone,
      'smsCode': smsCode,
      'captchaCode': captchaCode,
      'captchaId': captchaId,
    });
    await api.saveTokens(Map<String, dynamic>.from(data as Map));
    if (!mounted) return;
    setState(() {
      isLoggedIn = true;
      apiError = null;
    });
    await loadRemoteData();
  }

  Future<Map<String, dynamic>?> loadCaptcha() async {
    try {
      final data = await api.get('/api/v1/auth/captcha');
      return Map<String, dynamic>.from(data as Map);
    } catch (_) {
      return null;
    }
  }

  Future<void> sendSms(
      String phone, String captchaCode, String captchaId) async {
    await api.post('/api/v1/auth/sms', {
      'phone': phone,
      'captchaCode': captchaCode,
      'captchaId': captchaId,
    });
  }

  Future<void> logout() async {
    try {
      await api.post('/api/v1/auth/logout', {});
    } catch (_) {
      // Local logout should still work if the server is unavailable.
    }
    await api.clearTokens();
    if (!mounted) return;
    setState(() {
      isLoggedIn = false;
      profile = null;
      messages.clear();
    });
  }

  Future<void> loadRemoteData() async {
    setState(() {
      loadingData = true;
      apiError = null;
    });
    await Future.wait([
      _loadExperts(),
      _loadSkills(),
      _loadReports(),
      _loadNotifications(),
      _loadProfile(),
      _loadTasks(),
    ]);
    if (!mounted) return;
    setState(() => loadingData = false);
  }

  Future<void> _loadExperts() async {
    try {
      final data = await api.get('/api/v1/config/experts');
      final experts = (data['experts'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (mounted) setState(() => apiExperts = experts);
    } catch (e) {
      _rememberApiError(e);
    }
  }

  Future<void> _loadSkills() async {
    try {
      final data = await api.get('/api/v1/config/skills');
      final official = (data['skills'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      final mineData = await api.get('/api/v1/skills/custom');
      final mine = (mineData as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (mounted) {
        setState(() {
          apiSkills = official;
          customSkills = mine;
        });
      }
    } catch (e) {
      _rememberApiError(e);
    }
  }

  Future<void> _loadReports() async {
    try {
      final data = await api.get('/api/v1/reports');
      final rows = (data as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (mounted) setState(() => apiReports = rows);
    } catch (e) {
      _rememberApiError(e);
    }
  }

  Future<void> _loadNotifications() async {
    try {
      final data = await api.get('/api/v1/notifications');
      final rows = (data as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (mounted) setState(() => apiNotifications = rows);
    } catch (e) {
      _rememberApiError(e);
    }
  }

  Future<void> _loadProfile() async {
    try {
      final data = await api.get('/api/v1/profile');
      if (mounted) {
        setState(() => profile = Map<String, dynamic>.from(data as Map));
      }
    } catch (e) {
      _rememberApiError(e);
    }
  }

  Future<void> _loadTasks() async {
    try {
      final data = await api.get('/api/v1/tasks');
      final rows = (data as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (mounted) setState(() => apiTasks = rows);
    } catch (e) {
      _rememberApiError(e);
    }
  }

  void _rememberApiError(Object error) {
    if (!mounted) return;
    setState(() => apiError ??= error.toString());
  }

  Future<void> openReport(Map<String, dynamic> report) async {
    Map<String, dynamic> detail = report;
    final reportId = asText(report['reportId'] ?? report['report_id']);
    if (reportId.isNotEmpty && isLoggedIn) {
      try {
        final data = await api.get('/api/v1/reports/$reportId');
        detail = Map<String, dynamic>.from(data as Map);
      } catch (e) {
        _rememberApiError(e);
      }
    }
    if (!mounted) return;
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => ReportDetailPage(report: detail),
    ));
  }

  Future<void> exportReport(Map<String, dynamic> report) async {
    final reportId = asText(report['reportId'] ?? report['report_id']);
    if (reportId.isEmpty || !isLoggedIn) {
      snack('导出处理中 · mock');
      return;
    }
    try {
      final data =
          await api.post('/api/v1/reports/$reportId/export', {'format': 'pdf'});
      snack('导出任务已创建：${data['task_id'] ?? 'mock'}');
    } catch (e) {
      _rememberApiError(e);
      snack('导出处理中 · mock');
    }
  }

  Future<void> toggleSkill(Map<String, dynamic> skill) async {
    final name = asText(skill['name']);
    final id = skill['id'];
    final currentlyOff = disabledSkills.contains(name);
    setState(() {
      if (currentlyOff) {
        disabledSkills.remove(name);
      } else {
        disabledSkills.add(name);
      }
    });
    if (id != null && isLoggedIn) {
      try {
        await api.put('/api/v1/skills/$id/enabled', {'enabled': currentlyOff});
      } catch (e) {
        _rememberApiError(e);
      }
    }
  }

  Future<void> createTaskMock() async {
    final task = <String, dynamic>{
      'taskId': 'local-${DateTime.now().millisecondsSinceEpoch}',
      'type': 'reminder',
      'status': 'enabled',
      'title': '每周一 08:30 自动重跑高研发低估值筛选',
    };
    try {
      if (isLoggedIn) {
        final data = await api.post('/api/v1/tasks', {
          'type': task['type'],
          'cron': '0 30 8 ? * MON',
          'payload': jsonEncode(task),
        });
        if (data is Map) task.addAll(Map<String, dynamic>.from(data));
      }
    } catch (e) {
      _rememberApiError(e);
    }
    setState(() {
      localTasks.insert(0, task);
      reminders.insert(0, asText(task['title']));
    });
    snack('已创建 mock 任务');
  }

  void go(PageKey next) {
    setState(() {
      page = next;
      drawerOpen = false;
    });
    if (isLoggedIn) {
      if (next == PageKey.reports) _loadReports();
      if (next == PageKey.skills) _loadSkills();
      if (next == PageKey.notifications) _loadNotifications();
      if (next == PageKey.profile) _loadProfile();
      if (next == PageKey.reminders) _loadTasks();
    }
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

  Future<void> send() async {
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
      sending = true;
    });
    _scrollDown();
    if (isLoggedIn) {
      try {
        if (mode == '深度研究') {
          final data =
              await api.agentPost('/chat/deep-research', _chatBody(text));
          final taskId = data['task_id']?.toString() ??
              'local-${DateTime.now().millisecondsSinceEpoch}';
          setState(() {
            ai.stage = Stage.done;
            ai.tool = '深度研究';
            ai.intro = '深度研究任务已转入后台执行。';
            ai.sections.add(
                SectionData('后台任务', ['任务 ID：$taskId', '完成后会在通知中心或我的报告中展示。']));
            ai.risk = '内容由 AI 生成，请核查重要信息。';
            localTasks.insert(0, {
              'taskId': taskId,
              'type': 'deep_research',
              'status': 'running'
            });
            sending = false;
          });
          _scrollDown();
          return;
        }
        await for (final event in api.streamChat(_chatBody(text))) {
          if (!mounted) return;
          _applySseEvent(ai, event);
          _scrollDown();
        }
        if (mounted) setState(() => sending = false);
        return;
      } catch (e) {
        _rememberApiError(e);
      }
    }
    Timer(const Duration(milliseconds: 700), () {
      if (!mounted) return;
      setState(() => ai.stage = Stage.tool);
      _scrollDown();
    });
    Timer(const Duration(milliseconds: 1700), () {
      if (!mounted) return;
      setState(() {
        ai.stage = Stage.done;
        sending = false;
      });
      _scrollDown();
    });
  }

  Map<String, dynamic> _chatBody(String text) {
    return {
      'mode': mode == '深度研究'
          ? 'deep'
          : mode == '金融专家团'
              ? 'expert'
              : 'quick',
      'expert': mode == '金融专家团' ? selectedExpertId : null,
      'conversation_id':
          'mobile-${api.userId ?? 'guest'}-${DateTime.now().microsecondsSinceEpoch}',
      'messages': [
        {
          'role': 'user',
          'content': text,
          'created_at': DateTime.now().toIso8601String()
        }
      ],
    };
  }

  void _applySseEvent(ChatMsg ai, Map<String, dynamic> event) {
    setState(() {
      final name = event['event']?.toString() ?? '';
      if (name.contains('error') || event['code'] != null) {
        ai.stage = Stage.done;
        if (ai.intro.isNotEmpty || ai.sections.isNotEmpty) {
          if (ai.risk.isEmpty) {
            ai.risk = event['message']?.toString() ?? '内容由 AI 生成，请核查重要信息。';
          }
          sending = false;
          return;
        }
        ai.intro = '服务暂时不可用，已切换为本地演示回复。';
        ai.sections.add(const SectionData('错误信息', ['请稍后重试，或检查后端服务地址与登录状态。']));
        ai.risk = event['message']?.toString() ?? '内容由 AI 生成，请核查重要信息。';
        sending = false;
        return;
      }
      if (name.contains('tool') || event['tool_name'] != null) {
        ai.stage = Stage.tool;
        ai.tool = event['tool_name']?.toString() ?? ai.tool;
        ai.stageNote = event['tool_input']?.toString() ??
            event['tool_result']?.toString() ??
            '正在检索、取数、交叉验证…';
        ai.skill = event['is_skill'] == true;
      }
      if (event['intro'] != null) {
        ai.stage = Stage.tool;
        ai.intro = event['intro'].toString();
      }
      if (event['content'] != null) {
        ai.stage = Stage.tool;
        final chunk = event['content'].toString();
        ai.intro = ai.intro.isEmpty ? chunk : '${ai.intro}$chunk';
      }
      if (event['title'] != null ||
          event['items'] != null ||
          event['para'] != null) {
        final items =
            (event['items'] as List? ?? []).map((e) => e.toString()).toList();
        final para = event['para']?.toString();
        ai.sections.add(SectionData(
          event['title']?.toString() ?? '分析结果',
          para == null || para.isEmpty ? items : [para, ...items],
        ));
      }
      if (event['table_rows'] is List) {
        ai.rows
          ..clear()
          ..addAll((event['table_rows'] as List).map((row) {
            final cells = row is List ? row : [row.toString(), ''];
            return [
              cells.isNotEmpty ? cells[0].toString() : '',
              cells.length > 1 ? cells[1].toString() : '',
            ];
          }));
      }
      if (event['risk'] != null) ai.risk = event['risk'].toString();
      if (event['ref_count'] != null) {
        ai.refCount = int.tryParse(event['ref_count'].toString()) ?? 0;
      }
      if (event['refs'] is List && (event['refs'] as List).isNotEmpty) {
        final first =
            Map<String, dynamic>.from((event['refs'] as List).first as Map);
        ai.ref = first['title']?.toString() ?? first.toString();
      }
      if (name.contains('done')) {
        ai.stage = Stage.done;
        if (ai.intro.isEmpty) ai.intro = '已完成分析。';
        if (ai.risk.isEmpty) ai.risk = '内容由 AI 生成，请核查重要信息。';
        sending = false;
      }
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
    if (!authReady) {
      return const Scaffold(
        backgroundColor: C.paper,
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (!isLoggedIn) {
      return LoginView(state: this);
    }
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

class LoginView extends StatefulWidget {
  const LoginView({required this.state, super.key});
  final JihengShellState state;

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final phone = TextEditingController(text: '15611437032');
  final sms = TextEditingController();
  final captcha = TextEditingController();
  String captchaId = '';
  String captchaImage = '';
  bool loading = false;
  String error = '';

  @override
  void initState() {
    super.initState();
    _loadCaptcha();
  }

  @override
  void dispose() {
    phone.dispose();
    sms.dispose();
    captcha.dispose();
    super.dispose();
  }

  Future<void> _loadCaptcha({bool clearInput = false}) async {
    final data = await widget.state.loadCaptcha();
    if (!mounted || data == null) return;
    setState(() {
      captchaId = data['captchaId']?.toString() ?? '';
      captchaImage = data['captchaImage']?.toString() ?? '';
      if (clearInput) captcha.clear();
    });
  }

  Uint8List? _captchaBytes() {
    if (!captchaImage.startsWith('data:image')) return null;
    final comma = captchaImage.indexOf(',');
    if (comma < 0) return null;
    try {
      return base64Decode(captchaImage.substring(comma + 1));
    } catch (_) {
      return null;
    }
  }

  Future<void> _sendSms() async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      await widget.state
          .sendSms(phone.text.trim(), captcha.text.trim(), captchaId);
      sms.text = '000000';
      await _loadCaptcha(clearInput: true);
      if (mounted) widget.state.snack('已填入默认短信验证码 000000');
    } catch (e) {
      setState(() => error = '短信发送失败：$e');
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void _enterDemoMode([String? reason]) {
    widget.state.mutate(() {
      widget.state.isLoggedIn = true;
      widget.state.apiError = reason ?? '当前使用本地演示模式，未连接真实登录。';
    });
  }

  Future<void> _login() async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      await widget.state.login(
        phone: phone.text.trim(),
        smsCode: sms.text.trim(),
        captchaCode: captcha.text.trim(),
        captchaId: captchaId,
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => error = '登录失败：$e');
      await _loadCaptcha();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final compact = size.height < 780;
    final captchaBytes = _captchaBytes();
    return Scaffold(
      backgroundColor: const Color(0xFFFBFAF7),
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(
              child: CustomPaint(painter: LoginWavePainter()),
            ),
            ListView(
              padding: EdgeInsets.fromLTRB(20, compact ? 12 : 18, 20, 18),
              children: [
                SizedBox(height: compact ? 6 : 10),
                Center(
                  child: Container(
                    width: compact ? 58 : 64,
                    height: compact ? 58 : 64,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: C.ink,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: .12),
                          blurRadius: 24,
                          offset: const Offset(0, 12),
                        )
                      ],
                    ),
                    child: const Text('玑',
                        style: TextStyle(
                            color: Color(0xFFD8B483),
                            fontFamily: 'serif',
                            fontSize: 30,
                            fontWeight: FontWeight.w600)),
                  ),
                ),
                SizedBox(height: compact ? 14 : 18),
                const Text('玑衡AI',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        fontFamily: 'serif',
                        fontWeight: FontWeight.w800,
                        fontSize: 31,
                        height: 1.1,
                        color: C.text)),
                const SizedBox(height: 9),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(width: 36, height: 1, color: C.line),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 11),
                      child: Text('你的智能金融操作系统',
                          style: TextStyle(
                              color: C.muted, fontSize: 13, letterSpacing: 2)),
                    ),
                    Container(width: 36, height: 1, color: C.line),
                  ],
                ),
                const SizedBox(height: 14),
                Center(
                    child: Container(
                        width: 44,
                        height: 4,
                        decoration: BoxDecoration(
                            color: const Color(0xFFC8A173),
                            borderRadius: BorderRadius.circular(99)))),
                SizedBox(height: compact ? 24 : 32),
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 374),
                    child: Container(
                      padding: EdgeInsets.fromLTRB(
                          16, compact ? 20 : 22, 16, compact ? 20 : 24),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: .92),
                        borderRadius: BorderRadius.circular(22),
                        border: Border.all(color: C.line),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: .055),
                            blurRadius: 34,
                            offset: const Offset(0, 18),
                          )
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Text('手机号',
                              style: TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 16,
                                  color: C.text)),
                          const SizedBox(height: 10),
                          LoginInput(
                            controller: phone,
                            hint: '请输入手机号',
                            icon: Icons.phone_android_rounded,
                            keyboardType: TextInputType.phone,
                          ),
                          SizedBox(height: compact ? 18 : 20),
                          const Text('图形验证码',
                              style: TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 16,
                                  color: C.text)),
                          const SizedBox(height: 10),
                          Row(children: [
                            Flexible(
                              flex: 10,
                              child: LoginInput(
                                controller: captcha,
                                hint: '请输入图形验证码',
                                compactHint: true,
                                icon: Icons.verified_user_outlined,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              width: 110,
                              height: 48,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: const Color(0xFFFAF8F3),
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: C.line),
                              ),
                              child: captchaBytes == null
                                  ? const Text(
                                      '7F3K',
                                      style: TextStyle(
                                          fontFamily: 'serif',
                                          color: C.gold,
                                          fontSize: 22,
                                          letterSpacing: 3,
                                          fontWeight: FontWeight.w700),
                                    )
                                  : ClipRRect(
                                      borderRadius: BorderRadius.circular(12),
                                      child: Image.memory(
                                        captchaBytes,
                                        width: 110,
                                        height: 48,
                                        fit: BoxFit.contain,
                                        gaplessPlayback: true,
                                      ),
                                    ),
                            ),
                            const SizedBox(width: 8),
                            SizedBox(
                              width: 88,
                              height: 48,
                              child: OutlinedButton(
                                onPressed: () =>
                                    _loadCaptcha(clearInput: true),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: C.gold,
                                  padding:
                                      const EdgeInsets.symmetric(horizontal: 6),
                                  side: const BorderSide(color: C.gold),
                                  shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(14)),
                                ),
                                child: const Text('刷新验证码',
                                    style: TextStyle(fontSize: 12)),
                              ),
                            ),
                          ]),
                          SizedBox(height: compact ? 18 : 20),
                          const Text('短信验证码',
                              style: TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 16,
                                  color: C.text)),
                          const SizedBox(height: 10),
                          Row(children: [
                            Expanded(
                              child: LoginInput(
                                controller: sms,
                                hint: '请输入短信验证码',
                                compactHint: true,
                                icon: Icons.chat_bubble_outline_rounded,
                              ),
                            ),
                            const SizedBox(width: 8),
                            SizedBox(
                              width: 92,
                              height: 48,
                              child: OutlinedButton(
                                onPressed: loading ? null : _sendSms,
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: C.text,
                                  padding:
                                      const EdgeInsets.symmetric(horizontal: 8),
                                  side: const BorderSide(color: C.gold),
                                  shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(14)),
                                ),
                                child: const Text('发送短信',
                                    style: TextStyle(fontSize: 13)),
                              ),
                            ),
                          ]),
                          if (error.isNotEmpty) ...[
                            const SizedBox(height: 14),
                            Text(error,
                                style: const TextStyle(
                                    color: Colors.red, fontSize: 12.5)),
                          ],
                          SizedBox(height: compact ? 22 : 26),
                          SizedBox(
                            height: 54,
                            child: FilledButton(
                              onPressed: loading ? null : _login,
                              style: FilledButton.styleFrom(
                                backgroundColor: C.ink,
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(18)),
                              ),
                              child: loading
                                  ? const SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(
                                          strokeWidth: 2, color: Colors.white),
                                    )
                                  : const Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        Text('登录',
                                            style: TextStyle(
                                                fontSize: 17,
                                                fontWeight: FontWeight.w700)),
                                        SizedBox(width: 12),
                                        Icon(Icons.arrow_forward_rounded,
                                            color: Color(0xFFD8B483)),
                                      ],
                                    ),
                            ),
                          ),
                          SizedBox(height: compact ? 14 : 16),
                          TextButton(
                            onPressed: () => _enterDemoMode(),
                            child: const Text('后端不可用时进入演示模式',
                                style: TextStyle(
                                    color: C.gold,
                                    fontWeight: FontWeight.w600)),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                SizedBox(height: compact ? 42 : 64),
                const Center(
                  child: Text('—  AI 让金融更智能  —',
                      style: TextStyle(
                          color: Color(0xFF9A948C),
                          fontSize: 13,
                          letterSpacing: 3)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class LoginInput extends StatelessWidget {
  const LoginInput({
    required this.controller,
    required this.hint,
    required this.icon,
    this.compactHint = false,
    this.keyboardType,
    super.key,
  });

  final TextEditingController controller;
  final String hint;
  final IconData icon;
  final bool compactHint;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: TextField(
        controller: controller,
        keyboardType: keyboardType,
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(
              color: const Color(0xFF9AA1A8), fontSize: compactHint ? 12 : 14),
          prefixIcon: Icon(icon, color: C.text, size: 20),
          prefixIconConstraints:
              const BoxConstraints(minWidth: 42, minHeight: 42),
          filled: true,
          fillColor: Colors.white,
          contentPadding: const EdgeInsets.symmetric(horizontal: 12),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(13),
            borderSide: const BorderSide(color: Color(0xFFDCD8D1)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(13),
            borderSide: const BorderSide(color: C.gold, width: 1.2),
          ),
        ),
      ),
    );
  }
}

class LoginWavePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFD8B483).withValues(alpha: .22)
      ..style = PaintingStyle.stroke
      ..strokeWidth = .7;
    final startY = size.height - 160;
    for (var i = 0; i < 13; i++) {
      final path = Path()..moveTo(0, startY + i * 9);
      path.cubicTo(
        size.width * .30,
        startY - 54 + i * 5,
        size.width * .62,
        startY + 96 - i * 3,
        size.width,
        startY + 18 + i * 8,
      );
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
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
              if (state.loadingData)
                const Padding(
                  padding: EdgeInsets.fromLTRB(16, 4, 16, 4),
                  child: LinearProgressIndicator(minHeight: 2),
                ),
              if (state.apiError != null)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
                  child: Text('后端连接异常，已使用本地 mock 兜底',
                      style:
                          TextStyle(color: Colors.red.shade400, fontSize: 12)),
                ),
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

Color colorFromHex(dynamic value, Color fallback) {
  final text = value?.toString().replaceAll('#', '');
  if (text == null || text.length != 6) return fallback;
  return Color(int.parse('FF$text', radix: 16));
}

String asText(dynamic value, [String fallback = '']) {
  final text = value?.toString();
  return text == null || text.isEmpty ? fallback : text;
}

class ExpertGrid extends StatelessWidget {
  const ExpertGrid({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final rows = state.apiExperts.isNotEmpty
        ? state.apiExperts
            .map((e) => [
                  asText(e['name']),
                  asText(e['initial'], '专'),
                  asText(e['description']),
                  colorFromHex(e['avatarBg'] ?? e['avatar_bg'], C.ink),
                  asText(e['expertId'] ?? e['expert_id']),
                ])
            .toList()
        : expertOptions.map((e) => [...e, '']).toList();
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: rows.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        crossAxisSpacing: 9,
        mainAxisSpacing: 9,
        childAspectRatio: .86,
      ),
      itemBuilder: (context, index) {
        final e = rows[index];
        final name = e[0] as String;
        final initial = e[1] as String;
        final color = e[3] as Color;
        final expertId = e.length > 4 ? e[4] as String : '';
        final picked = state.expert == name;
        return InkWell(
          onTap: () => state.mutate(() {
            state.expert = name;
            state.selectedExpertId = expertId;
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
    final remote = message.intro.isNotEmpty ||
        message.sections.isNotEmpty ||
        message.risk.isNotEmpty;
    final tool = remote
        ? (message.tool.isEmpty ? script.tool : message.tool)
        : script.tool;
    final intro = remote ? message.intro : script.intro;
    final sections = remote ? message.sections : script.sections;
    final rows = remote ? message.rows : script.rows;
    final risk = remote ? message.risk : script.risk;
    final ref = remote ? message.ref : script.ref;
    final refCount = remote ? message.refCount : script.refCount;
    final isSkill = remote ? message.skill : script.skill;
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
                Label(text: isSkill ? '技能调用 · $tool' : '工具调用 · $tool'),
                const SizedBox(height: 10),
                Text(intro.isEmpty ? '正在检索……' : intro,
                    style: const TextStyle(fontSize: 14, height: 1.7)),
                if (message.stage == Stage.tool) ...[
                  const SizedBox(height: 12),
                  const LinearProgressIndicator(minHeight: 3),
                  const SizedBox(height: 8),
                  Text(
                      message.stageNote.isEmpty
                          ? '正在检索、取数、交叉验证…'
                          : message.stageNote,
                      style: const TextStyle(color: C.muted, fontSize: 12)),
                ],
              ],
              if (message.stage == Stage.done) ...[
                const SizedBox(height: 12),
                for (final section in sections) ...[
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
                if (rows.isNotEmpty) DataTableLite(rows: rows),
                const SizedBox(height: 8),
                Text(risk.isEmpty ? '内容由 AI 生成，请核查重要信息。' : risk,
                    style: const TextStyle(
                        color: C.muted, fontSize: 12.2, height: 1.55)),
                const SizedBox(height: 10),
                InkWell(
                  onTap: () =>
                      state.mutate(() => message.refOpen = !message.refOpen),
                  child: Text('引用 ${refCount == 0 ? 1 : refCount} 条 · 点击查看来源',
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
                    child: Text(
                        '${ref.isEmpty ? '示例数据来源' : ref}\n数据 · 2026-09-22',
                        style: const TextStyle(fontSize: 12, height: 1.55)),
                  ),
                const SizedBox(height: 8),
                Row(children: [
                  TextButton(
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: '$intro\n$risk'));
                        state.snack('已复制回答');
                      },
                      child: const Text('复制')),
                  TextButton(
                      onPressed: () => state.mutate(() {
                            state.favorites
                                .add(intro.isEmpty ? message.flow : intro);
                            state.snack('已收藏到本地 mock');
                          }),
                      child: const Text('收藏')),
                  TextButton(
                      onPressed: () => state.snack('系统分享待接入 · mock'),
                      child: const Text('分享')),
                ]),
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
    final fallback = [
      {
        'kind': '深度研究',
        'group': '本周',
        'createdAt': '09-22 14:20',
        'state': '已完成',
        'title': '创新药板块上涨驱动因素与配置窗口研究',
        'summary': '政策、业绩、BD 出海三条主线梳理，附板块估值分位与重点公司盈利预测。',
        'pages': 18,
        'refCount': 22
      },
      {
        'kind': '公司研究',
        'group': '本周',
        'createdAt': '09-21 09:05',
        'state': '已完成',
        'title': '美的集团（000333.SZ）创新高后的回调复盘',
        'summary': '海外 OBM 占比提升与 KUKA 减亏节奏跟踪，短期获利了结压力测算。',
        'pages': 12,
        'refCount': 15
      },
      {
        'kind': '晨报',
        'group': '本周',
        'createdAt': '09-20 07:30',
        'state': '已发送',
        'title': '9月20日 玑衡晨报：算力链订单兑现节奏',
        'summary': 'CoWoS 满载、液冷订单放量，关注中报业绩兑现与国产替代节奏。',
        'pages': 6,
        'refCount': 9
      },
      {
        'kind': '宏观研究',
        'group': '更早',
        'createdAt': '09-12 16:40',
        'state': '已完成',
        'title': '8000亿元新型政策性金融工具规模测算',
        'summary': '母子基金结构下的杠杆撬动测算，四季度基建投资拉动弹性推演。',
        'pages': 15,
        'refCount': 12,
      },
      {
        'kind': '大宗商品',
        'group': '更早',
        'createdAt': '09-05 11:12',
        'state': '草稿',
        'title': '伦敦金银比历史分位与均值回归分析',
        'summary': '金银比 82.3 处近十年 78% 分位，白银补涨弹性情景分析。',
        'pages': 9,
        'refCount': 9,
      },
    ];
    final source = state.apiReports.isNotEmpty ? state.apiReports : fallback;
    final reports = source
        .where((r) =>
            state.reportTab == '全部' || asText(r['kind']) == state.reportTab)
        .toList();
    return Column(children: [
      PrototypeHeader(title: '我的报告', onBack: () => state.go(PageKey.home)),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
        child: Row(children: [
          for (final tab in ['全部', '深度研究', '公司研究', '晨报']) ...[
            SkillTabButton(
              text: tab,
              selected: state.reportTab == tab,
              onTap: () => state.mutate(() => state.reportTab = tab),
            ),
            if (tab != '晨报') const SizedBox(width: 8),
          ],
        ]),
      ),
      Expanded(
        child: ListView(children: [
          for (final group in ['本周', '更早'])
            if (reports.any((r) => asText(r['group'], '本周') == group)) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 2),
                child: Text(group,
                    style: const TextStyle(
                        color: Color(0xFFA3AAB0), fontSize: 11.5)),
              ),
              for (final report
                  in reports.where((r) => asText(r['group'], '本周') == group))
                ReportTile(
                  report: report,
                  onOpen: () => state.openReport(report),
                  onExport: () => state.exportReport(report),
                ),
            ],
        ]),
      ),
    ]);
  }
}

class ReportTile extends StatelessWidget {
  const ReportTile(
      {required this.report,
      required this.onOpen,
      required this.onExport,
      super.key});
  final Map<String, dynamic> report;
  final VoidCallback onOpen;
  final VoidCallback onExport;

  @override
  Widget build(BuildContext context) {
    final status = asText(report['state']);
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE7E5E0)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
                color: C.goldSoft, borderRadius: BorderRadius.circular(3)),
            child: Text(asText(report['kind']),
                style: const TextStyle(color: C.gold, fontSize: 10.5)),
          ),
          const SizedBox(width: 8),
          Text(asText(report['createdAt'] ?? report['created_at']),
              style: const TextStyle(color: Color(0xFFADB4BA), fontSize: 11.5)),
          const Spacer(),
          Text(status,
              style: TextStyle(
                  color: status == '草稿' ? const Color(0xFFADB4BA) : C.green,
                  fontSize: 11.5)),
        ]),
        const SizedBox(height: 8),
        Text(asText(report['title'], '未命名报告'),
            style: const TextStyle(
                fontFamily: 'Noto Serif SC',
                fontSize: 14.5,
                fontWeight: FontWeight.w600,
                height: 1.5)),
        const SizedBox(height: 6),
        Text(asText(report['summary']),
            style:
                const TextStyle(color: C.muted, fontSize: 12.5, height: 1.7)),
        const SizedBox(height: 11),
        Container(height: 1, color: const Color(0xFFEFECE7)),
        const SizedBox(height: 11),
        Row(children: [
          Text(
              '${asText(report['pages'], '0')} 页 · 引用 ${asText(report['refCount'] ?? report['ref_count'], '0')} 条',
              style: const TextStyle(color: Color(0xFF8B9299), fontSize: 12)),
          const Spacer(),
          InkWell(
              onTap: onOpen,
              child: const Text('查看',
                  style: TextStyle(
                      color: C.gold,
                      fontSize: 12,
                      fontWeight: FontWeight.w600))),
          const SizedBox(width: 14),
          InkWell(
              onTap: onExport,
              child: const Text('导出',
                  style: TextStyle(
                      color: C.gold,
                      fontSize: 12,
                      fontWeight: FontWeight.w600))),
        ]),
      ]),
    );
  }
}

class PrototypeHeader extends StatelessWidget {
  const PrototypeHeader({required this.title, required this.onBack, super.key});
  final String title;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: Stack(children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.only(left: 16),
            child: IconButton(
              onPressed: onBack,
              icon: const Icon(Icons.chevron_left, size: 24),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints.tightFor(width: 32, height: 32),
            ),
          ),
        ),
        Center(
            child: Text(title,
                style: const TextStyle(
                    fontFamily: 'Noto Serif SC',
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: C.text))),
      ]),
    );
  }
}

class SkillsView extends StatelessWidget {
  const SkillsView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final official = <Map<String, dynamic>>[
      {
        'name': '有色板块深度透视',
        'description': '有色金属板块深度分析，采用通用框架+品种插件模…',
        'kind': 'official'
      },
      {
        'name': '贵金属板块深度透视',
        'description': '用于黄金、白银、铂、钯的行情快评、日报、走势复…',
        'kind': 'official'
      },
      {
        'name': '期货主力行为分析',
        'description': '期货主力行为分析基于交易所公开的期货公司席位数…',
        'kind': 'official'
      },
      {
        'name': '基金涨跌解读',
        'description': '帮助客户看懂某只基金或ETF在一段时间内为什么上涨…',
        'kind': 'official'
      },
      {
        'name': '期货资金流向监测',
        'description': '基于国内商品期货品种持仓额变化，监测全市场、板…',
        'kind': 'official'
      },
      {
        'name': '期权波动率洞察',
        'description': '期权波动率数据诊断与市场扫描技能。分析 IV 估值、…',
        'kind': 'official'
      },
      {
        'name': '期权定价计算器',
        'description': '期权与结构化期权产品理论定价技能。对香草、二元…',
        'kind': 'official'
      },
      {
        'name': '机构持仓透视',
        'description': '查看巴菲特、桥水、易方达等顶级机构最新买了什么…',
        'kind': 'official'
      },
      {
        'name': '期货盘中异动归因',
        'description': '用于商品期货盘中异动归因与市场扫描。用户可询问…',
        'kind': 'official'
      },
    ];
    final mine = <Map<String, dynamic>>[
      {
        'name': '组合周度复盘',
        'description': '按持仓权重拆解本周组合收益来源，输出归因表与调仓建议。',
        'kind': 'custom',
        'meta': '最近编辑 09-19 · 已运行 24 次',
      },
      {
        'name': '客户晨会纪要',
        'description': '把晨会语音转写整理成结构化纪要，自动提取观点与待办。',
        'kind': 'custom',
        'meta': '最近编辑 09-11 · 已运行 63 次',
      },
      {
        'name': '行业景气打分卡',
        'description': '按自定义指标体系给跟踪行业打分，生成景气趋势对比表。',
        'kind': 'custom',
        'meta': '最近编辑 08-28 · 已运行 17 次',
      },
      ...state.localCustomSkills,
    ];
    final all = [...official, ...mine];
    final selectedRows = state.skillTab == '我创建的'
        ? mine
        : state.skillTab == '官方技能'
            ? official
            : all
                .where((r) => !state.disabledSkills.contains(asText(r['name'])))
                .toList();
    final query = state.skillQuery.trim();
    final rows = query.isEmpty
        ? selectedRows
        : selectedRows
            .where((r) =>
                asText(r['name']).contains(query) ||
                asText(r['description']).contains(query))
            .toList();
    final enabledCount = all
        .where((r) => !state.disabledSkills.contains(asText(r['name'])))
        .length;
    return Column(
      children: [
        SizedBox(
          height: 48,
          child: Stack(
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: Padding(
                  padding: const EdgeInsets.only(left: 16),
                  child: IconButton(
                    onPressed: () => state.go(PageKey.home),
                    icon: const Icon(Icons.chevron_left, size: 24),
                    padding: EdgeInsets.zero,
                    constraints:
                        const BoxConstraints.tightFor(width: 32, height: 32),
                  ),
                ),
              ),
              const Center(
                child: Text('技能广场',
                    style: TextStyle(
                        fontFamily: 'Noto Serif SC',
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: C.text)),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
          child: Row(children: [
            for (final t in ['已开启的', '我创建的', '官方技能']) ...[
              SkillTabButton(
                  text: t,
                  selected: state.skillTab == t,
                  onTap: () => state.mutate(() => state.skillTab = t)),
              if (t != '官方技能') const SizedBox(width: 8),
            ],
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
          child: SizedBox(
            height: 39,
            child: TextField(
              onChanged: (value) =>
                  state.mutate(() => state.skillQuery = value),
              style: const TextStyle(fontSize: 13),
              decoration: InputDecoration(
                hintText: '搜索技能名称或描述',
                hintStyle:
                    const TextStyle(color: Color(0xFF8B9299), fontSize: 13),
                prefixIcon: const Icon(Icons.search,
                    color: Color(0xFF8B9299), size: 16),
                prefixIconConstraints: const BoxConstraints(minWidth: 39),
                filled: true,
                fillColor: C.faint,
                contentPadding: const EdgeInsets.symmetric(vertical: 8),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: C.line),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: C.gold),
                ),
              ),
            ),
          ),
        ),
        Expanded(
          child: ListView(
            padding: EdgeInsets.zero,
            children: [
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(children: [
                  Text(
                    state.skillTab == '我创建的'
                        ? '${rows.length} 个自建技能'
                        : state.skillTab == '官方技能'
                            ? '${rows.length} / 36 个官方技能'
                            : '$enabledCount 个技能已开启',
                    style: const TextStyle(
                        color: Color(0xFF8B9299), fontSize: 12.5),
                  ),
                  if (state.skillTab == '我创建的') ...[
                    const Spacer(),
                    TextButton(
                      onPressed: () => _showCreateSkill(context),
                      style: TextButton.styleFrom(foregroundColor: C.gold),
                      child: const Text('＋ 新建技能'),
                    ),
                  ],
                ]),
              ),
              for (final r in rows)
                SkillListRow(
                    skill: r,
                    enabled: !state.disabledSkills.contains(asText(r['name'])),
                    onToggle: () => state.toggleSkill(r)),
              if (rows.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(60),
                  child: Center(
                      child: Text('还没有创建技能\n把常用的分析流程沉淀成一个技能，随时调用',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                              color: Color(0xFFADB4BA),
                              fontSize: 13.5,
                              height: 1.8))),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _showCreateSkill(BuildContext context) async {
    final name = TextEditingController();
    final description = TextEditingController();
    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('新建技能'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(
              controller: name,
              decoration: const InputDecoration(labelText: '技能名称')),
          TextField(
              controller: description,
              decoration: const InputDecoration(labelText: '技能描述')),
        ]),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('取消')),
          TextButton(
            onPressed: () {
              if (name.text.trim().isEmpty) return;
              Navigator.pop(dialogContext, {
                'name': name.text.trim(),
                'description': description.text.trim(),
              });
            },
            child: const Text('创建'),
          ),
        ],
      ),
    );
    name.dispose();
    description.dispose();
    if (result == null) return;
    final skill = <String, dynamic>{...result, 'kind': 'custom'};
    state.mutate(() => state.localCustomSkills.add(skill));
    if (state.isLoggedIn) {
      try {
        await state.api.post('/api/v1/skills', result);
      } catch (error) {
        state._rememberApiError(error);
      }
    }
  }
}

class SkillTabButton extends StatelessWidget {
  const SkillTabButton(
      {required this.text,
      required this.selected,
      required this.onTap,
      super.key});
  final String text;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(4),
      child: Container(
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? C.ink : C.faint,
          border: Border.all(color: selected ? C.ink : C.line),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(text,
            style: TextStyle(
                color: selected ? Colors.white : const Color(0xFF4A5259),
                fontWeight: FontWeight.w600,
                fontSize: 13)),
      ),
    );
  }
}

class SkillListRow extends StatelessWidget {
  const SkillListRow(
      {required this.skill,
      required this.enabled,
      required this.onToggle,
      super.key});
  final Map<String, dynamic> skill;
  final bool enabled;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final isOfficial = asText(skill['kind']) != 'custom';
    return InkWell(
      onTap: onToggle,
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: Color(0xFFEFECE7))),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
          Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Flexible(
                  child: Text(asText(skill['name']),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontFamily: 'Noto Serif SC',
                          fontSize: 14.5,
                          height: 1.2,
                          fontWeight: FontWeight.w600,
                          color: C.text)),
                ),
                const SizedBox(width: 7),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                      color: const Color(0xFFF3EDE4),
                      borderRadius: BorderRadius.circular(3)),
                  child: Text(isOfficial ? '官方' : '自建',
                      style: const TextStyle(color: C.gold, fontSize: 10.5)),
                ),
              ]),
              const SizedBox(height: 4),
              Text(asText(skill['description']),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: C.muted, fontSize: 12, height: 1.6)),
              if (asText(skill['meta']).isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(asText(skill['meta']),
                    style: const TextStyle(
                        color: Color(0xFFADB4BA), fontSize: 11.5)),
              ],
            ]),
          ),
          const SizedBox(width: 12),
          Semantics(
            label: '${asText(skill['name'])}开关',
            toggled: enabled,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 42,
              height: 24,
              padding: const EdgeInsets.all(2),
              decoration: BoxDecoration(
                color: enabled ? C.ink : const Color(0xFFE2E0DB),
                borderRadius: BorderRadius.circular(12),
              ),
              child: AnimatedAlign(
                duration: const Duration(milliseconds: 200),
                alignment:
                    enabled ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                          color: Color(0x33000000),
                          blurRadius: 3,
                          offset: Offset(0, 1))
                    ],
                  ),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}

class RemindersView extends StatelessWidget {
  const RemindersView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final tasks = [...state.localTasks, ...state.apiTasks];
    return Column(children: [
      PrototypeHeader(title: '定时与提醒', onBack: () => state.go(PageKey.home)),
      Expanded(
          child: ListView(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
          child: Row(children: [
            Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                  Text('定时任务',
                      style: TextStyle(
                          fontFamily: 'Noto Serif SC',
                          fontSize: 17,
                          fontWeight: FontWeight.w600)),
                  SizedBox(height: 3),
                  Text('管理你的自动化任务',
                      style: TextStyle(color: C.muted, fontSize: 12.5)),
                ])),
            InkWell(
              onTap: state.createTaskMock,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                decoration: BoxDecoration(
                    color: C.ink, borderRadius: BorderRadius.circular(4)),
                child: const Text('＋ 创建定时任务',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600)),
              ),
            ),
          ]),
        ),
        if (tasks.isEmpty)
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 46, 20, 10),
            child: Column(children: [
              Text('暂无定时任务', style: TextStyle(color: C.muted, fontSize: 14)),
              SizedBox(height: 5),
              Text('创建后可在这里查看和管理自动执行的任务',
                  style: TextStyle(color: Color(0xFFADB4BA), fontSize: 12.5)),
            ]),
          ),
        for (final task in tasks)
          CardTile(
            title: asText(
                task['title'] ?? task['taskId'] ?? task['task_id'], '自动化任务'),
            subtitle:
                '${asText(task['type'], 'reminder')} · ${asText(task['status'], 'enabled')}',
            trailing: '删除',
            onTrailingTap: () async {
              final id = asText(task['taskId'] ?? task['task_id']);
              if (id.isNotEmpty &&
                  state.isLoggedIn &&
                  !id.startsWith('local-')) {
                try {
                  await state.api.delete('/api/v1/tasks/$id');
                } catch (error) {
                  state._rememberApiError(error);
                }
              }
              state.mutate(() {
                state.localTasks.remove(task);
                state.apiTasks.remove(task);
              });
            },
            onTap: () => state.snack('任务详情待接入 · mock'),
          ),
        Container(
          margin: const EdgeInsets.only(top: 20),
          decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: C.faint, width: 8))),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('提醒任务',
                      style: TextStyle(
                          fontFamily: 'Noto Serif SC',
                          fontSize: 17,
                          fontWeight: FontWeight.w600)),
                  SizedBox(height: 3),
                  Text('展示满足条件后自动触发的提醒任务',
                      style: TextStyle(color: C.muted, fontSize: 12.5)),
                ]),
          ),
        ),
        if (state.reminders.isEmpty)
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 46, 20, 30),
            child: Column(children: [
              Text('暂无提醒任务', style: TextStyle(color: C.muted, fontSize: 14)),
              SizedBox(height: 5),
              Text('通过对话自动创建提醒订阅任务，满足条件后会在这里展示',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Color(0xFFADB4BA), fontSize: 12.5)),
            ]),
          ),
        for (final reminder in state.reminders)
          CardTile(
              title: reminder,
              subtitle: '提醒任务',
              trailing: '查看',
              onTap: () => state.snack('提醒状态已切换 · mock')),
      ])),
    ]);
  }
}

class NotificationsView extends StatelessWidget {
  const NotificationsView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final remote = state.apiNotifications
        .map((n) => {
              'title': asText(n['title']),
              'subtitle':
                  '${asText(n['type'], '任务记录')} · ${asText(n['createdAt'] ?? n['created_at'], '刚刚')}',
              'id': n['id'],
            })
        .toList();
    return Column(children: [
      PrototypeHeader(title: '通知中心', onBack: () => state.go(PageKey.home)),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Align(
          alignment: Alignment.centerLeft,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 17, vertical: 8),
            decoration: BoxDecoration(
                color: C.ink, borderRadius: BorderRadius.circular(4)),
            child: const Text('任务记录',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600)),
          ),
        ),
      ),
      Expanded(
        child: remote.isEmpty && state.notifications.isEmpty
            ? const Center(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.notifications_none_rounded,
                    size: 34, color: Color(0xFFC9CFD4)),
                SizedBox(height: 12),
                Text('暂无通知',
                    style: TextStyle(fontSize: 13.5, color: Color(0xFFC9CFD4))),
              ]))
            : ListView(children: [
                for (final notification in remote)
                  CardTile(
                    title: asText(notification['title']),
                    subtitle: asText(notification['subtitle']),
                    trailing: '查看',
                    onTap: () async {
                      final id = notification['id'];
                      if (id != null && state.isLoggedIn) {
                        try {
                          await state.api
                              .put('/api/v1/notifications/$id/read', {});
                        } catch (error) {
                          state._rememberApiError(error);
                        }
                      }
                      state.go(PageKey.reports);
                    },
                  ),
                for (final notification in state.notifications)
                  CardTile(
                      title: notification,
                      subtitle: '任务记录 · 刚刚',
                      trailing: '查看',
                      onTap: () => state.go(PageKey.reports)),
              ]),
      ),
    ]);
  }
}

class ProfileView extends StatelessWidget {
  const ProfileView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final p = state.profile ?? {};
    final stats = Map<String, dynamic>.from((p['stats'] as Map?) ?? {});
    final rows = [
      ('账号与安全', '已绑定手机'),
      ('订阅与积分', '机构版 · 8,420 分'),
      ('数据权限', '行情 / 研报 / 财报'),
      ('消息通知', '已开启'),
      ('偏好设置', '简体中文'),
      ('关于玑衡AI', 'v2.4.1'),
    ];
    return Column(children: [
      PrototypeHeader(title: '个人中心', onBack: () => state.go(PageKey.home)),
      Expanded(
          child: ListView(children: [
        Container(
          margin: const EdgeInsets.fromLTRB(16, 6, 16, 0),
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
              color: C.ink, borderRadius: BorderRadius.circular(12)),
          child: Column(children: [
            Row(children: [
              Container(
                width: 48,
                height: 48,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                    color: const Color(0xFF33393F),
                    border: Border.all(color: const Color(0xFF4A5157)),
                    shape: BoxShape.circle),
                child: const Text('用',
                    style: TextStyle(
                        fontFamily: 'Noto Serif SC',
                        fontSize: 17,
                        color: Color(0xFFD8B483))),
              ),
              const SizedBox(width: 13),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    Text(asText(p['displayName'], 'USER_6450'),
                        style: const TextStyle(
                            fontFamily: 'Noto Serif SC',
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.white)),
                    const SizedBox(height: 3),
                    Text(
                        '${asText(p['plan'], '机构版')} · ${asText(p['department'], '研究部')}',
                        style: const TextStyle(
                            fontSize: 12, color: Color(0xFF9AA4AC))),
                  ])),
              InkWell(
                  onTap: () => _editProfile(context),
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                        border: Border.all(color: const Color(0xFF6D6153)),
                        borderRadius: BorderRadius.circular(3)),
                    child: const Text('编辑资料',
                        style: TextStyle(
                            fontSize: 11.5, color: Color(0xFFD8B483))),
                  )),
            ]),
            const SizedBox(height: 16),
            Container(height: 1, color: const Color(0xFF333940)),
            const SizedBox(height: 15),
            Row(children: [
              for (final stat in [
                (asText(stats['reportCount'], '24'), '生成报告'),
                (asText(stats['skillCount'], '9'), '启用技能'),
                (asText(stats['usageDays'], '146'), '使用天数'),
              ])
                Expanded(
                    child: Column(children: [
                  Text(stat.$1,
                      style: const TextStyle(
                          fontFamily: 'Noto Serif SC',
                          fontSize: 19,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFD8B483))),
                  const SizedBox(height: 4),
                  Text(stat.$2,
                      style: const TextStyle(
                          fontSize: 11.5, color: Color(0xFF9AA4AC))),
                ])),
            ]),
          ]),
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(16, 18, 16, 4),
          child: Text('账号',
              style: TextStyle(fontSize: 11.5, color: Color(0xFFA3AAB0))),
        ),
        for (final row in rows)
          InkWell(
            onTap: () => row.$1 == '消息通知'
                ? state.go(PageKey.notifications)
                : state.snack('${row.$1} · mock'),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: const BoxDecoration(
                  border: Border(bottom: BorderSide(color: Color(0xFFEFECE7)))),
              child: Row(children: [
                Expanded(
                    child: Text(row.$1,
                        style: const TextStyle(fontSize: 14, color: C.text))),
                Text(row.$2,
                    style: const TextStyle(
                        fontSize: 12.5, color: Color(0xFF8B9299))),
                const SizedBox(width: 12),
                const Icon(Icons.chevron_right,
                    size: 17, color: Color(0xFFC9CFD4)),
              ]),
            ),
          ),
        InkWell(
            onTap: state.logout,
            child: Container(
              margin: const EdgeInsets.fromLTRB(16, 22, 16, 24),
              padding: const EdgeInsets.all(13),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                  border: Border.all(color: const Color(0xFFE7E5E0)),
                  borderRadius: BorderRadius.circular(8)),
              child: const Text('退出登录',
                  style: TextStyle(color: C.muted, fontSize: 13.5)),
            )),
      ])),
    ]);
  }

  Future<void> _editProfile(BuildContext context) async {
    final controller = TextEditingController(
        text: asText(state.profile?['displayName'], 'USER_6450'));
    final name = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('编辑资料'),
        content: TextField(
            controller: controller,
            decoration: const InputDecoration(labelText: '昵称')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('取消')),
          TextButton(
              onPressed: () =>
                  Navigator.pop(dialogContext, controller.text.trim()),
              child: const Text('保存')),
        ],
      ),
    );
    controller.dispose();
    if (name == null || name.isEmpty) return;
    state
        .mutate(() => state.profile = {...?state.profile, 'displayName': name});
    if (state.isLoggedIn) {
      try {
        await state.api.put('/api/v1/profile', {'displayName': name});
      } catch (error) {
        state._rememberApiError(error);
      }
    }
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
              title: Text(asText(state.profile?['displayName'], 'USER_6450')),
              subtitle: Text(
                  '${asText(state.profile?['plan'], '机构版')} · ${asText(state.profile?['department'], '研究部')}'),
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
    final experts = state.apiExperts.isNotEmpty
        ? state.apiExperts
            .map((e) => [
                  asText(e['name']),
                  asText(e['initial'], '专'),
                  asText(e['description']),
                  asText(e['expertId'] ?? e['expert_id']),
                  colorFromHex(e['avatarBg'] ?? e['avatar_bg'], C.ink),
                ])
            .toList()
        : [
            ['会议专家', '会', '全程协助处理会前到会后的关键工作', '', C.ink],
            ['个股研究专家', '股', '围绕公司基本面、财报与事件进行研究', '', C.ink],
            ['行业研究专家', '行', '围绕行业、子行业、产业链环节分析', '', C.ink],
            ['财富管理专家', '财', '覆盖客户洞察、产品匹配与沟通话术', '', C.ink],
            ['研报专家', '研', '追踪全市场研报，提炼核心观点', '', C.ink],
            ['舆情专家', '舆', '监测个股与行业舆情，识别情绪拐点', '', C.ink],
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
                              backgroundColor: e[4] as Color,
                              child: Text(e[1] as String,
                                  style: const TextStyle(
                                      color: Color(0xFFD8B483)))),
                          title: Text(e[0] as String),
                          subtitle: Text(e[2] as String),
                          trailing: state.expert == e[0]
                              ? const Icon(Icons.check, color: C.green)
                              : null,
                          onTap: () => state.mutate(() {
                            state.expert = e[0] as String;
                            state.selectedExpertId = e[3] as String;
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

class ReportDetailPage extends StatelessWidget {
  const ReportDetailPage({required this.report, super.key});
  final Map<String, dynamic> report;

  @override
  Widget build(BuildContext context) {
    final title = asText(report['title'], '报告详情');
    final content = asText(report['content']);
    final summary =
        asText(report['summary'], '这是一份前端 mock 报告阅读页。后端返回正文后会展示真实 content 字段。');
    final refs = asText(report['refs'], '暂无完整引用列表');
    return Scaffold(
      backgroundColor: C.paper,
      appBar: AppBar(
        title: const Text('报告详情'),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
        children: [
          Label(text: asText(report['kind'], '深度研究')),
          const SizedBox(height: 12),
          Text(title,
              style: const TextStyle(
                  fontFamily: 'serif',
                  fontWeight: FontWeight.w700,
                  fontSize: 21,
                  height: 1.35)),
          const SizedBox(height: 8),
          Text(
              '${asText(report['state'], '已完成')} · ${asText(report['pages'], '0')} 页 · 引用 ${asText(report['refCount'] ?? report['ref_count'], '0')} 条',
              style: const TextStyle(color: C.muted, fontSize: 12)),
          const SizedBox(height: 18),
          Text(content.isEmpty ? summary : content,
              style: const TextStyle(fontSize: 14, height: 1.8)),
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
                color: C.faint,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: C.line)),
            child: Text('引用来源\n$refs',
                style: const TextStyle(fontSize: 12.5, height: 1.6)),
          ),
          const SizedBox(height: 18),
          const Text('内容由 AI 生成，请核查重要信息。',
              style: TextStyle(color: C.muted, fontSize: 12)),
        ],
      ),
    );
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
      this.onTrailingTap,
      super.key});
  final String title;
  final String subtitle;
  final String trailing;
  final VoidCallback? onTap;
  final VoidCallback? onTrailingTap;

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
          trailing: InkWell(
            onTap: onTrailingTap,
            child: Text(trailing, style: const TextStyle(color: C.gold)),
          )),
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
