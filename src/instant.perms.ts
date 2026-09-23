// Docs: https://www.instantdb.com/docs/permissions

import type { InstantRules } from "@instantdb/admin";

const rules = {
  articles: {
    allow: {
      "$default": "false",
    },
  },
} satisfies InstantRules;

export default rules;
