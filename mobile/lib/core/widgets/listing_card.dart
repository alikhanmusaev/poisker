import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../api/models.dart';
import '../theme/poisker_icons.dart';
import '../theme/poisker_theme.dart';

class ListingCard extends StatelessWidget {
  const ListingCard({
    super.key,
    required this.listing,
    required this.onTap,
    this.onBookmark,
  });

  final Listing listing;
  final VoidCallback onTap;
  final VoidCallback? onBookmark;

  String get _conditionLabel => switch (listing.condition) {
        'new' => 'Новый',
        _ => 'Б/У',
      };

  @override
  Widget build(BuildContext context) {
    final price = listing.priceDisplay.isNotEmpty
        ? listing.priceDisplay
        : 'По договорённости';
    final mutedPrice =
        listing.price == null || listing.priceDisplay.contains('договор');

    return Material(
      color: PoiskerColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(PoiskerRadii.lg),
        side: const BorderSide(color: PoiskerColors.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AspectRatio(
              aspectRatio: 4 / 3,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (listing.coverImage != null &&
                      listing.coverImage!.isNotEmpty)
                    CachedNetworkImage(
                      imageUrl: listing.coverImage!,
                      fit: BoxFit.cover,
                      errorWidget: (_, _, _) => const _ImagePlaceholder(),
                    )
                  else
                    const _ImagePlaceholder(),
                  if (onBookmark != null)
                    Positioned(
                      top: 8,
                      right: 8,
                      child: Material(
                        color: Colors.white.withValues(alpha: 0.92),
                        shape: const CircleBorder(),
                        elevation: 1,
                        child: InkWell(
                          customBorder: const CircleBorder(),
                          onTap: onBookmark,
                          child: SizedBox(
                            width: 36,
                            height: 36,
                            child: Icon(
                              PoiskerIcons.bookmark,
                              size: 20,
                              color: listing.isBookmarked
                                  ? PoiskerColors.primary700
                                  : PoiskerColors.slate700,
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    price,
                    style: GoogleFonts.inter(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.36,
                      height: 1.2,
                      color: mutedPrice
                          ? PoiskerColors.slate500
                          : PoiskerColors.primary800,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    listing.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      height: 1.35,
                      color: PoiskerColors.slate900,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    [
                      _conditionLabel,
                      if (listing.cityLabel.isNotEmpty) listing.cityLabel,
                      if (listing.categoryLabel.isNotEmpty)
                        listing.categoryLabel,
                      if (listing.statusLabel != null &&
                          listing.status != 'published')
                        listing.statusLabel!,
                    ].join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      color: PoiskerColors.muted,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ImagePlaceholder extends StatelessWidget {
  const _ImagePlaceholder();

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [PoiskerColors.slate100, PoiskerColors.slate200],
        ),
      ),
      child: Center(
        child: Icon(PoiskerIcons.image, size: 36, color: PoiskerColors.slate400),
      ),
    );
  }
}
