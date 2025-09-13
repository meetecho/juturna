from collections import deque
from typing import Iterable

from juturna.components import Message
from juturna.components import BaseNode

from juturna.payloads._payloads import ObjectPayload

from plugins.nodes.proc._prompter_words import prompter_utils


class PrompterWords(BaseNode[ObjectPayload, ObjectPayload]):
    def __init__(self,
                 static_replace: dict,
                 regex_replace: list,
                 keywords: list,
                 cut_edge_word_thresh: float,
                 overlap_thresh: float,
                 matcher_thresh: int,
                 **kwargs):
        super().__init__(**kwargs)

        self._static_replace = static_replace
        self._regex_replace = regex_replace
        self._keywords = keywords

        self._cut_edge_word_thresh = cut_edge_word_thresh
        self._overlap_thresh = overlap_thresh
        self._matcher_thresh = matcher_thresh

        self._last_words = list()
        self._low_drop = deque(list(), maxlen=2)
        self._covered_to = -1.0

    def update(self, message: Message[ObjectPayload]):
        self.logger.info(f'receive:    {message.version}')
        self.logger.info(f'content:    {message.payload}')
        self.logger.info(f'transcript: {message.payload['transcript']}')

        # wordlist = message.payload
        wordlist = message.payload['transcript']

        to_send = Message[ObjectPayload](
            creator=self.name,
            version=message.version,
            payload=ObjectPayload())

        payload = {
            'sequence_number': message.version,
            'suggestion': '',
            'silence': False,
            'hallucination': False
        }

        # no words received from transcriber: last chunk is silence
        if len(wordlist) == 0:
            payload['suggestion'] = PrompterWords.concat_words(
                list(self._low_drop)[::-1])
            payload['silence'] = payload['suggestion'] == ''

            self._last_words.clear()
            self._low_drop.clear()

            to_send.payload = payload

            to_send.timer(self.name, -1)
            self.transmit(to_send)

            self.logger.info(f'transmit: {to_send.version}')

            return

        # drop last 2 words if low on probability
        if wordlist[-1]['probability'] < self._cut_edge_word_thresh:
            self._low_drop.append(wordlist.pop(-1))

            try:
                self._low_drop.append(wordlist.pop(-1))
            except IndexError:
                ...
        else:
            self._low_drop.clear()

        wordlist = [w for w in wordlist if w['start'] >= self._covered_to]

        # chunk received after silence: generate suggestion
        if len(self._last_words) == 0:
            self._last_words = wordlist

            try:
                self._covered_to = self._last_words[-1]['start']
            except IndexError:
                ...

            suggested_text = PrompterWords.concat_words(wordlist)
            suggested_text = prompter_utils.clean_suggestion(
                suggested_text, self._static_replace, self._regex_replace,
                self._keywords, self._matcher_thresh)

            payload['suggestion'] = suggested_text
            to_send.payload = payload
            # to_send.payload['suggestion'] = payload

            self.transmit(to_send)
            self.logger.info(f'{self.name} transmit: {to_send.version}')

            return

        with to_send.timeit(self.name):
            coverage_from = self._last_words[-1]['end']
            # coverage_to = message.meta['end_abs']
            coverage_to = message.payload['transcript'][-1]['end']

            best_subset, best_coverage = prompter_utils.compute_coverage(
                wordlist, coverage_from, coverage_to)

            if len(best_subset) > 0:
                # check for duplicates at the juncture of the best word subset
                cross_overlap_perc = prompter_utils.word_overlap(
                    best_subset[0], self._last_words[-1])

                # if a duplicated word overlaps more than the specified threshold,
                # drop it from the subset of suggested words
                if cross_overlap_perc > self._overlap_thresh:
                    best_subset = best_subset[1:]

            hallucinated_words = prompter_utils.detect_overlapping_words(
                best_subset, self._overlap_thresh)

            if len(hallucinated_words) > 0:
                # to_send.payload['hallucination'] = True
                best_subset = [w for i, w in enumerate(best_subset)
                               if i not in hallucinated_words]

            suggested_text = PrompterWords.concat_words(best_subset)

            suggested_text = prompter_utils.clean_suggestion(
                suggested_text, self._static_replace, self._regex_replace,
                self._keywords, self._matcher_thresh)

        payload['suggestion'] = suggested_text
        payload['silence'] = suggested_text == ''
        to_send.payload = payload
        # to_send.payload['suggestion'] = payload

        self.transmit(to_send)

        self._last_words = best_subset

        if len(self._last_words) > 0:
            self._covered_to = self._last_words[-1]['start']

    @staticmethod
    def concat_words(words: Iterable) -> str:
        return ''.join([w['word'] for w in words])
