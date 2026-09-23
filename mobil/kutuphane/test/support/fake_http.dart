import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// Test ortamındaki `NetworkImage` istekleri için sahte PNG döndürür.
/// flutter_test'in varsayılan istemcisi 400 döndürdüğü için resim yükleyen
/// ekranlar (kitap detayı, galeri) bu override ile gerçek ağa çıkmaz.
class FakeHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) => _FakeHttpClient();
}

class _FakeHttpClient implements HttpClient {
  Future<HttpClientRequest> _request() async => _FakeHttpClientRequest();

  @override
  Future<HttpClientRequest> getUrl(Uri url) => _request();
  @override
  Future<HttpClientRequest> openUrl(String method, Uri url) => _request();
  @override
  Future<HttpClientRequest> open(String method, String host, int port, String path) =>
      _request();
  @override
  Future<HttpClientRequest> get(String host, int port, String path) => _request();
  @override
  Future<HttpClientRequest> post(String host, int port, String path) => _request();
  @override
  Future<HttpClientRequest> put(String host, int port, String path) => _request();
  @override
  Future<HttpClientRequest> delete(String host, int port, String path) => _request();
  @override
  Future<HttpClientRequest> patch(String host, int port, String path) => _request();
  @override
  Future<HttpClientRequest> head(String host, int port, String path) => _request();
  @override
  Future<HttpClientRequest> postUrl(Uri url) => _request();
  @override
  Future<HttpClientRequest> putUrl(Uri url) => _request();
  @override
  Future<HttpClientRequest> deleteUrl(Uri url) => _request();
  @override
  Future<HttpClientRequest> patchUrl(Uri url) => _request();
  @override
  Future<HttpClientRequest> headUrl(Uri url) => _request();

  @override
  bool autoUncompress = true;
  @override
  Duration? connectionTimeout;
  @override
  Duration idleTimeout = const Duration(seconds: 15);
  @override
  int? maxConnectionsPerHost;
  @override
  String? userAgent;
  bool followRedirects = true;
  Duration? responseTimeout;
  @override
  void close({bool force = false}) {}
  @override
  void addCredentials(
      Uri url, String realm, HttpClientCredentials credentials) {}
  @override
  void addProxyCredentials(
      String host, int port, String realm, HttpClientCredentials credentials) {}
  @override
  set connectionFactory(
      Future<ConnectionTask<Socket>> Function(Uri url, String? proxyHost,
          int? proxyPort)? _) {}
  @override
  set keyLog(void Function(String line)? _) {}
  @override
  set authenticate(Future<bool> Function(Uri url, String scheme, String? realm)? _) {}
  @override
  set authenticateProxy(
      Future<bool> Function(String host, int port, String scheme, String? realm)? _) {}
  @override
  set badCertificateCallback(
      bool Function(X509Certificate cert, String host, int port)? _) {}
  @override
  set findProxy(String Function(Uri url)? _) {}
}

class _FakeHttpClientRequest implements HttpClientRequest {
  @override
  Future<HttpClientResponse> close() async {
    final bytes = base64Decode(_tinyPngBase64);
    return _FakeHttpClientResponse(List<List<int>>.from([bytes]));
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeHttpClientResponse implements HttpClientResponse {
  _FakeHttpClientResponse(this._chunks);

  final List<List<int>> _chunks;

  @override
  int get statusCode => HttpStatus.ok;
  @override
  int get contentLength => -1;
  @override
  HttpClientResponseCompressionState get compressionState =>
      HttpClientResponseCompressionState.notCompressed;

  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int>)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) {
    return Stream.fromIterable(_chunks).listen(
      onData,
      onError: onError,
      onDone: onDone,
      cancelOnError: cancelOnError,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 1x1 PNG (şeffaf) — görselin başarıyla "yüklendiğini" simüle eder.
const _tinyPngBase64 =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';