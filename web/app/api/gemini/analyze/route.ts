import { GoogleGenerativeAI } from "@google/generative-ai";
import { NextResponse } from "next/server";

const API_KEY = process.env.GEMINI_API_KEY;

if (!API_KEY) {
    console.error("GEMINI_API_KEY is not set in environment variables");
}

const genAI = new GoogleGenerativeAI(API_KEY || "");
// Use gemini-2.0-flash as 1.5-flash is not available for this key
const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });

const SYSTEM_INSTRUCTION = `
You are an Olympic Biathlon Referee. Analyze the provided camera frame of a robotic obstacle course. 
Identify if the robot is centered, drifting left, drifting right, or completely off-track. 
Also, check if a target (black circle) is visible. 

You must act as a referee. Do not stay silent. Pick the best fitting status even if uncertain.

Output your response ONLY in the following JSON format: 
{
  "status": "on_track" | "drifting_left" | "drifting_right" | "off_track", 
  "target_visible": true | false, 
  "commentary_cue": "a short dramatic observation"
}`;

export async function POST(req: Request) {
    try {
        if (!API_KEY) {
            return NextResponse.json(
                { error: "GEMINI_API_KEY not configured" },
                { status: 500 }
            );
        }

        const { image } = await req.json();

        if (!image) {
            return NextResponse.json(
                { error: "No image provided" },
                { status: 400 }
            );
        }

        const base64Data = image.replace(/^data:image\/\w+;base64,/, "");
        const prompt = "Analyze this frame for lane discipline and biathlon targets. Return JSON status.";

        const result = await model.generateContent([
            SYSTEM_INSTRUCTION,
            prompt,
            {
                inlineData: {
                    data: base64Data,
                    mimeType: "image/jpeg",
                },
            },
        ]);

        const response = await result.response;
        const text = response.text();

        console.log("Gemini Raw Response:", text);

        // Robust JSON extraction
        let jsonStr = text;
        const jsonMatch = text.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
            jsonStr = jsonMatch[0];
        }

        let analysis;
        try {
            analysis = JSON.parse(jsonStr);
        } catch (e) {
            console.error("Failed to parse JSON from Gemini:", text);
            analysis = {
                status: "off_track", // Fail safe to off_track if we can't read it
                target_visible: false,
                commentary_cue: "Referee communication error. Penalty loop!"
            };
        }

        return NextResponse.json(analysis);

    } catch (error: any) {
        console.error("Gemini API Error:", error.message);
        return NextResponse.json(
            { error: error.message || "Internal Server Error" },
            { status: 500 }
        );
    }
}
