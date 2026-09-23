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
}
