class StudentInfo {
  const StudentInfo({
    required this.name,
    required this.className,
    required this.studentNo,
    required this.points,
    required this.badge,
  });

  final String name;
  final String className;
  final String studentNo;
  final int points;
  final String badge;

  String get initials {
    final parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return name.isNotEmpty ? name[0].toUpperCase() : 'Ö';
  }
}
