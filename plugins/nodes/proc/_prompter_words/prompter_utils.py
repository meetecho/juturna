import re
import string

import rapidfuzz.process as process
import rapidfuzz.utils as fuzz_utils

from rapidfuzz.distance import Indel


def compute_coverage(words: list, cov_from: float, cov_to: float) -> tuple:
    span_to_cover = cov_to - cov_from
    words = sorted(words, key=lambda x: x['start'])

    included_words = list()
    effective_coverage = 0
    current_end = cov_from

    for word in words:
        start, end = word['start'], word['end']

        overlap = max(0, current_end - start)
        new_coverage = max(0, end - max(current_end, start))

        if new_coverage > overlap:
            included_words.append(word)
            effective_coverage += new_coverage
            current_end = max(current_end, end)

    coverage_ratio = effective_coverage / span_to_cover

    return included_words, coverage_ratio


def word_overlap(first_word: dict, second_word: dict) -> float:
    """Overlap percentage

    Given 2 words, this method computes the overlap area between them, and then
    returns the percentage of the second word included in the overlap area.

    """
    overlap_start = max(first_word['start'], second_word['start'])
    overlap_end = min(first_word['end'], second_word['end'])
    overlap_duration = max(0, overlap_end - overlap_start)

    second_word_duration = second_word['end'] - second_word['start']

    overlap_percentage = 0

    if second_word_duration > 0:
        overlap_percentage = overlap_duration / second_word_duration

    return overlap_percentage


def detect_overlapping_words(words: list, overlap_thresh: float) -> list:
    marked_for_deletion = list()

    for i in range(len(words) - 1):
        current_word = words[i]
        next_word = words[i + 1]

        if (current_word['start'] == next_word['start'] and
                current_word['end'] == next_word['end'] and
                current_word['word'] == next_word['word']):
            marked_for_deletion.append(i + 1)

            continue

        overlap_percentage = word_overlap(current_word, next_word)

        if overlap_percentage > overlap_thresh:
            marked_for_deletion.append(i + 1)

    return marked_for_deletion


def clean_suggestion(text: str,
                     static_rules: dict,
                     regex_rules: list,
                     keywords: list,
                     matcher_thresh: int) -> str:
    text = apply_static_replace(text, static_rules)
    text = apply_regex_replace(text, regex_rules)
    text = match_keywords(text, keywords, matcher_thresh)

    return text


def apply_static_replace(text: str, rules: dict) -> str:
    for search_key, replace_txt in rules.items():
        pattern = re.compile(re.escape(search_key), re.IGNORECASE)

        text = pattern.sub(replace_txt, text)

    return text


def apply_regex_replace(text: str, rules: list) -> str:
    for replace_rule in rules:
        text = re.sub(rf'{replace_rule}', '', text)

    return text


def match_keywords(text: str, keywords: list, matcher_thresh: int) -> str:
    words = text.split()
    corrected_words = list()
    special_chars = string.punctuation + string.whitespace
    i = 0

    while i < len(words):
        best_match = None
        best_score = 0
        best_j = i

        for j in range(1, min(3, len(words) - i + 1)):
            phrase = ' '.join(words[i:i + j])
            spec_char_found = list()

            for char in reversed(phrase):
                if char in special_chars:
                    spec_char_found.append(char)
                else:
                    break

            match = process.extractOne(
                phrase, keywords,
                processor=fuzz_utils.default_process,
                scorer=Indel.normalized_similarity)

            if match[1] > best_score:
                best_match = match[0] + ''.join(spec_char_found)
                best_score = match[1]
                best_j = i + j - 1

        if best_score > matcher_thresh:
            corrected_words.append(best_match)
            i = best_j + 1
        else:
            corrected_words.append(words[i])
            i += 1

    return ' '.join(corrected_words)

