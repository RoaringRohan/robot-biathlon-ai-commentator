import TeslaVision from "../../components/features/TeslaVision";

export default function VisionPage() {
    return (
        <main className="h-screen w-full bg-black text-white flex flex-col">
            {/* Header */}
            <div className="border-b border-white/10 p-4 flex items-center justify-between">
                <h1 className="text-xl font-bold tracking-widest text-neonBlue">WINTEROPS // VISION SYSTEM</h1>
                <div className="flex gap-4 text-xs font-mono text-gray-400">
                    <span>STATUS: ONLINE</span>
                    <span>MODE: AUTONOMOUS</span>
                </div>
            </div>

            {/* Vision Component */}
            <div className="flex-1 overflow-hidden p-4">
                <div className="h-full w-full border border-white/10 rounded-xl overflow-hidden bg-gray-900/50 backdrop-blur-sm">
                    <TeslaVision isMatchActive={false} />
                </div>
            </div>
        </main>
    );
}
