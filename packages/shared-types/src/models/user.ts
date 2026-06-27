export type UserTier = "free" | "premium";

export interface User {
  id: string;
  supabaseUid: string;
  email: string;
  fullName: string | null;
  tier: UserTier;
  stripeCustomerId: string | null;
  createdAt: string;
  updatedAt: string;
}
