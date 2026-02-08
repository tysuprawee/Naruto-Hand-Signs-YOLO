import Link from "next/link";
import { Sword, Scroll, ArrowRight, Video, Trophy, UploadCloud, Youtube, Instagram, Shield, Info } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-ninja-bg text-ninja-text font-sans selection:bg-ninja-accent selection:text-white">
      {/* Background Image */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: "url('/village.jpg')",
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'grayscale(100%) contrast(120%)' // Stylized look
        }}
      ></div>

      {/* Header */}
      <header className="fixed top-0 w-full z-50 bg-ninja-bg/80 backdrop-blur-md border-b border-ninja-border">
        <div className="container mx-auto flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 relative">
              <img src="/logo2.png" alt="Shinobi Academy" className="object-contain w-full h-full" />
            </div>
            <span className="font-bold tracking-tight text-lg text-white">SHINOBI ACADEMY</span>
          </div>
          <nav className="hidden md:flex gap-8 text-sm font-medium text-ninja-dim">
            <Link href="#features" className="hover:text-ninja-accent transition-colors">Features</Link>
            <Link href="#dev" className="hover:text-ninja-accent transition-colors">Dev</Link>
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
            {/* Badges Container */}
            <div className="flex flex-col items-start gap-4">
              {/* Global Launch Date Pill */}
              <div className="inline-flex items-center gap-3 px-5 py-2 rounded-full border border-ninja-accent/50 bg-ninja-accent/10 backdrop-blur-md shadow-[0_0_20px_rgba(255,120,50,0.2)]">
                <span className="flex h-3 w-3 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ninja-accent opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-ninja-accent"></span>
                </span>
                <span className="text-ninja-accent font-bold tracking-widest text-xs uppercase">Global Launch</span>
                <div className="w-px h-4 bg-ninja-accent/30"></div>
                <span className="text-white font-black tracking-tighter text-lg">FEB 21</span>
              </div>

              {/* System Status */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-ninja-border bg-ninja-card text-[10px] font-bold font-mono text-ninja-dim uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                v1.0 SYSTEM ONLINE • UNOFFICIAL FANGAME
              </div>
            </div>

            <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-[1.1] text-white">
              MASTER YOUR <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-ninja-accent to-red-500">
                JUTSUS.
              </span>
            </h1>

            <p className="text-xl text-ninja-dim max-w-lg leading-relaxed">
              Train real hand signs using AI computer vision. Level up, unlock jutsus, and climb the ranks from Student to Hokage.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-4">

              {/* Play Button Removed for now */}
              {/* <Link
                href="/play"
                className="group h-14 px-8 bg-ninja-accent hover:bg-ninja-accent-glow text-white text-lg font-bold rounded-lg flex items-center gap-3 transition-all shadow-[0_0_20px_rgba(255,120,50,0.3)] hover:shadow-[0_0_30px_rgba(255,120,50,0.5)] hover:-translate-y-1"
              >
                PLAY NOW
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link> */}


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
            </div>
          </div>

          {/* Hero Visual */}
          {/* Hero Visual */}
          <div className="flex-1 relative flex flex-col justify-center items-center perspective-container">
            <div className="absolute inset-0 bg-ninja-accent/20 blur-[150px] rounded-full opacity-40"></div>

            <div className="relative w-full max-w-[800px] aspect-square flex items-center justify-center p-0 animate-float-3d">
              <img
                src="/logo2.png"
                alt="Shinobi Academy Emblem"
                className="w-full h-full object-contain"
              />
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
              <img src="/me1.png" alt="Dev" className="w-full h-full object-cover" />
            </div>

            <div className="space-y-6 text-center md:text-left">
              <h2 className="text-3xl font-black text-white flex items-center justify-center md:justify-start gap-3">
                <Scroll className="w-8 h-8 text-ninja-accent" />
                DEV
              </h2>
              <p className="text-lg text-ninja-dim max-w-2xl leading-relaxed space-y-4">
                <span className="block">
                  "I built the Shinobi Academy as a <strong>non-profit fan project</strong> to prove that advanced AI can be fun, accessible, and private.
                </span>
                <span className="block text-sm opacity-70 italic">
                  Disclaimer: This project is not affiliated with, endorsed, sponsored, or specifically approved by Masashi Kishimoto, Shueisha, Viz Media, or the Naruto franchise. All original character names and designs are the property of their respective owners.
                </span>
                <span className="block mt-4">
                  The game launches on <span className="text-white font-bold">February 21st</span>. Get ready to master the signs!"
                </span>
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
          <p>&copy; 2026 Shinobi Academy. Built with PyTorch & ONNX.</p>
        </div>
      </footer>
    </div>
  );
}
