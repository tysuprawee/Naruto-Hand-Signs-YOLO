"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/utils/supabase";
import Link from "next/link";
import { ArrowLeft, Trophy, Clock, Zap, Crown } from "lucide-react";

interface LeaderboardEntry {
    id: string;
    created_at: string;
    username: string;
    score_time: number;
    mode: string;
    discord_id?: string;
    avatar_url?: string;
}

export default function LeaderboardPage() {
    const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [mode, setMode] = useState("Fireball"); // Default mode

    const modes = ["Fireball", "Chidori", "Water Dragon", "Shadow Clone", "Phoenix Flower"];

    useEffect(() => {
        async function fetchLeaderboard() {
            setLoading(true);

            // Convert display mode to database format (UPPERCASE)
            // e.g. "Water Dragon" -> "WATER DRAGON" (assuming DB uses spaces)
            // If DB uses underscores for some (like SHADOW_CLONE), we might need a map.
            // Based on screenshot "FIREBALL", "CHIDORI", assuming direct upper case.
            const dbMode = mode.toUpperCase();

            // 1. Fetch Leaderboard
            // data already includes avatar_url according to user schema
            const { data: leaderboardData, error: leaderboardError } = await supabase
                .from('leaderboard')
                .select('*')
                .eq('mode', dbMode)
                .order('score_time', { ascending: true })
                .limit(50);

            if (leaderboardError) {
                console.error("Error fetching leaderboard:", leaderboardError);
                setLoading(false);
                return;
            }

            setEntries(leaderboardData || []);
            setLoading(false);
        }

        fetchLeaderboard();
    }, [mode]);

    return (
        <div className="min-h-screen bg-ninja-bg text-ninja-text font-sans selection:bg-ninja-accent selection:text-white pb-20">
            {/* Heavy Grid Background Effect */}
            <div className="fixed inset-0 z-0 pointer-events-none opacity-[0.03]"
                style={{
                    backgroundImage: `linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)`,
                    backgroundSize: '40px 40px'
                }}
            ></div>

            {/* Header */}
            <header className="fixed top-0 w-full z-50 bg-ninja-bg/80 backdrop-blur-md border-b border-ninja-border">
                <div className="container mx-auto flex h-16 items-center justify-between px-6">
                    <Link href="/" className="flex items-center gap-3 hover:opacity-70 transition-opacity">
                        <div className="h-10 w-10 relative">
                            <img src="/logo2.png" alt="Shinobi Academy" className="object-contain w-full h-full" />
                        </div>
                        <span className="font-bold tracking-tight text-lg text-white">SHINOBI ACADEMY</span>
                    </Link>
                    <nav className="flex gap-4">
                        <Link href="/" className="text-sm font-medium text-ninja-dim hover:text-white flex items-center gap-1">
                            <ArrowLeft className="w-4 h-4" /> Back to Base
                        </Link>
                    </nav>
                </div>
            </header>

            <main className="relative z-10 pt-32 px-6 container mx-auto max-w-4xl">
                <div className="flex flex-col md:flex-row items-center justify-between gap-8 mb-12">
                    <div>
                        <h1 className="text-4xl md:text-5xl font-black tracking-tighter mb-2 flex items-center gap-3 text-white">
                            <Trophy className="w-10 h-10 text-ninja-accent" />
                            LEADERBOARD
                        </h1>
                        <p className="text-ninja-dim">Top ranking Shinobi from around the world.</p>
                    </div>

                    {/* Mode Selector */}
                    <div className="flex flex-wrap gap-2 justify-center">
                        {modes.map((m) => (
                            <button
                                key={m}
                                onClick={() => setMode(m)}
                                className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border
                  ${mode === m
                                        ? "bg-ninja-accent text-white border-ninja-accent shadow-[0_0_15px_rgba(255,120,50,0.3)] scale-105"
                                        : "bg-ninja-card text-ninja-dim border-ninja-border hover:border-ninja-hover hover:text-white"}
                `}
                            >
                                {m}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Table */}
                <div className="bg-ninja-panel border border-ninja-border shadow-2xl rounded-xl overflow-hidden">
                    {loading ? (
                        <div className="p-16 text-center text-ninja-dim animate-pulse flex flex-col items-center gap-4">
                            <Zap className="w-8 h-8 text-ninja-accent animate-bounce" />
                            <p>Fetching Scroll Records...</p>
                        </div>
                    ) : entries.length === 0 ? (
                        <div className="p-16 text-center text-ninja-dim border-t border-dashed border-ninja-border">
                            <p className="mb-4 text-lg">No records found for this Jutsu.</p>
                            <div className="text-sm opacity-50">Be the first to master it!</div>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-ninja-bg border-b border-ninja-border text-xs uppercase text-ninja-dim font-bold tracking-wider">
                                    <tr>
                                        <th className="px-6 py-4 w-20 text-center">Rank</th>
                                        <th className="px-6 py-4">Shinobi</th>
                                        <th className="px-6 py-4 text-right">Time</th>
                                        <th className="px-6 py-4 text-center">Date</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-ninja-border">
                                    {entries.map((entry, index) => (
                                        <tr key={entry.id} className="hover:bg-ninja-hover/30 transition-colors group">
                                            <td className="px-6 py-5 text-center font-bold text-ninja-dim group-hover:text-white">
                                                {index === 0 ? (
                                                    <div className="relative inline-block">
                                                        <Crown className="w-6 h-6 text-yellow-400 mx-auto drop-shadow-md" />
                                                        <div className="absolute inset-0 bg-yellow-400/20 blur-md rounded-full"></div>
                                                    </div>
                                                ) : (
                                                    `#${index + 1}`
                                                )}
                                            </td>
                                            <td className="px-6 py-5 font-medium text-white flex items-center gap-4">
                                                {entry.avatar_url ? (
                                                    <div className={`w-10 h-10 rounded-lg overflow-hidden shadow-lg border border-white/10
                                                        ${index === 0 ? "ring-2 ring-yellow-400" : ""}
                                                    `}>
                                                        <img
                                                            src={entry.avatar_url}
                                                            alt={entry.username}
                                                            className="w-full h-full object-cover"
                                                        />
                                                    </div>
                                                ) : (
                                                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold text-white shadow-lg border border-white/10
                                                        ${index === 0 ? "bg-gradient-to-br from-yellow-400 to-yellow-600" :
                                                            index === 1 ? "bg-gradient-to-br from-gray-300 to-gray-500" :
                                                                index === 2 ? "bg-gradient-to-br from-orange-400 to-orange-600" :
                                                                    "bg-ninja-card border-ninja-border text-ninja-dim"}
                                                    `}>
                                                        {entry.username.charAt(0).toUpperCase()}
                                                    </div>
                                                )}
                                                <div className="flex items-center gap-2">
                                                    <span className={index < 3 ? "text-ninja-accent-glow font-bold" : ""}>{entry.username}</span>
                                                    {entry.discord_id === "308811789544718348" && (
                                                        <span className="text-[10px] bg-red-600 text-white px-1.5 py-0.5 rounded font-black tracking-wider shadow-sm border border-red-400">DEV</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-5 text-right font-mono font-bold text-white">
                                                <div className="flex items-center justify-end gap-2">
                                                    <Clock className="w-4 h-4 text-ninja-dim" />
                                                    <span className={index === 0 ? "text-yellow-400 text-lg" : ""}>{entry.score_time.toFixed(2)}s</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-5 text-center text-xs text-ninja-dim font-mono">
                                                {new Date(entry.created_at).toLocaleDateString()}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
