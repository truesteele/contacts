// Supabase Edge Function: One-click unsubscribe
// Handles unsubscribe requests via secure token

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Simple HMAC-like verification using Web Crypto API
async function verifyToken(token: string, secret: string): Promise<number | null> {
  try {
    // Token format: base64(contactId:signature)
    const decoded = atob(token);
    const [contactIdStr, signature] = decoded.split(":");

    if (!contactIdStr || !signature) return null;

    const contactId = parseInt(contactIdStr, 10);
    if (isNaN(contactId)) return null;

    // Verify signature
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      "raw",
      encoder.encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );

    const signatureBytes = await crypto.subtle.sign(
      "HMAC",
      key,
      encoder.encode(contactIdStr)
    );

    const expectedSignature = btoa(String.fromCharCode(...new Uint8Array(signatureBytes)));

    if (signature === expectedSignature) {
      return contactId;
    }

    return null;
  } catch {
    return null;
  }
}

Deno.serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    const token = url.searchParams.get("token");

    if (!token) {
      return new Response(renderPage("Missing Token", "No unsubscribe token provided.", false), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "text/html" },
      });
    }

    // Get the secret from environment
    const unsubscribeSecret = Deno.env.get("UNSUBSCRIBE_SECRET");
    if (!unsubscribeSecret) {
      console.error("UNSUBSCRIBE_SECRET not configured");
      return new Response(renderPage("Configuration Error", "Please contact support.", false), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "text/html" },
      });
    }

    // Verify token and extract contact ID
    const contactId = await verifyToken(token, unsubscribeSecret);

    if (!contactId) {
      return new Response(renderPage("Invalid Link", "This unsubscribe link is invalid or expired.", false), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "text/html" },
      });
    }

    // Initialize Supabase client with service role key
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Update contact to unsubscribed
    const { data, error } = await supabase
      .from("contacts")
      .update({
        unsubscribed: true,
        unsubscribed_at: new Date().toISOString(),
        unsubscribe_source: "one_click_link",
      })
      .eq("id", contactId)
      .select("first_name, email")
      .single();

    if (error) {
      console.error("Database error:", error);
      return new Response(renderPage("Error", "Something went wrong. Please try again or reply 'unsubscribe' to the email.", false), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "text/html" },
      });
    }

    const name = data?.first_name || "there";

    return new Response(
      renderPage(
        "Unsubscribed",
        `Thanks, ${name}. You've been removed from future emails. If this was a mistake, just reply to any email from Justin.`,
        true
      ),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "text/html" },
      }
    );
  } catch (err) {
    console.error("Unexpected error:", err);
    return new Response(renderPage("Error", "An unexpected error occurred.", false), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "text/html" },
    });
  }
});

function renderPage(title: string, message: string, success: boolean): string {
  const color = success ? "#10b981" : "#ef4444";
  const icon = success ? "✓" : "✕";

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title} - True Steele</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      background: #f9fafb;
    }
    .card {
      background: white;
      padding: 3rem;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      text-align: center;
      max-width: 400px;
    }
    .icon {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: ${color};
      color: white;
      font-size: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.5rem;
    }
    h1 {
      margin: 0 0 1rem;
      color: #111827;
      font-size: 1.5rem;
    }
    p {
      color: #6b7280;
      line-height: 1.6;
      margin: 0;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">${icon}</div>
    <h1>${title}</h1>
    <p>${message}</p>
  </div>
</body>
</html>`;
}
