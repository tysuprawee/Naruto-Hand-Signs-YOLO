"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { ArrowLeft, Camera, RefreshCw, AlertTriangle, Bug, X, UploadCloud, CheckCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";
import { KNNClassifier, normalizeHand } from "@/utils/knn"; // Import our new utils

export default function PlayPage() {
    const router = useRouter();

    useEffect(() => {
        router.push("/");
    }, [router]);

    // Return null or a loading state to prevent the rest of the component from flashing
    return (
        <div className="min-h-screen bg-black flex items-center justify-center">
            <h1 className="text-white text-2xl font-bold animate-pulse">Redirecting to Home...</h1>
        </div>
    );

    // Code helper to stop execution here
    // Original code below is unreachable but kept for restoration later 
    const [classifier, setClassifier] = useState<KNNClassifier | null>(null);
    const [landmarker, setLandmarker] = useState<HandLandmarker | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [prediction, setPrediction] = useState<string>("Initializing...");
    const [fps, setFps] = useState(0);

    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const requestRef = useRef<number>(0);
    const lastVideoTime = useRef<number>(-1);
    const lastFpsUpdateTime = useRef<number>(0);
    const frameCount = useRef<number>(0);
    const lastPredictionTime = useRef<number>(0);

    // Load Resources
    useEffect(() => {
        async function loadResources() {
            try {
                setLoading(true);

                // 1. Load Data
                const response = await fetch("/model/hand_signs_db.json");
                const data = await response.json();
                const knn = new KNNClassifier(data);
                setClassifier(knn);
                console.log("KNN Classifier loaded");

                // 2. Load MediaPipe
                const vision = await FilesetResolver.forVisionTasks(
                    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
                );

                const handLandmarker = await HandLandmarker.createFromOptions(vision, {
                    baseOptions: {
                        modelAssetPath: "/model/hand_landmarker.task",
                        delegate: "GPU"
                    },
                    runningMode: "VIDEO",
                    numHands: 2,
                    minHandDetectionConfidence: 0.3, // Match Python sensitivity
                    minHandPresenceConfidence: 0.3,
                    minTrackingConfidence: 0.3
                });

                setLandmarker(handLandmarker);
                console.log("MediaPipe loaded");
                setLoading(false);

            } catch (e: any) {
                console.error("Load failed:", e);
                setError("Failed to load AI resources. " + e.message);
                setLoading(false);
            }
        }
        loadResources();
    }, []);

    // Camera Setup
    useEffect(() => {
        if (!videoRef.current) return;
        async function setupCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: 640, height: 480 }
                });
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                    videoRef.current.addEventListener("loadeddata", () => {
                        if (videoRef.current) {
                            videoRef.current.play();
                            requestRef.current = requestAnimationFrame(predictLoop);
                        }
                    });
                }
            } catch (err) {
                console.error("Camera error:", err);
                setError("Camera access denied.");
            }
        }
        setupCamera();

        return () => {
            cancelAnimationFrame(requestRef.current);
            if (videoRef.current) {
                videoRef.current.removeEventListener("loadeddata", () => {
                    if (videoRef.current) videoRef.current.play();
                });
                const stream = videoRef.current.srcObject as MediaStream;
                stream?.getTracks().forEach(track => track.stop());
            }
        };
    }, [landmarker, classifier]);

    // Prediction Loop
    const predictLoop = useCallback(() => {
        if (!landmarker || !classifier || !videoRef.current || !canvasRef.current) {
            requestRef.current = requestAnimationFrame(predictLoop);
            return;
        }

        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");

        if (!ctx) {
            requestRef.current = requestAnimationFrame(predictLoop);
            return;
        }

        const now = performance.now();

        // Ensure strictly video frame updates
        if (video.currentTime !== lastVideoTime.current) {
            lastVideoTime.current = video.currentTime;

            // Detect (Fast enough to do every frame usually)
            const results = landmarker.detectForVideo(video, now);

            // Clear & Draw
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            if (results.landmarks && results.landmarks.length === 2) {
                // Drawing - Always smooth
                results.landmarks.forEach((landmarks, index) => {
                    drawConnectors(ctx, landmarks, HandLandmarker.HAND_CONNECTIONS, { color: "#00FF00", lineWidth: 2 });
                    drawLandmarks(ctx, landmarks, { color: "#FF0000", lineWidth: 1 });
                });

                // Classification - THROTTLED to ~10 FPS (every 100ms) to save CPU
                if (now - lastPredictionTime.current > 100) {
                    lastPredictionTime.current = now;

                    let features: number[] = new Array(126).fill(0);

                    // Match Python Logic: Left Hand -> Index 0-62 | Right Hand -> Index 63-125
                    results.handedness.forEach((handCats, index) => {
                        if (index >= results.landmarks.length) return;

                        const label = handCats[0].categoryName; // "Left" or "Right"
                        const landmarks = results.landmarks[index];

                        // FLIP LOGIC:
                        // Python used cv2.flip(1), meaning X was inverted (0->1, 1->0) before MP saw it.
                        // Web uses raw video (unflipped).
                        // We must mathematically flip X to match the training data distribution.
                        const flippedLandmarks = landmarks.map(lm => ({
                            x: 1.0 - lm.x,
                            y: lm.y,
                            z: lm.z
                        }));

                        const normalized = normalizeHand(flippedLandmarks);

                        const offset = (label === "Left") ? 0 : 63;

                        for (let i = 0; i < normalized.length; i++) {
                            features[offset + i] = normalized[i];
                        }
                    });

                    if (classifier) {
                        const result = classifier.predict(features);
                        setPrediction(result);

                        // --- GAME PROGRESS LOGIC ---
                        if (currentStepRef.current < targetSequence.length) {
                            const targetSign = targetSequence[currentStepRef.current];

                            // Fix Casing Issue: DB labels are Title Case (e.g. "Ram"), Target checks are UPPERCASE (e.g. "RAM")
                            // We normalize to UpperCase for comparison
                            if (result.toUpperCase() === targetSign.toUpperCase()) {
                                // If this is a new hold on the correct sign
                                if (lastSign.current !== result) {
                                    lastSignTime.current = now;
                                    lastSign.current = result;
                                }

                                // Check duration
                                const holdDuration = now - lastSignTime.current;
                                if (holdDuration > CONFIRM_DELAY) {
                                    // SUCCESS! Move step
                                    currentStepRef.current += 1;
                                    setCurrentStep(currentStepRef.current);

                                    // Reset
                                    lastSignTime.current = 0;
                                    lastSign.current = "Idle";

                                    // Optional: Sound effect here?
                                    // playSound();
                                }
                            } else {
                                // Wrong sign or Idle resets the hold timer
                                if (result !== lastSign.current) {
                                    lastSignTime.current = now; // Reset timer for new sign
                                    lastSign.current = result;
                                }
                            }
                        }
                    }
                }
            } else {
                // Less than 2 hands = IDLE
                setPrediction("Idle");

                // Optional: Draw single hand if present, but don't predict
                if (results.landmarks) {
                    for (const landmarks of results.landmarks) {
                        drawConnectors(ctx, landmarks, HandLandmarker.HAND_CONNECTIONS, { color: "rgba(255, 255, 255, 0.2)", lineWidth: 1 });
                        drawLandmarks(ctx, landmarks, { color: "rgba(255, 255, 255, 0.2)", lineWidth: 1 });
                    }
                }
            }

            // FPS calculation
            frameCount.current++;
            if (now - lastFpsUpdateTime.current >= 1000) {
                setFps(frameCount.current);
                frameCount.current = 0;
                lastFpsUpdateTime.current = now;
            }
        }

        requestRef.current = requestAnimationFrame(predictLoop);
    }, [landmarker, classifier]);

    // Game Logic State
    // Game Logic State
    const [targetSequence] = useState(["SNAKE", "RAM", "MONKEY", "BOAR", "HORSE", "TIGER"]);

    // We use REFS for the game loop to avoid React State update lag/batching issues
    // But we sync them to state for UI updates
    const currentStepRef = useRef(0);
    const [currentStep, setCurrentStep] = useState(0);

    // Debounce Logic
    const CONFIRM_DELAY = 600; // 600ms hold to confirm
    const lastSign = useRef("Idle");
    const lastSignTime = useRef(0);

    // Helper map for images (lowercase pngs in public)
    const signImages: { [key: string]: string } = {
        "SNAKE": "/snake.png",
        "RAM": "/ram.png",
        "MONKEY": "/monkey.png",
        "BOAR": "/boar.png",
        "HORSE": "/horse.png",
        "TIGER": "/tiger.png",
        "DRAGON": "/dragon.png",
        "BIRD": "/bird.png",
        "DOG": "/dog.png",
        "OX": "/ox.png",
        "HARE": "/hare.png",
        "RAT": "/rat.png"
    };

    return (
        <div className="min-h-screen bg-black text-white p-4 font-sans selection:bg-orange-500 selection:text-white">
            <Link href="/" className="absolute top-4 left-4 z-50 p-3 bg-gray-900/80 rounded-full hover:bg-gray-800 transition backdrop-blur-md border border-gray-700 group">
                <ArrowLeft className="w-6 h-6 text-gray-400 group-hover:text-white transition-colors" />
            </Link>

            <div className="max-w-4xl mx-auto pt-4 pb-20">

                {/* Main HUD Container */}
                <div className="relative aspect-video rounded-3xl overflow-hidden border-2 border-gray-800 shadow-[0_0_50px_rgba(0,0,0,0.5)] bg-gray-950">

                    {/* Loading State */}
                    {loading && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-950 z-20">
                            <div className="relative w-24 h-24 mb-6">
                                <div className="absolute inset-0 border-t-4 border-orange-500 rounded-full animate-spin"></div>
                                <div className="absolute inset-2 border-r-4 border-orange-500/30 rounded-full animate-spin-reverse"></div>
                                <img src="/logo2.png" className="absolute inset-0 w-full h-full object-contain p-4 opacity-50 animate-pulse" />
                            </div>
                            <p className="font-mono text-orange-500 tracking-widest text-sm animate-pulse">SYNCHRONIZING CHAKRA...</p>
                        </div>
                    )}

                    {/* Error State */}
                    {error && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-950/90 z-30 p-6 text-center backdrop-blur-md">
                            <AlertTriangle className="w-16 h-16 text-red-500 mb-4 animate-bounce" />
                            <h3 className="text-2xl font-black text-white mb-2 uppercase tracking-tight">System Global Failure</h3>
                            <p className="text-red-200 font-mono text-sm max-w-md">{error}</p>
                            <button onClick={() => window.location.reload()} className="mt-6 px-6 py-2 bg-red-600 hover:bg-red-500 text-white font-bold rounded-lg transition uppercase tracking-widest text-xs">
                                Reboot System
                            </button>
                        </div>
                    )}

                    {/* Video Layer */}
                    <video
                        ref={videoRef}
                        className="absolute inset-0 w-full h-full object-cover opacity-0 pointer-events-none transform scale-x-[-1]" // Mirrored
                        autoPlay
                        playsInline
                        muted
                    />

                    {/* Canvas Layer */}
                    <canvas
                        ref={canvasRef}
                        width={640}
                        height={480}
                        className="absolute inset-0 w-full h-full object-cover transform scale-x-[-1]" // Mirrored matching video
                    />

                    {/* Top HUD: Target Sequence */}
                    <div className="absolute top-0 left-0 right-0 p-6 bg-gradient-to-b from-black/80 to-transparent flex justify-between items-start pointer-events-none">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></span>
                                <span className="text-xs font-mono text-orange-500 uppercase tracking-[0.2em] shadow-orange-500/20 drop-shadow-[0_0_5px_rgba(249,115,22,0.5)]">Mission Objective</span>
                            </div>
                            <h1 className="text-4xl font-black text-white tracking-tighter italic drop-shadow-lg mb-4">
                                FIREBALL JUTSU
                            </h1>

                            {/* Sequence Steps */}
                            <div className="flex gap-3">
                                {targetSequence.map((sign, i) => (
                                    <div key={i} className={`
                                        relative w-14 h-14 rounded-xl border-2 flex items-center justify-center bg-black/60 backdrop-blur-sm transition-all duration-300
                                        ${i < currentStep ? "border-green-500 opacity-50" :
                                            i === currentStep ? "border-orange-500 scale-110 shadow-[0_0_20px_rgba(249,115,22,0.4)]" :
                                                "border-gray-700 opacity-30"}
                                    `}>
                                        {/* Step Number */}
                                        <div className="absolute -top-2 -left-2 w-5 h-5 rounded-full bg-black border border-gray-700 flex items-center justify-center text-[10px] font-bold text-gray-400">
                                            {i + 1}
                                        </div>

                                        {/* Sign Image */}
                                        {signImages[sign] ? (
                                            <img src={signImages[sign]} alt={sign} className={`w-8 h-8 object-contain ${i === currentStep ? "filter brightness-150 drop-shadow-[0_0_5px_rgba(249,115,22,0.8)]" : "filter grayscale"}`} />
                                        ) : (
                                            <span className="text-[10px] font-bold">{sign}</span>
                                        )}

                                        {/* Checkmark for completed */}
                                        {i < currentStep && (
                                            <div className="absolute inset-0 flex items-center justify-center bg-green-500/20 rounded-lg">
                                                <CheckCircle className="w-6 h-6 text-green-500" />
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Stats Corner */}
                        <div className="flex flex-col items-end">
                            <div className="flex items-center gap-2 bg-black/40 backdrop-blur-md px-3 py-1 rounded-full border border-white/10 mb-2">
                                <Camera className="w-3 h-3 text-gray-400" />
                                <span className="font-mono text-xs font-bold text-gray-400">{fps} FPS</span>
                            </div>
                            {landmarker && (
                                <div className="flex items-center gap-2 bg-green-900/30 backdrop-blur-md px-3 py-1 rounded-full border border-green-500/30">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                                    <span className="font-mono text-xs font-bold text-green-400">VISION ACTIVE</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Bottom HUD: Current Status */}
                    <div className="absolute bottom-8 left-0 right-0 flex justify-center items-end pointer-events-none">

                        {/* Central Status Pill */}
                        <div className={`
                            px-8 py-4 rounded-2xl border-2 backdrop-blur-xl shadow-2xl transition-all duration-300 transform
                            ${prediction === "Idle" || prediction === "No Hand"
                                ? "bg-gray-900/80 border-gray-700 translate-y-2 opacity-80"
                                : "bg-orange-600/20 border-orange-500 scale-110 shadow-[0_0_40px_rgba(249,115,22,0.3)]"}
                        `}>
                            <div className="text-center">
                                <p className="text-[10px] font-mono uppercase tracking-[0.3em] text-gray-400 mb-1">
                                    Current Seal
                                </p>
                                <div className="flex items-center justify-center gap-4">
                                    {/* Show Image of current prediction if available */}
                                    {signImages[prediction] && (
                                        <img src={signImages[prediction]} className="w-10 h-10 object-contain animate-bounce-short" />
                                    )}
                                    <h2 className={`text-4xl font-black italic tracking-tighter uppercase ${prediction === "Idle" || prediction === "No Hand" ? "text-gray-500" : "text-white drop-shadow-[0_0_10px_rgba(249,115,22,0.8)]"
                                        }`}>
                                        {prediction}
                                    </h2>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Instructions / Footer */}
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4 opacity-60 hover:opacity-100 transition-opacity">
                    <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800 flex items-start gap-4">
                        <div className="p-2 bg-gray-800 rounded-lg">
                            <AlertTriangle className="w-5 h-5 text-yellow-500" />
                        </div>
                        <div>
                            <h4 className="font-bold text-gray-300 text-sm uppercase mb-1">Dojo Rules</h4>
                            <p className="text-xs text-gray-500 leading-relaxed">
                                You must use <strong className="text-white">BOTH HANDS</strong> clearly visible to the camera.
                                The ancient techniques require precise chakra control.
                            </p>
                        </div>
                    </div>
                    <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800 flex items-center justify-between">
                        <div>
                            <h4 className="font-bold text-gray-300 text-sm uppercase mb-1">Progress</h4>
                            <p className="text-xs text-gray-500">Master the 6 signs to cast the jutsu.</p>
                        </div>
                        <div className="text-3xl font-black text-gray-700">
                            <span className="text-white">{currentStep}</span>/6
                        </div>
                    </div>
                </div>

                {/* Privacy Badge */}
                <div className="mt-8 flex justify-center">
                    <div className="flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/20 rounded-full">
                        <div className="relative w-2 h-2">
                            <div className="absolute inset-0 bg-green-500 rounded-full animate-ping"></div>
                            <div className="relative w-2 h-2 bg-green-500 rounded-full"></div>
                        </div>
                        <span className="text-[10px] font-mono text-green-400 uppercase tracking-widest">
                            Secure Client-Side AI • No Video Uploaded
                        </span>
                    </div>
                </div>

            </div >
        </div >
    );
}

// Drawing Utils
function drawLandmarks(ctx: CanvasRenderingContext2D, landmarks: any[], style: any) {
    if (!landmarks) return;
    ctx.fillStyle = style.color;
    for (const lm of landmarks) {
        ctx.beginPath();
        const x = lm.x * ctx.canvas.width;
        const y = lm.y * ctx.canvas.height;
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
    }
}

function drawConnectors(ctx: CanvasRenderingContext2D, landmarks: any[], connections: any[], style: any) {
    if (!landmarks) return;
    ctx.strokeStyle = style.color;
    ctx.lineWidth = style.lineWidth;

    // MediaPipe connectors are index pairs [start, end]
    for (const conn of connections) {
        const p1 = landmarks[conn.start];
        const p2 = landmarks[conn.end];
        if (p1 && p2) {
            ctx.beginPath();
            ctx.moveTo(p1.x * ctx.canvas.width, p1.y * ctx.canvas.height);
            ctx.lineTo(p2.x * ctx.canvas.width, p2.y * ctx.canvas.height);
            ctx.stroke();
        }
    }
}
