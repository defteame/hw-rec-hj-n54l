import sharp from 'sharp';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const renderDir = join(__dirname, 'build/renders/full-components');

const files = [
    { input: 'svg/assembly.svg', output: 'main_ALL_COMPONENTS.png' },
    { input: 'svg/complete.svg', output: 'main_ALL_complete.png' }
];

for (const file of files) {
    const inputPath = join(renderDir, file.input);
    const outputPath = join(renderDir, file.output);

    console.log(`Converting ${file.input}...`);

    try {
        await sharp(inputPath, { density: 200, limitInputPixels: false })
            .resize(3000, null, { fit: 'inside' })
            .png()
            .toFile(outputPath);
        console.log(`  -> ${file.output} created`);
    } catch (err) {
        console.error(`  Error: ${err.message}`);
    }
}

console.log('\nDone!');
