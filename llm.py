#Name:  M.HimaBindu
#Emp Num:  1204977

from google.genai import types


def generate_content(client, contents, config=None):
    if isinstance(contents, str):
        contents = types.Content(
            role="user",
            parts=[types.Part.from_text(text=contents)]
        )

    return client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=contents,
        config=config,
    )
