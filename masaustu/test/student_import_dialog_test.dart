import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:masaustu/api/kutuphane_api.dart';
import 'package:masaustu/screens/student_import_dialog.dart';
import 'package:masaustu/screens/student_list_screen.dart';

class _FakeApi extends KutuphaneApi {
  _FakeApi({required this.preview, this.applied});

  final Map<String, dynamic> preview;
  final Map<String, dynamic>? applied;
  bool lastDryRun = true;
  bool lastYeniden = false;

  @override
  Future<({Map<String, dynamic>? data, String? error})> ogrenciImport(
    String csv, {
    bool dryRun = true,
    bool yenidenKullan = false,
  }) async {
    lastDryRun = dryRun;
    lastYeniden = yenidenKullan;
    return (data: dryRun ? preview : (applied ?? preview), error: null);
  }
}

Map<String, dynamic> _preview() => {
      'dry_run': true,
      'ozet': {
        'toplam': 3,
        'yeni': 1,
        'yenileme': 1,
        'cakisma': 1,
        'hatali': 0,
        'pasife_cekilecek': 1,
      },
      'satirlar': [
        {
          'satir': 2,
          'uye_no': '101',
          'ad': 'Yeni',
          'soyad': 'Ogrenci',
          'sinif': '5-A',
          'rol': 'Öğrenci',
          'islem': 'yeni',
          'sebep': null,
        },
        {
          'satir': 3,
          'uye_no': '100',
          'ad': 'Ali',
          'soyad': 'Veli',
          'sinif': '5-A',
          'rol': 'Öğrenci',
          'islem': 'yenileme',
          'sebep': null,
        },
        {
          'satir': 4,
          'uye_no': '200',
          'ad': 'Mezun',
          'soyad': 'Kisi',
          'sinif': '5-A',
          'rol': 'Öğrenci',
          'islem': 'cakisma',
          'sebep': 'Pasif (mezun) kayıtla aynı üye no; atlandı.',
        },
      ],
      'pasife_cekilecekler': [
        {'uye_no': '150', 'ad': 'Giden', 'soyad': 'Ogrenci'},
      ],
      'yeni_siniflar': ['6-B'],
    };

Future<void> _pumpDialog(
  WidgetTester tester,
  _FakeApi api, {
  void Function(Map<String, dynamic>?)? onResult,
}) async {
  tester.view.physicalSize = const Size(1280, 1024);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      home: Builder(
        builder: (context) => Scaffold(
          body: Center(
            child: ElevatedButton(
              onPressed: () async {
                final r = await showDialog<Map<String, dynamic>>(
                  context: context,
                  builder: (_) => StudentImportDialog(csv: 'x', api: api),
                );
                onResult?.call(r);
              },
              child: const Text('ac'),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('ac'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('önizleme özet + satırlar + yeni sınıf gösterilir', (tester) async {
    final api = _FakeApi(preview: _preview());
    await _pumpDialog(tester, api);

    expect(find.text('Yeni: 1'), findsOneWidget);
    expect(find.text('Yenileme: 1'), findsOneWidget);
    expect(find.text('Çakışma: 1'), findsOneWidget);
    expect(find.text('Pasife: 1'), findsOneWidget);
    expect(find.text('Otomatik oluşturulacak sınıf(lar): 6-B'), findsOneWidget);
    expect(find.text('101 — Yeni Ogrenci'), findsOneWidget);
    expect(find.text('200 — Mezun Kisi'), findsOneWidget);
    expect(find.text('Pasife çekilecek öğrenciler (1)'), findsOneWidget);
  });

  testWidgets('yeniden kullan anahtarı önizlemeyi tazeler', (tester) async {
    final api = _FakeApi(preview: _preview());
    await _pumpDialog(tester, api);

    expect(api.lastYeniden, isFalse);
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
    expect(api.lastYeniden, isTrue);
  });

  testWidgets('"Aktar" uygular ve sonucu döndürür', (tester) async {
    final api = _FakeApi(
      preview: _preview(),
      applied: {'uygulandi': true, 'ozet': {'yeni': 1}},
    );
    Map<String, dynamic>? sonuc;
    await _pumpDialog(tester, api, onResult: (r) => sonuc = r);

    await tester.tap(find.text('Aktar'));
    await tester.pumpAndSettle();

    expect(api.lastDryRun, isFalse);
    expect(sonuc, isNotNull);
    expect(sonuc!['uygulandi'], isTrue);
  });

  testWidgets('üye listesinde "Öğrenci İçe Aktar" butonu var', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: StudentListScreen())),
    );
    await tester.pumpAndSettle();
    expect(find.text('Öğrenci İçe Aktar'), findsOneWidget);
  });
}
