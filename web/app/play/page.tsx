"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as ort from "onnxruntime-web";
import { ArrowLeft, Camera, RefreshCw, AlertTriangle, Bug, X, UploadCloud, CheckCircle } from "lucide-react";
import Link from "next/link";
import { postprocess, DetectedObject, LABELS } from "@/utils/yolo";
import { supabase } from "@/utils/supabase";

// Configure ONNX Runtime to use WASM backend
ort.env.wasm.numThreads = 1;

export default function PlayPage() {
    const [model, setModel] = useState<ort.InferenceSession | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [detections, setDetections] = useState<DetectedObject[]>([]);
    const [inferenceTime, setInferenceTime] = useState(0);

    // Reporting State
    const [showConsentModal, setShowConsentModal] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState<"idle" | "success" | "error">("idle");

    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const requestRef = useRef<number>(0);

    // FPS Smoothing Refs
    const lastFpsUpdate = useRef<number>(0);
    const framesCount = useRef<number>(0);
    const accumulatedTime = useRef<number>(0);

    // Initialize Modal
    useEffect(() => {
        async function loadModel() {
            try {
                setLoading(true);
                // Path to the ONNX model in the public folder
                const modelPath = "/model/model.onnx";

                // Create session
                const session = await ort.InferenceSession.create(modelPath, {
                    executionProviders: ["webgl", "wasm"], // Try WebGL first, fallback to Wasm
                    graphOptimizationLevel: "all"
                });

                console.log("Model loaded successfully");
                setModel(session);
                setLoading(false);
            } catch (e: any) {
                // ... error handling
                console.error("Failed to load model:", e);
                setError("Failed to load AI model. Please check your connection.");
                setLoading(false);
            }
        }
        loadModel();
    }, []);

    // Initialize Webcam
    useEffect(() => {
        if (!videoRef.current) return;

        async function setupCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: "user",
                        width: { ideal: 640 },
                        height: { ideal: 640 }
                    },
                    audio: false
                });

                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
            } catch (err) {
                console.error("Error accessing webcam:", err);
                setError("Could not access webcam. Please allow permission.");
            }
        }
        setupCamera();

        return () => {
            // eslint-disable-next-line react-hooks/exhaustive-deps
            const stream = videoRef.current?.srcObject as MediaStream;
            stream?.getTracks().forEach(track => track.stop());
        };
    }, []);

    // Inference Loop
    const runInference = useCallback(async () => {
        if (!model || !videoRef.current || !canvasRef.current) return;

        const video = videoRef.current;
        if (video.readyState !== 4) return;

        const start = performance.now();

        // 1. Prepare Input
        const w = 640;
        const h = 640;

        const ctx = canvasRef.current.getContext("2d");
        if (!ctx) return;

        // Draw video (mirrored for simpler user experience, but be careful with hand signs if they are asymmetric)
        // We will keep it standard for now to match training data
        ctx.drawImage(video, 0, 0, w, h);

        const imageData = ctx.getImageData(0, 0, w, h);
        const data = imageData.data;

        const float32Data = new Float32Array(3 * w * h);
        for (let i = 0; i < w * h; i++) {
            float32Data[i] = data[i * 4] / 255.0;
            float32Data[w * h + i] = data[i * 4 + 1] / 255.0;
            float32Data[2 * w * h + i] = data[i * 4 + 2] / 255.0;
        }

        const inputTensor = new ort.Tensor("float32", float32Data, [1, 3, w, h]);

        // 2. Run Model
        try {
            const feeds = { images: inputTensor };
            const results = await model.run(feeds);
            const output = results[model.outputNames[0]].data as Float32Array;

            // 3. Post Process
            const boxes = postprocess(output, w, h, 0.50, 0.45);
            setDetections(boxes);

            // 4. Draw Minimal UI (Black Ink / Red Seal)
            ctx.drawImage(video, 0, 0, w, h); // Redraw clear frame

            // Add a subtle paper grain or grayscale filter effect? 
            // For now, let's keep the video clear but make the overlay bold.

            boxes.forEach(det => {
                const [x1, y1, x2, y2] = det.box;

                // Red 'Seal' Box style
                ctx.strokeStyle = "#dc2626"; // Red-600
                ctx.lineWidth = 4;

                // Draw Box
                ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

                // Label Tag (White text on Red background)
                const text = `${det.label} ${Math.round(det.score * 100)}%`;
                ctx.font = "bold 16px sans-serif";
                const textWidth = ctx.measureText(text).width + 20;

                ctx.fillStyle = "#dc2626";
                ctx.fillRect(x1, y1 - 30, textWidth, 30);

                ctx.fillStyle = "#ffffff";
                ctx.fillText(text.toUpperCase(), x1 + 10, y1 - 8);
            });

        } catch (e) {
            console.error("Inference error:", e);
        }

        const end = performance.now();
        const duration = end - start;

        // Smoothing: update FPS only every 500ms
        accumulatedTime.current += duration;
        framesCount.current++;

        const now = performance.now();
        if (now - lastFpsUpdate.current > 500) {
            setInferenceTime(accumulatedTime.current / framesCount.current);
            accumulatedTime.current = 0;
            framesCount.current = 0;
            lastFpsUpdate.current = now;
        }

        requestRef.current = requestAnimationFrame(runInference);
    }, [model]);

    useEffect(() => {
        if (model && !requestRef.current) {
            requestRef.current = requestAnimationFrame(runInference);
        }
        return () => cancelAnimationFrame(requestRef.current);
    }, [model, runInference]);

    // Handle Upload
    const handleReportIssue = async () => {
        if (!canvasRef.current) return;
        setIsUploading(true);

        try {
            // 1. Convert canvas to blob
            const blob = await new Promise<Blob | null>(resolve =>
                canvasRef.current!.toBlob(resolve, 'image/jpeg', 0.8)
            );

            if (!blob) throw new Error("Failed to capture image");

            // 2. Generate filename
            const filename = `report_${Date.now()}_${Math.random().toString(36).substring(7)}.jpg`;

            // 3. Upload to Supabase
            const { error: uploadError } = await supabase.storage
                .from('training_data')
                .upload(filename, blob);

            if (uploadError) throw uploadError;

            setUploadStatus("success");
            setTimeout(() => {
                setUploadStatus("idle");
                setShowConsentModal(false);
            }, 2000);

        } catch (error: any) {
            console.error("Upload failed", error);
            setUploadStatus("error");
            if (error.message?.includes("bucket")) {
                alert("Error: 'training_data' bucket missing in Supabase. Please create it.");
            }
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="min-h-screen bg-ninja-bg text-ninja-text p-4 font-sans selection:bg-ninja-accent selection:text-white flex flex-col items-center">
            {/* Header */}
            <div className="w-full max-w-[640px] flex items-center justify-between mb-8 pt-4 z-10">
                <Link href="/" className="flex items-center gap-2 text-ninja-dim hover:text-white transition-colors font-bold uppercase tracking-wider text-sm">
                    <ArrowLeft className="w-4 h-4" /> <span className="hidden sm:inline">Return to Hub</span>
                </Link>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-xs font-bold font-mono text-ninja-accent bg-ninja-card border border-ninja-border px-4 py-2 rounded-full shadow-lg">
                        <Camera className="w-4 h-4" />
                        <span>FPS: {Math.round(1000 / (inferenceTime || 1))} <span className="text-ninja-dim">({inferenceTime.toFixed(1)}ms)</span></span>
                    </div>
                </div>
            </div>

            {/* Main Viewport */}
            <div className="relative w-full max-w-[640px] aspect-square bg-ninja-black rounded-2xl overflow-hidden border-4 border-ninja-border shadow-[0_0_40px_rgba(0,0,0,0.5)] group">
                {/* Status Overlays */}
                {loading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-ninja-bg/90 z-20 backdrop-blur-sm">
                        <RefreshCw className="w-12 h-12 animate-spin text-ninja-accent mb-6" />
                        <p className="text-ninja-accent font-black animate-pulse tracking-[0.2em] text-sm">INITIALIZING NEURAL NET</p>
                    </div>
                )}

                {/* Report Button */}
                <button
                    onClick={() => setShowConsentModal(true)}
                    className="absolute top-4 right-4 z-30 flex items-center gap-2 bg-ninja-card/80 backdrop-blur-md text-white border border-ninja-border px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider hover:bg-ninja-accent hover:border-ninja-accent transition-all shadow-lg opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 duration-300"
                >
                    <Bug className="w-3 h-3" />
                    Unknown Sign?
                </button>

                {error && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-ninja-bg z-20 p-8 text-center">
                        <AlertTriangle className="w-16 h-16 text-ninja-error mb-6 opacity-80" />
                        <p className="text-ninja-error font-black text-2xl mb-2 tracking-tight">SYSTEM FAILURE</p>
                        <p className="text-ninja-dim mb-8 max-w-xs leading-relaxed">{error}</p>
                        <button
                            onClick={() => window.location.reload()}
                            className="bg-ninja-card hover:bg-ninja-hover text-white px-8 py-3 rounded-lg font-bold uppercase tracking-wider text-xs transition-all border border-ninja-border flex items-center gap-2"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Reboot System
                        </button>
                    </div>
                )}

                {/* Video/Canvas */}
                <video
                    ref={videoRef}
                    className="hidden"
                    autoPlay
                    playsInline
                    muted
                    onLoadedMetadata={() => {
                        console.log("Video metadata loaded");
                        if (videoRef.current) videoRef.current.play();
                    }}
                />

                <canvas
                    ref={canvasRef}
                    width={640}
                    height={640}
                    className="w-full h-full object-cover bg-black"
                />

                {/* HUD Corners */}
                <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-ninja-accent opacity-50 pointer-events-none"></div>
                <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-ninja-accent opacity-50 pointer-events-none"></div>
                <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-ninja-accent opacity-50 pointer-events-none"></div>
                <div className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-ninja-accent opacity-50 pointer-events-none"></div>

                {/* Current Detection Banner */}
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 w-full px-4 text-center pointer-events-none">
                    {detections.length > 0 ? (
                        <div className="inline-block bg-ninja-accent text-white px-8 py-2 rounded-lg shadow-[0_0_20px_rgba(255,120,50,0.4)] backdrop-blur-md">
                            <span className="font-black text-3xl tracking-widest uppercase drop-shadow-md">{detections[0].label}</span>
                        </div>
                    ) : null}
                </div>
            </div>

            {/* Active Class Grid */}
            <div className="mt-8 w-full max-w-[640px] grid grid-cols-4 sm:grid-cols-6 gap-2">
                {LABELS.map(label => {
                    const isActive = detections.some(d => d.label === label);
                    return (
                        <div key={label}
                            className={`
                                text-center py-3 text-[10px] sm:text-xs font-black uppercase tracking-wider transition-all duration-200 rounded-md border
                                ${isActive
                                    ? 'bg-ninja-accent text-white border-ninja-accent shadow-[0_0_15px_rgba(255,120,50,0.3)] scale-105 z-10'
                                    : 'bg-ninja-card text-ninja-dim border-ninja-border hover:border-ninja-hover'
                                }
                            `}
                        >
                            {label}
                        </div>
                    )
                })}
            </div>

            {/* Consent Modal */}
            {showConsentModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                    <div className="bg-ninja-card border border-ninja-border w-full max-w-sm p-8 rounded-2xl shadow-2xl relative">
                        <button
                            onClick={() => setShowConsentModal(false)}
                            className="absolute top-4 right-4 text-ninja-dim hover:text-white transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        <div className="mb-8 text-center">
                            <div className="w-16 h-16 bg-ninja-bg rounded-full flex items-center justify-center mb-6 mx-auto border border-ninja-border">
                                <UploadCloud className="w-8 h-8 text-ninja-accent" />
                            </div>
                            <h3 className="text-xl font-black text-white mb-2 uppercase tracking-wide">Contribute Data</h3>
                            <p className="text-ninja-dim text-sm leading-relaxed">
                                Helps the AI learn new hands. Uploads anonymous image for training.
                            </p>
                        </div>

                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowConsentModal(false)}
                                className="flex-1 py-3 bg-ninja-bg hover:bg-ninja-hover text-ninja-dim hover:text-white font-bold uppercase text-xs tracking-wider rounded-lg transition-colors border border-ninja-border"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleReportIssue}
                                disabled={isUploading || uploadStatus === 'success'}
                                className={`
                                    flex-1 py-3 font-bold flex items-center justify-center gap-2 transition-all uppercase text-xs tracking-wider text-white rounded-lg
                                    ${uploadStatus === 'success' ? 'bg-ninja-success border border-ninja-success' : 'bg-ninja-accent hover:bg-ninja-accent-glow shadow-[0_0_15px_rgba(255,120,50,0.3)]'}
                                    ${isUploading ? 'opacity-80 cursor-wait' : ''}
                                `}
                            >
                                {isUploading ? (
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                ) : uploadStatus === 'success' ? (
                                    <>
                                        <CheckCircle className="w-4 h-4" /> Sent
                                    </>
                                ) : (
                                    "Upload"
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
