#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Reads the files containing the syntactic parser output"""

import unittest
import options
import os
import sys

import framenetreader
from framenetallreader import FNAllReader
from conllreader import SyntacticTreeBuilder


class FNParsedReader:
    """A simple object that can read the syntactic parser output and
    build the corresponding syntactic trees.
    
    :var annotation_path: str -- The path to the annotated corpus.
    :var sentences_data: str List -- The parser output for each sentence in the current file.
    :var tree: SyntacticTreeNode -- The tree corresponding to the current sentence.
    """
    
    def __init__(self):
        self.sentences_data = []

    def load_file(self, filename):
        """Set the current file to filename, and fill sentences_data
        accordingly. Not affected by newlines at the end of the file.
        
        :param filename: The file to load.
        :type filename: str.
        """
        
        with open(str(filename)) as content:
            self.sentences_data = content.read().split("\n\n")
            if self.sentences_data[len(self.sentences_data) - 1] == "":
                del self.sentences_data[len(self.sentences_data) - 1]
        
    def sentence_trees(self):
        """Yield all sentence trees in order. To be used with enumerate()"""
        for sentence_id, sentence in enumerate(self.sentences_data):
            tree_builder = SyntacticTreeBuilder(sentence)
            for tree in tree_builder.tree_list:
                yield sentence_id, tree_builder.sentence, tree
        
class FNParsedReaderTest(unittest.TestCase):
    def comp(self, original, parsed):
        return all(
            [x == y or y == "<num>" for x,y in zip(original.split(), parsed.split())]
        )

    def test_sentences_match(self, num_sample = 0):

        # List of sentences and files for which the test would fail because of
        # mistakes in the parser output

        bad_files = ["ANC__110CYL", "ANC__HistoryOfJerusalem",
                "ANC__HistoryOfLasVegas", "ANC__WhereToHongKong",
                "C-4__C-4Text.xml", "KBEval", "LUCorpus-v0.3", "NTI",
                "PropBank__BellRinging", "PropBank__LomaPrieta",
                "IranRelatedQuestions"]

        bad_sentences = [("Miscellaneous__SadatAssassination.xml", 0),
                ("PropBank__AetnaLifeAndCasualty.xml", 0),
                ("PropBank__ElectionVictory.xml", 0),
                ("PropBank__TicketSplitting.xml", 0),
                ("SemAnno__Text1.xml", 3)]


        print("Checking FrameNetParsedReader")
        parsed_reader = FNParsedReader()

        for annotation, parse in zip(options.fulltext_annotations, options.fulltext_parses):
            # Skip unwanted files
            if any([annotation.match('*{}*'.format(bad_file)) for bad_file in bad_files]):
                continue

            parsed_reader.load_file(parse)
            reader = framenetreader.FulltextReader(annotation, False)
            previous_sentence = 0

            for frame in reader.frames:
                # don't test bad sentences in files
                if any(annotation.match(bad_annotation) and bad_sentence_id == frame.sentence_id
                        for bad_annotation, bad_sentence_id in bad_sentences):
                    continue

                # find the correct sentence
                if frame.sentence_id != previous_sentence:
                    for sentence_id, builder_sentence, tree in parsed_reader.sentence_trees():
                        if sentence_id == frame.sentence_id:
                            sentence = tree.flat()
                            self.assertEqual(builder_sentence, sentence)
                            previous_sentence = frame.sentence_id

                # test the sentence
                self.assertTrue(self.comp(frame.sentence, sentence))
