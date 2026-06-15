const STREET_TYPES =
  "st|street|rd|road|ave|av|avenue|ln|lane|way|wy|cres|crescent|ct|court|pl|place|" +
  "dr|drv|drive|hwy|highway|tce|terrace|pde|parade|bvd|blvd|boulevard|cl|close|" +
  "gr|grove|gdns|gardens|cct|circuit|esp|esplanade|prom|promenade|qy|quay|rise|" +
  "loop|mews|gate|vista|heights|hts|entrance|ent|retreat|circle|chase|cove|dale|" +
  "edge|elbow|end|fairway|gap|glade|glen|green|grange|haven|hill|key|link|mall|" +
  "nook|outlook|pass|path|ridge|rest|square|sq|trail|view|vw|walk|approach|bend|" +
  "brace|brook|corner|crest|crossing|dell|driveway|gateway|lookout|meander|parkway|ramble";

const STREET_TYPE_RE = new RegExp(
  `^(lot\\s+\\d+\\s+|\\d+[a-z]?(?:[/-]\\d+[a-z]?)?\\s+)\\S+.*\\b(${STREET_TYPES})\\b`,
  "i",
);
const ADDRESS_NUMBER_RE = /^(?:lot\s+)?\d+[a-z]?(?:[/-]\d+[a-z]?)?(?:[\s/,]|$)/i;
const ADDRESS_NUMBER_WITH_WORD_RE = /^(?:lot\s+)?\d+[a-z]?(?:[/-]\d+[a-z]?)?\s+[a-z]/i;
const STREET_NAME_WITH_TYPE_RE = new RegExp(
  `\\b[a-z][a-z'-]*\\b(?:\\s+\\b[a-z][a-z'-]*\\b){0,4}\\s+\\b(${STREET_TYPES})\\b`,
  "i",
);
const QUESTION_PREFIX_RE = /^(what|when|where|why|how|who|can|does|do|is|are|will|would|should)\b/i;

export function looksLikeAddress(text: string): boolean {
  return STREET_TYPE_RE.test(text.trim());
}

export function addressish(text: string): boolean {
  return ADDRESS_NUMBER_WITH_WORD_RE.test(text.trim());
}

export function addressSearchIntent(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 3) return false;
  if (QUESTION_PREFIX_RE.test(trimmed)) return false;
  if (ADDRESS_NUMBER_RE.test(trimmed)) return true;
  return trimmed.length >= 6 && STREET_NAME_WITH_TYPE_RE.test(trimmed);
}
