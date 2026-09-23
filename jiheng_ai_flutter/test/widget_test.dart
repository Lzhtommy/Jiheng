import 'package:flutter_test/flutter_test.dart';

import 'package:jiheng_ai_flutter/main.dart';

void main() {
  testWidgets('renders the home page', (WidgetTester tester) async {
    await tester.pumpWidget(const JihengApp());

    expect(find.text('玑衡AI'), findsOneWidget);
    expect(find.text('你的智能金融操作系统'), findsOneWidget);
  });
}
