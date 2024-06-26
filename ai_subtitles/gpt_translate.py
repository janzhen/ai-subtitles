import argparse
import asyncio
import logging
import os
import pathlib
from datetime import datetime

import srt
from dotenv import load_dotenv
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

load_dotenv()
if not os.environ.get("OPENAI_API_KEY"):
    logger.error("Missing OPENAI_API_KEY. Set it environment variable.")

client = AsyncOpenAI()

SYS_PROMPT = """You are a translation expert proficient in various languages that can only translate text and cannot interpret it. Translate user's input into %s.

The format of input is SRT. Translate the subtitle content only.

Do not change the format of the input.
"""  # noqa

SEMAPHORE = asyncio.Semaphore(4)


async def gpt_translate(text, language, model):
    async with SEMAPHORE:
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYS_PROMPT % language},
                {"role": "user", "content": text},
            ],
        )

    logger.debug(completion)
    return completion.choices[0].message.content


async def translate_subtitles(subtitles, language, model):
    BATCH_SIZE = 50

    tasks = []
    async with asyncio.TaskGroup() as tg:
        for i in range(0, len(subtitles), BATCH_SIZE):
            content = srt.compose(subtitles[i : i + BATCH_SIZE])
            logger.debug(f"srt content for translation: {content}")

            tasks.append(
                tg.create_task(gpt_translate(content, language, model))
            )
            logger.info(f"Task created for {i}-{i+BATCH_SIZE}")

    trans_subtitles = []
    for task in tasks:
        translation = task.result()
        logger.debug(f"Translation: {translation}")
        trans_subtitles.extend(srt.parse(translation))

    return trans_subtitles


async def main(input, language, model):
    input = pathlib.Path(input)
    if not input.exists():
        logger.error(f"{input} does not exist")
        return

    output = pathlib.Path(input).with_suffix(
        f".{language.split('-')[0].split('_')[0]}.srt"
    )

    subtitles = []

    with open(input, "r") as f:
        for sub in srt.parse(f.read()):
            sub.content = sub.content.strip()
            subtitles.append(sub)
    logger.debug(f"Subtitles count: {len(subtitles)}")
    logger.info(f"Translating {input} to {language}")

    trans_subtitles = await translate_subtitles(subtitles, language, model)
    srt_content = srt.compose(trans_subtitles)
    logger.debug(f"Translated srt content: {srt_content}")

    if output.exists():
        backup_file = output.with_name(
            f"{output.stem}.{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.srt"
        )
        output.rename(backup_file)
        logger.info(f"Backup created: {backup_file}")

    with open(output, "w") as f:
        f.write(srt_content)

    logger.info(f"Translated srt file saved to {output}")


def cli():
    parser = argparse.ArgumentParser(description="Translate srt file")
    parser.add_argument("input", help="Input srt file")
    parser.add_argument(
        "--language",
        "-l",
        default="zh-CN",
        help="Language code, e.g. zh-CN, en, etc., default is zh-CN",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="gpt-3.5-turbo",
        help="GPT model, e.g. gpt-3.5-turbo, gpt-4-turbo, gpt-4, etc., "
        "default is gpt-3.5-turbo",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose mode"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    asyncio.run(main(args.input, args.language, args.model))
