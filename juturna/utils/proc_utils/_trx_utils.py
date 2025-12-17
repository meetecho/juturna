def rescale_trx_words(words: list, buffer: list) -> list:
    if not buffer or not words:
        return list()

    chunk_time_map = list()
    accumulated_time = 0

    for m in buffer:
        start_abs = m.payload.start
        speech_offset_map = []

        for segment in m.meta['speech_timestamps']:
            speech_start_abs = start_abs + segment['start_s']
            speech_end_abs = start_abs + segment['end_s']
            speech_offset_map.append(
                (speech_start_abs, speech_end_abs, accumulated_time)
            )
            accumulated_time += segment['end_s'] - segment['start_s']

        chunk_time_map.append((start_abs, speech_offset_map))

    rescaled_words = list()

    for word in words:
        word_start_rescaled = None
        word_end_rescaled = None

        for _, speech_map in chunk_time_map:
            for sp_start_abs, sp_end_abs, offset in speech_map:
                start = word['start']
                end = word['end']

                if offset <= start < offset + (sp_end_abs - sp_start_abs):
                    word_start_rescaled = sp_start_abs + (start - offset)

                if offset <= end < offset + (sp_end_abs - sp_start_abs):
                    word_end_rescaled = sp_start_abs + (end - offset)

                if (
                    word_start_rescaled is not None
                    and word_end_rescaled is not None
                ):
                    break

            if (
                word_start_rescaled is not None
                and word_end_rescaled is not None
            ):
                break

        if word_start_rescaled is not None and word_end_rescaled is not None:
            rescaled_words.append(
                {
                    'word': word['word'],
                    'start': word_start_rescaled,
                    'end': word_end_rescaled,
                    'probability': word['probability'],
                }
            )

    return rescaled_words
