import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jiheng_ai_flutter/collab.dart';
import 'package:jiheng_ai_flutter/main.dart';

Map<String, dynamic> planResponse() => {
      'plan': {
        'goal': '对比茅台与五粮液',
        'coverage': ['行情'],
        'excluded': [],
        'nodes': [
          {'id': 'n1', 'parent': null, 'role': '首席分析师', 'title': '汇总'},
          {
            'id': 'n2',
            'parent': 'n1',
            'role': '行情分析员',
            'title': '行情估值',
            'instruction': '查询 sh600519、sz000858',
            'tools': ['get_realtime_quote'],
          },
          {
            'id': 'n3',
            'parent': 'n1',
            'role': '资料员',
            'title': '公告',
            'instruction': '查询公告',
            'tools': ['list_announcements'],
          },
        ],
      },
      'tools': ['get_realtime_quote', 'list_announcements'],
      'max_nodes': 5,
    };

void main() {
  test('loads plan and validates structure', () {
    final collab = CollabData(question: 'q', history: [])
      ..loadPlan(planResponse());
    expect(collab.root?.id, 'n1');
    expect(collab.children('n1').map((n) => n.id), ['n2', 'n3']);
    expect(collab.validate(), isEmpty);

    collab.nodes[2].tools.clear();
    expect(collab.validate(), contains('「公告」至少选择一个工具'));

    collab.nodes[2].tools.add('list_announcements');
    collab.nodes.addAll([
      for (final id in ['n4', 'n5', 'n6'])
        PlanNodeData(
            id: id,
            parent: 'n1',
            role: 'r',
            title: id,
            instruction: 'x',
            tools: ['get_realtime_quote']),
    ]);
    expect(collab.validate(), contains('节点数 6 超过上限 5'));
  });

  testWidgets('graph renders every node with status', (tester) async {
    final collab = CollabData(question: 'q', history: [])
      ..loadPlan(planResponse());
    collab.nodes[1].status = 'running';
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: CollabGraph(collab: collab, onTap: (_) {})),
    ));
    expect(find.text('行情估值'), findsOneWidget);
    expect(find.text('汇总'), findsOneWidget);
    expect(find.text('执行中'), findsOneWidget);
  });

  testWidgets('narrow layout keeps node edges centered', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final collab = CollabData(question: 'q', history: [])
      ..loadPlan(planResponse());
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: CollabGraph(collab: collab, onTap: (_) {})),
    ));

    final root = tester.getRect(find.byType(InkWell).at(0));
    final left = tester.getRect(find.byType(InkWell).at(1));
    final right = tester.getRect(find.byType(InkWell).at(2));
    expect(root.center.dx, closeTo((left.center.dx + right.center.dx) / 2, 1));
    expect(left.width, lessThan(100));
    expect(tester.takeException(), isNull);
  });

  testWidgets('confirm actions stack on a phone width', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final state = JihengShellState();
    final collab = CollabData(question: 'q', history: [])
      ..loadPlan(planResponse())
      ..phase = 'confirm';
    final message = ChatMsg.ai('generic')..collab = collab;

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: CollabPanel(message: message, state: state)),
    ));
    await tester.pump();

    final run = tester.getRect(find.widgetWithText(FilledButton, '按此计划执行'));
    final edit = tester.getRect(find.widgetWithText(OutlinedButton, '编辑计划'));
    expect(run.bottom, lessThanOrEqualTo(edit.top));
    expect(run.width, greaterThan(300));
    expect(tester.takeException(), isNull);
  });
}
