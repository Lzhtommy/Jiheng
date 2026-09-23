import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';

import 'main.dart';

const collabPhases = [
  ('planning', '规划'),
  ('confirm', '确认计划'),
  ('research', '并行调研'),
  ('review', '审核'),
  ('writing', '成稿'),
];

const nodeStatusLabels = {
  'pending': '待执行',
  'running': '执行中',
  'waiting': '等待下级',
  'submitted': '已提交',
  'reviewing': '审核中',
  'revising': '补充中',
  'approved': '已通过',
  'failed': '失败',
  'done': '已完成',
};

const messageKindLabels = {
  'assign': '派发',
  'submit': '提交',
  'feedback': '打回',
  'approve': '通过',
};

Color nodeStatusColor(String status) => switch (status) {
      'running' || 'reviewing' => const Color(0xFF2F6FDB),
      'waiting' => const Color(0xFF7A8CA8),
      'submitted' => C.gold,
      'revising' => const Color(0xFFD9822B),
      'approved' || 'done' => C.green,
      'failed' => const Color(0xFFC62828),
      _ => const Color(0xFFB5B9BE),
    };

Color messageKindColor(String kind) => switch (kind) {
      'assign' => const Color(0xFF2F6FDB),
      'submit' => C.gold,
      'feedback' => const Color(0xFFD9822B),
      'approve' => C.green,
      _ => C.muted,
    };

class PlanNodeData {
  PlanNodeData({
    required this.id,
    required this.parent,
    required this.role,
    required this.title,
    this.instruction = '',
    this.expectedOutput = '',
    List<String>? tools,
  }) : tools = tools ?? [];

  factory PlanNodeData.fromJson(Map<String, dynamic> json) => PlanNodeData(
        id: json['id'].toString(),
        parent: json['parent']?.toString(),
        role: json['role']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        instruction: json['instruction']?.toString() ?? '',
        expectedOutput: json['expected_output']?.toString() ?? '',
        tools: (json['tools'] as List? ?? []).map((e) => e.toString()).toList(),
      );

  final String id;
  String? parent;
  String role;
  String title;
  String instruction;
  String expectedOutput;
  List<String> tools;
  String status = 'pending';
  int attempt = 0;
  String output = '';
  final List<ToolCallData> toolCalls = [];

  PlanNodeData copy() => PlanNodeData(
        id: id,
        parent: parent,
        role: role,
        title: title,
        instruction: instruction,
        expectedOutput: expectedOutput,
        tools: [...tools],
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'parent': parent,
        'role': role,
        'title': title,
        'instruction': instruction,
        'expected_output': expectedOutput,
        'tools': tools,
      };
}

class CollabMessage {
  const CollabMessage(this.id, this.from, this.to, this.kind, this.summary);
  final int id;
  final String from;
  final String? to;
  final String kind;
  final String summary;
}

class CollabData {
  CollabData({required this.question, required this.history});

  final String question;
  final List<Map<String, dynamic>> history;
  String phase = 'planning';
  String goal = '';
  List<String> coverage = [];
  List<String> excluded = [];
  List<PlanNodeData> nodes = [];
  List<String> tools = [];
  int maxNodes = 5;
  bool graphOpen = true;
  bool timelineOpen = false;
  final List<CollabMessage> messages = [];
  final revision = ValueNotifier(0);

  void loadPlan(Map<String, dynamic> data) {
    final plan = Map<String, dynamic>.from(data['plan'] as Map);
    goal = plan['goal']?.toString() ?? '';
    coverage =
        (plan['coverage'] as List? ?? []).map((e) => e.toString()).toList();
    excluded =
        (plan['excluded'] as List? ?? []).map((e) => e.toString()).toList();
    nodes = (plan['nodes'] as List? ?? [])
        .map((e) => PlanNodeData.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
    tools = (data['tools'] as List? ?? []).map((e) => e.toString()).toList();
    maxNodes = int.tryParse(data['max_nodes']?.toString() ?? '') ?? maxNodes;
  }

  PlanNodeData? get root {
    for (final node in nodes) {
      if (node.parent == null) return node;
    }
    return null;
  }

  PlanNodeData? byId(String? id) {
    for (final node in nodes) {
      if (node.id == id) return node;
    }
    return null;
  }

  List<PlanNodeData> children(String id) =>
      nodes.where((node) => node.parent == id).toList();

  int depth(PlanNodeData node) {
    var depth = 1;
    var current = node;
    while (current.parent != null) {
      final parent = byId(current.parent);
      if (parent == null) break;
      current = parent;
      depth++;
    }
    return depth;
  }

  List<PlanNodeData> ordered() {
    final result = <PlanNodeData>[];
    void visit(PlanNodeData node) {
      result.add(node);
      children(node.id).forEach(visit);
    }

    final top = root;
    if (top != null) visit(top);
    return result;
  }

  bool get running =>
      phase == 'research' || phase == 'review' || phase == 'writing';

  int get finishedCount => nodes
      .where((n) => const {'approved', 'done', 'failed'}.contains(n.status))
      .length;

  List<String> validate() {
    final errors = <String>[];
    final top = root;
    if (nodes.length > maxNodes) {
      errors.add('节点数 ${nodes.length} 超过上限 $maxNodes');
    }
    if (top == null) return [...errors, '缺少根节点'];
    if (children(top.id).length < 2) errors.add('首席分析师下至少需要两个任务');
    for (final node in nodes) {
      final kids = children(node.id);
      if (node.title.trim().isEmpty) errors.add('有节点缺少标题');
      if (node.parent != null && kids.isNotEmpty && kids.length < 3) {
        errors.add('「${node.title}」作为中间节点至少需要 3 个下级');
      }
      if (kids.isEmpty) {
        if (node.instruction.trim().isEmpty) {
          errors.add('「${node.title}」缺少任务说明');
        }
        if (node.tools.isEmpty) errors.add('「${node.title}」至少选择一个工具');
      }
    }
    return errors;
  }

  Map<String, dynamic> toPlanJson() => {
        'goal': goal,
        'coverage': coverage,
        'excluded': excluded,
        'nodes': nodes.map((n) => n.toJson()).toList(),
      };
}

class CollabPanel extends StatelessWidget {
  const CollabPanel({required this.message, required this.state, super.key});
  final ChatMsg message;
  final JihengShellState state;

  @override
  Widget build(BuildContext context) {
    final collab = message.collab!;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE7E5E0)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.hub_outlined, size: 16, color: C.gold),
          const SizedBox(width: 6),
          const Text('多智能体协作',
              style: TextStyle(
                  color: C.gold, fontWeight: FontWeight.w700, fontSize: 13)),
          const Spacer(),
          if (collab.running)
            Text('进度 ${collab.finishedCount}/${collab.nodes.length}',
                style: const TextStyle(color: C.muted, fontSize: 12)),
        ]),
        const SizedBox(height: 10),
        PhaseBar(phase: collab.phase),
        if (collab.phase == 'planning') ...[
          const SizedBox(height: 12),
          const Row(children: [
            SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(strokeWidth: 2)),
            SizedBox(width: 8),
            Text('正在规划研究任务，约 30~60 秒…',
                style: TextStyle(color: C.muted, fontSize: 12.5)),
          ]),
        ],
        if (collab.goal.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('研究目标：${collab.goal}',
              style: const TextStyle(fontSize: 13, height: 1.55)),
        ],
        if (collab.phase == 'confirm') ...[
          if (collab.coverage.isNotEmpty) ...[
            const SizedBox(height: 8),
            _scopeLine('覆盖维度', collab.coverage.join('；')),
          ],
          if (collab.excluded.isNotEmpty)
            _scopeLine('本次不覆盖', collab.excluded.join('；')),
        ],
        if (collab.nodes.isNotEmpty) ...[
          const SizedBox(height: 10),
          if (collab.phase != 'confirm')
            InkWell(
              onTap: () =>
                  state.mutate(() => collab.graphOpen = !collab.graphOpen),
              child: Row(children: [
                Text(collab.graphOpen ? '收起协作图谱' : '展开协作图谱',
                    style: const TextStyle(color: C.gold, fontSize: 12.5)),
                Icon(collab.graphOpen ? Icons.expand_less : Icons.expand_more,
                    size: 16, color: C.gold),
              ]),
            ),
          if (collab.phase == 'confirm' || collab.graphOpen) ...[
            const SizedBox(height: 8),
            CollabGraph(
                collab: collab,
                onTap: (node) => _showNode(context, collab, node)),
          ],
        ],
        if (collab.phase == 'confirm') ...[
          const SizedBox(height: 12),
          LayoutBuilder(builder: (context, constraints) {
            final narrow = constraints.maxWidth < 460;
            final edit = OutlinedButton(
                onPressed: () => state.editCollabPlan(message),
                child: const Text('编辑计划'));
            final run = FilledButton(
                style: FilledButton.styleFrom(backgroundColor: C.ink),
                onPressed: () => state.runCollab(message),
                child: const Text('按此计划执行'));
            final cancel = TextButton(
                onPressed: () => state.cancelCollab(message),
                child: const Text('取消'));
            if (!narrow) {
              return Row(children: [
                edit,
                const SizedBox(width: 8),
                run,
                const Spacer(),
                cancel,
              ]);
            }
            return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  run,
                  const SizedBox(height: 8),
                  Row(children: [
                    Expanded(child: edit),
                    const SizedBox(width: 8),
                    Expanded(child: cancel),
                  ]),
                ]);
          }),
        ],
        if (collab.messages.isNotEmpty) ...[
          const SizedBox(height: 10),
          InkWell(
            onTap: () =>
                state.mutate(() => collab.timelineOpen = !collab.timelineOpen),
            child: Row(children: [
              Expanded(
                child: Text(
                  '协作记录 ${collab.messages.length} 条 · 最新：${_messageText(collab, collab.messages.last)}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: C.muted, fontSize: 12),
                ),
              ),
              Icon(collab.timelineOpen ? Icons.expand_less : Icons.expand_more,
                  size: 16, color: C.muted),
            ]),
          ),
          if (collab.timelineOpen)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final item in collab.messages)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              margin: const EdgeInsets.only(top: 5, right: 6),
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                  color: messageKindColor(item.kind),
                                  shape: BoxShape.circle),
                            ),
                            Expanded(
                              child: Text(_messageText(collab, item),
                                  style: const TextStyle(
                                      fontSize: 12, height: 1.5)),
                            ),
                          ]),
                    ),
                ],
              ),
            ),
        ],
      ]),
    );
  }

  Widget _scopeLine(String label, String text) => Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Text('$label：$text',
            style: const TextStyle(color: C.muted, fontSize: 12, height: 1.55)),
      );

  String _messageText(CollabData collab, CollabMessage item) {
    final from = collab.byId(item.from)?.role ?? item.from;
    final to = collab.byId(item.to)?.role ?? '';
    final kind = messageKindLabels[item.kind] ?? item.kind;
    return '$from → $to · $kind：${item.summary}';
  }

  void _showNode(BuildContext context, CollabData collab, PlanNodeData node) {
    final narrow = MediaQuery.sizeOf(context).width < 600;
    if (narrow) {
      Navigator.of(context).push(MaterialPageRoute<void>(
        builder: (_) => NodeDetailPage(collab: collab, node: node),
      ));
      return;
    }
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: .7,
        maxChildSize: .95,
        builder: (_, controller) => ValueListenableBuilder(
          valueListenable: collab.revision,
          builder: (_, __, ___) =>
              NodeDetail(collab: collab, node: node, controller: controller),
        ),
      ),
    );
  }
}

class PhaseBar extends StatelessWidget {
  const PhaseBar({required this.phase, super.key});
  final String phase;

  @override
  Widget build(BuildContext context) {
    final current = phase == 'done'
        ? collabPhases.length
        : collabPhases.indexWhere((p) => p.$1 == phase);
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(children: [
        for (var i = 0; i < collabPhases.length; i++) ...[
          if (i > 0)
            Container(
                width: 14,
                height: 1,
                color: i <= current ? C.gold : C.line,
                margin: const EdgeInsets.symmetric(horizontal: 4)),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: i == current ? C.goldSoft : Colors.transparent,
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                  color: i <= current ? C.gold : C.line,
                  width: i == current ? 1.2 : 1),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              if (i < current)
                const Icon(Icons.check, size: 12, color: C.gold)
              else if (i == current && phase != 'confirm')
                const SizedBox(
                    width: 10,
                    height: 10,
                    child: CircularProgressIndicator(strokeWidth: 1.5)),
              if (i <= current) const SizedBox(width: 4),
              Text(collabPhases[i].$2,
                  style: TextStyle(
                      fontSize: 11.5,
                      color: i <= current ? C.gold : C.muted,
                      fontWeight:
                          i == current ? FontWeight.w600 : FontWeight.w400)),
            ]),
          ),
        ],
      ]),
    );
  }
}

class CollabGraph extends StatelessWidget {
  const CollabGraph({required this.collab, required this.onTap, super.key});
  final CollabData collab;
  final void Function(PlanNodeData node) onTap;

  static const nodeWidth = 112.0;
  static const nodeHeight = 64.0;

  static double nodeWidthFor(double available) =>
      (available < 480 ? 96.0 : nodeWidth);
  static const gapX = 12.0;
  static const gapY = 34.0;

  @override
  Widget build(BuildContext context) {
    final root = collab.root;
    if (root == null) return const SizedBox.shrink();
    final latest = collab.messages.isEmpty ? null : collab.messages.last;

    return LayoutBuilder(builder: (context, constraints) {
      final availableWidth = constraints.maxWidth.isFinite
          ? constraints.maxWidth
          : MediaQuery.sizeOf(context).width;
      final nodeWidth = nodeWidthFor(availableWidth);
      final layout =
          _GraphLayout.forWidth(collab, root, availableWidth, nodeWidth);
      final graph = SizedBox(
        width: layout.width,
        height: layout.height,
        child: Stack(children: [
          Positioned.fill(
            child: TweenAnimationBuilder<double>(
              key: ValueKey(latest?.id ?? 0),
              tween: Tween(begin: 0, end: 1),
              duration: const Duration(milliseconds: 900),
              builder: (_, progress, __) => CustomPaint(
                painter: _EdgePainter(
                    collab, layout.positions, latest, progress, nodeWidth),
              ),
            ),
          ),
          for (final node in collab.nodes)
            if (layout.positions[node.id] != null)
              Positioned(
                left: layout.positions[node.id]!.dx,
                top: layout.positions[node.id]!.dy,
                child: _NodeBox(
                    node: node, width: nodeWidth, onTap: () => onTap(node)),
              ),
        ]),
      );
      return SizedBox(
        width: double.infinity,
        height: layout.height,
        child: Align(alignment: Alignment.topCenter, child: graph),
      );
    });
  }
}

class _GraphLayout {
  const _GraphLayout(this.positions, this.width, this.height, this.nodeWidth);
  final Map<String, Offset> positions;
  final double width;
  final double height;
  final double nodeWidth;

  static const _nodeHeight = CollabGraph.nodeHeight;
  static const _gapX = CollabGraph.gapX;
  static const _gapY = CollabGraph.gapY;

  factory _GraphLayout.forWidth(CollabData collab, PlanNodeData root,
      double availableWidth, double nodeWidth) {
    final natural = _natural(collab, root, nodeWidth);
    if (natural.width <= availableWidth) return natural;

    final rootChildren = collab.children(root.id);
    final directOnly = collab.nodes
        .every((node) => node.id == root.id || node.parent == root.id);
    if (!directOnly || rootChildren.length < 3) return natural;

    return _wrappedRoot(root, rootChildren, availableWidth, nodeWidth);
  }

  static _GraphLayout _natural(
      CollabData collab, PlanNodeData root, double nodeWidth) {
    final positions = <String, Offset>{};
    var cursor = 0.0;

    void place(PlanNodeData node, int level) {
      final kids = collab.children(node.id);
      final y = level * (_nodeHeight + _gapY);
      if (kids.isEmpty) {
        positions[node.id] = Offset(cursor, y);
        cursor += nodeWidth + _gapX;
        return;
      }
      for (final kid in kids) {
        place(kid, level + 1);
      }
      final first = positions[kids.first.id]!.dx;
      final last = positions[kids.last.id]!.dx;
      positions[node.id] = Offset((first + last) / 2, y);
    }

    place(root, 0);
    final width = math.max(cursor - _gapX, nodeWidth);
    final height =
        positions.values.map((p) => p.dy).reduce(math.max) + _nodeHeight + 2;
    return _GraphLayout(positions, width, height, nodeWidth);
  }

  static _GraphLayout _wrappedRoot(PlanNodeData root,
      List<PlanNodeData> children, double availableWidth, double nodeWidth) {
    final maxColumns =
        math.max(1, ((availableWidth + _gapX) / (nodeWidth + _gapX)).floor());
    final columns =
        children.length <= 3 ? math.min(children.length, maxColumns) : 2;
    final safeColumns = math.max(1, columns);
    final rowWidth = safeColumns * nodeWidth + (safeColumns - 1) * _gapX;
    final width = math.max(rowWidth, nodeWidth);
    final positions = <String, Offset>{
      root.id: Offset((width - nodeWidth) / 2, 0),
    };

    for (var i = 0; i < children.length; i += 1) {
      final row = i ~/ safeColumns;
      final col = i % safeColumns;
      final rowCount =
          math.min(safeColumns, children.length - row * safeColumns);
      final currentRowWidth = rowCount * nodeWidth + (rowCount - 1) * _gapX;
      final rowOffset = (width - currentRowWidth) / 2;
      positions[children[i].id] = Offset(
        rowOffset + col * (nodeWidth + _gapX),
        _nodeHeight + _gapY + row * (_nodeHeight + _gapY * .55),
      );
    }

    final rows = ((children.length + safeColumns - 1) / safeColumns).ceil();
    final height = _nodeHeight +
        _gapY +
        rows * _nodeHeight +
        math.max(0, rows - 1) * _gapY * .55 +
        2;
    return _GraphLayout(positions, width, height, nodeWidth);
  }
}

class _EdgePainter extends CustomPainter {
  _EdgePainter(
      this.collab, this.positions, this.latest, this.progress, this.nodeWidth);
  final CollabData collab;
  final Map<String, Offset> positions;
  final CollabMessage? latest;
  final double progress;
  final double nodeWidth;

  static const h = CollabGraph.nodeHeight;

  Path _edge(Offset parent, Offset child) {
    final start = parent.translate(nodeWidth / 2, h);
    final end = child.translate(nodeWidth / 2, 0);
    final midY = (start.dy + end.dy) / 2;
    return Path()
      ..moveTo(start.dx, start.dy)
      ..lineTo(start.dx, midY)
      ..lineTo(end.dx, midY)
      ..lineTo(end.dx, end.dy);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final base = Paint()
      ..color = const Color(0xFFD9D5CC)
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke;
    for (final node in collab.nodes) {
      final parent = positions[node.parent];
      final child = positions[node.id];
      if (parent == null || child == null) continue;
      canvas.drawPath(_edge(parent, child), base);
    }
    final message = latest;
    if (message == null || message.to == null) return;
    final ids = {message.from, message.to};
    PlanNodeData? child;
    for (final node in collab.nodes) {
      if (node.parent != null && ids.containsAll({node.id, node.parent})) {
        child = node;
      }
    }
    if (child == null) return;
    final path = _edge(positions[child.parent]!, positions[child.id]!);
    final color = messageKindColor(message.kind);
    canvas.drawPath(
        path,
        Paint()
          ..color = color
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke);
    final metric = path.computeMetrics().first;
    final upward = message.from == child.id;
    final t = upward ? 1 - progress : progress;
    final point = metric.getTangentForOffset(metric.length * t)?.position;
    if (point != null) {
      canvas.drawCircle(point, 4.5, Paint()..color = color);
      canvas.drawCircle(point, 7, Paint()..color = color.withAlpha(60));
    }
  }

  @override
  bool shouldRepaint(covariant _EdgePainter old) => true;
}

class _NodeBox extends StatelessWidget {
  const _NodeBox(
      {required this.node, required this.width, required this.onTap});
  final PlanNodeData node;
  final double width;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = nodeStatusColor(node.status);
    final busy =
        const {'running', 'reviewing', 'revising'}.contains(node.status);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(9),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: width,
        height: CollabGraph.nodeHeight,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: node.status == 'pending' ? Colors.white : color.withAlpha(22),
          borderRadius: BorderRadius.circular(9),
          border: Border.all(color: color, width: busy ? 1.8 : 1.1),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(node.role,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 10.5, color: C.muted)),
            Text(node.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                    fontSize: 12.5, fontWeight: FontWeight.w600)),
            const Spacer(),
            Row(children: [
              if (busy)
                SizedBox(
                    width: 9,
                    height: 9,
                    child: CircularProgressIndicator(
                        strokeWidth: 1.4, color: color))
              else
                Container(
                    width: 7,
                    height: 7,
                    decoration:
                        BoxDecoration(color: color, shape: BoxShape.circle)),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                    '${nodeStatusLabels[node.status] ?? node.status}${node.attempt > 1 ? ' · 第${node.attempt}次' : ''}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 10.5, color: color)),
              ),
            ]),
          ],
        ),
      ),
    );
  }
}

class NodeDetailPage extends StatelessWidget {
  const NodeDetailPage({required this.collab, required this.node, super.key});
  final CollabData collab;
  final PlanNodeData node;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: ValueListenableBuilder(
          valueListenable: collab.revision,
          builder: (_, __, ___) => Text(node.role,
              style: const TextStyle(fontSize: 16),
              overflow: TextOverflow.ellipsis),
        ),
      ),
      body: ValueListenableBuilder(
        valueListenable: collab.revision,
        builder: (_, __, ___) =>
            NodeDetail(collab: collab, node: node, showHandle: false),
      ),
    );
  }
}

class NodeDetail extends StatelessWidget {
  const NodeDetail(
      {required this.collab,
      required this.node,
      this.controller,
      this.showHandle = true,
      super.key});
  final CollabData collab;
  final PlanNodeData node;
  final ScrollController? controller;
  final bool showHandle;

  @override
  Widget build(BuildContext context) {
    final reviews = collab.messages
        .where((m) =>
            m.to == node.id && (m.kind == 'feedback' || m.kind == 'approve'))
        .toList();
    return ListView(
      controller: controller,
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
      children: [
        if (showHandle) ...[
          Center(
            child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                    color: C.line, borderRadius: BorderRadius.circular(2))),
          ),
          const SizedBox(height: 12),
        ],
        Text(node.role, style: const TextStyle(color: C.muted, fontSize: 12)),
        Text(node.title,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text(nodeStatusLabels[node.status] ?? node.status,
            style: TextStyle(color: nodeStatusColor(node.status))),
        if (node.instruction.isNotEmpty) _section('任务说明', node.instruction),
        if (node.expectedOutput.isNotEmpty)
          _section('完成标准', node.expectedOutput),
        if (node.tools.isNotEmpty)
          _section('可用工具', node.tools.map((t) => toolLabels[t] ?? t).join('、')),
        if (reviews.isNotEmpty)
          _section(
              '审核记录',
              reviews
                  .map((m) => '${messageKindLabels[m.kind]}：${m.summary}')
                  .join('\n')),
        if (node.toolCalls.isNotEmpty) ...[
          const SizedBox(height: 14),
          const Text('工具调用',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          const SizedBox(height: 6),
          for (final call in node.toolCalls)
            ToolCallTile(key: ValueKey(call.id), call: call),
        ],
        if (node.output.isNotEmpty) ...[
          const SizedBox(height: 14),
          const Text('提交内容',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          const SizedBox(height: 6),
          MarkdownBody(
              data: node.output,
              selectable: true,
              styleSheet: answerMarkdownStyle),
        ],
      ],
    );
  }

  Widget _section(String title, String body) => Padding(
        padding: const EdgeInsets.only(top: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title,
              style:
                  const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          const SizedBox(height: 4),
          Text(body, style: const TextStyle(fontSize: 13, height: 1.6)),
        ]),
      );
}

class PlanEditorPage extends StatefulWidget {
  const PlanEditorPage({required this.collab, super.key});
  final CollabData collab;

  @override
  State<PlanEditorPage> createState() => _PlanEditorPageState();
}

class _PlanEditorPageState extends State<PlanEditorPage> {
  late final CollabData draft;
  var counter = 0;

  @override
  void initState() {
    super.initState();
    final source = widget.collab;
    draft = CollabData(question: source.question, history: source.history)
      ..goal = source.goal
      ..coverage = [...source.coverage]
      ..excluded = [...source.excluded]
      ..tools = source.tools
      ..maxNodes = source.maxNodes
      ..nodes = source.nodes.map((n) => n.copy()).toList();
  }

  void _add(PlanNodeData parent) {
    setState(() {
      counter++;
      draft.nodes.add(PlanNodeData(
          id: 'u$counter', parent: parent.id, role: '分析员', title: '新任务'));
    });
  }

  void _remove(PlanNodeData node) {
    final doomed = <String>{node.id};
    var changed = true;
    while (changed) {
      changed = false;
      for (final n in draft.nodes) {
        if (n.parent != null && doomed.contains(n.parent) && doomed.add(n.id)) {
          changed = true;
        }
      }
    }
    setState(() => draft.nodes.removeWhere((n) => doomed.contains(n.id)));
  }

  void _save() {
    final errors = draft.validate();
    if (errors.isNotEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(errors.take(3).join('\n')),
          duration: const Duration(seconds: 4)));
      return;
    }
    Navigator.of(context).pop(draft);
  }

  @override
  Widget build(BuildContext context) {
    final full = draft.nodes.length >= draft.maxNodes;
    return Scaffold(
      backgroundColor: C.faint,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text('编辑研究计划', style: TextStyle(fontSize: 16)),
        actions: [
          TextButton(onPressed: _save, child: const Text('完成')),
        ],
      ),
      body: LayoutBuilder(builder: (context, constraints) {
        final indent = constraints.maxWidth < 480 ? 10.0 : 18.0;
        return ListView(
          padding: const EdgeInsets.all(14),
          children: [
            TextFormField(
              initialValue: draft.goal,
              maxLines: null,
              decoration: _input('研究目标'),
              onChanged: (v) => draft.goal = v,
            ),
            const SizedBox(height: 8),
            Text('节点 ${draft.nodes.length} / ${draft.maxNodes}（含首席分析师）',
                style: TextStyle(
                    fontSize: 12, color: full ? Colors.red.shade700 : C.muted)),
            const SizedBox(height: 8),
            for (final node in draft.ordered()) _nodeCard(node, full, indent),
          ],
        );
      }),
    );
  }

  Widget _nodeCard(PlanNodeData node, bool full, double indent) {
    final depth = draft.depth(node);
    final isRoot = node.parent == null;
    final isLeaf = draft.children(node.id).isEmpty;
    return Container(
      key: ValueKey(node.id),
      margin: EdgeInsets.only(left: (depth - 1) * indent, bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: C.line),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Expanded(
            child: TextFormField(
              initialValue: node.role,
              decoration: _input('角色'),
              onChanged: (v) => node.role = v,
            ),
          ),
          if (!isRoot)
            IconButton(
                tooltip: '删除',
                onPressed: () => _remove(node),
                icon: const Icon(Icons.delete_outline, size: 20)),
        ]),
        const SizedBox(height: 8),
        TextFormField(
          initialValue: node.title,
          decoration: _input('任务标题'),
          onChanged: (v) => node.title = v,
        ),
        if (isLeaf && !isRoot) ...[
          const SizedBox(height: 8),
          TextFormField(
            initialValue: node.instruction,
            maxLines: null,
            decoration: _input('任务说明'),
            onChanged: (v) => node.instruction = v,
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: node.expectedOutput,
            maxLines: null,
            decoration: _input('完成标准'),
            onChanged: (v) => node.expectedOutput = v,
          ),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final tool in draft.tools)
              FilterChip(
                label: Text(toolLabels[tool] ?? tool,
                    style: const TextStyle(fontSize: 11.5)),
                selected: node.tools.contains(tool),
                visualDensity: VisualDensity.compact,
                selectedColor: C.goldSoft,
                onSelected: (on) => setState(() {
                  if (on) {
                    node.tools.add(tool);
                  } else {
                    node.tools.remove(tool);
                  }
                }),
              ),
          ]),
        ],
        if (depth < 3)
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: full ? null : () => _add(node),
              icon: const Icon(Icons.add, size: 16),
              label: const Text('添加下级任务'),
            ),
          ),
      ]),
    );
  }

  InputDecoration _input(String label) => InputDecoration(
        labelText: label,
        isDense: true,
        border: const OutlineInputBorder(),
      );
}
