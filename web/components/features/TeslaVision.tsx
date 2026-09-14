"use client";

import { useEffect, useRef, useState } from "react";
import { Maximize2, Minimize2, Power, Volume2 } from "lucide-react";

// CONFIGURATION
const STREAM_URL = "http://192.168.38.209:81/stream"; // Your ESP32 IP
const DETECTION_INTERVAL_MS = 100; // Run detection every 100ms

type DetectedObject = {
    color: "Red" | "Black" | "Green" | "Yellow";
    rect: { x: number; y: number; w: number; h: number };
    angle: number;
};

interface TeslaVisionProps {
    isMatchActive: boolean;
    onLog?: (message: string) => void;
    onArchive?: (data: { filename: string, url: string }) => void;
}

export default function TeslaVision({ isMatchActive, onLog, onArchive }: TeslaVisionProps) {
    const [isPlaying, setIsPlaying] = useState(false);
    const [activeNavColor, setActiveNavColor] = useState<string | null>(null);
    const [activeNavAngle, setActiveNavAngle] = useState(0);

    const [geminiStatus, setGeminiStatus] = useState<"on_track" | "drifting_left" | "drifting_right" | "off_track" | "idle" | "error">("idle");
    const [lastCue, setLastCue] = useState<string>("");
    // const [isMatchActive, setIsMatchActive] = useState(false); // PROPPED INSTEAD
    const [targetVisible, setTargetVisible] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [offPathCount, setOffPathCount] = useState(0);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    const videoRef = useRef<HTMLImageElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    // Toggle Stream
    const toggleStream = () => {
        if (isPlaying) {
            setIsPlaying(false);
        } else {
            setIsPlaying(true);
        }
    };

    useEffect(() => {
        if (!isPlaying) return;
        const interval = setInterval(runDetection, DETECTION_INTERVAL_MS);
        return () => clearInterval(interval);
    }, [isPlaying]);

    // GEMINI ANALYSIS LOOP
    useEffect(() => {
        if (!isMatchActive || !isPlaying) return;

        const analyzeInterval = setInterval(async () => {
            await analyzeFrame();
        }, 15000); // 15 seconds

        return () => clearInterval(analyzeInterval);
    }, [isMatchActive, isPlaying]);

    // [STEP 4] RECORDING LOGIC
    useEffect(() => {
        if (isMatchActive) {
            setOffPathCount(0); // Reset count on new match
            startRecording();
        } else {
            stopRecordingAndUpload();
        }
    }, [isMatchActive]);

    const startRecording = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        try {
            // Capture canvas stream (30FPS)
            const stream = canvas.captureStream(30);
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: "video/webm;codecs=vp9"
            });

            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    chunksRef.current.push(event.data);
                }
            };

            mediaRecorder.start();
            setIsRecording(true);
            console.log("🎥 Recording Started");

        } catch (e) {
            console.error("Failed to start recording:", e);
        }
    };

    const stopRecordingAndUpload = async () => {
        if (!mediaRecorderRef.current || mediaRecorderRef.current.state === "inactive") return;

        mediaRecorderRef.current.stop();
        setIsRecording(false);
        console.log("🎥 Recording Stopped, processing...");

        // Wait a bit for the last chunk
        setTimeout(async () => {
            const blob = new Blob(chunksRef.current, { type: "video/webm" });
            if (blob.size === 0) return;

            // Pass the current offPathCount to upload
            await uploadVideo(blob, offPathCount);
        }, 500);
    };

    const uploadVideo = async (videoBlob: Blob, finalOffPathCount: number) => {
        setIsUploading(true);
        const formData = new FormData();
        formData.append("file", videoBlob, "match_recording.webm");
        formData.append("offPathCount", finalOffPathCount.toString());

        try {
            const res = await fetch("/api/archive/upload", {
                method: "POST",
                body: formData,
            });
            const data = await res.json();

            if (data.success) {
                console.log("✅ Video Archived to Snowflake:", data.filename);
                // if (onLog) onLog(`[ARCHIVE] Video saved: ${data.playbackUrl || data.filename}`); // Removed as per user request
                if (onArchive) onArchive({ filename: data.filename, url: data.playbackUrl || "" });
                // Optional: Play a sound or show a notification
            } else {
                console.error("Upload Failed:", data.error);
            }
        } catch (e) {
            console.error("Upload Error:", e);
        } finally {
            setIsUploading(false);
        }
    };

    // [STEP 3] VOICE INTEGRATION
    useEffect(() => {
        if (!lastCue) return;
        playAudio(lastCue);
    }, [lastCue]);

    const playAudio = async (text: string) => {
        if (!text || isSpeaking) return;

        try {
            // Optimistic UI
            setIsSpeaking(true);

            const res = await fetch("/api/voice/speak", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text }),
            });

            if (!res.ok) throw new Error("Audio generation failed");

            const blob = await res.blob();
            const audio = new Audio(URL.createObjectURL(blob));

            audio.onended = () => setIsSpeaking(false);
            audio.onerror = () => setIsSpeaking(false);

            await audio.play();

        } catch (e) {
            console.error("Audio Error:", e);
            setIsSpeaking(false);
        }
    };

    const analyzeFrame = async () => {
        const img = videoRef.current;
        const canvas = canvasRef.current;
        if (!img || !canvas || !img.complete) return;

        setIsAnalyzing(true); // START THINKING

        // Draw current frame to get base64
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            setIsAnalyzing(false);
            return;
        }

        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const base64Image = canvas.toDataURL("image/jpeg", 0.6); // Compress quality

        try {
            const res = await fetch("/api/gemini/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: base64Image }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || `API Error: ${res.status}`);
            }

            if (data.status) {
                setGeminiStatus(data.status);

                // Increment Off-Path Count
                if (data.status === 'off_track' || data.status === 'drifting_left' || data.status === 'drifting_right') {
                    setOffPathCount(prev => prev + 1);
                }

                setLastCue(data.commentary_cue);
                setTargetVisible(data.target_visible);
                console.log("Ref says:", data);
            } else {
                setGeminiStatus("error");
                setLastCue("Invalid response from referee.");
            }

        } catch (err: any) {
            console.error("Gemini Analysis Failed:", err);
            setGeminiStatus("error");
            // Show the actual error message if available
            setLastCue(err.message || "Connection to referee lost.");
        } finally {
            setIsAnalyzing(false); // STOP THINKING
        }
    };

    // Helper: Convert RGB to HSV
    // Returns h [0-180], s [0-255], v [0-255]
    const rgbToHsv = (r: number, g: number, b: number) => {
        r /= 255; g /= 255; b /= 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        let h = 0, s = 0, v = max;
        const d = max - min;
        s = max === 0 ? 0 : d / max;

        if (max !== min) {
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }
        return [h * 180, s * 255, v * 255];
    };

    const runDetection = () => {
        const img = videoRef.current;
        const canvas = canvasRef.current;
        if (!img || !canvas || !img.complete || img.naturalWidth === 0) return;

        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        if (!ctx) return;

        // 1. Draw current video frame to canvas
        const w = 320;
        const h = 240;
        canvas.width = w;
        canvas.height = h;
        ctx.drawImage(img, 0, 0, w, h);

        try {
            // 2. Scan pixels using HSV logic
            const frameData = ctx.getImageData(0, 0, w, h);
            const data = frameData.data;

            let sumX = { Red: 0, Green: 0, Black: 0, Yellow: 0 };
            let count = { Red: 0, Green: 0, Black: 0, Yellow: 0 };

            // Optimized Loop: Skip every 4th pixel for speed
            for (let i = 0; i < data.length; i += 16) {
                const r = data[i];
                const g = data[i + 1];
                const b = data[i + 2];

                const [hue, sat, val] = rgbToHsv(r, g, b);

                // BLACK DETECTION: Low Value (Brightness)
                // Adjust this threshold (40-60 usually works for black objects)
                if (val < 60) {
                    sumX.Black += (i / 4) % w;
                    count.Black++;
                }
                // COLORS: High Saturation & Value
                else if (sat > 80 && val > 80) {
                    // RED
                    if (hue < 10 || hue > 160) {
                        sumX.Red += (i / 4) % w;
                        count.Red++;
                    }
                    // GREEN
                    else if (hue > 35 && hue < 95) {
                        sumX.Green += (i / 4) % w;
                        count.Green++;
                    }
                    // YELLOW
                    else if (hue > 15 && hue < 35) {
                        sumX.Yellow += (i / 4) % w;
                        count.Yellow++;
                    }
                }
            }

            // Logic: If enough pixels of a color, assume object
            const THRESHOLD = 100;

            let foundColor = null;
            let foundAngle = 0;

            // Priority Logic
            if (count.Green > THRESHOLD) {
                foundColor = "Green";
                const centerX = sumX.Green / count.Green;
                foundAngle = (centerX - w / 2) / (w / 2) * 45;
            }
            else if (count.Red > THRESHOLD) {
                foundColor = "Red";
                const centerX = sumX.Red / count.Red;
                foundAngle = (centerX - w / 2) / (w / 2) * 45;
            }
            else if (count.Black > THRESHOLD) {
                foundColor = "Black";
                const centerX = sumX.Black / count.Black;
                foundAngle = (centerX - w / 2) / (w / 2) * 45;
            }

            // State Update
            setActiveNavColor(foundColor);
            if (foundColor) {
                // Calibration Offset: Camera is tilted. -21 degrees raw = 0 degrees straight.
                setActiveNavAngle(foundAngle + 21);
            } else {
                setActiveNavAngle(0);
            }

        } catch (e) {
            console.error("Vision Error:", e);
        }
    };

    return (
        <div className="flex h-full w-full bg-black/20">

            {/* LEFT: Camera Feed */}
            <div className="flex-1 relative border-r border-white/10 group">
                <img
                    ref={videoRef}
                    src={isPlaying ? STREAM_URL : ""}
                    className="w-full h-full object-cover opacity-80"
                    crossOrigin="anonymous"
                    alt=""
                />

                <div className="absolute top-3 left-3 flex gap-2">
                    <div className={`px-2 py-0.5 rounded text-[10px] font-mono tracking-wider backdrop-blur-md border border-white/10
                    ${isPlaying ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-500'}`}>
                        CAM_01: {isPlaying ? "LIVE" : "OFFLINE"}
                    </div>
                </div>

                {/* VISUAL INDICATORS FOR GEMINI */}
                {isMatchActive && (
                    <div className="absolute top-3 right-3 flex flex-col gap-2 items-end">
                        <div className={`flex items-center gap-2 px-2 py-1 rounded-full border border-white/10 backdrop-blur-md ${geminiStatus === 'on_track' ? 'bg-green-500/20 text-green-300' :
                            geminiStatus === 'error' ? 'bg-red-900/40 text-red-500 border-red-500/50' :
                                (geminiStatus === 'off_track' || geminiStatus.includes('drifting')) ? 'bg-red-500/20 text-red-300' :
                                    'bg-yellow-500/20 text-yellow-300'
                            }`}>
                            <div className={`w-2 h-2 rounded-full ${geminiStatus === 'on_track' ? 'bg-green-500 animate-pulse' :
                                geminiStatus === 'error' ? 'bg-red-500' :
                                    (geminiStatus === 'off_track' || geminiStatus.includes('drifting')) ? 'bg-red-500 animate-ping' :
                                        'bg-yellow-500'
                                }`}></div>
                            <span className="text-[10px] font-mono uppercase font-bold">{geminiStatus.replace('_', ' ')}</span>
                        </div>

                        {/* ANALYZING INDICATOR */}
                        {isAnalyzing && (
                            <div className="flex items-center gap-2 px-2 py-0.5 rounded border border-blue-500/30 bg-blue-500/10 backdrop-blur-md">
                                <div className="animate-spin h-3 w-3 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                                <span className="text-[10px] font-mono text-blue-300">THINKING...</span>
                            </div>
                        )}

                        {/* SPEAKING INDICATOR */}
                        {isSpeaking && (
                            <div className="flex items-center gap-2 px-2 py-0.5 rounded border border-purple-500/30 bg-purple-500/10 backdrop-blur-md">
                                <Volume2 className="w-3 h-3 text-purple-400 animate-pulse" />
                                <span className="text-[10px] font-mono text-purple-300">SPEAKING...</span>
                            </div>
                        )}

                        {/* RECORDING INDICATOR */}
                        {isRecording && (
                            <div className="flex items-center gap-2 px-2 py-0.5 rounded border border-red-500/30 bg-red-500/10 backdrop-blur-md">
                                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_5px_red]"></div>
                                <span className="text-[10px] font-mono text-red-300">REC</span>
                            </div>
                        )}

                        {/* UPLOADING INDICATOR */}
                        {isUploading && (
                            <div className="flex items-center gap-2 px-2 py-0.5 rounded border border-blue-500/30 bg-blue-500/10 backdrop-blur-md">
                                <div className="animate-bounce text-[10px]">☁️</div>
                                <span className="text-[10px] font-mono text-blue-300">ARCHIVING...</span>
                            </div>
                        )}

                        {targetVisible && (
                            <div className="px-2 py-0.5 bg-blue-500/20 border border-blue-500/30 text-blue-300 text-[10px] font-mono rounded">
                                TARGET_LOCKED
                            </div>
                        )}

                        {lastCue && (
                            <div className="max-w-[200px] bg-black/50 backdrop-blur p-2 rounded border-l-2 border-neonBlue">
                                <p className="text-[10px] text-gray-300 italic">"{lastCue}"</p>
                            </div>
                        )}
                    </div>
                )}


                <canvas ref={canvasRef} className="hidden" />

                <div className="absolute bottom-5 left-0 right-0 flex justify-center gap-4">
                    {!isPlaying && (
                        <button
                            onClick={toggleStream}
                            className="flex items-center gap-2 px-6 py-2 bg-neonBlue/20 hover:bg-neonBlue/40 text-neonBlue border border-neonBlue rounded uppercase text-xs font-bold tracking-widest transition-all"
                        >
                            <Power className="w-4 h-4" />
                            INIT_VISION_SYSTEM
                        </button>
                    )}
                </div>
            </div>

            {/* RIGHT: navigation HUD */}
            <div className="w-[40%] bg-gray-900/80 relative overflow-hidden flex flex-col">
                <div className="absolute top-0 left-0 right-0 p-3 z-10 flex justify-between items-start bg-gradient-to-b from-black/80 to-transparent">
                    <div className="text-[10px] text-gray-400 font-mono">
                        <div>V_NAV_SYSTEM_V2</div>
                        <div className="text-white font-bold">{activeNavColor ? activeNavColor.toUpperCase() : "IDLE"}</div>
                    </div>
                    <div className="text-xs font-mono text-neonBlue">{Math.round(activeNavAngle)}°</div>
                </div>

                <div className="flex-1 relative perspective-container">
                    <div
                        className={`absolute bottom-0 left-1/2 -translate-x-1/2 w-32 h-[120%] origin-bottom transition-all duration-300
                  ${activeNavColor === 'Green' ? 'bg-gradient-to-t from-green-500/30 to-transparent' :
                                activeNavColor === 'Red' ? 'bg-gradient-to-t from-red-500/30 to-transparent' :
                                    activeNavColor === 'Black' ? 'bg-gradient-to-t from-gray-200/20 to-transparent' :
                                        'bg-gradient-to-t from-gray-700/20 to-transparent'}`}
                        style={{
                            transform: `translateX(-50%) skewX(${activeNavAngle * -1.5}deg)`,
                            clipPath: "polygon(20% 0%, 80% 0%, 100% 100%, 0% 100%)"
                        }}
                    >
                        <div className="absolute top-0 bottom-0 left-2 w-0.5 bg-white/20"></div>
                        <div className="absolute top-0 bottom-0 right-2 w-0.5 bg-white/20"></div>
                    </div>

                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2">
                        {/* Rover marker */}
                        <img
                            src="/rover.svg"
                            alt="Rover"
                            className="w-20 h-auto drop-shadow-[0_0_15px_rgba(255,255,255,0.2)] opacity-100"
                        />
                    </div>
                </div>
            </div>

        </div>
    );
}
