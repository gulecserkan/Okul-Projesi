import 'package:flutter/material.dart';
import 'package:photo_view/photo_view.dart';
import 'package:photo_view/photo_view_gallery.dart';

import '../models/book.dart';

class ImageGalleryScreen extends StatelessWidget {
  const ImageGalleryScreen({
    super.key,
    required this.images,
    this.initialIndex = 0,
  });

  final List<BookImageSlot> images;
  final int initialIndex;

  @override
  Widget build(BuildContext context) {
    final validImages = images.where((e) => e.hasImage).toList();
    final startIndex = validImages.indexWhere((e) => e.index == initialIndex);
    final pageController = PageController(initialPage: startIndex < 0 ? 0 : startIndex);

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text("Resmi görüntüle"),
      ),
      body: validImages.isEmpty
          ? const Center(
              child: Text("Gösterilecek resim yok", style: TextStyle(color: Colors.white)),
            )
          : PhotoViewGallery.builder(
              itemCount: validImages.length,
              pageController: pageController,
              builder: (context, index) {
                final item = validImages[index];
                return PhotoViewGalleryPageOptions(
                  imageProvider: NetworkImage(item.url!),
                  minScale: PhotoViewComputedScale.contained,
                  maxScale: PhotoViewComputedScale.covered * 3,
                  heroAttributes: PhotoViewHeroAttributes(tag: item.url ?? "img_$index"),
                );
              },
              backgroundDecoration: const BoxDecoration(color: Colors.black),
            ),
    );
  }
}
