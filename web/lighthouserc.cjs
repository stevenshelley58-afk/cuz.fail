const { existsSync } = require("node:fs");

const windowsChromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const chromePath = process.env.CHROME_PATH || (existsSync(windowsChromePath) ? windowsChromePath : undefined);

module.exports = {
  ci: {
    collect: {
      staticDistDir: "./dist",
      url: ["http://localhost/"],
      isSinglePageApplication: true,
      numberOfRuns: 3,
      chromePath,
      settings: {
        onlyCategories: ["seo"],
        chromeFlags: "--no-sandbox --disable-dev-shm-usage",
      },
    },
    assert: {
      assertions: {
        "categories:seo": ["error", { minScore: 0.9, aggregationMethod: "median" }],
      },
    },
    upload: {
      target: "filesystem",
      outputDir: "./.lighthouseci",
    },
  },
};
