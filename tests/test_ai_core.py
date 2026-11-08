"""Тесты текстовых примитивов и BM25-ретривера."""

from app.ai.retriever import Retriever
from app.ai.text import numbers, overlap, sentences, shorten, stems, tokenize


def test_tokenize_drops_short_and_stopwords() -> None:
    assert tokenize("La remise des prix au comptoir") == ["remise", "prix", "comptoir"]


def test_stem_is_stable_prefix() -> None:
    assert stems("ordonnances ordonnance") == ["ordonn", "ordonn"]


def test_sentences_split_on_punctuation() -> None:
    assert len(sentences("Première règle. Deuxième règle ! Troisième")) == 3


def test_numbers_parse_french_decimals() -> None:
    assert numbers("remise de 5,5 % et 30 %") == [5.5, 30.0]


def test_overlap_is_jaccard() -> None:
    assert overlap(["a", "b"], ["b", "c"]) == 1 / 3


def test_shorten_respects_limit() -> None:
    assert len(shorten("x" * 400, 100)) == 100


def test_retriever_ranks_relevant_chunk_first() -> None:
    index = Retriever.from_texts(["remise maximale autorisée 30 %", "température +2 +8"]) 
    assert index.search("remise")[0].chunk.text.startswith("remise")


def test_retriever_returns_empty_for_unknown_term() -> None:
    index = Retriever.from_texts(["remise maximale autorisée"]) 
    assert index.search("zzzz") == []
