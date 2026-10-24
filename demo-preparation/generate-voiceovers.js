// Generate CodeMemory demo voiceovers using ElevenLabs SDK
const { ElevenLabsClient } = require('@elevenlabs/elevenlabs-js');
const fs = require('fs');
const path = require('path');

const API_KEY = "sk_f416c36c387a0e467fae08e29bbb031e803d56932c2a3821";
const VOICE_ID = "CwhRBWXzGAHq8TQ4Fs17";
const MODEL_ID = "eleven_v4";
const OUTPUT_DIR = "C:\\Users\\Jay Janardan Patil\\Desktop\\CodeMemory\\demo-preparation\\recordings";

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const client = new ElevenLabsClient({ apiKey: API_KEY });

const segments = [
    { filename: "hero-audio.mp3", text: "CodeMemory turns every coding submission into searchable knowledge. Your coding history, remembered." },
    { filename: "memory-audio.mp3", text: "Every failed attempt is preserved alongside the accepted one. A time-limit exceeded on attempt one becomes part of the story of attempt three." },
    { filename: "evolution-audio.mp3", text: "Each problem is a sequence, not just the final answer. See how your thinking evolved from the first brute-force approach to the optimized solution." },
    { filename: "analytics-audio.mp3", text: "Derived from your own submissions, the analytics show real progress — difficulty distribution, language usage, and solving patterns over time." },
    { filename: "knowledge-audio.mp3", text: "Every problem links to the topics it uses, the approaches you tried, and the mistakes you made. Select a node to follow the connection back to practice history." },
    { filename: "revision-audio.mp3", text: "The revision queue ranks what to revisit using deterministic priority scores — weighing difficulty, failure history, recency, and topic weakness." },
    { filename: "cta-audio.mp3", text: "Import the submissions you already have. CodeMemory indexes them, connects them, and remembers the parts worth revisiting." },
];

async function generateAudio(segment) {
    const outputPath = path.join(OUTPUT_DIR, segment.filename);
    console.log(`Generating: ${segment.filename}`);

    try {
        const audio = await client.textToSpeech.convert(VOICE_ID, {
            modelId: MODEL_ID,
            text: segment.text,
        });

        const chunks = [];
        for await (const chunk of audio) {
            chunks.push(Buffer.from(chunk));
        }
        const buffer = Buffer.concat(chunks);
        fs.writeFileSync(outputPath, buffer);
        console.log(`  -> Saved: ${outputPath} (${buffer.length} bytes)`);
        return { filename: segment.filename, success: true, size: buffer.length, error: null };
    } catch (err) {
        console.error(`  -> ERROR: ${err.message}`);
        return { filename: segment.filename, success: false, size: 0, error: err.message };
    }
}

(async () => {
    console.log(`Generating ${segments.length} voiceover files to: ${OUTPUT_DIR}\n`);

    const results = [];
    for (const segment of segments) {
        const result = await generateAudio(segment);
        results.push(result);
    }

    console.log("\n=== VERIFICATION ===");
    let allOk = true;
    for (const r of results) {
        if (r.success && r.size > 0) {
            console.log(`[OK] ${r.filename} - ${r.size} bytes`);
        } else {
            console.log(`[FAIL] ${r.filename} - ${r.error || 'empty file'}`);
            allOk = false;
        }
    }

    if (allOk) {
        console.log("\nAll audio files generated successfully!");
    } else {
        console.log("\nSome files failed to generate.");
        process.exit(1);
    }
})();
