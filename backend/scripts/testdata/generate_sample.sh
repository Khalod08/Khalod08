#!/usr/bin/env bash
# Regenerates messy_test.mp3: a synthetic, copyright-free "messy audio" fixture
# for stage-1 pipeline testing — fast rap-cadence verses, an overlapping-vocal
# chorus, background noise, and lo-fi/compression distortion. Requires
# espeak-ng and ffmpeg on PATH.
set -euo pipefail
cd "$(dirname "$0")"

# --- fast rap-style verse lines, high speed + slight pitch variation ---
i=0
while IFS= read -r line; do
  i=$((i + 1))
  espeak-ng -v en-us -s 235 -p 45 -a 180 "$line" --stdout > "verse_${i}.wav"
done < verse_lines.txt

# --- chorus: two voices overlapping with a 150ms offset (simulates overlapping vocals) ---
espeak-ng -v en-us+m3 -s 190 -p 40 "$(cat chorus_line.txt)" --stdout > chorus_a.wav
espeak-ng -v en-us+m4 -s 205 -p 60 "$(cat chorus_line.txt)" --stdout > chorus_b.wav
ffmpeg -y -i chorus_a.wav -i chorus_b.wav -filter_complex \
  "[1:a]adelay=150|150[b];[0:a][b]amix=inputs=2:duration=longest:normalize=0[out]" \
  -map "[out]" -ac 1 -ar 22050 chorus_mixed.wav

# --- concat verse + chorus + repeated verse into one dry vocal track ---
cat > concat_list.txt <<'EOF'
file 'verse_1.wav'
file 'verse_2.wav'
file 'verse_3.wav'
file 'verse_4.wav'
file 'chorus_mixed.wav'
file 'verse_2.wav'
EOF
ffmpeg -y -f concat -safe 0 -i concat_list.txt -ac 1 -ar 22050 dry_mix.wav
duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 dry_mix.wav)

# --- background noise bed + lo-fi/distortion chain (bandpass, bitcrush, hot compression) ---
ffmpeg -y -f lavfi -i "anoisesrc=d=${duration}:c=pink:a=0.35" \
  -filter_complex "lowpass=f=800,highpass=f=80" -ac 1 -ar 22050 -t "$duration" noise_bed.wav

ffmpeg -y -i dry_mix.wav -i noise_bed.wav -filter_complex \
  "[0:a]volume=1.0[voc];[1:a]volume=0.5[bed];[voc][bed]amix=inputs=2:duration=first:normalize=0[mixed];\
   [mixed]highpass=f=120,lowpass=f=6000,acrusher=bits=6:mode=log:aa=1,acompressor=threshold=0.1:ratio=6:attack=5:release=50[out]" \
  -map "[out]" -ac 1 -ar 22050 messy_test.wav

# --- final lossy encode (low-bitrate mp3) to add compression artifacts ---
ffmpeg -y -i messy_test.wav -codec:a libmp3lame -b:a 48k -ar 22050 messy_test.mp3

rm -f verse_*.wav chorus_a.wav chorus_b.wav chorus_mixed.wav dry_mix.wav noise_bed.wav messy_test.wav concat_list.txt
echo "Wrote messy_test.mp3 ($(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 messy_test.mp3)s)"
