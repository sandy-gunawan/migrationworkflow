import {execFileSync} from 'node:child_process';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ffmpeg from 'ffmpeg-static';
import ffprobe from 'ffprobe-static';

const here = path.dirname(fileURLToPath(import.meta.url));
const target = path.resolve(here, '..', '..', 'docs', 'videos');
const publicDirectory = path.join(here, 'public');
const stories = JSON.parse(await readFile(path.join(here, 'story.json'), 'utf8'));
const fps = 25;
const videos = [];
await mkdir(path.join(publicDirectory, 'captures'), {recursive: true});
await mkdir(target, {recursive: true});

function subtitleTime(frames) {
  const milliseconds = Math.round(frames * 1000 / fps);
  const hours = Math.floor(milliseconds / 3600000);
  const minutes = Math.floor(milliseconds / 60000) % 60;
  const seconds = Math.floor(milliseconds / 1000) % 60;
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, '0')).join(':') +
    ',' + String(milliseconds % 1000).padStart(3, '0');
}

for (const [kind, story] of Object.entries(stories)) {
  const receipt = JSON.parse(await readFile(
    path.join(here, 'raw', kind, 'capture.local.json'), 'utf8',
  ));
  if (receipt.status !== 'success' || receipt.submissions !== 1 ||
      receipt.result.status !== 'success' || receipt.result.route !== 'mcp') {
    throw new Error(`The ${kind} recording is not a verified single live capture.`);
  }
  const source = path.resolve(here, receipt.video);
  const probe = JSON.parse(execFileSync(ffprobe.path, [
    '-v', 'error', '-show_format', '-show_streams', '-of', 'json', source,
  ], {encoding: 'utf8'}));
  const duration = Number(probe.format.duration);
  const maximum = Math.floor((duration - 0.12) * fps);
  execFileSync(ffmpeg, [
    '-hide_banner', '-loglevel', 'error', '-y', '-i', source,
    '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '24',
    '-pix_fmt', 'yuv420p', '-threads', '2', '-movflags', '+faststart',
    path.join(publicDirectory, 'captures', `${kind}.mp4`),
  ]);
  const scenes = [];
  const cues = [];
  let cursor = 0;
  function add(name, start, end, lines, options = {}) {
    if (lines.length > 2 || lines.some((line) => line.length > 42)) {
      throw new Error(`${kind}/${name}: captions must be at most two lines of 42 characters.`);
    }
    const sourceStart = Math.max(0, Math.round(start * fps));
    const sourceEnd = Math.min(maximum, Math.round(end * fps));
    if (sourceStart >= sourceEnd) throw new Error(`Invalid source segment ${kind}/${name}.`);
    const available = sourceEnd - sourceStart;
    const frames = options.card ? 6 * fps : options.cap
      ? Math.min(available, options.cap * fps) : available;
    const scene = {
      name, from: cursor, durationInFrames: Math.max(4 * fps, frames),
      sourceStart, sourceEnd, lines, card: options.card || null,
    };
    scene.playbackRate = available > scene.durationInFrames
      ? available / scene.durationInFrames : 1;
    scenes.push(scene);
    cues.push({
      from: cursor, to: cursor + scene.durationInFrames - 1, lines,
    });
    cursor += scene.durationInFrames;
  }
  const m = receipt.marks;
  add('intro', m.overview, m.overview + 1,
    [story.title, 'Satu pertanyaan, satu alur yang nyata.'], {card: 'intro'});
  add('overview', m.overview, m.definition ?? m.question, story.overview);
  if (m.definition !== undefined) {
    add('definition', m.definition, m.question, story.definition);
  }
  add('question', m.question, m.submitted, story.question);
  add('running', m.submitted, m.completed, story.running, {cap: 20});
  add('answer', m.completed, m.inspector, story.answer);
  add('inspector', m.inspector, m.nativeSource ?? m.trace, story.inspector);
  if (m.nativeSource !== undefined) {
    add('nativeSource', m.nativeSource, m.trace, story.nativeSource);
  }
  add('trace', m.trace, m.closing, story.trace);
  add('closing', m.closing, m.end, story.closing);
  add('outro', m.closing, m.closing + 1,
    ['Lanjutkan lewat panduan di README.', 'MCP01 saja; bukan full50 atau Fabric.'], {card: 'outro'});
  videos.push({
    kind, ...story, fps, width: 1920, height: 1080,
    capturedAt: receipt.captured_at,
    source: `captures/${kind}.mp4`,
    liveRunSeconds: Math.round((m.completed - m.submitted) * 100) / 100,
    durationInFrames: cursor, scenes, cues,
    verifiedResult: receipt.result,
    narration: 'none',
  });
  const srt = cues.map((cue, index) =>
    `${index + 1}\n${subtitleTime(cue.from)} --> ${subtitleTime(cue.to + 1)}\n` +
    cue.lines.join('\n') + '\n',
  ).join('\n');
  await writeFile(path.join(target, `${kind}.srt`), srt);
}
await writeFile(path.join(publicDirectory, 'timeline.json'), JSON.stringify(videos, null, 2) + '\n');
console.log('Prepared deterministic timelines, original capture assets, and subtitles.');
for (const video of videos) {
  console.log(`${video.kind}: ${(video.durationInFrames / fps).toFixed(2)}s; live call ${video.liveRunSeconds}s`);
}
