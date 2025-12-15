import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:image_cropper/image_cropper.dart';

import '../api/library_api.dart';
import '../models/book.dart';
import 'image_gallery_screen.dart';

class BookDetailScreen extends StatefulWidget {
  const BookDetailScreen({
    super.key,
    required this.bookId,
    required this.api,
    this.summary,
  });

  final int bookId;
  final LibraryApiClient api;
  final BookSummary? summary;

  @override
  State<BookDetailScreen> createState() => _BookDetailScreenState();
}

class _BookDetailScreenState extends State<BookDetailScreen> {
  BookDetail? _detail;
  bool _loading = true;
  bool _savingDescription = false;
  final Map<int, bool> _uploadingSlot = {};
  final TextEditingController _descriptionController = TextEditingController();
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDetail();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.summary?.baslik ?? "Kitap"),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _detail == null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text("Detaylar alınamadı."),
                      if (_error != null) Text(_error!),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        onPressed: _loadDetail,
                        icon: const Icon(Icons.refresh),
                        label: const Text("Tekrar dene"),
                      ),
                    ],
                  ),
                )
              : SafeArea(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildHeaderCard(scheme),
                        const SizedBox(height: 16),
                        _buildDescriptionCard(scheme),
                        const SizedBox(height: 16),
                        _buildImagesSection(scheme),
                      ],
                    ),
                  ),
                ),
    );
  }

  Widget _buildHeaderCard(ColorScheme scheme) {
    final detail = _detail!;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            scheme.primary.withOpacity(0.14),
            scheme.secondary.withOpacity(0.12),
            scheme.surfaceVariant.withOpacity(0.12),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: scheme.shadow.withOpacity(0.06),
            blurRadius: 12,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            detail.baslik,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 12,
            runSpacing: 8,
            children: [
              if (detail.yazar != null)
                _infoChip(Icons.person_outline, detail.yazar!, scheme),
              if (detail.kategori != null)
                _infoChip(Icons.category_outlined, detail.kategori!, scheme),
              if (detail.isbn != null && detail.isbn!.isNotEmpty)
                _infoChip(Icons.qr_code_2, "ISBN ${detail.isbn}", scheme),
              _infoChip(Icons.layers, "Nüsha: ${detail.nushaSayisi ?? "-"}", scheme),
            ],
          ),
        ],
      ),
    );
  }

  Widget _infoChip(IconData icon, String label, ColorScheme scheme) {
    return Chip(
      avatar: Icon(icon, size: 18, color: scheme.primary),
      label: Text(label),
      backgroundColor: scheme.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    );
  }

  Widget _buildDescriptionCard(ColorScheme scheme) {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.notes_outlined),
                const SizedBox(width: 8),
                Text(
                  "Açıklama",
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                ),
                const Spacer(),
                Text(
                  "sunucuya kaydedilir",
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(color: scheme.outline),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _descriptionController,
              minLines: 3,
              maxLines: 6,
              decoration: const InputDecoration(hintText: "Kitap hakkında kısa açıklama"),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton.icon(
                onPressed: _savingDescription || _descriptionController.text.trim().isEmpty ? null : _saveDescription,
                icon: _savingDescription
                    ? SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: scheme.onPrimary,
                        ),
                      )
                    : const Icon(Icons.save_outlined),
                label: Text(_savingDescription ? "Kaydediliyor..." : "Açıklamayı kaydet"),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImagesSection(ColorScheme scheme) {
    final detail = _detail!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.photo_library_outlined),
            const SizedBox(width: 8),
            Text(
              "Kapak ve görseller",
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: detail.resimler.map((slot) {
            final uploading = _uploadingSlot[slot.index] == true;
            return Container(
              width: 160,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: scheme.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: scheme.outlineVariant),
                boxShadow: [
                  BoxShadow(
                    color: scheme.shadow.withOpacity(0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  AspectRatio(
                    aspectRatio: 3 / 4,
                    child: Stack(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: slot.hasImage
                              ? GestureDetector(
                                  onTap: () => _openGallery(slot.index),
                                  child: Image.network(
                                    slot.url!,
                                    fit: BoxFit.cover,
                                    errorBuilder: (_, __, ___) => _placeholder(scheme),
                                  ),
                                )
                              : _placeholder(scheme),
                        ),
                        if (slot.hasImage)
                          Positioned(
                            top: 6,
                            right: 6,
                            child: CircleAvatar(
                              radius: 14,
                              backgroundColor: Colors.black45,
                              child: IconButton(
                                padding: EdgeInsets.zero,
                                visualDensity: VisualDensity.compact,
                                icon: const Icon(Icons.close, size: 16, color: Colors.white),
                                onPressed: uploading ? null : () => _confirmDelete(slot.index),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Resim ${slot.index}",
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 6),
                  ElevatedButton.icon(
                    onPressed: uploading ? null : () => _pickImage(slot.index),
                    icon: uploading
                        ? SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: scheme.onPrimary,
                            ),
                          )
                        : const Icon(Icons.upload_outlined),
                    label: Text(
                      uploading
                          ? "Yükleniyor..."
                          : slot.hasImage
                              ? "Değiştir"
                              : "Yükle",
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Row(
            children: [
              Icon(Icons.error_outline, color: scheme.error),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _error!,
                  style: TextStyle(color: scheme.error),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _placeholder(ColorScheme scheme) {
    return Container(
      color: scheme.primary.withOpacity(0.12),
      child: Center(
        child: Icon(Icons.image_not_supported_outlined, color: scheme.outline),
      ),
    );
  }

  Future<void> _loadDetail() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final detail = await widget.api.fetchBookDetail(widget.bookId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
        _descriptionController.text = detail.aciklama ?? "";
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _saveDescription() async {
    if (_detail == null) return;
    setState(() => _savingDescription = true);
    try {
      final updated = await widget.api.updateBook(
        id: widget.bookId,
        aciklama: _descriptionController.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _detail = updated;
        _savingDescription = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Açıklama kaydedildi")),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _savingDescription = false;
      });
    }
  }

  Future<void> _pickImage(int slot) async {
    final source = await _selectImageSource();
    if (source == null) return;

    final picker = ImagePicker();
    final picked = await picker.pickImage(source: source, maxHeight: 1600, maxWidth: 1600);
    if (picked == null) return;

    // Önce kırp, iptal edilirse yükleme yapma
    final fileForUpload = await _cropImage(picked);
    if (fileForUpload == null) return;

    setState(() {
      _uploadingSlot[slot] = true;
      _error = null;
    });

    try {
      final updated = await widget.api.updateBook(
        id: widget.bookId,
        imageFile: fileForUpload,
        imageSlot: slot,
      );
      if (!mounted) return;
      setState(() {
        _detail = updated;
        _uploadingSlot.remove(slot);
        _descriptionController.text = updated.aciklama ?? "";
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Resim $slot güncellendi")),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _uploadingSlot.remove(slot);
      });
    }
  }

  Future<ImageSource?> _selectImageSource() async {
    return showModalBottomSheet<ImageSource>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.photo_camera_outlined),
                title: const Text("Kamera ile çek"),
                onTap: () => Navigator.of(context).pop(ImageSource.camera),
              ),
              ListTile(
                leading: const Icon(Icons.photo_library_outlined),
                title: const Text("Galeriden seç"),
                onTap: () => Navigator.of(context).pop(ImageSource.gallery),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<XFile?> _cropImage(XFile original) async {
    try {
      final cropped = await ImageCropper().cropImage(
        sourcePath: original.path,
        aspectRatio: const CropAspectRatio(ratioX: 3, ratioY: 4),
        compressQuality: 90,
        uiSettings: [
          AndroidUiSettings(
            toolbarTitle: "Kırp",
            toolbarWidgetColor: Colors.white,
            toolbarColor: Theme.of(context).colorScheme.primary,
            lockAspectRatio: false,
          ),
          IOSUiSettings(
            title: "Kırp",
            aspectRatioLockEnabled: false,
          ),
        ],
      );
      if (cropped == null) return null;
      return XFile(cropped.path);
    } catch (e) {
      setState(() => _error = "Kırpma açılamadı: $e");
      return null;
    }
  }

  void _openGallery(int slotIndex) {
    final images = _detail?.resimler ?? [];
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ImageGalleryScreen(
          images: images,
          initialIndex: slotIndex,
        ),
      ),
    );
  }

  Future<void> _confirmDelete(int slot) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text("Resmi sil"),
          content: const Text("Bu slotta bulunan resmi silmek istediğinize emin misiniz?"),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text("Vazgeç"),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text("Sil"),
            ),
          ],
        );
      },
    );
    if (confirmed != true) return;

    setState(() {
      _uploadingSlot[slot] = true;
      _error = null;
    });

    try {
      final updated = await widget.api.updateBook(
        id: widget.bookId,
        deleteImageSlot: slot,
      );
      if (!mounted) return;
      setState(() {
        _detail = updated;
        _uploadingSlot.remove(slot);
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Resim $slot silindi")),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _uploadingSlot.remove(slot);
      });
    }
  }
}
