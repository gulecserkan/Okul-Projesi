class BorrowedBook {
  const BorrowedBook({
    required this.title,
    required this.author,
    required this.code,
    required this.dueDate,
    required this.progress,
  });

  final String title;
  final String author;
  final String code;
  final DateTime dueDate;
  final double progress;
}
