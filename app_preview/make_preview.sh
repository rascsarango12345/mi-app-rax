#!/bin/bash
set -e
cd /app/app_preview

W=1290
H=2796
FPS=30
DUR=4   # seconds per screenshot
TRANS=0.6  # crossfade transition seconds
SRC=/app/appstore_screenshots

# Step 1: Generate Ken Burns clip per screenshot
# We use zoompan to zoom from 1.0 to 1.08 over DUR seconds
make_clip() {
  local IN=$1
  local OUT=$2
  local FRAMES=$((DUR * FPS))
  ffmpeg -y -loop 1 -i "$IN" -t $DUR \
    -vf "scale=${W}*2:${H}*2,zoompan=z='min(zoom+0.0008,1.08)':d=${FRAMES}:s=${W}x${H}:fps=${FPS}" \
    -c:v libx264 -pix_fmt yuv420p -preset fast -crf 18 "$OUT" 2>&1 | tail -2
}

echo "==> Clip 1 of 6 (login)"
make_clip "${SRC}/EN_01_login.png" clip01.mp4
echo "==> Clip 2 of 6 (home / chat)"
make_clip "${SRC}/EN_02_home.png" clip02.mp4
echo "==> Clip 3 of 6 (studio)"
make_clip "${SRC}/EN_03_studio.png" clip03.mp4
echo "==> Clip 4 of 6 (voice)"
make_clip "${SRC}/EN_04_voice.png" clip04.mp4
echo "==> Clip 5 of 6 (premium)"
make_clip "${SRC}/EN_05_premium.png" clip05.mp4
echo "==> Clip 6 of 6 (profile)"
make_clip "${SRC}/EN_06_profile.png" clip06.mp4

echo "==> Combining with crossfade transitions..."

# Calculate xfade offsets:
# clip01 plays 0..4
# clip02 starts crossfade at 4-0.6 = 3.4 (total now 4+(4-0.6) = 7.4)
# etc. Each xfade output ends at: prev_end + (DUR - TRANS)

OFF1=$(echo "$DUR - $TRANS" | bc -l)               # 3.4
OFF2=$(echo "2*$DUR - 2*$TRANS" | bc -l)           # 6.8
OFF3=$(echo "3*$DUR - 3*$TRANS" | bc -l)           # 10.2
OFF4=$(echo "4*$DUR - 4*$TRANS" | bc -l)           # 13.6
OFF5=$(echo "5*$DUR - 5*$TRANS" | bc -l)           # 17.0

ffmpeg -y \
  -i clip01.mp4 -i clip02.mp4 -i clip03.mp4 \
  -i clip04.mp4 -i clip05.mp4 -i clip06.mp4 \
  -filter_complex "\
    [0:v][1:v]xfade=transition=fade:duration=${TRANS}:offset=${OFF1}[v01]; \
    [v01][2:v]xfade=transition=fade:duration=${TRANS}:offset=${OFF2}[v02]; \
    [v02][3:v]xfade=transition=fade:duration=${TRANS}:offset=${OFF3}[v03]; \
    [v03][4:v]xfade=transition=fade:duration=${TRANS}:offset=${OFF4}[v04]; \
    [v04][5:v]xfade=transition=fade:duration=${TRANS}:offset=${OFF5}[vout]" \
  -map "[vout]" \
  -c:v libx264 -pix_fmt yuv420p -preset slow -crf 20 -movflags +faststart \
  rax_ai_preview_silent.mp4 2>&1 | tail -3

echo "==> Adding silent audio track (required by Apple)..."

ffmpeg -y -i rax_ai_preview_silent.mp4 \
  -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=44100" \
  -c:v copy -c:a aac -b:a 128k -shortest \
  rax_ai_preview_final.mp4 2>&1 | tail -3

DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 rax_ai_preview_final.mp4)
SIZE=$(du -h rax_ai_preview_final.mp4 | cut -f1)
RES=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 rax_ai_preview_final.mp4)

echo ""
echo "=========================================="
echo "✅ App Preview Video Generated Successfully"
echo "=========================================="
echo "File: /app/app_preview/rax_ai_preview_final.mp4"
echo "Duration: ${DURATION}s"
echo "Resolution: ${RES}"
echo "Size: ${SIZE}"
echo "=========================================="
