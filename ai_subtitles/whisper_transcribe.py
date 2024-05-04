import argparse
import asyncio
import logging
import os
import pathlib
from datetime import datetime, timedelta

import srt
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydub import AudioSegment

from .gpt_translate import translate_subtitles
from .split import split

logger = logging.getLogger(__name__)

load_dotenv()
if not os.environ.get("OPENAI_API_KEY"):
    logger.error("Missing OPENAI_API_KEY. Set it environment variable.")

client = AsyncOpenAI()

SEMAPHORE = None


async def transcribe(audio_file, language=None, offset=0):
    async with SEMAPHORE:
        offset = timedelta(milliseconds=offset)
        logger.info(f"Transcribing {offset}...")

        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.mp3", audio_file),
            response_format="srt",
            language=language,
        )

    # add start time to each subtitle
    subs_ajusted = []
    subs = list(srt.parse(transcription))
    for i, sub in enumerate(subs):
        sub.start = sub.start + offset
        sub.end = sub.end + offset
        subs_ajusted.append(sub)

    return subs_ajusted


async def transcribe_parts(
    audio_parts, language=None, ss=0
) -> list[srt.Subtitle]:
    offset = ss * 1000

    tasks = []
    async with asyncio.TaskGroup() as tg:
        for audio_part in audio_parts:
            tasks.append(
                tg.create_task(
                    transcribe(
                        audio_part.export(format="mp3"),
                        language,
                        offset,
                    )
                )
            )
            offset += len(audio_part)

    subs = []
    for task in tasks:
        subs.extend(task.result())
    return subs


def convert_audio(audio_file, ss=0, to=None, silence_thresh=-40):
    MAX_DURATION = 900  # 15 minutes
    MIN_SPLIT_DURATION = 600  # 10 minutes

    logger.info(f"Converting {audio_file}...")

    audio_file = pathlib.Path(audio_file)
    audio = AudioSegment.from_file(audio_file)

    if to is not None:
        audio = audio[ss * 1000 : to * 1000]
    else:
        audio = audio[ss * 1000 :]

    if audio.channels > 1:
        audio = audio.set_channels(1)
    if audio.frame_rate > 16000:
        audio = audio.set_frame_rate(16000)

    if audio.duration_seconds < MAX_DURATION:
        return [audio]

    logger.info(
        f"Audo duration: {audio.duration_seconds} longer than "
        f"{MAX_DURATION}, splitting..."
    )
    parts = split(audio, silence_thresh, MIN_SPLIT_DURATION)
    logger.info(f"Split into {len(parts)} parts")
    return [part for part in parts]


def write_srt(subs, srt_file):
    if srt_file.exists():
        # read existing srt file
        logger.info("Srt file already exists, backing up...")
        backup_file = srt_file.with_name(
            f"{srt_file.stem}.{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.srt"
        )
        srt_file.rename(backup_file)
        logger.info(f"Backup created: {backup_file}")

    with open(srt_file, "w") as f:
        f.write(srt.compose(subs))
    logger.info(f"Transcription saved to {srt_file}")


def overlap_check(original_subs, ss, to) -> bool:
    for sub in original_subs:
        if sub.end.total_seconds() < ss:
            continue
        if to is not None and sub.start.total_seconds() > to:
            continue
        logger.info(f"Overlapping subtitle found: {sub.start} - {sub.end}")
        return True

    return False


def read_srt(srt_file: pathlib.Path) -> list[srt.Subtitle]:
    try:
        with open(srt_file) as f:
            return list(srt.parse(f.read()))
    except FileNotFoundError:
        return []


async def translate(subtitles, language, model):
    return await translate_subtitles(subtitles, language, model)


async def main(
    audio_file,
    language=None,
    ss=0,
    to=None,
    silence_thresh=-40,
    jobs=4,
    translate_to=None,
    translation_model=None,
):
    global SEMAPHORE
    SEMAPHORE = asyncio.Semaphore(max(jobs, 1))

    audio_file = pathlib.Path(audio_file)
    if not audio_file.exists():
        logger.error(f"File not found: {audio_file}")
        return

    # ss and to may be seconds or timestamps like "00:00:00", parse to seconds
    if isinstance(ss, str):
        ss = sum(int(x) * 60**i for i, x in enumerate(reversed(ss.split(":"))))
    if to is not None and isinstance(to, str):
        to = sum(int(x) * 60**i for i, x in enumerate(reversed(to.split(":"))))

    if to is not None and to <= ss:
        logger.error("End time must be greater than start time")
        return

    srt_file = audio_file.with_suffix(".srt")
    original_subs = read_srt(srt_file)
    if overlap_check(original_subs, ss, to):
        logger.error(
            "Overlapping subtitles, please adjust start and end time "
            "or backup and remove the existing srt file."
        )
        return

    audio_parts = convert_audio(audio_file, ss, to, silence_thresh)
    subs = await transcribe_parts(audio_parts, language, ss)

    write_srt(original_subs + subs, srt_file)

    if translate_to:
        trans_subs = await translate(subs, translate_to, translation_model)
        trans_srt_file = pathlib.Path(audio_file).with_suffix(
            f".{translate_to.split('-')[0].split('_')[0]}.srt"
        )
        ori_trans_subs = read_srt(trans_srt_file)
        write_srt(ori_trans_subs + trans_subs, trans_srt_file)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "audio_file", help="Path to the audio file to transcribe"
    )
    parser.add_argument(
        "--language", "-l", help="Language code, e.g. zh, en, ja, ko"
    )
    parser.add_argument(
        "--ss",
        default=0,
        help="Start time in seconds or timestamp, e.g. 10, 00:10",
    )
    parser.add_argument(
        "--to", help="End time in seconds or timestamp, e.g. 20, 00:20"
    )
    parser.add_argument(
        "--jobs", "-j", type=int, default=4, help="Number of parallel jobs"
    )
    parser.add_argument(
        "--silence-thresh",
        type=int,
        default=-40,
        help="Silence threshold in dB",
    )
    parser.add_argument(
        "--translate-to",
        "-t",
        default="zh-CN",
        help="Language code, e.g. zh-CN, en, etc., default is zh-CN",
    )
    parser.add_argument(
        "--translate-model",
        "-m",
        default="gpt-4-turbo",
        help="GPT model, e.g. gpt-3.5-turbo, gpt-4-turbo, gpt-4, etc., "
        "default is gpt-4-turbo",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    asyncio.run(
        main(
            args.audio_file,
            language=args.language,
            ss=args.ss,
            to=args.to,
            silence_thresh=args.silence_thresh,
            jobs=args.jobs,
            translate_to=args.translate_to,
            translation_model=args.translate_model,
        )
    )
