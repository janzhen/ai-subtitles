import argparse
import asyncio
import logging

from .whisper_transcribe import main as transcribe_main
from .gpt_translate import main as translate_main


def cli():
    parser = argparse.ArgumentParser(description="AI Subtitles CLI")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(required=True, dest="command")
    transcribe_parser = subparsers.add_parser(
        "transcribe", help="Transcribe a video"
    )
    translate_parser = subparsers.add_parser(
        "translate", help="Translate an srt file"
    )

    transcribe_parser.add_argument(
        "audio_file", help="Path to the audio file to transcribe"
    )
    transcribe_parser.add_argument(
        "--language", "-l", help="Language code, e.g. zh, en, ja, ko"
    )
    transcribe_parser.add_argument(
        "--ss",
        default=0,
        help="Start time in seconds or timestamp, e.g. 10, 00:10",
    )
    transcribe_parser.add_argument(
        "--to", help="End time in seconds or timestamp, e.g. 20, 00:20"
    )
    transcribe_parser.add_argument(
        "--jobs", "-j", type=int, default=4, help="Number of parallel jobs"
    )
    transcribe_parser.add_argument(
        "--silence-thresh",
        type=int,
        default=-40,
        help="Silence threshold in dB",
    )
    transcribe_parser.add_argument(
        "--translate", "-t", action="store_true", help="Translate to English"
    )

    translate_parser.add_argument("input", type=str, help="Input srt file")
    translate_parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="zh-Hans",
        help="Language code, e.g. zh-Hans, en, etc., default is zh-Hans",
    )
    translate_parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="gpt-4-turbo",
        help="GPT model, e.g. gpt-3.5-turbo, gpt-4-turbo, gpt-4, etc., "
        "default is gpt-4-turbo",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    match args.command:
        case "transcribe":
            asyncio.run(
                transcribe_main(
                    args.audio_file,
                    language=args.language,
                    ss=args.ss,
                    to=args.to,
                    silence_thresh=args.silence_thresh,
                    jobs=args.jobs,
                    translate=args.translate,
                )
            )
        case "translate":
            asyncio.run(translate_main(args.input, args.language, args.model))
        case _:
            raise ValueError("Invalid command")
