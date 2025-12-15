import '../models/models.dart';

final StudentInfo student = StudentInfo(
  name: 'Uluğbey Çetin',
  className: '5-A',
  studentNo: '5A01',
  points: 128,
  badge: 'Kitap Kulübü',
);

final List<BorrowedBook> borrowedBooks = [
  BorrowedBook(
    title: 'Küçük Prens',
    author: 'Antoine de Saint-Exupéry',
    code: 'KTP-204',
    dueDate: DateTime.now().add(const Duration(days: 5)),
    progress: 0.65,
  ),
  BorrowedBook(
    title: 'Define Adası',
    author: 'R. L. Stevenson',
    code: 'KTP-118',
    dueDate: DateTime.now().add(const Duration(days: -1)),
    progress: 0.3,
  ),
];

final List<SuggestedBook> suggestedBooks = [
  const SuggestedBook(title: 'Momo', author: 'Michael Ende', tag: 'Fantastik'),
  const SuggestedBook(title: 'Martı', author: 'Richard Bach', tag: 'Klasik'),
  const SuggestedBook(title: 'Dijital Kale', author: 'Dan Brown', tag: 'Macera'),
];

const List<Announcement> announcements = [
  Announcement(
    title: 'Yeni kitaplar raflarda',
    detail:
        'Bilim kurgu ve çizgi roman rafı güncellendi, ödünç almadan önce online sıraya yazıl.',
    dateLabel: '13 Mar',
  ),
  Announcement(
    title: 'Sessiz saat',
    detail:
        'Çarşamba 15.00 - 16.00 arası sınav grubu için sessiz çalışma alanı ayrıldı.',
    dateLabel: '12 Mar',
  ),
];
