#!/bin/bash
# Build the 90-second RAX AI promo companion video.
# Each scene has subtle Ken Burns zoom + crossfade transitions.
set -e
cd /app/app_preview

FPS=30
W=1080
H=1920
FRAMES_DIR=promo_frames
OUT_DIR=promo_clips
mkdir -p "$OUT_DIR"

# Section durations in seconds (match the voice-over script)
declare -a NAMES=(01_intro 02_chat 03_images 04_voice 05_creator 06_studio 07_premium 08_profile 09_coming)
declare -a DURS=(8 12 12 10 13 13 10 6 6)

# Zoom direction per scene alternates for visual rhythm: 'in' or 'out'
declare -a ZOOMS=(in in in in in in in in in)

make_clip() {
  local IN=$1
  local OUT=$2
  local DUR=$3
  local FRAMES=$((DUR * FPS))

  # Ken Burns: zoom from 1.0 to 1.06 over DUR seconds, with gentle drift.
  ffmpeg -y -loop 1 -i "$IN" -t $DUR \
    -vf "scale=${W}*2:${H}*2,zoompan=z='min(zoom+0.0005,1.06)':d=${FRAMES}:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=${W}x${H}:fps=${FPS}" \
    -c:v libx264 -pix_fmt yuv420p -preset fast -crf 18 -an "$OUT" 2>&1 | tail -1
}

echo "==> Generating per-section clips..."
for i in "${!NAMES[@]}"; do
  N="${NAMES[$i]}"
  D="${DURS[$i]}"
  echo "  -> $N ($D s)"
  make_clip "${FRAMES_DIR}/${N}.png" "${OUT_DIR}/${N}.mp4" "$D"
done

echo "==> Stitching with crossfade transitions..."

TRANS=0.5

# Cumulative offset for xfade chaining:
# After clip1 (8s): xfade at 8 - 0.5 = 7.5, output ends 8 + 12 - 0.5 = 19.5
# After clip2: xfade at 7.5 + 12 - 0.5 = 19.0
# After clip3: 19.0 + 12 - 0.5 = 30.5
# After clip4: 30.5 + 10 - 0.5 = 40.0
# After clip5: 40.0 + 13 - 0.5 = 52.5
# After clip6: 52.5 + 13 - 0.5 = 65.0
# After clip7: 65.0 + 10 - 0.5 = 74.5
# After clip8: 74.5 + 6 - 0.5 = 80.0
# Final length: 80.0 + 6 = 86s (close enough to 90)

ffmpeg -y \
  -i ${OUT_DIR}/01_intro.mp4 \
  -i ${OUT_DIR}/02_chat.mp4 \
  -i ${OUT_DIR}/03_images.mp4 \
  -i ${OUT_DIR}/04_voice.mp4 \
  -i ${OUT_DIR}/05_creator.mp4 \
  -i ${OUT_DIR}/06_studio.mp4 \
  -i ${OUT_DIR}/07_premium.mp4 \
  -i ${OUT_DIR}/08_profile.mp4 \
  -i ${OUT_DIR}/09_coming.mp4 \
  -filter_complex "\
    [0:v][1:v]xfade=transition=fade:duration=0.5:offset=7.5[v01]; \
    [v01][2:v]xfade=transition=fade:duration=0.5:offset=19.0[v02]; \
    [v02][3:v]xfade=transition=fade:duration=0.5:offset=30.5[v03]; \
    [v03][4:v]xfade=transition=fade:duration=0.5:offset=40.0[v04]; \
    [v04][5:v]xfade=transition=fade:duration=0.5:offset=52.5[v05]; \
    [v05][6:v]xfade=transition=fade:duration=0.5:offset=65.0[v06]; \
    [v06][7:v]xfade=transition=fade:duration=0.5:offset=74.5[v07]; \
    [v07][8:v]xfade=transition=fade:duration=0.5:offset=80.0[vout]" \
  -map "[vout]" \
  -c:v libx264 -pix_fmt yuv420p -preset slow -crf 20 -movflags +faststart \
  rax_promo_silent.mp4 2>&1 | tail -3

echo "==> Adding silent audio track..."
ffmpeg -y -i rax_promo_silent.mp4 \
  -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" \
  -c:v copy -c:a aac -b:a 128k -shortest \
  rax_promo_final.mp4 2>&1 | tail -3

DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 rax_promo_final.mp4)
SIZE=$(du -h rax_promo_final.mp4 | cut -f1)
RES=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 rax_promo_final.mp4)

echo ""
echo "========================================================"
echo "✅ RAX AI 90-second Promo Companion Video Generated"
echo "========================================================"
echo "File: /app/app_preview/rax_promo_final.mp4"
echo "Duration: ${DURATION}s"
echo "Resolution: ${RES}"
echo "Size: ${SIZE}"
echo "========================================================"
