import config from '../../../shared/languages.json';
export const languages = config;
export type Language = keyof typeof languages;
export const languageEntries = Object.entries(languages) as [Language, typeof languages[Language]][];
