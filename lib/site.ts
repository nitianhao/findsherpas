/**
 * European languages supported (all in Europe except Hungarian, Estonian, Finnish).
 * Alphabetical for display.
 */
export const SUPPORTED_LANGUAGES = [
  "Albanian",
  "Basque",
  "Bosnian",
  "Bulgarian",
  "Catalan",
  "Croatian",
  "Czech",
  "Danish",
  "Dutch",
  "English",
  "French",
  "Galician",
  "German",
  "Greek",
  "Icelandic",
  "Irish",
  "Italian",
  "Latvian",
  "Lithuanian",
  "Macedonian",
  "Maltese",
  "Montenegrin",
  "Norwegian",
  "Polish",
  "Portuguese",
  "Romanian",
  "Serbian",
  "Slovak",
  "Slovenian",
  "Spanish",
  "Swedish",
  "Ukrainian",
  "Welsh",
] as const;

export const LANGUAGES_EXCLUDED = ["Hungarian", "Estonian", "Finnish"] as const;
