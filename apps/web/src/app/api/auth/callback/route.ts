import type { NextRequest } from "next/server";

import { exchangeAuthCode } from "@/lib/auth/callback";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  return exchangeAuthCode(new URL(request.url), supabase);
}
