"""Conservative sentence endings, including punctuation inside closing quotes."""
POSTPROCESSOR_VERSION='terminal-quotes-v1'


def finish_native_sentence(text):
    text=text.strip()
    if not text: return text
    closers='\"\'”’»)]} '
    terminal=('।','.','!','?','॥','…')
    # Also repairs the previous adapter's appended danda after a quoted ending.
    if text.endswith('।') and text[:-1] and text[:-1][-1] in closers and text[:-1].rstrip(closers).endswith(terminal):
        text=text[:-1]
    return text if text.rstrip(closers).endswith(terminal) else text+'।'
