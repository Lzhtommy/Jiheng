import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'collab.dart';

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

enum PageKey {
  home,
  reports,
  profile,
  skills,
  reminders,
  notifications,
  favorites
}

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
  List<Map<String, String>> refList = [];
  String stageNote = '';
  int refCount = 0;
  bool skill = false;
  final List<SectionData> sections = [];
  final List<List<String>> rows = [];
  final List<ToolCallData> toolCalls = [];
  CollabData? collab;
  final DateTime startedAt = DateTime.now();
}

class ToolCallData {
  ToolCallData(this.id, this.name, this.input);
  final String id;
  final String name;
  final String input;
  String? result;
  bool? success;

  bool get running => success == null;
}

const toolLabels = {
  'search_symbol': '证券代码检索',
  'get_realtime_quote': '实时行情',
  'get_kline': 'K线数据',
  'get_minute_kline': '分钟K线',
  'get_index_quote': '指数行情',
  'get_sector_quote': '板块行情',
  'get_fund_flow': '板块资金流',
  'list_announcements': '公告检索',
  'download_announcement': '公告下载',
  'get_corporate_calendar': '交易日历',
  'search_news': '财经新闻',
  'get_official_policy': '政策资讯',
  'call_financial_mcp': '财报数据',
};

final answerMarkdownStyle = MarkdownStyleSheet(
  p: const TextStyle(fontSize: 14, height: 1.7, color: C.ink),
  h1: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: C.ink),
  h2: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: C.ink),
  h3: const TextStyle(
      fontSize: 14.5, fontWeight: FontWeight.w700, color: C.ink),
  strong: const TextStyle(fontWeight: FontWeight.w700),
  listBullet: const TextStyle(fontSize: 14, height: 1.7, color: C.ink),
  blockSpacing: 10,
  tableHead:
      const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: C.ink),
  tableBody: const TextStyle(fontSize: 13, height: 1.5, color: C.ink),
  tableBorder: TableBorder.all(color: C.line),
  tableCellsPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
  tableHeadCellsDecoration: const BoxDecoration(color: C.goldSoft),
  tableColumnWidth: const IntrinsicColumnWidth(),
  blockquoteDecoration: const BoxDecoration(
    color: Color(0xFFF7F6F3),
    border: Border(left: BorderSide(color: C.gold, width: 3)),
  ),
  code: const TextStyle(
      fontFamily: 'monospace', fontSize: 12.5, backgroundColor: C.goldSoft),
  horizontalRuleDecoration: const BoxDecoration(
    border: Border(top: BorderSide(color: C.line)),
  ),
);

String prettyJson(String? raw) {
  if (raw == null || raw.isEmpty) return '';
  try {
    return const JsonEncoder.withIndent('  ').convert(jsonDecode(raw));
  } catch (_) {
    return raw;
  }
}

class ApiClient {
  ApiClient();

  static const _javaOverride = String.fromEnvironment('JIHENG_JAVA_BASE_URL');
  static const _agentOverride = String.fromEnvironment('JIHENG_AGENT_BASE_URL');
  static const _lanBase = 'http://192.168.184.207';

  /// 本机页面连本机服务；部署到服务器后走当前站点，由 nginx 转发。
  static String get javaBase =>
      _javaOverride.isNotEmpty ? _javaOverride : _localOrOrigin(_lanBase);

  static String get agentBase =>
      _agentOverride.isNotEmpty ? _agentOverride : _localOrOrigin(_lanBase);

  static String _localOrOrigin(String local) {
    if (!kIsWeb) return local;
    final host = Uri.base.host;
    if (host == 'localhost' || host == '127.0.0.1') return local;
    return Uri.base.origin;
  }

  final storage = const FlutterSecureStorage();
  String? accessToken;
  String? refreshToken;
  String? userId;
  void Function()? onUnauthorized;

  void _checkUnauthorized(int statusCode) {
    if (statusCode == 401 && accessToken != null) onUnauthorized?.call();
  }

  Future<void> loadTokens() async {
    try {
      final values = await Future.wait([
        storage.read(key: 'accessToken'),
        storage.read(key: 'refreshToken'),
        storage.read(key: 'userId'),
      ]).timeout(const Duration(seconds: 1));
      accessToken = values[0];
      refreshToken = values[1];
      userId = values[2];
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
        'Content-Type': 'application/json; charset=utf-8',
        if (accessToken != null && accessToken!.isNotEmpty)
          'Authorization': 'Bearer $accessToken',
      };

  dynamic _unwrap(http.Response response) {
    final text = utf8.decode(response.bodyBytes);
    final decoded = text.isEmpty ? null : jsonDecode(text);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      _checkUnauthorized(response.statusCode);
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
        headers: _headers, body: utf8.encode(jsonEncode(body)));
    return _unwrap(response);
  }

  Future<dynamic> put(String path, Map<String, dynamic> body) async {
    final response = await http.put(Uri.parse('$javaBase$path'),
        headers: _headers, body: utf8.encode(jsonEncode(body)));
    return _unwrap(response);
  }

  Future<dynamic> delete(String path) async {
    final response =
        await http.delete(Uri.parse('$javaBase$path'), headers: _headers);
    return _unwrap(response);
  }

  Future<dynamic> agentPost(String path, Map<String, dynamic> body) async {
    final response = await http.post(Uri.parse('$agentBase$path'),
        headers: _headers, body: utf8.encode(jsonEncode(body)));
    if (response.statusCode == 202) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    }
    return _unwrap(response);
  }

  Stream<Map<String, dynamic>> streamChat(Map<String, dynamic> body,
      {String path = '/chat/stream'}) async* {
    final request = http.Request('POST', Uri.parse('$agentBase$path'));
    request.headers.addAll({
      ..._headers,
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
    });
    request.bodyBytes = utf8.encode(jsonEncode(body));
    final response = await request.send();
    if (response.statusCode < 200 || response.statusCode >= 300) {
      _checkUnauthorized(response.statusCode);
      final text = await response.stream.bytesToString();
      try {
        final decoded = jsonDecode(text);
        if (decoded is Map && decoded['message'] != null) {
          throw Exception(decoded['message']);
        }
      } on FormatException {
        // Non-JSON error bodies fall through to the status code message.
      }
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
    if (data.isNotEmpty) {
      final parsed = jsonDecode(data.toString());
      if (parsed is Map<String, dynamic>) {
        yield {'event': event, ...parsed};
      } else {
        yield {'event': event, 'data': parsed};
      }
    }
  }
}

class SectionData {
  const SectionData(this.title, this.items);
  final String title;
  final List<String> items;
}

class JihengShell extends StatefulWidget {
  const JihengShell({super.key});

  @override
  State<JihengShell> createState() => JihengShellState();
}

class JihengShellState extends State<JihengShell> {
  final api = ApiClient();
  PageKey page = PageKey.home;
  final input = TextEditingController();
  final drawerSearch = TextEditingController();
  final scroll = ScrollController();
  final List<ChatMsg> messages = [];
  final Set<String> disabledSkills = {};
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
  List<Map<String, dynamic>> apiConversations = [];
  final List<Map<String, dynamic>> localTasks = [];
  final List<String> favorites = [];
  bool drawerOpen = false;
  bool expertSheet = false;
  bool worldOpen = false;
  bool worldTransitioning = false;
  bool _transitionToWorld = false;
  bool authReady = false;
  bool isLoggedIn = false;
  bool loadingData = false;
  bool sending = false;
  bool collabMode = false;
  String? _chatSessionId;

  String get chatSessionId => _chatSessionId ??=
      'mobile-${api.userId ?? 'guest'}-${DateTime.now().microsecondsSinceEpoch}';
  String get activeExpertId =>
      selectedExpertId.isNotEmpty ? selectedExpertId : 'expert_stock_research';
  String get activeExpertName => expert.isNotEmpty ? expert : '个股研究专家';

  @override
  void initState() {
    super.initState();
    api.onUnauthorized = _handleUnauthorized;
    _bootstrap();
    loadFavorites();
  }

  Future<void> _handleUnauthorized() async {
    if (mounted) {
      setState(() {
        isLoggedIn = false;
        profile = null;
        messages.clear();
        _chatSessionId = null;
        sending = false;
        apiError = '登录已失效，请重新登录';
      });
    }
    await api.clearTokens();
  }

  void newChat() {
    setState(() {
      messages.clear();
      _chatSessionId = null;
      sending = false;
      worldOpen = false;
    });
    go(PageKey.home);
  }

  @override
  void dispose() {
    input.dispose();
    drawerSearch.dispose();
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
    if (isLoggedIn) await loadRemoteData();
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
      _chatSessionId = null;
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
      _loadConversations(),
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

  Future<void> _loadConversations() async {
    try {
      final data = await api.get('/api/v1/conversations');
      final rows = (data as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (mounted) setState(() => apiConversations = rows);
    } catch (e) {
      _rememberApiError(e);
    }
  }

  Future<void> openConversation(String conversationId) async {
    try {
      final data =
          await api.get('/api/v1/conversations/$conversationId/messages');
      final rows = (data as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (!mounted) return;
      setState(() {
        messages
          ..clear()
          ..addAll(rows.map((row) => row['role'] == 'user'
              ? ChatMsg.user(asText(row['content']))
              : (ChatMsg.ai('generic')
                ..intro = asText(row['content'])
                ..stage = Stage.done)));
        _chatSessionId = conversationId;
        page = PageKey.home;
        drawerOpen = false;
      });
    } catch (e) {
      _rememberApiError(e);
      snack('对话加载失败');
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
      snack('演示报告不支持导出，请登录后导出自己的报告');
      return;
    }
    try {
      final data =
          await api.post('/api/v1/reports/$reportId/export', {'format': 'pdf'});
      final taskId = asText(data is Map ? data['task_id'] : null);
      snack(taskId.isEmpty ? '导出任务已提交' : '导出任务已创建：$taskId');
    } catch (e) {
      _rememberApiError(e);
      snack('导出失败，请稍后重试');
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

  Future<void> createTask() async {
    final title = TextEditingController();
    final cron = TextEditingController(text: '0 30 8 ? * MON');
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('创建定时任务', style: TextStyle(fontSize: 16)),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(
              controller: title,
              decoration: const InputDecoration(labelText: '任务名称')),
          const SizedBox(height: 8),
          TextField(
              controller: cron,
              decoration: const InputDecoration(
                  labelText: '执行时间（cron）', hintText: '0 30 8 ? * MON')),
        ]),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('取消')),
          FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('创建')),
        ],
      ),
    );
    final taskTitle = title.text.trim();
    final taskCron = cron.text.trim();
    title.dispose();
    cron.dispose();
    if (confirmed != true || taskTitle.isEmpty) return;
    final task = <String, dynamic>{
      'taskId': 'local-${DateTime.now().millisecondsSinceEpoch}',
      'type': 'reminder',
      'status': 'enabled',
      'title': taskTitle,
      'cron': taskCron,
    };
    var synced = false;
    try {
      if (isLoggedIn) {
        await api.post('/api/v1/tasks', {
          'type': task['type'],
          'cron': taskCron,
          'payload': jsonEncode(task),
        });
        synced = true;
      }
    } catch (e) {
      _rememberApiError(e);
    }
    if (!mounted) return;
    setState(() {
      if (!synced) localTasks.insert(0, task);
      reminders.insert(0, asText(task['title']));
    });
    if (synced) await _loadTasks();
    snack(synced ? '定时任务已创建' : '已保存在本地');
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

  void switchWorld(bool toWorld) {
    if (worldOpen == toWorld || worldTransitioning) return;
    setState(() {
      worldTransitioning = true;
      _transitionToWorld = toWorld;
    });
  }

  void _applyWorldSwitch() {
    if (!mounted) return;
    setState(() => worldOpen = _transitionToWorld);
  }

  void _endWorldTransition() {
    if (!mounted) return;
    setState(() => worldTransitioning = false);
  }

  static const _favoritesKey = 'favorites';

  Future<void> loadFavorites() async {
    try {
      final raw = await api.storage.read(key: _favoritesKey);
      final decoded = raw == null || raw.isEmpty ? [] : jsonDecode(raw);
      if (decoded is List && mounted) {
        setState(() => favorites
          ..clear()
          ..addAll(decoded.map((e) => e.toString())));
      }
    } on MissingPluginException {
      // 测试环境没有本地存储。
    }
  }

  Future<void> toggleFavorite(String text) async {
    final content = text.trim();
    if (content.isEmpty) return;
    setState(() {
      if (!favorites.remove(content)) favorites.insert(0, content);
    });
    snack(favorites.contains(content) ? '已收藏' : '已取消收藏');
    try {
      await api.storage.write(key: _favoritesKey, value: jsonEncode(favorites));
    } on MissingPluginException {
      // 测试环境没有本地存储。
    }
  }

  void setPrompt(String text, String nextFlow) {
    setState(() {
      input.text = text;
      flow = nextFlow;
    });
  }

  Future<void> send() async {
    final text = input.text.trim();
    if (sending) return;
    if (text.isEmpty) return;
    final ai = ChatMsg.ai(flow);
    setState(() {
      messages.add(ChatMsg.user(text));
      messages.add(ai);
      activity.insert(0, '新问答：$text');
      input.clear();
      flow = 'generic';
      sending = true;
    });
    _scrollDown();
    if (api.accessToken == null) {
      setState(() {
        ai.stage = Stage.done;
        ai.intro = '当前为演示模式，未连接后端，请退出后使用默认账号登录。';
        ai.risk = '内容由 AI 生成，请核查重要信息。';
        sending = false;
      });
      return;
    }
    if (mode == '分析师' && collabMode) {
      await _planCollab(ai, text);
      return;
    }
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
          localTasks.insert(0,
              {'taskId': taskId, 'type': 'deep_research', 'status': 'running'});
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
      if (!mounted) return;
      setState(() {
        if (ai.stage != Stage.done) {
          ai.stage = Stage.done;
          if (ai.intro.isEmpty) ai.intro = '已完成分析。';
          if (ai.risk.isEmpty) ai.risk = '内容由 AI 生成，请核查重要信息。';
        }
        sending = false;
      });
      return;
    } catch (e) {
      if (!mounted) return;
      if (!isLoggedIn) {
        setState(() => sending = false);
        return;
      }
      _rememberApiError(e);
      setState(() {
        ai.stage = Stage.done;
        if (ai.intro.isEmpty) ai.intro = '请求失败，请稍后重试。';
        ai.risk = e.toString();
        sending = false;
      });
    }
  }

  Map<String, dynamic> _collabBody(CollabData collab) => {
        'expert': activeExpertId,
        'conversation_id': chatSessionId,
        'messages': [
          ...collab.history,
          {'role': 'user', 'content': collab.question},
        ],
      };

  Future<void> _planCollab(ChatMsg ai, String text) async {
    final collab = CollabData(question: text, history: _chatHistory());
    setState(() => ai.collab = collab);
    try {
      final data =
          await api.agentPost('/chat/multi-agent/plan', _collabBody(collab));
      if (!mounted) return;
      setState(() {
        collab.loadPlan(Map<String, dynamic>.from(data as Map));
        collab.phase = 'confirm';
        sending = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        collab.phase = 'failed';
        ai.stage = Stage.done;
        ai.intro = '研究计划生成失败，请稍后重试。';
        ai.risk = e.toString();
        sending = false;
      });
    }
    _scrollDown();
  }

  Future<void> editCollabPlan(ChatMsg ai) async {
    final collab = ai.collab!;
    final edited = await Navigator.of(context).push<CollabData>(
        MaterialPageRoute(builder: (_) => PlanEditorPage(collab: collab)));
    if (edited == null || !mounted) return;
    setState(() {
      collab.goal = edited.goal;
      collab.nodes = edited.nodes;
    });
  }

  void cancelCollab(ChatMsg ai) {
    setState(() {
      ai.collab!.phase = 'cancelled';
      ai.stage = Stage.done;
      ai.intro = '已取消本次协作研究。';
    });
  }

  Future<void> runCollab(ChatMsg ai) async {
    final collab = ai.collab!;
    final errors = collab.validate();
    if (errors.isNotEmpty) {
      snack(errors.first);
      return;
    }
    setState(() {
      collab.phase = 'research';
      ai.stage = Stage.tool;
      sending = true;
    });
    try {
      final body = {..._collabBody(collab), 'plan': collab.toPlanJson()};
      await for (final event
          in api.streamChat(body, path: '/chat/multi-agent/stream')) {
        if (!mounted) return;
        _applySseEvent(ai, event);
        _scrollDown();
      }
      if (!mounted) return;
      setState(() {
        if (collab.phase != 'failed') collab.phase = 'done';
        ai.stage = Stage.done;
        _loadConversations();
        if (ai.intro.isEmpty) ai.intro = '协作研究已结束，但未生成回答。';
        sending = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        collab.phase = 'failed';
        ai.stage = Stage.done;
        if (ai.intro.isEmpty) ai.intro = '协作研究执行失败，请稍后重试。';
        ai.risk = e.toString();
        sending = false;
      });
    }
  }

  Map<String, dynamic> _chatBody(String text) {
    return {
      'mode': mode == '深度研究'
          ? 'deep'
          : mode == '分析师'
              ? 'expert'
              : 'quick',
      'expert': mode == '分析师' ? selectedExpertId : null,
      'conversation_id': chatSessionId,
      'messages': [
        ..._chatHistory(),
        {
          'role': 'user',
          'content': text,
          'created_at': DateTime.now().toIso8601String()
        }
      ],
    };
  }

  // 本轮 send() 已把当前提问和待填充的 AI 消息加进 messages，历史不含这两条
  List<Map<String, dynamic>> _chatHistory() {
    final previous = messages.length >= 2
        ? messages.sublist(0, messages.length - 2)
        : <ChatMsg>[];
    final history = <Map<String, dynamic>>[];
    for (final msg in previous) {
      final content = msg.isUser ? msg.text : msg.intro;
      if (content.trim().isEmpty) continue;
      history
          .add({'role': msg.isUser ? 'user' : 'assistant', 'content': content});
    }
    return history.length > 10 ? history.sublist(history.length - 10) : history;
  }

  bool _applyCollabEvent(
      CollabData collab, String name, Map<String, dynamic> event) {
    final node = collab.byId(event['node_id']?.toString());
    switch (name) {
      case 'phase':
        collab.phase = event['name']?.toString() ?? collab.phase;
      case 'agent_graph':
        break;
      case 'agent_status':
        node?.status = event['status']?.toString() ?? 'pending';
        node?.attempt = int.tryParse('${event['attempt']}') ?? 0;
      case 'agent_message':
        collab.messages.add(CollabMessage(
          int.tryParse('${event['id']}') ?? collab.messages.length + 1,
          (event['from'] ?? event['from_node'])?.toString() ?? '',
          (event['to'] ?? event['to_node'])?.toString(),
          (event['kind'] ?? event['message_type'])?.toString() ?? '',
          (event['summary'] ?? event['content'])?.toString() ?? '',
        ));
      case 'agent_output':
        node?.output = (event['output'] ?? event['summary'] ?? event['content'])
                ?.toString() ??
            '';
      case 'tool_call' when node != null:
        final rawInput = event['tool_input'] ?? event['arguments'] ?? '';
        node.toolCalls.add(ToolCallData(
            (event['call_id'] ?? event['id'])?.toString() ?? '',
            (event['tool_name'] ?? event['name'])?.toString() ?? '',
            rawInput is String ? rawInput : jsonEncode(rawInput)));
      case 'tool_result' when node != null:
        for (final call in node.toolCalls) {
          if (call.id == (event['call_id'] ?? event['id'])?.toString()) {
            final rawResult =
                event['tool_result'] ?? event['result'] ?? event['error'] ?? '';
            call.result =
                rawResult is String ? rawResult : jsonEncode(rawResult);
            call.success = event['success'] != false;
          }
        }
      default:
        return false;
    }
    return true;
  }

  void _applySseEvent(ChatMsg ai, Map<String, dynamic> event) {
    setState(() {
      final name = event['event']?.toString() ?? '';
      if (name.contains('error') || event['code'] != null) {
        ai.collab?.phase = 'failed';
        ai.stage = Stage.done;
        if (ai.intro.isNotEmpty || ai.sections.isNotEmpty) {
          if (ai.risk.isEmpty) {
            ai.risk = event['message']?.toString() ?? '内容由 AI 生成，请核查重要信息。';
          }
          sending = false;
          return;
        }
        ai.intro = '服务暂时不可用，请稍后重试。';
        ai.sections.add(const SectionData('错误信息', ['请稍后重试，或检查后端服务地址与登录状态。']));
        ai.risk = event['message']?.toString() ?? '内容由 AI 生成，请核查重要信息。';
        sending = false;
        return;
      }
      if (ai.collab != null && _applyCollabEvent(ai.collab!, name, event)) {
        ai.collab!.revision.value++;
        return;
      }
      final callId = event['call_id']?.toString();
      if (name == 'tool_call' && callId != null) {
        ai.toolCalls.add(ToolCallData(
            callId,
            event['tool_name']?.toString() ?? '',
            event['tool_input']?.toString() ?? ''));
      } else if (name == 'tool_result' && callId != null) {
        for (final call in ai.toolCalls) {
          if (call.id == callId) {
            call.result = event['tool_result']?.toString() ?? '';
            call.success = event['success'] != false;
          }
        }
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
        ai.refList = (event['refs'] as List).map((item) {
          final source = item is Map ? item : {'title': item};
          return {
            'title': (source['title'] ?? '').toString(),
            'url': (source['url'] ?? '').toString(),
          };
        }).toList();
        ai.ref = ai.refList.map((s) => '· ${s['title']}').join('\n');
      }
      if (name.contains('done')) {
        if (ai.collab != null && ai.collab!.phase != 'failed') {
          ai.collab!.phase = 'done';
          ai.collab!.revision.value++;
        }
        ai.stage = Stage.done;
        if (ai.intro.isEmpty) ai.intro = '已完成分析。';
        if (ai.risk.isEmpty) ai.risk = '内容由 AI 生成，请核查重要信息。';
        sending = false;
        _loadConversations();
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
            if (worldTransitioning)
              Positioned.fill(
                child: WorldTransitionOverlay(
                  toWorld: _transitionToWorld,
                  onMidpoint: _applyWorldSwitch,
                  onDone: _endWorldTransition,
                ),
              ),
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
      case PageKey.favorites:
        return FavoritesView(state: this);
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
      if (mounted) setState(() => error = '短信发送失败：$e');
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
                    padding: const EdgeInsets.all(2),
                    clipBehavior: Clip.antiAlias,
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
                    child: Transform.scale(
                      scale: 1.72,
                      child: Image.asset('logo.png', fit: BoxFit.cover),
                    ),
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
                                onPressed: () => _loadCaptcha(clearInput: true),
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
    if (state.worldOpen) {
      return Column(
        children: [
          HomeHeader(state: state),
          const Expanded(child: JihengWorldView()),
        ],
      );
    }
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
                  title: '分析师',
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
    final world = state.worldOpen;
    return Container(
      width: double.infinity,
      color: world ? const Color(0xFF0E1D31) : C.paper,
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
      child: Stack(
        alignment: Alignment.center,
        children: [
          if (!world)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                    onPressed: () =>
                        state.mutate(() => state.drawerOpen = true),
                    icon: const Icon(Icons.menu_rounded)),
                IconButton(
                    onPressed: () => state.go(PageKey.notifications),
                    icon: const Icon(Icons.notifications_none_rounded)),
              ],
            ),
          Container(
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(
              color: world ? const Color(0xFF20324D) : const Color(0xFFF1EFEB),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              HomeTabButton(
                label: '玑衡AI',
                selected: !world,
                dark: world,
                onTap: () => state.switchWorld(false),
              ),
              HomeTabButton(
                label: '玑衡World',
                selected: world,
                dark: world,
                onTap: () => state.switchWorld(true),
              ),
            ]),
          ),
        ],
      ),
    );
  }
}

class HomeTabButton extends StatelessWidget {
  const HomeTabButton({
    required this.label,
    required this.selected,
    required this.dark,
    required this.onTap,
    super.key,
  });

  final String label;
  final bool selected;
  final bool dark;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected
        ? Colors.white
        : dark
            ? const Color(0xFF8FA0B7)
            : const Color(0xFF9AA1A8);
    final textColor = selected
        ? C.text
        : dark
            ? const Color(0xFF9BA9BE)
            : const Color(0xFF6F7780);
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? color : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          boxShadow: selected
              ? const [
                  BoxShadow(
                      color: Color(0x16000000),
                      blurRadius: 4,
                      offset: Offset(0, 1))
                ]
              : null,
        ),
        child: Text(label,
            style: TextStyle(
                color: textColor, fontWeight: FontWeight.w700, fontSize: 15)),
      ),
    );
  }
}

class WorldTransitionOverlay extends StatefulWidget {
  const WorldTransitionOverlay({
    required this.toWorld,
    required this.onMidpoint,
    required this.onDone,
    super.key,
  });

  final bool toWorld;
  final VoidCallback onMidpoint;
  final VoidCallback onDone;

  @override
  State<WorldTransitionOverlay> createState() =>
      _WorldTransitionOverlayState();
}

class _WorldTransitionOverlayState extends State<WorldTransitionOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;
  late final Animation<double> _scale;
  bool _switched = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..addListener(_onTick)
      ..addStatusListener((status) {
        if (status == AnimationStatus.completed) widget.onDone();
      })
      ..forward();
    _opacity = TweenSequence<double>([
      TweenSequenceItem(
          tween: Tween(begin: 0.0, end: 1.0).chain(CurveTween(curve: Curves.easeOut)),
          weight: 30),
      TweenSequenceItem(tween: ConstantTween(1.0), weight: 40),
      TweenSequenceItem(
          tween: Tween(begin: 1.0, end: 0.0).chain(CurveTween(curve: Curves.easeIn)),
          weight: 30),
    ]).animate(_controller);
    _scale = TweenSequence<double>([
      TweenSequenceItem(
          tween: Tween(begin: 0.88, end: 1.0)
              .chain(CurveTween(curve: Curves.easeOutBack)),
          weight: 30),
      TweenSequenceItem(tween: ConstantTween(1.0), weight: 70),
    ]).animate(_controller);
  }

  void _onTick() {
    if (!_switched && _controller.value >= 0.32) {
      _switched = true;
      widget.onMidpoint();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final world = widget.toWorld;
    return AbsorbPointer(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return Opacity(
            opacity: _opacity.value,
            child: Container(
              color: world ? const Color(0xFF0E1D31) : C.paper,
              alignment: Alignment.center,
              child: Transform.scale(scale: _scale.value, child: child),
            ),
          );
        },
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              world ? Icons.public_rounded : Icons.auto_awesome_rounded,
              size: 46,
              color: world ? Colors.white : C.gold,
            ),
            const SizedBox(height: 16),
            Text(
              world ? '欢迎来到玑衡World' : '欢迎来到玑衡AI',
              style: TextStyle(
                fontFamily: 'serif',
                fontWeight: FontWeight.w800,
                fontSize: 22,
                color: world ? Colors.white : C.text,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              world ? '探索资本世界的协作图谱' : '你的智能金融操作系统',
              style: TextStyle(
                fontSize: 13,
                letterSpacing: 1,
                color: world ? const Color(0xFF9BA9BE) : C.muted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class JihengWorldView extends StatefulWidget {
  const JihengWorldView({super.key});

  @override
  State<JihengWorldView> createState() => _JihengWorldViewState();
}

class _JihengWorldViewState extends State<JihengWorldView> {
  late final WebViewController controller;
  bool loading = true;

  @override
  void initState() {
    super.initState();
    controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF0E1D31))
      ..setNavigationDelegate(NavigationDelegate(
        onPageFinished: (_) {
          if (mounted) setState(() => loading = false);
        },
      ))
      ..loadFlutterAsset('assets/game/procurement-journey.html');
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: const Color(0xFF0E1D31),
      child: Stack(
        children: [
          Positioned.fill(
            child: WebViewWidget(controller: controller),
          ),
          if (loading)
            const Positioned.fill(
              child: ColoredBox(
                color: Color(0xFF0E1D31),
                child: Center(
                  child: CircularProgressIndicator(
                    color: Color(0xFFD8B483),
                    strokeWidth: 2,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class DashedFramePainter extends CustomPainter {
  const DashedFramePainter();

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final rrect = RRect.fromRectAndRadius(
      rect.deflate(1),
      const Radius.circular(24),
    );
    final paint = Paint()
      ..color = const Color(0xFF988A70)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    final path = Path()..addRRect(rrect);
    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      const dash = 6.0;
      const gap = 6.0;
      while (distance < metric.length) {
        final next = distance + dash;
        canvas.drawPath(metric.extractPath(distance, next), paint);
        distance = next + gap;
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
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
              child: const Text('已为你接入实时行情、研究数据与分析师多Agent协作，今天想做什么？',
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
  [
    '个股分析师',
    'assets/prototype/expert-stock.png',
    '面向二级市场的个股研究搭档，围绕公司基本面、财报与事件、估…',
    'expert_stock_research'
  ],
  [
    '行业分析师',
    'assets/prototype/expert-industry.png',
    '面向股票投研团队的行业研究搭档，围绕行业、子行业、产业链环…',
    'expert_industry_research'
  ],
  [
    '财报分析师',
    'assets/prototype/expert-report.png',
    '解读上市公司定期报告，提炼营收利润、现金流、毛利率与同比变化…',
    'expert_research_report'
  ],
];

Color colorFromHex(dynamic value, Color fallback) {
  final text = value?.toString().replaceAll('#', '');
  if (text == null || text.length != 6) return fallback;
  return Color(int.parse('FF$text', radix: 16));
}

const planLabels = {'basic': '基础版', 'pro': '专业版', 'institution': '机构版'};

String planLabel(dynamic value) => planLabels[asText(value)] ?? asText(value);

const reportKindLabels = {
  'deep_research': '深度研究',
  'company': '公司研究',
  'company_research': '公司研究',
  'morning': '晨报',
  'morning_brief': '晨报',
};

String reportKindLabel(dynamic value) =>
    reportKindLabels[asText(value)] ?? asText(value, '深度研究');

const reportStateLabels = {
  'completed': '已完成',
  'draft': '草稿',
  'running': '生成中',
  'failed': '失败',
};

String reportStateLabel(dynamic value) =>
    reportStateLabels[asText(value)] ?? asText(value, '已完成');

String asTime(dynamic value) {
  final text = asText(value);
  final parsed = DateTime.tryParse(text);
  if (parsed == null) return text;
  final local = parsed.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(local.month)}-${two(local.day)} ${two(local.hour)}:${two(local.minute)}';
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
    const rows = expertOptions;
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
        final name = e[0];
        final image = e[1];
        final expertId = e[3];
        final picked = state.expert == name;
        return InkWell(
          onTap: () => state.mutate(() {
            state.expert = name;
            state.selectedExpertId = expertId;
            state.mode = '分析师';
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
                Container(
                  width: 52,
                  height: 52,
                  clipBehavior: Clip.antiAlias,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    border: Border.all(color: C.line),
                  ),
                  child: Transform.scale(
                    scale: 1.28,
                    child: Image.asset(image, fit: BoxFit.cover),
                  ),
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
    final intro = message.intro;
    final sections = message.sections;
    final rows = message.rows;
    final risk = message.risk;
    final refCount = message.refCount;
    final collab = message.collab;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const BrandAvatar(size: 30),
        const SizedBox(width: 10),
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (collab != null)
                CollabPanel(message: message, state: state)
              else ...[
                if (message.toolCalls.isNotEmpty) ...[
                  for (final call in message.toolCalls)
                    ToolCallTile(key: ValueKey(call.id), call: call),
                  const SizedBox(height: 4),
                ],
                if (intro.isNotEmpty)
                  MarkdownBody(
                    data: intro,
                    selectable: true,
                    styleSheet: answerMarkdownStyle,
                  ),
                if (message.stage != Stage.done) ...[
                  if (intro.isNotEmpty) const BlinkCursor(),
                  WaitLine(
                    startedAt: message.startedAt,
                    label: intro.isEmpty ? '正在等待回答' : '正在生成',
                  ),
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
                  child: Text('引用 $refCount 条 · 点击查看来源',
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
                    child: message.refList.isEmpty
                        ? const Text('本次回答未调用带来源的数据工具',
                            style: TextStyle(fontSize: 12, height: 1.55))
                        : _RefList(refs: message.refList),
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
                      onPressed: () => state
                          .toggleFavorite(intro.isEmpty ? message.flow : intro),
                      child: Text(
                          state.favorites.contains(intro) ? '取消收藏' : '收藏')),
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
        Align(
          alignment: Alignment.centerLeft,
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              ModeChip(state: state, label: '快速问答'),
              ModeChip(state: state, label: '深度研究'),
              ModeChip(
                state: state,
                label: state.mode == '分析师' && state.expert.isNotEmpty
                    ? state.expert
                    : '分析师',
                value: '分析师',
                expert: true,
              ),
              if (state.mode == '分析师')
                ModePill(
                  label: '多Agent协作',
                  selected: state.collabMode,
                  optional: true,
                  onTap: () => state.mutate(() {
                    state.collabMode = !state.collabMode;
                    if (state.collabMode && state.selectedExpertId.isEmpty) {
                      state.expert = state.activeExpertName;
                      state.selectedExpertId = state.activeExpertId;
                    }
                  }),
                ),
            ]),
          ),
        ),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(
            child: TextField(
              controller: state.input,
              minLines: 1,
              maxLines: 4,
              onChanged: (_) => state.mutate(() {}),
              onSubmitted: (_) {
                if (!state.sending) state.send();
              },
              decoration: InputDecoration(
                hintText: state.messages.isNotEmpty
                    ? null
                    : state.mode == '深度研究'
                        ? '输入研究问题'
                        : state.mode == '分析师' && state.collabMode
                            ? '输入要协作研究的问题'
                            : '输入问题',
                hintStyle: const TextStyle(color: C.muted, fontSize: 14),
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
            onTap: state.sending || state.input.text.trim().isEmpty
                ? null
                : state.send,
            borderRadius: BorderRadius.circular(999),
            child: Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: state.sending || state.input.text.trim().isNotEmpty
                    ? C.ink
                    : Colors.white,
                border: Border.all(
                    color: state.sending || state.input.text.trim().isNotEmpty
                        ? C.ink
                        : C.line),
              ),
              child: state.sending
                  ? const Padding(
                      padding: EdgeInsets.all(9),
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : Icon(Icons.arrow_upward,
                      size: 18,
                      color: state.input.text.trim().isEmpty
                          ? C.muted
                          : Colors.white),
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
      this.value,
      this.expert = false,
      super.key});
  final JihengShellState state;
  final String label;
  final String? value;
  final bool expert;

  @override
  Widget build(BuildContext context) {
    final mode = value ?? label;
    final selected = state.mode == mode;
    return ModePill(
      label: label,
      selected: selected,
      onTap: () {
        if (expert) {
          state.mutate(() => state.expertSheet = true);
        } else {
          state.mutate(() {
            state.mode = mode;
            state.expert = '';
            state.selectedExpertId = '';
            state.collabMode = false;
          });
        }
      },
    );
  }
}

class ModePill extends StatelessWidget {
  const ModePill(
      {required this.label,
      required this.selected,
      required this.onTap,
      this.optional = false,
      super.key});
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool optional;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Material(
        color: optional
            ? (selected ? C.goldSoft : Colors.transparent)
            : (selected ? C.goldSoft : C.faint),
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: EdgeInsets.symmetric(
                horizontal: optional ? 8 : 10, vertical: optional ? 1 : 4),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                  color: selected ? const Color(0xFFE4D7C4) : C.line),
            ),
            child: Text(
              label,
              softWrap: false,
              style: TextStyle(
                fontSize: optional ? 11 : 12,
                color: selected
                    ? C.gold
                    : (optional ? C.muted : const Color(0xFF4A5259)),
                fontFamily: 'Microsoft YaHei',
                fontFamilyFallback: const ['Segoe UI', 'sans-serif'],
              ),
            ),
          ),
        ),
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
    final source = state.api.accessToken == null ? fallback : state.apiReports;
    final reports = source
        .where((r) =>
            state.reportTab == '全部' ||
            reportKindLabel(r['kind']) == state.reportTab)
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
        child: reports.isEmpty
            ? const Center(
                child: Text('还没有报告',
                    style: TextStyle(color: C.muted, fontSize: 13.5)))
            : ListView(children: [
                for (final group in ['本周', '更早'])
                  if (reports
                      .any((r) => asText(r['group'], '本周') == group)) ...[
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 10, 16, 2),
                      child: Text(group,
                          style: const TextStyle(
                              color: Color(0xFFA3AAB0), fontSize: 11.5)),
                    ),
                    for (final report in reports
                        .where((r) => asText(r['group'], '本周') == group))
                      ReportTile(
                        report: report,
                        onOpen: () => state.openReport(report),
                      ),
                  ],
              ]),
      ),
    ]);
  }
}

class ReportTile extends StatelessWidget {
  const ReportTile(
      {required this.report, required this.onOpen, this.onExport, super.key});
  final Map<String, dynamic> report;
  final VoidCallback onOpen;
  final VoidCallback? onExport;

  @override
  Widget build(BuildContext context) {
    final status = reportStateLabel(report['state']);
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
            child: Text(reportKindLabel(report['kind']),
                style: const TextStyle(color: C.gold, fontSize: 10.5)),
          ),
          const SizedBox(width: 8),
          Text(asTime(report['createdAt'] ?? report['created_at']),
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
          if (onExport != null) ...[
            const SizedBox(width: 14),
            InkWell(
                onTap: onExport,
                child: const Text('导出',
                    style: TextStyle(
                        color: C.gold,
                        fontSize: 12,
                        fontWeight: FontWeight.w600))),
          ],
        ]),
      ]),
    );
  }
}

String _taskTitle(Map<String, dynamic> task) {
  final payload = task['payload'];
  if (payload is String && payload.startsWith('{')) {
    try {
      final decoded = jsonDecode(payload);
      if (decoded is Map && asText(decoded['title']).isNotEmpty) {
        return asText(decoded['title']);
      }
    } catch (_) {}
  }
  return asText(task['taskId'] ?? task['task_id']);
}

String _skillMeta(Map<String, dynamic> skill) {
  final preset = asText(skill['meta']);
  if (preset.isNotEmpty) return preset;
  final edited = asTime(skill['lastEditedAt']);
  final runs = int.tryParse('${skill['runCount'] ?? ''}');
  final parts = [
    if (edited.isNotEmpty) '最近编辑 $edited',
    if (runs != null && runs > 0) '已运行 $runs 次',
  ];
  return parts.join(' · ');
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
    final officialFallback = <Map<String, dynamic>>[
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
    final mineFallback = <Map<String, dynamic>>[
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
    final demo = state.api.accessToken == null;
    final official = demo ? officialFallback : state.apiSkills;
    final mine = demo ? mineFallback : state.customSkills;
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
    if (state.api.accessToken == null) {
      state.mutate(() => state.localCustomSkills.add(skill));
      return;
    }
    try {
      await state.api.post('/api/v1/skills', result);
      await state._loadSkills();
      state.snack('技能已创建');
    } catch (error) {
      state._rememberApiError(error);
      state.snack('技能创建失败');
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
              if (_skillMeta(skill).isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(_skillMeta(skill),
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
    final tasks = [...state.apiTasks, ...state.localTasks];
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
              onTap: state.createTask,
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
            title: asText(task['title'] ?? _taskTitle(task), '自动化任务'),
            subtitle:
                '${asText(task['type'], 'reminder')} · ${asText(task['status'], 'enabled')}'
                '${asText(task['cron']).isEmpty ? '' : ' · ${task['cron']}'}',
            trailing: '删除',
            onTrailingTap: () async {
              final id = asText(task['taskId'] ?? task['task_id']);
              if (id.isNotEmpty &&
                  state.isLoggedIn &&
                  !id.startsWith('local-') &&
                  task['type'] != 'deep_research') {
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
          CardTile(title: reminder, subtitle: '提醒任务'),
      ])),
    ]);
  }
}

class FavoritesView extends StatelessWidget {
  const FavoritesView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      PrototypeHeader(title: '我的收藏', onBack: () => state.go(PageKey.home)),
      Expanded(
        child: state.favorites.isEmpty
            ? const Center(
                child: Text('还没有收藏',
                    style: TextStyle(color: C.muted, fontSize: 13.5)))
            : ListView(children: [
                for (final item in state.favorites)
                  CardTile(
                    title: item.split('\n').first,
                    subtitle: '收藏的回答',
                    trailing: '取消',
                    onTrailingTap: () => state.toggleFavorite(item),
                    onTap: () =>
                        state.setPrompt(item.split('\n').first, 'generic'),
                  ),
              ]),
      ),
    ]);
  }
}

class NotificationsView extends StatelessWidget {
  const NotificationsView({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final remote = state.apiNotifications;
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
                    subtitle:
                        '${asText(notification['content'])} · ${asTime(notification['createdAt'])}',
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
    final p = state.profile ?? const <String, dynamic>{};
    final stats = p['stats'] is Map
        ? Map<String, dynamic>.from(p['stats'] as Map)
        : const <String, dynamic>{};
    final name = asText(p['displayName'], '未设置昵称');
    final rows = [
      ('账号与安全', asText(p['phone'], '未绑定')),
      ('订阅与积分', '${planLabel(p['plan'])} · ${asText(p['points'], '0')} 分'),
      ('数据权限', asText(p['dataScopes'], '未设置')),
      ('消息通知', p['notifyOn'] == false ? '已关闭' : '已开启'),
      (
        '偏好设置',
        asText(p['locale']) == 'zh_CN' ? '简体中文' : asText(p['locale'], '简体中文')
      ),
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
                child: Text(name.characters.first,
                    style: const TextStyle(
                        fontFamily: 'Noto Serif SC',
                        fontSize: 17,
                        color: Color(0xFFD8B483))),
              ),
              const SizedBox(width: 13),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    Text(name,
                        style: const TextStyle(
                            fontFamily: 'Noto Serif SC',
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.white)),
                    const SizedBox(height: 3),
                    Text(
                        '${planLabel(p['plan'])} · ${asText(p['department'], '未设置部门')}',
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
                (asText(stats['reportCount'], '0'), '生成报告'),
                (asText(stats['usageDays'], '0'), '使用天数'),
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
            onTap:
                row.$1 == '消息通知' ? () => state.go(PageKey.notifications) : null,
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
                if (row.$1 == '消息通知') ...[
                  const SizedBox(width: 12),
                  const Icon(Icons.chevron_right,
                      size: 17, color: Color(0xFFC9CFD4)),
                ],
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
    final controller =
        TextEditingController(text: asText(state.profile?['displayName']));
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
    final query = state.drawerSearch.text.trim().toLowerCase();
    final items = [
      ['新建对话', PageKey.home, Icons.chat_bubble_outline],
      ['我的报告', PageKey.reports, Icons.description_outlined],
      ['定时与提醒', PageKey.reminders, Icons.schedule],
      ['我的收藏', PageKey.favorites, Icons.star_border],
    ];
    final prototypeHistory = <({String day, String text, VoidCallback onTap})>[
      (day: '今天', text: '金融AI助手自我介绍', onTap: () => state.go(PageKey.home)),
      (
        day: '昨天',
        text: '做一份宁德时代（300750.SZ）三季报前瞻…',
        onTap: () {
          state.setPrompt('做一份宁德时代（300750.SZ）三季报前瞻', 'generic');
          state.go(PageKey.home);
        }
      ),
    ];
    final apiHistory = [
      for (final conversation in state.apiConversations)
        (
          day: '最近',
          text: asText(conversation['title'], '未命名对话'),
          onTap: () =>
              state.openConversation(asText(conversation['conversationId']))
        ),
    ];
    final history = apiHistory.isEmpty ? prototypeHistory : apiHistory;
    final filteredHistory = query.isEmpty
        ? history
        : history
            .where((item) => item.text.toLowerCase().contains(query))
            .toList();
    final historyDays = [
      for (final item in filteredHistory)
        if (!filteredHistory
            .take(filteredHistory.indexOf(item))
            .any((previous) => previous.day == item.day))
          item.day,
    ];

    return Stack(children: [
      Positioned.fill(
          child: GestureDetector(
              onTap: () => state.mutate(() => state.drawerOpen = false),
              child: Container(color: const Color(0x55000000)))),
      Align(
        alignment: Alignment.centerLeft,
        child: Material(
          color: Colors.white,
          child: Container(
            width: MediaQuery.of(context).size.width * .82,
            height: double.infinity,
            color: Colors.white,
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(20, 52, 20, 18),
                  children: [
                    const Row(children: [
                      BrandAvatar(size: 28),
                      SizedBox(width: 9),
                      Text('玑衡AI',
                          style: TextStyle(
                              fontFamily: 'Noto Serif SC',
                              fontWeight: FontWeight.w600,
                              fontSize: 15,
                              color: C.text)),
                    ]),
                    const SizedBox(height: 25),
                    for (final item in items)
                      _DrawerMenuRow(
                        icon: item[2] as IconData,
                        text: item[0] as String,
                        onTap: () {
                          if (item[0] == '新建对话') {
                            state.newChat();
                          } else {
                            state.go(item[1] as PageKey);
                          }
                        },
                      ),
                    const SizedBox(height: 14),
                    SizedBox(
                      height: 39,
                      child: TextField(
                        controller: state.drawerSearch,
                        cursorColor: C.gold,
                        onChanged: (_) => state.mutate(() {}),
                        style: const TextStyle(
                            color: Color(0xFF3D454C), fontSize: 12.5),
                        decoration: InputDecoration(
                          isDense: true,
                          hintText: '搜索历史对话',
                          hintStyle: const TextStyle(
                              color: Color(0xFF8B9299), fontSize: 12.5),
                          prefixIcon: const Icon(Icons.search_rounded,
                              size: 16, color: Color(0xFF8B9299)),
                          prefixIconConstraints:
                              const BoxConstraints(minWidth: 34),
                          contentPadding:
                              const EdgeInsets.symmetric(vertical: 10),
                          filled: true,
                          fillColor: const Color(0xFFF6F4F0),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide:
                                const BorderSide(color: Color(0xFFEDEAE3)),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide:
                                const BorderSide(color: Color(0xFFE4D7C4)),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    for (final day in historyDays) ...[
                      _DrawerDayLabel(day),
                      for (final item
                          in filteredHistory.where((item) => item.day == day))
                        _DrawerHistoryItem(text: item.text, onTap: item.onTap),
                    ],
                    if (filteredHistory.isEmpty)
                      const Padding(
                        padding: EdgeInsets.only(top: 10),
                        child: Text('没有匹配的历史对话',
                            style: TextStyle(
                                color: Color(0xFFA3AAB0), fontSize: 12.5)),
                      ),
                  ],
                ),
              ),
              InkWell(
                onTap: () => state.go(PageKey.profile),
                child: Container(
                  height: 63,
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 10),
                  decoration: const BoxDecoration(
                      border: Border(top: BorderSide(color: C.line))),
                  child: Row(children: [
                    const CircleAvatar(
                      radius: 16,
                      backgroundColor: Color(0xFFFFF8EA),
                      child: Text('用',
                          style: TextStyle(
                              fontFamily: 'Noto Serif SC',
                              fontWeight: FontWeight.w700,
                              color: C.gold,
                              fontSize: 13)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              asText(
                                  state.profile?['displayName'], 'USER_6450'),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  fontSize: 13.5,
                                  color: C.text,
                                  fontWeight: FontWeight.w400)),
                          const SizedBox(height: 2),
                          Text(
                              '${asText(state.profile?['plan'], '机构版')} · ${asText(state.profile?['department'], '研究部')}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  color: Color(0xFFA3AAB0), fontSize: 11.5)),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right_rounded,
                        size: 18, color: Color(0xFFC6CCD2)),
                  ]),
                ),
              ),
            ]),
          ),
        ),
      ),
    ]);
  }
}

class _DrawerMenuRow extends StatelessWidget {
  const _DrawerMenuRow({
    required this.icon,
    required this.text,
    required this.onTap,
  });

  final IconData icon;
  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 11),
        child: Row(children: [
          Icon(icon, size: 17, color: const Color(0xFF7D8790)),
          const SizedBox(width: 13),
          Text(text,
              style: const TextStyle(
                  color: C.text, fontWeight: FontWeight.w500, fontSize: 14.5)),
        ]),
      ),
    );
  }
}

class _DrawerDayLabel extends StatelessWidget {
  const _DrawerDayLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 10, bottom: 4),
      child: Text(text,
          style: const TextStyle(
              color: Color(0xFFA3AAB0),
              fontSize: 11.5,
              letterSpacing: .6,
              fontWeight: FontWeight.w400)),
    );
  }
}

class _DrawerHistoryItem extends StatelessWidget {
  const _DrawerHistoryItem({required this.text, required this.onTap});
  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Text(text,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
                color: Color(0xFF3D454C), fontSize: 13.5, height: 1.35)),
      ),
    );
  }
}

class ExpertSheet extends StatelessWidget {
  const ExpertSheet({required this.state, super.key});
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    const experts = expertOptions;
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
              padding: const EdgeInsets.fromLTRB(18, 18, 12, 10),
              child: Row(children: [
                const Text('选择分析师',
                    style: TextStyle(
                        fontFamily: 'Noto Serif SC',
                        fontWeight: FontWeight.w600,
                        fontSize: 16)),
                const Spacer(),
                IconButton(
                    onPressed: () =>
                        state.mutate(() => state.expertSheet = false),
                    icon: const Icon(Icons.close)),
              ]),
            ),
            Container(
              height: 40,
              margin: const EdgeInsets.fromLTRB(18, 0, 18, 6),
              padding: const EdgeInsets.symmetric(horizontal: 13),
              decoration: BoxDecoration(
                color: C.faint,
                border: Border.all(color: C.line),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(children: [
                Icon(Icons.search, size: 15, color: Color(0xFF8B9299)),
                SizedBox(width: 8),
                Text('搜索分析师',
                    style: TextStyle(color: Color(0xFF8B9299), fontSize: 13)),
              ]),
            ),
            Expanded(
              child: ListView(
                children: experts
                    .map((e) => ListTile(
                          contentPadding:
                              const EdgeInsets.symmetric(horizontal: 18),
                          leading: Container(
                            width: 40,
                            height: 40,
                            clipBehavior: Clip.antiAlias,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              shape: BoxShape.circle,
                              border: Border.all(color: C.line),
                            ),
                            child: Transform.scale(
                              scale: 1.28,
                              child: Image.asset(e[1], fit: BoxFit.cover),
                            ),
                          ),
                          title: Text(e[0]),
                          subtitle: Text(e[2]),
                          trailing: state.expert == e[0]
                              ? const Icon(Icons.check, color: C.green)
                              : null,
                          onTap: () => state.mutate(() {
                            state.expert = e[0];
                            state.selectedExpertId = e[3];
                            state.mode = '分析师';
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
    final summary = asText(report['summary'], '报告正文生成中，请稍后刷新查看。');
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
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('引用来源',
                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, height: 1.6)),
                const SizedBox(height: 4),
                if (report['refs'] is List && (report['refs'] as List).isNotEmpty)
                  _RefList(refs: (report['refs'] as List).map((item) {
                    final source = item is Map ? item : {'title': item};
                    return {
                      'title': (source['title'] ?? '').toString(),
                      'url': (source['url'] ?? '').toString(),
                    };
                  }).toList())
                else
                  Text(refs, style: const TextStyle(fontSize: 12.5, height: 1.6)),
              ],
            ),
          ),
          const SizedBox(height: 18),
          const Text('内容由 AI 生成，请核查重要信息。',
              style: TextStyle(color: C.muted, fontSize: 12)),
        ],
      ),
    );
  }
}

class _RefList extends StatelessWidget {
  const _RefList({required this.refs});
  final List<Map<String, String>> refs;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: refs.map((source) {
        final title = source['title'] ?? '';
        final url = source['url'] ?? '';
        if (url.isEmpty) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text('· $title',
                style: const TextStyle(fontSize: 12, height: 1.55)),
          );
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: GestureDetector(
            onTap: () => launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication),
            child: Text('· $title',
                style: const TextStyle(
                    fontSize: 12,
                    height: 1.55,
                    color: C.gold,
                    decoration: TextDecoration.underline,
                    decorationColor: C.gold)),
          ),
        );
      }).toList(),
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
      clipBehavior: Clip.antiAlias,
      decoration: const BoxDecoration(shape: BoxShape.circle, color: C.ink),
      child: Transform.scale(
        scale: 1.72,
        child: Image.asset('logo.png', fit: BoxFit.cover),
      ),
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

class WaitLine extends StatefulWidget {
  const WaitLine({required this.startedAt, required this.label, super.key});
  final DateTime startedAt;
  final String label;

  @override
  State<WaitLine> createState() => _WaitLineState();
}

class _WaitLineState extends State<WaitLine> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final elapsed = DateTime.now().difference(widget.startedAt);
    final seconds = elapsed.inSeconds.clamp(0, 359999);
    final text = seconds >= 60
        ? '${seconds ~/ 60}分${(seconds % 60).toString().padLeft(2, '0')}秒'
        : '$seconds秒';
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(children: [
        const SizedBox(
          width: 14,
          height: 14,
          child: CircularProgressIndicator(strokeWidth: 2, color: C.gold),
        ),
        const SizedBox(width: 8),
        Text('${widget.label} · 已等待 $text',
            style: const TextStyle(color: C.muted, fontSize: 12.5)),
      ]),
    );
  }
}

class BlinkCursor extends StatefulWidget {
  const BlinkCursor({super.key});

  @override
  State<BlinkCursor> createState() => _BlinkCursorState();
}

class _BlinkCursorState extends State<BlinkCursor>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 700),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _controller,
      child: const Padding(
        padding: EdgeInsets.only(top: 2),
        child: SizedBox(width: 2, height: 16, child: ColoredBox(color: C.ink)),
      ),
    );
  }
}

class ToolCallTile extends StatefulWidget {
  const ToolCallTile({required this.call, super.key});
  final ToolCallData call;

  @override
  State<ToolCallTile> createState() => _ToolCallTileState();
}

class _ToolCallTileState extends State<ToolCallTile> {
  bool? userOpen;

  @override
  Widget build(BuildContext context) {
    final call = widget.call;
    final open = userOpen ?? call.running;
    final label = toolLabels[call.name] ?? call.name;
    final title = call.running
        ? '正在获取$label'
        : (call.success! ? '已获取$label' : '获取$label失败');
    final rawReason =
        (call.result ?? '').replaceAll(RegExp(r'\s+'), ' ').trim();
    final reason = call.success == false
        ? (rawReason.length > 48 ? '${rawReason.substring(0, 48)}…' : rawReason)
        : '';
    final Widget status = call.running
        ? const SizedBox(
            width: 12,
            height: 12,
            child: CircularProgressIndicator(strokeWidth: 1.8))
        : Text(call.success! ? '成功' : '失败',
            style: TextStyle(
                color: call.success! ? C.green : Colors.red.shade700,
                fontSize: 12));
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFE7E5E0)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        InkWell(
          onTap: () => setState(() => userOpen = !open),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
            child: Row(children: [
              const Icon(Icons.build_outlined, size: 14, color: C.gold),
              const SizedBox(width: 6),
              Expanded(
                child: Text(title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: C.gold,
                        fontWeight: FontWeight.w600,
                        fontSize: 12.5)),
              ),
              status,
              const SizedBox(width: 4),
              Icon(open ? Icons.expand_less : Icons.expand_more,
                  size: 16, color: C.muted),
            ]),
          ),
        ),
        if (reason.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(31, 0, 11, 8),
            child: Text(reason,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                    color: Colors.red.shade700, fontSize: 12, height: 1.4)),
          ),
        if (open)
          Padding(
            padding: const EdgeInsets.fromLTRB(11, 0, 11, 10),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _block('入参', prettyJson(call.input)),
                  if (!call.running) ...[
                    const SizedBox(height: 8),
                    _block('出参', prettyJson(call.result)),
                  ],
                ]),
          ),
      ]),
    );
  }

  Widget _block(String title, String body) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text(title, style: const TextStyle(color: C.muted, fontSize: 11.5)),
      const SizedBox(height: 4),
      Container(
        constraints: const BoxConstraints(maxHeight: 220),
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
            color: const Color(0xFFF7F6F3),
            borderRadius: BorderRadius.circular(6)),
        child: SingleChildScrollView(
          child: SelectableText(body.isEmpty ? '（空）' : body,
              style: const TextStyle(
                  fontFamily: 'monospace', fontSize: 11.5, height: 1.45)),
        ),
      ),
    ]);
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
      this.trailing = '',
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
