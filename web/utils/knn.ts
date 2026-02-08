export class KNNClassifier {
    private data: { features: number[], label: string }[]; // Optimized storage
    private k: number;
    private labels: string[];

    constructor(rawData: any[], k: number = 3) {
        this.k = k;
        this.data = [];
        this.labels = [];

        if (rawData.length > 0) {
            // Determine feature keys once (assume consistent schema)
            // Filter out 'label' and ensure we only get numeric columns essentially
            const sample = rawData[0];
            const featureKeys = Object.keys(sample).filter(key => key !== 'label');

            // Pre-process all rows
            rawData.forEach(row => {
                const features = featureKeys.map(key => parseFloat(row[key]));
                this.data.push({ features, label: row.label });
            });

            // unique labels
            this.labels = Array.from(new Set(this.data.map(d => d.label))).sort();
        }
    }

    predict(features: number[]): string {
        if (!features || features.length === 0 || this.data.length === 0) return "Unknown";

        // Calculate distances with optimized pre-parsed numbers
        // We avoid creating new objects inside the loop if possible, 
        // but modern JS engines embrace object creation well.
        // Let's stick to simple map/sort first, but use Pre-Parsed numbers.

        /* 
           PERFORMANCE NOTE:
           Even with pre-parsing, mapping 10k objects every frame is costly.
           Ideally, we'd use a flat Float32Array for features and doing loop unrolling,
           but let's try this standard optimization first.
        */

        const distances = new Array(this.data.length);
        for (let i = 0; i < this.data.length; i++) {
            distances[i] = {
                label: this.data[i].label,
                dist: this.euclideanDistance(features, this.data[i].features)
            };
        }

        // Sort by distance (ASC)
        distances.sort((a, b) => a.dist - b.dist);

        // Get top K
        const kNearest = distances.slice(0, this.k);
        const minDist = kNearest[0].dist;

        // Threshold check (User requested change?)
        // Python script used 1.8. User said "when no hand it's 30 just no hand is 10"
        // I suspect they mean "Just ONE hand is 10 [fps]". They might verify logic later.
        if (minDist > 1.8) {
            return "Idle";
        }

        // Majority vote
        const counts: { [key: string]: number } = {};
        for (const n of kNearest) {
            counts[n.label] = (counts[n.label] || 0) + 1;
        }

        let maxCount = 0;
        let prediction = "Unknown";

        for (const label in counts) {
            if (counts[label] > maxCount) {
                maxCount = counts[label];
                prediction = label;
            }
        }

        return prediction;
    }

    private euclideanDistance(a: number[], b: number[]): number {
        let sum = 0;
        const len = Math.min(a.length, b.length);
        for (let i = 0; i < len; i++) {
            const diff = a[i] - b[i];
            sum += diff * diff;
        }
        return Math.sqrt(sum);
    }
}

export function normalizeHand(landmarks: any[]): number[] {
    if (!landmarks || landmarks.length === 0) return [];

    const wrist = landmarks[0];
    const middleBase = landmarks[9];

    let dist = Math.sqrt(
        (wrist.x - middleBase.x) ** 2 +
        (wrist.y - middleBase.y) ** 2 +
        (wrist.z - middleBase.z) ** 2
    );

    if (dist < 0.0001) dist = 1.0;

    const coords: number[] = [];
    for (const lm of landmarks) {
        const normX = (lm.x - wrist.x) / dist;
        const normY = (lm.y - wrist.y) / dist;
        const normZ = (lm.z - wrist.z) / dist;
        coords.push(normX, normY, normZ);
    }

    return coords;
}
