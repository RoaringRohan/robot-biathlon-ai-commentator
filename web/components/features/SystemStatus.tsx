"use client";

import { useEffect, useState } from 'react';
import { Server, Cpu, Database, Cloud, Radio, Activity } from 'lucide-react';

interface StatusData {
    snowflake: { online: boolean };
    gemini: { online: boolean };
    elevenlabs: { online: boolean };
    digitalocean: { online: boolean; ip: string };
}

export default function SystemStatus() {
    const [status, setStatus] = useState<StatusData | null>(null);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                setStatus(data);
            } catch (e) {
                console.error("Status check failed", e);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    if (!status) return (
        <div className="text-[10px] text-gray-500 animate-pulse">Initializing System Link...</div>
    );

    const ModuleRow = ({ name, icon: Icon, online, extra }: { name: string, icon: any, online: boolean, extra?: string }) => (
        <div className="flex items-center justify-between p-2 bg-white/5 border border-white/5 rounded hover:bg-white/10 transition-colors group">
            <div className="flex items-center gap-3">
                <div className={`p-1.5 rounded bg-black/50 border ${online ? 'border-emerald-500/30 text-emerald-400' : 'border-red-500/30 text-red-500'}`}>
                    <Icon className="w-3 h-3" />
                </div>
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold tracking-wider text-gray-300 group-hover:text-white transition-colors">{name}</span>
                    <span className="text-[9px] font-mono text-gray-600">{extra || (online ? "CONNECTED" : "OFFLINE")}</span>
                </div>
            </div>

            <div className="flex flex-col items-end gap-0.5">
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-emerald-500 shadow-[0_0_5px_#10b981]' : 'bg-red-500 shadow-[0_0_5px_#ef4444]'}`}></div>
                </div>
                {online && <Activity className="w-2 h-2 text-emerald-500/50" />}
            </div>
        </div>
    );

    return (
        <div className="mt-auto flex flex-col gap-2">
            <div className="flex items-center justify-between">
                <div className="text-[10px] text-gray-500 font-mono flex items-center gap-1">
                    <Radio className="w-3 h-3 animate-pulse text-cyan-500" />
                    SYSTEM_INTEGRITY
                </div>
                <div className="text-[9px] text-emerald-500/80 font-mono">ALL SYSTEMS NOMINAL</div>
            </div>

            <div className="space-y-1">
                <ModuleRow
                    name="SNOWFLAKE"
                    icon={Database}
                    online={status.snowflake.online}
                    extra="DATA_WAREHOUSE"
                />
                <ModuleRow
                    name="GEMINI AI"
                    icon={Cpu}
                    online={status.gemini.online}
                    extra="NEURAL_ENGINE"
                />
                <ModuleRow
                    name="ELEVENLABS"
                    icon={Activity}
                    online={status.elevenlabs.online}
                    extra="VOICE_SYNTH"
                />
                <ModuleRow
                    name="DIGITALOCEAN"
                    icon={Server}
                    online={status.digitalocean.online}
                    extra={status.digitalocean.online ? status.digitalocean.ip : "DROPLET_OFFLINE"}
                />
            </div>
        </div>
    );
}
