export const COMPANY_STATUSES = [
  { value: 'prospect', label: 'Prospect', color: 'bg-slate-50 text-slate-600 border border-slate-200' },
  { value: 'contacted', label: 'Contacted', color: 'bg-teal-50 text-teal-700 border border-teal-200' },
  { value: 'in-sequence', label: 'In Sequence', color: 'bg-cyan-50 text-cyan-700 border border-cyan-200' },
  { value: 'replied', label: 'Replied', color: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
  { value: 'meeting-booked', label: 'Meeting Booked', color: 'bg-amber-50 text-amber-700 border border-amber-200' },
  { value: 'won', label: 'Won', color: 'bg-green-50 text-green-700 border border-green-200' },
  { value: 'lost', label: 'Lost', color: 'bg-red-50 text-red-600 border border-red-200' },
  { value: 'not-interested', label: 'Not Interested', color: 'bg-gray-50 text-gray-500 border border-gray-200' },
] as const;

export const CONTACT_STATUSES = [
  { value: 'active', label: 'Active', color: 'bg-teal-50 text-teal-700 border border-teal-200' },
  { value: 'bounced', label: 'Bounced', color: 'bg-red-50 text-red-600 border border-red-200' },
  { value: 'unsubscribed', label: 'Unsubscribed', color: 'bg-gray-50 text-gray-500 border border-gray-200' },
  { value: 'replied', label: 'Replied', color: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
] as const;

export const ENROLLMENT_STATUSES = [
  { value: 'active', label: 'Active', color: 'bg-teal-50 text-teal-700 border border-teal-200' },
  { value: 'paused', label: 'Paused', color: 'bg-amber-50 text-amber-700 border border-amber-200' },
  { value: 'completed', label: 'Completed', color: 'bg-cyan-50 text-cyan-700 border border-cyan-200' },
  { value: 'replied', label: 'Replied', color: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
  { value: 'bounced', label: 'Bounced', color: 'bg-red-50 text-red-600 border border-red-200' },
] as const;

export const EVENT_STATUSES = [
  { value: 'pending', label: 'Pending', color: 'bg-slate-50 text-slate-600 border border-slate-200' },
  { value: 'scheduled', label: 'Scheduled', color: 'bg-teal-50 text-teal-700 border border-teal-200' },
  { value: 'sent', label: 'Sent', color: 'bg-cyan-50 text-cyan-700 border border-cyan-200' },
  { value: 'replied', label: 'Replied', color: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
  { value: 'bounced', label: 'Bounced', color: 'bg-red-50 text-red-600 border border-red-200' },
  { value: 'skipped', label: 'Skipped', color: 'bg-gray-50 text-gray-500 border border-gray-200' },
] as const;

export const DEFAULT_ROLES = [
  'CEO',
  'CTO',
  'CMO',
  'Head of Marketing',
  'Ecommerce Manager',
  'Head of Product',
  'VP Engineering',
];

export const PLATFORMS = [
  'Shopify',
  'Shopify Plus',
  'WooCommerce',
  'Magento',
  'BigCommerce',
  'Salesforce Commerce Cloud',
  'PrestaShop',
  'OpenCart',
  'Custom',
  'Other',
];

export const SEARCH_SOLUTIONS = [
  'Algolia',
  'Elasticsearch',
  'OpenSearch',
  'Typesense',
  'Luigi\'s Box',
  'Klevu',
  'Searchspring',
  'Constructor.io',
  'Bloomreach',
  'Coveo',
  'Doofinder',
  'Native/Built-in',
  'Unknown',
  'None',
];

export const SIZE_ESTIMATES = [
  '1-10',
  '11-50',
  '51-200',
  '201-500',
  '501-1000',
  '1001-5000',
  '5000+',
];

export const REVENUE_ESTIMATES = [
  'Under $1M',
  '$1M-$5M',
  '$5M-$10M',
  '$10M-$50M',
  '$50M-$100M',
  '$100M-$500M',
  '$500M+',
];
