const siteConfig = require("./config.json");

const theme = siteConfig.theme;

module.exports = {
  content: [
    "./templates/**/*.html",
    "./Introduction.md",
    "./Introduction.zh.md",
    "./TechStack.md",
    "./TechStack.zh.md",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: theme.primary_color,
          dark: theme.dark_primary_color,
        },
        secondary: {
          DEFAULT: theme.secondary_color,
          dark: theme.dark_secondary_color,
        },
        "primary-dark": theme.dark_primary_color,
        "secondary-dark": theme.dark_secondary_color,
      },
      fontFamily: {
        sans: [
          "Inter",
          "SF Pro Text",
          "SF Pro Display",
          "Segoe UI Variable Text",
          "Segoe UI",
          "PingFang SC",
          "Microsoft YaHei",
          "Noto Sans CJK SC",
          "system-ui",
          "sans-serif",
        ],
      },
    },
  },
};
