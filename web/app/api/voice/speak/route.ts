import { NextResponse } from "next/server";

const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY;
const VOICE_ID = "pFZP5JQG7iQjIQuC4Bku"; // 'Fin' - Standard Male (Energetic)

export async function POST(req: Request) {
    try {
        if (!ELEVENLABS_API_KEY) {
            return NextResponse.json(
                { error: "ELEVENLABS_API_KEY is not configured" },
                { status: 500 }
            );
        }

        const { text } = await req.json();

        if (!text) {
            return NextResponse.json(
                { error: "No text provided" },
                { status: 400 }
            );
        }

        // Call ElevenLabs API
        const response = await fetch(
            `https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`,
            {
                method: "POST",
                headers: {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": ELEVENLABS_API_KEY,
                },
                body: JSON.stringify({
                    text: text,
                    model_id: "eleven_flash_v2_5", // Faster, cheaper model
                    voice_settings: {
                        stability: 0.5,
                        similarity_boost: 0.5,
                    },
                }),
            }
        );

        if (!response.ok) {
            const error = await response.json();
            console.error("ElevenLabs API Error:", error);
            return NextResponse.json(
                { error: "Failed to generate speech" },
                { status: response.status }
            );
        }

        // Return audio stream
        // We can pass the stream through, or buffer it. 
        // For simplicity in Next.js App Router, we can return the blob directly.
        const audioBlob = await response.blob();
        const headers = new Headers();
        headers.set("Content-Type", "audio/mpeg");

        return new NextResponse(audioBlob, { headers });

    } catch (error) {
        console.error("Voice API Error:", error);
        return NextResponse.json(
            { error: "Internal Server Error" },
            { status: 500 }
        );
    }
}
