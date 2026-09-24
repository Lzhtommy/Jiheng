import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:jiheng_ai_flutter/main.dart';

void main() {
  testWidgets('renders the login page before auth',
      (WidgetTester tester) async {
    await tester.pumpWidget(const JihengApp());
    await tester.pump(const Duration(milliseconds: 1500));

    expect(find.text('玑衡AI'), findsOneWidget);
    expect(find.text('你的智能金融操作系统'), findsOneWidget);
    expect(find.text('登录'), findsOneWidget);
  });

  testWidgets('skills start with all prototype entries enabled',
      (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(375, 812));
    final state = JihengShellState();
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: SkillsView(state: state)),
    ));

    expect(find.text('12 个技能已开启'), findsOneWidget);
    expect(find.text('有色板块深度透视'), findsOneWidget);
    expect(find.text('期权定价计算器'), findsOneWidget);
    expect(find.text('机构持仓透视'), findsOneWidget);
  });

  testWidgets('report detail decodes archived reference JSON',
      (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: ReportDetailPage(report: {
        'title': '测试报告',
        'content': '报告正文',
        'refs': '[{"title":"交易所公告","url":"https://example.com/report"}]',
      }),
    ));

    expect(find.text('· 交易所公告'), findsOneWidget);
    expect(find.textContaining('"url"'), findsNothing);
  });

  testWidgets('report detail renders markdown content',
      (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: ReportDetailPage(report: {
        'title': 'Markdown 报告',
        'content': '# 核心结论\n\n**营收持续增长**\n\n- 依据一\n- 依据二',
        'refs': '[]',
      }),
    ));

    expect(find.text('核心结论'), findsOneWidget);
    expect(find.text('营收持续增长'), findsOneWidget);
    expect(find.text('依据一'), findsOneWidget);
    expect(find.textContaining('# 核心结论'), findsNothing);
    expect(find.textContaining('**营收持续增长**'), findsNothing);
  });

  testWidgets('completed answer uses icon actions instead of favorite text',
      (WidgetTester tester) async {
    final state = JihengShellState();
    final message = ChatMsg.ai('generic')
      ..sourceQuestion = '测试问题'
      ..intro = '测试回答'
      ..stage = Stage.done;

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: MessageBubble(message: message, state: state)),
    ));

    expect(find.byIcon(Icons.copy_outlined), findsOneWidget);
    expect(find.byIcon(Icons.description_outlined), findsOneWidget);
    expect(find.byTooltip('复制'), findsOneWidget);
    expect(find.byTooltip('生成报告'), findsOneWidget);
    expect(find.text('收藏'), findsNothing);
    expect(find.widgetWithText(TextButton, '复制'), findsNothing);
  });

  testWidgets('drawer hides favorites entry', (WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: DrawerOverlay(state: JihengShellState())),
    ));

    expect(find.text('我的报告'), findsOneWidget);
    expect(find.text('我的收藏'), findsNothing);
  });

  test('report content includes structured answer data', () {
    final message = ChatMsg.ai('generic')
      ..intro = '结论'
      ..sections.add(const SectionData('依据', ['数据一']))
      ..rows.add(['营收', '100亿元'])
      ..risk = '请核查重要信息';

    expect(reportContent(message), contains('## 依据'));
    expect(reportContent(message), contains('营收 | 100亿元'));
    expect(reportContent(message), contains('请核查重要信息'));
  });
}
