import { NextResponse } from 'next/server';

export async function GET() {
    // In a real production app, we would perform actual health checks (pings, SELECT 1, etc.)
    // For this hackathon/demo, we assume "Online" if the configuration is present.
    // We can simulate latency for the "Control Room" feel.

    const status = {
        snowflake: {
            online: !!process.env.SNOWFLAKE_ACCOUNT && !!process.env.SNOWFLAKE_USER
        },
        gemini: {
            online: !!process.env.GEMINI_API_KEY
        },
        elevenlabs: {
            online: !!process.env.ELEVENLABS_API_KEY
        },
        digitalocean: {
            online: !!process.env.DROPLET_IP,
            ip: process.env.DROPLET_IP || "Unknown"
        }
    };

    return NextResponse.json(status);
}
