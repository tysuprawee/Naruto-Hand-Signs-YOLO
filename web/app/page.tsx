import Link from "next/link";
import { Sword, Scroll, ArrowRight, Github, Twitter, Info, Shield, InfoIcon, Youtube, Instagram } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#fafafa] text-zinc-900 font-sans selection:bg-black selection:text-white">
      {/* Minimal Header */}
      <header className="fixed top-0 w-full z-50 bg-[#fafafa]/80 backdrop-blur-md border-b border-zinc-200">
        <div className="container mx-auto flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 bg-black text-white flex items-center justify-center font-bold rounded-md">
              忍
            </div>
            <span className="font-bold tracking-tight text-lg">NINJA ACADEMY</span>
          </div>
          <nav className="hidden md:flex gap-8 text-sm font-medium text-zinc-500">
            <Link href="#mission" className="hover:text-black transition-colors">Mission</Link>
            <Link href="#dev" className="hover:text-black transition-colors">Sensei</Link>
          </nav>
        </div>
      </header>

      <main className="pt-32 pb-20 px-6 container mx-auto max-w-5xl">

        {/* Hero Section - Clean & Bold */}
        <section className="mb-24 flex flex-col md:flex-row items-center gap-12">
          <div className="flex-1 space-y-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-200 bg-white text-xs font-semibold text-zinc-600">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              v1.0 Research Preview
            </div>

            <h1 className="text-6xl md:text-8xl font-black tracking-tighter leading-[0.9]">
              MASTER <br />
              YOUR <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-600 to-red-900">JUTSU.</span>
            </h1>

            <p className="text-xl text-zinc-500 max-w-md leading-relaxed">
              The first open-source, privacy-focused Ninja Hand Sign trainer.
              Powered by local AI. No data leaves your device.
            </p>

            <div className="flex items-center gap-4 pt-4">
              <Link
                href="/play"
                className="group h-14 px-8 bg-black text-white text-lg font-bold rounded-none flex items-center gap-3 hover:bg-zinc-800 transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,0.1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]"
              >
                ENTER DOJO
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>

          {/* Decorative / minimal graphic */}
          <div className="flex-1 flex justify-center grayscale opacity-80">
            {/* Abstract 'Circle' or Zen aesthetic */}
            <div className="w-64 h-64 md:w-96 md:h-96 border-[20px] border-zinc-900 rounded-full flex items-center justify-center p-12">
              <div className="w-full h-full bg-zinc-100 rounded-full flex items-center justify-center">
                <Sword className="w-24 h-24 text-zinc-900" />
              </div>
            </div>
          </div>
        </section>

        {/* Developer / Message Section - "The Scroll" */}
        <section id="dev" className="grid md:grid-cols-12 gap-12 border-t border-zinc-200 pt-24">
          <div className="md:col-span-4 space-y-2">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Scroll className="w-5 h-5" />
              Developer's Note
            </h2>
            <p className="text-zinc-400 text-sm">From the desk of the Sensei</p>
          </div>

          <div className="md:col-span-8">
            <div className="bg-white border border-zinc-200 p-8 shadow-sm relative overflow-hidden">
              {/* Decorative 'tape' */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-4 bg-red-100/50 -rotate-1"></div>

              <div className="flex items-start gap-6">
                <div className="w-16 h-16 bg-zinc-100 rounded-full flex-shrink-0 flex items-center justify-center border border-zinc-200 overflow-hidden">
                  <img src="/dev.jpg" alt="Sensei Ty" className="w-full h-full object-cover" />
                </div>
                <div className="space-y-4">
                  <p className="text-lg font-medium leading-relaxed">
                    "I built this project purely for education and research—it is completely <span className="font-bold underline">non-profit</span>.
                    My goal is to democratize AI by proving sophisticated models can run right in your browser, respecting your privacy.
                    If this helps you on your ninja way, consider contributing data to help the model learn!"
                  </p>

                  <div className="flex gap-4 pt-2">
                    <a href="https://www.youtube.com/@James_Uzumaki" target="_blank" className="text-sm font-bold text-zinc-900 flex items-center gap-2 hover:underline">
                      <Youtube className="w-4 h-4 text-red-600" /> @James_Uzumaki
                    </a>
                    <a href="https://www.instagram.com/james.uzumaki_/" target="_blank" className="text-sm font-bold text-zinc-900 flex items-center gap-2 hover:underline">
                      <Instagram className="w-4 h-4 text-pink-600" /> @james.uzumaki_
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Stats / Info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-12">
              <div>
                <div className="text-3xl font-black">12</div>
                <div className="text-xs uppercase tracking-wider text-zinc-500 font-semibold mt-1">Hand Signs</div>
              </div>
              <div>
                <div className="text-3xl font-black">100%</div>
                <div className="text-xs uppercase tracking-wider text-zinc-500 font-semibold mt-1">Client-Side</div>
              </div>
              <div>
                <div className="text-3xl font-black">0ms</div>
                <div className="text-xs uppercase tracking-wider text-zinc-500 font-semibold mt-1">Latency</div>
              </div>
              <div>
                {/* Status Indicator */}
                <div className="flex items-center gap-2 h-9">
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                  </span>
                  <span className="font-bold">Online</span>
                </div>
                <div className="text-xs uppercase tracking-wider text-zinc-500 font-semibold mt-1">System Status</div>
              </div>
            </div>
          </div>
        </section>

      </main>

      {/* Simple Footer */}
      <footer className="bg-zinc-50 border-t border-zinc-200 py-12 text-center text-zinc-400 text-sm">
        <div className="flex items-center justify-center gap-2 mb-4">
          <Shield className="w-4 h-4" />
          <span>Privacy Preserved. No tracking pixels.</span>
        </div>
        <p>&copy; 2026 Ninja Academy Project. All rights reserved.</p>
      </footer>
    </div>
  );
}
