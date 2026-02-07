import Link from "next/link";
import { Sword, Scroll, ArrowRight, Video, Trophy, UploadCloud, Youtube, Instagram, Shield, Info } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-ninja-bg text-ninja-text font-sans selection:bg-ninja-accent selection:text-white">
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
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 bg-ninja-accent text-white flex items-center justify-center font-bold rounded-md shadow-[0_0_15px_rgba(255,120,50,0.5)]">
              忍
            </div>
            <span className="font-bold tracking-tight text-lg text-white">JUTSU ACADEMY</span>
          </div>
          <nav className="hidden md:flex gap-8 text-sm font-medium text-ninja-dim">
            <Link href="#features" className="hover:text-ninja-accent transition-colors">Features</Link>
            <Link href="#dev" className="hover:text-ninja-accent transition-colors">Sensei</Link>
            <Link href="/leaderboard" className="flex items-center gap-2 text-ninja-accent font-bold hover:text-ninja-accent-glow transition-colors">
              <Trophy className="w-4 h-4" />
              Leaderboard
            </Link>
          </nav>
        </div>
      </header>

      <main className="relative z-10 pt-32 pb-20 px-6 container mx-auto max-w-6xl">

        {/* Hero Section */}
        <section className="mb-32 flex flex-col md:flex-row items-center gap-16">
          <div className="flex-1 space-y-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-ninja-border bg-ninja-card text-xs font-bold font-mono text-ninja-accent uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-ninja-accent animate-pulse shadow-[0_0_8px_var(--color-ninja-accent)]"></span>
              v1.0 SYSTEM ONLINE
            </div>

            <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-[1.1] text-white">
              MASTER YOUR <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-ninja-accent to-red-500">
                INNER CHAKRA.
              </span>
            </h1>

            <p className="text-xl text-ninja-dim max-w-lg leading-relaxed">
              Train real hand signs using AI computer vision. Level up, unlock jutsus, and climb the ranks from Student to Hokage.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-4">
              <Link
                href="/play"
                className="group h-14 px-8 bg-ninja-accent hover:bg-ninja-accent-glow text-white text-lg font-bold rounded-lg flex items-center gap-3 transition-all shadow-[0_0_20px_rgba(255,120,50,0.3)] hover:shadow-[0_0_30px_rgba(255,120,50,0.5)] hover:-translate-y-1"
              >
                ENTER DOJO
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>

              <Link
                href="/leaderboard"
                className="h-14 px-8 bg-ninja-card hover:bg-ninja-hover border border-ninja-border text-white text-lg font-bold rounded-lg flex items-center gap-3 transition-all"
              >
                <Trophy className="w-5 h-5 text-ninja-dim" />
                VIEW RANKS
              </Link>
            </div>

            <div className="flex items-center gap-4 text-xs font-medium text-ninja-dim pt-4">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-ninja-success" /> Privacy First (Local AI)
              </div>
              <div className="w-1 h-1 bg-ninja-border rounded-full"></div>
              <div className="flex items-center gap-2">
                <Video className="w-4 h-4 text-blue-400" /> GPU Recommended
              </div>
            </div>
          </div>

          {/* Hero Visual */}
          <div className="flex-1 relative">
            <div className="absolute inset-0 bg-ninja-accent/20 blur-[100px] rounded-full opacity-50"></div>
            <div className="relative bg-ninja-panel border border-ninja-border rounded-2xl p-2 shadow-2xl rotate-3 hover:rotate-0 transition-all duration-500">
              <div className="aspect-video bg-black rounded-xl overflow-hidden relative group">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center space-y-4">
                    <div className="w-20 h-20 bg-ninja-accent/20 rounded-full flex items-center justify-center mx-auto border border-ninja-accent/50">
                      <Video className="w-8 h-8 text-ninja-accent" />
                    </div>
                    <p className="font-bold text-ninja-dim">LIVE WEBCAM PREVIEW</p>
                  </div>
                </div>
                {/* Scanline effect */}
                <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.5)_50%)] bg-[length:100%_4px] pointer-events-none opacity-20"></div>
              </div>
            </div>
          </div>
        </section>

        {/* Features / Stats */}
        <section id="features" className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-32">
          {[
            { label: "Hand Signs", value: "12", sub: "Real-time Detection", icon: "✋" },
            { label: "Jutsu Arts", value: "5+", sub: "Fireball, Chidori & More", icon: "🔥" },
            { label: "Latency", value: "~15ms", sub: "Powered by ONNX", icon: "⚡" },
          ].map((stat, i) => (
            <div key={i} className="bg-ninja-card border border-ninja-border p-8 rounded-2xl hover:border-ninja-accent/50 transition-colors group">
              <div className="text-4xl mb-4 group-hover:scale-110 transition-transform duration-300 inline-block">{stat.icon}</div>
              <div className="text-4xl font-black font-mono text-white mb-2">{stat.value}</div>
              <div className="text-lg font-bold text-ninja-accent mb-1">{stat.label}</div>
              <div className="text-sm text-ninja-dim">{stat.sub}</div>
            </div>
          ))}
        </section>

        {/* Dev Section */}
        <section id="dev" className="bg-ninja-panel border border-ninja-border rounded-3xl p-12 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-ninja-accent/10 blur-[80px] rounded-full pointer-events-none"></div>

          <div className="flex flex-col md:flex-row gap-12 items-center relative z-10">
            <div className="w-32 h-32 md:w-48 md:h-48 rounded-full border-4 border-ninja-bg overflow-hidden shadow-2xl shrink-0">
              <img src="/dev.jpg" alt="Dev" className="w-full h-full object-cover" />
            </div>

            <div className="space-y-6 text-center md:text-left">
              <h2 className="text-3xl font-black text-white flex items-center justify-center md:justify-start gap-3">
                <Scroll className="w-8 h-8 text-ninja-accent" />
                MESSAGE FROM SENSEI
              </h2>
              <p className="text-lg text-ninja-dim max-w-2xl leading-relaxed">
                "I built the Jutsu Academy to prove that advanced AI can be fun, accessible, and private.
                Join thousands of other ninjas, master the signs, and contribute to the open-source dataset
                to help the model learn even more distinctive styles!"
              </p>

              <div className="flex flex-wrap justify-center md:justify-start gap-4">
                <a href="https://www.youtube.com/@James_Uzumaki" target="_blank" className="bg-red-600/10 hover:bg-red-600/20 text-red-500 hover:text-red-400 px-6 py-3 rounded-lg font-bold flex items-center gap-2 transition-colors border border-red-600/20">
                  <Youtube className="w-5 h-5" /> YouTube
                </a>
                <a href="https://www.instagram.com/james.uzumaki_/" target="_blank" className="bg-pink-600/10 hover:bg-pink-600/20 text-pink-500 hover:text-pink-400 px-6 py-3 rounded-lg font-bold flex items-center gap-2 transition-colors border border-pink-600/20">
                  <Instagram className="w-5 h-5" /> Instagram
                </a>
              </div>
            </div>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-ninja-border bg-ninja-bg py-12">
        <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6 text-ninja-muted text-sm">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="font-mono">SYSTEM OPERATIONAL</span>
          </div>
          <p>&copy; 2026 Jutsu Academy. Built with PyTorch & ONNX.</p>
        </div>
      </footer>
    </div>
  );
}
