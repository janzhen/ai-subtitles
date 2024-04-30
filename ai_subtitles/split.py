import argparse
import pathlib

from pydub import AudioSegment, effects, silence


def split(audio, silence_thresh, min_length):
    chunks = silence.split_on_silence(
        audio,
        min_silence_len=2000,
        silence_thresh=silence_thresh,
        keep_silence=True,
        seek_step=10,
    )

    parts = []
    part = None
    for chunk in chunks:
        part = part + chunk if part else chunk
        if part.duration_seconds < min_length:
            continue

        parts.append(part)
        part = None

    if part is not None:
        parts.append(part)

    return parts


def main(input_file, silence_thresh, part_min_length):
    input_file = pathlib.Path(input_file)
    assert input_file.exists(), f"File {input_file} does not exist"
    parts_dir = input_file.with_suffix("").with_name(
        f"{input_file.stem}_parts"
    )
    parts_dir.mkdir(exist_ok=True)

    audio = AudioSegment.from_file(input_file)
    audio = audio.set_channels(1).set_frame_rate(16000)

    parts = split(audio, silence_thresh, part_min_length)
    for i, part in enumerate(parts):
        part = effects.normalize(part)
        part.export(parts_dir / f"part_{i:02d}.mp3")
        print(f"Exported part {i}, duration: {part.duration_seconds}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input file")
    parser.add_argument("--silence-thresh", type=int, default=-40)
    parser.add_argument(
        "--part-min-length",
        type=int,
        default=600,
        help="Minimum length of a part in seconds",
    )
    args = parser.parse_args()
    main(args.input, args.silence_thresh, args.part_min_length)
