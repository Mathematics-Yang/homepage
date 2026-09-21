# Bundled icon font subsets

The WOFF2 files in this directory are modified, renamed, page-specific subsets.

- Font Awesome Free 6.4.0 is Copyright Fonticons, Inc. and licensed under the SIL Open Font License 1.1. The complete upstream license is included in `LICENSE-FONT-AWESOME.txt`.
- Academicons 1.9.5 is by James Walsh and contributors and is licensed under the SIL Open Font License 1.1 (the full OFL text is also reproduced in `LICENSE-FONT-AWESOME.txt`).

The subsets use new primary font names so that the upstream reserved names are not used by modified versions.

Sources: [Font Awesome 6.4.0](https://github.com/FortAwesome/Font-Awesome/tree/6.4.0) and [Academicons 1.9.5](https://github.com/jpswalsh/academicons/tree/v1.9.5).
Only the glyphs mapped in `../icons.css` are included; adding another icon requires extending its font subset as well as the CSS mapping. These files were subsetted with FontTools and encoded as WOFF2.
