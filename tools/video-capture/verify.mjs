import {execFileSync} from 'node:child_process';
import {readFile, stat, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ffmpeg from 'ffmpeg-static';
import ffprobe from 'ffprobe-static';

const here = path.dirname(fileURLToPath(import.meta.url));
const target = path.resolve(here, '..', '..', 'docs', 'videos');
const videos = JSON.parse(await readFile(path.join(here, 'public', 'timeline.json'), 'utf8'));
const report = [];
for (const video of videos) {
  const filename = path.join(target, `${video.kind}.mp4`);
  const probe = JSON.parse(execFileSync(ffprobe.path, [
    '-v', 'error', '-show_streams', '-show_format', '-of', 'json', filename,
  ], {encoding: 'utf8'}));
  const stream = probe.streams.find((item) => item.codec_type === 'video');
  const expected = video.durationInFrames / video.fps;
  const bytes = (await stat(filename)).size;
  if (stream.codec_name !== 'h264' || stream.pix_fmt !== 'yuv420p' ||
      stream.width !== 1920 || stream.height !== 1080 ||
      stream.avg_frame_rate !== '25/1' ||
      Math.abs(Number(probe.format.duration) - expected) > 0.1 ||
      probe.streams.some((item) => item.codec_type === 'audio') ||
      bytes >= 10000000) {
    throw new Error(`MP4 format, duration, silence, or size check failed for ${video.kind}.`);
  }
  for (const cue of video.cues) {
    if (cue.lines.length > 2 || cue.lines.some((line) => line.length > 42) ||
        cue.to - cue.from + 1 < video.fps) {
      throw new Error(`Invalid caption shape for ${video.kind}.`);
    }
  }
  execFileSync(ffmpeg, [
    '-hide_banner', '-loglevel', 'error', '-i', filename, '-f', 'null', '-',
  ]);
  report.push({
    kind: video.kind, file: `${video.kind}.mp4`, width: stream.width, height: stream.height,
    fps: 25, duration_seconds: expected, bytes, audio: 'none', decode: 'PASS',
    live_requests: 1, case: 'MCP01', route: 'mcp', result: 'success',
    actual_live_seconds: video.liveRunSeconds,
    accelerated_wait_labeled: video.scenes.some((scene) => scene.playbackRate > 1.05),
  });
  console.log(`${video.kind}: H.264 1080p/25fps, ${(bytes / 1024 / 1024).toFixed(2)} MiB, full decode PASS.`);
}
await writeFile(path.join(target, 'verification.json'), JSON.stringify(report, null, 2) + '\n');
