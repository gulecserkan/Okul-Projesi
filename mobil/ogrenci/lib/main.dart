import 'package:flutter/material.dart';
import 'screens/home_page.dart';
import 'theme/app_themes.dart';

void main() {
  runApp(const OgrenciApp());
}

class OgrenciApp extends StatefulWidget {
  const OgrenciApp({super.key});

  @override
  State<OgrenciApp> createState() => _OgrenciAppState();
}

class _OgrenciAppState extends State<OgrenciApp> {
  AppTheme _currentTheme = AppTheme.breeze;

  void _setTheme(AppTheme theme) {
    setState(() {
      _currentTheme = theme;
    });
  }

  @override
  Widget build(BuildContext context) {
    final themeOption = appThemes[_currentTheme]!;

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Öğrenci Kütüphane',
      theme: themeOption.themeData,
      home: StudentHomePage(
        currentTheme: _currentTheme,
        onThemeChange: _setTheme,
      ),
    );
  }
}
