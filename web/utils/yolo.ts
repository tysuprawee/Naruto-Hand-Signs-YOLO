
/**
 * YOLOv8 Post-processing Utils
 */

export interface DetectedObject {
    label: string;
    score: number;
    box: [number, number, number, number]; // [x1, y1, x2, y2]
}

export const LABELS = [
    'tiger', 'boar', 'snake', 'ram', 'bird', 'dragon',
    'dog', 'rat', 'horse', 'monkey', 'ox', 'hare'
];

/**
 * Handle YOLOv8 Output
 * Output shape is [1, 4 + num_classes, 8400]
 * We need to transpose it effectively to iterate over 8400 anchors.
 */
export function postprocess(
    output: Float32Array,
    imgWidth: number,
    imgHeight: number,
    confThreshold: number = 0.5,
    iouThreshold: number = 0.45
): DetectedObject[] {
    const numAnchors = 8400;
    const numClasses = 12; // 0-11
    const numElements = 4 + numClasses; // 16

    const boxes: number[][] = [];
    const scores: number[] = [];
    const classIndices: number[] = [];

    // Loop over all 8400 anchors
    for (let i = 0; i < numAnchors; i++) {
        // Find the maximum score among the classes for this anchor
        let maxScore = -Infinity;
        let maxClassIndex = -1;

        // The output is flattened. 
        // Usually output[channel * numAnchors + anchorIndex] if channel-first (1, 16, 8400)
        // channel 0 = cx, 1 = cy, 2 = w, 3 = h
        // channel 4..15 = classes

        for (let c = 0; c < numClasses; c++) {
            const score = output[(4 + c) * numAnchors + i];
            if (score > maxScore) {
                maxScore = score;
                maxClassIndex = c;
            }
        }

        if (maxScore > confThreshold) {
            const cx = output[0 * numAnchors + i];
            const cy = output[1 * numAnchors + i];
            const w = output[2 * numAnchors + i];
            const h = output[3 * numAnchors + i];

            // Convert center-wh to top-left-wh
            const x = (cx - w / 2) * imgWidth;
            const y = (cy - h / 2) * imgHeight;
            const width = w * imgWidth;
            const height = h * imgHeight;

            boxes.push([x, y, width, height]);
            scores.push(maxScore);
            classIndices.push(maxClassIndex);
        }
    }

    // NMS
    const indices = nms(boxes, scores, iouThreshold);

    const results: DetectedObject[] = [];
    for (const i of indices) {
        const box = boxes[i];
        results.push({
            label: LABELS[classIndices[i]],
            score: scores[i],
            box: [box[0], box[1], box[0] + box[2], box[1] + box[3]] // [x1, y1, x2, y2]
        });
    }

    return results;
}

/**
 * Simple Non-Maximum Suppression
 */
function nms(boxes: number[][], scores: number[], iouThreshold: number): number[] {
    const indices = Array.from(Array(scores.length).keys());

    // Sort by score descending
    indices.sort((a, b) => scores[b] - scores[a]);

    const keep: number[] = [];

    while (indices.length > 0) {
        const current = indices.shift()!;
        keep.push(current);

        const remaining: number[] = [];

        for (const i of indices) {
            const iou = calculateIoU(boxes[current], boxes[i]);
            if (iou <= iouThreshold) {
                remaining.push(i);
            }
        }

        // Replace indices with filtered list
        indices.splice(0, indices.length, ...remaining);
    }

    return keep;
}

function calculateIoU(boxA: number[], boxB: number[]): number {
    const x1 = Math.max(boxA[0], boxB[0]);
    const y1 = Math.max(boxA[1], boxB[1]);
    const x2 = Math.min(boxA[0] + boxA[2], boxB[0] + boxB[2]);
    const y2 = Math.min(boxA[1] + boxA[3], boxB[1] + boxB[3]);

    const intersectionWidth = Math.max(0, x2 - x1);
    const intersectionHeight = Math.max(0, y2 - y1);
    const intersectionArea = intersectionWidth * intersectionHeight;

    const boxAArea = boxA[2] * boxA[3];
    const boxBArea = boxB[2] * boxB[3];

    return intersectionArea / (boxAArea + boxBArea - intersectionArea);
}
