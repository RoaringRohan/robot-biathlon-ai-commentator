"use client";

import { Activity, Battery, Wifi, Shield, Disc, Map, Layout, Zap, Play, Square, Snowflake, Database } from "lucide-react";
import Link from 'next/link';
import { useState, useEffect } from 'react';
import TeslaVision from "../components/features/TeslaVision";
import SystemStatus from "../components/features/SystemStatus";

export default function Home() {
    const [isMatchActive, setIsMatchActive] = useState(false);
    const [logs, setLogs] = useState<string[]>([
        "[SYSTEM] Initialization complete.",
        "[INFO] Gemini AI connected.",
        "[INFO] Vision System: Standby.",
        "[WARN] Battery levels optimal."
    ]);

    const addLog = (msg: string) => {
        setLogs(prev => [...prev, msg]);
    };

    const [recordings, setRecordings] = useState<{ filename: string, url: string, time: string }[]>([]);

    const handleArchive = (data: { filename: string, url: string }) => {
        const time = new Date().toLocaleTimeString();
        setRecordings(prev => [{ ...data, time }, ...prev].slice(0, 5));
    };

    // Fetch past recordings on mount
    useEffect(() => {
        const fetchRecordings = async () => {
            try {
                const res = await fetch("/api/archive/list");
                const data = await res.json();
                if (data.recordings) {
                    setRecordings(data.recordings);
                }
            } catch (e) {
                console.error("Failed to load recordings", e);
            }
        };
        fetchRecordings();
    }, []);

    return (
        <main className="h-screen w-full bg-[#0a0a0a] text-white flex flex-col p-2 gap-2">

            <header className="h-14 border border-white/10 rounded-lg bg-black/40 backdrop-blur flex items-center justify-between px-4">
                <div className="flex items-center gap-2">
                    <Disc className={`w-6 h-6 text-cyan-400 ${isMatchActive ? 'animate-spin' : 'animate-spin-slow'}`} />
                    <span className="font-bold tracking-widest text-lg">OLYMPUS // COMMAND</span>
                </div>

                <nav className="flex gap-6 text-xs font-mono">
                    <Link href="/" className="text-cyan-400 border-b border-cyan-400">DASHBOARD</Link>
                    <Link href="/vision" className="text-gray-400 hover:text-white transition-colors">VISION SYSTEM</Link>
                    <span className="text-gray-600 cursor-not-allowed">SETTINGS</span>
                </nav>

                <div className="flex items-center gap-4 text-xs font-mono">
                    {isMatchActive && (
                        <div className="flex items-center gap-1 text-red-500 animate-pulse">
                            <div className="w-2 h-2 bg-red-500 rounded-full" />
                            <span>MATCH LIVE</span>
                        </div>
                    )}
                    <div className="flex items-center gap-1 text-green-400">
                        <Wifi className="w-3 h-3" />
                        <span>ONLINE</span>
                    </div>
                    <div className="flex items-center gap-1 text-cyan-400">
                        <Battery className="w-3 h-3" />
                        <span>98%</span>
                    </div>
                </div>
            </header>

            {/* Main Grid */}
            <div className="flex-1 grid grid-cols-12 grid-rows-6 gap-2 min-h-0">

                {/* LEFT COL: Snowflake & Telemetry */}
                <div className="col-span-3 row-span-6 flex flex-col gap-2">

                    {/* TOP HALF: Snowflake Archives */}
                    <div className="flex-1 bg-black/40 border border-white/10 rounded-lg p-4 flex flex-col gap-4 overflow-hidden">
                        <h2 className="text-xs font-bold text-gray-400 tracking-wider flex items-center gap-2">
                            <Snowflake className="w-4 h-4 text-cyan-400" /> SNOWFLAKE ARCHIVES
                        </h2>

                        <div className="flex-1 overflow-y-auto space-y-2">
                            {recordings.length === 0 ? (
                                <div className="text-[10px] text-gray-600 italic text-center mt-10">
                                    No recordings yet.
                                    <br />Complete a match to archive.
                                </div>
                            ) : (
                                recordings.map((rec, i) => (
                                    <a
                                        key={i}
                                        href={rec.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block p-2 bg-white/5 border border-white/5 rounded hover:bg-white/10 hover:border-cyan-500/50 transition-all group"
                                    >
                                        <div className="flex justify-between items-start mb-1">
                                            <div className="text-[10px] text-cyan-300 font-mono font-bold">MATCH_REC_{5 - i}</div>
                                            <div className="text-[9px] text-gray-500">{rec.time}</div>
                                        </div>
                                        <div className="text-[9px] text-gray-400 truncate group-hover:text-white">
                                            {rec.filename}
                                        </div>
                                    </a>
                                ))
                            )}
                        </div>
                    </div>

                    {/* BOTTOM HALF: Telemetry Placeholder */}
                    <div className="flex-1 bg-black/40 border border-white/10 rounded-lg p-4 flex flex-col gap-4 opacity-50">
                        <h2 className="text-xs font-bold text-gray-400 tracking-wider flex items-center gap-2">
                            <Database className="w-4 h-4" /> SESSION TELEMETRY
                        </h2>

                        <div className="flex-1 relative border border-dashed border-white/10 rounded flex items-center justify-center">
                            <div className="text-[10px] text-gray-600 text-center">
                                WAITING FOR MONGODB CLUSTER
                                <br />
                                [PENDING IMPLEMENTATION]
                            </div>
                        </div>
                    </div>

                </div>

                {/* CENTER: Vision System */}
                <div className="col-span-6 row-span-4 bg-black/40 border border-white/10 rounded-lg relative overflow-hidden group">
                    <div className="w-full h-full p-2">
                        <TeslaVision isMatchActive={isMatchActive} onLog={addLog} onArchive={handleArchive} />
                    </div>
                </div>

                {/* RIGHT: Controls */}
                <div className="col-span-3 row-span-6 bg-black/40 border border-white/10 rounded-lg p-4 flex flex-col gap-4">
                    <h2 className="text-xs font-bold text-gray-400 tracking-wider flex items-center gap-2">
                        <Shield className="w-4 h-4" /> MISSION CONTROL
                    </h2>

                    {/* Start/Stop Match Button */}
                    <button
                        onClick={() => setIsMatchActive(!isMatchActive)}
                        className={`w-full py-4 font-mono text-sm tracking-widest border transition-all rounded flex items-center justify-center gap-2 relative overflow-hidden group
                            ${isMatchActive
                                ? 'bg-red-500/20 border-red-500/50 text-red-500 hover:bg-red-500/30'
                                : 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/30'
                            }`}
                    >
                        {isMatchActive ? (
                            <>
                                <span className="relative z-10">STOP MATCH</span>
                                <div className="absolute inset-0 bg-red-500/10 animate-pulse" />
                            </>
                        ) : (
                            <>
                                <span className="relative z-10">START MATCH</span>
                            </>
                        )}
                    </button>

                    <button className="w-full py-2 bg-red-900/10 border border-red-900/30 text-red-700/70 font-mono text-xs hover:bg-red-900/30 hover:text-red-500 transition-all rounded">
                        EMERGENCY STOP
                    </button>

                    <SystemStatus />
                </div>


                {/* BOTTOM CENTER: Logs */}
                <div className="col-span-6 row-span-2 bg-black/40 border border-white/10 rounded-lg p-3 font-mono text-[10px] text-gray-400 overflow-y-auto flex flex-col-reverse">
                    {logs.map((log, i) => (
                        <div key={i} className={`mb-1 ${log.includes('[WARN]') ? 'text-yellow-500' : log.includes('[ARCHIVE]') ? 'text-green-400' : log.includes('[SYSTEM]') ? 'text-cyan-500' : ''}`}>
                            {log}
                        </div>
                    ))}
                </div>

            </div>
        </main >
    )
}
