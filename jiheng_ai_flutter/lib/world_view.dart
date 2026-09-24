import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:webview_flutter/webview_flutter.dart';

/// The authored World story is bundled with the app, so it never points at
/// 127.0.0.1 on the player's phone. Model dialogue remains optional on web.
class WorldView extends StatefulWidget {
  const WorldView({required this.onExit, this.userId, super.key});

  final VoidCallback onExit;
  final String? userId;

  @override
  State<WorldView> createState() => _WorldViewState();
}

class _WorldViewState extends State<WorldView> {
  final _storage = const FlutterSecureStorage();
  late final WebViewController _controller;
  late final String _storageKey;
  String? _savedState;
  bool _ready = false;
  bool _restored = false;
  bool _loading = true;
  bool _failed = false;
  Future<void> _pendingWrite = Future<void>.value();

  @override
  void initState() {
    super.initState();
    final user = widget.userId;
    _storageKey = 'jiheng.world.v1.${user == null || user.isEmpty ? 'guest' : user}';
    _controller = WebViewController();
    unawaited(_initialize());
  }

  Future<void> _initialize() async {
    _ready = false;
    _restored = false;
    try {
      _savedState = await _storage.read(key: _storageKey);
    } catch (_) {
      _savedState = null;
    }
    try {
      await _controller.setJavaScriptMode(JavaScriptMode.unrestricted);
      await _controller.setBackgroundColor(const Color(0xFF09131B));
      await _controller.setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) {
          _ready = false;
          _restored = false;
        },
        onPageFinished: (_) => unawaited(_restore()),
      ));
      await _controller.addJavaScriptChannel(
        'JihengWorldBridge',
        onMessageReceived: _handleMessage,
      );
      await _controller.loadFlutterAsset('assets/world/index.html');
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _failed = true;
      });
    }
  }

  Future<void> _restore() async {
    if (_restored) return;
    _restored = true;
    try {
      await _controller.runJavaScript('document.body.classList.add("in-app");');
      if (_savedState != null) {
        await _controller.runJavaScript(
          'window.restoreWorldState(${jsonEncode(_savedState)});',
        );
      }
    } catch (_) {
      // The game still opens at the first scene when saved progress is invalid.
    }
    _ready = true;
    if (!mounted) return;
    setState(() {
      _loading = false;
      _failed = false;
    });
  }

  void _handleMessage(JavaScriptMessage message) {
    try {
      final data = jsonDecode(message.message);
      if (data is! Map<String, dynamic>) return;
      if (data['type'] == 'exit') {
        widget.onExit();
      } else if (data['type'] == 'save' && _ready && data['state'] is Map) {
        final value = jsonEncode(data['state']);
        _savedState = value;
        _pendingWrite = _pendingWrite
            .then((_) => _storage.write(key: _storageKey, value: value))
            .catchError((Object _) {});
        unawaited(_pendingWrite);
      }
    } catch (_) {
      // Ignore malformed messages from the embedded page.
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvoked: (didPop) {
        if (!didPop) widget.onExit();
      },
      child: Stack(children: [
        Positioned.fill(child: WebViewWidget(controller: _controller)),
        if (_loading)
          const Positioned.fill(
            child: ColoredBox(
              color: Color(0xFF09131B),
              child: Center(
                child: CircularProgressIndicator(color: Color(0xFFF3C884)),
              ),
            ),
          ),
        if (_failed)
          Positioned.fill(
            child: ColoredBox(
              color: const Color(0xFF09131B),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('World 资源未能打开',
                        style: TextStyle(color: Colors.white)),
                    const SizedBox(height: 16),
                    TextButton(
                      onPressed: widget.onExit,
                      child: const Text('返回玑衡 AI'),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ]),
    );
  }
}
