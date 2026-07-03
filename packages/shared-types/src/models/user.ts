export type UserTier = "free" | "premium";

export interface User {
  id: string;
  supabaseUid: string;
  email: string;
  fullName: string | null;
  tier: UserTier;
  paymentProvider: "lemonsqueezy" | null;
  lemonsqueezyCustomerId: string | null;
  lemonsqueezySubscriptionId: string | null;
  subscriptionStatus: string | null;
  currentPeriodEnd: string | null;
  createdAt: string;
  updatedAt: string;
}
