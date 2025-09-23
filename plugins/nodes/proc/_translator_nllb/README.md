# translator_nllb

This is a translation node that accepts object payloads containing text and
produces object payloads.



## Node type: proc

## Node class name: TranslatorNllb

## Node name: translator_nllb


## Configuration

- `mdoel_name`: the model name to be used for the translation
- `tokenizer_name`: the tokenizer name to be used for the translation
- `src_language`: language of the source text
- `dst_language`: target language of the generated text
- `device`: where the translation model should run
- `max_length`: maximum allowed length of input text
- `buffer_length`: how many input messaged to buffer before transcription
