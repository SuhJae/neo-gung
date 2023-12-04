# coding=utf-8
from openai import OpenAI

client = OpenAI(api_key="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")


def format_notice(notice_text: str) -> str:
    completion = client.chat.completions.create(
        model="ft:gpt-3.5-turbo-1106:personal::8QGmm9Pa",
        messages=[
            {"role": "system",
             "content": "You are a notice editor. For each document, please add the following to the original text:\n1. Refine and Fix the Markdown formatting so it has correct bullets, lists, and formatting.\n2. Remove line breaks if they are in between sentences.\n3. Substitute symbols (Like --> to →)\n4. Do not translate the document, leave it as it is. If there is a translated version, remove it."},
            {"role": "user", "content": notice_text}
        ]
    )

    response_text = completion.choices[0].message.content
    return response_text
