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

    // Initialize Modal
    useEffect(() => {
        async function loadModel() {
            try {
                setLoading(true);
                // Path to the ONNX model in the public folder
                const modelPath = "/model/model.onnx";

                // Create session
                const session = await ort.InferenceSession.create(modelPath, {
                    executionProviders: ["wasm"], // 'webgl' is faster but can be buggy on some devices
                    graphOptimizationLevel: "all"
                });

                console.log("Model loaded successfully");
                setModel(session);
                setLoading(false);
            } catch (e: any) {
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
        setInferenceTime(end - start);

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
        <div className="min-h-screen bg-[#fafafa] text-zinc-900 p-4 font-sans selection:bg-black selection:text-white">
            {/* Header */}
            <div className="flex items-center justify-between mb-8 max-w-[640px] mx-auto pt-4">
                <Link href="/" className="flex items-center gap-2 text-zinc-500 hover:text-black transition-colors font-medium">
                    <ArrowLeft className="w-5 h-5" /> <span className="hidden sm:inline">Back to Dojo</span>
                </Link>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-sm font-bold text-zinc-400 bg-white border border-zinc-200 px-3 py-1 rounded-full shadow-sm">
                        <Camera className="w-4 h-4" />
                        <span>{inferenceTime.toFixed(1)}ms</span>
                    </div>
                </div>
            </div>

            {/* Main Viewport */}
            <div className="relative mx-auto max-w-[640px] aspect-square bg-white rounded-none overflow-hidden border-[8px] border-zinc-900 shadow-2xl">
                {/* Status Overlays */}
                {loading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/90 z-20 backdrop-blur-sm">
                        <RefreshCw className="w-10 h-10 animate-spin text-black mb-4" />
                        <p className="text-zinc-500 font-bold animate-pulse tracking-widest">INITIALIZING...</p>
                    </div>
                )}

                {/* Report Button */}
                <button
                    onClick={() => setShowConsentModal(true)}
                    className="absolute top-4 right-4 z-30 flex items-center gap-2 bg-white text-black border-2 border-black px-4 py-2 text-xs font-black uppercase tracking-wider hover:bg-black hover:text-white transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]"
                >
                    <Bug className="w-3 h-3" />
                    Contribute
                </button>

                {error && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-white z-20">
                        <AlertTriangle className="w-12 h-12 text-red-600 mb-4" />
                        <p className="text-red-600 font-black text-xl mb-2">SYSTEM ERROR</p>
                        <p className="text-zinc-500 text-center px-8">{error}</p>
                    </div>
                )}

                {/* Video/Canvas */}
                <video ref={videoRef} className="hidden" autoPlay playsInline muted />
                <canvas ref={canvasRef} width={640} height={640} className="w-full h-full object-cover grayscale-[0.2] contrast-125" />

                {/* Current Detection Banner */}
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 w-full px-4 text-center">
                    {detections.length > 0 ? (
                        <div className="inline-block bg-white text-black border-2 border-black px-8 py-3 shadow-[4px_4px_0px_0px_rgba(0,0,0,0.2)]">
                            <span className="font-black text-2xl tracking-widest uppercase">{detections[0].label}</span>
                        </div>
                    ) : null}
                </div>
            </div>

            {/* Active Class Grid */}
            <div className="mt-8 max-w-[640px] mx-auto grid grid-cols-4 sm:grid-cols-6 gap-3">
                {LABELS.map(label => {
                    const isActive = detections.some(d => d.label === label);
                    return (
                        <div key={label}
                            className={`
                                text-center py-3 text-[10px] sm:text-xs font-black uppercase tracking-wider transition-all duration-200 border-2
                                ${isActive
                                    ? 'bg-black text-white border-black scale-105 shadow-md'
                                    : 'bg-white text-zinc-300 border-zinc-100'
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
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm p-4">
                    <div className="bg-white border-2 border-black max-w-sm w-full p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,0.2)] relative">
                        <button
                            onClick={() => setShowConsentModal(false)}
                            className="absolute top-4 right-4 text-zinc-400 hover:text-black"
                        >
                            <X className="w-6 h-6" />
                        </button>

                        <div className="mb-8">
                            <div className="w-12 h-12 bg-zinc-100 flex items-center justify-center mb-6 border border-zinc-200">
                                <UploadCloud className="w-6 h-6 text-black" />
                            </div>
                            <h3 className="text-2xl font-black text-black mb-3 uppercase tracking-tight">Contribute Data</h3>
                            <p className="text-zinc-600 text-sm leading-relaxed">
                                By clicking "Upload", you agree to donate the current image (including your face/hands) to our open-source dataset.
                            </p>
                        </div>

                        <div className="flex gap-4">
                            <button
                                onClick={() => setShowConsentModal(false)}
                                className="flex-1 py-3 bg-zinc-100 hover:bg-zinc-200 text-black font-bold uppercase text-xs tracking-wider transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleReportIssue}
                                disabled={isUploading || uploadStatus === 'success'}
                                className={`
                                    flex-1 py-3 font-bold flex items-center justify-center gap-2 transition-all uppercase text-xs tracking-wider text-white
                                    ${uploadStatus === 'success' ? 'bg-green-600' : 'bg-black hover:bg-zinc-800'}
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
