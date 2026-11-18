import {execFileSync} from 'node:child_process';
import {copyFile, mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import ffmpeg from 'ffmpeg-static';

const here = path.dirname(fileURLToPath(import.meta.url));
const destination = path.resolve(here, '..', '..', 'docs', 'videos');
const videos = JSON.parse(await readFile(path.join(here, 'public', 'timeline.json'), 'utf8'));
const stillsOnly = process.argv.includes('--stills');
const selected = process.argv.find((argument) => argument.startsWith('--kind='))?.split('=')[1];

const esc = (value) => String(value).replace(/[&<>"]/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
}[character]));
const seconds = (frames, fps) => (frames / fps).toFixed(4);
function clock(frames, fps) {
  const centiseconds = Math.round(frames * 100 / fps);
  return `${Math.floor(centiseconds / 360000)}:` +
    `${String(Math.floor(centiseconds / 6000) % 60).padStart(2, '0')}:` +
    `${String(Math.floor(centiseconds / 100) % 60).padStart(2, '0')}.` +
    String(centiseconds % 100).padStart(2, '0');
}
function subtitles(video) {
  const header = `[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,31,&H00EDF3F5,&H00EDF3F5,&H00261B10,&H00261B10,-1,0,0,0,100,100,0,0,1,1,0,2,160,160,22,1
Style: Status,Arial,23,&H0078AEE4,&H0078AEE4,&H00261B10,&H00261B10,0,0,0,0,100,100,0,0,1,1,0,9,160,160,21,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
`;
  const rows = video.cues.map((cue) =>
    `Dialogue: 0,${clock(cue.from, video.fps)},${clock(cue.to + 1, video.fps)},Caption,,0,0,0,,${cue.lines.join('\\N')}`);
  for (const scene of video.scenes.filter((item) => !item.card)) {
    const text = scene.playbackRate > 1.05
      ? `Waktu tunggu dipercepat ${scene.playbackRate.toFixed(1)}x`
      : 'Capture asli | Data sintetis | Tanpa suara';
    rows.push(
      `Dialogue: 0,${clock(scene.from, video.fps)},${clock(scene.from + scene.durationInFrames, video.fps)},Status,,0,0,0,,${text}`,
    );
  }
  return header + rows.join('\n') + '\n';
}
async function cards(video, output) {
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1920, height: 1080}});
    await page.route('**/*', (route) => route.abort('blockedbyclient'));
    const style = `<style>
      *{box-sizing:border-box}body{margin:0;width:1920px;height:1080px;font-family:Arial,sans-serif;color:#f5f3ed;background:transparent}
      .bar{position:absolute;inset:0 0 auto;height:74px;background:#101b26;padding:18px 160px;font-size:31px;font-weight:700}
      .bottom{position:absolute;inset:auto 0 0;height:106px;background:#101b26}
      .card{background:#101b26;height:1080px;padding:170px 150px}
      .eyebrow{font-size:24px;letter-spacing:4px;color:#e4ae78;margin-bottom:34px}
      h1{font-size:88px;line-height:1.05;margin:0 0 24px;max-width:1550px}
      p{font-size:35px;color:#b7c5d0;margin:0 0 60px}
      .chain{display:flex;align-items:center;gap:20px}
      .node{padding:22px 26px;background:#172635;border:1px solid #344555;border-radius:12px;font-size:27px}
      .arrow{color:#e4ae78;font-size:35px}.note{font-size:27px;margin-top:64px}
    </style>`;
    await page.setContent(style + `<div class="bar">${esc(video.title)}</div><div class="bottom"></div>`);
    await page.screenshot({path: path.join(output, 'header.png'), omitBackground: true});
    for (const outro of [false, true]) {
      const chain = video.chain.map((name, index) =>
        `${index ? '<span class="arrow">&rarr;</span>' : ''}<span class="node">${esc(name)}</span>`,
      ).join('');
      await page.setContent(style + `<div class="card">
        <div class="eyebrow">REKAMAN UI ASLI / MCP01</div>
        <h1>${esc(outro ? 'Coba, lalu periksa sumbernya.' : video.title)}</h1>
        <p>${esc(outro ? 'Panduan dan kode tersedia lewat README repository.' : video.subtitle)}</p>
        <div class="chain">${chain}</div>
        <p class="note">${esc(outro
          ? 'Satu contoh maintenance live. Bukan uji full50, Fabric, ontology, atau Work IQ.'
          : 'Pertanyaan yang sama: Show work orders for equipment TRK001.')}</p>
      </div>`);
      const overflow = await page.locator('.card h1,.card p,.chain').evaluateAll((nodes) =>
        nodes.some((node) => {
          const box = node.getBoundingClientRect();
          return box.left < 0 || box.right > 1920 || box.bottom > 960;
        }));
      if (overflow) throw new Error('A title-card element exceeds its safe area.');
      await page.screenshot({path: path.join(output, `${outro ? 'outro' : 'intro'}.png`)});
    }
  } finally {
    await browser.close();
  }
}
function run(args, cwd) {
  execFileSync(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-y', ...args], {cwd});
}

for (const video of videos) {
  if (selected && video.kind !== selected) continue;
  const output = path.join(here, 'out', video.kind);
  await mkdir(output, {recursive: true});
  await cards(video, output);
  await writeFile(path.join(output, 'captions.ass'), subtitles(video));
  const source = path.join(here, 'public', video.source);
  const base = 'scale=1600:900,pad=1920:1080:160:74:color=0x101b26';
  if (stillsOnly) {
    const samples = [
      {scene: video.scenes[0], frame: 0},
      ...video.scenes.map((scene) => ({
        scene, frame: scene.from + Math.floor(scene.durationInFrames / 2),
      })),
      {scene: video.scenes.at(-1), frame: video.durationInFrames - 1},
    ];
    for (const [index, {scene, frame}] of samples.entries()) {
      const filename = `scene-${String(index).padStart(2, '0')}.png`;
      const timestamp = seconds(frame, video.fps);
      if (scene.card) {
        run([
          '-i', `${scene.card}.png`, '-vf',
          `setpts=PTS+${timestamp}/TB,ass=captions.ass,setpts=PTS-STARTPTS`,
          '-frames:v', '1', filename,
        ], output);
      } else {
        const sourceFrame = Math.min(scene.sourceEnd - 1, Math.round(
          scene.sourceStart + (frame - scene.from) * scene.playbackRate,
        ));
        run([
          '-ss', seconds(sourceFrame, video.fps), '-i', source, '-i', 'header.png',
          '-filter_complex',
          `[0:v]${base}[base];[base][1:v]overlay=0:0,setpts=PTS+${timestamp}/TB,ass=captions.ass,setpts=PTS-STARTPTS`,
          '-frames:v', '1', filename,
        ], output);
      }
    }
    run([
      '-framerate', '1', '-i', 'scene-%02d.png',
      '-vf', 'scale=640:360,tile=3x5', '-frames:v', '1', 'contact-sheet.png',
    ], output);
    const answerIndex = 1 + video.scenes.findIndex((scene) => scene.name === 'answer');
    await copyFile(
      path.join(output, `scene-${String(answerIndex).padStart(2, '0')}.png`),
      path.join(destination, `${video.kind}.png`),
    );
    console.log(`${video.kind}: scene holds and first/last frames sampled.`);
  } else {
    const clips = [];
    for (const [index, scene] of video.scenes.entries()) {
      const clip = `clip-${String(index).padStart(2, '0')}.mp4`;
      const encode = [
        '-an', '-r', String(video.fps), '-c:v', 'libx264', '-preset', 'fast',
        '-crf', '18', '-pix_fmt', 'yuv420p', '-threads', '2',
        '-frames:v', String(scene.durationInFrames), clip,
      ];
      if (scene.card) {
        run(['-loop', '1', '-i', `${scene.card}.png`, ...encode], output);
      } else {
        run([
          '-ss', seconds(scene.sourceStart, video.fps),
          '-t', seconds(scene.sourceEnd - scene.sourceStart, video.fps),
          '-i', source, '-i', 'header.png', '-filter_complex',
          `[0:v]setpts=(PTS-STARTPTS)/${scene.playbackRate},fps=${video.fps},` +
          `tpad=stop_mode=clone:stop_duration=5,trim=end_frame=${scene.durationInFrames},${base}[base];` +
          '[base][1:v]overlay=0:0',
          ...encode,
        ], output);
      }
      clips.push(`file '${clip}'`);
      console.log(`${video.kind}: scene ${index + 1}/${video.scenes.length} encoded.`);
    }
    await writeFile(path.join(output, 'clips.txt'), clips.join('\n') + '\n');
    run([
      '-f', 'concat', '-safe', '0', '-i', 'clips.txt', '-vf', 'ass=captions.ass',
      '-an', '-c:v', 'libx264', '-preset', 'medium', '-b:v', '650k',
      '-pix_fmt', 'yuv420p', '-threads', '2', '-r', String(video.fps),
      '-frames:v', String(video.durationInFrames), '-movflags', '+faststart',
      path.join(destination, `${video.kind}.mp4`),
    ], output);
    console.log(`${video.kind}: captioned MP4 ready.`);
  }
}
